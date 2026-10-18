# Lista de Tareas (SDD) — Spec 012: Redacción de Contenidos, Soporte a Quejas con Selector de IA y Publicación en Discord

> 6 tareas atómicas de ~20 minutos cada una, siguiendo ciclo estricto TDD (Red -> Green -> Refactor) y preservando la inmutabilidad de los módulos protegidos.

---

### [x] Tarea 1: Fase Red TDD — Pruebas Automatizadas de Endpoints de Quejas y Copywriting
- **Estado:** `[x]` Completada
- **Tiempo estimado:** 20 min
- **RFs cubiertos:** RF-01, RF-02, RF-03, RF-04, RF-06, RF-07, RF-08
- **Archivos a modificar:** [`tests/test_unificacion_motor_ia.py`](file:///c:/Users/jeova/OneDrive/Documentos/Alura/Codigo%20unificado%20con%20imports/tests/test_unificacion_motor_ia.py)
- **Descripción:**
  Escribir pruebas automatizadas completas en `tests/test_unificacion_motor_ia.py` que comprueben:
  1. `POST /api/v1/content-workflow/complaints/generate-response`:
     - Genera respuesta con proveedor por defecto (`Groq (Llama 3.3)`) y con proveedores específicos (`Google Gemma 4`, `Google Gemini Flash Lite`).
     - Lanza HTTP 404 si la interacción no existe y HTTP 422 si el texto está vacío.
     - Lanza HTTP 502 si faltan credenciales o falla el motor, detallando el proveedor en el error sin sustitución silenciosa.
  2. `GET /api/v1/content-workflow/complaints/{id}/publish-preview`:
     - Responde HTTP 200 con `ready: false` y detalle explicativo si `DISCORD_BOT_TOKEN` / `DISCORD_TOKEN` no está configurado.
     - Responde HTTP 404 si el mensaje original no existe en Discord.
     - Responde HTTP 200 con `ready: true`, `channel_id`, `channel_name`, `source_message_id`, `author` y `original_content` cuando los datos son válidos.
  3. `POST /api/v1/content-workflow/complaints/publish-response`:
     - Rechaza con HTTP 400 si `confirmado` es falso o la respuesta supera los 2000 caracteres.
     - Con token y mensaje simulado/mocked de Discord, publica con reply directo (`allowed_mentions=none`), registra en SQLite `respuestas_quejas_discord` y retorna `estado: "publicado"`.
  4. `GET /api/v1/content-workflow/complaints/published-responses`:
     - Consulta la tabla `respuestas_quejas_discord` y devuelve `{"interaction_ids": [id1, ...]}`.
  5. `POST /api/v1/content-workflow/regenerate`:
     - Genera copy para LinkedIn, X y Discord con el proveedor solicitado.
     - Para formato `x`, valida que el texto devuelto nunca supere los 280 caracteres (`len(contenido) <= 280`).
  6. `POST /api/v1/content-workflow/drafts`:
     - Inserta en `contenidos_generados` con `estado: 'pendiente_revision'`, avanza la interacción a `en_aprobacion` y retorna `id` y `estado`.
- **Hecho cuando:** Las nuevas pruebas existen en `tests/test_unificacion_motor_ia.py` y fallan ordenadamente en los endpoints y contratos nuevos aún no implementados (Fase Red confirmada con código de salida esperado).

---

### [x] Tarea 2: Implementación Backend de Soporte a Quejas y Publicación Discord en `puente_motor_ia.py`
- **Estado:** `[x]` Completada
- **Tiempo estimado:** 20 min
- **RFs cubiertos:** RF-01, RF-02, RF-03, RF-04, RF-08
- **Archivos a modificar:** [`puente_motor_ia.py`](file:///c:/Users/jeova/OneDrive/Documentos/Alura/Codigo%20unificado%20con%20imports/puente_motor_ia.py)
- **Descripción:**
  Implementar en `puente_motor_ia.py`:
  1. Creación e inicialización de la tabla `respuestas_quejas_discord` en `_asegurar_esquema_sqlite()` con índice sobre `interaccion_id`.
  2. Endpoint `POST /api/v1/content-workflow/complaints/generate-response` invocando la plantilla estructurada de atención a quejas con el LLM normalizado (`_normalizar_proveedor_ia`), sin sustituciones silenciosas y con manejo de excepciones 404, 422 y 502/503.
  3. Endpoint `GET /api/v1/content-workflow/complaints/{interaccion_id}/publish-preview` con comprobación de tokens (`DISCORD_BOT_TOKEN` / `DISCORD_TOKEN`), respuesta 200 `ready: false` descriptiva si falta token, 404 si el mensaje no existe en Discord, y 200 `ready: true` con metadatos completos.
  4. Endpoint `POST /api/v1/content-workflow/complaints/publish-response` validando 1-2000 caracteres, enviando como reply directo mediante el bot oficial (`allowed_mentions=none`), registrando en `respuestas_quejas_discord` y actualizando la interacción.
  5. Endpoint `GET /api/v1/content-workflow/complaints/published-responses` consultando los IDs de `respuestas_quejas_discord`.
- **Hecho cuando:** Todas las pruebas automatizadas de quejas y publicación en Discord escritas en la Tarea 1 pasan al 100% en verde (`pytest tests/ -k "complaint" -v`).

---

### [x] Tarea 3: Implementación Backend de Copywriting en `puente_motor_ia.py`
- **Estado:** `[x]` Completada
- **Tiempo estimado:** 20 min
- **RFs cubiertos:** RF-05, RF-06, RF-07, RF-08
- **Archivos a modificar:** [`puente_motor_ia.py`](file:///c:/Users/jeova/OneDrive/Documentos/Alura/Codigo%20unificado%20con%20imports/puente_motor_ia.py)
- **Descripción:**
  Implementar en `puente_motor_ia.py`:
  1. Endpoint `POST /api/v1/content-workflow/regenerate`:
     - Acepta `texto`, `canal`, `formato`, `tono`, `proveedor`.
     - Normaliza el proveedor de IA y genera el copy adaptado según el formato.
     - Garantiza deterministamente en el servidor que para el formato `x` el texto no exceda los 280 caracteres (`len(contenido) <= 280`), aplicando recorte por frontera de palabra si el modelo se excede.
     - Retorna `{formato, titulo, contenido, llamada_accion, hashtags}`.
  2. Endpoint `POST /api/v1/content-workflow/drafts`:
     - Inserta el borrador en `contenidos_generados` con `estado = 'pendiente_revision'`.
     - Si recibe `interaccion_id`, actualiza su etapa a `en_aprobacion`.
     - Retorna `id: int`, `estado: 'pendiente_revision'`, `message: str`.
- **Hecho cuando:** Todas las pruebas automatizadas de copywriting pasan al 100% en verde (`pytest tests/ -k "regenerate or draft" -v`) y la suite completa de `test_unificacion_motor_ia.py` permanece en verde.

---

### [x] Tarea 4: Actualización del Cliente API Frontend en `contentWorkflow.ts`
- **Estado:** `[x]` Completada
- **Tiempo estimado:** 15 min
- **RFs cubiertos:** RF-01, RF-02, RF-06, RF-07
- **Archivos a modificar:** [`frontend/src/api/contentWorkflow.ts`](file:///c:/Users/jeova/OneDrive/Documentos/Alura/Codigo%20unificado%20con%20imports/frontend/src/api/contentWorkflow.ts)
- **Descripción:**
  Actualizar las firmas y tipos de TypeScript en `frontend/src/api/contentWorkflow.ts`:
  1. Añadir `proveedor?: string` a la interfaz `RegenerateContentRequest`.
  2. Actualizar `generateComplaintResponse(interaccionId: number, proveedor?: string)` para enviar `proveedor` en el cuerpo de la solicitud JSON.
  3. Enriquecer `ComplaintPublishPreview` con la propiedad opcional `detail?: string` para capturar mensajes cuando `ready === false`.
  4. Verificar que `createContentDraft`, `publishComplaintResponse`, y `getPublishedComplaintIds` mantengan tipos consistentes con las respuestas reales del backend.
- **Hecho cuando:** `npm run build` o el compilador de TypeScript valida los nuevos tipos sin errores de compilación en `frontend/src/api/contentWorkflow.ts`.

---

### [x] Tarea 5: Adaptación de la Interfaz de Usuario en `ContentStudio.tsx`
- **Estado:** `[x]` Completada
- **Tiempo estimado:** 25 min
- **RFs cubiertos:** RF-01, RF-02, RF-03, RF-04, RF-05, RF-06, RF-07
- **Archivos a modificar:** [`frontend/src/pages/ContentStudio.tsx`](file:///c:/Users/jeova/OneDrive/Documentos/Alura/Codigo%20unificado%20con%20imports/frontend/src/pages/ContentStudio.tsx)
- **Descripción:**
  Refactorizar la vista `ContentStudio.tsx`:
  1. **Selector de IA en Modal de Quejas**:
     - Agregar dropdown/selector de proveedor (`Groq (Llama 3.3)`, `Google Gemma 4`, `Google Gemini Flash Lite`).
     - Deshabilitar el selector y el botón "Generar con IA" durante la generación de respuesta (`complaintGenerating`).
     - Pasar el proveedor seleccionado a `generateComplaintResponse`.
  2. **Selector de IA en Mesa de Trabajo de Copys**:
     - Agregar selector de modelo en la cabecera de la sección "Contenido generado".
     - Deshabilitar el selector mientras haya regeneraciones en vuelo.
     - Pasar el proveedor seleccionado en la invocación de `handleRegenerate(format)`.
  3. **Erradicación de Mocks y Carga Real**:
     - Eliminar la importación y uso de `mockCommunityData.content_studio[0]`.
     - Vincular los borradores iniciales directamente al contenido de `selectedWorkflowMessage`.
     - Mostrar estado informativo si no hay mensajes en redacción.
  4. **Desbloqueo y Gestión de Publicación en Discord**:
     - Activar el botón "Enviar respuesta a Discord" cuando `complaintDestination?.ready === true` y la respuesta sea válida (1-2000 chars).
     - Mostrar aviso claro cuando `ready === false` (incluyendo `complaintDestination?.detail`).
     - Tras publicar exitosamente, agregar el ID a la lista de atendidos para excluir la queja de la pantalla de inmediato.
  5. **Manejo Independiente de Formatos**:
     - Preservar la selección del mensaje de redacción al guardar un formato, permitiendo redactar y enviar a aprobación los demás formatos sin expulsar la tarjeta prematuramente.
- **Hecho cuando:** `frontend/` compila de forma limpia con `npm run build` y la UI permite seleccionar modelo de IA, regenerar copys reales, guardar borradores independientes, verificar destino y publicar quejas en Discord.

---

### [x] Tarea 6: Verificación Global de Regresión, Compilación, Inviolabilidad y Memoria
- **Estado:** `[x]` Completada
- **Tiempo estimado:** 15 min
- **RFs cubiertos:** RF-01 a RF-08
- **Archivos a modificar:** [`MEMORY.md`](file:///c:/Users/jeova/OneDrive/Documentos/Alura/Codigo%20unificado%20con%20imports/MEMORY.md)
- **Descripción:**
  1. Ejecutar la suite completa de pruebas en el backend: `pytest tests/ -v`. Verificar 100% pruebas en verde (0 fallos).
  2. Ejecutar la compilación del frontend: `npm run build` en `frontend/` y verificar finalización limpia sin advertencias críticas ni errores.
  3. Ejecutar auditoría git con `git status` para confirmar que los 17 archivos protegidos de la raíz, `backend/` y `motor-ia/` no sufrieron ninguna modificación.
  4. Actualizar `MEMORY.md` resumiendo la culminación del soporte a quejas con selector de IA y mesa de trabajo de copywriting real.
- **Hecho cuando:** Todos los tests pasan en verde, el build de frontend sale con código 0, la inmutabilidad de archivos raíz está 100% verificada y `MEMORY.md` se encuentra actualizado.
