# Spec 016 — Trazabilidad Multicanal de Publicaciones en Redacción, Historias Destacadas e Ingesta de Mensajes

- **Estado:** Borrador para Revisión de QA (@reviewer)
- **Fecha:** 2026-10-19
- **Autor:** @planner
- **Rama objetivo:** `feature/integracion-motor-ia`

---

## 1. Contexto y Objetivo de Negocio (QUÉ y POR QUÉ)

### ¿Qué se necesita?
Unificar y sincronizar de extremo a extremo la trazabilidad por red social (`Discord`, `LinkedIn`, `X`) de cada mensaje publicado en las tres vistas operativas de la plataforma:
1. **Redacción de Contenidos (`/content`):** Retirar de la `"Bandeja de mensajes en Redacción"` cualquier mensaje que ya haya sido publicado en al menos una de las 3 redes sociales, pero mantenerlo activo en la `"Mesa de trabajo"` marcando explícitamente en qué red(es) social(es) fue publicado y conservando habilitadas las tarjetas de las redes restantes para que pueda publicarse en ellas.
2. **Dashboard — Historias Destacadas (`/dashboard`):** Mostrar en las historias ya publicadas en qué red(es) social(es) se publicaron y ofrecer la opción de publicarlas en las demás redes faltantes; en las historias que aún no han sido publicadas, mostrar únicamente el botón `"Generar publicación"` para enviarlas a la mesa de trabajo.
3. **Ingesta de Mensajes (`/messages`):** Garantizar que todo mensaje con publicación aparezca en el listado general (`Mostrando N mensajes en total (Todos los mensajes)`) tanto bajo el filtro `"Todos los estados"` como bajo `"Proceso completo"`, exhibiendo exactamente las mismas insignias de redes publicadas y opciones de publicación en redes restantes que aparecen en Historias Destacadas.

### ¿Por qué es necesario?
Actualmente, cuando un mensaje se publica desde la mesa de trabajo (ya sea mediante publicación individual por canal o mediante aprobación HITL global), la persistencia y visualización del estado de publicación entre pestañas es parcial:
- El usuario necesita que la **Bandeja de mensajes en Redacción** funcione como una cola limpia de pendientes (sin mensajes ya publicados en alguna red), mientras que la **Mesa de Trabajo** permita continuar publicando el mensaje activo en las redes sociales restantes sin perder sus borradores ni la visibilidad de las redes donde ya salió.
- Tanto en **Historias Destacadas** del Dashboard como en **Ingesta de Mensajes**, el equipo requiere identificar de inmediato en qué redes sociales (`Discord`, `LinkedIn`, `X`) ya fue publicado un mensaje y contar con un acceso directo para publicarlo en las redes faltantes, además de auditar todos los mensajes publicados bajo el filtro `"Proceso completo"`.

---

## 2. Requerimientos Funcionales (Formato EARS)

### RF-001: Persistencia Unificada de Publicación por Red Social en Base de Datos Local
- **CUANDO** el usuario ejecute una publicación individual por canal (`POST /api/v1/mototradis/publish-channel` o `/api/v1/content-workflow/publish-channel`) o una aprobación global HITL (`POST /api/v1/mototradis/hitl-decision` o `/api/v1/content-workflow/hitl-decision`) y el despacho hacia una o más redes sociales (`discord`, `linkedin`, `x`) sea exitoso, **EL SISTEMA DEBERÁ** registrar de forma persistente en la tabla SQLite `contenidos_generados` cada red social publicada (`estado = 'publicado'`, `estado_publicacion = 'publicado'`, `publicado_en = timestamp`), actualizar la interacción correspondiente en la tabla `interacciones` (`etapa_flujo = 'publicado'`, `estado_curaduria = 'curated'`) e invalidar de inmediato la caché en memoria de resúmenes y mensajes.
- **POR QUÉ:** Garantiza una fuente única de verdad persistente para las 3 redes sociales que sobrevive recargas de navegador y sincroniza instantáneamente las vistas de Redacción, Dashboard e Ingesta de Mensajes.

### RF-002: Exposición de Plataformas Publicadas y Preservación de Borradores en el Checkpoint de Mesa de Trabajo
- **CUANDO** el frontend consulte el estado de un mensaje para la Mesa de Trabajo Multicanal (`GET /api/v1/mototradis/checkpoint/{id_mensaje}`), **EL SISTEMA DEBERÁ** devolver la lista `plataformas_publicadas` con los identificadores canónicos de las redes donde dicho mensaje ya fue publicado (`discord`, `linkedin`, `x`), y **MIENTRAS** el mensaje tenga una o más redes publicadas, **EL SISTEMA DEBERÁ** preservar íntegros los objetos `borradores_ui` y `copys_generados` sin vaciarlos.
- **POR QUÉ:** Permite que al abrir o mantener en la mesa de trabajo un mensaje ya publicado en 1 o 2 redes sociales, el usuario conserve sus textos generados/editados y pueda publicarlo en las redes sociales restantes.

