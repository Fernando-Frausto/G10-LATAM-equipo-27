# Lista de Tareas 026: Corrección Integral de Hallazgos QA (Enoc) Pre-Demo Day

> **Regla de Oro Innegociable:** Todo cambio se circunscribe exclusivamente a `puente_motor_ia.py`, `frontend/src/pages/Messages.tsx`, `frontend/src/pages/ContentStudio.tsx` y `tests/test_unificacion_motor_ia.py`, preservando las lecturas `GET` en `< 2 ms` desde SQLite/caché y delegando toda operación remota a segundo plano (`asyncio.create_task` / `await asyncio.to_thread`).

---

## [x] T1: Suite de Pruebas TDD para los 7 Hallazgos QA de Enoc (Fase Red)
- **Tiempo estimado:** 20 min
- **Requisitos cubiertos:** RF-01, RF-02, RF-03, RF-04, RF-05, RF-06, RF-07, RNF-01, RNF-02, RNF-04
- **Archivos a modificar:** `tests/test_unificacion_motor_ia.py`
- **Descripción:**
  - Añadir pruebas automatizadas en `tests/test_unificacion_motor_ia.py` que validen cada uno de los 7 requisitos funcionales:
    1. [x] **Test RF-01:** Descarte manual (`discarded`) persiste en SQLite, excluye el ID en `_obtener_ids_evaluados_dual()`, sobrevive a `_sincronizar_supabase_a_sqlite()`, restaura a `'curated'` si ya está analizado o a `'pending'` si no lo está, y lanza réplica asíncrona a `public.lotes_ia_kpis` ignorando silenciosamente `0 rows affected`.
    2. [x] **Test RF-02:** Sincronización de mensajes nuevos adopta atómicamente el ID canónico de `public.interacciones`, empareja KPIs por `id_mensaje` y por `hash` / `(autor, texto_original)`, cambia a `analizado` al primer clic de evaluación y previene filas duplicadas en `public.lotes_ia_kpis`.
    3. [x] **Test RF-03:** `MODELOS_UTILIZADOS_CATALOGO` y `ContentStudio.tsx` exponen explícitamente la Matriz Multi-LLM con Fallbacks del Orquestador (`Qwen 3.8 27B`, `GPT-OSS 120B`, `Gemini 3.5/3.1 Flash Lite`, `Gemini 3.6 Flash`) y etiquetan el selector manual como motor de regeneración individual por canal.
    4. [x] **Test RF-04:** `construir_registro_historial_reporte` genera `contenido_original` con el objeto completo `json_precurado` (`relevancia` entero `0–100`, `temas_clave` lista, `segmento`, `razonamiento`, `decision_ia`, `estado_revision`) y `copys_generados` indexado por canal activo (`"discord"`, `"linkedin"`, `"x"`, `"reclamos"`) con `status`, `resumen_comunidad`, `activos_distribucion_generados` completo según `src/schemas.py` y `titulo`/`texto_copy` en la raíz del canal para retrocompatibilidad con Spec 024.
    5. [x] **Test RF-05:** `_sincronizar_discord_api_rest` deduplica los mensajes de bots mediante `_ids_bots_omitidos_vistos`, incrementando `0` bots omitidos al re-sincronizar los mismos `message_id`.
    6. [x] **Test RF-06:** Mensajes analizados con `relevancia >= 35` (incluyendo 60% y 68% en `#notificaciones`) quedan como `'curated'` / elegibles para publicación salvo que activen el filtro de seguridad de Prioridad 4 (`relevancia <= 10`, `"select"`, `"credenciales"`).
    7. [x] **Test RF-07:** `evaluate_batch_v1` y `evaluate_single_message_v1` ejecutan `evaluador_lotes.evaluar_lote` vía `await asyncio.to_thread(...)` sin bloquear el event loop, y `_CadenaGemmaResiliente` aplica timeout estricto (`<= 20s`), reintentos y fallback automático thread-safe ante errores `500 INTERNAL` o timeouts de Google API.
- **Hecho cuando:** Las nuevas pruebas existen en `tests/test_unificacion_motor_ia.py`, están sintácticamente limpias y evidencian los puntos a implementar.

---

