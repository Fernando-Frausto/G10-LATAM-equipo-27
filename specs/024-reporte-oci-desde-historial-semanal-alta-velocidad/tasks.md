# Tareas de Implementación — Spec 024: Generación de Reportes OCI desde Historial Semanal con Inyección de Copys Reales y Alta Velocidad

## [x] T1: Fase Red TDD en `tests/test_unificacion_motor_ia.py` (~20 min)
- **Rol:** `@implementer`
- **Archivos involucrados:**
  - `tests/test_unificacion_motor_ia.py`
- **Requerimientos Funcionales:** `RF-01`, `RF-02`, `RF-03`, `RF-04`, `RF-05`, `RF-06`
- **Descripción:**
  1. Diseñar e implementar pruebas unitarias y de integración exhaustivas en `tests/test_unificacion_motor_ia.py` para la Spec 024:
     - **Extracción desde Supabase Enoc:** `test_spec024_extraccion_historial_reportes_supabase_timeout_y_kpis` simulando conexión con `connect_timeout <= 4`, deserialización defensiva de `contenido_original` (sea string JSON o dict) y presencia obligatoria del subdiccionario `kpis` (`relevancia`, `sentimiento`, `temas_clave`, `segmento`, `razonamiento`).
     - **Prelación Determinista de Copys y Formateo:** `test_spec024_prelacion_copys_formateo_y_erradicacion_placeholders` validando el orden estricto LinkedIn > Discord > X, formateo con/sin título (`f"{titulo}\n\n{texto_copy}".strip()`), respaldo con texto original y ausencia absoluta del marcador `"Pendiente de redacción por Enoc..."`.
     - **Deduplicación por Mensaje:** `test_spec024_deduplicacion_publicaciones_multiples` verificando que publicaciones independientes de un mismo `id_mensaje` se agrupen consolidando `rutas_activas`, combinando `copys_generados` y tomando la `fecha_publicacion` más reciente.
     - **Complementación de Descartados:** `test_spec024_complemento_descartados_desde_sqlite` verificando que los mensajes con `estado_curaduria = 'discarded'` o `relevancia < 70` de SQLite local se integren en `descartados`, garantizando que `resumen_metricas.total_mensajes` refleje `aprobados + descartados` sin errores `KeyError`.
     - **Caché de Alta Velocidad (< 2 ms) e Invalidación Atómica:** `test_spec024_cache_alta_velocidad_get_reports_e_invalidacion_atomica` verificando que `GET /api/v1/oci-storage/reports` se resuelva desde la caché en memoria en < 2 ms sin llamadas de red WAN, y que la caché se invalide inmediatamente tras una publicación, decisión HITL o sync.
     - **Resiliencia y Códigos HTTP Semánticos:** `test_spec024_resiliencia_fallback_y_http_400_controlado` verificando conmutación a fallback local ante caída o timeout de Supabase Enoc, y retorno de HTTP 400 controlado (`ValueError`) si ninguna fuente contiene mensajes para la semana (cero HTTP 500).
     - **Modo Offline OCI:** `test_spec024_modo_offline_oci_y_status_saved_locally` verificando guardado en `reportes/{semana}.json` y respuesta HTTP 200 con `subido_oci=False` y `status="saved_locally"`.
  2. Ejecutar las pruebas y verificar que fallen en la fase roja por falta de implementación en `puente_motor_ia.py`.
- **Criterio de verificación:**
  ```powershell
  pytest tests/test_unificacion_motor_ia.py -k "spec024" -v
  ```
- **Hecho cuando:** Todas las pruebas de la Spec 024 están codificadas y fallan inequívocamente en la fase Red con `AssertionError` o `AttributeError` esperado.

---

## [x] T2: Extracción y Deserialización Defensiva desde `historial_reportes_semanales` en Supabase Enoc (~20 min)
- **Rol:** `@implementer`
- **Archivos involucrados:**
  - `puente_motor_ia.py`
