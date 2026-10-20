# Especificación 019: Sincronización Dinámica de Bandeja por ID e Integración del Design System CloudEdTech con Datos Reales

## 1. Contexto y Propósito (El POR QUÉ)

### 1.1 Sincronización Dinámica de la Bandeja de Redacción con el Buscador por ID
Actualmente, cuando el operador utiliza el buscador por ID (`Cargar ID`) en la vista de **Redacción de Contenidos** (`/content`), la tarjeta del mensaje original se carga en la Mesa de Trabajo inferior, pero si el mensaje no formaba parte de la cola activa de la **Bandeja de mensajes en Redacción** (por ejemplo, porque ya había sido publicado previamente o tenía otra etapa en el flujo), la bandeja horizontal superior no refleja visualmente ese mensaje como el elemento activo, o bien no limpia el elemento temporal cuando el operador modifica el número en el buscador.

**Por qué es necesario:**
- **Coherencia visual y orientación espacial:** El operador necesita ver reflejado en la `Bandeja de mensajes en Redacción` el mensaje que ha buscado por ID como elemento seleccionado (`isActive`), independientemente de si pertenecía originalmente a la cola pendiente o si fue recuperado bajo demanda.
- **Limpieza inmediata y predecibilidad:** Si el operador cambia o borra el número en el campo del buscador de ID, cualquier tarjeta inyectada temporalmente en la bandeja debe desaparecer de forma inmediata para no contaminar la cola natural de trabajo pendiente con elementos históricos o de consulta puntual.

### 1.2 Integración del Design System CloudEdTech (`origin/feature/design-system-cloudedtech`) bajo `/frontend-design` y 100% Datos Reales
El compañero Cristian desarrolló en la rama `origin/feature/design-system-cloudedtech` (commit `c606071`) el sistema de diseño oficial de **CloudEdTech (`cloudedtech-design-system/cloudedtech-ds/`)**, definiendo principios de diseño ejecutivos ("Datos primero", "Superficies con jerarquía, no decoración", "Un acento de marca con disciplina", "Estados semánticos inequívocos"), tokens CSS estructurados, isotipos vectoriales oficiales, anillos de relevancia (`score-ring`), tarjetas de marca oscuras (`c-card--brand`), vista previa en tiempo real de anuncios en formato Discord Embed (`discord-embed`) y tipografía numérica tabular (`tabular-nums`).

**Por qué es necesario:**
- **Reconocimiento del aporte del equipo y preservación documental:** Incorporar el directorio `cloudedtech-design-system/` al repositorio garantiza que el entregable de diseño de Cristian se preserve íntegro en el proyecto.
- **Elevación de la calidad visual y ergonómica (`/frontend-design`):** Integrar los patrones visuales, tokens semánticos, isotipos SVG e indicadores de alta precisión de Cristian en la aplicación React productiva (`frontend/src/`) unifica la identidad corporativa de CloudEdTech (`#FF7400` y `#080A27`) y mejora la escaneabilidad de KPIs y estados operativos.
- **Veracidad absoluta de datos (Cero Mocks):** Mientras que el entregable de referencia en HTML/JS estático utilizaba datos demostrativos locales (`js/data.js`), la aplicación productiva debe alimentar cada componente visual del Design System exclusivamente con datos reales provenientes de los endpoints en vivo de la plataforma (Supabase, SQLite, Discord y OCI Object Storage).

---

## 2. Requerimientos Funcionales (El QUÉ — Formato EARS)

### RF-01: Selección e Inyección Temporal en la Bandeja de Redacción al Buscar por ID
- **CUANDO** el operador ingrese un identificador numérico en el buscador por ID (`Cargar ID`) dentro de **Redacción de Contenidos** (`/content`) y el mensaje correspondiente exista y esté disponible en la plataforma, **SI** dicho mensaje ya forma parte de la cola natural de la `Bandeja de mensajes en Redacción`, **EL SISTEMA DEBERÁ** marcarlo visualmente como seleccionado y desplazar suavemente la bandeja horizontal hasta posicionar su tarjeta en el área visible.
- **CUANDO** el operador cargue mediante el buscador por ID un mensaje válido y disponible en la plataforma que no forme parte de la cola natural de la `Bandeja de mensajes en Redacción` (por ejemplo, un mensaje ya publicado o en otra etapa), **EL SISTEMA DEBERÁ** inyectar temporalmente dicho mensaje al inicio de la `Bandeja de mensajes en Redacción` con estado visualmente seleccionado y una insignia distintiva (`📌 Cargado por ID #N`), sincronizado con la Mesa de Trabajo inferior, manteniendo el contador de cabecera (`N listos para copy`) circunscrito exclusivamente al tamaño de la cola natural de pendientes.

