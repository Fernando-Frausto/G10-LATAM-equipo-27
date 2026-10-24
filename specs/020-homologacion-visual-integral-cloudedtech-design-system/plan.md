# Plan de Implementación — Spec 020: Homologación Visual Integral con el Prototipo y Design System CloudEdTech de Cristian Preservando Funcionalidades Reales e IA

## 1. Resumen Arquitectónico y Regla de Oro

El objetivo técnico de la **Spec 020** es homologar visualmente al 100% las vistas productivas de React (`frontend/src/`) con el prototipo `cloudedtech-design-system/cloudedtech-ds/app.html` (`components.css`, `layout.css`, `charts.js`) de Cristian, cumpliendo estrictamente dos principios inquebrantables:

1. **Regla de Oro — Preservación Absoluta de Selectores de IA, Insignias de IA y Funcionalidades de Producción (`RF-01`):**
   - **PROHIBIDO eliminar o esconder** los selectores de modelo de IA (`Groq (Llama 3.3)`, `Google Gemma 4`, `Google Gemini Flash Lite`) o las insignias que muestran con qué modelo de IA se analizó o redactó cada mensaje, borrador, anuncio o respuesta a queja.
   - **PROHIBIDO eliminar** el buscador por ID (`Cargar ID`) con sincronización e inyección temporal (`📌 Cargado por ID #N` y desaparición instantánea al editar el input), el procesamiento masivo `< 35` con Gemma 4, las 3 redes sociales de la Mesa de Trabajo de Enoc (`Discord`, `LinkedIn`, `X`), la telemetría de bots omitidos vs. mensajes humanos reales y la sección de participación por canal.
   - Todos estos elementos se mantienen 100% operativos y conectados a los endpoints reales del backend, adoptando las clases nativas del CommunityLab Design System (`.c-card`, `.c-select`, `.c-input`, `.c-pill`, `.c-btn`, `.c-iconbox`, `.c-tabs`).
2. **Inviolabilidad Constitucional y Cero Mocks (`RF-09`):**
   - Cero modificaciones a los 17 archivos protegidos de la raíz, `backend/`, `motor-ia/` y `src/`.
   - Prohibición absoluta de importar `js/data.js` (`window.CE_DATA`); todas las gráficas y tablas consumen los datos reales de la API con blindaje matemático contra división por cero (`max || 1`, `total || 1`).

---

## 2. Diseño Técnico Detallado por Componente y Archivo

