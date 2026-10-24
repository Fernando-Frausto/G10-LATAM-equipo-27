# Especificación 023: Persistencia en Historial de Reportes Semanales y LangGraph Checkpointer en Supabase Enoc con Garantía de Alta Velocidad

## 1. Contexto y Propósito (El POR QUÉ)

### 1.1 Contexto y Necesidad del Negocio
En el flujo editorial de la plataforma CloudEdTech, la Mesa de Redacción (`ContentStudio`) constituye el centro neurálgico donde los operadores humanos curan, editan y aprueban copys generados por modelos de Inteligencia Artificial antes de su publicación hacia las redes autorizadas (Discord, LinkedIn, X).

Actualmente:
1. Al completarse la publicación individual por canal (por ejemplo, publicación directa a Discord) o al ejecutarse la aprobación global mediante Human-in-the-Loop (HITL), la operación persiste los datos en SQLite local (`communitylab.db`), pero **no replica el registro histórico en la tabla `public.historial_reportes_semanales`** de la cuenta de Supabase de Enoc (`swdoucawdasxmnomlcfu`). Esta omisión impide la auditoría centralizada en la nube, el seguimiento semanal de copys aprobados y la visibilidad de los contenidos difundidos por la comunidad.
2. El orquestador de flujos complejos de IA de Mototradis utiliza LangGraph para gobernar las etapas de redacción, validación y control HITL. Cuando el sistema intenta persistir los estados intermedios en el PostgresSaver remoto conectado al Transaction Pooler (puerto `:6543`), el backend colapsa o aborta debido a la incompatibilidad intrínseca del pipeline de sentencias preparadas en modo transacción (`psycopg.errors.DuplicatePreparedStatement`), forzando a recurrir a soluciones en memoria volátiles o deshabilitando la persistencia duradera de hilos.

### 1.2 Diagnóstico Técnico y Causas Raíz
- **Incompatibilidad de Prepared Statements en Transaction Pooler (Puerto 6543):**
  El Transaction Pooler de Supabase (PgBouncer en modo transacción) intercambia conexiones de base de datos a nivel de transacción. Las librerías de checkpointing de LangGraph (`langgraph-checkpoint-postgres` y `psycopg 3`) utilizan internamente pipelines y sentencias preparadas nombradas (`_pg3_0`). Cuando una conexión se reutiliza, el driver intenta registrar nuevamente una sentencia preparada preexistente, arrojando `DuplicatePreparedStatement`. La resolución estándar y recomendada para Supabase consiste en operar sobre el **Session Mode (puerto `:5432`)** o configurar explícitamente el driver `psycopg` para deshabilitar sentencias preparadas automáticas (`prepare_threshold=None`), respaldado por un fallback inmediato a `MemorySaver` en caso de corte o degradación de red.
- **Ciclo de Vida de LangGraph Checkpoints vs. Replicación a Segundo Plano:**
  Los checkpoints de LangGraph capturan el estado paso a paso durante las transiciones de los nodos del grafo, por lo que su ejecución está vinculada al ciclo de vida del pipeline. Por el contrario, la replicación de datos consolidados hacia `public.historial_reportes_semanales` es una operación de auditoría diferida que debe desacoplarse estrictamente a segundo plano para no demorar la entrega de datos a los usuarios.
- **Ruta Crítica Síncrona vs. Experiencia de Usuario Reactiva:**
  Cualquier llamada de red WAN a Supabase (ida y vuelta transcontinental hacia PostgreSQL) introduce una latencia intrínseca de entre 200 y 1500 milisegundos. Si esta escritura remota se ubica de forma síncrona dentro del ciclo de solicitud-respuesta HTTP de publicación o checkpointing, la interfaz de usuario se congela, deteriorando la percepción de fluidez operativa.

### 1.3 Regla de Oro Innegociable de Alta Velocidad
Para salvaguardar la velocidad extrema de la aplicación y la precisión en el feedback al usuario:
1. **Sobrecarga Interna del Backend Inmediata (< 100 ms):**
   Al publicar un canal o emitir un veredicto HITL, la base de datos local SQLite (`communitylab.db`) absorbe la verdad operativa de forma atómica e inmediata, y la sobrecarga interna del procesamiento y persistencia local del backend se completa en menos de **100 milisegundos**.