### RF-003: Trazabilidad de Redes Publicadas en Endpoints de Mensajes e Historias Destacadas
- **CUANDO** se consulten los endpoints de listado de mensajes (`GET /api/community/messages`) y de resumen en vivo del Dashboard (`GET /api/v1/community/live-summary` y `GET /api/community/summary`), **EL SISTEMA DEBERÁ** exponer en cada mensaje e historia destacada los campos `is_published: bool` y `published_platforms: list[str]` con los nombres legibles y ordenados de las redes donde ya fue publicado (`Discord`, `LinkedIn`, `X`), excluyendo los registros de anuncios oficiales generales sin interacción asociada (`interaccion_id IS NULL` o vacío).
- **POR QUÉ:** Alimenta de forma consistente y sin ambigüedades las insignias de redes publicadas y la lógica de botones tanto en Dashboard (`FeaturedStories`) como en Ingesta de Mensajes (`Messages`) y Redacción (`ContentStudio`).

### RF-004: Exclusión Automática de la Bandeja de Mensajes en Redacción tras Publicación
- **CUANDO** un mensaje haya sido publicado exitosamente en **cualquiera** de las 3 redes sociales (1, 2 o las 3 plataformas), **EL SISTEMA DEBERÁ** retirarlo y excluirlo inmediatamente de la sección `"Bandeja de mensajes en Redacción"` en la pestaña Redacción de Contenidos (`/content`), asegurando que dicha bandeja liste únicamente interacciones pendientes que aún no tienen ninguna publicación.
- **POR QUÉ:** Mantiene la Bandeja de Redacción limpia y enfocada exclusivamente en los mensajes que aún no han tenido difusión en ninguna red social.

### RF-005: Permanencia en Mesa de Trabajo con Insignia de Redes Publicadas y Publicación en Redes Restantes
- **CUANDO** el mensaje activo en la `"Mesa de trabajo"` de Redacción de Contenidos (`/content`) sea publicado en una o más redes sociales, o **CUANDO** el usuario navegue hacia `/content?interaction={id}` desde el Dashboard o desde Ingesta de Mensajes para un mensaje ya publicado, **EL SISTEMA DEBERÁ**:
  1. Mantener el mensaje cargado en la `"Mesa de trabajo"` (`Mensaje original de Discord` y `Mesa de Trabajo Multicanal`) aunque ya no aparezca en la `"Bandeja de mensajes en Redacción"`.
  2. Mostrar en el encabezado de la mesa de trabajo una insignia visible de que el mensaje ya fue publicado indicando explícitamente en qué red(es) social(es) lo fue (ej. `✓ Publicado en: Discord` o `✓ Publicado en: Discord, LinkedIn`).
  3. Marcar cada tarjeta de canal donde ya fue publicado con el estado `✓ Publicado en {Red}` y mantener habilitadas las tarjetas de las redes sociales restantes para su generación, edición y publicación individual o global.
- **POR QUÉ:** Permite que el usuario verifique en la mesa de trabajo qué canales ya fueron cubiertos y complete la publicación en las demás redes sociales sin perder el contexto del mensaje activo.

### RF-006: Insignias por Red Social y Opciones de Acción en Historias Destacadas del Dashboard
- **MIENTRAS** el usuario visualice las tarjetas de `"Historias destacadas"` en la pestaña Dashboard (`/dashboard`):
  1. **SI** la historia aún no ha sido publicada en ninguna red social (`is_published === false`), **EL SISTEMA DEBERÁ** ocultar cualquier insignia de publicación y mostrar únicamente el botón `"Generar publicación"`, el cual redirigirá a `/content?interaction={id}` para abrir el mensaje en la mesa de trabajo de Redacción de Contenidos.
  2. **SI** la historia ya fue publicada en al menos una red social (`is_published === true`), **EL SISTEMA DEBERÁ** mostrar una insignia indicando explícitamente en qué red(es) social(es) fue publicada (ej. `✓ Publicado en: Discord`) y mostrar un botón de acción que dé la opción de publicarla en las demás redes sociales pendientes (ej. `"Publicar en demás redes (LinkedIn, X)"` cuando falten redes por publicar, o `"Ver publicación en mesa de trabajo"` cuando ya haya sido publicada en las 3 redes), redirigiendo a `/content?interaction={id}`.
- **POR QUÉ:** Informa al usuario en el Dashboard qué historias ya fueron difundidas y en qué canales, habilitando el flujo directo hacia la mesa de trabajo para publicarlas en las redes restantes o enviar por primera vez las no publicadas.