### 2.1 Hoja de Estilos Unificada del CommunityLab Design System (`frontend/src/index.css`)
- Incorporar las reglas completas de `cloudedtech-ds/css/components.css` y `cloudedtech-ds/css/layout.css` en `frontend/src/index.css` para que todas las vistas dispongan nativamente de:
  - **Tipografía:** `.t-page`, `.t-page--xl`, `.t-section`, `.t-card`, `.t-body`, `.t-muted`, `.t-caption`, `.t-overline`, `.t-kpi`, `.t-mono`, `.t-brand`, `.t-success`, `.t-danger`.
  - **Layouts y Grillas:** `.l-page-head`, `.l-page-head__text`, `.l-page-head__actions`, `.l-stack`, `.l-stack--sm`, `.l-grid`, `.l-grid--2`, `.l-grid--3`, `.l-grid--4`, `.l-grid--6`, `.l-grid--main-side` (2fr 1fr), `.l-grid--side-main` (1fr 2fr), `.l-grid--halves` (1fr 1fr), `.l-cluster`, `.l-between`.
  - **Tarjetas y Estadísticas:** `.c-card`, `.c-card--lg`, `.c-card--flush`, `.c-card--muted`, `.c-card--brand`, `.c-card--interactive`, `.c-card__header`, `.c-card__desc`, `.c-card__footer`, `.c-card__section`, `.c-stat`, `.c-stat__label`, `.c-stat__value`, `.c-stat__meta`, `.c-stat__spark`, `.c-trend`, `.c-trend--up`, `.c-trend--down`.
  - **Controles y Navegación:** `.c-btn` (`--primary`, `--secondary`, `--soft`, `--ghost`, `--danger`, `--success`, `--sm`, `--icon`), `.c-input`, `.c-select`, `.c-textarea`, `.c-input-group`, `.c-field`, `.c-label`, `.c-tabs`, `.c-tab` (`.is-active`, `.c-tab__count`), `.c-segmented` (`button.is-active`), `.c-chip` (`.is-active`, `.c-chip__n`), `.c-toolbar`.
  - **Píldoras, Iconboxes y Avatares:** `.c-pill` (`--brand`, `--success`, `--warning`, `--danger`, `--info`, `--accent`, `--outline`, `--dot`), `.c-tag`, `.c-tag--channel`, `.c-iconbox` (`--success`, `--info`, `--danger`, `--accent`, `--neutral`, `--sm`), `.c-avatar` (`--sm`, `--lg`, `--soft`, `--slate`, `--indigo`, `--emerald`, `--purple`).
  - **Listas, Tablas, Gráficas y Modales:** `.c-msg`, `.draft-item` (`.is-active` con `#FFF7ED` e `inset 3px 0 0 #FF7400`), `.c-table-wrap`, `.c-table` (`--compact`, `.is-right`, `.is-strong`), `.c-chart` (`--sm`, `--lg`, `--donut`, `.c-chart__center`), `.c-legend` (`--stack`, `.c-legend__item`, `.c-legend__swatch`, `.c-legend__value`), `.c-modal` (`.is-open`, `.c-modal__dialog`, `.c-code`), `.discord-embed`, `.emoji-card`, `.score-ring`, `.c-meter`, `.c-progress` (`--sm`, `--success`, `--danger`, `--info`).

### 2.2 Tarjetas KPI con Sparkline (`frontend/src/components/KpiCard.tsx`) (`RF-02`)
- Rediseñar `KpiCard.tsx` con la estructura `.c-card` + `.c-stat` de Cristian:
  - Parte superior izquierda: `.c-stat__label` (`title`), `.c-stat__value.t-kpi` (`value` tabular), `.c-stat__meta` (con `.c-trend--up` / `.c-trend--down` o texto semántico / enlace `Por aprobar →`).
  - Parte superior derecha: `.c-iconbox` con variante semántica (`iconKind`: naranja por defecto, `success`, `info`, `danger`, `accent`, `neutral`).
  - Parte inferior (`.c-stat__spark`, `height: 36px`): Renderizado de un **gráfico Sparkline SVG de curva suave Bezier** con área degradada vertical (`linearGradient` de opacidad `0.28` a `0`) y trazo de `2px` en el color semántico de la tarjeta (`#FF7400`, `#6366F1`, `#10B981`, `#FB923C`, `#A855F7`, `#F43F5E`), alimentado por una serie derivada de los datos reales de la métrica (con protección `max || 1`).

### 2.3 Gráficas del Dashboard (`frontend/src/pages/Dashboard.tsx` y `frontend/src/charts/*`) (`RF-02`, `RF-03`, `RF-04`)
- **Cabecera (`Dashboard.tsx`):**
  - `.l-page-head` con título `Dashboard`, subtítulo `Resumen de la actividad de la comunidad CloudEdTech en Discord.`, indicador `.c-live` (`● En vivo`), selector `.c-segmented` de período (`7d`, `30d`, `90d`) que filtra/escala reactivamente la ventana temporal y botón `.c-btn.c-btn--primary` `Sincronizar Discord` / `Actualizar datos`.
- **Fila Superior — 6 KPIs (`.l-grid.l-grid--6`):**
  - `Mensajes procesados`, `Total de audiencia`, `Sentimiento positivo`, `Temas detectados`, `Contenidos generados` y `Pendientes`, cada uno con su Sparkline semántico.
