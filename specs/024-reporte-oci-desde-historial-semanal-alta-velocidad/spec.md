# Especificación 024: Generación de Reportes OCI desde Historial Semanal con Inyección de Copys Reales y Alta Velocidad

## 1. Contexto y Propósito (El POR QUÉ)

### 1.1 Contexto y Necesidad del Negocio
En la plataforma CloudEdTech / CommunityLab, el generador de reportes semanales tiene como objetivo consolidar las interacciones analizadas durante un ciclo semanal, calcular las métricas agregadas de la comunidad (sentimiento, temas en tendencia, segmentos de audiencia y balances de curaduría) y empaquetar un archivo de distribución JSON para ser almacenado localmente y en el bucket de Oracle Cloud Infrastructure (OCI) Object Storage (`communitylab-assets`).

Actualmente:
1. El generador del reporte semanal (`_cargar_lote_consolidado_para_reporte` y `reporte_semanal.py`) recurre a tablas provisionales (`lotes_ia_kpis`), al archivo estático `resultados_kpis.json` o a la tabla de interacciones locales en SQLite. Estos orígenes contienen únicamente el texto original y las calificaciones de IA, pero **carecen de los copys reales aprobados y publicados** por el equipo editorial, inyectando marcadores provisionales tales como `"Pendiente de redacción por Enoc..."`.
2. A partir de la Especificación 023, cada vez que un operador humano publica un canal o aprueba un lote Human-in-the-Loop (HITL) en la Mesa de Redacción (`ContentStudio`), el sistema replica de manera desacoplada un registro canónico y autosuficiente en la tabla `public.historial_reportes_semanales` de la base de datos de Supabase de Enoc (`swdoucawdasxmnomlcfu`).
3. Cada registro de `public.historial_reportes_semanales` es **autosuficiente para los mensajes publicados**:
   - La columna `contenido_original` alberga el autor, canal de origen, texto original del mensaje y los KPIs analizados (`relevancia`, `sentimiento`, `temas_clave`, `segmento`, `razonamiento`), serializado como JSON o dict.
   - La columna `copys_generados` contiene los copys reales aprobados por el humano y efectivamente publicados para cada red social (`linkedin`, `discord`, `x`).
4. No obstante, `public.historial_reportes_semanales` solo registra mensajes que culminaron en publicación (mensajes aprobados). Para que las métricas agregadas del reporte (`total_mensajes = total_aprobados + total_descartados`) reflejen el universo completo de mensajes analizados en la comunidad, los mensajes descartados de la semana deben complementarse desde la base local SQLite (`communitylab.db`: mensajes con `estado_curaduria = 'discarded'` o `relevancia < 70`) o fuentes secundarias (`lotes_ia_kpis`).

### 1.2 Diagnóstico Técnico y Regla de Oro de Alta Velocidad
- **Aislamiento Estricto de Endpoints GET (< 2 ms):**
  Para cumplir con la Regla de Oro de Rendimiento establecida en `AGENTS.md` ("NUNCA realizar llamadas de red externas bloqueantes dentro de endpoints de lectura GET"), la consulta WAN remota a Supabase `historial_reportes_semanales` se ejecuta **EXCLUSIVAMENTE** durante la generación o sincronización activa disparada por el usuario (`POST /api/v1/oci-storage/weekly-sync`). El endpoint de lectura `GET /api/v1/oci-storage/reports` se resuelve estrictamente desde la caché en memoria y el disco local (`reportes/*.json`) con una latencia inferior a **2 milisegundos** (< 2 ms), prohibiendo cualquier llamada de red WAN bloqueante en lecturas.
- **Estrategia de Caché en Memoria con TTL (>= 5 min) e Invalidación Atómica:**
  Las consultas recurrentes de reportes se benefician de una caché en memoria en proceso con tiempo de expiración (TTL >= 5 minutos / 300 segundos). Esta caché se invalida de manera atómica e inmediata ante cualquier nueva publicación individual de canal, aprobación HITL en la Mesa de Redacción o generación de un nuevo reporte semanal.
