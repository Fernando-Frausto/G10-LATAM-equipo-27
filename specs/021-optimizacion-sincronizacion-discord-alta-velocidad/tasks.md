# Tareas de Implementación — Spec 021: Optimización de Alta Velocidad para la Sincronización con Discord y Homologación con la Rama de Respaldo demo-nube-funcional

## [x] T1: Fase Red TDD en `tests/test_unificacion_motor_ia.py` (~20 min)
- **Rol:** `@implementer`
- **Archivos involucrados:**
  - `tests/test_unificacion_motor_ia.py`
- **Requerimientos Funcionales:** `RF-01`, `RF-02`, `RF-03`, `RF-05`, `RF-06`
- **Descripción:**
  1. Escribir pruebas automatizadas unitarias y de integración para validar la nueva arquitectura de sincronización de alta velocidad en `tests/test_unificacion_motor_ia.py`:
     - **Persistencia Directa en SQLite:** Validar que al ejecutar la sincronización REST, los mensajes nuevos se insertan directamente en la tabla `interacciones` de SQLite sin invocar `_sincronizar_supabase_a_sqlite` en la ruta crítica síncrona.
     - **Pool de Conexiones Keep-Alive:** Validar que el componente de cliente HTTP utilice una sesión persistente `requests.Session` con adaptador de conexiones (`pool_connections=10`, `pool_maxsize=10`) y timeout estricto de 3.5s.
     - **Exclusión de Consulta de Servidor:** Validar que el proceso omita cualquier petición a `GET /guilds/{guild_id}/channels`, leyendo directamente los canales autorizados desde variables de entorno canónicas.
     - **Desacoplamiento de Supabase en Segundo Plano:** Validar que cuando existan mensajes nuevos, la persistencia en Supabase se despache vía `asyncio.create_task` en background sin demorar la respuesta HTTP del endpoint.
     - **Tolerancia a Fallos Parciales de Red:** Simular el fallo de red en 1 de los 4 canales autorizados y validar que los 3 canales exitosos se sincronicen adecuadamente y se reporte `(3 de 4 canales exitosos)`.
     - **Coherencia Contable y Telemetría de Bots:** Validar que los mensajes de bots/webhooks se omitan de `interacciones`, se contabilicen en `_cache_bots_omitidos_discord` y la ecuación `total_recibidas == guardadas_nuevas + repetidas_omitidas + vacias_omitidas` se cumpla rigurosamente.
  2. Ejecutar `pytest` y confirmar que los nuevos tests fallan inicialmente antes de modificar `puente_motor_ia.py` (Fase Red TDD).
- **Hecho cuando:** Los tests de la Spec 021 existen en `tests/test_unificacion_motor_ia.py` y fallan de manera controlada y verificada demostrando la ausencia inicial de la implementación.

---

## [x] T2: Fase Green Backend — Implementación de Pool HTTP, Persistencia Directa en SQLite y Replicación Desacoplada en `puente_motor_ia.py` (~20 min)
- **Rol:** `@implementer`
- **Archivos involucrados:**
  - `puente_motor_ia.py`
- **Requerimientos Funcionales:** `RF-01`, `RF-02`, `RF-03`, `RF-05`, `RF-06`
- **Descripción:**
  1. Implementar la sesión HTTP persistente `_obtener_discord_http_session()` con `requests.Session` y `HTTPAdapter(pool_connections=10, pool_maxsize=10, max_retries=Retry(...))` asegurando Keep-Alive hacia el proxy Cloudflare Worker o Discord API.
  2. Eliminar la consulta HTTP bloqueante a `GET /guilds/{guild_id}/channels` en `_sincronizar_discord_api_rest`, consumiendo directamente las variables canónicas `DISCORD_CHANNEL_GENERAL`, `DISCORD_CHANNEL_FAQ`, `DISCORD_CHANNEL_PQRS`, `DISCORD_CHANNEL_NOTIFICACIONES` con sus fallbacks oficiales.
  3. Refactorizar la recolección paralela por canal para usar la sesión persistente con timeout de 3.5s y aislamiento de excepciones por canal fallido.
  4. Implementar el pipeline de persistencia atómica directa en SQLite `communitylab.db`:
     - Detección y descarte de bots/webhooks con telemetría en `_cache_bots_omitidos_discord`.
     - Limpieza y normalización de texto con `limpieza.limpiar_texto`.
     - Cálculo de hash SHA-256 idempotente con `limpieza.calcular_hash`.
     - Verificación de existencia previa en `interacciones` (`hash` o `message_id`).
     - Inserción directa en SQLite (`conn.commit()`).
     - Ecuación contable rigurosa: `total_recibidas == guardadas_nuevas + repetidas_omitidas + vacias_omitidas`.
  5. Desacoplar la replicación a Supabase PostgreSQL:
     - Eliminar completamente `_sincronizar_supabase_a_sqlite()` y `obtener_datos_supabase(forzar=True)` de la ruta de respuesta síncrona.
     - Despachar la persistencia remota mediante `asyncio.create_task` en un hilo de trabajo (`asyncio.to_thread`) protegiendo el tiempo de respuesta del cliente.
  6. En el endpoint `POST /api/v1/discord/sync`:
     - Atender el modo síncrono manual (`asincrono: false`) entregando métricas definitivas completas en < 2.5s.
     - Atender el modo asíncrono (`asincrono: true`) entregando confirmación inmediata en < 100ms.
  7. Ejecutar `pytest` y confirmar que todos los tests de backend pasan en verde (Fase Green TDD).
