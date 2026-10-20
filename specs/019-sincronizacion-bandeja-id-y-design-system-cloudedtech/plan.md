# Plan de Implementación — Spec 019: Sincronización Dinámica de Bandeja por ID e Integración del Design System CloudEdTech con Datos Reales

## 1. Resumen Arquitectónico

La implementación de la **Spec 019** abarca dos pilares complementarios dentro del frontend productivo (`frontend/src/`), manteniendo inmutabilidad constitucional absoluta sobre los 17 archivos protegidos de la raíz, `backend/`, `motor-ia/` y `src/`:

1. **Sincronización Dinámica de la Bandeja de Mensajes en Redacción con el Buscador por ID (`RF-01`, `RF-02`):**
   - Gestión de estado reactiva en `frontend/src/pages/ContentStudio.tsx` mediante el estado `pinnedSearchMessage: WorkflowMessage | null` y la lista computada `displayedTrayMessages`.
   - Comportamiento determinista al buscar (`handleLoadById`) y al modificar el campo numérico (`onChange` de `manualIdInput`).
2. **Integración del Design System CloudEdTech de Cristian (`origin/feature/design-system-cloudedtech`, commit `c606071`) con 100% Datos Reales (`RF-03` a `RF-11`):**
   - Incorporación íntegra del directorio `cloudedtech-design-system/` al repositorio.
   - Adopción de tokens semánticos CSS, tipografía tabular (`tabular-nums`), clases utilitarias (`c-card--brand`, `score-ring`, `discord-embed`, `c-live`, `c-meter`) y accesibilidad en `frontend/src/index.css`.
   - Aplicación en `Sidebar.tsx`, `Login.tsx`, `Dashboard.tsx`, `FeaturedStories.tsx`, `ChannelParticipation.tsx`, `Messages.tsx`, `Analytics.tsx`, `ContentStudio.tsx` y `OCIStorage.tsx` conectados exclusivamente a los endpoints reales de la API (`communityLive.ts`).

---

## 2. Diseño Técnico por Requerimiento Funcional

### 2.1 Sincronización e Inyección Temporal en Bandeja de Redacción (`RF-01`, `RF-02`)
**Archivo:** `frontend/src/pages/ContentStudio.tsx`

- **Estado de Inyección Temporal:**
  - Se declarará `const [pinnedSearchMessage, setPinnedSearchMessage] = useState<WorkflowMessage | null>(null);`.
  - Se computará la lista de tarjetas renderizadas en la `Bandeja de mensajes en Redacción` mediante `displayedTrayMessages`:
    - Si `pinnedSearchMessage` existe y su `id` no se encuentra ya dentro de `workflowMessages`, `displayedTrayMessages` será `[pinnedSearchMessage, ...workflowMessages]`.
    - En caso contrario, `displayedTrayMessages` será `workflowMessages`.
  - El contador de cabecera `{workflowMessages.length} listos para copy` continuará evaluando `workflowMessages.length` para reflejar exclusivamente la cola natural pendiente.

- **Flujo en `handleLoadById` (`RF-01`):**
  1. Cuando el operador busca un ID válido (`targetId`):
     - **Caso A (Pertenece a `workflowMessages`):** Se limpia cualquier `pinnedSearchMessage` previo (`setPinnedSearchMessage(null)`), se asigna `setSelectedMessageId(inQueue.id)` y `setActiveWorkbenchMessage(inQueue)`, se actualiza `?interaction=${inQueue.id}` y se ejecuta `scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' })` sobre `trayCardRefs.current[inQueue.id]` y hacia `#original-message-card`.
     - **Caso B (Existe en `data.messages` o `data.ApprovalsAndContent.highlights` pero no está en `workflowMessages`):** Se construye el objeto `WorkflowMessage` (`resolved`), se guarda en `setPinnedSearchMessage(resolved)`, se selecciona (`setSelectedMessageId(resolved.id)`, `setActiveWorkbenchMessage(resolved)`), se actualiza `?interaction=${resolved.id}` y, tras el renderizado (`setTimeout`), se desplaza suavemente la bandeja horizontal hacia `trayCardRefs.current[resolved.id]` además de `#original-message-card`.
  2. En el renderizado de `displayedTrayMessages`, si `msg.id === pinnedSearchMessage?.id` y no pertenece a `workflowMessages`, la tarjeta mostrará una insignia superior distintiva `📌 Cargado por ID #${msg.id}` y se visualizará con el estado seleccionado (`isActive = true`).