## [x] T2: Persistencia de Curaduría Manual (RF-01) y Umbral de 4 Prioridades 35%–69% (RF-06) en Backend
- **Tiempo estimado:** 20 min
- **Requisitos cubiertos:** RF-01, RF-06, RNF-02
- **Archivos a modificar:** `puente_motor_ia.py`
- **Descripción:**
  - [x] Implementar `_es_spam_prioridad_4(relevancia, texto, razonamiento)` verificando `relevancia <= 10`, longitud `< 3` o términos `"select"` / `"credenciales"`.
  - [x] Actualizar `actualizar_curaduria_puente(interaccion_id, estado_curaduria)` y `curation_v1`:
    - Si se restaura un mensaje descartado, asignar `'curated'` si ya está analizado (`estado = 'analizado'` o `relevancia > 0`) o `'pending'` si aún no fue analizado.
    - Eliminar la llamada bloqueante `psycopg2.connect` del hilo de la petición HTTP y delegar la actualización de `estado_revision` (`'rechazado'` / `'pendiente'` / `'aprobado'`) en `public.lotes_ia_kpis` a segundo plano con `asyncio.create_task(asyncio.to_thread(...))`, ignorando silenciosamente `0 rows affected`.
  - [x] Actualizar `_obtener_ids_evaluados_dual()` para incluir `OR estado_curaduria = 'discarded'` y excluir de la evaluación por lote los mensajes descartados manualmente.
  - [x] Actualizar `_sincronizar_supabase_a_sqlite()`, `evaluate_batch_v1()`, `evaluate_single_message_v1()`, `_cargar_lote_consolidado_para_reporte()` y `_obtener_descartados_semana_sqlite()` para clasificar como `'curated'` (elegibles para publicar) los mensajes analizados con `relevancia >= 35` que no sean spam de Prioridad 4, respetando siempre cualquier decisión manual previa del operador en SQLite local (`discarded` o `pending`/`curated`).
- **Hecho cuando:** Las pruebas de RF-01 y RF-06 pasan en `pytest` y `PATCH /api/v1/content-workflow/messages/{id}/curation` responde en `< 5 ms` sin llamadas WAN bloqueantes.

---

## [x] T3: Paridad de ID Canónico, Vinculación Dual de KPIs (RF-02) y Deduplicación de Bots (RF-05)
- **Tiempo estimado:** 20 min
- **Requisitos cubiertos:** RF-02, RF-05, RNF-02
- **Archivos a modificar:** `puente_motor_ia.py`
- **Descripción:**
  - [x] Añadir el conjunto en memoria `_ids_bots_omitidos_vistos: set[str] = set()` y actualizar `_sincronizar_discord_api_rest` y `_ejecutar_sincronizacion_discord` para contabilizar en `_cache_bots_omitidos_discord` únicamente los `message_id` de bots/webhooks no vistos previamente.
  - [x] En `_sincronizar_discord_api_rest` (tarea de replicación y reconciliación) y en `evaluate_single_message_v1` / `evaluate_batch_v1`:
    - Garantizar que al insertar o evaluar un mensaje en `public.interacciones` de Supabase se obtenga su `id` canónico por `hash` y se reemplace atómicamente cualquier ID local temporal en SQLite local (evitando colisiones `UNIQUE PRIMARY KEY` o `UNIQUE hash`).
    - En `_sincronizar_supabase_a_sqlite`, vincular `kpis_raw` con las interacciones tanto por `id_mensaje` como por coincidencia de `hash` o par `(autor, texto_original)`, y conservar las interacciones locales recién sincronizadas para que jamás se borren ni requieran doble clic al analizar.
    - Evitar inserciones duplicadas en `public.lotes_ia_kpis` cuando `evaluador_lotes.evaluar_lote` ya persistió el resultado o cuando ya existe fila previa para el mismo `id_mensaje`.
- **Hecho cuando:** Las pruebas de RF-02 y RF-05 pasan en `pytest`, re-sincronizar Discord con los mismos bots suma `0` y evaluar un mensaje recién sincronizado lo marca como `analizado` desde el primer clic sin duplicar filas en `public.lotes_ia_kpis`.

---

## [x] T4: Estructura JSON Completa en `public.historial_reportes_semanales` (RF-04)
- **Tiempo estimado:** 20 min
- **Requisitos cubiertos:** RF-04, RNF-03
- **Archivos a modificar:** `puente_motor_ia.py`
- **Descripción:**
  - [x] Implementar `_normalizar_copy_canal_completo(...)` y actualizar `construir_registro_historial_reporte(...)`, `api_mototradis_hitl_decision(...)` y `api_mototradis_publish_channel(...)`:
    - En `contenido_original`: construir el objeto completo `json_precurado` con `id_mensaje`, `autor`, `canal_origen` (y alias `canal`), `comunidad`, `semana`, `texto_original` (y alias `texto`), `relevancia` (entero `0–100`), `sentimiento`, `temas_clave` (lista de strings), `segmento`, `razonamiento`, `decision_ia` y `estado_revision`, enriqueciendo desde SQLite local si algún campo no fue pasado en `interaccion`.
    - En `copys_generados`: estructurar el diccionario indexado por cada canal activo/publicado (`"discord"`, `"linkedin"`, `"x"`, `"reclamos"`), conteniendo para cada canal `status`, `resumen_comunidad` y `activos_distribucion_generados` completo conforme a `src/schemas.py` (`post_linkedin`, `destaque_newsletter_semanal`, `sugerencia_contenido_faq`, `post_postx`, `canal_seleccionado`, `post_discord`/`post_discord_faq`/`post_discord_notificaciones`/`post_discord_pqrs`, `temporalidad_producto_creado`), manteniendo además `titulo`, `texto_copy` y `plataforma` en la raíz de cada canal para retrocompatibilidad 100% con Spec 024 (OCI).