2. **Despacho Interactivo hacia Redes Sociales Externas:**
   El envío hacia las APIs externas de redes (Discord Bot REST, LinkedIn API, X API v2) se ejecuta de forma interactiva con la latencia propia de la red externa correspondiente, con el objetivo de devolver al operador el estado real e inequívoco de la entrega (`'enviado'`, `'omitido'` o `'error'`) junto con sus identificadores de publicación (`message_id`, `tweet_id`, `urn`).
3. **Replicación WAN Desacoplada en Segundo Plano (`asyncio.create_task`):**
   Toda escritura remota hacia la tabla `public.historial_reportes_semanales` en Supabase Enoc debe ejecutarse de manera estrictamente desacoplada en segundo plano mediante `asyncio.create_task` (o ejecutor en hilo no bloqueante), sin añadir ni un solo milisegundo a la respuesta HTTP del endpoint.
4. **Lecturas Inmediatas Locales (< 2 ms):**
   Todos los endpoints de lectura (GET) continúan sirviéndose con exclusividad desde SQLite local y caché en memoria, prohibiendo de forma taxativa llamadas de red WAN a Supabase durante la consulta de vistas o listados.

### 1.4 Aislamiento Constitucional e Inviolabilidad de Archivos Protegidos
En cumplimiento de la Constitución del Proyecto:
- Los 17 archivos protegidos de la raíz (`base_datos.py`, `reporte_semanal.py`, `procesamiento.py`, `api.py`, etc.) y las carpetas `backend/`, `motor-ia/` y `src/` permanecen estrictamente **intactos e inalterados**.
- La orquestación y el desacoplamiento residen exclusivamente en `puente_motor_ia.py` y sus módulos de soporte.
- Cero credenciales quemadas en código duro: las URLs y credenciales se consumen estrictamente desde `os.environ` mediante `.env`.

---

## 2. Requerimientos Funcionales (El QUÉ — Formato EARS)

### RF-01: Registro Desacoplado en `public.historial_reportes_semanales` ante Publicación Individual por Canal
- **CUANDO** el operador emita una orden de publicación individual para un canal específico (Discord, LinkedIn o X) a través de los endpoints `/api/v1/mototradis/publish-channel` o `/api/v1/content-workflow/publish-channel`, **EL SISTEMA DEBERÁ** validar el contenido del copy, despachar el mensaje a la red social externa de manera interactiva registrando su latencia natural de red, y persistir el estado actualizado de forma síncrona en la base de datos local SQLite (`contenidos_generados` e `interacciones`), asegurando que la sobrecarga interna del backend no supere los **100 milisegundos**.
- **CUANDO** la publicación en el canal sea confirmada como exitosa (`estado_canal = 'enviado'`), **EL SISTEMA DEBERÁ** despachar en segundo plano mediante `asyncio.create_task` (sin bloquear ni añadir latencia a la respuesta HTTP) una tarea de replicación hacia la tabla `public.historial_reportes_semanales` en la base de datos de Supabase de Enoc (`swdoucawdasxmnomlcfu`).
- **MIENTRAS** se construye el registro para `public.historial_reportes_semanales`, **EL SISTEMA DEBERÁ** poblar con exactitud los siguientes campos canónicos:
  - `id_mensaje`: Identificador normalizado y almacenado siempre como cadena de texto (`str`), garantizando compatibilidad con identificadores enteros de SQLite y snowflakes de 64 bits de Discord sin desbordamiento numérico.
  - `autor`: Nombre o identificador del autor del mensaje comunitario.
  - `semana`: Etiqueta de la semana o periodo de referencia asociado (ej. `Semana_01`, `Semana_05`).
  - `fecha_envio`: Marca temporal original del mensaje o nulo si no está disponible.
  - `fecha_extraccion`: Marca temporal de ingesta del mensaje en el sistema.
  - `fecha_publicacion`: Marca temporal exacta del momento de la publicación exitosa (`NOW()` en formato ISO UTC).
  - `rutas_activas`: Arreglo estructurado conteniendo la lista de canales efectivamente despachados en ese evento específico (ej. `['discord']`).
  - `estado`: Valor literal `'publicado'`.
  - `contenido_original`: Objeto JSON con la información íntegra del mensaje de origen (texto, autor, canal).
  - `cw_modelo_ia`: Identificador canónico del modelo de IA generador, resuelto mediante la función canónica `resolver_modelo_canal(canal, proveedor)` y el catálogo oficial `MODELOS_UTILIZADOS_CATALOGO` (o `'orquestador-multi-llm'` por defecto si no se identifica uno específico).
  - `copys_generados`: Objeto JSON con el esquema canónico uniforme indexado por el canal despachado: `{"discord": {"titulo": "...", "texto_copy": "..."}}`.
