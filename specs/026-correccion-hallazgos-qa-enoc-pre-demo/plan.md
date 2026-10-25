# Plan Técnico 026: Corrección Integral de Hallazgos QA (Enoc) Pre-Demo Day

## 1. Arquitectura General y Regla de Oro de Alta Velocidad

Toda la solución se diseñará bajo dos pilares arquitectónicos inquebrantables:

1. **Aislamiento Constitucional Estricto (RNF-01):**
   - **Prohibido modificar:** Los 17 archivos preexistentes de la raíz (`cerebro_ia.py`, `cerebro_ia_gemma.py`, `evaluador_lotes.py`, `base_datos.py`, `modelos.py`, `procesamiento.py`, `limpieza.py`, `app.py`, `api.py`, etc.), `backend/`, `motor-ia/` y `src/`.
   - **Superficie de cambio autorizada:** Exclusivamente `puente_motor_ia.py` (adaptador backend), `frontend/src/pages/Messages.tsx` y `frontend/src/pages/ContentStudio.tsx` (interfaz React), y `tests/test_unificacion_motor_ia.py` (suite TDD).

2. **Preservación Absoluta de Alta Velocidad (`< 2 ms` en Lecturas, Cero Bloqueo del Event Loop — RNF-02):**
   - **Lecturas GET ultrarrápidas:** `GET /api/community/messages`, `GET /api/community/analytics` y `GET /api/v1/oci-storage/reports` continuarán respondiendo en `< 2 ms` desde SQLite indexado o caché en memoria sin ejecutar jamás llamadas de red bloqueantes a Discord ni a Supabase WAN.
   - **Mutaciones instantáneas con réplica asíncrona:** Al descartar o restaurar un mensaje (`PATCH /api/v1/content-workflow/messages/{interaction_id}/curation`), la escritura local en SQLite se completará en `< 2 ms` y la actualización hacia `public.lotes_ia_kpis` en Supabase se delegará a segundo plano mediante `asyncio.create_task(asyncio.to_thread(...))`, eliminando la conexión bloqueante `psycopg2.connect` que antes retenía la respuesta HTTP.
   - **Evaluación IA fuera del Event Loop:** En `evaluate_batch_v1` y `evaluate_single_message_v1`, la llamada a `evaluador_lotes.evaluar_lote` y la sincronización posterior se ejecutarán mediante `await asyncio.to_thread(...)`, permitiendo que FastAPI atienda peticiones concurrentes de Dashboard, Ingesta y Análisis en `< 2 ms` incluso mientras un lote de IA está procesándose.

---

## 2. Diseño Técnico Detallado por Requisito Funcional

### 2.1. RF-01: Persistencia de descarte y restauración manual en Ingesta