- **Requerimientos Funcionales:** `RF-01`, `RF-03`, `RF-04`, `RF-06`
- **Descripción:**
  1. Implementar la función auxiliar `_deserializar_json_defensivo(valor: Any) -> Any` en `puente_motor_ia.py` para parsear de manera segura objetos `dict`, `list`, cadenas JSON o retornar `{}` ante entradas nulas o inválidas.
  2. Implementar la función `_extraer_historial_reportes_semanales_supabase(semana_objetivo: str) -> list[dict]`:
     - Resolver la URL de Supabase Enoc (`SUPABASE_DB_URL` o `DATABASE_URL`).
     - Conectar a la base de datos utilizando `psycopg.connect(url, connect_timeout=4)`.
     - Consultar `public.historial_reportes_semanales` filtrando por semana (soporte para formato `AAAA-semana-NN` y sufijos de semana como `Semana_NN`).
     - Deserializar defensivamente `contenido_original` y `copys_generados`.
     - Construir el subdiccionario normalizado `kpis` asegurando que contenga explícitamente `relevancia` (int), `sentimiento` (str), `temas_clave` (list o str), `segmento` (str) y `razonamiento` (str).
     - Asegurar que `id_mensaje` sea siempre `str`.
     - Capturar cualquier excepción de conexión o timeout con `logger.warning` y retornar lista vacía `[]` de forma defensiva para activar el fallback.
- **Criterio de verificación:**
  ```powershell
  pytest tests/test_unificacion_motor_ia.py -k "test_spec024_extraccion_historial_reportes_supabase_timeout_y_kpis" -v
  ```
- **Hecho cuando:** La prueba pasa en verde (Green), confirmando la extracción con timeout <= 4s, mapeo estricto de `kpis` y manejo defensivo de errores de red.

---

## [x] T3: Deduplicación por Mensaje, Prelación Determinista de Copys y Erradicación de Placeholders (~20 min)
- **Rol:** `@implementer`
- **Archivos involucrados:**
  - `puente_motor_ia.py`
- **Requerimientos Funcionales:** `RF-02`, `RF-06`
- **Descripción:**
  1. Implementar la función `_formatear_copy_final(copys_generados: dict, texto_original: str = "") -> str`:
     - Evaluar la prelación estricta por canal: 1) `'linkedin'`, 2) `'discord'`, 3) `'x'`.
     - Extraer el texto del copy del canal seleccionado (soportando dict con claves `texto_copy`, `contenido`, `texto` o string directo).
     - Extraer el `titulo` si está presente.
     - Si hay título: retornar `f"{titulo.strip()}\n\n{texto_copy.strip()}".strip()`.
     - Si no hay título: retornar `texto_copy.strip()`.
     - Si ningún canal contiene un copy válido: utilizar como respaldo `texto_original.strip()`.
     - Prohibir categóricamente cualquier texto provisional como `"Pendiente de redacción por Enoc..."`.
  2. Implementar la función `_consolidar_aprobados_historial(registros_crudos: list[dict]) -> list[dict]`:
     - Agrupar registros por `id_mensaje`.
     - Si un mensaje posee múltiples filas por despachos independientes: fusionar `rutas_activas` (lista única ordenada), combinar `copys_generados` y adoptar la `fecha_publicacion` más reciente.
     - Inyectar el campo `copy_final` calculado según la prelación y preservar el diccionario multicanal completo en `copys_generados`.
     - Sanitizar cada item con `_sanitizar_item_reporte`.
- **Criterio de verificación:**
  ```powershell
  pytest tests/test_unificacion_motor_ia.py -k "test_spec024_prelacion_copys or test_spec024_deduplicacion" -v
  ```
- **Hecho cuando:** Las pruebas de prelación multicanal y deduplicación pasan en verde (Green), validando la inyección exacta de copys reales y erradicación total de placeholders.

---

