# Tareas de Implementación — Spec 020: Homologación Visual Integral con el Prototipo y Design System CloudEdTech Preservando Funcionalidades Reales e IA

## T1: Fase Red TDD en `tests/test_unificacion_motor_ia.py` (~15 min)
- **Archivos involucrados:**
  - `tests/test_unificacion_motor_ia.py`
- **Requerimientos Funcionales:** `RF-01`, `RF-02`, `RF-03`, `RF-04`, `RF-05`, `RF-06`, `RF-07`, `RF-08`, `RF-09`
- **Descripción:**
  1. Escribir las pruebas automatizadas de la Spec 020 en `tests/test_unificacion_motor_ia.py` validando:
     - Clases completas del CommunityLab Design System en `frontend/src/index.css` (`.c-tabs`, `.c-tab`, `.c-segmented`, `.c-stat__spark`, `.c-chart__center`, `.c-legend--stack`, `.draft-item`, `.c-iconbox`, `.c-modal`, `.c-code`).
     - Sparklines en `KpiCard.tsx`, selector `.c-segmented` (`7d`, `30d`, `90d`) en `Dashboard.tsx`, centro interactivo `.c-chart__center` en `SentimentChart.tsx`, `Peak` horario en `AudienceHeatmap.tsx` y barras horizontales con toggle en `TopicsChart.tsx`.
     - Barra de 3 pestañas `.c-tabs` (`Bandeja`, `Anuncios oficiales`, `Quejas y soporte`) en `ContentStudio.tsx`, activación automática de `complaints` con `#panel-quejas`, layout Maestro-Detalle `.draft-item`, campos `Título` y `Tono` + tabla `Anuncios recientes`, y **preservación obligatoria de los selectores e insignias de los 3 modelos de IA (`Groq`, `Gemma`, `Gemini`), buscador por ID (`pinnedSearchMessage`) y las 3 redes de Enoc (`Discord`, `LinkedIn`, `X`)**.
     - Gráfico semanal de barras y modal visor `Ver JSON` en `OCIStorage.tsx`, y preservación de selectores de IA en `Messages.tsx`.
  2. Ejecutar `pytest` y confirmar que los nuevos tests fallan inicialmente (Fase Red TDD).
- **Hecho cuando:** Las pruebas de la Spec 020 existen en `tests/test_unificacion_motor_ia.py` y su ejecución muestra el fallo esperado antes de modificar el frontend.

---

## T2: Integración Completa de `components.css` y `layout.css` en `frontend/src/index.css` (~15 min)
- **Archivos involucrados:**
  - `frontend/src/index.css`
- **Requerimientos Funcionales:** `RF-01`
- **Descripción:**
  1. Incorporar en `frontend/src/index.css` todas las clases estructurales y de componentes del CommunityLab Design System de Cristian (`components.css` y `layout.css`): `.l-page-head`, `.l-grid--main-side`, `.l-grid--side-main`, `.l-grid--halves`, `.c-stat`, `.c-stat__spark`, `.c-iconbox` (y variantes `--success`, `--info`, `--danger`, `--accent`, `--neutral`), `.c-tabs`, `.c-tab`, `.c-tab__count`, `.c-segmented`, `.c-pill` (y variantes), `.c-tag--channel`, `.c-avatar` (y tonos), `.c-table`, `.c-chart__center`, `.c-legend--stack`, `.draft-item`, `.c-msg`, `.c-chip`, `.c-modal`, `.c-code`, `.c-dl` y `.c-progress`.
- **Hecho cuando:** `frontend/src/index.css` expone todas las clases del prototipo `app.html` de Cristian sin conflictos con Tailwind y las aserciones de CSS en `pytest` pasan en verde.

---

## T3: Homologación del Dashboard Ejecutivo y sus 6 Gráficas con Sparklines (`Dashboard.tsx`, `KpiCard.tsx`, `charts/*`) (~20 min)
- **Archivos involucrados:**
  - `frontend/src/components/KpiCard.tsx`
  - `frontend/src/pages/Dashboard.tsx`
  - `frontend/src/charts/SentimentChart.tsx`
  - `frontend/src/charts/SentimentEvolution.tsx`
  - `frontend/src/charts/AudienceHeatmap.tsx`
  - `frontend/src/charts/TopicsChart.tsx`
  - `frontend/src/components/dashboard/FeaturedStories.tsx`