- **En `puente_motor_ia.py`:**
  1. **`actualizar_curaduria_puente(interaccion_id: int, estado_curaduria: str)`:**
     - Consultar en SQLite local (`interacciones`) si el mensaje ya está analizado (`estado = 'analizado'` o `relevancia IS NOT NULL` con `relevancia > 0`).
     - Si el operador solicita restaurar (`estado_curaduria in ('pending', 'curated')`) un mensaje que estaba en `'discarded'`:
       - Si el mensaje ya está analizado (`estado == 'analizado'`), persistir `estado_curaduria = 'curated'` (para que pase directamente a elegible en bandeja de publicación).
       - Si el mensaje aún no ha sido analizado, persistir `estado_curaduria = 'pending'` y `etapa_flujo = 'ingesta'`.
     - Si el operador solicita descartar (`estado_curaduria == 'discarded'`), persistir inmediatamente `estado_curaduria = 'discarded'` en SQLite local.
     - Invalidar la caché en memoria (`invalidar_cache_analytics()`) sin forzar un re-pull síncrono desde Supabase que pise el cambio ni bloquee el request.
     - Reemplazar la llamada bloqueante `psycopg2.connect` dentro de `actualizar_curaduria_puente` por una función auxiliar `_replicar_curaduria_supabase_bg(interaccion_id, estado_sb)` despachada en segundo plano vía `asyncio.create_task(asyncio.to_thread(...))` (o hilo daemon si no hay event loop activo). Si el mensaje aún no existe en `public.lotes_ia_kpis` (`0 rows affected`), se ignora silenciosamente sin lanzar excepción.
  2. **`_obtener_ids_evaluados_dual()`:**
     - En la consulta SQLite sobre `interacciones`, incluir `OR estado_curaduria = 'discarded'` (`SELECT id FROM interacciones WHERE estado = 'analizado' OR relevancia IS NOT NULL OR estado_curaduria = 'discarded'`). Así, los mensajes descartados manualmente por el operador quedan excluidos de la cola de pendientes al ejecutar `evaluate_batch_v1(solo_pendientes=True)`.
  3. **`_sincronizar_supabase_a_sqlite(datos_sb)`:**
     - Reforzar la preservación de decisiones humanas locales: si `iid in locales` y `cur_loc in ('discarded', 'curated')`, preservar siempre `estado_curaduria = cur_loc` a menos que en Supabase ya figure como `'publicado'`/`'aprobado'` con contenido publicado. En particular, si el operador descartó manualmente (`cur_loc == 'discarded'`) o restauró (`cur_loc == 'pending'` / `'curated'`), ninguna resincronización posterior de Supabase revertirá esa decisión.

- **En `frontend/src/pages/Messages.tsx`:**
  - En `markCuration(message, status)`: cuando el operador pulsa "Restaurar", si `message.isAnalyzed` es `true`, enviar `'curated'` (o actualizar el estado local con el `curation_status` devuelto por el backend: `'curated'` si analizado, `'pending'` si no analizado), mostrando feedback claro al usuario y permitiendo tanto descartar como restaurar sin recargar la página.

---

### 2.2. RF-02: Sincronización de ID canónico y prevención de doble registro al evaluar mensajes nuevos

- **En `puente_motor_ia.py`:**
  1. **Adopción atómica del ID canónico en `_sincronizar_discord_api_rest` y `recover_discord_messages_v1`:**
     - Al insertar un mensaje nuevo en SQLite local y replicarlo a `public.interacciones` de Supabase (`_base_datos_raiz.guardar_interaccion`), o durante `_sincronizar_supabase_a_sqlite`:
     - Cuando `_replicar_a_supabase` inserta o consulta en `public.interacciones` por `hash`, recuperar el `id` canónico asignado por Supabase (`SELECT id FROM public.interacciones WHERE hash = %s`) y reconciliar atómicamente en SQLite local cualquier fila con el mismo `hash` cuyo `id` local temporal difiera del `id` canónico de Supabase (eliminando el registro temporal previo antes del `INSERT OR REPLACE` o actualizando su `id` en transacción atómica para evitar colisiones `UNIQUE PRIMARY KEY` o `UNIQUE hash`).
  2. **Vinculación dual de KPIs (`id_mensaje` + `hash` / `(autor, texto_original)`) en `_sincronizar_supabase_a_sqlite`:**
     - Construir además de `kpis_map` (por `id_mensaje`), un índice secundario `kpis_por_hash_o_texto` indexado por `hash` (`limpieza.calcular_hash(...)`) y por tupla normalizada `(autor.strip().lower(), texto_original.strip())`.
     - Al recorrer `interacciones_raw` (y las interacciones locales en SQLite que aún no hayan terminado de sincronizar), si no hay match directo por `iid` en `kpis_map`, buscar en `kpis_por_hash_o_texto`.
     - Asimismo, antes de eliminar en el paso final de `_sincronizar_supabase_a_sqlite` (`DELETE FROM interacciones WHERE id NOT IN (...)`), preservar las interacciones locales recién sincronizadas (o reconciliarlas por `hash` con las de Supabase) para que nunca desaparezcan ni pierdan su análisis si fueron evaluadas inmediatamente después de sincronizar Discord.
  3. **Prevención de doble fila en `public.lotes_ia_kpis` y actualización al primer clic en `evaluate_single_message_v1` y `evaluate_batch_v1`:**
     - Antes de invocar `evaluador_lotes.evaluar_lote`, asegurar que si la interacción existe en SQLite pero aún no tiene su ID canónico sincronizado en `public.interacciones`, se sincronice/obtenga su ID canónico en `public.interacciones` por `hash` y se actualice `msg_dict["id"]` e `interacciones.id` en SQLite.
     - Tras obtener `resultado_eval`, verificar que la persistencia en `public.lotes_ia_kpis` sea idempotente (evitando insertar una segunda fila si `evaluar_lote` ya la guardó o si ya existía un registro para ese `id_mensaje` / `(autor, texto_original)`, deduplicando en caso necesario).
     - Actualizar inmediatamente la fila en SQLite local (`estado = 'analizado'`, `relevancia`, `sentimiento`, `estado_curaduria`, `etapa_flujo = 'en_analisis'`) e invalidar la caché de lecturas sin permitir que `_sincronizar_supabase_a_sqlite()` pise los KPIs recién calculados con una caché vieja.