- **Hecho cuando:** Las pruebas de RF-04 y todas las pruebas preexistentes de Spec 023 y Spec 024 pasan al 100% en `pytest`.

---

## [x] T5: Evaluación No Bloqueante (`asyncio.to_thread`) y Envoltorio Resiliente Thread-Safe para Gemma 4 (RF-07)
- **Tiempo estimado:** 20 min
- **Requisitos cubiertos:** RF-07, RNF-02
- **Archivos a modificar:** `puente_motor_ia.py`
- **Descripción:**
  - [x] Implementar la clase thread-safe `_CadenaGemmaResiliente` en `puente_motor_ia.py` e inyectarla sobre `cerebro_ia_gemma_4.cadena`:
    - Configura invocación con `temperature=0.1`, `max_output_tokens=800`, timeout estricto por mensaje (`20s` vía `ThreadPoolExecutor`), hasta 2 reintentos ante errores `500 INTERNAL` / `503 UNAVAILABLE` / timeout, y fallback automático en cascada (`gemma-4-26b-a4b-it` -> `cerebro_ia_gemini_flash` -> `cerebro_ia` Groq) retornando siempre un `FormatoSalida` válido.
  - [x] Actualizar `evaluate_batch_v1` y `evaluate_single_message_v1` para ejecutar `evaluador_lotes.evaluar_lote`, `guardar_lote_ia_supabase` y `_sincronizar_supabase_a_sqlite` mediante `await asyncio.to_thread(...)`, garantizando que el event loop de FastAPI nunca quede bloqueado durante evaluaciones de IA.
- **Hecho cuando:** Las pruebas de RF-07 pasan en `pytest`, verificando concurrencia no bloqueante y fallback automático ante fallos `500 INTERNAL` o timeouts de Gemma 4.

---

## [x] T6: Homologación en Frontend React (`Messages.tsx` y `ContentStudio.tsx`) y Verificación Integral
- **Tiempo estimado:** 20 min
- **Requisitos cubiertos:** RF-01, RF-03, RF-06, RF-07, RNF-01, RNF-04
- **Archivos a modificar:** `frontend/src/pages/Messages.tsx`, `frontend/src/pages/ContentStudio.tsx`, `MEMORY.md`
- **Descripción:**
  - [x] En `frontend/src/pages/Messages.tsx`:
    - Actualizar el umbral de relevancia para `isDiscarded` / `Pendientes de publicar` de `< 70` a `< 35` (alineado con Prioridad 2 `35%–69%` del Orquestador, habilitando anuncios de `#notificaciones` de 60% y 68% para pasar a redacción).
    - Asegurar que al restaurar un mensaje descartado se actualice el estado local conforme a la respuesta del backend (`'curated'` si ya está analizado, `'pending'` si está sin analizar) y ajustar el aviso de evaluación con Gemma 4 reflejando el nuevo timeout resiliente con fallback automático.
  - [x] En `frontend/src/pages/ContentStudio.tsx`:
    - Actualizar el filtro de la Bandeja de Entrada de `relevance >= 70` a `relevance >= 35` (salvo descartados).
    - En la cabecera de la **Mesa de Trabajo Multicanal (Orquestador LangGraph)**, mostrar explícitamente la **Matriz Multi-LLM y Fallbacks Automáticos del Orquestador** (`Qwen 3.8 27B`, `GPT-OSS 120B`, `Gemini 3.5/3.1 Flash Lite`, `Gemini 3.6 Flash`) y renombrar la etiqueta del selector manual a **`IA Regeneración Individual:`** con tooltip aclaratorio.
  - [x] Ejecutar la suite completa `pytest`, compilar el frontend (`npm run build`), verificar `git status` para confirmar que los 17 archivos raíz protegidos y `src/` permanecen intactos, y actualizar `MEMORY.md`.
- **Hecho cuando:** `pytest` pasa con el 100% de los tests en verde, `npm run build` finaliza con código `0`, los 17 archivos protegidos y `src/` tienen `0` modificaciones en `git status`, y `MEMORY.md` está actualizado.
