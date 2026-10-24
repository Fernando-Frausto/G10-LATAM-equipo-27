# Plan de Implementación — Spec 024: Generación de Reportes OCI desde Historial Semanal con Inyección de Copys Reales y Alta Velocidad

## 1. Resumen Arquitectónico y Diagnóstico Técnico

### 1.1 Contexto del Ecosistema de Datos
El sistema CloudEdTech / CommunityLab opera con una arquitectura híbrida de almacenamiento dividida en tres capas de persistencia y distribución:
1. **Base de Datos Transaccional Local SQLite (`communitylab.db` / `motor-ia/communitylab.db`):**
   - Centro operacional de ultra-alta velocidad (< 2 ms) para ingesta, curaduría, análisis y visualización inmediata en la interfaz gráfica.
   - Contiene las tablas operacionales `interacciones` y `contenidos_generados`.
2. **Clúster Supabase Enoc PostgreSQL (`swdoucawdasxmnomlcfu`):**
   - Repositorio remoto canónico. Desde la Especificación 023, cada publicación individual de canal (LinkedIn, Discord, X) o aprobación masiva Human-in-the-Loop (HITL) en `ContentStudio` replica de manera desacoplada y asíncrona un registro canónico autosuficiente en la tabla `public.historial_reportes_semanales`.
   - Cada registro almacena en `contenido_original` los metadatos y KPIs del mensaje original analizado, y en `copys_generados` los textos de copy redactados por IA y aprobados/editados por el operador humano.
3. **Distribución y Almacenamiento OCI Object Storage (`communitylab-assets`) y Disco Local (`reportes/{semana}.json`):**
   - Almacén de activos y distribución semanal empaquetada (`paquete-distribucion.json`) consumido por sistemas externos, dashboards ejecutivos y el equipo de copywriting.

```
                                  [ Operador Editorial HITL / Publicación ]
                                                     │
                                                     ▼
                                      ┌──────────────────────────────┐
                                      │  Mesa de Trabajo / Redacción │
                                      │   (/api/v1/mototradis/...)   │
                                      └──────────────┬───────────────┘
                                                     │
                             ┌───────────────────────┴───────────────────────┐
                             │                                               │
                             ▼ (Inmediato < 2 ms)                            ▼ (asyncio.create_task)
              ┌─────────────────────────────┐                 ┌─────────────────────────────┐
              │ SQLite Local communitylab.db│                 │  Supabase Enoc PostgreSQL   │
              │  (interacciones curadas y   │                 │ historial_reportes_semanales│
              │         descartadas)        │                 │ (mensajes con copys reales) │
              └──────────────┬──────────────┘                 └──────────────┬──────────────┘
                             │                                               │
                             │ (Descartados + Fallback)                      │ (Aprobados con copys reales)
                             │                                               │
                             └───────────────────────┬───────────────────────┘
                                                     │
                                                     ▼
                                     ┌───────────────────────────────┐
                                     │   POST /oci-storage/weekly-sync│
                                     │  (Generación Activa Semanal)  │
                                     └───────────────┬───────────────┘
                                                     │
                                                     ├─────────────────────────────────────────┐
                                                     ▼                                         ▼
                                      ┌─────────────────────────────┐           ┌─────────────────────────────┐
                                      │      reportes/{semana}.json │           │ OCI Object Storage Bucket   │
                                      │       (Persistencia Local)  │           │   (communitylab-assets)     │
                                      └──────────────┬──────────────┘           └─────────────────────────────┘
                                                     │
                                                     ▼ (Lectura < 2 ms)
                                      ┌─────────────────────────────┐
                                      │  GET /oci-storage/reports   │
                                      │ (Caché en Memoria TTL 5 min)│
                                      └─────────────────────────────┘
```