- **Requerimientos Funcionales:** `RF-02`, `RF-03`, `RF-04`, `RF-09`
- **Descripción:**
  1. Actualizar `KpiCard.tsx` al formato `.c-card` + `.c-stat` con `.c-iconbox` semántico arriba a la derecha y **Sparkline SVG suave con área degradada** (`.c-stat__spark`) en la base de las 6 tarjetas.
  2. En `Dashboard.tsx`, estructurar `.l-page-head` con `.c-live` (`● En vivo`), selector `.c-segmented` (`7d`, `30d`, `90d`) y botón `.c-btn--primary` naranja `#FF7400`; y organizar las filas exactamente como en la captura 1 de Cristian:
     - Fila 1 (`l-grid--main-side`): `Actividad de mensajes` (área suave naranja `Mensajes` + curva índigo `Preguntas` con píldora de delta y leyenda `.c-legend`) + `Sentimiento de la comunidad` (`SentimentChart.tsx` con dona `cutout: 72%`, **centro interactivo `.c-chart__center`** que cambia porcentaje y categoría al pasar el mouse, y leyenda apilada `.c-legend--stack`).
     - Fila 2 (`l-grid--halves`): `Evolución del sentimiento` (`SentimentEvolution.tsx` con curvas `0%–100%` Positivo/Neutral/Negativo) + `Actividad de audiencia` (`AudienceHeatmap.tsx` con píldora `Peak HH:00` y barras verticales por hora `00:00–23:00` destacando la hora pico en `#FF7400` y el resto en `#FDBA74`).
     - Fila 3 (`l-grid--halves`): `Temas principales` (`TopicsChart.tsx` con botón `Ordenar por crecimiento / volumen` y barras horizontales en `#FF7400` / `#FDBA74`) + `Historias destacadas` (`FeaturedStories.tsx` con `.score-ring`), conservando debajo `Participación por canal`.
- **Hecho cuando:** `Dashboard.tsx` y sus gráficas reproducen el diseño exacto de la captura 1 de Cristian alimentados al 100% por datos reales con protección contra división por cero.

---

## T4: Redacción de Contenidos — Barra de 3 Pestañas `.c-tabs` y Pestaña 1 (`Bandeja` Maestro-Detalle) Conservando Buscador ID, Lote Masivo, 3 Redes y 3 Modelos de IA (`ContentStudio.tsx`) (~20 min)
- **Archivos involucrados:**
  - `frontend/src/pages/ContentStudio.tsx`
- **Requerimientos Funcionales:** `RF-01`, `RF-05`, `RF-09`
- **Descripción:**
  1. Incorporar la barra de 3 pestañas horizontales `.c-tabs` (`Bandeja`, `Anuncios oficiales`, `Quejas y soporte`) con contadores `.c-tab__count` en vivo, activando automáticamente `Bandeja` cuando haya `?interaction={id}` y `Quejas y soporte` cuando se navegue a `#panel-quejas`.
  2. Estructurar el panel `Bandeja` con el layout Maestro-Detalle de 2 columnas (`.l-grid--side-main`) de la captura de Cristian:
     - **Columna Izquierda (`.c-card--flush`):** Cabecera con título `Bandeja de mensajes en Redacción`, integrando con estilo del Design System el **Buscador por ID (`Cargar ID`)** y el control de **Procesamiento Masivo (`< 35` con Gemma 4)**, seguido de la lista vertical `.draft-item` con avatar circular de iniciales, autor, `#ID · #canal · relevancia` y píldora de estado, manteniendo intacto `pinnedSearchMessage` (`📌 Cargado por ID #N` y desaparición inmediata al editar el buscador).
     - **Columna Derecha (`.l-stack--sm`):** Arriba la tarjeta `Mensaje original de Discord` (con `.c-tag--channel`, avatar, autor, texto, sentimiento, tema e **insignia/selector del modelo de IA**); abajo la tarjeta `Contenido generado` conservando las **3 redes de Enoc (`Discord`, `LinkedIn`, `X`)**, el **selector e insignia de los 3 modelos de IA (`Groq (Llama 3.3)`, `Google Gemma 4`, `Google Gemini Flash Lite`)**, el área de edición con contador de caracteres y el pie `.c-card__footer` con `Copiar`, `Regenerar`, `Rechazar` y `✓ Aprobar / Publicar`.
- **Hecho cuando:** La pestaña `Bandeja` luce como la captura Maestro-Detalle de Cristian y conserva al 100% el buscador por ID con sincronización dinámica, el lote masivo, las 3 redes de Enoc y los selectores/insignias de los 3 modelos de IA.

---

## T5: Redacción de Contenidos — Pestaña 2 (`Anuncios oficiales`) y Pestaña 3 (`Quejas y soporte`) Fieles a las Capturas Conservando Selectores e Insignias de IA (`ContentStudio.tsx`) (~20 min)
- **Archivos involucrados:**
  - `frontend/src/pages/ContentStudio.tsx`