---

### 2.3. RF-03: Claridad visual de la Matriz Multi-LLM y Fallbacks del Orquestador en `ContentStudio.tsx`

- **En `puente_motor_ia.py`:**
  - Actualizar `MODELOS_UTILIZADOS_CATALOGO` para reflejar con total exactitud la matriz real definida por Enoc en `src/nodes.py`:
    - `"orquestador"`: `"Groq · qwen/qwen3.8-27b (Fallback: Gemini 3.6 Flash)"`
    - `"linkedin"`: `"Google Gemini · gemini-3.5-flash-lite (Fallback: Gemini 3.1 Flash Lite)"`
    - `"x"`: `"Google Gemini · gemini-3.5-flash-lite (Fallback: Gemini 3.1 Flash Lite)"`
    - `"discord"`: `"Groq · openai/gpt-oss-120b (Fallback: Gemini 3.1 Flash Lite)"`
    - `"pqrs"`: `"Groq · qwen/qwen3.8-27b (Fallback: Gemini 3.1 Flash Lite)"`
    - `"masivo"`: `"Google Gemma 4 · gemma-4-31b-it (Fallback: gemma-4-26b-a4b-it)"`
- **En `frontend/src/pages/ContentStudio.tsx`:**
  - En la cabecera de la **Mesa de Trabajo Multicanal (Orquestador LangGraph)**:
    - Mostrar un bloque/insignia informativa clara detallando la **Matriz Multi-LLM Automática del Pipeline LangGraph**:
      - Orquestador y PQRS: `Qwen 3.8 27B` → Fallback `Gemini 3.6 / 3.1 Flash`
      - Discord: `GPT-OSS 120B` → Fallback `Gemini 3.1 Flash Lite`
      - LinkedIn y X: `Gemini 3.5 Flash Lite` → Fallback `Gemini 3.1 Flash Lite`
    - Cambiar la etiqueta del selector manual de `"Fallback IA:"` a **`"IA Regeneración Individual:"`** con `title` explicativo (`"Este selector aplica exclusivamente al pulsar 'Regenerar' dentro de un canal individual (LinkedIn, X o Discord). El botón 'Ejecutar Pipeline (LangGraph)' utiliza siempre la matriz Multi-LLM automática del orquestador."`).

---

### 2.4. RF-04: Estructura JSON completa en `public.historial_reportes_semanales`