- **Fila 1 de Gráficas (`.l-grid.l-grid--main-side` — 2/3 + 1/3) (`RF-03`):**
  1. **Izquierda (`Actividad de mensajes`):** Tarjeta `.c-card` con cabecera, píldora `.c-pill.c-pill--success` con el delta porcentual real, gráfico de área suave Recharts/SVG con degradado naranja `#FF7400` para `Mensajes` y curva índigo `#6366F1` para `Preguntas` (calculadas a partir de los mensajes e interrogantes reales por fecha), y leyenda clicable `.c-legend` (`■ Mensajes`, `■ Preguntas`).
  2. **Derecha (`Sentimiento de la comunidad` — `SentimentChart.tsx`):** Tarjeta `.c-card` con subtítulo `Pasa el mouse por cada segmento.`, gráfico de dona con `cutout` de `72%` (`innerRadius="72%"`, `outerRadius="92%"`) en colores exactos (`Positivo: #10B981`, `Neutral: #94A3B8`, `Pregunta: #6366F1`, `Negativo: #EF4444`), **centro flotante `.c-chart__center`** que muestra en grande el porcentaje (`72%`) y la categoría (`Positivo`) y se actualiza dinámicamente en `onMouseEnter` / `onMouseLeave` de cada segmento o leyenda, acompañado abajo por la leyenda apilada `.c-legend.c-legend--stack` con punto de color, nombre y porcentaje tabular a la derecha (`total || 1`).
- **Fila 2 de Gráficas (`.l-grid.l-grid--halves` — 1/2 + 1/2) (`RF-04`):**
  1. **Izquierda (`Evolución del sentimiento` — `SentimentEvolution.tsx`):** Gráfico de áreas suaves (`0%` a `100%`) con degradado esmeralda bajo `Positivo` (`#10B981`), línea gris `Neutral` (`#94A3B8`) y línea roja `Negativo` (`#EF4444`), más leyenda `.c-legend` inferior.
  2. **Derecha (`Actividad de audiencia` — `AudienceHeatmap.tsx`):** Cabecera con título `Actividad de audiencia`, subtítulo `Mensajes promedio por hora del día.` y píldora `.c-pill.c-pill--brand` `Peak HH:00` (calculada de la hora real con más mensajes). Gráfico de **barras verticales por hora (`00:00` a `23:00`)** donde la barra de mayor volumen se pinta en naranja sólido `#FF7400` y las demás en naranja pastel `#FDBA74` (`rgb(255 116 0 / 0.35)`).
- **Fila 3 de Gráficas (`.l-grid.l-grid--halves` — 1/2 + 1/2) (`RF-04`):**
  1. **Izquierda (`Temas principales` — `TopicsChart.tsx`):** Cabecera con título `Temas principales`, subtítulo `Menciones en el período.` y botón `.c-btn.c-btn--ghost.c-btn--sm` `⇅ Ordenar por crecimiento` / `Ordenar por volumen`. Gráfico de **barras horizontales** redondeadas donde el tema #1 se pinta en `#FF7400` y los demás en `#FDBA74`.
  2. **Derecha (`Historias destacadas` — `FeaturedStories.tsx`):** Lista compacta con `.score-ring` cónico, título/extracto, `autor · #canal`, píldora de tipo/estado (`✓ Publicado en...`) y botón hacia Redacción de Contenidos. Debajo se conserva íntegra la sección de `Participación por canal` (`ChannelParticipation.tsx`) estilizada con `.c-card` y `.c-meter`.

