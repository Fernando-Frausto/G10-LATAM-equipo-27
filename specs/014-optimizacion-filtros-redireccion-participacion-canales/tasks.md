# Tareas de Implementación: Spec 014 - Optimización de Filtros, Redirección a Publicación y Participación por Canal en Dashboard

Lista de tareas secuenciales de ~20 minutos cada una siguiendo la metodología Test-Driven Development (TDD) y el principio de inviolabilidad constitucional de código legado.

---

### [x] Tarea 1: Fase Red TDD — Pruebas Automatizadas de Backend (RF-03, RF-06)
- **Estimación**: ~20 minutos
- **Requerimientos**: RF-03, RF-06
- **Descripción**: Crear la batería de tests unitarios y de integración en `tests/test_unificacion_motor_ia.py` que especifiquen el comportamiento del nuevo endpoint de participación por canal antes de escribir el código en el adaptador.
- **Detalle técnico**:
  1. Diseñar `test_participacion_canales_discord_calculo_y_orden`:
     - Invoca `GET /api/community/channel-participation` mediante `TestClient(app)`.
     - Verifica respuesta HTTP 200 con campos `total_messages` y `channels`.
     - Valida que `channels` contenga exactamente 6 elementos en el orden canónico estricto: `#general`, `#faq`, `#pqrs`, `#notificaciones`, `#chat-egresados`, `#oportunidades-laborales`.
     - Valida que la suma de porcentajes sea exactamente 100.0%.
  2. Diseñar `test_participacion_canales_discord_corpus_vacio`:
     - Mockea o aísla una consulta con 0 interacciones en la base de datos.
     - Verifica que la API responda HTTP 200 con `total_messages: 0` y los 6 canales con `count: 0` y `percentage: 0.0`, sin lanzar `ZeroDivisionError`.
  3. Diseñar `test_participacion_canales_exclusion_bots_y_alias`:
     - Verifica que las interacciones con autor bot o formato webhook sean excluidas de los conteos.
     - Valida que el alias `GET /api/v1/community/channels-participation` responda con idéntica estructura y datos.
- **Hecho cuando**: Los tests nuevos están escritos en `tests/test_unificacion_motor_ia.py` y fallan de manera predecible con código HTTP 404 (Fase Red) al no existir aún el endpoint en `puente_motor_ia.py`, sin romper los 112 tests preexistentes del proyecto.

---

### [x] Tarea 2: Fase Green Backend — Implementación en `puente_motor_ia.py` (RF-03, RF-06)
- **Estimación**: ~20 minutos
- **Requerimientos**: RF-03, RF-06
- **Descripción**: Implementar en `puente_motor_ia.py` el endpoint `GET /api/community/channel-participation` y su alias canónico, con normalización de canales, exclusión de bots y blindaje contra `ZeroDivisionError`.
- **Detalle técnico**:
  1. Definir la lista constante `CANALES_OFICIALES_DISCORD` con los 6 canales y su orden oficial estricto.
  2. Implementar la función `obtener_participacion_canales()`:
     - Consultar interacciones disponibles en SQLite (`communitylab.db`) y Supabase.
     - Filtrar mensajes excluyendo bots y webhooks (`es_mensaje_bot_o_webhook` y autores terminados en `#0000` o con `'bot'`).
     - Normalizar nombres de canal (`canal.lstrip('#').strip().lower()`) y mapear sinónimos conocidos (ej. `'preguntas'`, `'dudas'` a `'faq'`).
     - Contabilizar los mensajes para cada uno de los 6 canales oficiales y computar `total_messages`.
     - Si `total_messages == 0`, asignar `0.0%` y conteo `0` para cada canal.
     - Si `total_messages > 0`, calcular el porcentaje con un decimal y ajustar la diferencia residual de redondeo sobre el canal mayoritario para garantizar suma 100.0%.
  3. Registrar las rutas FastAPI:
     - `@app.get("/api/community/channel-participation")`
     - `@app.get("/api/v1/community/channels-participation")`
- **Hecho cuando**: Todos los nuevos tests de la Tarea 1 pasan a verde (`pytest tests/test_unificacion_motor_ia.py` al 100% exitoso), superando los 112 tests previos sin regresiones.

---