- **En `puente_motor_ia.py` (`construir_registro_historial_reporte`, `api_mototradis_hitl_decision` y `api_mototradis_publish_channel`):**
  1. **Enriquecimiento de `contenido_original` (`json_precurado` completo):**
     - Si `interaccion` no trae todos los campos analíticos (`relevancia`, `sentimiento`, `temas_clave`, `segmento`, `razonamiento`, `estado_curaduria`, `origen_comunidad`, `periodo_referencia`), consultarlos de forma ultrarrápida desde SQLite local (`SELECT * FROM interacciones WHERE id = ?`).
     - Construir `contenido_original` incluyendo todas las llaves canónicas de `json_precurado`:
       - `id_mensaje`: `int(id_mensaje)` si es numérico, o `id_msg_str`
       - `autor`: `autor_final`
       - `canal_origen`: `canal_origen_val` (con alias `canal` preservado para retrocompatibilidad)
       - `comunidad`: `origen_comunidad` (`"Discord_Grupo_ONE_G10"` / `"Discord"`)
       - `semana`: `semana_final`
       - `texto_original`: `txt_orig` (con alias `texto` preservado para retrocompatibilidad con Spec 024)
       - `relevancia`: entero `0–100` (ej. `70`, idéntico a `public.lotes_ia_kpis` y `src/database.py`)
       - `sentimiento`: `sentimiento_val` (ej. `"Positivo"`, `"Neutral"`, `"Negativo"`)
       - `temas_clave`: lista de strings (ej. `["#sql", "#empleo"]`)
       - `segmento`: `segmento_val` (ej. `"General"`, `"Estudiante"`, etc.)
       - `razonamiento`: `razonamiento_val`
       - `decision_ia`: `"PUBLICAR"` si `relevancia >= 35` else `"DESCARTAR"`
       - `estado_revision`: `"aprobado"`
  2. **Enriquecimiento de `copys_generados` indexado por canal activo/publicado (`"discord"`, `"linkedin"`, `"x"`, `"reclamos"`):**
     - Crear una función auxiliar `_normalizar_copy_canal_completo(canal, data_canal, interaccion_dict, f_envio, f_extraccion, semana_final)` que garantice que cada canal en `copys_generados` posea simultáneamente:
       - El árbol completo definido en `src/schemas.py`:
         - `status`: `"exito"`
         - `resumen_comunidad`: `{"total_interacciones_procesadas": 1, "sentimiento_predominante": ..., "temas_principales": [...], "programa": "CloudEDTech"}`
         - `activos_distribucion_generados`:
           - Para `"linkedin"`: `post_linkedin` (`titulo`, `texto_copy`, `canal_recomendado`, `potencial_engagement`), `destaque_newsletter_semanal` (`seccion`, `titular`, `resumen`), `sugerencia_contenido_faq` (`tema`, `origen`, `status`), `temporalidad_producto_creado` (`fecha_envio`, `fecha_extraccion`, `semana`).
           - Para `"x"`: `post_postx` (`titulo`, `texto_copy`, `canal_recomendado`, `potencial_engagement`), `temporalidad_producto_creado` (`fecha_envio`, `fecha_extraccion`, `semana`).
           - Para `"discord"`: `canal_seleccionado`, `post_discord` / `post_discord_faq` / `post_discord_notificaciones` según el canal seleccionado (`titulo`, `texto_copy`, `canal_recomendado`, `potencial_engagement`, `origen`, `status`), `temporalidad_producto_creado` (`fecha_envio`, `fecha_extraccion`, `semana`).
           - Para `"reclamos"`: `post_discord_pqrs` (`titulo`, `texto_copy`, `canal_recomendado`, `potencial_engagement`, `origen`, `status`), `temporalidad_producto_creado`.
       - **Retrocompatibilidad garantizada con Spec 024 (OCI):** Mantener en la raíz del objeto de cada canal las llaves `titulo`, `texto_copy` y `plataforma` reflejando los textos definitivos (incluyendo cualquier edición humana HITL).

---