- **Requerimientos Funcionales:** `RF-01`, `RF-06`, `RF-09`
- **Descripción:**
  1. En la pestaña **`Anuncios oficiales`**, implementar el layout de 2 columnas (`.l-grid--halves`) idéntico a la captura subida por el usuario:
     - **Izquierda (`.c-card--lg`):** Cabecera con `.c-iconbox` naranja de megáfono, campo `Título`, fila `.l-grid--2` con `Canal` y `Tono` (`Cercano`, `Formal`, `Entusiasta`), **selector e insignia visible del modelo de IA (`Groq (Llama 3.3)`, `Google Gemma 4`, `Google Gemini Flash Lite`)**, textarea de indicaciones/cuerpo y botones `✨ Generar con IA` (`.c-btn--secondary`) y `✈️ Publicar en Discord` (`.c-btn--primary`).
     - **Derecha (`.l-stack--sm`):** Arriba `Vista previa` con `.discord-embed` (`CE`, `CloudEdTech_Oficial`, pill índigo `BOT`, `📣 ${announcementTitle}` y cuerpo en vivo) y abajo `Anuncios recientes` con tabla compacta `.c-table--compact` (`ANUNCIO`, `ESTADO`, `ALCANCE / CANAL`).
  2. En la pestaña **`Quejas y soporte`** (`id="panel-quejas"`), implementar la tarjeta `.c-card--flush` idéntica a la captura subida por el usuario:
     - Cabecera con `.c-iconbox--danger`, título `Panel de Quejas, Reclamos y Soporte Crítico` y **selector e insignia del modelo de IA (`Groq / Gemma 4 / Gemini`)**.
     - Filas `.c-msg` con avatar de iniciales, autor, `.c-tag--channel`, `#ID · fecha`, píldoras de prioridad (`Crítica`, `Alta`, `Media`) y estado (`● Sin responder`, `● En curso`, `● Publicada`), texto de la queja en caja gris `--surface-muted`, campo `Respuesta sugerida` con **insignia de la IA generadora** y botones `✨ Generar respuesta` y `✈️ Publicar respuesta`.
- **Hecho cuando:** Las pestañas `Anuncios oficiales` y `Quejas y soporte` reproducen el diseño exacto de las dos capturas subidas por el usuario y mantienen 100% visibles y funcionales los selectores e insignias de los 3 modelos de IA.

---

## T6: Homologación de Informes OCI (`OCIStorage.tsx`), Ingesta (`Messages.tsx`) y Análisis (`Analytics.tsx`) (~20 min)
- **Archivos involucrados:**
  - `frontend/src/pages/OCIStorage.tsx`
  - `frontend/src/pages/Messages.tsx`
  - `frontend/src/pages/Analytics.tsx`
- **Requerimientos Funcionales:** `RF-01`, `RF-07`, `RF-08`, `RF-09`
- **Descripción:**
  1. En `OCIStorage.tsx` (idéntico a la 3ª captura subida por el usuario):
     - Fila superior (`.l-grid--side-main`): a la izquierda tarjeta `.c-card--brand` (`OCI Object Storage`, píldora `● Conectado`, `<dl class="c-dl">` con `Bucket`, `Región`, `Namespace / Modo`, `Último sync` y barra `.c-meter` inferior); a la derecha tarjeta `📦 Reporte Semanal y Distribución (OCI)` con botones `📄 Generar reporte` y `☁️ Sincronizar con OCI` y **gráfico de barras verticales por semana (`W...`)** en `#FF7400` / `#FDBA74`.
     - Fila inferior: tabla `.c-table` `Historial de Informes Semanales` con modal visor `.c-modal` (`👁 Ver JSON` con código formateado `.c-code` y `Copiar JSON`), descarga e integración OCI.
  2. En `Messages.tsx`: 4 tarjetas `.c-stat` con `.c-iconbox`, panel de Lote IA con **selector e insignia de los 3 modelos de IA (`Groq / Gemma 4 / Gemini`)** y barra `.c-meter`, filtros con chips `.c-chip` y filas `.c-msg` con avatar, `.c-tag--channel`, **insignia del modelo de IA**, mini barra de relevancia y botón hacia Redacción.
  3. En `Analytics.tsx`: tarjeta `Métricas globales de curaduría` con 4 medidores `.c-meter`, fila central con `Evolución del sentimiento` + `Insight destacado` `.c-card--brand` (3 bloques oscuros + botón a `#panel-quejas`), `Scorecards de Emojis` `.emoji-card` y fila inferior con `Hashtags más populares` (barras horizontales con `.c-segmented` `Volumen / Crecimiento`) y `Temas clave`.
- **Hecho cuando:** `OCIStorage.tsx`, `Messages.tsx` y `Analytics.tsx` lucen idénticos al prototipo de Cristian, manteniendo todos los selectores e insignias de IA y conectados 100% a datos reales.

---

## T7: Verificación Integral (Fase Green TDD), Compilación de Producción y Actualización de `MEMORY.md` (~15 min)
- **Archivos involucrados:**
  - `tests/test_unificacion_motor_ia.py`
  - `MEMORY.md`
- **Requerimientos Funcionales:** `RF-01` a `RF-09`
- **Descripción:**
  1. Ejecutar `pytest tests/test_unificacion_motor_ia.py` verificando que el 100% de los tests pasen en verde.
  2. Ejecutar `npm run build` en `frontend/` verificando 0 errores de TypeScript o empaquetado.
  3. Comprobar con `git status` que los 17 archivos protegidos de la raíz, `backend/`, `motor-ia/` y `src/` permanezcan intactos.
  4. Actualizar `MEMORY.md` documentando los logros de la Spec 020.
- **Hecho cuando:** `pytest` pasa al 100% en verde, `npm run build` finaliza con exit code 0, `git status` confirma 0 modificaciones en archivos protegidos y `MEMORY.md` está actualizado.
