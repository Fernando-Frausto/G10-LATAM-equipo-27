# Tareas de Implementación — Spec 019: Sincronización Dinámica de Bandeja por ID e Integración del Design System CloudEdTech

## [x] T1: Fase Red TDD y Extracción de Activos del Design System de Cristian (~15 min)
- **Estado:** `[x] Completada`
- **Archivos involucrados:**
  - `tests/test_unificacion_motor_ia.py`
  - `cloudedtech-design-system/` (extraído desde `origin/feature/design-system-cloudedtech`)
- **Requerimientos Funcionales:** `RF-01`, `RF-02`, `RF-03`, `RF-04`, `RF-05`, `RF-06`, `RF-07`, `RF-08`, `RF-09`, `RF-10`, `RF-11`
- **Descripción:**
  1. Incorporar el directorio completo `cloudedtech-design-system/` desde `origin/feature/design-system-cloudedtech` (`commit c606071`) al árbol de trabajo para preservar el entregable de Cristian.
  2. Escribir en `tests/test_unificacion_motor_ia.py` las pruebas automatizadas para la Spec 019 (verificando `pinnedSearchMessage`, limpieza inmediata al cambiar el input de ID, tokens y clases en `index.css`, isotipo SVG y contadores en `Sidebar.tsx`, `score-ring`, `c-card--brand`, `discord-embed` y ausencia de mocks en `frontend/src/`) y confirmar que fallan inicialmente en los componentes de React aún no actualizados (Fase Red TDD).
- **Hecho cuando:** El directorio `cloudedtech-design-system/` existe íntegro en el repositorio y los nuevos tests de la Spec 019 en `tests/test_unificacion_motor_ia.py` se ejecutan evidenciando el estado Red previo a la implementación en React.

---

## [x] T2: Tokens Semánticos, Tipografía Tabular y Clases del Design System en `index.css` (~20 min)
- **Estado:** `[x] Completada`
- **Archivos involucrados:**
  - `frontend/src/index.css`
- **Requerimientos Funcionales:** `RF-04`
- **Descripción:**
  1. Integrar en `:root` de `frontend/src/index.css` la paleta de tokens de Cristian (`--orange-50` a `--orange-700`, `--navy-800` a `--navy-950`, superficies `--surface-app`, `--surface-card`, `--surface-muted`, bordes `--border-subtle`, `--border-strong`, sombras estratificadas `--shadow-xs` a `--shadow-focus` y radios).
  2. Definir las clases utilitarias reutilizables del Design System: `.tabular-nums`, `.c-card--brand`, `.score-ring`, `.c-live`, `.c-live__dot`, `.c-meter`, `.discord-embed` y `.c-tray-card--active`.
  3. Configurar `:focus-visible` con contorno `#FF7400` y soporte a `@media (prefers-reduced-motion: reduce)`.
- **Hecho cuando:** `frontend/src/index.css` contiene todos los tokens y clases del Design System CloudEdTech sin errores de sintaxis CSS y las aserciones de estilos del test pasan en verde.

---

## [x] T3: Identidad Vectorial SVG y Contadores Reales en Vivo en `Sidebar.tsx` y `Login.tsx` (~20 min)
- **Estado:** `[x] Completada`
- **Archivos involucrados:**
  - `frontend/src/components/Sidebar.tsx`
  - `frontend/src/pages/Login.tsx`
- **Requerimientos Funcionales:** `RF-05`, `RF-11`
- **Descripción:**
  1. Integrar el isotipo vectorial oficial SVG de Cristian (nodos conectados y flecha ascendente en `#FF7400` y blanco sobre `#080A27`) y el wordmark `CloudEdTech` (`Ed` en `#FF7400`) con subtítulo `EDUCATION & TECHNOLOGY` tanto en `Sidebar.tsx` (vista desktop y barra superior móvil) como en `Login.tsx`.
  2. En `Sidebar.tsx`, consultar `/api/community/messages?limit=500` de forma resiliente para mostrar badges numéricos en vivo con `tabular-nums` en `Ingesta de mensajes` (total de mensajes reales en ingesta) y `Redacción de contenidos` (total de mensajes listos para publicar), e incluir el indicador `● En vivo` (`c-live`) en la navegación.
- **Hecho cuando:** `Sidebar.tsx` y `Login.tsx` exhiben el isotipo vectorial oficial SVG de Cristian y `Sidebar.tsx` muestra los contadores reales en vivo sin utilizar ningún dato mock.

---

## [x] T4: Dashboard Ejecutivo, Score Rings e Ingesta de Mensajes (`Dashboard.tsx`, `FeaturedStories.tsx`, `ChannelParticipation.tsx`, `Messages.tsx`) (~20 min)
- **Estado:** `[x] Completada`
- **Archivos involucrados:**
  - `frontend/src/pages/Dashboard.tsx`
  - `frontend/src/components/FeaturedStories.tsx`
  - `frontend/src/components/ChannelParticipation.tsx`
  - `frontend/src/pages/Messages.tsx`