- **Flujo al Modificar o Borrar el Buscador (`onChange` de `manualIdInput`) (`RF-02`):**
  - En el manejador `onChange` del input numérico de ID:
    1. Se actualiza `setManualIdInput(newVal)`.
    2. Si `pinnedSearchMessage !== null`:
       - Se ejecuta inmediatamente `setPinnedSearchMessage(null)` para que el mensaje inyectado temporalmente desaparezca al instante de la `Bandeja de mensajes en Redacción`.
       - Si el mensaje actualmente abierto en la Mesa de Trabajo (`activeWorkbenchMessage?.id` o `selectedMessageId`) era ese `pinnedSearchMessage.id`, se restablece la selección al primer elemento de la cola natural (`const firstNatural = workflowMessages[0] || null; setSelectedMessageId(firstNatural?.id ?? null); setActiveWorkbenchMessage(firstNatural);`) y se limpia el parámetro `?interaction=` de `searchParams`.
    3. Si el mensaje seleccionado pertenecía a la cola natural `workflowMessages`, permanece intacto en la bandeja tal como lo especificó QA.

### 2.2 Incorporación de Activos de Referencia del Design System (`RF-03`)
**Directorio:** `cloudedtech-design-system/`
- Se extraerá íntegramente el directorio `cloudedtech-design-system/` desde `origin/feature/design-system-cloudedtech` (`commit c606071`) hacia la raíz del repositorio para preservar la entrega documental y de referencia de Cristian sin alteraciones.

### 2.3 Tokens Semánticos, Números Tabulares y Clases del Design System (`RF-04`)
**Archivo:** `frontend/src/index.css`
- Integración en `:root` de los tokens de Cristian:
  - Marca y acento: `--orange-50` a `--orange-700` (`--orange-500: #ff7400`), `--navy-800` a `--navy-950` (`--navy-950: #080a27`).
  - Superficies y bordes: `--surface-app: #f8fafc`, `--surface-card: #ffffff`, `--surface-muted: #f1f5f9`, `--border-subtle: #e2e8f0`, `--border-strong: #cbd5e1`.
  - Sombras estratificadas: `--shadow-xs`, `--shadow-sm`, `--shadow-md`, `--shadow-lg`, `--shadow-focus: 0 0 0 3px rgb(255 116 0 / 0.22)`.
- Clases utilitarias del Design System:
  - `.tabular-nums` (`font-variant-numeric: tabular-nums`) aplicada a métricas, KPIs, badges y porcentajes.
  - `.c-card--brand`: Superficie oscura `linear-gradient(135deg, #0f172a 0%, #1e293b 100%)` con resplandor radial naranja `radial-gradient(circle at 85% 20%, rgb(255 116 0 / 0.18), transparent 55%)` y texto blanco.
  - `.score-ring`: Anillo circular cónico `background: conic-gradient(#ff7400 calc(var(--p, 0) * 1%), #f1f5f9 0)` con máscara interior blanca y porcentaje tabular.
  - `.c-live` y `.c-live__dot`: Indicador semántico en vivo con halo esmeralda (`box-shadow: 0 0 0 3px rgb(16 185 129 / 0.2)`).
  - `.c-meter`: Barra de progreso con relleno `linear-gradient(90deg, #ff7400, #ea580c)`.
  - `.discord-embed`: Contenedor de vista previa con `border-left: 4px solid #ff7400`, fondo `#f1f5f9`, avatar `CE` (`#080a27`), autor `CloudEdTech_Oficial` e insignia `BOT` (`#6366f1`).
  - `.c-tray-card--active`: Sombra interior lateral `box-shadow: inset 3px 0 0 #ff7400, var(--shadow-sm)` y borde `#ff7400`.
