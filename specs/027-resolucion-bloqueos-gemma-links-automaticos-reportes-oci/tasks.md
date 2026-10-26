# Lista de Tareas 027: Resolución de Bloqueos en Gemma 4, Inclusión Automática de Links y Sincronización de Reportes OCI

> **Regla Constitucional Innegociable:** Los cambios se circunscriben estrictamente a los archivos autorizados: `src/nodes.py`, `src/publishers.py`, `src/schemas.py`, `puente_motor_ia.py`, `frontend/src/pages/Messages.tsx` y `tests/test_unificacion_motor_ia.py`. Queda categóricamente prohibido modificar `reporte_semanal.py` o cualquier archivo preexistente de la raíz o `motor-ia/`. Toda lectura `GET` debe responder en `< 2 ms` (Regla de Oro de Alta Velocidad).

---

## - [x] Tarea 1: Suite de Pruebas TDD para la Spec 027 (Fase Red)
- **Tiempo estimado:** 20 min
- **Requisitos cubiertos:** RF-01, RF-02, RF-03, RF-04, RF-05, RF-06, RF-07, RNF-01, RNF-02, RNF-04
- **Archivos a modificar:** `tests/test_unificacion_motor_ia.py`
- **Descripción:**
  - Crear pruebas automatizadas dedicadas que verifiquen los 7 requerimientos funcionales antes de su implementación (Fase Red):
    1. **Test RF-01:** Verificar que `evaluate_batch_v1` o `evaluate_single_message_v1` al recibir `"cerebro_ia_gemma_4"` o `"Google Gemma 4"` responda `HTTP 400 Bad Request` indicando su exclusividad para masivo `< 35%`, o ejecute fallback transparente hacia Groq (Llama 3.3) / Gemini Flash Lite.
    2. **Test RF-02:** Verificar que `POST /api/v1/ai/cancel-evaluation` active la señal cooperativa `_evento_cancelacion_evaluacion`, detenga el bucle de procesamiento y persista las evaluaciones completadas hasta ese instante.
    3. **Test RF-03:** Verificar que `nodo_linkedin`, `enviar_linkedin` y `puente_motor_ia.py` incluyan de forma automática e idempotente el bloque "Más Información" con los 3 links oficiales (`gX2m2Rhq`, `gvbqJiF4`, `gU7h7xyG`) y saniticen `"Alura"` -> `"CloudEDTech"`.
    4. **Test RF-04:** Verificar que `nodo_x`, `enviar_tweet_x` y `puente_motor_ia.py` incluyan de forma automática los 2 links oficiales (`gvbqJiF4`, `gU7h7xyG`), respeten la longitud total <= 280 caracteres recortando el cuerpo en frontera de palabra (`...`) sin truncar jamás los enlaces, y saniticen `"Alura"`.
    5. **Test RF-05:** Verificar que `nodo_publicador` persista en `public.historial_reportes_semanales` ante publicaciones parciales (ej. Discord exitoso y X fallido por falta de credenciales), guardando `rutas_activas = ["discord"]` y `estado = "publicado"`.
    6. **Test RF-06:** Verificar que `src/nodes.py`, `src/schemas.py` y `puente_motor_ia.py` utilicen el formato canónico de semana `YYYY-semana-WW` (ej. `2026-semana-42`), asegurando que `reporte_semanal.py` no sea modificado.
    7. **Test RF-07:** Verificar que `_cargar_lote_para_reporte_semanal` reconstruya los copys reales desde `contenidos_generados` e `interacciones` de SQLite cuando Supabase no tenga datos para la semana, erradicando por completo cualquier registro con `id_mensaje: "999"` o `fallback_user`.
- **Comando de verificación:** `pytest tests/test_unificacion_motor_ia.py -k "spec027"`
- **Hecho cuando:** Los casos de prueba existen en `tests/test_unificacion_motor_ia.py`, compilan sin errores de sintaxis y exponen los puntos a implementar.

---

## - [x] Tarea 2: Automatización de Links y Sanitización de Marca en LinkedIn y X (RF-03 y RF-04)
- **Tiempo estimado:** 20 min
- **Requisitos cubiertos:** RF-03, RF-04, RNF-01, RNF-02
- **Archivos a modificar:** `src/nodes.py`, `src/publishers.py`, `puente_motor_ia.py`
- **Descripción:**
  - Modificar `src/nodes.py`:
    - En `nodo_linkedin`: actualizar `<system_prompt>` para exigir el bloque "Más Información" con los 3 links oficiales (`https://lnkd.in/gX2m2Rhq`, `https://lnkd.in/gvbqJiF4`, `https://lnkd.in/gU7h7xyG`); en la salida, aplicar post-procesamiento defensivo e idempotente para anexar el bloque si faltaba y sanitizar cualquier mención a `"Alura"` -> `"CloudEDTech"`.
    - En `nodo_x`: actualizar `<system_prompt>` para exigir los 2 links oficiales (`https://lnkd.in/gvbqJiF4`, `https://lnkd.in/gU7h7xyG`); en la salida, asegurar que el post resultante tenga longitud total <= 280 caracteres recortando el cuerpo en frontera de palabra (`...`) sin mutilar las URLs y sanitizando `"Alura"` -> `"CloudEDTech"`.
  - Modificar `src/publishers.py`:
    - En `enviar_linkedin`: sanitizar marca y verificar/anexar de forma idempotente el bloque de 3 links antes de enviar a la API de LinkedIn.
    - En `enviar_tweet_x`: sanitizar marca y verificar/anexar de forma idempotente los 2 links garantizando que el tweet completo no supere 280 caracteres y que las URLs no sean truncadas.
  - Modificar `puente_motor_ia.py`:
    - En `_formatear_borradores_ui` y en las funciones de generación (`generate-channel`, `execute-pipeline`), aplicar la inyección automática para que los borradores de LinkedIn y X muestren los links inmediatamente en la interfaz.