### RF-02: Desaparición Inmediata del Mensaje Temporal al Modificar el Buscador de ID
- **CUANDO** el operador modifique, edite o borre el valor numérico en el campo de entrada del buscador de ID, **SI** existía un mensaje inyectado temporalmente en la `Bandeja de mensajes en Redacción` producto de una búsqueda por ID anterior que no pertenece a la cola natural de pendientes, **EL SISTEMA DEBERÁ** retirar inmediatamente dicho mensaje temporal de la `Bandeja de mensajes en Redacción` (conservando intactos todos los mensajes que sí pertenecen a la cola natural de pendientes) y, si dicho mensaje temporal era el que estaba abierto en la Mesa de Trabajo, **EL SISTEMA DEBERÁ** restablecer la selección activa al primer mensaje disponible de la cola natural.

### RF-03: Incorporación Íntegra de los Activos del Design System de Cristian
- **CUANDO** se integre el sistema de diseño en la rama de trabajo, **EL SISTEMA DEBERÁ** conservar el directorio completo `cloudedtech-design-system/` proveniente de `origin/feature/design-system-cloudedtech` (incluyendo hojas de tokens, componentes, layouts, isotipos vectoriales SVG y vistas de referencia), preservando la autoría y documentación técnica de Cristian dentro del repositorio.

### RF-04: Tokens Semánticos, Tipografía Numérica Tabular y Accesibilidad Global
- **MIENTRAS** la aplicación frontend esté en ejecución, **EL SISTEMA DEBERÁ** exponer en su hoja de estilos global las variables semánticas del Design System CloudEdTech (escala cromática `--orange-500: #ff7400`, `--navy-950: #080a27`, superficies jerárquicas `--surface-app` y `--surface-card`, sombras estratificadas `--shadow-sm`, `--shadow-md`, `--shadow-lg`, `--shadow-focus` y radios de borde consistentes).
- **MIENTRAS** se rendericen métricas numéricas, porcentajes, conteos de mensajes, puntuaciones de relevancia e indicadores KPI en cualquier vista de la plataforma, **EL SISTEMA DEBERÁ** aplicar alineación numérica tabular (`tabular-nums`) para garantizar lectura vertical y comparativa de alta precisión.
- **CUANDO** el usuario navegue mediante teclado o tenga activada la preferencia de reducción de movimiento del sistema operativo, **EL SISTEMA DEBERÁ** presentar anillos de foco visibles de alto contraste en naranja de marca (`#FF7400`) y respetar la supresión de animaciones no esenciales (`prefers-reduced-motion: reduce`).

### RF-05: Identidad de Marca Vectorial y Contadores en Vivo en Navegación y Acceso
- **MIENTRAS** el usuario visualice la barra lateral de navegación (`Sidebar`, tanto en escritorio como en cabecera móvil) o la pantalla de inicio de sesión (`Login`), **EL SISTEMA DEBERÁ** mostrar el isotipo vectorial oficial de CloudEdTech (red de nodos conectados con flecha de crecimiento ascendente en `#FF7400` y blanco sobre fondo `#080A27`) acompañado de la marca tipográfica `CloudEdTech` (`Ed` destacado en `#FF7400`) y el subtítulo `EDUCATION & TECHNOLOGY`.
- **MIENTRAS** la barra lateral de navegación esté activa y existan datos cargados de la comunidad, **EL SISTEMA DEBERÁ** exhibir insignias numéricas tabulares en tiempo real junto a los enlaces de `Ingesta de mensajes` (total de mensajes reales en ingesta) y `Redacción de contenidos` (total de mensajes en cola listos para redactar/publicar), así como un indicador de estado operativo `● En vivo` en el pie de la barra lateral.

### RF-06: Dashboard Ejecutivo con Indicador En Vivo, Score Rings y Participación Refinada
- **MIENTRAS** el usuario consulte la vista principal de **Dashboard** (`/dashboard`), **EL SISTEMA DEBERÁ** mostrar en la cabecera un indicador semántico pulsante `● En vivo` con halo esmeralda suave que refleje la conexión activa con las fuentes de datos reales.
- **MIENTRAS** se visualicen las tarjetas de **Historias Destacadas** (`FeaturedStories`) en el Dashboard, **EL SISTEMA DEBERÁ** representar el porcentaje de relevancia real de cada historia mediante el componente visual de anillo circular cónico (`score-ring`) del Design System en color `#FF7400`, manteniendo intacta la trazabilidad multicanal y acciones de publicación.
- **MIENTRAS** se visualice la sección de **Participación por Canal** (`ChannelParticipation`), **EL SISTEMA DEBERÁ** presentar los conteos y porcentajes reales de los cinco canales oficiales con tipografía numérica tabular y barras de progreso estilizadas según los tokens del Design System.

### RF-07: Medidor de Lote IA y Anillos de Relevancia en Ingesta de Mensajes
- **MIENTRAS** el usuario opere la vista de **Ingesta de Mensajes** (`/messages`), **EL SISTEMA DEBERÁ** presentar en el panel de Evaluación por Lote con IA un medidor visual de progreso con gradiente de marca (`c-meter`) que ilustre la proporción de mensajes analizados frente al total real en ingesta.
- **MIENTRAS** se listen las tarjetas de mensajes reales en **Ingesta de Mensajes**, **SI** un mensaje ya cuenta con evaluación de IA, **EL SISTEMA DEBERÁ** mostrar su puntuación de relevancia real acompañada del indicador visual circular (`score-ring`) y tipografía tabular.