- Accesibilidad: `:focus-visible` con `outline: 2px solid #ff7400` y soporte para `@media (prefers-reduced-motion: reduce)`.

### 2.4 Identidad Vectorial SVG y Contadores Reales en Navegación y Login (`RF-05`)
**Archivos:** `frontend/src/components/layout/Sidebar.tsx`, `frontend/src/pages/Login.tsx`
- Creación de un componente reutilizable o renderizado inline del **Isotipo Vectorial Oficial SVG de CloudEdTech** diseñado por Cristian (rectángulo `#080A27`, nodos conectados en `#FF7400` y blanco, flecha ascendente de crecimiento en `#FF7400`) junto con el wordmark `CloudEdTech` (`Ed` en `#FF7400`) y subtítulo `EDUCATION & TECHNOLOGY` tanto en `Sidebar.tsx` (barra lateral desktop y barra superior móvil) como en `Login.tsx`.
- En `Sidebar.tsx`:
  - Consumo ligero y resiliente de `fetchCommunityOverview()` (aprovechando la caché TTL y actualizándose al cambiar de ruta o recibir eventos de sincronización) para calcular dos contadores reales en vivo con clase `tabular-nums`:
    1. **Ingesta de mensajes (`/messages`):** Total de mensajes reales en ingesta (`real_messages_count ?? messages.length`).
    2. **Redacción de contenidos (`/content`):** Total de mensajes listos para redactar/publicar (misma regla de negocio que la Bandeja de Redacción: analizados con IA, no descartados, relevancia $\ge 70\%$ y aún no publicados).
  - Pie del Sidebar con indicador `● En vivo · Sincronizado` (`c-live`).

### 2.5 Dashboard Ejecutivo, Score Rings y Participación por Canal (`RF-06`)
**Archivos:** `frontend/src/pages/Dashboard.tsx`, `frontend/src/components/dashboard/FeaturedStories.tsx`, `frontend/src/components/dashboard/ChannelParticipation.tsx`
- `Dashboard.tsx`:
  - Incorporación de la insignia pulsante `● En vivo` (`c-live`) en la cabecera del Dashboard junto al título o controles superiores.
  - Aplicación de `tabular-nums` y sombras estratificadas en las 6 tarjetas de KPIs.
- `FeaturedStories.tsx`:
  - Integración del componente visual **Score Ring (`score-ring`)** con `--p: ${relevanceScore}` en la cabecera de cada historia destacada para mostrar el porcentaje de relevancia real de manera gráfica y tabular.
- `ChannelParticipation.tsx`:
  - Aplicación de `tabular-nums` en conteos y porcentajes de los 5 canales oficiales y barra de progreso con el gradiente de marca (`c-meter`).

### 2.6 Medidor de Lote IA y Score Rings en Ingesta de Mensajes (`RF-07`)
**Archivo:** `frontend/src/pages/Messages.tsx`
- En el panel de **Evaluación por Lote con IA**:
  - Incorporación de la barra de progreso visual `.c-meter` que muestra el porcentaje de mensajes ya analizados con IA respecto al total de mensajes reales en ingesta, con conteos en `tabular-nums`.
- En las tarjetas de mensajes de la lista:
  - Cuando el mensaje está analizado (`isAnalyzed`), exhibir el anillo circular `.score-ring` con su porcentaje de relevancia real junto a las insignias de estado.

### 2.7 Tarjeta de Marca para Insight Principal y Scorecards de Emojis en Análisis (`RF-08`)
**Archivo:** `frontend/src/pages/Analytics.tsx`
- **Insight Principal de la Comunidad:**
  - Aplicación del estilo `.c-card--brand` (fondo oscuro `slate-900` con resplandor radial `#FF7400`, icono en contenedor translúcido naranja y textos blancos/slate claros de alto contraste) alimentado 100% por los datos reales de `insights` y manteniendo intacto el botón "Gestionar quejas y reclamos".