### RF-007: Visibilidad de Mensajes Publicados en "Todos los estados" y "Proceso completo" en Ingesta de Mensajes
- **CUANDO** un mensaje tenga al menos una publicación registrada en cualquiera de las 3 redes sociales (`isPublished === true`), **EL SISTEMA DEBERÁ** reconocer su estado en la pestaña `"Ingesta de mensajes"` (`/messages`) como `"Proceso completo"` (`isCompleted = true`, nunca como pendiente de copy ni como descartado), contabilizarlo en el resumen de mensajes `Completos` y mostrarlo dentro del listado principal (`Mostrando N mensajes en total (Todos los mensajes)`) tanto cuando el filtro `"Estado del mensaje"` esté en `"Todos los estados"` como cuando esté en `"Proceso completo"`.
- **POR QUÉ:** Asegura que todo mensaje que ya cuenta con publicación sea considerado un proceso completo dentro del ciclo de vida de la plataforma y sea siempre auditable bajo los filtros `"Todos los estados"` y `"Proceso completo"`.

### RF-008: Paridad de Insignias y Opciones de Publicación entre Historias Destacadas e Ingesta de Mensajes
- **MIENTRAS** el usuario consulte el listado de mensajes en la pestaña `"Ingesta de mensajes"` (`/messages`):
  1. **SI** el mensaje ya cuenta con publicación en una o más redes sociales (`isPublished === true`), **EL SISTEMA DEBERÁ** mostrar en su tarjeta exactamente las mismas insignias y opciones de acción que tienen los mensajes publicados en Historias Destacadas del Dashboard: la insignia explícita con las redes sociales donde ya fue publicado (`✓ Publicado en: {redes}`) y el botón para publicarlo en las demás redes pendientes (`"Publicar en demás redes (...)"` si faltan redes por publicar, o `"Ver publicación en mesa de trabajo"` si ya se publicó en las 3 redes), redirigiendo a `/content?interaction={id}`.
  2. **SI** el mensaje ya fue analizado por la IA (y no está descartado) pero aún no tiene publicación (`isPublished === false`), **EL SISTEMA DEBERÁ** mostrar únicamente el botón `"Generar publicación"` para enviarlo a la mesa de trabajo en `/content?interaction={id}`.
- **POR QUÉ:** Proporciona paridad visual y funcional absoluta entre las tarjetas de Historias Destacadas en el Dashboard y las tarjetas de Ingesta de Mensajes.

### RF-009: Inviolabilidad Constitucional de Archivos Protegidos
- **MIENTRAS** se implementen las mejoras de trazabilidad multicanal, **EL SISTEMA DEBERÁ** preservar sin modificaciones los 17 archivos protegidos de la raíz, los módulos originales de `src/`, `backend/` y `motor-ia/`, realizando toda adaptación de servidor en `puente_motor_ia.py` y toda adaptación de interfaz en `frontend/src/`.
- **POR QUÉ:** Garantiza el cumplimiento estricto de `docs/constitution.md` y `AGENTS.md`, evitando regresiones en los motores base de IA y almacenamiento.

---

## 3. Criterios de Aceptación y Escenarios de Verificación

1. **Publicación en 1 red social (ej. Discord) desde la Mesa de Trabajo:**
   - El mensaje desaparece de inmediato de la `"Bandeja de mensajes en Redacción"` en `/content`.
   - El mensaje permanece abierto en la `"Mesa de trabajo"` mostrando `✓ Publicado en: Discord`, la tarjeta de Discord marcada como publicada y las tarjetas de `LinkedIn` y `X` listas para publicar.
2. **Verificación en Dashboard (`Historias destacadas`):**
   - El mensaje recién publicado en Discord aparece con la insignia `✓ Publicado en: Discord` y el botón `"Publicar en demás redes (LinkedIn, X)"`, que al pulsarse lleva a `/content?interaction={id}` cargando el mensaje en la mesa de trabajo con sus borradores intactos.
   - Los mensajes en Historias Destacadas que aún no han sido publicados muestran únicamente el botón `"Generar publicación"`.
3. **Verificación en Ingesta de Mensajes (`/messages`):**
   - El mensaje publicado aparece en `Mostrando N mensajes en total (Todos los mensajes)` tanto cuando el filtro `"Estado del mensaje"` está en `"Todos los estados"` como cuando está en `"Proceso completo"`.
   - Su tarjeta exhibe la insignia `✓ Publicado en: Discord` y el botón `"Publicar en demás redes (LinkedIn, X)"` (idéntico a Historias Destacadas), redirigiendo a la mesa de trabajo en `/content?interaction={id}`.
4. **Publicación completada en las 3 redes (`Discord, LinkedIn, X`):**
   - La insignia en Mesa de Trabajo, Historias Destacadas e Ingesta de Mensajes muestra `✓ Publicado en: Discord, LinkedIn, X` y el botón ofrece `"Ver publicación en mesa de trabajo"`.