### [x] Tarea 3: Frontend — API Client y Componente `ChannelParticipation.tsx` en `Dashboard.tsx` (RF-03, RF-04, RF-05)
- **Estimación**: ~20 minutos
- **Requerimientos**: RF-03, RF-04, RF-05
- **Descripción**: Crear los tipos y función de cliente en `communityLive.ts`, diseñar el componente modular `ChannelParticipation.tsx` y montarlo reactivamente en `Dashboard.tsx`.
- **Detalle técnico**:
  1. En `frontend/src/api/communityLive.ts`:
     - Declarar `ChannelParticipationItem` y `ChannelParticipationResponse`.
     - Implementar `getChannelParticipation()` con consumo del endpoint y fallback resiliente con los 6 canales en 0.0% ante fallos.
  2. Crear `frontend/src/components/ChannelParticipation.tsx`:
     - Contenedor con borde `border-slate-200`, fondo blanco y esquinas redondeadas.
     - Encabezado: glifo `#` con estilo acento naranja (`text-orange-500 font-bold text-lg`), título *"Participación por canal"* y subtítulo *"Distribución de mensajes registrados en los seis canales de Discord"*.
     - Desglose de los 6 canales en orden estricto: `#general`, `#faq`, `#pqrs`, `#notificaciones`, `#chat-egresados`, `#oportunidades-laborales`.
     - Fila de cada canal: nombre a la izquierda, `{percentage.toFixed(1)}% · {count}` a la derecha, barra horizontal gris con relleno naranja proporcional (`width: 0%` estricto si conteo es 0).
  3. En `frontend/src/pages/Dashboard.tsx`:
     - Importar y montar `<ChannelParticipation key={`channels-${analyticsVersion}`} />` en el layout principal.
     - Comprobar que el botón *"Actualizar datos"* refresque el componente reactivamente vía `analyticsVersion`.
- **Hecho cuando**: La pantalla del Dashboard exhibe la nueva tarjeta de participación por canal con diseño idéntico al solicitado, conectada a datos reales y reactiva al botón de actualización.

---

### [x] Tarea 4: Frontend — Ingesta de Mensajes: Botón Publicación, Redirección y Unificación de Filtros en `Messages.tsx` (RF-01, RF-02)
- **Estimación**: ~20 minutos
- **Requerimientos**: RF-01, RF-02
- **Descripción**: Actualizar las tarjetas de mensaje en `Messages.tsx` para suprimir el botón *"Analytics"* e incluir el botón *"Generar publicación"* con navegación contextual, y depurar el panel de filtros unificando el selector bajo *"Estado del mensaje"* con precedencia humana.
- **Detalle técnico**:
  1. En las tarjetas de mensaje de `frontend/src/pages/Messages.tsx`:
     - Eliminar el botón *"Analytics"*.
     - Para mensajes analizados (`isAnalyzed === true`), renderizar el botón *"Generar publicación"*:
       * Si `status === 'discarded'`, deshabilitarlo con `title="Restaura el mensaje para generar publicación"`.
       * Si `status !== 'discarded'`, habilitarlo para navegar a `/content?interaction=${message.interactionId}` con `{ state: { interactionId: message.interactionId } }`.
       * Si `relevance < 70` pero no está descartado, permitir la navegación para habilitar la redacción forzada de Enoc.
  2. En el panel de filtrado de `frontend/src/pages/Messages.tsx`:
     - Eliminar el selector redundante `stageFilter` situado al lado de *"Todos los sentimientos"*.
     - Actualizar el selector bajo *"Estado del mensaje"* (`curationFilter`) con las 5 opciones exactas en orden:
       1. `Todos los estados` (`all`)
       2. `Pendientes de evaluar` (`pending_eval`)
       3. `Pendientes de copy` (`pending_copy`)
       4. `Proceso completo` (`completos`)
       5. `Descartado` (`descartados`)
     - Implementar la lógica de filtrado con precedencia humana (HITL): `curationStatus` manual prevalece sobre la IA. Si un mensaje con baja relevancia es restaurado a `'pending'`, sale de descartados e ingresa a *"Pendientes de copy"*.
     - Adaptar el rótulo de conteo en la cabecera de la cola para reflejar con exactitud la opción activa (`'mensajes descartados'`, `'mensajes pendientes de evaluar'`, `'mensajes en la cola de copy'`, `'mensajes con proceso completo'`, `'mensajes en total (Todos los mensajes)'`).
     - Asegurar que el botón *"Deseleccionar"* restablezca el filtro a `'all'`.
- **Hecho cuando**: Las tarjetas muestran *"Generar publicación"* al estar analizadas y navegan hacia `/content?interaction=ID`; el panel de filtros posee únicamente el selector bajo *"Estado del mensaje"* con las 5 opciones en orden, filtrando con precisión fidedigna.

---

### [x] Tarea 5: Verificación Global, Compilación Limpia e Inviolabilidad Constitucional (RF-06)
- **Estimación**: ~20 minutos
- **Requerimientos**: RF-06
- **Descripción**: Ejecutar la verificación integral de pruebas automatizadas, compilación de TypeScript y comprobación de inmutabilidad git para certificar cero regresiones.
- **Detalle técnico**:
  1. Ejecutar la suite completa de pruebas de backend: `pytest tests/ -v`, comprobando que el 100% de los tests (preexistentes y nuevos) pasen en verde.
  2. Ejecutar la compilación del frontend: `npm run build` en `frontend/`, comprobando cero advertencias o errores de tipado de TypeScript.
  3. Ejecutar la comprobación git de inmutabilidad:
     - `git diff --exit-code <archivos_raiz>`
     - `git diff --exit-code backend motor-ia`
     garantizando que ninguno de los 17 archivos preexistentes ni carpetas legadas haya sido modificado.
- **Hecho cuando**: El 100% de las pruebas automatizadas pasa en verde, el frontend compila sin errores y se confirma la estricta inmutabilidad de los archivos constitucionales protegidos.