- **Scorecards de Emojis Destacados:**
  - Estilizado de cada tarjeta de emoji con glifo a `2rem`, porcentaje en `tabular-nums`, conteo de menciones reales y barra de proporción `.c-meter`.

### 2.8 Vista Previa en Vivo Discord Embed y Acento de Selección en Redacción (`RF-09`)
**Archivo:** `frontend/src/pages/ContentStudio.tsx`
- **Cabecera de Redacción de Contenidos:**
  - Insignia de estado en vivo `● Webhook Discord conectado` (`c-live`) en la cabecera de la vista.
- **Bandeja de Mensajes en Redacción:**
  - Aplicación de la clase `.c-tray-card--active` (`box-shadow: inset 3px 0 0 #ff7400`) en la tarjeta activa de la bandeja y `tabular-nums` en el score de relevancia e ID.
- **Panel de Anuncios Oficiales para Discord:**
  - Incorporación de una columna/bloque de **Vista Previa en vivo (Discord Embed)** (`.discord-embed`) que refleja en tiempo real:
    - Avatar `CE`, nombre `CloudEdTech_Oficial`, insignia `BOT` (`#6366f1`) y canal de destino seleccionado (ej. `#notificaciones`).
    - El texto que el operador está escribiendo o que ha generado con IA en `announcementText` (con texto guía si aún está vacío).

### 2.9 Tarjeta de Marca y Lista Monoespaciada en Informes y Almacenamiento OCI (`RF-10`)
**Archivo:** `frontend/src/pages/OCIStorage.tsx`
- Estilizado del panel superior de estado de **OCI Object Storage** con el patrón `.c-card--brand` de Cristian:
  - Cabecera con título, subtítulo e insignia semántica `.c-live` (`● Conectado` en esmeralda cuando `ociStatus.status === 'connected' || ociStatus.status === 'ready'`, o `● Modo Local` en ámbar cuando opera offline).
  - Lista de definición `<dl>` con tipografía monoespaciada (`font-mono tabular-nums`) mostrando `Bucket`, `Región`, `Modo` y los 4 contadores reales provenientes de `/api/v1/oci-storage/status`.

---

## 3. Estrategia de Pruebas (TDD) y Verificación (`RF-11`)

- **Archivo de pruebas:** `tests/test_unificacion_motor_ia.py`
  - Se agregarán pruebas unitarias/integración que verifiquen:
    1. La presencia e integridad de los activos del Design System en `cloudedtech-design-system/cloudedtech-ds/css/tokens.css` y `frontend/src/index.css` (clases `.c-card--brand`, `.score-ring`, `.discord-embed`, `.tabular-nums`).
    2. La sincronización dinámica por ID e inyección temporal (`pinnedSearchMessage`, `displayedTrayMessages`, insignia `📌 Cargado por ID #` y limpieza inmediata en el `onChange` de `manualIdInput`) en `frontend/src/pages/ContentStudio.tsx`, así como la vista previa `.discord-embed`.
    3. La integración de `.c-card--brand` en `Analytics.tsx` y `OCIStorage.tsx`, `.score-ring` en `FeaturedStories.tsx` y `Messages.tsx`, y el isotipo SVG con contadores reales en `Sidebar.tsx` y `Login.tsx`, verificando que ningún archivo de `frontend/src/` importe datos mock de `cloudedtech-design-system`.
- **Verificación de Compilación e Inmutabilidad:**
  - `pytest tests/test_unificacion_motor_ia.py` al 100% en verde.
  - `npm run build` en `frontend/` con 0 errores de TypeScript o empaquetado.
  - `git status` confirmando 0 modificaciones en los 17 archivos protegidos de la raíz, `backend/`, `motor-ia/` y `src/`.