### 1.2 Diagnóstico del Problema Previo
1. **Ausencia de Copys Reales en Reportes Semanales:**
   Anteriormente, el generador de reportes semanales (`_cargar_lote_consolidado_para_reporte`) obtenía los datos desde tablas provisionales (`lotes_ia_kpis`), desde el archivo estático `resultados_kpis.json` o desde la tabla `interacciones` de SQLite. Estos orígenes carecen de los copys aprobados y publicados por canal, recurriendo a marcadores de texto provisionales como `"Pendiente de redacción por Enoc..."`.
2. **Falta de Complemento de Descartados en Supabase:**
   La tabla `public.historial_reportes_semanales` en Supabase Enoc únicamente contiene registros que han sido efectivamente aprobados y publicados. Para que las métricas agregadas del reporte (`total_mensajes = total_aprobados + total_descartados`, distribución de sentimientos y temas) reflejen fielmente el universo completo de interacciones analizadas en la semana, los mensajes descartados (`estado_curaduria = 'discarded'` o `relevancia < 70`) deben extraerse de la base SQLite local (`communitylab.db`).
3. **Riesgo de Regresión de Latencia y Violación de la Regla de Oro en Lecturas:**
   El endpoint `GET /api/v1/oci-storage/reports` carecía de caché en memoria en proceso e intentaba sincronizar sincronamente desde el bucket OCI (`_sincronizar_reportes_desde_oci_bucket`), lo que arriesgaba degradar la latencia a cientos de milisegundos o segundos en caso de tráfico recurrente o conectividad WAN.
4. **Fragilidad de Formato en `reporte_semanal.py` (Subdiccionario `kpis`):**
   La función `reporte_semanal.generar_reporte_semanal` asume de forma estricta que cada elemento dentro de `aprobados` y `descartados` contiene un subdiccionario `item["kpis"]`. Si un registro de Supabase o SQLite no contiene dicha estructura normalizada, el sistema lanza una excepción fatal `KeyError`.

---

## 2. Decisiones de Diseño y Solución Técnica

### 2.1 Extracción Primaria desde Supabase Enoc (`historial_reportes_semanales`)
- **Consulta con Timeout Estricto (`connect_timeout <= 4`):**
  Durante la invocación activa de generación de reporte (`POST /api/v1/oci-storage/weekly-sync`), el sistema ejecuta una consulta SQL sobre `public.historial_reportes_semanales` en el clúster Supabase Enoc utilizando `psycopg`:
  ```sql
  SELECT id_mensaje, autor, semana, fecha_envio, fecha_extraccion,
         fecha_publicacion, rutas_activas, estado, contenido_original,
         copys_generados, cw_modelo_ia
  FROM public.historial_reportes_semanales
  WHERE semana = %(semana)s OR LOWER(semana) = LOWER(%(semana_lower)s) OR LOWER(semana) = LOWER(%(sufijo_semana)s)
  ORDER BY id ASC;
  ```
- **Deserialización Defensiva:**
  Los campos `contenido_original` y `copys_generados` son deserializados mediante una función auxiliar `_deserializar_json_defensivo` que soporta objetos nativos (`dict`, `list`), cadenas de texto JSON (`str`) o `None`, retornando un diccionario vacío ante cualquier irregularidad o fallo de parseo.
- **Normalización Obligatoria del Subdiccionario `kpis`:**
  Cada elemento aprobado se normaliza con:
  ```python
  "kpis": {
      "relevancia": int(kpis_origen.get("relevancia") or 0),
      "sentimiento": str(kpis_origen.get("sentimiento") or "Neutral"),
      "temas_clave": temas_normalizados,
      "segmento": str(kpis_origen.get("segmento") or "General"),
      "razonamiento": str(kpis_origen.get("razonamiento") or "")
  }
  ```
  Esto blinda al motor contra errores `KeyError` al calcular contadores en `reporte_semanal.py`.

### 2.2 Deduplicación y Prelación Determinista de Copys (LinkedIn > Discord > X)
- **Deduplicación por `id_mensaje`:**
  Si un mismo mensaje fue publicado en múltiples canales en momentos distintos (generando múltiples filas en Supabase), el sistema los agrupa bajo un único registro canónico:
  - Fusiona las listas `rutas_activas` eliminando duplicados preservando el orden.
  - Combina los diccionarios `copys_generados`.
  - Adopta la marca temporal más reciente como `fecha_publicacion`.
