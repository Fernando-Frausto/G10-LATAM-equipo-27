# MEMORY.md - Análisis de Comunidad con IA (Código Unificado)
Memoria del proyecto entre sesiones. Máximo ~50 líneas: resume o elimina lo que ya no aporte.

## Estado actual
- **Sincronización Discord y Evaluación IA:** Ingesta bajo demanda (`POST /api/v1/discord/sync`), evaluación individual y por lotes (`POST /api/v1/ai/evaluate-batch`) con 3 cerebros (Groq, Gemma, Gemini). Sincronización directa en SQLite local y Supabase (`lotes_ia_kpis`).
- **Dashboard Homologado 1:1 con Cristian (Spec 020):** 6 tarjetas KPI con iconos exactos (`Smile` en verde, `Hash` con sparkline negro, `PenLine` con sparkline morado, `Clock` en rojo), sin sección de participación por canal, título `Dashboard` en negrita, filtros interactivos de sentimiento y botón funcional `Actualizar datos`.
- **Ingesta de Mensajes Homologada (Spec 020):** 4 tarjetas KPI (`Analizados`, `Positivos`, `Preguntas`, `Destacados`), cabecera compacta con telemetría de bots/reales, panel de evaluación IA en una sola fila con `.c-meter`, contenedor unificado `.c-card--flush` de filtro y mensajes con scroll interno, pod derecho compacto de relevancia y botones de ancho natural.
- **Pestaña de Análisis Homologada 1:1 con Cristian (Spec 020):**
  - **Cabecera (`.l-page-head`):** Título `Análisis` en negrita, subtítulo y selector segmentado de período (`7d`, `30d`, `90d`) conectado al filtrado.
  - **Métricas Globales de Curaduría (`.c-card.c-card--lg`):** Grid de 4 columnas con contenedor vertical inmune a colapsos, `.t-kpi` tabular y barras `.c-progress` (`Tasa de sentimiento positivo`, `Índice de interacción`, `Relevancia promedio`, `Alertas activas`), con datos reales.
  - **Evolución y Señales Clave (`.l-grid.l-grid--main-side`):**
    - Izquierda: Gráfico de área `Evolución del sentimiento` con series Positivo, Neutral y Negativo, leyenda interactiva para aislar series y filtrado por días.
    - Derecha: **Tarjeta Unificada de Insights (`.c-card--brand`)** con el diseño oscuro de marca original (`Insight principal`, `Preguntas frecuentes` y `Atención requerida` agrupadas en un solo bloque con botón interactivo hacia `/content#panel-quejas`).
  - **Scorecards de Emojis Destacados (`.c-card.c-card--lg`):** Grid de 6 columnas con `.emoji-card`, emoji a 2rem, conteo `.t-kpi`, etiqueta y badge de tendencia `.c-trend`.
  - **Hashtags y Temas (`.l-grid.l-grid--halves`):**
    - Mitad 1: Gráfico de barras horizontal con selector segmentado de métrica (`Volumen` / `Crecimiento`).
    - Mitad 2: Gráfico de radar semántico (`Relevancia` vs. `Participación`) con botones interactivos para aislar u ocultar series en vivo.
- **Redacción de Contenidos Homologada y Limpia:** Fusión de Mesa de Trabajo Multicanal con Mensaje original de Discord, 3 tarjetas lanzadoras (LinkedIn, X, Discord), Procesamiento Masivo (< 35) compacto integrado al pie de la columna derecha, banner inferior 'Flujo editorial directo', modal emergente (`.c-modal`) para redacción paralela/individual, y Panel de Anuncios Oficiales con editores superiores y Live Discord Embed (`.discord-embed`) inferior, sin badges redundantes ('Manual de marca', badge de modelo en selector) ni contadores numéricos en navegación. Cero vacío blanco y perfecta sincronización visual.
- **Informes y Almacenamiento OCI (OCIStorage.tsx - Tania):** Conectado con `reporte_semanal.py` y `oci_uploader.py`, panel de estado de bucket y generación de paquetes.
- **Infraestructura y Tests:** Netlify + Render con Cloudflare Worker proxy. 100% tests pasando (100/100 en verde), build frontend exitoso con código 0 (`npm run build`). Inmutabilidad absoluta de los 17 archivos protegidos de la raíz, `backend/`, `motor-ia/` y `src/`.

## Decisiones (y por qué)
- **Restauración desde Descartados a Bandeja:** Al pulsar 'Restaurar a pendientes' en un mensaje analizado desde 'Descartados', se guarda `estado_curaduria = 'curated'`, permitiendo que mensajes rescatados por el operador salgan de descartados, pasen a 'Pendientes de publicar' y se listen en la Bandeja de Redacción independientemente de su score de IA.
- **Alineación al Ras y Flujo Editorial en Redacción:** Se integró 'Procesamiento Masivo de Baja Relevancia (< 35)' de forma compacta en la columna derecha debajo de los 3 lanzadores, igualando con precisión la altura de la Bandeja izquierda. El aviso 'Flujo editorial directo' se reubicó al pie de ambas columnas, logrando simetría visual absoluta y eliminando cualquier espacio en blanco.
- **Criterio Estricto de 'Proceso Completo':** Un mensaje solo se clasifica y contabiliza como 'Proceso completo' cuando ha sido efectivamente publicado en al menos 1 de las 3 redes sociales (Discord, LinkedIn, X) o en las 3 (`isMsgPublished`).
- **Aislamiento Total de Pruebas de Discord:** Mocks rigurosos para evitar llamadas reales a la API de Discord o interacción del CommunityLab Bot durante tests.
- **Design System con Datos Reales:** Se adoptan 1:1 los componentes y layouts de Cristian (`cloudedtech-design-system`), alimentados exclusivamente por los datos reales de la comunidad y del backend (0 mocks).
- **Tarjeta Unificada de Insights en Análisis:** Se agruparon las 3 secciones inferiores (`Insight principal`, `Preguntas frecuentes` y `Atención requerida`) en una sola tarjeta lateral con la estética de marca oscura (`c-card--brand`), conservando el botón funcional a `/content#panel-quejas`.
- **Aislamiento Constitucional:** Cero modificaciones a los 17 archivos protegidos de la raíz ni `backend/`; la lógica de compatibilidad reside en `puente_motor_ia.py` y `frontend/src/`.

## Errores a evitar
- Nunca modificar los archivos preexistentes de la raíz, `backend/` ni `motor-ia/`.
- Nunca saltarse el flujo ni asumir que un cambio es "demasiado pequeño".
- Nunca hacer push directo a `main` (Regla 1). Todo el trabajo se mantiene en ramas `feature/` o `beta-pruebas`.
- Nunca escribir credenciales en código duro (Regla 4).
