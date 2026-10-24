# Especificación 021: Optimización de Alta Velocidad para la Sincronización con Discord y Homologación con la Rama de Respaldo demo-nube-funcional

## 1. Contexto y Propósito (El POR QUÉ)

### 1.1 Diagnóstico de Latencia en Producción Cloud (Render)
En el entorno de producción desplegado en Render, la sincronización de mensajes de la comunidad con Discord funciona correctamente a nivel funcional:
`"Sincronización exitosa: 1 mensajes nuevos guardados (Nuevas: 1 | Omitidas: 81 | Total: 82)"`
Sin embargo, el ciclo completo de ejecución experimenta una latencia inaceptable de entre 20 y 30 segundos por cada sincronización. Este retardo degrada severamente la experiencia de usuario en la vista de Ingesta (`/messages`), genera la percepción de congelamiento de la aplicación y puede provocar problemas de timeout en peticiones HTTP en cascada.

### 1.2 Hallazgos Técnicos y Corrección de Premisas de Arquitectura
Al auditar y contrastar la rama de respaldo en la nube `personal/demo-nube-funcional` y el código real frente a la implementación en `puente_motor_ia.py`, se identificaron los cuellos de botella críticos que provocan esta latencia:

1. **Consulta Bloqueante e Innecesaria de Canales del Servidor (`guilds/{guild_id}/channels`):**
   - Antes de leer mensajes, el backend realiza una petición HTTP `GET /api/v10/guilds/{guild_id}/channels` con un timeout de 4 segundos a través del proxy Cloudflare Worker para redescubrir dinámicamente los canales.
   - Dado que los 4 canales autorizados de la comunidad CloudEdTech están formalmente definidos y son estáticos (#general, #faq, #pqrs, #notificaciones), esta consulta añade entre 3 y 5 segundos de retraso por llamada externa y agrega un punto de falla innecesario.
2. **Persistencia Bloqueante en Supabase PostgreSQL en la Ruta Crítica (Corrección de Premisa):**
   - En el diseño anterior se asumía incorrectamente que `procesamiento.procesar_actividad(paquete)` guardaba en SQLite local. En realidad, dicho módulo invoca `base_datos.guardar_interaccion`, el cual conecta y escribe directamente en **Supabase PostgreSQL remoto** a través de internet (vía `psycopg2`).
   - Cada mensaje nuevo realizaba un viaje de ida y vuelta sobre WAN a Supabase.
   - Inmediatamente después, el backend ejecutaba `invalidar_cache_supabase()` y llamaba a `_sincronizar_supabase_a_sqlite()`, lo que desencadenaba un `SELECT *` masivo de vuelta a través de internet desde Supabase hacia SQLite.
   - Este doble viaje WAN remoto representaba entre 12 y 20 segundos de la latencia total observada.
3. **Descarga de Canales sin Pool de Conexiones ni Keep-Alive Reutilizable:**
   - La recuperación de mensajes se hacía abriendo conexiones HTTP independientes por canal, repitiendo handshakes TCP y negociaciones TLS con el proxy Cloudflare Worker.
   - La implementación de una instancia persistente de `requests.Session` con adaptador de pool (`HTTPAdapter`) permite reusar los túneles TCP/TLS existentes, recortando la descarga concurrente de los 4 canales a < 500 ms.
4. **Desconexión entre Frontend y Backend en Sincronización Manual:**
   - En `frontend/src/pages/Messages.tsx`, el botón manual `Sincronizar Discord` enviaba `{ asincrono: true }`, forzando al usuario a recibir contadores en cero y obligando a la interfaz a usar un temporizador ciego (`setTimeout(2000)`) que no garantizaba mostrar las métricas reales recién obtenidas.

### 1.3 Objetivos de Rendimiento y Experiencia de Usuario
- Reducir el tiempo total de sincronización síncrona manual de >25 segundos a menos de **2.5 segundos** en producción.
- Persistir atómicamente de forma directa e inmediata en la tabla `interacciones` de SQLite local (`communitylab.db`), respondiendo al cliente con las métricas definitivas al instante.
- Desacoplar la replicación a Supabase PostgreSQL ejecutándola en segundo plano (`asyncio.create_task`), eliminando completamente `_sincronizar_supabase_a_sqlite` y `obtener_datos_supabase(forzar=True)` de la ruta crítica del endpoint de sincronización.
- Mantener auto-sincronizaciones en segundo plano (`asincrono: true`) con respuesta ultra-rápida en menos de **100 milisegundos**.
- Asegurar estricta coherencia matemática en las métricas de mensajes y telemetría de bots omitidos.
- Preservar la inviolabilidad de los 17 archivos protegidos de la raíz y respetar las reglas constitucionales.

---

## 2. Requerimientos Funcionales (El QUÉ — Formato EARS)

### RF-01: Descarga Concurrente de Canales Autorizados con Pool de Conexiones HTTP y Parametrización Canónica
- **MIENTRAS** el sistema procese una sincronización con Discord en el endpoint `POST /api/v1/discord/sync`, **EL SISTEMA DEBERÁ** consultar de manera concurrente y directa los 4 canales autorizados leyendo prioritariamente las variables de entorno canónicas:
  - `DISCORD_CHANNEL_GENERAL` (fallback: `1550016804418621452`, nombre `#general`)
  - `DISCORD_CHANNEL_FAQ` (fallback: `1551309664397033513`, nombre `#faq`)
  - `DISCORD_CHANNEL_PQRS` (fallback: `1559244209884504245`, nombre `#pqrs`)
  - `DISCORD_CHANNEL_NOTIFICACIONES` (fallback: `1559244522842488942`, nombre `#notificaciones`)
  **sin realizar llamadas previas bloqueantes** a la ruta de redescubrimiento `/guilds/{guild_id}/channels`.
- **CUANDO** se despachen las peticiones concurrentes de descarga de mensajes hacia los canales autorizados, **EL SISTEMA DEBERÁ** utilizar una instancia persistente de `requests.Session` configurada con `HTTPAdapter(pool_connections=10, pool_maxsize=10)` para reutilizar las conexiones TCP/TLS activas y mantener Keep-Alive hacia el proxy Cloudflare Worker o la API REST de Discord.
- **SI** uno o más canales presentan error de red o timeout durante la descarga paralela, **EL SISTEMA DEBERÁ** capturar la excepción de forma aislada para cada canal fallido, continuar con la recolección de los canales exitosos y reportar en el mensaje de respuesta cuántos canales respondieron con éxito (por ejemplo: `Sincronizados 3 de 4 canales`).

### RF-02: Persistencia Local Inmediata en SQLite y Replicación Desacoplada a Supabase
- **CUANDO** el backend finalice la recolección de mensajes de Discord y construya el paquete de actividad, **EL SISTEMA DEBERÁ** persistir de manera directa, atómica e inmediata los mensajes nuevos en la tabla `interacciones` de la base de datos local SQLite (`communitylab.db`), calculando su hash unificado con `limpieza.calcular_hash`, normalizando su texto con `limpieza.limpiar_texto` y asignando su estado inicial (`estado = 'pendiente'`, `estado_curaduria = 'pending'`, `etapa_flujo = 'ingesta'`).
- **MIENTRAS** se ejecuta la sincronización en el endpoint `POST /api/v1/discord/sync`, **EL SISTEMA DEBERÁ** eliminar de la ruta crítica síncrona cualquier llamada a `_sincronizar_supabase_a_sqlite()` o consultas `SELECT *` masivas a Supabase PostgreSQL (`obtener_datos_supabase(forzar=True)`), respondiendo de inmediato al cliente con el desglose definitivo de la operación (`guardadas_nuevas`, `repetidas_omitidas`, `vacias_omitidas`, `total_recibidas`).
- **CUANDO** se hayan almacenado los mensajes nuevos en SQLite local, **EL SISTEMA DEBERÁ** despachar la replicación y respaldo hacia Supabase PostgreSQL en segundo plano mediante `asyncio.create_task` (invocando de forma asíncrona la persistencia remota o `procesamiento.procesar_actividad(paquete)` en un hilo secundario con `asyncio.to_thread`), garantizando que la latencia de la base de datos remota no degrade la respuesta al cliente.

### RF-03: Optimización de Conexiones HTTP, Resiliencia ante Rate Limits y Telemetría Coherente de Bots
- **CUANDO** se realicen peticiones hacia Discord vía REST o mediante el proxy Cloudflare Worker, **EL SISTEMA DEBERÁ** aplicar un timeout estricto de máximo 3.5 segundos por petición concurrente de canal, garantizando que la recolección total concluya en menos de 1 segundo en condiciones normales.
- **SI** la API de Discord o el proxy Cloudflare Worker responden con limitación de tasa (HTTP 429), **EL SISTEMA DEBERÁ** devolver una respuesta estructurada (`es_rate_limit: true`, `reintentar_en_segundos`, `origen: 'Cloudflare Proxy' | 'Discord API'`) para su manejo adecuado sin generar bloqueos en el servidor.
- **MIENTRAS** se reciban mensajes durante la descarga, **EL SISTEMA DEBERÁ** identificar los mensajes emitidos por bots o webhooks (`author.bot == True` o presencia de `webhook_id`), contabilizarlos en `_cache_bots_omitidos_discord` y excluirlos de las interacciones de la comunidad, asegurando una estricta coherencia matemática en el balance del resumen: `total_recibidas = guardadas_nuevas + repetidas_omitidas + vacias_omitidas` (los bots se contabilizan de forma transparente en su propia métrica de telemetría).

### RF-04: Armonización de Frontend en Ingesta de Mensajes (`Messages.tsx`)
- **CUANDO** el operador presione manualmente el botón `Sincronizar Discord` en la vista de Ingesta (`/messages`), **EL SISTEMA DEBERÁ** despachar la petición a `POST /api/v1/discord/sync` con el parámetro `{ asincrono: false }`, deshabilitar temporalmente el botón mostrando el estado visual `Sincronizando...` y un indicador animado.
- **CUANDO** el backend retorne la respuesta síncrona en menos de 2.5 segundos con el resultado definitivo, **EL SISTEMA DEBERÁ** actualizar de inmediato la lista de mensajes en pantalla (`loadMessages`), refrescar las 4 tarjetas KPI (`Analizados`, `Positivos`, `Preguntas`, `Destacados`) y desplegar una notificación informativa con el desglose exacto de mensajes (`guardadas_nuevas`, `repetidas_omitidas`).
- **SI** el backend responde con conflicto (HTTP 409), **EL SISTEMA DEBERÁ** capturar la respuesta y mostrar una notificación amigable de tipo informativo indicando `Sincronización en curso, por favor espera un momento` sin bloquear la UI ni alterar el estado del operador.

### RF-05: Soporte Dual Síncrono de Alta Velocidad y Asíncrono en Segundo Plano
- **SI** la petición a `POST /api/v1/discord/sync` recibe `{ asincrono: true }` —utilizado exclusivamente en la auto-sincronización silenciosa al montar `Messages.tsx` o tras la publicación de contenidos, quejas y anuncios en `ContentStudio.tsx`—, **EL SISTEMA DEBERÁ** responder en menos de 100 milisegundos con confirmación de tarea en segundo plano e iniciar la descarga y persistencia sin bloquear el hilo principal.
- **SI** la petición a `POST /api/v1/discord/sync` recibe `{ asincrono: false }` o se omiten parámetros de segundo plano, **EL SISTEMA DEBERÁ** ejecutar la sincronización síncrona directa optimizada, persistir en SQLite local y responder con las métricas definitivas completas en menos de 2.5 segundos.

### RF-06: Inviolabilidad Constitucional y Aislamiento Arquitectónico
- **EN TODO MOMENTO**, **EL SISTEMA DEBERÁ** mantener intactos y sin modificaciones los 17 archivos protegidos de la raíz del proyecto (`armar_json_bot_python.py`, `anuncios_discord.py`, `base_datos.py`, `api.py`, `procesamiento.py`, etc.), así como las carpetas `backend/`, `motor-ia/` y `src/`.
- **EN TODO MOMENTO**, toda la lógica de alta velocidad, manejo de pool HTTP, persistencia directa en SQLite y despacho desacoplado a Supabase deberá residir exclusivamente en `puente_motor_ia.py`, los componentes de `frontend/src/` y sus pruebas asociadas en `tests/`.

---

## 3. Casos Límite y Manejo de Errores

### 3.1 Manejo de Concurrencia y Conflicto (HTTP 409)
- **SI** se dispara una petición síncrona o asíncrona mientras existe otra sincronización en ejecución protegida por `_discord_sync_lock`, el endpoint responde HTTP 409 con `{ "exito": false, "mensaje": "Sincronización en curso" }`. El frontend muestra un aviso amigable tipo notificación/toast sin bloquear la interfaz ni interrumpir la navegación del operador.

### 3.2 Tolerancia a Fallos Parciales de Red en Canales
- **SI** uno o más de los 4 canales autorizados falla durante la descarga (por ejemplo, timeout de 3.5 segundos o error de red transitorio), los canales restantes se procesan con normalidad. El sistema calcula las métricas sobre los canales recuperados y reporta en el mensaje de respuesta: `Sincronización parcial (X de 4 canales exitosos): Y mensajes guardados`.

### 3.3 Coherencia Matemática en Contadores y Telemetría de Bots
- **SI** se detectan mensajes emitidos por bots (`author.bot == True`) o webhooks (`webhook_id` presente), estos no se integran al paquete de interacciones humanas de la comunidad. El total de bots detectados se acumula en el contador de telemetría global `_cache_bots_omitidos_discord` expuesto en la cabecera. La ecuación contable del paquete se mantiene matemáticamente consistente:
  `total_recibidas == guardadas_nuevas + repetidas_omitidas + vacias_omitidas`.

### 3.4 Rate Limit de Cloudflare Worker o Discord API (HTTP 429)
- **SI** el proxy de Cloudflare o Discord devuelven código HTTP 429, el backend extrae el valor de espera de `Retry-After` (con fallback de 5 segundos) y devuelve `{ "es_rate_limit": true, "reintentar_en_segundos": N, "origen": "Cloudflare Proxy" }`. El frontend notifica con claridad al operador el tiempo de espera recomendado.

---

## 4. Criterios de Aceptación y Verificación (Definition of Done)

1. **Rendimiento Cuantitativo:**
   - Modo manual síncrono (`asincrono: false`): ciclo completo de sincronización de los 4 canales con persistencia en SQLite local en menos de **2.5 segundos** en producción.
   - Modo background (`asincrono: true`): respuesta inmediata en menos de **100 milisegundos**.
2. **Eliminación Total de Cuellos de Botella:**
   - 0 llamadas salientes a `GET /guilds/{guild_id}/channels`.
   - 0 consultas bloqueantes `SELECT *` a Supabase PostgreSQL en la ruta crítica del endpoint de sincronización de Discord.
3. **Persistencia e Integridad:**
   - Los mensajes nuevos se insertan inmediatamente en la tabla `interacciones` de `communitylab.db`.
   - La replicación a Supabase se despacha en segundo plano vía `asyncio.create_task` sin retrasar la respuesta al usuario.
   - Idempotencia estricta verificada: mensajes duplicados se omiten y contabilizan en `repetidas_omitidas`.
4. **Armonización Frontend:**
   - Al pulsar `Sincronizar Discord` en `/messages`, se envía `{ asincrono: false }`, la UI recibe el desglose real (`guardadas_nuevas`, `repetidas_omitidas`, `total_recibidas`) y actualiza instantáneamente la lista y las 4 tarjetas KPI.
   - En el montaje de página (`Messages.tsx`) y al publicar anuncios/respuestas (`ContentStudio.tsx`), se envía `{ asincrono: true }` silencioso en segundo plano.
   - Respuestas HTTP 409 se muestran con mensaje amigable sin congelar la interfaz ni generar errores no capturados.
5. **Pool de Conexiones y Parametrización:**
   - Instancia persistente de `requests.Session` con `HTTPAdapter(pool_connections=10, pool_maxsize=10)` configurada en `puente_motor_ia.py`.
   - Variables de entorno canónicas `DISCORD_CHANNEL_GENERAL`, `DISCORD_CHANNEL_FAQ`, `DISCORD_CHANNEL_PQRS`, `DISCORD_CHANNEL_NOTIFICACIONES` con fallback a los 4 IDs oficiales (`1550016804418621452`, `1551309664397033513`, `1559244209884504245`, `1559244522842488942`).
6. **Calidad y Aislamiento Constitucional:**
   - Suite de pruebas unitarias e integración en `tests/` cubriendo los nuevos escenarios (mocks de Discord, pool de sesión y despacho desacoplado a Supabase).
   - 100% pruebas de `pytest` ejecutándose exitosamente en verde.
   - `npm run build` en `frontend/` finaliza con código 0 sin errores de tipado.
   - Cero modificaciones a los 17 archivos protegidos de la raíz del repositorio (`git status`).