- **Inyección Determinista de `copy_final`:**
  Se evalúa la disponibilidad del copy publicado con la prelación estricta:
  1. Canal `'linkedin'` (si existe en `copys_generados` y tiene texto).
  2. Canal `'discord'` (si existe en `copys_generados` y tiene texto).
  3. Canal `'x'` (si existe en `copys_generados` y tiene texto).
  4. Respaldo: `texto_original` de `contenido_original`.
- **Formateo con Título:**
  - Si el objeto de canal posee un `titulo` no vacío: `f"{titulo}\n\n{texto_copy}".strip()`.
  - Si no posee título o es nulo/vacío: `texto_copy.strip()`.
  - Se erradican totalmente los textos marcadores como `"Pendiente de redacción por Enoc..."`.

### 2.3 Complementación de Descartados desde SQLite Local y Fallback Resiliente
- **Complemento de Descartados:**
  Para calcular las métricas de toda la comunidad en la semana solicitada, se extraen de la tabla `interacciones` de SQLite local los registros con `estado_curaduria = 'discarded'` o `relevancia < 70` cuya fecha o semana correspondan al período, excluyendo aquellos IDs que ya fueron clasificados como `aprobados`. Cada descartado cuenta igualmente con su subdiccionario `kpis` completo.
- **Estrategia de Fallback Transparente:**
  - Si la conexión a Supabase Enoc excede el timeout de 4 segundos o lanza un error de red/autenticación:
    1. Registra advertencia en log: `logger.warning(...)`.
    2. Conmuta defensivamente al fallback local de tres niveles: `lotes_ia_kpis` de Supabase/local -> `resultados_kpis.json` -> SQLite local `interacciones`.
    3. Si tras consultar todas las fuentes no hay mensajes para la semana: retorna un error controlado HTTP 400 (`ValueError: No hay mensajes analizados para el período indicado`), impidiendo categóricamente la emisión de errores HTTP 500.

### 2.4 Cumplimiento Estricto de la Regla de Oro (< 2 ms) y Caché en Memoria (< 10 ms)
- **Aislamiento Absoluto de Red en `GET /api/v1/oci-storage/reports`:**
  - Queda prohibida cualquier llamada síncrona WAN a Supabase o al cliente de OCI Object Storage dentro de este endpoint.
  - La descarga/sincronización de OCI (`_sincronizar_reportes_desde_oci_bucket`) se elimina de la ruta crítica de lectura y solo se activa en generación o segundo plano diferido.
- **Caché en Memoria en Proceso:**
  - Variables globales `_cache_reportes_oci: dict | None = None` y `_timestamp_cache_reportes_oci: float = 0.0` con `TTL_CACHE_REPORTES_OCI = 300.0` (5 minutos).
  - Si la caché es válida, responde en < 1 milisegundo.
  - Si expira o está vacía, lee los archivos locales `reportes/*.json`, actualiza la caché y responde en < 2 milisegundos.
- **Invalidación Atómica Inmediata:**
  - La función `invalidar_cache_reportes_oci()` se invoca de manera atómica ante:
    1. Publicación de canal individual (`POST /api/v1/mototradis/publish-channel` y `/content-workflow/publish-channel`).
    2. Aprobación o decisión HITL (`POST /api/v1/mototradis/hitl-decision`).
    3. Sincronización o generación semanal (`POST /api/v1/oci-storage/weekly-sync`).
    4. Mutaciones generales en `invalidar_cache_supabase()`.

