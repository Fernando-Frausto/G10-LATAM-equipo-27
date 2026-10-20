# Tareas de Implementación — Spec 016: Trazabilidad Multicanal de Publicaciones en Redacción, Historias Destacadas e Ingesta de Mensajes

- [x] **Tarea 1 (Fase Red TDD): Pruebas de integración para persistencia individual de canal, checkpoint con plataformas y mensajes enriquecidos**
  - **Archivos:** `tests/test_unificacion_motor_ia.py`
  - **Acción:**
    - Escribir prueba unitaria `test_publish_channel_persiste_en_sqlite_y_actualiza_interaccion` para verificar que tras `POST /api/v1/mototradis/publish-channel`, se registre en `contenidos_generados` con `estado = 'publicado'` y `interacciones` con `etapa_flujo = 'publicado'`.
    - Escribir prueba `test_checkpoint_retorna_plataformas_publicadas_y_preserva_borradores` para verificar que `GET /api/v1/mototradis/checkpoint/{id}` devuelva `plataformas_publicadas: list[str]` sin vaciar `borradores_ui` ni `copys_generados`.
    - Escribir prueba `test_community_messages_enriquecido_con_is_published_y_plataformas` para verificar que `GET /api/community/messages` exponga `is_published: bool` y `published_platforms: list[str]`.
  - **Hecho cuando:** `pytest tests/test_unificacion_motor_ia.py -k "publish_channel or checkpoint or community_messages"` falle de forma controlada (Fase Red) por la ausencia de estas adaptaciones en `puente_motor_ia.py`.

- [x] **Tarea 2 (Fase Green Backend): Implementar persistencia por canal, enriquecimiento de checkpoint y endpoint de mensajes en puente**
  - **Archivos:** `puente_motor_ia.py`
  - **Acción:**
    - En `api_mototradis_publish_channel`: persistir en `contenidos_generados` (`estado = 'publicado'`, `estado_publicacion = 'publicado'`, `publicado_en = now`) y actualizar `interacciones` (`etapa_flujo = 'publicado'`, `estado_curaduria = 'curated'`) cuando el despacho sea exitoso, invalidando la caché.
    - En `api_mototradis_checkpoint`: retornar `plataformas_publicadas` consultando `contenidos_generados` y preservar íntegros `borradores_ui` y `copys_generados`.
    - Reemplazar `/api/community/messages` en `puente_motor_ia.py` para inyectar `is_published` y `published_platforms` (`Discord`, `LinkedIn`, `X`) y asignar `etapa_flujo = 'publicado'` cuando tenga publicaciones.
    - Normalizar nombres de plataformas en `/api/v1/community/live-summary`.
  - **Hecho cuando:** Todas las pruebas de la Tarea 1 pasen en verde (`pytest tests/test_unificacion_motor_ia.py`).

- [x] **Tarea 3: Frontend Redacción de Contenidos (`ContentStudio.tsx`)**
  - **Archivos:** `frontend/src/pages/ContentStudio.tsx`, `frontend/src/api/contentWorkflow.ts`
  - **Acción:**
    - Excluir mensajes ya publicados (`isPublished === true`) de la `"Bandeja de mensajes en Redacción"`.
    - En la `"Mesa de trabajo"` (`Mensaje original` y cabecera multicanal), mostrar la insignia `✓ Publicado en: {redes}`.
    - En cada tarjeta de red social (`LinkedIn`, `X`, `Discord`): si la red ya fue publicada, marcarla como `✓ Publicado en {Red}` y deshabilitar su botón de publicación individual; si la red NO fue publicada, mantenerla plenamente editable, regenerable y publicable.
    - Asegurar que al publicar un canal (individual o HITL), se actualice el estado local para retirar el mensaje de la bandeja pero mantenerlo activo en la mesa de trabajo con su nueva insignia.
  - **Hecho cuando:** `npm run build` en `frontend/` compile con código 0 y la mesa de trabajo refleje el comportamiento reactivo.

- [x] **Tarea 4: Frontend Historias Destacadas del Dashboard (`FeaturedStories.tsx`)**
  - **Archivos:** `frontend/src/components/FeaturedStories.tsx`
  - **Acción:**
    - Si `!currentStory.is_published`: ocultar insignias de publicación y mostrar únicamente el botón `"Generar publicación"`.
    - Si `currentStory.is_published`: mostrar la insignia `✓ Publicado en: {redes}`.
    - Calcular las redes faltantes respecto a `["Discord", "LinkedIn", "X"]`:
      - Si faltan redes: mostrar el botón `"Publicar en demás redes (" + faltantes.join(', ') + ")"`.
      - Si ya está en las 3 redes: mostrar `"Ver publicación en mesa de trabajo"`.
    - Redireccionar a `/content?interaction={targetId}`.
  - **Hecho cuando:** `npm run build` en `frontend/` compile sin errores.

- [x] **Tarea 5: Frontend Ingesta de Mensajes (`Messages.tsx`)**
  - **Archivos:** `frontend/src/pages/Messages.tsx`
  - **Acción:**
    - Adaptar tipos `ApiMessage` y `MessageItem` para incluir `isPublished` y `publishedPlatforms`.
    - Actualizar `isCompleted` para que reconozca los mensajes con `isPublished === true` o `workflowStage === 'publicado'`, garantizando que aparezcan bajo `"Todos los estados"` y `"Proceso completo"`.
    - En cada tarjeta de mensaje: si `isPublished`, exhibir la insignia `✓ Publicado en: {redes}` y el botón de acción con paridad a Historias Destacadas (`"Publicar en demás redes (...)"` o `"Ver en mesa de trabajo"`), mientras que los analizados no publicados muestran solo `"Generar publicación"`.
  - **Hecho cuando:** `npm run build` en `frontend/` compile limpiamente y los filtros muestren los mensajes publicados.

- [x] **Tarea 6: Verificación Global de Regresión, Compilación e Inviolabilidad Constitucional**
  - **Acción:**
    - Ejecutar suite global `pytest tests/test_unificacion_motor_ia.py` (100% pruebas en verde).
    - Ejecutar `npm run build` en `frontend/` (0 errores de TypeScript).
    - Verificar `git status` para confirmar inmutabilidad estricta de los 17 archivos de la raíz, `src/`, `backend/` y `motor-ia/`.
    - Actualizar `MEMORY.md`.
  - **Hecho cuando:** Todo el flujo esté verificado y listo para entrega.
