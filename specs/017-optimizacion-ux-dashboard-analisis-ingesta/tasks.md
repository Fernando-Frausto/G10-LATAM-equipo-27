# Tareas de Implementación — Spec 017: Corrección Tipográfica Global, Terminología Intuitiva, Scroll de Mensajes, Telemetría Real de Bots y Navegación de Quejas

- [x] **Tarea 1 (Fase Red TDD): Pruebas automatizadas para telemetría de bots/reales y corte de lote IA en backend**
  - **RF Asignados:** RF-004, RF-005, RF-010
  - **Archivos:** `tests/test_unificacion_motor_ia.py`
  - **Acción:**
    - Diseñar prueba unitaria `test_community_messages_incluye_omitted_bots_count_y_real_messages_count` que verifique que el endpoint `GET /api/community/messages` retorne los campos enteros `omitted_bots_count` y `real_messages_count` calculados a partir de las interacciones en SQLite discriminadas mediante `_es_cuenta_bot`, preservando los campos existentes `total` y `messages`.
    - Diseñar prueba de integración `test_evaluate_batch_aplica_corte_limite_sobre_pendientes_con_ver_json_inmutable` que verifique que `POST /api/v1/ai/evaluate-batch` con payload `{"limite": 5, "proveedor": "Groq (Llama 3.3)"}` evalúe exactamente hasta 5 mensajes pendientes sin alterar en absoluto `ver_json.py`.
  - **Hecho cuando:** `pytest tests/test_unificacion_motor_ia.py -k "omitted_bots or evaluate_batch_aplica_corte"` falle de manera controlada (Fase Red) evidenciando la falta de los campos y del corte estricto en `puente_motor_ia.py`.

- [x] **Tarea 2 (Fase Green Backend): Implementar telemetría de bots/reales y corte determinista de lote en puente_motor_ia.py**
  - **RF Asignados:** RF-004, RF-005, RF-010
  - **Archivos:** `puente_motor_ia.py`
  - **Acción:**
    - En el endpoint `GET /api/community/messages` de `puente_motor_ia.py`: calcular a partir de `motor_bd.listar_interacciones(limite=None, incluir_bots=True)` el total de bots/webhooks detectados (`omitted_bots_count`) mediante `_es_cuenta_bot(it)` y el total de mensajes de usuarios humanos reales (`real_messages_count`), exponiéndolos en la respuesta JSON raíz sin romper el contrato previo.
    - En el endpoint `POST /api/v1/ai/evaluate-batch` de `puente_motor_ia.py`: procesar el parámetro `limite` recibido en el body, obtener el universo de mensajes de `ver_json.py` con margen suficiente sin modificar dicho archivo protegido, y aplicar el slice estricto `[:limite]` sobre la colección de interacciones efectivamente pendientes de análisis.
  - **Hecho cuando:** Todas las pruebas de la Tarea 1 pasen al 100% en verde (`pytest tests/test_unificacion_motor_ia.py -k "omitted_bots or evaluate_batch_aplica_corte"`).

- [x] **Tarea 3: Frontend Saneamiento UTF-8 Global con Preservación del Corpus de Usuarios**
  - **RF Asignados:** RF-001
  - **Archivos:** `frontend/src/pages/Messages.tsx`, `frontend/src/pages/Analytics.tsx`, `frontend/src/pages/ContentStudio.tsx`, `frontend/src/api/contentWorkflow.ts`, `frontend/src/api/messageCuration.ts`, `frontend/src/api/motorContent.ts`
  - **Acción:**
    - Reemplazar sistemáticamente los caracteres `?` y secuencias de escape corruptas por sus caracteres acentuados correspondientes en español (`curaduría`, `interacción`, `válida`, `inválido`, `confirmó`, `Atención`, `crítico`, `Señales`, `revisión`, `aquí`, `envían`, `telemetría`, `semántica`) en todos los textos estáticos, badges, tooltips, modales y mensajes de error del frontend.
    - Verificar que los reemplazos NO afecten las cadenas textuales de mensajes emitidos por los usuarios (`message.content`), conservando íntegros los signos de interrogación auténticos en preguntas de la comunidad.
  - **Hecho cuando:** Una búsqueda global de expresiones como `curadur?a`, `interacci?n`, `Atenci?n`, `cr?tico`, `aqu?`, `env?an` en `frontend/src/` retorne cero coincidencias en textos estáticos y `npm run build` en `frontend/` compile con código 0.

