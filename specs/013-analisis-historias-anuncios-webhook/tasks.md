# Tareas de Implementación: Spec 013 - Análisis Integral, Historias Destacadas del Dashboard y Webhook de Anuncios en Redacción

Lista de tareas secuenciales de ~20 minutos cada una siguiendo la metodología Test-Driven Development (TDD) y el principio de inviolabilidad constitucional de código legado.

---

### [x] Tarea 1: Fase Red TDD — Pruebas Automatizadas de Backend (RF-02, RF-03, RF-04, RF-06, RF-07, RF-08, RF-09)
- **Descripción**: Crear la batería de tests unitarios y de integración en `tests/test_unificacion_motor_ia.py` que especifiquen el comportamiento esperado antes de escribir el código de backend.
- **Detalle técnico**:
  1. Test para `GET /api/community/analytics`: extracción de emojis Unicode (ZWJ), emojis de Discord (`<:name:id>` y `<a:name:id>`), cálculo de frecuencia, etiquetas semánticas y fallback contextual. Validación de `brand_alignment_percentage` y blindaje matemático determinista contra división por cero con corpus vacío (`analizados: 0`).
  2. Test para `GET /api/v1/community/live-summary` y alias `GET /api/community/summary`: paridad idéntica de respuesta, filtrado riguroso de autores de prueba (`usuario_uno`, `usuario_tres`, prefijo `usuario_`, `test_`, IDs 31 y 34), e inclusión de metadatos `is_published` y `published_platforms`.
  3. Test para `GET /api/v1/content-workflow/announcements/status`: verificación de estado de webhook y límites (1500/2000 chars).
  4. Test para `POST /api/v1/content-workflow/announcements/generate`: rechazo HTTP 400 ante borradores vacíos o mayores a 10,000 caracteres, y mock de delegación hacia `anuncios_discord.generar_anuncio`.
  5. Test para `POST /api/v1/content-workflow/announcements/publish`: rechazo HTTP 400 ante confirmación falsa o exceso de 2000 caracteres, HTTP 503 ante ausencia de webhook, mock de despacho a Discord e inserción del registro en la tabla SQLite `contenidos_generados` con formato `'discord'`, tipo `'anuncio_oficial'` y estado `'publicado'`.
- **Hecho cuando**: Los tests nuevos están definidos y fallan de manera predecible (Fase Red) al invocar endpoints o métodos aún no implementados, sin romper los 100 tests preexistentes del proyecto.

---

### [x] Tarea 2: Fase Green Backend — Implementación en `puente_motor_ia.py` (RF-02, RF-03, RF-04, RF-06, RF-07, RF-08, RF-09)
- **Descripción**: Implementar en `puente_motor_ia.py` todos los adaptadores, cálculos de telemetría y endpoints REST requeridos para satisfacer la Tarea 1.
- **Detalle técnico**:
  1. Sobrescribir limpiamente el handler de `GET /api/community/analytics` integrando el algoritmo de extracción de emojis (Unicode ZWJ y sintaxis Discord), catálogo semántico, cálculo de `brand_alignment_percentage` y salvaguarda contra `ZeroDivisionError`.
  2. Depurar el constructor de `highlights` en `GET /api/v1/community/live-summary` para excluir autores sintéticos (`usuario_uno`, `usuario_tres`, prefijos `usuario_`, IDs 31 y 34), consultar estado de publicación en SQLite y registrar el alias canónico `@app.get("/api/community/summary")`.
  3. Registrar `GET /api/v1/content-workflow/announcements/status` reportando la disponibilidad de `DISCORD_WEBHOOK_ANUNCIOS`.
  4. Registrar `POST /api/v1/content-workflow/announcements/generate` validando $\le 10,000$ caracteres y delegando en `anuncios_discord.generar_anuncio` sin alterar `anuncios_discord.py`.
  5. Registrar `POST /api/v1/content-workflow/announcements/publish` validando $\le 2000$ caracteres y confirmación explícita, delegando en `anuncios_discord.publicar_en_discord` e insertando la auditoría en `contenidos_generados` de SQLite.
- **Hecho cuando**: Todos los nuevos tests de la Tarea 1 pasan a verde (`pytest tests/test_unificacion_motor_ia.py` al 100% exitoso).

---

### [x] Tarea 3: Frontend — Servicios Tipados y Pestaña de Análisis (`Analytics.tsx`) (RF-01, RF-02, RF-03)
- **Descripción**: Actualizar los clientes de API y depurar la pestaña de Análisis erradicando secciones obsoletas y conectando telemetría real de emojis.
- **Detalle técnico**:
  1. Enriquecer `frontend/src/api/communityLive.ts` y `contentWorkflow.ts` con tipos e interfaces para `EmojiScorecard`, analíticas enriquecidas y contratos de webhook de anuncios.
  2. En `frontend/src/pages/Analytics.tsx`: suprimir por completo el bloque "Bandeja de mensajes en Análisis" y la sección "Revisión de mensajes y curaduría", eliminando dependencias de `updateMessageCuration` y `updateMessageWorkflow`.
  3. Conectar el mapeo dinámico de "Scorecards de Emojis Destacados en la Comunidad" a la propiedad `emojis` proveniente de la API, mostrando glifo, frecuencia, sentimiento (esmeralda, azul, rosa), etiqueta semántica y variación porcentual, con estado vacío elegante si no hay datos.
  4. Actualizar el banner informativo final con el texto fidedigno de CloudEdTech y asegurar la operatividad de todos los enlaces restantes.