- **EN TODO MOMENTO**, cada publicación individual exitosa se registrará como un evento histórico independiente (`INSERT`) en la tabla `public.historial_reportes_semanales`.

---

### RF-02: Registro Desacoplado en `public.historial_reportes_semanales` ante Aprobación Global HITL
- **CUANDO** el operador apruebe globalmente un lote de copys en la Mesa de Redacción mediante los endpoints `/api/v1/mototradis/hitl-decision` o `/api/v1/content-workflow/hitl-decision` (`decision = 'aprobar'`), **EL SISTEMA DEBERÁ** despachar concurrentemente los copys hacia todas las rutas activas configuradas respetando la latencia nativa de las redes sociales externas, registrar los resultados de forma atómica en SQLite local (`contenidos_generados` e `interacciones`), y retornar interactivamente al operador el diccionario `resultados_canales` con el estado real (`'enviado'`, `'omitido'` o `'error'`), manteniendo la sobrecarga interna del backend inferior a **100 milisegundos**.
- **CUANDO** al menos uno de los canales del lote haya sido publicado exitosamente (`estado_canal = 'enviado'`), **EL SISTEMA DEBERÁ** despachar en segundo plano mediante `asyncio.create_task` una tarea asíncrona no bloqueante para registrar la publicación consolidada en la tabla `public.historial_reportes_semanales` de Supabase Enoc.
- **MIENTRAS** se efectúe el registro consolidado del lote aprobado, **EL SISTEMA DEBERÁ** poblar:
  - `id_mensaje`: Cadena de texto (`str`) normalizada.
  - `rutas_activas`: Arreglo estructurado con la lista exhaustiva de canales que resultaron exitosamente despachados en ese evento (ej. `['discord', 'linkedin']`).
  - `fecha_publicacion`: Marca temporal exacta de la publicación exitosa (`NOW()`).
  - `copys_generados`: Objeto JSON manteniendo el esquema canónico uniforme indexado por canal para todos los borradores aprobados con las ediciones realizadas por el operador humano (Soberanía Humana), e.g. `{"discord": {"titulo": "...", "texto_copy": "..."}, "linkedin": {"titulo": "...", "texto_copy": "..."}, "x": {"titulo": "...", "texto_copy": "..."}}`.
  - `cw_modelo_ia`: Cadena descriptiva consolidada de los modelos intervinientes a partir de `MODELOS_UTILIZADOS_CATALOGO` o `'orquestador-multi-llm'`.
- **EN TODO MOMENTO**, el registro consolidado HITL se insertará como un evento histórico independiente (`INSERT`) en `public.historial_reportes_semanales`.

---

### RF-03: Persistencia de Checkpoints de LangGraph en Supabase Enoc con Resolución de Prepared Statements
- **MIENTRAS** el orquestador de LangGraph ejecute el flujo de trabajo de Mototradis (`execute-pipeline`, `generate-channel` o generación asistida), **EL SISTEMA DEBERÁ** persistir los estados intermedios del grafo durante el ciclo de vida de los nodos en las tablas de checkpointing de Supabase de Enoc (`public.checkpoints`, `public.checkpoint_writes`, `public.checkpoint_blobs`).
- **CUANDO** se inicialice o configure la conexión de `PostgresSaver` hacia Supabase de Enoc, **EL SISTEMA DEBERÁ** utilizar la estrategia primaria de conexión en Session Mode (puerto `:5432`) o configurar los parámetros de conexión de `psycopg 3` para deshabilitar la reutilización de sentencias preparadas automáticas (`prepare_threshold=None`), erradicando definitivamente la excepción `DuplicatePreparedStatement`.
- **DONDE** el identificador de hilo (`thread_id`) sea provisto, **EL SISTEMA DEBERÁ** estructurarlo bajo la convención canónica `sesion_{id_mensaje}` (con `id_mensaje` normalizado a texto), garantizando la recuperación exacta del estado de la sesión editorial ante recargas de página.
- **EN TODO MOMENTO**, el desacoplamiento estricto a segundo plano mediante `asyncio.create_task` aplicará a la replicación de `public.historial_reportes_semanales`, mientras que los checkpoints de LangGraph se gestionan de forma nativa durante la ejecución del grafo.

