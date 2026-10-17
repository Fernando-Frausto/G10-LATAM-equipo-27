# Tareas de Implementación: Spec 007
## Sincronización de Discord desde la UI y Flujo Integral de Extremo a Extremo

---

### [x] Tarea 1: Fase Red TDD — Pruebas Automatizadas con Mocks
- **RF Asociado:** RF-01, RF-02, RF-03, RF-06
- **Estimación:** ~20 minutos
- **Archivos a modificar:** `tests/test_unificacion_motor_ia.py`
- **Descripción:**
  Escribir la batería de pruebas unitarias y de integración simuladas en `tests/test_unificacion_motor_ia.py` cubriendo la totalidad de requerimientos del backend antes de implementar el código:
  1. `test_discord_sync_endpoint_exitoso`: Mockea `discord.Client` y valida llamada a `POST /api/v1/discord/sync`, verificando que se devuelvan los conteos de mensajes, código HTTP 200 y se persistan en base de datos.
  2. `test_discord_sync_concurrencia_lock_409`: Simula el estado bloqueado de `_discord_sync_lock` y comprueba que una petición concurrente a `POST /api/v1/discord/sync` retorne inmediatamente HTTP 409 Conflict con cuerpo `{"exito": false, "mensaje": "Sincronización en curso", "detail": "Sincronización en curso"}`.
  3. `test_discord_sync_token_ausente_o_login_failure_502`: Simula ausencia de `DISCORD_BOT_TOKEN` o excepción `discord.errors.LoginFailure`, verificando que retorne HTTP 502 Bad Gateway sin tumbar la aplicación.
  4. `test_discord_sync_todos_al_dia_y_sin_canales`: Valida que cuando no existan mensajes nuevos retorne HTTP 200 con `guardadas_nuevas: 0` y mensaje `"Todos los mensajes están al día"`, y cuando no haya canales autorizados retorne el mensaje descriptivo correspondiente.
  5. `test_discord_recover_endpoint`: Valida `POST /api/v1/discord/recover` con carga de mensajes históricos, verificando cálculo de hash SHA-256, asignación de etapa `'ingesta'` y estado `'pendiente'`, y respuesta HTTP 200 estructurada.
  6. `test_discord_recovery_preview_alias`: Comprueba que `/api/v1/content-workflow/discord/recovery-preview` y `/api/v1/discord/recovery-preview` expongan la misma respuesta.
  7. `test_evaluate_batch_solo_pendientes_blindaje_dual`: Valida que al enviar `solo_pendientes=True` a `POST /api/v1/ai/evaluate-batch`, se consulten y excluyan los IDs ya evaluados tanto en Supabase como en SQLite local (`communitylab.db`).
- [x] **Hecho cuando:**
  Al ejecutar `pytest tests/test_unificacion_motor_ia.py -k "discord or evaluate_batch_solo_pendientes"`, las nuevas pruebas fallen de forma controlada y esperada (estado RED) al no estar aún implementados los endpoints ni el cerrojo en `puente_motor_ia.py`.

---

### [x] Tarea 2: Implementación Backend en `puente_motor_ia.py` (Fase Green)
- **RF Asociado:** RF-01, RF-03, RF-05, RF-06
- **Estimación:** ~20 minutos
- **Archivos a modificar:** `puente_motor_ia.py`
- **Descripción:**
  Implementar los endpoints y mecanismos en `puente_motor_ia.py` sin alterar ninguno de los 17 archivos preexistentes:
  1. Instanciar `_discord_sync_lock = asyncio.Lock()`.
  2. Implementar endpoint `POST /api/v1/discord/sync`:
     - Validación preventiva de concurrencia con `_discord_sync_lock.locked()` retornando HTTP 409 Conflict si está ocupado.
     - Extracción segura del token de entorno (`DISCORD_BOT_TOKEN` o `DISCORD_TOKEN`), retornando HTTP 502 Bad Gateway si falta o falla el login.
     - Creación de cliente efímero `discord.Client` ejecutado en el bucle de eventos con `asyncio.wait_for(..., timeout=30.0)` y cierre forzado en bloque `finally`.
     - Reutilización de `armar_json_bot_python.detectar_canales`, `construir_paquete` y `procesamiento.procesar_actividad`.
     - Persistencia dual en Supabase y sincronización a SQLite local mediante `_sincronizar_supabase_a_sqlite()`.
     - Retorno de estructura estándar con métricas, respetando los casos de mensajes al día (0 nuevos) y ausencia de canales.
  3. Implementar endpoint `POST /api/v1/discord/recover`:
     - Validación del payload `mensajes: [...]`.
     - Limpieza e inserción idempotente con hash SHA-256 en etapa `'ingesta'` y estado `'pendiente'`.
     - Respuesta estructurada con `guardados_nuevos` y `repetidos_omitidos`.
  4. Configurar alias idénticos para previsualización en `/api/v1/content-workflow/discord/recovery-preview` y `/api/v1/discord/recovery-preview`.
  5. Crear la función `_obtener_ids_evaluados_dual()` que consulte de forma segura tanto Supabase (`lotes_ia_kpis`) como SQLite local (`interacciones WHERE estado = 'analizado' OR relevancia IS NOT NULL`), aplicándola en `evaluate_batch_v1` cuando `solo_pendientes=True`.
- [x] **Hecho cuando:**
  Al ejecutar `pytest tests/test_unificacion_motor_ia.py`, todas las pruebas diseñadas en la Tarea 1 pasen al 100% en verde (GREEN), sin regresión en las pruebas preexistentes.

---