### 2.4 Redacción de Contenidos con 3 Pestañas `.c-tabs`, Maestro-Detalle, Anuncios y Quejas (`frontend/src/pages/ContentStudio.tsx`) (`RF-05`, `RF-06`)
- **Cabecera y Barra de 3 Pestañas (`.c-tabs`):**
  - Cabecera `.l-page-head` con título `Redacción de Contenidos`, subtítulo `Convierte conversaciones destacadas en contenido, anuncios y respuestas oficiales.` y píldora `.c-pill.c-pill--success.c-pill--dot` `Webhook Discord conectado`.
  - Estado `activeTab: 'inbox' | 'announcements' | 'complaints'`:
    - Por defecto `'inbox'`.
    - **Aclaración QA 1 (Enrutamiento contextual):** Si la URL contiene `?interaction={id}`, se asegura `activeTab = 'inbox'`. Si `location.hash === '#panel-quejas'`, un `useEffect` cambia automáticamente `activeTab = 'complaints'` y desplaza suavemente la vista hacia `#panel-quejas`.
  - Barra `.c-tabs` con los 3 botones `.c-tab`:
    1. `Bandeja` con contador `.c-tab__count` (`workflowMessages.length`).
    2. `Anuncios oficiales` con contador `.c-tab__count` (`recentAnnouncements.length`).
    3. `Quejas y soporte` con contador `.c-tab__count` (`complaints.length`).

- **Pestaña 1: `Bandeja` (`activeTab === 'inbox'`) — Layout Maestro-Detalle (`.l-grid.l-grid--side-main`) (`RF-05`):**
  - **Columna Izquierda (`Bandeja de mensajes en Redacción` — `.c-card.c-card--flush`):**
    - `.c-card__section` superior con título `Bandeja de mensajes en Redacción`, subtítulo `Selecciona un borrador para revisarlo.` y barra compacta integrada con el **Buscador por ID (`Cargar ID`)** (`.c-input` + `.c-btn--primary.c-btn--sm`) y el botón/panel de **Procesamiento Masivo (`< 35` con Gemma 4)** estilizados con el Design System.
    - Lista vertical de items `.draft-item` renderizando `displayedTrayMessages`:
      * Mantiene al 100% la lógica de `pinnedSearchMessage`: si el ID buscado está en `workflowMessages`, se selecciona y hace `scrollIntoView`; si existe en la BD pero no en `workflowMessages`, se inyecta al inicio con insignia `📌 Cargado por ID #${msg.id}` y se selecciona; al cambiar o borrar el número en el buscador (`onChange` de `manualIdInput`), `pinnedSearchMessage` desaparece inmediatamente de la bandeja.
      * Cada `.draft-item` muestra avatar `.c-avatar.c-avatar--sm` con iniciales y tono por autor, nombre del autor en negrita, subtítulo `#${msg.id} · #${msg.channel} · ${msg.relevanceScore}% rel.` y píldora `.c-pill` de estado (`Pendiente`, `En revisión`, `Aprobado`). El item activo lleva `.is-active` (`background: #FFF7ED; box-shadow: inset 3px 0 0 #FF7400`).
  - **Columna Derecha (`.l-stack.l-stack--sm`):**
    - **Arriba (`Mensaje original de Discord` — `.c-card`):** Cabecera con título `Mensaje original de Discord`, etiqueta `.c-tag.c-tag--channel` a la derecha, avatar con iniciales, autor, fecha, texto del mensaje original y fila `.c-msg__meta` con píldora de sentimiento, píldora de tema, **insignia del modelo de IA evaluador** y botón/selector para evaluar con cualquiera de los 3 modelos de IA si aplica.
    - **Abajo (`Contenido generado` — `.c-card`):**
      * Cabecera con título `Contenido generado`, **selector e insignia visible de los 3 modelos de IA (`Groq (Llama 3.3)`, `Google Gemma 4`, `Google Gemini Flash Lite`)** y selector/pestañas de las **3 redes sociales del pipeline de Enoc (`Discord`, `LinkedIn`, `X`)** con sus píldoras de estado (`Pendiente`, `✓ Publicado en {Red}` con link directo, o alerta de error con reintento).
      * Área de texto `.c-textarea` editable con el borrador de la red activa (o vista de las 3 redes) y pie `.c-card__footer` con contador de caracteres en vivo (`${chars} caracteres`) a la izquierda y a la derecha los botones exactos del prototipo: `Copiar` (`.c-btn--ghost.c-btn--sm`), `Regenerar` (`.c-btn--secondary.c-btn--sm` usando el modelo de IA seleccionado), `Rechazar` (`.c-btn--danger.c-btn--sm`) y `✓ Aprobar / Publicar` (`.c-btn--success.c-btn--sm` / despacho individual o HITL global).