- **Hecho cuando:** Todos los tests de la Spec 021 y la suite existente de `puente_motor_ia.py` pasan 100% en verde.

---

## [x] T3: Fase Green Frontend — Sincronización Síncrona Manual y Auto-Sync Silencioso en `api/discordSync.ts` y `Messages.tsx` (~20 min)
- **Rol:** `@implementer`
- **Archivos involucrados:**
  - `frontend/src/api/discordSync.ts`
  - `frontend/src/pages/Messages.tsx`
- **Requerimientos Funcionales:** `RF-04`, `RF-05`
- **Descripción:**
  1. En `frontend/src/api/discordSync.ts`:
     - Ajustar la función `syncDiscord` para que respete explícitamente el valor de `asincrono` provisto en los parámetros (por defecto `false` para llamadas manuales, configurable).
     - Tipar adecuadamente los campos de respuesta (`canales_consultados`, `canales_exitosos`, `asincrono`).
  2. En `frontend/src/pages/Messages.tsx`:
     - En `handleSyncDiscord`, despachar `syncDiscord({ asincrono: false })` al pulsar el botón `Sincronizar Discord`.
     - Mostrar estado visual `Sincronizando...`, spinner animado y botón deshabilitado durante la petición (< 2.5s).
     - Al completar exitosamente:
       * Invocar inmediatamente `loadMessages()` para recargar la lista de mensajes y actualizar las 4 tarjetas KPI (`Analizados`, `Positivos`, `Preguntas`, `Destacados`).
       * Mostrar notificación de éxito detallada: `✓ Sincronización exitosa: ${guardadas_nuevas} mensajes nuevos (${repetidas_omitidas} ya existían).`
     - Capturar amigablemente respuestas HTTP 409 (`Sincronización en curso, por favor espera un momento`) mostrando una notificación informativa sin romper la interfaz.
     - Preservar la auto-sincronización silenciosa en segundo plano en el `useEffect` de montaje con `syncDiscord({ asincrono: true }).catch(() => {})`.
  3. Ejecutar `npm run build` en `frontend/` y verificar compilación limpia con código de salida 0.
- **Hecho cuando:** `npm run build` compila con código 0 y la interfaz de Ingesta permite la sincronización manual ultrarrápida con métricas reales inmediatas y mantiene la auto-sincronización silenciosa.

---

## [x] T4: Fase Refactor & Verificación Global de Regresión (~15 min)
- **Rol:** `@implementer`
- **Archivos involucrados:**
  - `tests/test_unificacion_motor_ia.py`
  - `puente_motor_ia.py`
  - `frontend/src/api/discordSync.ts`
  - `frontend/src/pages/Messages.tsx`
- **Requerimientos Funcionales:** `RF-01`, `RF-02`, `RF-03`, `RF-04`, `RF-05`, `RF-06`
- **Descripción:**
  1. Revisar y optimizar la legibilidad del código, asegurando typing estricto, manejo adecuado de recursos y logs informativos limpios.
  2. Ejecutar la suite completa de pruebas unitarias y de integración con `pytest` asegurando que 150+ pruebas pasen en verde.
  3. Ejecutar `npm run build` en `frontend/` validando cero errores de compilación o empaquetado.
  4. Realizar auditoría de `git status` verificando que ninguno de los 17 archivos protegidos de la raíz, `backend/`, `motor-ia/` o `src/` haya sido modificado.
- **Hecho cuando:** La suite completa de `pytest` pasa al 100% en verde, el frontend compila sin errores y `git status` confirma la inviolabilidad absoluta de los archivos protegidos.