### 2.5. RF-05: Deduplicación del contador de Bots Omitidos en Sincronización Discord

- **En `puente_motor_ia.py`:**
  - Declarar a nivel de módulo el conjunto en memoria `_ids_bots_omitidos_vistos: set[str] = set()`.
  - En `_sincronizar_discord_api_rest` y en `_ejecutar_sincronizacion_discord`:
    - Al detectar un mensaje de bot o webhook (`is_bot == True`), obtener su identificador único `bot_msg_id = str(m_raw.get("id") or "")` (o `str(getattr(m, "id", "") or "")`).
    - Incrementar `bots_nuevos_detectados` y añadir a `_ids_bots_omitidos_vistos` **únicamente si** `bot_msg_id` no estaba ya en `_ids_bots_omitidos_vistos`.
    - Sumar a `_cache_bots_omitidos_discord` únicamente `bots_nuevos_detectados` (de modo que re-sincronizar los mismos mensajes incremente `0`).
    - Incluir `"bots_omitidos": bots_nuevos_detectados` y `"total_bots_omitidos": _cache_bots_omitidos_discord` en el diccionario de retorno de `_sincronizar_discord_api_rest`.

---

### 2.6. RF-06: Alineación del umbral de relevancia con las 4 Prioridades del Orquestador (`35%–69%`)

- **En `puente_motor_ia.py`:**
  1. Crear una función auxiliar determinista `_es_spam_prioridad_4(relevancia: int | float, texto: str, razonamiento: str = "") -> bool`:
     - Retorna `True` si `relevancia <= 10`, o si `len(texto.strip()) < 3`, o si `"select"` o `"credenciales"` aparecen en `texto.lower()` o `razonamiento.lower()` (alineado con Prioridad 4 de `src/nodes.py` y `src/database.py`).
  2. En `_sincronizar_supabase_a_sqlite`, `evaluate_batch_v1` y `evaluate_single_message_v1`:
     - Al determinar `estado_curaduria` de un mensaje analizado cuando `st_rev` es `'pendiente'` o `'rechazado'` (y el operador NO lo descartó manualmente en SQLite local):
       - Si `relevancia >= 35` y `not _es_spam_prioridad_4(relevancia, texto, razonamiento)`: asignar `estado_curaduria = 'curated'` (para que los mensajes de Prioridad 1 `>= 70%` y Prioridad 2 `35%–69%`, incluyendo anuncios de `#notificaciones` de 60% y 68%, queden habilitados para publicación).
       - Si `relevancia < 35` o `_es_spam_prioridad_4(...)`: asignar `estado_curaduria = 'discarded'`.
  3. En `_cargar_lote_consolidado_para_reporte` y `_obtener_descartados_semana_sqlite`:
     - Ajustar el umbral de descarte automático por relevancia de `rel < 70` a `rel < 35 or _es_spam_prioridad_4(rel, texto, razonamiento)`.
- **En `frontend/src/pages/Messages.tsx` y `frontend/src/pages/ContentStudio.tsx`:**
  - En `Messages.tsx` (`filteredMessages`, `batchEvalMetrics`, `handleEvaluateSingleMessage`, tarjetas de mensaje):
    - Actualizar el umbral de descarte automático de `relevance < 70` a `relevance < 35` (o presencia de bloqueo de Prioridad 4), de modo que los mensajes analizados con `relevancia >= 35%` (como los de 60% y 68% en `#notificaciones`) se clasifiquen en **`Pendientes de publicar`** (`pending_copy`) y muestren el botón de pasar a redacción / generar copy.
  - En `ContentStudio.tsx` (`loadWorkflowMessages`):
    - Actualizar el filtro de la Bandeja de Entrada de `item.analysis.relevance >= 70` a `(item.analysis.relevance >= 35 || item.analysis.curation_status === 'curated') && item.analysis.curation_status !== 'discarded'`.

---