- **Hecho cuando**: La vista `/analytics` compila sin errores, muestra emojis reales de Discord calculados por el backend, no contiene componentes de curaduría huérfanos y exhibe el texto informativo oficial.

---

### [x] Tarea 4: Frontend — Historias Destacadas del Dashboard (`FeaturedStories.tsx`) (RF-04, RF-05)
- **Descripción**: Optimizar el componente del carrusel en el Dashboard para garantizar historias reales, navegación contextual a Redacción y visibilidad del estado de publicación.
- **Detalle técnico**:
  1. Suprimir el botón "Ver mensaje" de `FeaturedStories.tsx`.
  2. Implementar la navegación contextual en el botón "Generar publicación": redirigir a `/content?interaction={id}` transfiriendo el identificador numérico (`currentStory.id_mensaje || currentStory.id`) tanto por query param como por `location.state`.
  3. Resiliencia de carrusel vacío: si `stories.length === 0` o `currentStory.id === 0`, deshabilitar la acción y mostrar el texto "Sin historias disponibles".
  4. Indicador de publicación: si `currentStory.is_published === true`, desplegar la insignia `"✓ Publicado en " + plataformas`, y cambiar la etiqueta del botón de acción a `"Volver a publicar"` (o `"Publicar en otra plataforma"`).
- **Hecho cuando**: Al hacer clic en "Generar publicación", la aplicación redirige a `/content?interaction={id}` con el ID numérico correcto; no aparecen usuarios sintéticos en el carrusel y las historias publicadas muestran su insignia correspondiente.

---

### [x] Tarea 5: Frontend — Selección Contextual y Panel de Anuncios Webhook en `ContentStudio.tsx` (RF-05, RF-06, RF-07, RF-08)
- **Descripción**: Dotar a la mesa de trabajo de Enoc de selección automática de la interacción solicitada desde el Dashboard y añadir el panel completo de Anuncios Oficiales con webhook de Discord.
- **Detalle técnico**:
  1. En `frontend/src/pages/ContentStudio.tsx`, incorporar `useSearchParams` y `useLocation` para leer el parámetro `interaction`. Seleccionar automáticamente la interacción correspondiente en la bandeja de redacción y enfocar la tarjeta de "Mensaje original de Discord".
  2. Incorporar el panel "Anuncios Oficiales de la Comunidad (Discord Webhook)" inmediatamente antes de la "Bandeja de mensajes en Redacción".
  3. Consultar el estado del webhook al montar el componente; si `configured: false`, exhibir banner preventivo claro indicando que falta configurar `DISCORD_WEBHOOK_ANUNCIOS` en el servidor y bloquear el despacho.
  4. Implementar entrada de borrador: textarea manual y botón "Subir archivo .txt / .md" con validación de extensión y límite de 10,000 caracteres.
  5. Implementar botón "Generar anuncio con IA" conectado a `POST /api/v1/content-workflow/announcements/generate` con estados de carga y retroalimentación de errores.
  6. Disponer del "Editor del Anuncio Final" con contador reactivo y semáforo cromático: verde ($\le 1500$), ámbar ($1501-2000$) y rojo con bloqueo ($> 2000$).
  7. Implementar botón "Publicar anuncio en Discord" con modal de confirmación previa, llamada a `POST /api/v1/content-workflow/announcements/publish`, feedback visual de éxito e inserción auditada.
- **Hecho cuando**: Un redactor puede cargar un archivo `.txt`/`.md` o escribir un borrador, generar el anuncio con IA, ajustar el texto validando el semáforo y publicarlo en Discord con persistencia en SQLite; y al acceder con `?interaction={id}` la interacción solicitada queda seleccionada de inmediato.

---

### [x] Tarea 6: Verificación Global, Compilación Limpia e Inviolabilidad Constitucional (RF-09)
- **Descripción**: Ejecución integral de las pruebas del sistema, compilación estricta de TypeScript y verificación de inmutabilidad git para asegurar 0 regresiones.
- **Detalle técnico**:
  1. Ejecutar la suite completa de pruebas: `pytest tests/` (asegurando el 100% de tests en verde, superando los 100 tests anteriores).
  2. Ejecutar la compilación del frontend: `npm run build` en `frontend/` verificando 0 errores de tipado en TypeScript y bundle generado exitosamente.
  3. Ejecutar comprobación de inmutabilidad: `git diff --exit-code feature/ia-resultados-supabase -- <archivos_raiz>` y `git diff --exit-code 758ff6a -- backend motor-ia` garantizando 0 modificaciones en los 17 archivos preexistentes.
- **Hecho cuando**: El 100% de la suite de pruebas automatizadas está en verde, el frontend compila sin errores, no hay archivos protegidos alterados y la memoria del proyecto se encuentra lista para actualizarse.