- **Requerimientos Funcionales:** `RF-06`, `RF-07`, `RF-11`
- **Descripción:**
  1. En `Dashboard.tsx`, incorporar el indicador pulsante `● En vivo` (`c-live`) en la cabecera y aplicar `tabular-nums` en las tarjetas de KPIs.
  2. En `FeaturedStories.tsx`, integrar el componente visual `.score-ring` cónico (`--p: ${relevanceScore}`) en cada tarjeta de historia destacada para mostrar el porcentaje de relevancia real.
  3. En `ChannelParticipation.tsx`, aplicar `tabular-nums` en conteos y porcentajes reales de los 5 canales y barra `.c-meter`.
  4. En `Messages.tsx`, añadir la barra de progreso `.c-meter` en el panel de Evaluación por Lote con IA (proporción de analizados vs. total en ingesta) y el `.score-ring` de relevancia en las tarjetas de mensajes analizados.
- **Hecho cuando:** El Dashboard y la vista de Ingesta renderizan el indicador `● En vivo`, los anillos `.score-ring` cónicos y los medidores `.c-meter` alimentados al 100% por datos reales.

---

## T5: Patrón `c-card--brand` y Scorecards en `Analytics.tsx` y `OCIStorage.tsx` (~20 min) — [x] Completada
- **Archivos involucrados:**
  - `frontend/src/pages/Analytics.tsx`
  - `frontend/src/pages/OCIStorage.tsx`
- **Requerimientos Funcionales:** `RF-08`, `RF-10`, `RF-11`
- **Descripción:**
  1. En `Analytics.tsx`, estilizar la tarjeta de **Insight Principal de la Comunidad** con la clase `.c-card--brand` (fondo oscuro `slate-900` con resplandor radial `#FF7400` y alto contraste) manteniendo los insights reales y el botón de navegación a quejas, y aplicar en las **Scorecards de Emojis Destacados** el formato `emoji-card` con glifo a `2rem`, porcentaje `tabular-nums` y barra `.c-meter`.
  2. En `OCIStorage.tsx`, estilizar el panel de estado de **OCI Object Storage** con `.c-card--brand`, indicador semántico `.c-live` (`● Conectado` / `● Modo Local`) y lista `<dl>` con tipografía monoespaciada (`font-mono tabular-nums`) conectada a `/api/v1/oci-storage/status`.
- **Hecho cuando:** `Analytics.tsx` y `OCIStorage.tsx` aplican el diseño `.c-card--brand` y tipografía tabular/monoespaciada alimentados exclusivamente por los endpoints reales de la plataforma.

---

## T6: Sincronización Dinámica de Bandeja por ID y Vista Previa Discord Embed en `ContentStudio.tsx` (~20 min) — [x] Completada
- **Archivos involucrados:**
  - `frontend/src/pages/ContentStudio.tsx`
- **Requerimientos Funcionales:** `RF-01`, `RF-02`, `RF-09`, `RF-11`
- **Descripción:**
  1. Implementar `pinnedSearchMessage: WorkflowMessage | null` y `displayedTrayMessages` en `ContentStudio.tsx`:
     - Al buscar un ID en `handleLoadById`: si está en `workflowMessages`, seleccionarlo y hacer `scrollIntoView` en la bandeja; si existe en la plataforma pero no está en `workflowMessages`, inyectarlo al inicio mediante `pinnedSearchMessage` como seleccionado con insignia `📌 Cargado por ID #${msg.id}` y hacer `scrollIntoView`.
     - Al modificar o borrar el input `manualIdInput` (`onChange`), limpiar inmediatamente `pinnedSearchMessage` (`setPinnedSearchMessage(null)`) para que el mensaje temporal desaparezca al instante de la `Bandeja de mensajes en Redacción`, conservando intactos los mensajes de `workflowMessages` y restableciendo la Mesa de Trabajo al primer elemento de `workflowMessages` si el temporal era el activo.
  2. Aplicar `.c-tray-card--active` en la tarjeta seleccionada de la bandeja, mostrar la píldora `● Webhook Discord conectado` (`c-live`) en la cabecera e incorporar la **Vista Previa en vivo estilo Discord Embed (`.discord-embed`)** en el panel de Anuncios Oficiales con avatar `CE`, `CloudEdTech_Oficial`, insignia `BOT` (`#6366f1`) y renderizado instantáneo del texto del anuncio.
- **Hecho cuando:** Al buscar un ID existente se muestra seleccionado en la `Bandeja de mensajes en Redacción`, al cambiar el número en el buscador cualquier mensaje temporal desaparece inmediatamente de la bandeja, y el panel de Anuncios Oficiales muestra la vista previa Discord Embed en tiempo real.

---

## T7: Verificación Integral, Pruebas en Verde, Build de Producción y Memoria (~15 min) — [x] Completada
- **Archivos involucrados:**
  - `tests/test_unificacion_motor_ia.py`
  - `MEMORY.md`
- **Requerimientos Funcionales:** `RF-01` a `RF-11`
- **Descripción:**
  1. Ejecutar la suite completa `pytest tests/test_unificacion_motor_ia.py` verificando que el 100% de las pruebas (incluyendo las nuevas de la Spec 019) pasen en verde (Fase Green TDD).
  2. Ejecutar `npm run build` en `frontend/` verificando 0 errores de TypeScript y compilación limpia de producción.
  3. Comprobar con `git status` la inmutabilidad estricta de los 17 archivos protegidos de la raíz, `backend/`, `motor-ia/` y `src/`.
  4. Actualizar `MEMORY.md` documentando el cierre de la Spec 019.
- **Hecho cuando:** `pytest` pasa al 100% en verde, `npm run build` finaliza con éxito (exit code 0), `git status` confirma 0 cambios en archivos protegidos y `MEMORY.md` está actualizado.