### 2.7. RF-07: Ejecución no bloqueante en hilo separado y envoltorio resiliente thread-safe para Google Gemma 4

- **En `puente_motor_ia.py`:**
  1. **Desacoplamiento asíncrono con `await asyncio.to_thread(...)`:**
     - En `evaluate_batch_v1` y `evaluate_single_message_v1`, crear una función síncrona interna o invocar `await asyncio.to_thread(evaluador_lotes.evaluar_lote, ...)` para que la inferencia LLM y el guardado en Supabase ocurran fuera del event loop principal de FastAPI.
     - Asimismo, envolver cualquier llamada posterior de reconciliación (`_sincronizar_supabase_a_sqlite`) en `await asyncio.to_thread(...)` o actualizar directamente SQLite local e invalidar la caché para que el event loop jamás se bloquee.
  2. **Envoltorio resiliente y thread-safe para `cerebro_ia_gemma_4.cadena`:**
     - Implementar en `puente_motor_ia.py` la clase/runnable thread-safe `_CadenaGemmaResiliente` que envuelva la invocación (`invoke`) cuando se usa `cerebro_ia_gemma_4`:
       - Utiliza `concurrent.futures.ThreadPoolExecutor` local por invocación (100% thread-safe dentro de `asyncio.to_thread`) con **timeout estricto por mensaje** (`GEMMA_EVAL_TIMEOUT_SECONDS = 20.0`).
       - Configura parámetros deterministas y ligeros (`temperature=0.1`, `max_output_tokens=800`).
       - Aplica **máximo 2 reintentos** rápidos sobre el modelo primario (`gemma-4-31b-it`) ante errores `500 INTERNAL`, `503 UNAVAILABLE`, `429` o `TimeoutError`.
       - Si el modelo primario falla o agota el timeout, conmuta automáticamente en cascada (**fallback transparente**) hacia:
         1. `gemma-4-26b-a4b-it` (Google AI Studio)
         2. `gemini-3.5-flash-lite` / `gemini-2.5-flash` (`cerebro_ia_gemini_flash`)
         3. `openai/gpt-oss-120b` / `Groq` (`cerebro_ia`)
       - Devuelve siempre una instancia válida de `FormatoSalida` sin colgar el servidor.
     - Inyectar `_CadenaGemmaResiliente` tanto en `_motor_gemma.cadena` como en el módulo `cerebro_ia_gemma_4` cargado en `sys.modules` al ejecutar `evaluar_lote`.

---

## 3. Matriz de Impacto y Verificación de Velocidad

| Componente / Endpoint | Archivo Modificado | Impacto en Latencia | Garantía de Regla de Oro |
| :--- | :--- | :--- | :--- |
| `PATCH /curation` (RF-01) | `puente_motor_ia.py`, `Messages.tsx` | **Mejora de ~400ms a `< 2ms`** | Eliminada conexión síncrona a Supabase; ahora usa SQLite local + `asyncio.create_task` |
| `POST /discord/sync` (RF-02, RF-05) | `puente_motor_ia.py` | **Sin cambio (`< 1.5s`)** | Reconciliación de ID canónico en tarea background y deduplicación O(1) en `_ids_bots_omitidos_vistos` |
| `POST /ai/evaluate-*` (RF-02, RF-06, RF-07) | `puente_motor_ia.py`, `Messages.tsx` | **Event loop 0ms bloqueado** | `await asyncio.to_thread(...)` + timeout 20s y fallback automático en Gemma 4 |
| `ContentStudio.tsx` (RF-03, RF-06) | `ContentStudio.tsx`, `puente_motor_ia.py` | **0ms (render estático)** | Transparencia de matriz Multi-LLM y filtro local `>= 35%` en memoria |
| `POST /hitl-decision` y `/publish-channel` (RF-04) | `puente_motor_ia.py` | **0ms extra en request** | Construcción en memoria de `json_precurado` y `activos_distribucion_generados` + réplica en background |