---

### RF-04: Resiliencia y Fallback Automático a `MemorySaver` ante Desconexión
- **SI** la conexión hacia la base de datos de Supabase de Enoc experimenta un fallo de red, timeout, rechazo de credenciales o indisponibilidad transitoria al inicializar o interactuar con `PostgresSaver`, **EL SISTEMA DEBERÁ** capturar la excepción defensivamente, emitir una advertencia estructurada en el registro de logs (`logger.warning`) y conmutar de manera automática y transparente a `MemorySaver` en memoria local.
- **EN TODO MOMENTO**, el fallo o lentitud de Supabase **NO DEBERÁ** interrumpir la ejecución del pipeline de redacción ni arrojar errores HTTP 500 al usuario de la Mesa de Redacción.

---

### RF-05: Garantía de Alta Velocidad: Sobrecarga Interna (< 100 ms), Despacho Interactivo y Lecturas Locales (< 2 ms)
- **EN TODO MOMENTO**, la sobrecarga interna del backend (validaciones, cálculo de metadatos y persistencia atómica en SQLite) en endpoints de mutación (`publish-channel`, `hitl-decision`) **DEBERÁ** ser estrictamente inferior a **100 milisegundos**.
- **MIENTRAS** se realiza la comunicación con APIs externas de redes sociales (Discord, LinkedIn, X), **EL SISTEMA DEBERÁ** ejecutarla con la latencia propia de la red externa de forma interactiva para retornar de inmediato el estado real (`'enviado'`, `'omitido'`, `'error'`) al operador, desacoplando cualquier escritura posterior hacia Supabase a segundo plano mediante `asyncio.create_task`.
- **MIENTRAS** los clientes consuman endpoints de lectura (GET) del catálogo editorial, mensajes, métricas o historial de trabajo, **EL SISTEMA DEBERÁ** responder en menos de **2 milisegundos** sirviendo los datos exclusivamente desde SQLite local (`communitylab.db`) y memoria caché, prohibiendo cualquier consulta de red remota en la ruta crítica de lectura.

---

### RF-06: Inviolabilidad Constitucional y Aislamiento Arquitectónico
- **EN TODO MOMENTO**, **EL SISTEMA DEBERÁ** mantener estrictamente intactos y sin modificación los 17 archivos protegidos de la raíz del repositorio (`base_datos.py`, `reporte_semanal.py`, `procesamiento.py`, `api.py`, etc.), así como los archivos y subdirectorios de `backend/`, `motor-ia/` y `src/`.
- **EN TODO MOMENTO**, cualquier adaptación, puente o fábrica de conexiones deberá residir exclusivamente en `puente_motor_ia.py` y módulos creados en `scripts/` o `tests/`.
- **EN TODO MOMENTO**, todas las cadenas de conexión y credenciales de base de datos **DEBERÁN** obtenerse exclusivamente de variables de entorno (`SUPABASE_DB_URL`, `DATABASE_URL`) definidas en `.env`, sin exponer ninguna credencial en código duro.

---

## 3. Casos Límite y Manejo de Errores

### 3.1 Indisponibilidad Transitoria o Timeout de Supabase en Segundo Plano
- **SI** la conexión a Supabase de Enoc falla durante la inserción en segundo plano en `public.historial_reportes_semanales` (timeout, error de red o autenticación):
  1. El sistema captura la excepción y registra el fallo en logs con nivel de advertencia (`logger.warning`).
  2. El sistema registra el estado de sincronización fallida/pendiente y el payload correspondiente en la base de datos local SQLite (`contenidos_generados` o registro de auditoría local) para permitir futura reconciliación automática o manual.
  3. La respuesta HTTP al usuario y el estado operativo local en SQLite permanecen 100% exitosos y no se ven afectados por el fallo remoto.

