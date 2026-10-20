# Tareas de Implementación — Spec 018: Resiliencia de Publicaciones Multicanal, Diagnóstico de Despacho Real y Manejo de Rate-Limit Discord en la Nube

- [x] **Tarea 1 (Fase Red TDD): Pruebas de integración para captura de HTTP 429 con CORS, emisión bajo `CloudEdTech_Oficial` con `?wait=true`, erradicación de retornos falsos positivos y captura de IDs/URLs en X y LinkedIn**
  - **Archivos:** `tests/test_unificacion_motor_ia.py`
  - **RF Asociados:** RF-001, RF-003, RF-005, RF-006, RF-008, RF-010
  - **Acción:**
    - Escribir `test_sync_discord_captura_rate_limit_429_con_cors` simulando excepción HTTP 429 / Cloudflare 1015 en Discord y verificando que el endpoint `/api/v1/discord/sync` retorne status HTTP 429, cabeceras CORS (`Access-Control-Allow-Origin: *`) y JSON estructurado con `codigo_error: "RATE_LIMIT_CLOUDFLARE_1015"`.
    - Escribir `test_sync_discord_tolera_cuerpo_html_sin_json_decode_error` simulando cuerpo de error en formato HTML de Cloudflare.
    - Escribir `test_despacho_discord_cascada_sin_falsos_positivos` verificando que cuando Bot API y Webhook fallen o sean rechazados, `despachar_discord_con_cascada` retorne estrictamente `ok: False` y `estado_canal: "error"` (sin el retorno falso positivo previo).
    - Escribir `test_despacho_discord_webhook_anexa_wait_true_y_obtiene_message_id` verificando que las llamadas salientes a webhooks de Discord bajo `CloudEdTech_Oficial` incluyan `?wait=true` y procesen el `message_id`.
    - Escribir `test_adaptadores_autonomos_x_y_linkedin_capturan_ids_y_urls_canonicas` simulando respuestas exitosas y verificando la captura del ID numérico de tweet (`https://x.com/CloudEdTech_1/status/{id}`) y del URN de LinkedIn (`https://www.linkedin.com/feed/update/{urn}`).
    - Escribir `test_publish_channel_no_persiste_en_sqlite_ante_fallo_de_canal` verificando que si el despacho falla, no se actualice `interacciones` ni `contenidos_generados` a estado publicado.
  - **Hecho cuando:** La ejecución de `pytest tests/test_unificacion_motor_ia.py -k "rate_limit or false_positive or wait_true or adaptadores"` falle de forma controlada (Fase Red) debido a la ausencia de estas adaptaciones en `puente_motor_ia.py`.

- [x] **Tarea 2 (Fase Green Backend): Captura defensiva de Rate Limits (HTTP 429 / Cloudflare 1015) y tolerancia HTML en sincronización de Discord**
  - **Archivos:** `puente_motor_ia.py`
  - **RF Asociados:** RF-001, RF-002
  - **Acción:**
    - Crear función auxiliar defensiva `_formatear_respuesta_rate_limit(error_o_codigo, detalle_contextual)` que detecte status 429 o textos de Cloudflare/Discord sin invocar `json.loads` sobre respuestas HTML, garantizando cabeceras CORS explícitas (`Access-Control-Allow-Origin: *`) y el JSON canónico con `codigo_error: "RATE_LIMIT_CLOUDFLARE_1015"`.
    - En `sync_discord_v1` y `_ejecutar_sincronizacion_discord`, envolver la ejecución en captura de excepciones (`discord.errors.HTTPException`, `discord.errors.DiscordException`, `aiohttp.ClientResponseError`, `Exception`) retornando deterministamente la respuesta 429 ante rate limits.
  - **Hecho cuando:** `test_sync_discord_captura_rate_limit_429_con_cors` y `test_sync_discord_tolera_cuerpo_html_sin_json_decode_error` pasen en verde.

- [x] **Tarea 3 (Fase Green Backend): Emisión unificada bajo `CloudEdTech_Oficial` con `?wait=true` en Anuncios y Quejas**
  - **Archivos:** `puente_motor_ia.py`
  - **RF Asociados:** RF-003, RF-004, RF-008, RF-010
  - **Acción:**
    - En `publish_announcement_v1`: canalizar el despacho hacia el webhook oficial de `CloudEdTech_Oficial` (`DISCORD_WEBHOOK_ANUNCIOS`), garantizando que la URL contenga el parámetro `?wait=true`. Si se solicita canal directo por Bot API y falla con 429 / 1015, conmutar inmediatamente al webhook oficial tolerando respuestas HTML sin `JSONDecodeError`. Si ambos fallan, retornar status 429 estructurado con CORS.
    - En `publicar_respuesta_queja_v1` y `_enviar_reply_discord`: canalizar la respuesta hacia el webhook de soporte/PQRS configurado bajo `CloudEdTech_Oficial` con `?wait=true`. Ante errores 429 de Discord, retornar status 429 estructurado con CORS sin romper la transacción de la queja.
    - Preservar al bot de lectura (`DISCORD_TOKEN`) enfocado exclusivamente en la ingesta pasiva de mensajes.
  - **Hecho cuando:** `test_despacho_discord_webhook_anexa_wait_true_y_obtiene_message_id` y las pruebas de anuncios/quejas pasen en verde.