### [x] Tarea 3: Cliente API en Frontend y Habilitación de Recuperación Histórica
- **RF Asociado:** RF-03, RF-04
- **Estimación:** ~20 minutos
- **Archivos a modificar:**
  - `frontend/src/api/discordSync.ts` (nuevo archivo)
  - `frontend/src/components/RecoverDiscordMessagesModal.tsx`
  - `frontend/src/pages/Approvals.tsx`
- **Descripción:**
  1. Crear `frontend/src/api/discordSync.ts`:
     - Definir tipos TypeScript: `DiscordSyncParams`, `DiscordSyncResponse`, `DiscordRecoverItem`, `DiscordRecoverPayload`, `DiscordRecoverResponse`.
     - Exportar `syncDiscord(params?: DiscordSyncParams)` invocando `POST /api/v1/discord/sync` con manejo de errores 409 y 502.
     - Exportar `recoverDiscordMessages(payload: DiscordRecoverPayload)` invocando `POST /api/v1/discord/recover`.
  2. Modificar `RecoverDiscordMessagesModal.tsx`:
     - Añadir soporte para callback `onRecovered?: () => void` en `Props`.
     - Habilitar el botón "Recuperar seleccionados" cuando `selected.length > 0`, mostrando indicador de carga durante el proceso (`isRecovering`).
     - Al confirmar la recuperación con `recoverDiscordMessages`:
       - Actualizar localmente los mensajes seleccionados marcándolos como `recuperado: true` con etiqueta "Ya recuperado".
       - Desmarcar y limpiar la lista de selección.
       - Disparar `onRecovered?.()` para refrescar de forma reactiva la bandeja en la pantalla principal.
  3. En `Approvals.tsx`: asegurar que la invocación a `RecoverDiscordMessagesModal` pase el callback para recargar la lista ante recuperaciones exitosas.
- [x] **Hecho cuando:**
  El modal permita seleccionar mensajes y hacer clic en "Recuperar seleccionados", enviando la petición al backend, actualizando su estado a "Ya recuperado" y notificando a la vista padre para refrescar su información.

---

### [x] Tarea 4: Contador Reactivo Dinámico, Validación Preventiva y Botón de Sincronización en `Messages.tsx`
- **RF Asociado:** RF-02, RF-04
- **Estimación:** ~20 minutos
- **Archivos a modificar:** `frontend/src/pages/Messages.tsx`
- **Descripción:**
  1. Integrar el botón "📥 Sincronizar Discord":
     - Incorporarlo en la sección superior de acciones junto a la evaluación por lotes.
     - Estado reactivo `isSyncingDiscord` con spinner de carga (`RefreshCw animate-spin`).
     - Al hacer clic: invocar `syncDiscord()`, desplegar notificación con las métricas recibidas (`mensaje`), alertar adecuadamente ante HTTP 409 ("Sincronización en curso") y refrescar automáticamente la tabla con `loadMessages()`.
  2. Implementar el Contador Dinámico Reactivo (Paridad con Streamlit):
     - Calcular mediante `useMemo` en vivo según `dateFrom`, `dateTo`, `onlyPending` y la lista de mensajes:
       - Total de mensajes coincidentes con el rango de fechas.
       - Subtotal de mensajes pendientes de evaluar.
       - Cantidad evaluable neta según el estado de la casilla "Solo pendientes de evaluar".
       - Detección de error cronológico (`dateFrom > dateTo`).
     - Renderizar el banner informativo dinámico en la UI: `📊 X mensajes disponibles para evaluar (Y pendientes)`.
  3. Blindaje y Deshabilitación Preventiva:
     - Mostrar aviso contextual informativo cuando el conteo evaluable sea 0 o cuando `dateFrom > dateTo`.
     - Deshabilitar el botón "Evaluar mensajes con IA" si el conteo evaluable es 0, si hay error de fechas o durante la ejecución (`isEvaluatingBatch`).
- [x] **Hecho cuando:**
  En `Messages.tsx`, al cambiar las fechas o la casilla "Solo pendientes", el contador se actualice en tiempo real; si no hay mensajes o las fechas son inválidas, se muestre el aviso informativo y el botón de evaluación se deshabilite inmediatamente; y el botón de sincronización ejecute la extracción con spinner y refresco automático.

---

### [x] Tarea 5: Verificación Global de Regresión, Compilación e Inmutabilidad
- **RF Asociado:** RF-05, RF-06
- **Estimación:** ~20 minutos
- **Archivos a inspeccionar:**
  - Raíz del proyecto (17 archivos inmutables)
  - `tests/`
  - `frontend/`
- **Descripción:**
  1. Ejecutar la suite completa de pruebas en Python con `pytest tests/ -v`, verificando que la totalidad de pruebas (anteriores y nuevas) pasen al 100% en verde sin errores ni warnings críticos.
  2. Ejecutar la compilación estricta de TypeScript en `frontend/` (`npm run build`), asegurando cero errores de sintaxis, tipos o empaquetado.
  3. Ejecutar verificación de estado de Git (`git status`) y confirmar que **NINGUNO** de los 17 archivos preexistentes de la raíz (`api.py`, `app.py`, `armar_json_bot_python.py`, `base_datos.py`, `bot_lote.py`, etc.) haya sufrido modificaciones.
- [x] **Hecho cuando:**
  `pytest tests/` reporte 100% de tests aprobados, `npm run build` finalice con código de salida 0, y `git status` certifique que solo se han creado o modificado archivos dentro de `specs/`, `puente_motor_ia.py`, `frontend/src/` y `tests/`.