### 3.2 Semántica de Idempotencia, Múltiples Publicaciones y Tipos de Datos
- **SI** un operador publica sucesivamente diferentes canales de un mismo mensaje (por ejemplo, primero Discord y posteriormente LinkedIn):
  1. Cada publicación exitosa se registra como un evento histórico independiente (`INSERT`) en `public.historial_reportes_semanales`.
  2. Cada registro consigna su propia `fecha_publicacion = NOW()` y la lista exacta de `rutas_activas` despachadas en ese evento específico.
  3. El campo `id_mensaje` se normaliza y almacena invariablemente como cadena de texto (`str`), previniendo desbordamientos de enteros de 64 bits provenientes de identificadores de Discord (snowflakes) o identificadores de SQLite.

### 3.3 Campos Opcionales o Mensajes con Metadatos Parciales
- **SI** el mensaje de origen carece de `fecha_envio`, `canal` o `periodo_referencia`, el sistema aplica valores defensivos por defecto (`fecha_envio = NULL` o fecha actual, `canal = '#general'`, `semana = 'Semana_01'`), impidiendo errores de validación de esquemas en Supabase.

### 3.4 Desconexión Abrupta Durante el Checkpointing de LangGraph
- **SI** el checkpointer `PostgresSaver` sufre una desconexión en medio de la ejecución de un nodo, el orquestador captura el error, realiza el fallback a `MemorySaver` para los pasos subsiguientes y permite que los copys generados se presenten normalmente en la interfaz web sin pérdida del contenido recién inferido.

---

## 4. Criterios de Aceptación y Verificación (Definition of Done)

1. **Persistencia Verificada en `historial_reportes_semanales`:**
   - Al publicar individualmente un canal desde ContentStudio (Discord, LinkedIn, X), se despacha en segundo plano un `INSERT` en la tabla `public.historial_reportes_semanales` de Supabase Enoc registrando:
     - `id_mensaje` normalizado como `str`.
     - `cw_modelo_ia` resuelto mediante `resolver_modelo_canal(canal, proveedor)` y `MODELOS_UTILIZADOS_CATALOGO`.
     - `copys_generados` bajo el esquema canónico uniforme indexado por canal `{"discord": {"titulo": "...", "texto_copy": "..."}}`.
     - `rutas_activas` conteniendo la lista de canales despachados en ese evento (ej. `['discord']`).
     - `fecha_publicacion = NOW()`.
   - Al emitir aprobación HITL exitosa, se inserta un registro histórico independiente en la tabla con las rutas activas despachadas y `copys_generados` indexado por cada canal aprobado.
2. **Manejo Defensivo y Reconciliación ante Fallos en Segundo Plano:**
   - Ante simulación de indisponibilidad de Supabase durante la tarea en segundo plano, se emite un `logger.warning` y se almacena el estado pendiente en SQLite local sin arrojar errores ni retrasar la respuesta al cliente.
3. **LangGraph Checkpointer Funcional en Supabase Enoc:**
   - El checkpointer conecta a Supabase Enoc utilizando Session Mode (puerto `:5432`) o `prepare_threshold=None` en `psycopg 3`, eliminando el error `DuplicatePreparedStatement: prepared statement "_pg3_0" already exists`.
   - Los checkpoints de sesiones se registran en `checkpoints`, `checkpoint_writes` y `checkpoint_blobs` durante el ciclo de vida del grafo.
   - Ante simulación de desconexión remota, el sistema conmuta transparentemente a `MemorySaver` sin interrumpir la operación ni arrojar HTTP 500.
4. **Preservación Innegociable de Alta Velocidad:**
   - La sobrecarga interna del backend en endpoints de mutación (`publish-channel` y `hitl-decision`) se completa en menos de **100 milisegundos**.
   - El despacho a redes externas devuelve interactivamente el estado real (`'enviado'`, `'omitido'`, `'error'`) con la latencia propia de la red.
   - Los endpoints GET de lectura responden en menos de **2 milisegundos** desde SQLite local.
   - Cero consultas remotas bloqueantes a Supabase en la ruta crítica del hilo HTTP principal.
5. **Aislamiento Constitucional y Calidad:**
   - Cero modificaciones a los 17 archivos protegidos de la raíz, `backend/`, `motor-ia/` y `src/`.
   - Cero secretos o credenciales expuestos en código duro (100% via `os.environ` / `.env`).
   - 100% de la suite de pruebas automatizadas en `tests/` pasando satisfactoriamente en verde (`pytest`).