- [x] **Tarea 4: Frontend Messages.tsx — Terminología 'Publicar', Scroll Delimitado y Selector de Lote IA**
  - **RF Asignados:** RF-002, RF-003, RF-004
  - **Archivos:** `frontend/src/pages/Messages.tsx`
  - **Acción:**
    - Sustituir la terminología técnica: en el panel de lote IA cambiar `"pendientes de copy"` por `"Pendientes de publicar"`; en el selector `"Estado del mensaje"` cambiar `"Pendientes de copy"` por `"Pendientes de publicar"`; en el badge de etapa de la tarjeta cambiar `"Copy"` por `"Publicar"`; y en `StatusBadge` cambiar `"Falta redacción de copy"` por `"Falta redacción de publicación"`.
    - En el contenedor de la lista de tarjetas de mensajes, aplicar la clase de scroll vertical delimitado y responsivo: `max-h-[min(850px,70vh)] overflow-y-auto pr-2`.
    - Eliminar la casilla de verificación y etiqueta `"Solo pendientes de evaluar"`.
    - Incorporar el selector `<select>` estilizado para el tamaño del lote: opciones fijas `1`, `5`, `10`; opción dinámica `"Evaluar todos ({conteo})"` cuando $1 \le \text{conteo} \le 10$ y $\text{conteo} \notin \{1, 5, 10\}$; valor por defecto `5` (o el conteo disponible si es menor); si $\text{conteo} == 0$, deshabilitar el selector con la opción `"Sin pendientes"` y deshabilitar el botón de evaluación.
    - Pasar el valor seleccionado como `limite` a la función `handleEvaluateBatch`.
  - **Hecho cuando:** `npm run build` compile limpiamente y en la vista `/messages` se visualice el selector desplegable con las opciones exactas, las nuevas etiquetas de publicación y el contenedor con scroll vertical contenido.

- [x] **Tarea 5: Frontend Messages.tsx Cabecera de Telemetría, Analytics.tsx Insights y Botón a Quejas con Anclaje en ContentStudio.tsx**
  - **RF Asignados:** RF-005, RF-006, RF-007
  - **Archivos:** `frontend/src/pages/Messages.tsx`, `frontend/src/pages/Analytics.tsx`, `frontend/src/pages/ContentStudio.tsx`
  - **Acción:**
    - En `Messages.tsx`: actualizar la interfaz `MessagesApiResponse` y en la cabecera contigua a `"Sincronizar Discord"`, reemplazar `"Pendientes en Copy"` por `"Mensajes omitidos de bots"` (usando `omitted_bots_count`) y `"Incidentes prioritarios"` por `"Mensajes reales detectados"` (usando `real_messages_count`).
    - En `Analytics.tsx`: asegurar que las tarjetas `"Insight principal"`, `"Preguntas frecuentes"` y `"Atención requerida"` consuman datos reales de la comunidad, y en la tarjeta `"Atención requerida"`, agregar el botón `"Gestionar quejas y reclamos"` que navega a `/content#panel-quejas`.
    - En `ContentStudio.tsx`: asignar el identificador `id="panel-quejas"` al contenedor principal de la sección `"Panel de Quejas, Reclamos y Soporte Crítico"` y configurar un hook `useEffect` reactivo a `location.hash` que ejecute `scrollIntoView({ behavior: 'smooth', block: 'start' })` con tolerancia a renderizado asíncrono.
  - **Hecho cuando:** `npm run build` compile sin errores, la cabecera de Ingesta muestre la telemetría real de bots/humanos y al pulsar `"Gestionar quejas y reclamos"` en Análisis se redirija fluidamente hacia el panel de quejas en Redacción con desplazamiento suave.

- [x] **Tarea 6: Verificación Global de Regresión, CI/CD e Inviolabilidad Constitucional**
  - **RF Asignados:** RF-008, RF-009, RF-010
  - **Archivos:** `puente_motor_ia.py`, `frontend/`, `tests/test_unificacion_motor_ia.py`, `MEMORY.md`
  - **Acción:**
    - Ejecutar suite de pruebas completa en local: `pytest tests/test_unificacion_motor_ia.py` verificando 100% pruebas en verde.
    - Ejecutar compilación de frontend: `npm run build` en `frontend/` verificando 0 errores de TypeScript y salida limpia.
    - Ejecutar `git status` para auditar la inviolabilidad de los 17 archivos protegidos de la raíz, `backend/`, `motor-ia/` y `src/` de Enoc.
    - Confirmar que ningún commit contenga la etiqueta `[skip netlify]` para permitir el despliegue automático del frontend.
    - Redactar y entregar la guía detallada de variables de entorno para Enoc en Render y Netlify.
    - Actualizar `MEMORY.md` con las decisiones y avances de la Spec 017.
  - **Hecho cuando:** Todas las suites pasen al 100%, la compilación sea exitosa, la auditoría git confirme 0 archivos protegidos modificados y la guía de variables esté lista.