## [x] T4: Complementación de Mensajes Descartados desde SQLite Local y Fallback Integral (~20 min)
- **Rol:** `@implementer`
- **Archivos involucrados:**
  - `puente_motor_ia.py`
- **Requerimientos Funcionales:** `RF-01`, `RF-03`, `RF-04`, `RF-06`
- **Descripción:**
  1. Implementar la función `_obtener_descartados_semana_sqlite(semana_objetivo: str, ids_aprobados: set) -> list[dict]`:
     - Conectar a la base SQLite local (`communitylab.db`).
     - Consultar filas de `interacciones` donde `estado_curaduria = 'discarded'` o `(estado_curaduria != 'curated' AND relevancia < 70)`.
     - Filtrar por la semana objetivo (verificando `periodo_referencia`, `semana` o fecha de envío ISO).
     - Excluir registros cuyo `id` ya esté presente en `ids_aprobados`.
     - Construir para cada descarte su estructura canónica con el subdiccionario `kpis` normalizado mediante `_sanitizar_item_reporte`.
  2. Implementar la función orquestadora `_cargar_lote_para_reporte_semanal(semana_objetivo: str) -> dict`:
     - Consultar `_extraer_historial_reportes_semanales_supabase(semana_objetivo)`.
     - Si existen aprobados en Supabase Enoc:
       - Consolidar con `_consolidar_aprobados_historial`.
       - Obtener descartados de SQLite local vía `_obtener_descartados_semana_sqlite` excluyendo los IDs aprobados.
       - Retornar `{"aprobados": aprobados, "descartados": descartados}`.
     - Si Supabase Enoc falla o está vacío:
       - Conmutar de forma transparente al fallback local `_cargar_lote_consolidado_para_reporte()` filtrando por semana mediante `_construir_paquete_para_semana`.
     - Si tras agotar todas las fuentes no hay mensajes para la semana: retornar `{"aprobados": [], "descartados": []}`.
- **Criterio de verificación:**
  ```powershell
  pytest tests/test_unificacion_motor_ia.py -k "test_spec024_complemento_descartados" -v
  ```
- **Hecho cuando:** Las pruebas pasan en verde (Green), confirmando que el lote empaqueta tanto aprobados reales como descartados de SQLite para el cómputo integral de métricas sin `KeyError`.

---

## [x] T5: Caché en Memoria (< 2 ms), Aislamiento WAN de GET /reports e Invalidación Atómica (~20 min)
- **Rol:** `@implementer`
- **Archivos involucrados:**
  - `puente_motor_ia.py`
- **Requerimientos Funcionales:** `RF-01`, `RF-05`, `RF-06`
- **Descripción:**
  1. Definir en `puente_motor_ia.py` las variables globales de caché:
     - `_cache_reportes_oci: dict | None = None`
     - `_timestamp_cache_reportes_oci: float = 0.0`
     - `TTL_CACHE_REPORTES_OCI: float = 300.0` (5 minutos).
  2. Implementar la función `invalidar_cache_reportes_oci()`:
     - Reinicia `_cache_reportes_oci = None` y `_timestamp_cache_reportes_oci = 0.0`.
  3. Modificar el endpoint `GET /api/v1/oci-storage/reports`:
     - Si la caché en memoria es válida (`time.time() - _timestamp < 300.0`), retornar de inmediato (< 1 ms).
     - Si es caché miss o expiró: leer estrictamente los archivos locales `reportes/*.json`.
     - Eliminar la llamada síncrona bloqueante `_sincronizar_reportes_desde_oci_bucket` del flujo de lectura GET.
     - Almacenar la lista en `_cache_reportes_oci`, actualizar timestamp y responder (< 2 ms).
  4. Integrar `invalidar_cache_reportes_oci()` de manera atómica e inmediata en:
     - `invalidar_cache_supabase()` (mutaciones generales del sistema).
     - `POST /api/v1/mototradis/publish-channel` y `/api/v1/content-workflow/publish-channel`.
     - `POST /api/v1/mototradis/hitl-decision`.
     - `POST /api/v1/oci-storage/weekly-sync`.