### 2.5 Inviolabilidad Constitucional y Cero Secretos Quemados
- Cero alteraciones en los 17 archivos protegidos de la raíz (`base_datos.py`, `reporte_semanal.py`, `procesamiento.py`, `api.py`, `modelos.py`, etc.), ni en los directorios `backend/`, `motor-ia/` y `src/`.
- Toda la lógica se aloja en `puente_motor_ia.py` y las pruebas correspondientes en `tests/test_unificacion_motor_ia.py`.
- Todas las variables de acceso se leen de `os.environ` y `.env` (`SUPABASE_DB_URL`, `DATABASE_URL`, `OCI_BUCKET_NAME`, etc.).

---

## 3. Matriz de Requerimientos Funcionales vs Componentes

| Requerimiento Funcional | Componente / Función en `puente_motor_ia.py` | Mecanismo de Prueba en `tests/` |
| :--- | :--- | :--- |
| **RF-01**: Extracción Primaria desde `public.historial_reportes_semanales` en Supabase Enoc | `_extraer_historial_reportes_semanales_supabase` | `test_spec024_extraccion_supabase_enoc_connect_timeout` |
| **RF-02**: Inyección Determinista de Copys Reales y Prelación Multicanal | `_formatear_copy_final`, `_consolidar_registros_aprobados_historial` | `test_spec024_prelacion_copys_linkedin_discord_x` |
| **RF-03**: Compatibilidad con `reporte_semanal.py`, Normalización de KPIs y Métricas | `_cargar_lote_para_reporte_semanal`, `_sanitizar_item_reporte` | `test_spec024_compatibilidad_kpis_sin_key_error` |
| **RF-04**: Modo Offline OCI, Resiliencia y Códigos HTTP Controlados | `oci_weekly_sync_v1`, manejo de `ValueError` -> HTTP 400 | `test_spec024_resiliencia_fallback_y_http_400_controlado` |
| **RF-05**: Regla de Oro de Alta Velocidad (< 2 ms) y Caché en Memoria | `_cache_reportes_oci`, `invalidar_cache_reportes_oci`, `oci_reports_v1` | `test_spec024_cache_alta_velocidad_e_invalidacion_atomica` |
| **RF-06**: Inviolabilidad Constitucional y Cero Secretos Quemados | Conexión por variables de entorno y aislamiento en `puente_motor_ia.py` | `test_spec024_inviolabilidad_archivos_y_cero_secretos` |

---

## 4. Estrategia de Implementación TDD Estricta (Red -> Green -> Refactor)

1. **Fase Red (T1):**
   - Diseñar y escribir un conjunto exhaustivo de pruebas en `tests/test_unificacion_motor_ia.py` que definan y exijan los comportamientos de la Spec 024.
   - Ejecutar pytest para verificar que fallen inequívocamente por ausencia de las funciones y cambios requeridos.
2. **Fase Green (T2 a T6):**
   - **T2:** Implementar la extracción segura y deserialización de `public.historial_reportes_semanales` en Supabase Enoc con timeout <= 4s.
   - **T3:** Implementar la deduplicación de publicaciones y la función de prelación multicanal (`linkedin` > `discord` > `x`) con formateo de título y eliminación de placeholders.
   - **T4:** Implementar la complementación de mensajes descartados desde SQLite local (`communitylab.db`) y la cascada de fallbacks.
   - **T5:** Implementar la caché en memoria en proceso (< 2 ms) para `GET /api/v1/oci-storage/reports`, eliminando llamadas bloqueantes e integrando la invalidación atómica en todas las mutaciones.
   - **T6:** Integrar el ensamblado completo en `POST /api/v1/oci-storage/weekly-sync` garantizando códigos semánticos (HTTP 200 con `status: "saved_locally"` o `"synced"`, y HTTP 400 controlado si no hay datos).
3. **Fase Refactor y Certificación (T7):**
   - Ejecutar la suite completa de pruebas del proyecto asegurando 100% verde (115+ tests pasando).
   - Medir latencia de respuesta en endpoints GET asegurando < 2 ms.
   - Ejecutar auditoría git para certificar que ningún archivo protegido fuera de `puente_motor_ia.py` y `tests/` fue tocado.