- **Comando de verificación:** `pytest tests/test_unificacion_motor_ia.py -k "links or linkedin or tweet"`
- **Hecho cuando:** La generación de copys para LinkedIn y X incorpora automáticamente los links correspondientes, respeta los 280 caracteres en X sin romper URLs, elimina cualquier mención a "Alura", y las pruebas de RF-03 y RF-04 pasan en verde.

---

## - [x] Tarea 3: Tolerancia a Éxitos Parciales en `nodo_publicador` y Normalización Canónica de Semana (RF-05 y RF-06)
- **Tiempo estimado:** 20 min
- **Requisitos cubiertos:** RF-05, RF-06, RNF-01, RNF-03
- **Archivos a modificar:** `src/nodes.py`, `src/schemas.py`, `puente_motor_ia.py`
- **Descripción:**
  - Modificar `src/nodes.py`:
    - En `nodo_publicador`: reemplazar la condición `if todas_exitosas:` por `if al_menos_una_exitosa:` (donde `al_menos_una_exitosa = len(canales_exitosos) > 0`).
    - Almacenar en `rutas_activas` la lista de canales que efectivamente tuvieron éxito (ej. `["discord"]`), persistir `estado = "publicado"` y registrar el detalle por canal en `estado_publicacion`.
    - Normalizar el valor de `semana` al formato canónico `YYYY-semana-WW` (ej. `2026-semana-42`) antes de insertar en `public.historial_reportes_semanales`.
  - Modificar `src/schemas.py`:
    - Actualizar los valores por defecto en `TemporalidadProductoCreado` y `TemporalidadProductoCreadoX` para reflejar el formato canónico `YYYY-semana-WW`.
  - Modificar `puente_motor_ia.py`:
    - Homologar `_normalizar_semana_canonico(semana_raw, fecha_ref)` para transformar variantes como `"Semana_01"` o `"Semana_05"` en `YYYY-semana-WW` utilizando la fecha de referencia del mensaje.
    - En `_extraer_historial_reportes_semanales_supabase`, permitir coincidencia por clave canónica exacta y búsqueda por patrón numérico (`WHERE semana = %s OR semana ILIKE %s`).
    - Mantener `reporte_semanal.py` estrictamente intacto.
- **Comando de verificación:** `pytest tests/test_unificacion_motor_ia.py -k "publicador or semana"`
- **Hecho cuando:** Despachar un contenido donde solo un canal tenga credenciales válidas guarda la fila en `public.historial_reportes_semanales`, la semana se registra en formato `YYYY-semana-WW`, `reporte_semanal.py` tiene 0 modificaciones, y las pruebas de RF-05 y RF-06 pasan al 100%.

---

## - [x] Tarea 4: Reconstrucción de Reportes OCI desde SQLite y Erradicación Total de Mocks (RF-07)
- **Tiempo estimado:** 20 min
- **Requisitos cubiertos:** RF-07, RNF-01, RNF-03
- **Archivos a modificar:** `puente_motor_ia.py`, `tests/test_unificacion_motor_ia.py`, `reportes/2026-semana-42.json`
- **Descripción:**
  - Modificar `puente_motor_ia.py`:
    - En `_cargar_lote_para_reporte_semanal`: si Supabase no contiene aprobados para la semana indicada, consultar SQLite local uniendo `contenidos_generados` con `interacciones` (`WHERE c.estado_publicacion = 'publicado' OR c.estado = 'publicado' OR i.etapa_flujo = 'publicado'`).
    - Construir la estructura de aprobados con los copys y KPIs reales persistidos localmente.
    - Erradicar por completo cualquier referencia a `id_mensaje: "999"` o `fallback_user`. Si tras agotar Supabase y SQLite no existen registros, retornar `{"aprobados": [], "descartados": []}` (provocando `HTTP 400` controlado en `POST /api/v1/oci-storage/weekly-sync`).
  - Actualizar pruebas en `tests/test_unificacion_motor_ia.py`:
    - Reemplazar los mocks que inyectaban `id_mensaje: "999"` y `fallback_user` por datos reales de prueba.
  - Saneamiento de reportes:
    - Regenerar y sobrescribir `reportes/2026-semana-42.json` con los mensajes reales de la base de datos local y asegurar que no contenga registros ficticios.
    - Eliminar `reportes/2026-semana-99.json` o cualquier residuo de pruebas con datos falsos.