- **Criterio de verificación:**
  ```powershell
  pytest tests/test_unificacion_motor_ia.py -k "test_spec024_cache_alta_velocidad" -v
  ```
- **Hecho cuando:** La prueba pasa en verde (Green), certificando lectura < 2 ms, cero llamadas de red en GET e invalidación atómica inmediata ante cualquier mutación.

---

## [x] T6: Integración del Endpoint POST /weekly-sync, Manejo Offline OCI y Códigos HTTP Semánticos (~20 min)
- **Rol:** `@implementer`
- **Archivos involucrados:**
  - `puente_motor_ia.py`
- **Requerimientos Funcionales:** `RF-01`, `RF-02`, `RF-03`, `RF-04`, `RF-06`
- **Descripción:**
  1. Actualizar la función `oci_weekly_sync_v1` en `puente_motor_ia.py`:
     - Obtener el lote consolidado mediante `_cargar_lote_para_reporte_semanal(semana_nombre)`.
     - Si el paquete resultante carece de aprobados y de descartados:
       - Lanzar `HTTPException(status_code=400, detail="No hay mensajes analizados para el período indicado.")` para evitar categóricamente errores HTTP 500.
     - Delegar la generación del reporte a `reporte_semanal.generar_reporte_semanal(semana_nombre, paquete)`.
     - Asegurar la persistencia local obligatoria del archivo en `reportes/{semana_nombre}.json`.
     - Evaluar el resultado de subida a OCI:
       - Si subió con éxito: retornar HTTP 200 con `subido_oci: True`, `status: "synced"`.
       - Si no hay credenciales OCI o falló: retornar HTTP 200 con `subido_oci: False`, `status: "saved_locally"` y mensaje descriptivo.
     - Disparar de forma atómica `invalidar_cache_reportes_oci()`.
- **Criterio de verificación:**
  ```powershell
  pytest tests/test_unificacion_motor_ia.py -k "test_spec024_resiliencia or test_spec024_modo_offline" -v
  ```
- **Hecho cuando:** Las pruebas de sincronización semanal pasan en verde (Green), generando reportes con copys reales inyectados, respuesta HTTP 200 con códigos semánticos y HTTP 400 controlado si la semana está vacía.

---

## [x] T7: Fase Refactor, Verificación Global de Regresión y Certificación de Inviolabilidad (~20 min)
- **Rol:** `@implementer`
- **Archivos involucrados:**
  - `puente_motor_ia.py`
  - `tests/test_unificacion_motor_ia.py`
- **Requerimientos Funcionales:** `RF-01`, `RF-02`, `RF-03`, `RF-04`, `RF-05`, `RF-06`
- **Descripción:**
  1. Revisar y pulir la implementación en `puente_motor_ia.py`: eliminar código muerto, asegurar tipado defensivo y documentación clara de funciones.
  2. Ejecutar la suite completa de pruebas unitarias y de integración del proyecto (115+ tests) verificando 100% de éxito sin ninguna regresión.
  3. Comprobar la latencia de respuesta en endpoints GET asegurando cumplimiento de la Regla de Oro (< 2 ms).
  4. Auditar mediante `git status` y scripts de verificación que ninguno de los 17 archivos protegidos de la raíz (`base_datos.py`, `reporte_semanal.py`, `procesamiento.py`, `api.py`, `modelos.py`, etc.), ni las carpetas `backend/`, `motor-ia/` ni `src/` hayan sido alterados en ningún byte.
- **Criterio de verificación:**
  ```powershell
  pytest tests/
  git status --porcelain
  ```
- **Hecho cuando:** Todos los tests pasan en verde (100%), 0 regresiones detectadas, latencia < 2 ms confirmada y 0 archivos protegidos modificados.