### RF-08: Tarjeta de Marca para Insight Principal y Scorecards de Emojis en Análisis
- **MIENTRAS** el usuario consulte la vista de **Análisis** (`/analytics`), **EL SISTEMA DEBERÁ** presentar el bloque de **Insight Principal de la Comunidad** utilizando el patrón visual de tarjeta oscura de marca (`c-card--brand`, con fondo `#0f172a`, resplandor radial naranja `#FF7400` sutil y tipografía blanca de alto contraste), alimentado exclusivamente por los hallazgos y métricas reales de la comunidad y manteniendo la acción directa hacia la gestión de quejas.
- **MIENTRAS** se visualice la sección de **Scorecards de Emojis Destacados** en **Análisis**, **EL SISTEMA DEBERÁ** estructurar cada tarjeta siguiendo el patrón `emoji-card` del Design System (glifo a escala destacada, porcentaje en números tabulares, conteo de menciones reales y barra horizontal de proporción en `#FF7400`).

### RF-09: Vista Previa en Vivo Discord Embed y Selección con Acento en Redacción de Contenidos
- **MIENTRAS** el operador redacte o genere con IA un comunicado en el panel de **Anuncios Oficiales para Discord** dentro de **Redacción de Contenidos** (`/content`), **EL SISTEMA DEBERÁ** renderizar en tiempo real una **Vista Previa estilo Discord Embed (`discord-embed`)** con borde izquierdo de 4px en `#FF7400`, avatar `CE`, identificador oficial `CloudEdTech_Oficial`, insignia `BOT` en color índigo (`#6366f1`), canal de destino seleccionado y el contenido textual actualizado al instante.
- **MIENTRAS** el operador se encuentre en **Redacción de Contenidos**, **EL SISTEMA DEBERÁ** mostrar en la cabecera un indicador de estado del canal de salida (`● Webhook Discord conectado` en verde esmeralda cuando la configuración esté activa) y aplicar en las tarjetas de la `Bandeja de mensajes en Redacción` el borde y acento lateral interior de 3px en `#FF7400` cuando se encuentren seleccionadas.

### RF-10: Tarjeta de Marca y Definiciones Monoespaciadas en Informes y Almacenamiento OCI
- **MIENTRAS** el usuario consulte la vista de **Informes y Almacenamiento** (`/oci-storage`), **EL SISTEMA DEBERÁ** presentar el panel de estado de **OCI Object Storage** con el patrón de tarjeta oscura de marca (`c-card--brand`), mostrando el indicador semántico de conexión (`● Conectado` o `● Modo Local`), y una lista estructurada con tipografía monoespaciada para los metadatos reales de `Bucket`, `Región`, `Modo` y contadores provenientes del endpoint `/api/v1/oci-storage/status`.

### RF-11: Inviolabilidad Constitucional y Prohibición Estricta de Datos Mock
- **EN TODO MOMENTO**, **EL SISTEMA DEBERÁ** mantener intactos y sin modificaciones los 17 archivos protegidos de la raíz del proyecto, el directorio `backend/`, el directorio `motor-ia/` y el directorio `src/`.
- **EN TODO MOMENTO**, **EL SISTEMA DEBERÁ** alimentar todos los componentes visuales de la aplicación React exclusivamente con datos reales procedentes de la API y base de datos del proyecto, quedando prohibida la importación o visualización de datos ficticios estáticos en la interfaz de usuario productiva.

---

## 3. Criterios de Aceptación y Verificación

1. **Verificación de Sincronización de Bandeja por ID (`ContentStudio.tsx`):**
   - Buscar un ID existente que esté en la cola pendiente lo selecciona y desplaza a la vista en la Bandeja de Redacción.
   - Buscar un ID existente que no esté en la cola pendiente (ej. ya publicado o con menor relevancia) lo muestra temporalmente al inicio de la Bandeja de Redacción como seleccionado (`📌 Cargado por ID #N`).
   - Modificar o vaciar el número en el campo del buscador de ID elimina inmediatamente de la Bandeja de Redacción el mensaje inyectado temporalmente.
2. **Verificación del Design System CloudEdTech con Datos Reales:**
   - El directorio `cloudedtech-design-system/` existe íntegro en el repositorio.
   - Los tokens CSS, números tabulares (`tabular-nums`), isotipo vectorial SVG, badges numéricos en `Sidebar`, `score-ring` en historias e ingesta, `c-card--brand` en Análisis y OCI Storage, y `discord-embed` en tiempo real en Anuncios Oficiales se renderizan correctamente sin usar datos estáticos falsos.
3. **Verificación de Integridad y Compilación:**
   - `git status` confirma 0 modificaciones en los 17 archivos protegidos de la raíz, `backend/`, `motor-ia/` y `src/`.
   - La suite de pruebas de backend (`pytest`) y la compilación de producción de frontend (`npm run build`) finalizan con 0 errores.