- **Comando de verificación:** `pytest tests/test_unificacion_motor_ia.py -k "oci or reporte"`
- **Hecho cuando:** Las consultas y sincronizaciones de reportes OCI extraen mensajes reales de la base local, `reportes/2026-semana-42.json` carece de registros ficticios, y las pruebas de RF-07 pasan en verde.

---

## - [x] Tarea 5: Blindaje Backend de Ingesta: Descarte de Gemma 4 y Endpoint de Cancelación (RF-01 y RF-02)
- **Tiempo estimado:** 20 min
- **Requisitos cubiertos:** RF-01, RF-02, RNF-02
- **Archivos a modificar:** `puente_motor_ia.py`
- **Descripción:**
  - En `puente_motor_ia.py`:
    - Descartar Gemma 4 en Ingesta: en `evaluate_batch_v1` y `evaluate_single_message_v1`, si el proveedor solicitado es Gemma 4, responder `HTTP 400 Bad Request` indicando que está reservado para la cola de copywriting masivo, o ejecutar fallback automático transparente hacia Groq (Llama 3.3) o Gemini Flash Lite.
    - Implementar el evento cooperativo global `_evento_cancelacion_evaluacion = threading.Event()`.
    - Implementar el endpoint:
      ```python
      @app.post("/api/v1/ai/cancel-evaluation")
      @app.post("/api/v1/ai/cancel-evaluation/")
      async def cancel_evaluation_v1(payload: dict = Body(default={})):
          _evento_cancelacion_evaluacion.set()
          return {"status": "cancelled", "message": "Evaluación cancelada exitosamente"}
      ```
    - En el bucle de evaluación de mensajes en el hilo de trabajo, verificar `if _evento_cancelacion_evaluacion.is_set(): break` antes de cada invocación al LLM, asegurando que los mensajes procesados hasta ese instante se persistan en SQLite.
    - Envolver la llamada al hilo secundario en `await asyncio.wait_for(asyncio.to_thread(...), timeout=60.0)` para prevenir sockets o llamadas colgadas en Google AI Studio.
- **Comando de verificación:** `pytest tests/test_unificacion_motor_ia.py -k "cancel or gemma_ingesta"`
- **Hecho cuando:** `POST /api/v1/ai/cancel-evaluation` responde en `< 5 ms`, la cancelación cooperativa interrumpe el bucle de evaluación conservando los mensajes previos, Gemma 4 no puede ejecutarse en Ingesta, y las pruebas de RF-01 y RF-02 pasan al 100%.

---

## - [x] Tarea 6: Integración en Frontend (`Messages.tsx`), Compilación y Verificación Integral
- **Tiempo estimado:** 20 min
- **Requisitos cubiertos:** RF-01, RF-02, RNF-01, RNF-02, RNF-04
- **Archivos a modificar:** `frontend/src/pages/Messages.tsx`, `MEMORY.md`
- **Descripción:**
  - Modificar `frontend/src/pages/Messages.tsx`:
    - En `DEFAULT_AI_MODELS` y en el selector de proveedor de Ingesta, dejar activos únicamente Groq (Llama 3.3) y Google Gemini Flash Lite. Deshabilitar Gemma 4 (`disabled: true`) con badge/tooltip: *"Reservado para copywriting masivo (<35%). En Ingesta usa Groq o Gemini Flash Lite"*.
    - Añadir la referencia `abortControllerRef = useRef<AbortController | null>(null)` y vincular su señal al `fetch` en `handleEvaluateBatch`.
    - Renderizar en la interfaz el botón visible e interactivo de **"Cancelar Evaluación"** cuando `isEvaluatingBatch === true`.
    - Al pulsar "Cancelar": disparar `abortControllerRef.current?.abort()`, invocar `POST /api/v1/ai/cancel-evaluation`, restablecer `setIsEvaluatingBatch(false)`, invocar `loadMessages()` y desplegar advertencia informativa.
    - Configurar timeout del cliente a 60 segundos ante posibles demoras de la API externa.
  - Verificación Integral del Proyecto:
    - Ejecutar suite completa de tests: `pytest` (100% verde).
    - Ejecutar build de frontend: `npm run build` dentro de `frontend/` (código de salida 0).
    - Ejecutar `git status` para confirmar que los 17 archivos protegidos de la raíz (`reporte_semanal.py`, `evaluador_lotes.py`, `base_datos.py`, etc.) permanecen 100% intactos.
    - Actualizar `MEMORY.md` resumiendo las decisiones y logros de la Spec 027.
- **Comandos de verificación:**
  * `pytest`
  * `cd frontend; npm run build; cd ..`
  * `git status`
- **Hecho cuando:** `pytest` pasa al 100% en verde, el build de TypeScript finaliza con código 0, la interfaz de Ingesta cuenta con el botón de cancelación activo y Gemma 4 deshabilitado, y `MEMORY.md` queda debidamente documentado.