- **Compatibilidad Estricta con `reporte_semanal.py` (Subdiccionario `kpis`):**
  El módulo central `reporte_semanal.py` accede directamente a `item["kpis"]` para calcular las métricas agregadas (`Counter(i["kpis"].get("sentimiento", ...) for i in todos)`). Si un item carece de dicha estructura, se produce un error crítico `KeyError`. Por ello, la extracción debe deserializar defensivamente `contenido_original` (sea string JSON o dict) y mapear explícitamente el subdiccionario `item["kpis"]` normalizado antes de delegar el procesamiento a `reporte_semanal.py`.
- **Modo Offline OCI y Códigos HTTP Semánticos:**
  En entornos locales de desarrollo, pruebas o ausencia de credenciales OCI (`OCI_USER_OCID`, etc.), el sistema debe persistir el reporte en `reportes/{semana}.json` y responder exitosamente con HTTP 200 (`subido_oci: False`, `status: 'saved_locally'`). Si se solicita una semana para la cual no existe ningún registro analizado en ninguna fuente, el sistema debe responder con un error de negocio controlado HTTP 400 (`ValueError`), evitando categóricamente excepciones no controladas o errores HTTP 500. El timeout de conexión hacia Supabase se fija en un máximo estricto de 4 segundos.

### 1.3 Inviolabilidad Constitucional y Cero Secretos Quemados
- **Inviolabilidad de los 17 Archivos Protegidos:**
  La Constitución del Proyecto y `AGENTS.md` prohíben modificar los 17 archivos protegidos de la raíz (incluyendo `reporte_semanal.py`, `base_datos.py`, `api.py`, `procesamiento.py`), así como los directorios `backend/`, `motor-ia/` y `src/`.
  Toda la lógica de extracción desde Supabase, normalización de KPIs, orden de prelación de copys, complemento de descartados desde SQLite, caché en memoria y resiliencia para OCI se ubica exclusivamente en `puente_motor_ia.py` y sus tests asociados en `tests/`.
- **Seguridad de Secretos (Regla 4):**
  Ninguna credencial de OCI, Supabase o base de datos puede quemarse en código duro. Todo se resuelve dinámicamente mediante variables de entorno (`SUPABASE_DB_URL`, `DATABASE_URL`, `OCI_*`) a través de `os.environ` y `.env`.

---

## 2. Requerimientos Funcionales (El QUÉ — Formato EARS)

### RF-01: Extracción Primaria desde `public.historial_reportes_semanales` en Supabase Enoc (Generación Activa)
- **CUANDO** se solicite la generación o sincronización activa de un reporte semanal para OCI mediante `POST /api/v1/oci-storage/weekly-sync`, **EL SISTEMA DEBERÁ** consultar de manera primaria la tabla `public.historial_reportes_semanales` en la base de datos de Supabase de Enoc (`swdoucawdasxmnomlcfu`) filtrando los registros correspondientes a la semana solicitada con un timeout de conexión no mayor a 4 segundos (`connect_timeout <= 4`).
- **MIENTRAS** se procese cada fila obtenida de `historial_reportes_semanales`, **EL SISTEMA DEBERÁ** deserializar defensivamente el campo `contenido_original` (si se encuentra almacenado como cadena JSON o como diccionario) y estructurar explícitamente en el registro resultante:
  - `id_mensaje`: Identificador normalizado como cadena de texto (`str`).
  - `autor`: Nombre o identificador del autor comunitario.
  - `canal_origen`: Canal de procedencia del mensaje original.
  - `semana`: Etiqueta de la semana o período de referencia (ej. `2026-semana-42`).
  - `fecha_envio`: Marca temporal de emisión del mensaje original (o fecha de extracción si no está disponible).
  - `fecha_publicacion`: Marca temporal en que el contenido fue efectivamente publicado.
  - `rutas_activas`: Arreglo de canales despachados exitosamente (ej. `['discord', 'linkedin']`).
  - `texto_original`: Texto extraído del `contenido_original`.
  - `kpis`: Subdiccionario normalizado obligatorio que contenga explícitamente `relevancia` (`int`), `sentimiento` (`str`), `temas_clave` (`list` o `str`), `segmento` (`str`) y `razonamiento` (`str`), garantizando que ninguna invocación a `reporte_semanal.py` sufra fallos por `KeyError`.
  - `copys_generados`: Diccionario estructurado multicanal preservado con los copys aprobados (`{"linkedin": {...}, "discord": {...}, "x": {...}}`).