- [x] **Tarea 4 (Fase Green Backend): Erradicación de falsos positivos y adaptadores autónomos para X, LinkedIn y Discord**
  - **Archivos:** `puente_motor_ia.py`
  - **RF Asociados:** RF-005, RF-006, RF-009, RF-010
  - **Acción:**
    - En `despachar_discord_con_cascada`: suprimir definitivamente el retorno incondicional de falso positivo. Despachar vía webhook de `CloudEdTech_Oficial` con `?wait=true` (o Bot API) y exigir status 200/201 con `id` devuelto. Si falla o no hay credenciales válidas, retornar estrictamente `ok: False, estado_canal: "error"` con el detalle real.
    - En `despachar_x_resiliente`: implementar adaptador autónomo en el puente que interactúe con Tweepy v2, capture el `tweet_id` numérico devuelto por `client.create_tweet` y genere la URL canónica `https://x.com/CloudEdTech_1/status/{id}`. Si falla, retornar `ok: False, estado_canal: "error"`.
    - En `despachar_linkedin_resiliente`: implementar adaptador autónomo en el puente hacia `ugcPosts`, capture el URN del post generado (HTTP 201) y genere la URL canónica `https://www.linkedin.com/feed/update/{urn}`. Si falla, retornar `ok: False, estado_canal: "error"`.
    - En `api_mototradis_publish_channel` y `api_mototradis_hitl_decision`: condicionar la persistencia en `contenidos_generados` y la actualización de `interacciones` estrictamente a que el canal haya obtenido `estado_canal == "enviado"`, e inyectar las URLs canónicas devueltas en la respuesta.
    - Confirmar que `src/publishers.py` permanezca 100% inalterado.
  - **Hecho cuando:** `test_despacho_discord_cascada_sin_falsos_positivos`, `test_adaptadores_autonomos_x_y_linkedin_capturan_ids_y_urls_canonicas` y `test_publish_channel_no_persiste_en_sqlite_ante_fallo_de_canal` pasen en verde.

- [x] **Tarea 5: Frontend Ingesta de Mensajes (`Messages.tsx` y `client.ts`)**
  - **Archivos:** `frontend/src/api/client.ts`, `frontend/src/pages/Messages.tsx`
  - **RF Asociados:** RF-001, RF-002
  - **Acción:**
    - En `frontend/src/api/client.ts`: extraer prioritariamente `error.detail || error.mensaje || message` para preservar mensajes de error devueltos ante HTTP 429 / 502 sin ser suplantados por strings genéricos.
    - En `frontend/src/pages/Messages.tsx`: en `handleSyncDiscord`, interceptar respuestas de error HTTP 429 o menciones a Cloudflare 1015 / Rate Limit, desplegando un banner informativo de advertencia con el texto amigable exacto: *"Discord o Cloudflare ha limitado temporalmente la IP del servidor en la nube (Error 1015 / Rate Limit). Sincroniza desde tu entorno local o intenta en unos minutos."*. Restaurar el estado `isSyncingDiscord = false` de inmediato sin crasheos.
  - **Hecho cuando:** `npm run build` en `frontend/` compile con código 0 y la interfaz de mensajes maneje limpiamente el rate limit sin reportar `Failed to fetch`.

- [x] **Tarea 6: Frontend Redacción de Contenidos (`ContentStudio.tsx`)**
  - **Archivos:** `frontend/src/pages/ContentStudio.tsx`
  - **RF Asociados:** RF-004, RF-005, RF-006, RF-007, RF-008
  - **Acción:**
    - Panel de Anuncios: capturar errores 429 de Cloudflare y mostrar el banner explicativo preservando el contenido en el editor.
    - Panel de Quejas: capturar 429 de Discord y mostrar notificación clara al operador sin colapsar el formulario de respuesta.
    - Mesa de Trabajo Multicanal (Individual y HITL):
      * Marcar tarjetas con `✓ Publicado en {Red}` e inhabilitar botón únicamente cuando `res.ok && res.estado_canal === 'enviado'`.
      * Si un canal falla (`estado_canal === 'error'`), mantener la tarjeta editable, desplegar banner de error rojo con el detalle técnico exacto devuelto por la API y habilitar botón de reintento (`Reintentar publicación en {Red}`).
      * Mostrar el enlace directo verificado provisto por el backend (URL canónica a X o LinkedIn).
      * En decisiones HITL colectivas, manejar publicaciones parciales: marcar en verde únicamente los canales exitosos y habilitar el reintento de los canales fallidos sin duplicar los exitosos.
  - **Hecho cuando:** `npm run build` en `frontend/` compile sin errores de tipado TypeScript y la mesa de trabajo refleje fidelidad visual ante fallos y reintentos.

- [x] **Tarea 7: Verificación Global, Compilación E2E e Inviolabilidad Constitucional**
  - **RF Asociados:** RF-009, RF-010 y Criterios de Aceptación
  - **Acción:**
    - Ejecutar suite completa `pytest tests/test_unificacion_motor_ia.py` verificando el 100% de pruebas en verde.
    - Ejecutar `npm run build` en `frontend/` confirmando 0 advertencias o errores de compilación.
    - Ejecutar `git status` y `git diff` verificando inmutabilidad estricta de los 17 archivos protegidos de la raíz, la carpeta `src/` (con énfasis en `src/publishers.py`), `backend/` y `motor-ia/`.
    - Actualizar `MEMORY.md` con los avances de la Spec 018.
  - **Hecho cuando:** La suite completa de backend y el build de frontend finalicen con código de salida 0 y el árbol git cumpla rigurosamente con la Constitución.
