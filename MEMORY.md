# MEMORY.md - Análisis de Comunidad con IA (Código Unificado)
Memoria del proyecto entre sesiones. Máximo ~50 líneas: resume o elimina lo que ya no aporte.

## Estado actual
- **Sincronización Discord y Evaluación IA:** Ingesta bajo demanda (`POST /api/v1/discord/sync`), evaluación individual y por lotes (`POST /api/v1/ai/evaluate-batch`) con 3 cerebros (Groq, Gemma, Gemini). Sincronización directa en SQLite local y Supabase (`lotes_ia_kpis`).
- **Dashboard Homologado 1:1 con Cristian (Spec 020):** 6 tarjetas KPI con iconos exactos (`Smile` en verde, `Hash` con sparkline negro, `PenLine` con sparkline morado, `Clock` en rojo), sin sección de participación por canal, título `Dashboard` en negrita, filtros interactivos de sentimiento y botón funcional `Actualizar datos`.
- **Ingesta de Mensajes Homologada (Spec 020 - En progreso):**
  - **4 Tarjetas KPI Superiores (`#msg-summary`):** Homologadas 1:1 con el Design System de Cristian (`l-grid l-grid--4` y `KpiCard`): `Analizados` (`Inbox`), `Positivos` (`Smile` en `.c-iconbox--success` con `% del total`), `Preguntas` (`MessageSquare` en `.c-iconbox--info` con `Candidatas a FAQ`) y `Destacados` (`Star` con `Relevancia ≥ 85`), con datos reales y sin sparkline.
  - **Cabecera Compacta y Reorganización:** Eliminado el icono naranja junto al título `Ingesta de mensajes`. Trasladada la sección de `Mensajes totales recibidos` a la cabecera en tarjeta compacta (totales recibidos, estado de conexión a Discord, datos en Motor IA, bots omitidos, reales detectados y botón `Sincronizar Discord` `.c-btn--primary`), eliminando la sección grande redundante inferior. Indicador `Motor de ingesta conectado` reubicado junto a `3 cerebros IA disponibles` en Evaluación por Lote.
  - **Panel Evaluación por Lote compacto:** `.c-card` con píldoras `.c-pill` (primero `cerebros IA`, luego `Motor de ingesta`), robot morado conservado, controles en una sola fila (`.c-select`/`.c-input` compactos + `Evaluar mensajes con IA` `.c-btn--primary`) y franja única de cobertura `.c-meter` + conteos del rango. Cabecera dice `Mensajes totales recibidos`.
- **Redacción de Contenidos y Mesa de Trabajo (ContentStudio.tsx - Enoc):** Integración multicanal Mototradis (Discord, LinkedIn, X), persistencia SQLite, panel de quejas con resolución de canales, anuncios oficiales con vista previa Discord Embed y buscador dinámico de mensajes por ID.
- **Informes y Almacenamiento OCI (OCIStorage.tsx - Tania):** Conectado con `reporte_semanal.py` y `oci_uploader.py`, panel de estado de bucket y generación de paquetes.
- **Infraestructura y Despliegue:** Frontend desplegado en Netlify (`https://cloudedtech-communitylab2.netlify.app`), backend en Render con Cloudflare Worker reverse proxy (`https://discord-proxy-edtech.fraustojeovany.workers.dev`) para evitar rate limit de Discord. CI/CD activo sin `[skip netlify]`.
- **Tests y Calidad:** 100% de la suite pasando en verde (`pytest tests/test_unificacion_motor_ia.py`), build frontend limpio con código 0 (`npm run build`). Inmutabilidad absoluta de los 17 archivos protegidos de la raíz, `backend/`, `motor-ia/` y `src/`.

## Decisiones (y por qué)
- **Design System con Datos Reales:** Se adoptan 1:1 los componentes y estilos de Cristian (`cloudedtech-design-system`), alimentados exclusivamente por los datos reales de la comunidad y del backend (0 mocks de `CE_DATA`).
- **Eliminación de Tecnicismos:** Se reemplazó la terminología de "curaduría" y "pendientes de copy" por términos intuitivos ("Pendientes de publicar", "Listo / Aprobado").
- **Aislamiento Constitucional:** Cero modificaciones a los 17 archivos protegidos de la raíz ni `backend/`; la lógica de compatibilidad reside en `puente_motor_ia.py` y `frontend/src/`.
- **Soberanía Humana (HITL):** Los estados y textos editados por humanos prevalecen sobre el motor de IA.

## Errores a evitar
- Nunca modificar los archivos preexistentes de la raíz, `backend/` ni `motor-ia/`.
- Nunca saltarse el flujo ni asumir que un cambio es "demasiado pequeño".
- Nunca hacer push directo a `main` (Regla 1). Todo el trabajo se mantiene en ramas `feature/` o `beta-pruebas`.
- Nunca escribir credenciales en código duro (Regla 4).