- **CUANDO** se recopilen los registros aprobados de `historial_reportes_semanales`, **EL SISTEMA DEBERÁ** complementar el universo de la semana extrayendo los registros "descartados" desde la base de datos SQLite local (`communitylab.db`: mensajes con `estado_curaduria = 'discarded'` o `relevancia < 70` pertenecientes al período) o alternativamente desde `lotes_ia_kpis`, estructurando igualmente en cada elemento descartado su correspondiente subdiccionario `kpis`.
- **EN TODO MOMENTO**, las consultas de lectura de reportes semanales a través de `GET /api/v1/oci-storage/reports` **NO DEBERÁN** realizar ninguna llamada de red WAN a Supabase ni a OCI, resolviéndose con exclusividad desde la memoria caché y los archivos locales (`reportes/*.json`).

---

### RF-02: Inyección Determinista de Copys Reales y Prelación Multicanal
- **CUANDO** se ensamble la lista de activos aprobados (`activos_copywriting.aprobados`) para el reporte a partir de `historial_reportes_semanales`, **EL SISTEMA DEBERÁ** inyectar el texto del copy real publicado en el campo `copy_final` siguiendo un orden determinista y estricto de prelación por canal:
  1. Canal `'linkedin'` (si existe en `copys_generados` y contiene texto de copy).
  2. Canal `'discord'` (si existe en `copys_generados` y contiene texto de copy).
  3. Canal `'x'` (si existe en `copys_generados` y contiene texto de copy).
- **MIENTRAS** se formatee la propiedad `copy_final` a partir del canal seleccionado según la prelación, **EL SISTEMA DEBERÁ** aplicar el siguiente formato:
  - Si el objeto del canal contiene un `titulo` no vacío: `f"{titulo}\n\n{texto_copy}".strip()`
  - Si no existe `titulo` o es nulo/vacío: `texto_copy.strip()`
  - Si ningún canal en `copys_generados` provee un texto de copy válido: utilizar como respaldo el texto original del mensaje (`contenido_original["texto"]`).
- **EN TODO MOMENTO**, **EL SISTEMA DEBERÁ** preservar el diccionario completo multicanal en la propiedad `copys_generados` de cada elemento aprobado.
- **EN TODO MOMENTO**, **EL SISTEMA DEBERÁ** prohibir la inyección de marcadores provisionales tales como `"Pendiente de redacción por Enoc..."` en cualquier elemento originado en `historial_reportes_semanales`.
- **DONDE** un mismo `id_mensaje` presente múltiples registros en `historial_reportes_semanales` por publicaciones independientes, **EL SISTEMA DEBERÁ** agrupar los canales despachados en `rutas_activas`, unificar los copys en `copys_generados` y adoptar la marca temporal de publicación más reciente como `fecha_publicacion`.

---

### RF-03: Compatibilidad con `reporte_semanal.py`, Cálculo de Métricas y Empaquetado
- **CUANDO** se invoque la función `reporte_semanal.generar_reporte_semanal(semana_nombre, paquete)`, **EL SISTEMA DEBERÁ** proveer un diccionario `paquete` compuesto por:
  - `aprobados`: Lista de mensajes publicados provenientes de `historial_reportes_semanales` (o fuentes secundarias en fallback).
  - `descartados`: Lista de mensajes no publicados de la semana provenientes de SQLite (`communitylab.db`) o `lotes_ia_kpis`.
- **EN TODO MOMENTO**, cada elemento dentro de `aprobados` y `descartados` **DEBERÁ** contener obligatoriamente el subdiccionario `kpis` con las claves `"sentimiento"`, `"temas_clave"`, `"segmento"` y `"relevancia"`, evitando excepciones `KeyError` durante el cómputo de métricas en `reporte_semanal.py`.
- **CUANDO** se genere el reporte semanal, **EL SISTEMA DEBERÁ** asegurar que `resumen_metricas` refleje el universo completo del período:
  - `total_mensajes`: Conteo total de interacciones analizadas (`len(aprobados) + len(descartados)`).
  - `total_aprobados`: Cantidad de mensajes con copys aprobados y publicados.
  - `total_descartados`: Cantidad de mensajes descartados durante la curaduría o con relevancia inferior a 70.
  - `sentimiento`: Frecuencia agregada por valor de sentimiento.
  - `temas_tendencia`: Los 5 temas o hashtags más recurrentes con sus menciones.
  - `segmentos`: Conteo de interacciones agrupadas por segmento de audiencia.