- **Pestaña 2: `Anuncios oficiales` (`activeTab === 'announcements'`) — Layout 2 Columnas (`.l-grid.l-grid--halves`) (`RF-06`):**
  - **Columna Izquierda (`Panel de Anuncios Oficiales de la Comunidad (Discord Webhook)` — `.c-card.c-card--lg`):**
    - Cabecera con `.c-iconbox` naranja de megáfono, título `Panel de Anuncios Oficiales de la Comunidad (Discord Webhook)` y subtítulo `Genera el anuncio con IA, revísalo y publícalo en el canal elegido.`.
    - Campo `Título` (`.c-input`, ej. `Demo Day de proyectos de la comunidad`), fila `.l-grid.l-grid--2` con `Canal` (`.c-select` con los canales reales encabezados por `#notificaciones`) y `Tono` (`.c-select`: `Cercano`, `Formal`, `Entusiasta`), más el **selector e insignia del modelo de IA (`Groq (Llama 3.3)`, `Google Gemma 4`, `Google Gemini Flash Lite`)** 100% visible y funcional.
    - Campo `Indicaciones para la IA / Cuerpo del anuncio` (`.c-textarea`) con contador y semáforo 1500/2000 caracteres.
    - Pie alineado a la derecha con los botones `✨ Generar con IA` (`.c-btn.c-btn--secondary`, que pasa el `Título`, `Tono` e indicaciones al motor de IA seleccionado) y `✈️ Publicar en Discord` (`.c-btn.c-btn--primary`).
  - **Columna Derecha (`.l-stack.l-stack--sm`):**
    - **Arriba (`Vista previa` — `.c-card`):** Bloque `.discord-embed` con `.discord-embed__bot` (`CE`, `CloudEdTech_Oficial`, pill índigo `BOT`, `Hoy`), título en negrita `📣 ${announcementTitle}` y cuerpo en tiempo real `${announcementText}`.
    - **Abajo (`Anuncios recientes` — `.c-card.c-card--flush`):** Tabla `.c-table.c-table--compact` con columnas `ANUNCIO` (título en negrita + `#canal · fecha`), `ESTADO` (píldora `.c-pill--success.c-pill--dot` `Publicado` o `Listo`) y `ALCANCE / CANAL` a la derecha, actualizándose en vivo al publicar un anuncio.

- **Pestaña 3: `Quejas y soporte` (`activeTab === 'complaints'`, `id="panel-quejas"`) (`RF-06`):**
  - Tarjeta `.c-card.c-card--flush` con `.c-card__section` superior que muestra `.c-iconbox.c-iconbox--danger` (icono de alerta), título `Panel de Quejas, Reclamos y Soporte Crítico`, subtítulo `Mensajes con sentimiento negativo o problemas de plataforma que requieren respuesta oficial.` y a la derecha el **selector e insignia del modelo de IA (`Groq (Llama 3.3)`, `Google Gemma 4`, `Google Gemini Flash Lite`)** junto al botón de actualizar.
  - Lista vertical de quejas reales donde cada fila `.c-msg` (`flex-direction: column`) muestra:
    - Cabecera `.l-between` con avatar circular `.c-avatar.c-avatar--sm` con iniciales, nombre del autor, etiqueta `.c-tag.c-tag--channel`, `#${c.id} · ${c.fecha}` a la izquierda; y a la derecha píldora de prioridad (`Crítica` en rojo, `Alta` en ámbar, `Media` en índigo, derivada de urgencia/sentimiento), píldora de estado con punto (`● Sin responder`, `● En curso`, `● Publicada`) e **insignia del modelo de IA** cuando se ha generado borrador.
    - Texto de la queja en caja gris suave (`padding: var(--space-3); background: var(--surface-muted); border-radius: var(--radius-lg)`).
    - Campo `.c-field` con etiqueta `Respuesta sugerida` (mostrando con qué modelo de IA se redactó) y `.c-textarea` editable.
    - Botones inferiores alineados a la derecha: `✨ Generar respuesta` (`.c-btn.c-btn--secondary.c-btn--sm`) y `✈️ Publicar respuesta` (`.c-btn.c-btn--primary.c-btn--sm` naranja `#FF7400`).

