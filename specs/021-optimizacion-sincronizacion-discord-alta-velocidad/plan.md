# Plan de Implementación — Spec 021: Optimización de Alta Velocidad para la Sincronización con Discord y Homologación con la Rama de Respaldo demo-nube-funcional

## 1. Resumen Arquitectónico y Diagnóstico Técnico

### 1.1 Diagnóstico de Latencia y Cuellos de Botella en Producción Cloud (Render)
En el entorno desplegado de producción, la sincronización de mensajes desde Discord hacia el backend experimentaba retardos inaceptables de entre 20 y 30 segundos. El análisis del flujo y la homologación con la rama de respaldo funcional en la nube (`personal/demo-nube-funcional`) reveló tres cuellos de botella estructurales:

1. **Consulta bloqueante de canales del servidor (`GET /guilds/{guild_id}/channels`):**
   - Previo a descargar mensajes, el backend ejecutaba una petición HTTP externa con timeout de 4s a través del proxy Cloudflare Worker para redescubrir dinámicamente los canales.
   - Dado que los 4 canales autorizados de la comunidad CloudEdTech (#general, #faq, #pqrs, #notificaciones) son estáticos y canónicos, esta consulta añadía de 3 a 5 segundos de retardo WAN innecesario y un punto de fallo crítico.
2. **Persistencia bloqueante en Supabase PostgreSQL en la ruta crítica:**
   - La implementación previa invocaba `procesamiento.procesar_actividad(paquete)` creyendo que persistía en SQLite local, cuando en realidad invocaba `base_datos.guardar_interaccion` hacia **Supabase PostgreSQL remoto**.
   - Cada mensaje nuevo hacía un round-trip WAN sobre internet a Supabase; inmediatamente después, el backend ejecutaba `invalidar_cache_supabase()` y llamaba a `_sincronizar_supabase_a_sqlite()`, realizando un `SELECT *` masivo de vuelta a través de internet desde Supabase hacia SQLite.
   - Este doble viaje WAN representaba entre 12 y 20 segundos de la latencia observada.
3. **Falta de Keep-Alive y Pool de Conexiones HTTP:**
   - Las solicitudes se realizaban mediante `urllib.request` sin reutilización de conexiones TCP ni túneles TLS, penalizando cada canal con nuevos handshakes.
4. **Desconexión Frontend/Backend en Sincronización Manual:**
   - El botón de sincronización manual en `Messages.tsx` forzaba `{ asincrono: true }` y dependía de un `setTimeout(2000)` ciego que retornaba métricas en cero.

### 1.2 Objetivos Arquitectónicos
- **Tiempo síncrono manual (`asincrono: false`):** < 2.5 segundos de ciclo completo (descarga concurrente + persistencia local SQLite + respuesta con métricas reales definitivas).
- **Tiempo asíncrono en segundo plano (`asincrono: true`):** < 100 milisegundos de respuesta inmediata con confirmación de tarea en background.
- **Replicación desacoplada:** La escritura en Supabase PostgreSQL se despacha en segundo plano vía `asyncio.create_task` utilizando un hilo de trabajo (`asyncio.to_thread`), protegiendo la latencia del usuario.
- **Inviolabilidad Constitucional:** Preservar intactos los 17 archivos protegidos de la raíz del proyecto, `backend/`, `motor-ia/` y `src/`.

---

## 2. Arquitectura Técnica de la Solución

```
                                  ARQUITECTURA DE SINCRONIZACIÓN ULTRA-RÁPIDA
                                  
  [Frontend: Messages.tsx]
       │
       │ POST /api/v1/discord/sync { asincrono: false }
       ▼
  [FastAPI: puente_motor_ia.py] ─── (Verifica _discord_sync_lock)
       │
       ├────────────────────────────────────────────────────────────────────────┐
       │ (1) Conexiones Concurrente Keep-Alive                                  │ (Modo asíncrono: false)
       ▼                                                                        │
  ┌───────────────────────────────────────────────────────────┐                 │
  │ HTTP Connection Pool (requests.Session + HTTPAdapter)     │                 │
  │ Pool Size: 10 | Max Retries: 2 | Timeout: 3.5s            │                 │
  └──────────────────────────┬────────────────────────────────┘                 │
                             │                                                  │
                 ┌───────────┴───────────┐                                      │
                 ▼                       ▼                                      │
       [Cloudflare Worker Proxy]   [Discord API REST v10]                       │
       GET /channels/{id}/messages (x4 canales concurrentes)                    │
                 │                       │                                      │
                 └───────────┬───────────┘                                      │
                             ▼                                                  │
       (2) Recolección & Filtrado de Bots/Webhooks                              │
           (Telemetría en _cache_bots_omitidos_discord)                         │
                             │                                                  │
                             ▼                                                  │
       (3) Persistencia Atómica Directa en SQLite Local                         │
           - Normalización de texto (limpieza.limpiar_texto)                    │
           - Hash SHA-256 idempotente (limpieza.calcular_hash)                  │
           - Transacción directa en communitylab.db (tabla interacciones)       │
           - Métricas definitivas calculadas instantáneamente                   │
                             │                                                  │
       ┌─────────────────────┴────────────────────────┐                         │
       ▼                                              ▼                         │
  (4) Retorno Inmediato al Cliente          (5) Replicación Desacoplada         │
      HTTP 200 (< 2.5 segundos)                 asyncio.create_task(...)        │
      {                                               │                         │
        "exito": true,                                ▼                         │
        "guardadas_nuevas": 1,             [Supabase PostgreSQL WAN]            │
        "repetidas_omitidas": 81,          (Ejecución en segundo plano          │
        "total_recibidas": 82               vía asyncio.to_thread)              │
      }                                                                         │
```

---

## 3. Detalle de Componentes y Módulos

### 3.1 Pool de Conexiones Persistente y Keep-Alive hacia Proxy/Discord
- Se implementa un singleton a nivel de módulo `_obtener_discord_http_session()` en `puente_motor_ia.py`:
  - Instancia persistente de `requests.Session`.
  - Montaje de `HTTPAdapter(pool_connections=10, pool_maxsize=10, max_retries=Retry(total=2, backoff_factor=0.2, status_forcelist=[500, 502, 503, 504]))` tanto en `https://` como en `http://`.
  - Configuración de cabeceras fijas: `Authorization: Bot <token>`, `User-Agent: CommunityLab/1.0`, `Accept: application/json`.
  - Reutilización de túneles TLS ya negociados con Cloudflare Worker proxy (`https://discord-proxy-edtech.fraustojeovany.workers.dev`) o Discord API directa.
  - Timeout individual estricto de 3.5s por canal.
- **Eliminación de la consulta a `/guilds/{guild_id}/channels`:**
  - El sistema no realiza llamadas a la ruta de guild.
  - Consume directamente los canales autorizados canónicos:
    - `DISCORD_CHANNEL_GENERAL` (fallback: `"1550016804418621452"`, nombre: `general`)
    - `DISCORD_CHANNEL_FAQ` (fallback: `"1551309664397033513"`, nombre: `faq`)
    - `DISCORD_CHANNEL_PQRS` (fallback: `"1559244209884504245"`, nombre: `pqrs`)
    - `DISCORD_CHANNEL_NOTIFICACIONES` (fallback: `"1559244522842488942"`, nombre: `notificaciones`)

### 3.2 Descarga Concurrente de Canales y Manejo de Rate Limit (HTTP 429)
- Las descargas se despachan en paralelo utilizando `asyncio.gather(*[asyncio.to_thread(_descargar_canal, cid, cname) for cid, cname in canales_objetivo], return_exceptions=True)`.
- Si un canal específico experimenta timeout o error de red, la excepción se captura localmente en su hilo y no interrumpe la sincronización de los otros canales.
- Se contabilizan los canales exitosos y se formula el mensaje: `Sincronización exitosa (4 de 4 canales): X mensajes guardados`.
- Si el proxy o Discord devuelven `429 Too Many Requests`:
  - Se extrae el encabezado `Retry-After` (fallback 5s).
  - Se retorna respuesta estructurada: `{"es_rate_limit": true, "reintentar_en_segundos": N, "origen": "Cloudflare Proxy" | "Discord API"}`.

### 3.3 Persistencia Atómica Directa en SQLite Local (`communitylab.db`)
- Para cada mensaje extraído de los canales:
  1. **Filtrado de bots y webhooks:** Si `author.bot == True` o existe `webhook_id`, se incrementa la telemetría `_cache_bots_omitidos_discord` y se excluye de las interacciones de la comunidad.
  2. **Limpieza y normalización de texto:** Se invoca `limpieza.limpiar_texto(texto_raw)`. Si el texto resultante es vacío, se suma a `vacias_omitidas` y se omite.
  3. **Cálculo de hash:** Se obtiene la huella unificada con `limpieza.calcular_hash(origen, canal_nombre, autor, texto_limpio)`.
  4. **Detección de duplicados e idempotencia:** Se consulta `SELECT id FROM interacciones WHERE hash = ? OR (message_id = ? AND message_id != '')`.
     - Si existe: se incrementa `repetidas_omitidas`.
     - Si no existe: se ejecuta `INSERT INTO interacciones` con valores:
       - `hash`: hash calculado
       - `origen_comunidad`: `"Discord_Grupo_ONE_G10"`
       - `periodo_referencia`: período ISO derivado de la fecha (`Semana_WW`)
       - `autor`: nombre del autor
       - `canal`: `#nombre_canal`
       - `tipo`: `"mensaje"`
       - `texto`: texto normalizado
       - `enviado_en`: timestamp ISO UTC del mensaje
       - `creado_en`: timestamp ISO UTC actual
       - `channel_id`: ID del canal de Discord
       - `message_id`: ID del mensaje de Discord
       - `estado`: `"pendiente"`
       - `estado_curaduria`: `"pending"`
       - `etapa_flujo`: `"ingesta"`
       - `etapa`: `"ingesta"`
       - Se incrementa `guardadas_nuevas`.
  5. Se ejecuta `conn.commit()` tras procesar el lote completo de forma atómica.
  6. Ecuación contable rigurosa: `total_recibidas == guardadas_nuevas + repetidas_omitidas + vacias_omitidas`.

### 3.4 Desacoplamiento de Supabase vía `asyncio.create_task`
- Se elimina completamente de la ruta síncrona:
  - `procesamiento.procesar_actividad(paquete)` en el hilo principal.
  - `_sincronizar_supabase_a_sqlite()`.
  - `obtener_datos_supabase(forzar=True)`.
- Si `guardadas_nuevas > 0`, se lanza una corrutina en segundo plano con `asyncio.create_task(_replicar_supabase_background(mensajes_nuevos))`.
- La función de réplica ejecuta en un hilo aislado (`asyncio.to_thread`) la persistencia en Supabase usando `_base_datos_raiz.guardar_interaccion` para cada mensaje nuevo y luego llama a `invalidar_cache_supabase()`.
- Cualquier fallo o lentitud en Supabase queda contenido en los logs de advertencia sin afectar en absoluto la respuesta que ya se entregó al cliente HTTP.

### 3.5 Contratos de Entrada y Salida del Endpoint `/api/v1/discord/sync`

#### Modo Manual Síncrono (`asincrono: false`)
- **Petición:** `POST /api/v1/discord/sync`
  ```json
  {
    "limite_por_canal": 100,
    "asincrono": false
  }
  ```
- **Respuesta Exitosa (HTTP 200, < 2.5s):**
  ```json
  {
    "exito": true,
    "total_recibidas": 82,
    "guardadas_nuevas": 1,
    "repetidas_omitidas": 81,
    "vacias_omitidas": 0,
    "canales_consultados": 4,
    "canales_exitosos": 4,
    "periodo_referencia": "Semana_43",
    "mensaje": "Sincronización exitosa: 1 mensajes nuevos guardados (Nuevas: 1 | Omitidas: 81 | Total: 82)",
    "asincrono": false
  }
  ```

#### Modo Segundo Plano (`asincrono: true`)
- **Petición:** `POST /api/v1/discord/sync`
  ```json
  {
    "limite_por_canal": 100,
    "asincrono": true
  }
  ```
- **Respuesta Exitosa (HTTP 200, < 100ms):**
  ```json
  {
    "exito": true,
    "total_recibidas": 0,
    "guardadas_nuevas": 0,
    "repetidas_omitidas": 0,
    "vacias_omitidas": 0,
    "periodo_referencia": "Semana_43",
    "mensaje": "Comprobando mensajes en segundo plano. Tu bandeja se actualizará automáticamente.",
    "asincrono": true
  }
  ```

#### Conflicto Concurrente (HTTP 409)
- **Respuesta:**
  ```json
  {
    "exito": false,
    "mensaje": "Sincronización en curso, por favor espera un momento",
    "detail": "Sincronización en curso"
  }
  ```

---

## 4. Ajustes en Frontend (`frontend/src/`)

### 4.1 Cliente de API (`frontend/src/api/discordSync.ts`)
- Configurar el valor predeterminado del parámetro `asincrono` en `syncDiscord`:
  - Si se invoca sin argumentos o con `{ asincrono: false }`, despachar efectivamente `asincrono: false`.
  - Asegurar tipado `asincrono?: boolean` en `DiscordSyncParams` y `DiscordSyncResponse`.
  - Incluir en la respuesta los campos `canales_consultados` y `canales_exitosos`.

### 4.2 Vista de Ingesta (`frontend/src/pages/Messages.tsx`)
- En `handleSyncDiscord`:
  1. Invocar `syncDiscord({ asincrono: false })`.
  2. Activar spinner de carga en el botón (`isSyncingDiscord = true`, `Sincronizando...`).
  3. Al recibir la respuesta en < 2.5s:
     - Ejecutar inmediatamente `loadMessages()` para recargar los mensajes y refrescar las 4 tarjetas KPI (`Analizados`, `Positivos`, `Preguntas`, `Destacados`).
     - Desplegar alerta informativa / toast con el desglose exacto:
       `✓ Sincronización exitosa: ${guardadas_nuevas} mensajes nuevos (${repetidas_omitidas} ya existían).`
  4. Manejo amigable de HTTP 409: capturar el status 409 y mostrar alerta tipo info: `Sincronización en curso, por favor espera un momento` sin arrojar excepción no controlada.
- Preservar la auto-sincronización silenciosa en el `useEffect` inicial al montar el componente con `syncDiscord({ asincrono: true }).catch(() => {})`.
- Preservar las auto-sincronizaciones en segundo plano tras publicar anuncios o quejas en `ContentStudio.tsx`.

---

## 5. Cumplimiento Constitucional e Inviolabilidad

| Principio Constitucional | Mecanismo de Garantía en Spec 021 |
|---|---|
| **1. Inviolabilidad del Main** | Desarrollo en rama activa `beta-pruebas`. Cero commits a `main`. |
| **2. Aislamiento de Interfaz** | `app.py` no se modifica. La lógica de sincronización permanece en `puente_motor_ia.py` y `api/discordSync.ts`. |
| **3. Retrocompatibilidad** | Los contratos JSON de `POST /api/v1/discord/sync` mantienen todos los campos previos (`exito`, `total_recibidas`, `guardadas_nuevas`, `repetidas_omitidas`, `vacias_omitidas`, `periodo_referencia`, `mensaje`, `asincrono`). |
| **4. Seguridad de Secretos** | Tokens leídos de `os.getenv("DISCORD_BOT_TOKEN")`. IDs de canales desde variables canónicas de entorno. Ningún secreto en código duro. |
| **5. Control de Dependencias** | Se utilizan `requests`, `urllib`, `sqlite3`, `asyncio`, ya presentes en `requirements.txt`. |
| **6. Diseño Test-First (TDD)** | Fase Red previa con pruebas unitarias e integración en `tests/test_unificacion_motor_ia.py` antes de modificar `puente_motor_ia.py` y frontend. |
| **Protección de Archivos** | Cero modificaciones a los 17 archivos protegidos de la raíz, `backend/`, `motor-ia/` y `src/`. |