- **MIENTRAS** se ensamble el objeto final, **EL SISTEMA DEBERÁ** incluir en la sección `metadata`:
  - `proyecto`: `"CommunityLab"`.
  - `semana`: Etiqueta normalizada en formato canónico `AAAA-semana-NN` (ej. `2026-semana-42`).
  - `version_esquema`: `"1.0"`.
  - `generado_en`: Marca temporal ISO UTC actual.
  - `oci_storage`: Objeto con `bucket`, `ruta` y el indicador booleano `subido`.

---

### RF-04: Modo Offline OCI, Resiliencia y Manejo de Códigos HTTP
- **CUANDO** se ejecute la generación semanal mediante `POST /api/v1/oci-storage/weekly-sync`:
  - **EL SISTEMA DEBERÁ** persistir de forma obligatoria el archivo local en el disco del servidor bajo la ruta `reportes/{semana}.json`.
  - **SI** OCI Object Storage está configurado con credenciales válidas y el archivo se sube exitosamente al bucket, **EL SISTEMA DEBERÁ** responder con HTTP 200 conteniendo `subido_oci: True`, `status: "synced"` y los metadatos correspondientes.
  - **SI** OCI Object Storage carece de credenciales configuradas en el entorno (`OCI_USER_OCID`, etc.) o el entorno es local/offline, **EL SISTEMA DEBERÁ** responder con HTTP 200 conteniendo `subido_oci: False`, `status: "saved_locally"` y un mensaje informativo indicando que el reporte fue generado y almacenado localmente.
- **SI** se produce un timeout de red WAN (> 4 segundos), indisponibilidad o fallo de autenticación en la conexión hacia Supabase Enoc:
  1. **EL SISTEMA DEBERÁ** registrar una advertencia estructurada (`logger.warning`).
  2. **EL SISTEMA DEBERÁ** activar un mecanismo de fallback automático consultando las fuentes secundarias locales (`lotes_ia_kpis` o SQLite local `communitylab.db`).
- **SI** tras agotar las fuentes (Supabase Enoc, `lotes_ia_kpis` y SQLite local) no existe ninguna interacción analizada para la semana indicada:
  - **EL SISTEMA DEBERÁ** retornar un código de error controlado HTTP 400 (`ValueError` con detalle explicativo indicando que no hay mensajes analizados en el período), impidiendo categóricamente la emisión de errores HTTP 500.

---

### RF-05: Garantía de Alta Velocidad (Regla de Oro), Endpoint GET (< 2 ms) y Caché en Memoria (< 10 ms)
- **EN TODO MOMENTO**, el endpoint de lectura `GET /api/v1/oci-storage/reports` **DEBERÁ** responder estrictamente en menos de **2 milisegundos** (< 2 ms) leyendo con exclusividad de la memoria caché en proceso y de los archivos locales preexistentes en `reportes/*.json`. Queda estrictamente prohibida cualquier llamada WAN bloqueante en este endpoint.
- **EN TODO MOMENTO**, las consultas recurrentes de reportes semanales por etiqueta ya generada **DEBERÁN** servirse desde la memoria caché con un TTL >= 5 minutos (300 segundos), alcanzando latencias de respuesta inferiores a **10 milisegundos** (< 10 ms).
- **CUANDO** se produzca una nueva publicación por canal individual, una decisión HITL en la Mesa de Redacción (`/api/v1/mototradis/publish-channel`, `/api/v1/content-workflow/publish-channel`, `/api/v1/mototradis/hitl-decision`) o una generación de reporte semanal (`/api/v1/oci-storage/weekly-sync`), **EL SISTEMA DEBERÁ** invalidar de forma atómica e inmediata la memoria caché de reportes OCI.
- **EN TODO MOMENTO**, las consultas cotidianas de los paneles de Dashboard, Ingesta de Mensajes y Pestaña de Análisis **DEBERÁN** continuar sirviéndose de forma exclusiva desde SQLite local (`communitylab.db`), preservando tiempos de respuesta ultrarrápidos inferiores a **2 milisegundos** (< 2 ms).