### 2.5 Informes y Almacenamiento OCI (`frontend/src/pages/OCIStorage.tsx`) (`RF-07`)
- **Fila Superior (`.l-grid.l-grid--side-main`):**
  1. **Izquierda (`.c-card.c-card--brand`):** Cabecera con `.c-iconbox` de nube, título blanco `OCI Object Storage` y píldora `.c-pill--success.c-pill--dot` (`Conectado`) o `.c-pill--warning.c-pill--dot` (`Modo Local`). Lista `<dl class="c-dl">` con `Bucket`, `Región`, `Namespace / Modo` y `Último sync` (datos reales de `/api/v1/oci-storage/status`), más medidor inferior `.c-meter` con barra `.c-progress` naranja mostrando los reportes sincronizados en el bucket.
  2. **Derecha (`.c-card.c-card--lg` — `📦 Reporte Semanal y Distribución (OCI)`):** Cabecera con período actual en negrita, botones `📄 Generar reporte` (`.c-btn.c-btn--secondary`) y `☁️ Sincronizar con OCI` (`.c-btn.c-btn--primary` naranja `#FF7400`), y debajo un **gráfico de barras verticales por semana (`W...`)** construido a partir de los reportes reales del historial (`reports`), donde la semana con mayor volumen de mensajes resalta en `#FF7400` y las demás en `#FDBA74` (`max || 1`).
- **Fila Inferior (`.c-card.c-card--flush` — `Historial de Informes Semanales`):**
  - Tabla `.c-table` con columnas `SEMANA` (código monoespaciado en negrita + fechas/estado), `MENSAJES`, `TAMAÑO`, `GENERADO`, `ESTADO` (píldora `✅ Subido a OCI` o `💾 Respaldo Local`) y `ACCIONES` a la derecha:
    * Botón `👁 Ver JSON` (`.c-btn--secondary.c-btn--sm`) que abre el modal `.c-modal.is-open` con bloque oscuro `.c-code` coloreado y botón `Copiar JSON`.
    * Botón de icono `.c-btn--secondary.c-btn--icon.c-btn--sm` para descargar el JSON.
    * Botón `.c-btn--primary.c-btn--sm` `☁️ Subir a OCI` / `🔄 Reintentar OCI`.

### 2.6 Ingesta de Mensajes y Análisis Homologados (`frontend/src/pages/Messages.tsx`, `frontend/src/pages/Analytics.tsx`) (`RF-08`)
- **`Messages.tsx`:**
  - 4 tarjetas superiores `.c-stat` con `.c-iconbox` (`Analizados`, `Positivos`, `Preguntas`, `Destacados`) + indicadores reales de mensajes humanos y bots omitidos.
  - Tarjeta `.c-card.c-card--lg` `Evaluación por Lote con Inteligencia Artificial` con `.c-iconbox` naranja, píldora `.c-pill--warning.c-pill--dot` (`N pendientes`), barra `.c-toolbar` con selector `.c-select` de tamaño de lote, **selector `.c-select` e insignia del modelo de IA (`Groq (Llama 3.3)`, `Google Gemma 4`, `Google Gemini Flash Lite`)**, botón `.c-btn--primary` `⚡ Evaluar lote` y medidor `.c-meter` con `.c-progress`.
  - Tarjeta `.c-card.c-card--flush` `Panel de filtrado de mensajes` con `.c-toolbar` (buscador `.c-input-group`, canal, sentimiento, estado), fila de chips `.c-chip` con contadores `.c-chip__n` y lista `.c-msg` donde cada mensaje muestra avatar `.c-avatar` coloreado por autor, `#canal`, fecha, texto, píldoras de sentimiento/tema/estado, **insignia del modelo de IA evaluador (y selector individual para evaluar si está pendiente)**, columna derecha `.c-msg__score` con puntaje tabular, mini barra `.c-progress--sm` naranja y botón hacia Redacción (`✎ Redactar` / `Generar publicación`).