---

### RF-06: Inviolabilidad Constitucional y Cero Secretos Quemados
- **EN TODO MOMENTO**, los 17 archivos protegidos de la raíz (`base_datos.py`, `reporte_semanal.py`, `procesamiento.py`, `api.py`, `modelos.py`, etc.), así como las carpetas `backend/`, `motor-ia/` y `src/`, **DEBERÁN** permanecer estrictamente inalterados.
- **EN TODO MOMENTO**, cualquier función de extracción desde Supabase Enoc, agregación de descartados desde SQLite, mapeo de `kpis`, prelación de copys y gestión de caché para OCI **DEBERÁ** residir exclusivamente dentro de `puente_motor_ia.py` y sus pruebas asociadas en `tests/`.
- **EN TODO MOMENTO**, todas las credenciales de acceso, URLs de Supabase y parámetros de OCI Storage **DEBERÁN** consumirse exclusivamente a través de variables de entorno (`SUPABASE_DB_URL`, `DATABASE_URL`, `OCI_BUCKET_NAME`, `OCI_USER_OCID`, etc.) mediante `os.environ` y `.env`, quedando estrictamente prohibida la inclusión de tokens o claves en código duro.

---

## 3. Casos Límite y Manejo de Errores

### 3.1 Semana sin Registros Históricos en Supabase Enoc
- **SI** un usuario solicita generar el reporte de una semana (ej. `2026-semana-42`) en la que aún no se han aprobado ni publicado mensajes en `public.historial_reportes_semanales`:
  1. El sistema detecta que el conjunto de datos de Supabase está vacío.
  2. El sistema conmuta defensivamente a fuentes secundarias: `lotes_ia_kpis` o SQLite local (`communitylab.db`).
  3. Si existen interacciones analizadas en SQLite para dicho período, el reporte se genera con éxito y se responde HTTP 200.
  4. Si no existe ningún mensaje analizado en ninguna fuente para el período, el sistema devuelve un error controlado HTTP 400 (`ValueError: No hay mensajes analizados para el período indicado`) y **nunca un error HTTP 500**.

### 3.2 Indisponibilidad o Latencia Degradada de Red WAN hacia Supabase Enoc
- **SI** la conexión remota a Supabase Enoc sufre de desconexión abrupta, latencia degradada (> 4 segundos de timeout) o credenciales expiradas durante la lectura de `historial_reportes_semanales`:
  1. El sistema captura la excepción (`psycopg.Error` o `Exception`) mediante un bloque defensivo.
  2. Registra el evento en logs con nivel de advertencia estructurada (`logger.warning("Fallo o timeout al consultar historial_reportes_semanales en Supabase Enoc: ...")`).
  3. Conmuta inmediatamente al fallback local sin abortar el flujo y sin emitir HTTP 500.

### 3.3 Modo Offline OCI y Ausencia de Credenciales OCI
- **SI** el entorno carece de configuración OCI (ej. `~/.oci/config` no existe, `OCI_USER_OCID` no definido o red aislada):
  1. `reporte_semanal.py` intenta subir el paquete; al fallar o detectar falta de configuración, retorna `False` o `None`.
  2. El sistema almacena el reporte en disco local bajo `reportes/{semana}.json`.
  3. El endpoint `POST /api/v1/oci-storage/weekly-sync` retorna HTTP 200 con `status: "saved_locally"`, `subido_oci: False` y mensaje `"Reporte generado y guardado localmente."`.

### 3.4 Deserialización Defensiva de `contenido_original` y `copys_generados`
- **SI** en la base de datos de Supabase `contenido_original` o `copys_generados` fueron persistidos como cadenas de texto JSON en lugar de objetos nativos:
  1. El sistema aplica un deserializador defensivo con `json.loads` si el valor es de tipo `str`.
  2. Si ocurre un error de parseo o el contenido es nulo, el sistema inyecta un diccionario vacío por defecto.
  3. Se garantiza la existencia y estructura del subdiccionario `kpis` con tipos de datos nativos para evitar fallos en `reporte_semanal.py`.