- **`Analytics.tsx`:**
  - Tarjeta superior `.c-card.c-card--lg` `Métricas globales de curaduría` con grilla `.l-grid--4` de 4 medidores `.c-meter` (`Mensajes analizados` naranja, `Sentimiento positivo` verde `--success`, `Relevancia promedio` índigo `--info`, `Alertas activas` rojo `--danger`).
  - Fila central `.l-grid--main-side` (2/3 + 1/3): a la izquierda `Evolución del sentimiento` y a la derecha `Insight destacado` `.c-card--brand` con los 3 bloques oscuros (`Principal`, `Preguntas frecuentes`, `Atención requerida` alimentados por datos reales) y el botón de acción hacia `#panel-quejas`.
  - Tarjeta `Scorecards de Emojis Destacados en la Comunidad` con grilla `.l-grid--6` de tarjetas `.c-card--muted.emoji-card`.
  - Fila inferior `.l-grid--halves`: a la izquierda `Hashtags más populares` con barras horizontales y selector `.c-segmented` (`Volumen` / `Crecimiento`), y a la derecha `Temas clave detectados en la comunidad`.

---

## 3. Estrategia de Pruebas (TDD) y Verificación (`tests/test_unificacion_motor_ia.py`)

Se añadirán pruebas automatizadas en `tests/test_unificacion_motor_ia.py` para verificar:
1. Presencia de las clases estructurales del CommunityLab Design System en `frontend/src/index.css` (`.c-tabs`, `.c-tab`, `.c-segmented`, `.c-stat__spark`, `.c-chart__center`, `.c-legend--stack`, `.draft-item`, `.c-iconbox`, `.c-modal`, `.c-code`).
2. En `KpiCard.tsx` y `Dashboard.tsx`: renderizado de sparklines (`.c-stat__spark`), selector `.c-segmented` (`7d`, `30d`, `90d`), dona de sentimiento (`SentimentChart.tsx`) con centro interactivo `.c-chart__center` y leyenda `.c-legend--stack`, barras por hora con `Peak` en `AudienceHeatmap.tsx` y barras horizontales con ordenamiento en `TopicsChart.tsx`.
3. En `ContentStudio.tsx`: presencia de las 3 pestañas `.c-tabs` (`Bandeja`, `Anuncios oficiales`, `Quejas y soporte`), activación automática de `complaints` ante `#panel-quejas`, preservación intacta de `pinnedSearchMessage` (`📌 Cargado por ID #`) y su desaparición al cambiar el input, **preservación obligatoria de los selectores e insignias de los 3 modelos de IA (`Groq`, `Gemma`, `Gemini`)** y de las 3 redes (`Discord`, `LinkedIn`, `X`), campos `Título` y `Tono` + tabla `Anuncios recientes` en Anuncios, y tarjetas de quejas con `Respuesta sugerida` en Quejas.
4. En `OCIStorage.tsx`, `Messages.tsx` y `Analytics.tsx`: gráfico semanal de barras y visor modal JSON en OCI, preservación del selector de IA en `Messages.tsx` y estructura de 4 medidores `.c-meter` en `Analytics.tsx`.