### 3.5 Desduplicación de Publicaciones Múltiples de un Mismo Mensaje
- **SI** un mensaje con `id_mensaje = "105"` fue publicado sucesivamente a varios canales (ej. Discord a las 10:00 y LinkedIn a las 10:30), existiendo dos filas en `public.historial_reportes_semanales`:
  1. El sistema agrupa los registros por `id_mensaje`.
  2. Consolida las `rutas_activas` combinando los canales (`['discord', 'linkedin']`).
  3. Unifica el objeto `copys_generados` conteniendo ambos canales (`{"discord": {...}, "linkedin": {...}}`).
  4. Adopta la fecha de publicación más reciente como `fecha_publicacion`.
  5. Computa una única vez las métricas de sentimiento, temas y segmentos para no inflar los totales de la comunidad.

### 3.6 Formateo Determinista de `copy_final`
- **SI** un mensaje publicado cuenta con copys en múltiples canales en `copys_generados`:
  1. El sistema evalúa el orden de prelación estricto: LinkedIn -> Discord -> X.
  2. Para el canal seleccionado, une el título y el cuerpo con doble salto de línea si el título existe: `f"{titulo}\n\n{texto_copy}".strip()`.
  3. Si no hay título, utiliza únicamente `texto_copy.strip()`.
  4. Si ningún canal contiene copy, utiliza `texto_original`.

---

## 4. Criterios de Aceptación y Verificación (Definition of Done)

1. **Extracción Primaria en Generación Activa (Supabase Enoc):**
   - El endpoint `POST /api/v1/oci-storage/weekly-sync` consulta de manera primaria `public.historial_reportes_semanales` en Supabase Enoc (`swdoucawdasxmnomlcfu`) con timeout <= 4s.
   - Deserializa defensivamente `contenido_original` y garantiza la presencia de `item["kpis"]` con todas sus claves requeridas.
2. **Complemento de Descartados desde SQLite Local:**
   - Los mensajes descartados de la semana se complementan desde SQLite local (`communitylab.db`: `estado_curaduria = 'discarded'` o `relevancia < 70`) o `lotes_ia_kpis`, de modo que `total_mensajes` (`aprobados + descartados`) refleje el universo completo analizado.
3. **Inyección Determinista de Copys y Erradicación de Placeholders:**
   - La propiedad `copy_final` se resuelve con prelación 1) LinkedIn, 2) Discord, 3) X.
   - Se formatea como `f"{titulo}\n\n{texto_copy}".strip()` si hay título, o `texto_copy.strip()` si no lo hay.
   - `copys_generados` preserva el diccionario estructurado multicanal íntegro.
   - Queda totalmente erradicado `"Pendiente de redacción por Enoc..."` en los registros procesados.
4. **Cumplimiento de la Regla de Oro en GET /api/v1/oci-storage/reports:**
   - `GET /api/v1/oci-storage/reports` responde estrictamente desde la caché en memoria y los archivos `reportes/*.json` en menos de **2 milisegundos** (< 2 ms), sin llamadas de red WAN bloqueantes.
   - La memoria caché con TTL >= 5 minutos responde consultas en menos de 10 ms y se invalida de forma atómica ante publicaciones, decisiones HITL o sincronizaciones semanales.
5. **Modo Offline OCI y Códigos HTTP Controlados:**
   - En ausencia de credenciales OCI, se guarda en disco local `reportes/{semana}.json` con `subido_oci=False` y `status="saved_locally"` respondiendo HTTP 200.
   - Si no existen mensajes analizados en ninguna fuente para la semana solicitada, se responde con HTTP 400 controlado, impidiendo errores HTTP 500.
6. **Inviolabilidad Constitucional y Cero Secretos:**
   - Cero modificaciones en los 17 archivos protegidos de la raíz, `backend/`, `motor-ia/` y `src/`.
   - Cero credenciales en código duro (uso exclusivo de variables de entorno).
   - Cobertura completa de pruebas unitarias y de integración en `tests/` ejecutadas satisfactoriamente en verde (`pytest`).
