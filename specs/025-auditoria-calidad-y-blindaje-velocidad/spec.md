# Especificación 025: Auditoría Integral de Calidad, Resiliencia de Interfaz y Blindaje de Alta Velocidad

## 1. Contexto y Propósito (El POR QUÉ)

### 1.1 Contexto y Necesidad del Negocio
La plataforma CloudEdTech / CommunityLab ha alcanzado un hito clave de madurez operativa tras la integración de los flujos de curaduría Human-in-the-Loop (Spec 020), la sincronización ultrarrápida de Discord (Spec 021), la unificación de persistencia con Supabase Enoc (Spec 022), el checkpointer de LangGraph con desacoplamiento asíncrono (Spec 023) y la consolidación de reportes semanales en Oracle Cloud Infrastructure (OCI) Object Storage con inyección de copys reales (Spec 024).

Actualmente, la base de datos de la comunidad alberga más de **1,192 mensajes reales** (1,210 interacciones registradas y sincronizadas), acumulando el histórico completo de canales como `#general`, `#faq`, `#pqrs`, `#notificaciones`, `#chat-egresados` y `#oportunidades-laborales`. Ante este volumen de datos reales y el uso intensivo de la plataforma por parte de los operadores de comunidad y redactores, el usuario solicita una **revisión minuciosa, estricta y exhaustiva de todas las pestañas de la aplicación**, orientada a:
1. Identificar y subsanar cualquier tipo de fallo, anomalía visual, recorte de interfaz o inconsistencia en las 5 pestañas principales: **Dashboard**, **Ingesta de mensajes**, **Análisis**, **Redacción de contenidos (ContentStudio)** e **Informes y almacenamiento (OCI Storage)**.
2. Identificar oportunidades críticas de optimización que multipliquen la velocidad percibida y garanticen que la agilidad actual no se degrade conforme la base comunitaria continúe escalando a miles de interacciones.

### 1.2 Diagnóstico Técnico y Cuellos de Botella Detectados

#### 1. Ingesta de Mensajes (`Messages.tsx`) — Saturación del DOM y Límite Artificial de Mensajes
- **Saturación del DOM (DOM Clutter):**
  Actualmente, `Messages.tsx` solicita los mensajes con `?limite=500` y procesa la colección renderizando la totalidad de las tarjetas filtradas de forma simultánea dentro del contenedor `#msg-list` (`filteredMessages.map(...)`). Con 500 tarjetas (y potencialmente 1,192+), cada una conteniendo aproximadamente 50 nodos DOM (avatares, chips de sentimiento, medidores de relevancia, etiquetas de canal, botones de acción, menús de redacción y popups), el árbol DOM supera los **25,000 nodos activos**. Esto provoca degradación severa de frames por segundo (jank) al hacer scroll, retardos al escribir en el campo de búsqueda rápida (`searchTerm`) y bloqueos momentáneos en el hilo principal de renderizado de React.
  Con una paginación reactiva en cliente a 50 tarjetas por página, la huella concurrente en `#msg-list` se reduce drásticamente a un máximo de **2,500 nodos concurrentes** (reducción del 90%), o a **1,250 nodos** al seleccionar 25 tarjetas por página, restableciendo un desplazamiento constante a 60 fps.
- **Tope Rígido Artificial en Backend (`max_limite = 1000`):**
  En `puente_motor_ia.py`, el endpoint `/api/community/messages` impone un tope rígido mediante `max_limite = max(1, min(max_limite, 1000))`. Al existir actualmente 1,210 interacciones en la base de datos, más de 210 mensajes quedan permanentemente inaccesibles e invisibles tanto para el usuario como para los filtros de curaduría.
- **Recálculo no memoizado de `filteredMessages`:**
  En `Messages.tsx`, la evaluación del arreglo `filteredMessages` se ejecuta en cada ciclo de renderizado sin envolverse en un `useMemo` con dependencias acotadas, recalculando innecesariamente la matriz de filtros ante cualquier cambio de estado efímero (como hover, clicks o animaciones).

#### 2. Base de Datos SQLite y Endpoints GET — Ausencia de Índices Estratégicos (< 2 ms)
- **Consultas con Escaneo Secuencial de Tabla (`SCAN interacciones`):**
  La base de datos local SQLite (`communitylab.db` y `motor-ia/communitylab.db`) únicamente cuenta con el índice automático implícito generado por la restricción `UNIQUE` sobre la columna `hash`. Carece de índices dedicados en columnas de alta frecuencia de filtrado y ordenamiento:
  - `enviado_en` y combinación `(enviado_en DESC, id DESC)`: utilizada por filtros temporales (`desde_utc`, `hasta_utc`) y orden cronológico descendente.
  - `canal`: consultada de forma repetida para partición de comunidad (`WHERE canal = ?`).
  - `estado_curaduria` y `etapa_flujo`: utilizadas intensivamente por los tableros de curaduría y la bandeja de redacción.
  - `interaccion_id` en `contenidos_generados`: consultada para correlacionar publicaciones efectivas multicanal (`Discord`, `LinkedIn`, `X`).
  Al ejecutar `EXPLAIN QUERY PLAN`, las consultas cotidianas reportan `SCAN interacciones`, realizando escaneos secuenciales completos. La creación de estos índices estratégicos garantizará que todas las lecturas GET respondan de forma estrictamente determinista en **menos de 2 milisegundos (< 2 ms)**.

#### 3. Carga Inicial de la Aplicación — Monolito de Empaquetado y Ausencia de Code-Splitting
- **Bundle Monolítico de ~1 MB:**
  En `frontend/src/App.tsx`, las 16 rutas de la aplicación (incluyendo `ContentStudio.tsx` con más de 4,300 líneas y módulos pesados como Recharts) son importadas estáticamente al inicio del archivo. La compilación de Vite advierte: `(!) Some chunks are larger than 500 kB after minification (dist/assets/index-SL2r4JnJ.js: 997.29 kB)`.
  Al ingresar a la plataforma, el navegador del usuario debe descargar y procesar este paquete gigante antes de poder renderizar incluso el Dashboard. La adopción de importaciones dinámicas (`React.lazy` y `<Suspense>`) permitirá dividir el paquete por rutas (`code-splitting`), reduciendo el bundle inicial a menos de **350 kB** y acelerando drásticamente el First Contentful Paint (FCP).
- **Preservación Estructural del Layout y Manejo de Errores de Carga:**
  Para evitar parpadeos molestos de la interfaz (sidebar y header superior) durante las transiciones de ruta, el contenedor `<Suspense>` debe situarse estrictamente en el interior del cuerpo de `MainLayout`, protegido por un `LazyRouteErrorBoundary` defensivo ante fallos de red (`ChunkLoadError`).

#### 4. Pestaña Dashboard (`Dashboard.tsx`) y Análisis (`Analytics.tsx`) — Desacoplamiento de Peticiones y Manejo de Datos Vacíos
- En `Dashboard.tsx`, para calcular series temporales y ratios de preguntas cuando los datos agregados de `analytics.sentiment.evolution` tienen pocos días, la página efectúa una llamada accesoria a `/api/community/messages?limit=500` con `cache: 'no-store'`. Si bien cuenta con salvaguardas defensivas, debe asegurarse que ningún fallo en este endpoint secundario bloquee los 6 KPI Cards principales ni el gráfico de evolución.
- En `Analytics.tsx`, el radar semántico (`RadarChart`), el gráfico de barras horizontales de hashtags y los scorecards de emojis deben tolerar gracefully cualquier conjunto de datos vacío o con caracteres especiales. Si `topics` o los datos del radar no contienen métricas válidas, debe renderizarse el estado visual `.c-empty` en vez de llamar a Recharts, evitando advertencias de valores `NaN` en la consola del navegador.

#### 5. Pestaña ContentStudio (`ContentStudio.tsx`) y OCI Storage (`OCIStorage.tsx`) — Estandarización Canónica de Modales
- En `ContentStudio.tsx` y `OCIStorage.tsx`, los modales de confirmación, redacción paralela e inspección deben estandarizarse canónicamente: contenedor exterior con `max-h-[90vh]` y `flex flex-col`, cuerpo con scroll interno `.c-modal__body` acotado a `max-h-[75vh]` (o `max-h-[70vh]` en viewports <= 768px) con `overflow-y-auto`.
- Las cabeceras y los botones de acción al pie deben permanecer siempre fijos y visibles fuera del área de scroll.
- El cierre mediante `Escape` o click en el backdrop debe estar habilitado en todo momento, salvo durante operaciones de red irreversibles de publicación activa (`isPublishingAnnouncement === true` o `complaintPublishing === true`).

### 1.3 Inviolabilidad Constitucional y Cero Secretos Quemados
- Se preserva de forma inmutable la Constitución del Proyecto (`docs/constitution.md`) y `AGENTS.md`. Queda estrictamente prohibido alterar los 17 archivos protegidos de la raíz, `backend/`, `motor-ia/` y `src/`.
- Todas las adaptaciones de backend se alojan exclusivamente en `puente_motor_ia.py` y las mejoras de frontend residen en `frontend/src/`.
- Absolutamente ningún token, clave API o credencial se almacena en código duro; todo se resuelve dinámicamente mediante variables de entorno (`os.environ`).
- Se aplica el principio constitucional 6 (Diseño Test-First / TDD): toda optimización de backend debe contar con su correspondiente prueba unitaria automatizada previa en `tests/test_unificacion_motor_ia.py`.

---

## 2. Requerimientos Funcionales (El QUÉ — Formato EARS)

### RF-01: Blindaje de Ingesta y Paginación Reactiva en Cliente (`Messages.tsx`)
- **CUANDO** el usuario ingrese a la pestaña de Ingesta de Mensajes (`/messages`), **EL SISTEMA DEBERÁ** solicitar al backend la totalidad de mensajes comunitarios (`GET /api/community/messages?limite=0`) para cargarlos en memoria cliente sin topes artificiales.
- **EN TODO MOMENTO**, los 4 KPI Cards superiores (`Analizados`, `Positivos`, `Preguntas`, `Destacados`) y la telemetría de mensajes reales vs bots **DEBERÁN** computarse con una exactitud matemática del 100% sobre la colección completa en memoria (1,192+ mensajes), independientemente del subconjunto o página que el usuario esté visualizando.
- **CUANDO** se rendericen las tarjetas de mensajes en el contenedor `#msg-list`:
  - **EL SISTEMA DEBERÁ** presentar los mensajes mediante una paginación reactiva estrictamente en el cliente con selector de elementos por página (25, 50, 100 mensajes, con valor por defecto de 50).
  - **EL SISTEMA DEBERÁ** renderizar simultáneamente en el DOM únicamente las tarjetas de la página activa (`paginatedMessages`), acotando la huella DOM en `#msg-list` a un máximo de **2,500 nodos concurrentes** para 50 tarjetas (o **1,250 nodos** para 25 tarjetas), reduciendo en más del 90% la sobrecarga respecto al renderizado sin paginar.
- **MIENTRAS** el usuario navegue entre páginas o alterne filtros:
  - **EL SISTEMA DEBERÁ** proveer controles visuales accesibles: botón "Anterior", botón "Siguiente", selector de tamaño de página, indicador de posición (`"Página X de Y"`), botones de salto numérico de página y un resumen cuantitativo exacto (ej. `"Mostrando 1–50 de 1,192 mensajes"`).
  - **EL SISTEMA DEBERÁ** reiniciar automáticamente a la primera página (`currentPage = 1`) cada vez que el usuario modifique cualquier criterio de filtro (texto de búsqueda, canal, sentimiento, estado de curaduría, etiqueta o rango de fechas) o cambie el tamaño de página.
- **CUANDO** se procese el filtrado de mensajes en cliente:
  - **EL SISTEMA DEBERÁ** envolver la lógica de `filteredMessages` en un `useMemo` con dependencias estrictas, evitando recálculos innecesarios ante eventos efímeros de la interfaz.

---

### RF-02: Indexación Estratégica en SQLite y Supresión de Topes Artificiales en Backend (`puente_motor_ia.py`)
- **CUANDO** se inicie la aplicación o se invoque la función `_asegurar_esquema_sqlite()` en `puente_motor_ia.py`, **EL SISTEMA DEBERÁ** crear de forma idempotente (`CREATE INDEX IF NOT EXISTS`) los siguientes 6 índices de alto rendimiento en la base de datos local SQLite:
  1. `idx_interacciones_enviado_id`: sobre `interacciones(enviado_en DESC, id DESC)`.
  2. `idx_interacciones_canal`: sobre `interacciones(canal, id DESC)`.
  3. `idx_interacciones_curaduria`: sobre `interacciones(estado_curaduria)`.
  4. `idx_interacciones_etapa`: sobre `interacciones(etapa_flujo)`.
  5. `idx_interacciones_id_desc`: sobre `interacciones(id DESC)`.
  6. `idx_contenidos_interaccion_estado`: sobre `contenidos_generados(interaccion_id, estado, estado_publicacion)`.
- **CUANDO** un cliente HTTP consulte `GET /api/community/messages`:
  - **EL SISTEMA DEBERÁ** admitir los parámetros de consulta `limite: int = 500`, `limit: int | None = None`, `offset: int = 0` y `pagina: int = 1`, manteniendo `limite: int = 500` por defecto para preservar estricta retrocompatibilidad con clientes antiguos y scripts existentes.
  - **SI** el cliente envía `limite=0` (o `limit=0`), **EL SISTEMA DEBERÁ** suprimir todo tope numérico artificial y retornar la totalidad absoluta de las interacciones registradas (superando los 1,000 registros y entregando los 1,192+ mensajes actuales).
  - **SI** el cliente envía `pagina > 1` y `offset == 0`, **EL SISTEMA DEBERÁ** calcular automáticamente el desplazamiento como `offset = (pagina - 1) * limite`, previniendo valores negativos (`offset = max(0, offset)`).
  - **EN TODO MOMENTO**, el endpoint **DEBERÁ** preservar al 100% la estructura JSON canónica preexistente (Principio 3 de la Constitución):
    ```json
    {
      "total": 1192,
      "omitted_bots_count": 18,
      "real_messages_count": 1192,
      "messages": [...]
    }
    ```
- **EN TODO MOMENTO**, todos los endpoints de lectura (`GET /api/community/messages`, `GET /api/community/dashboard`, `GET /api/community/analytics` y `GET /api/v1/oci-storage/reports`) **DEBERÁN** responder estrictamente desde SQLite local y memoria caché en menos de **2 milisegundos (< 2 ms)**, prohibiendo categóricamente llamadas WAN externas bloqueantes en su ciclo de ejecución.

---

### RF-03: Code-Splitting con `<Suspense>` Interior y Error Boundary Defensivo (`App.tsx`)
- **CUANDO** la aplicación frontend compile y se ejecute en el navegador:
  - **EL SISTEMA DEBERÁ** cargar de forma diferida mediante `React.lazy()` las 16 rutas de la aplicación en `frontend/src/App.tsx`, dividiendo el bundle monolítico de ~1 MB en fragmentos (chunks) asíncronos bajo demanda.
  - **EL SISTEMA DEBERÁ** ubicar el contenedor `<Suspense>` **DENTRO** del cuerpo de `MainLayout`, envolviendo estrictamente las rutas hijas (`<Routes>...</Routes>`), de modo que la barra superior y la barra lateral de navegación (Sidebar) permanezcan visibles, fijas e inmutables durante las transiciones de ruta, impidiendo cualquier parpadeo de la estructura principal.
  - **EL SISTEMA DEBERÁ** mostrar un fallback de carga minimalista y discreto (esqueleto o spinner CloudEdTech `#080A27` y `#FF7400`) exclusivamente en el área de contenido principal mientras se resuelve la importación dinámica de la ruta.
- **CUANDO** ocurra una interrupción de red o fallo de descarga de un chunk (`ChunkLoadError`):
  - **EL SISTEMA DEBERÁ** capturar la excepción mediante un componente defensivo `LazyRouteErrorBoundary` envolviendo a `<Suspense>`, presentando un estado amigable con botón de acción `"Reintentar carga"` (o recarga inteligente del documento), evitando pantallas en blanco o bloqueos silenciosos.
- **EN TODO MOMENTO**, el tamaño del paquete JavaScript inicial transferido (`initial vendor/app chunk`) **DEBERÁ** situarse por debajo de **350 kB** (gzip < 100 kB), eliminando la advertencia de Vite sobre chunks mayores a 500 kB.

---

### RF-04: Blindaje de Rendimiento y Manejo de Estados Vacíos en Dashboard y Análisis
- **CUANDO** el usuario ingrese al Dashboard (`/dashboard`):
  - **EL SISTEMA DEBERÁ** consultar en paralelo `/api/community/dashboard` y `/api/community/analytics`.
  - **SI** la llamada accesoria a `/api/community/messages` experimenta latencia o falla, **EL SISTEMA DEBERÁ** calcular las series temporales y métricas de soporte a partir de los datos agregados de `analytics` sin degradar ni bloquear la visualización de los 6 KPI Cards principales.
- **CUANDO** el usuario ingrese a la pestaña de Análisis (`/analytics`):
  - **SI** la colección de tópicos (`topics`) o los datos de polaridad para el `RadarChart` están vacíos o no contienen datos cuantitativos válidos, **EL SISTEMA DEBERÁ** mostrar directamente el estado visual estandarizado de CloudEdTech (`.c-empty`) con mensaje informativo, omitiendo la invocación del componente de Recharts para prevenir advertencias de valores `NaN` (`<path d="..." NaN />`) en la consola del navegador.
  - **SI** no existen emojis o hashtags registrados en el período seleccionado, **EL SISTEMA DEBERÁ** mostrar estados vacíos limpios y compactos sin desbordamientos de diseño.
  - **EL SISTEMA DEBERÁ** cancelar peticiones en curso al desmontar componentes mediante `AbortController`, previniendo advertencias de fugas de memoria en React.

---

### RF-05: Estandarización Canónica de Alturas de Modales y Resiliencia en ContentStudio y OCI Storage
- **CUANDO** el usuario interactúe con cualquier diálogo modal en la plataforma (modal de redacción paralela `.c-modal`, modal de confirmación de anuncios oficiales de Discord en `ContentStudio.tsx`, y modales de inspección y JSON en `OCIStorage.tsx`):
  - **EL SISTEMA DEBERÁ** estructurar el contenedor exterior del diálogo con `max-h-[90vh]` y disposición `flex flex-col`.
  - **EL SISTEMA DEBERÁ** acotar el cuerpo con scroll interno (`.c-modal__body`) a `max-h-[75vh]` en pantallas de escritorio, y a `max-h-[70vh]` en pantallas pequeñas o laptops (viewport vertical <= 768px), aplicando `overflow-y-auto`.
  - **EL SISTEMA DEBERÁ** fijar permanentemente las cabeceras (título y botón de cerrar) y los botones de acción al pie ("Confirmar", "Cancelar", "Publicar", "Cerrar") fuera del área de scroll interno, garantizando que permanezcan visibles e interactuables en todo momento.
  - **EL SISTEMA DEBERÁ** permitir cerrar el modal pulsando la tecla `Escape` o haciendo click en el fondo semitransparente (backdrop), excepto cuando exista una mutación de red irreversible de publicación en curso (`isPublishingAnnouncement === true` o `complaintPublishing === true`).
- **CUANDO** se invoque la sincronización manual de Discord (`syncDiscord`) o de OCI:
  - **EL SISTEMA DEBERÁ** ejecutar la sincronización de fondo con `asincrono: true`, retornando retroalimentación inmediata sin congelar los controles de la aplicación.
  - **SI** ocurre una colisión concurrente (código HTTP 409), **EL SISTEMA DEBERÁ** capturar la respuesta y notificar de manera informativa ("Ya hay una comprobación de mensajes en curso"), sin clasificarlo como error crítico.
- **CUANDO** el entorno carezca de credenciales en la nube de OCI (`subido_oci: false`, `status: "saved_locally"`):
  - **EL SISTEMA DEBERÁ** presentar un banner neutral o de éxito local ("Reporte generado y guardado localmente en reportes/{semana}.json"), prohibiendo cualquier estilo de alerta de error crítico cuando la persistencia local en disco se haya completado satisfactoriamente.

---

### RF-06: Inviolabilidad Constitucional, Preservación de Archivos Protegidos y Cero Secretos
- **EN TODO MOMENTO**, los 17 archivos protegidos de la raíz (`base_datos.py`, `reporte_semanal.py`, `procesamiento.py`, `api.py`, `modelos.py`, etc.), así como las carpetas `backend/`, `motor-ia/` y `src/`, **DEBERÁN** permanecer estrictamente inalterados.
- **EN TODO MOMENTO**, cualquier función de indexación SQLite, paginación ampliada, caché en memoria y resiliencia de endpoints **DEBERÁ** residir exclusivamente dentro de `puente_motor_ia.py` y sus pruebas asociadas en `tests/`.
- **EN TODO MOMENTO**, todas las credenciales de acceso, URLs y secretos **DEBERÁN** consumirse exclusivamente a través de variables de entorno (`os.environ` y `.env`), quedando estrictamente prohibida la inclusión de tokens o claves en código duro.

---

## 3. Requisitos No Funcionales (RNF)

- **RNF-01 (Velocidad de Lectura GET < 2 ms):**
  Todos los endpoints de consulta de datos locales (`/api/community/messages`, `/api/community/dashboard`, `/api/community/analytics`, `/api/v1/oci-storage/reports`) deben mantener un tiempo de respuesta de procesamiento backend inferior a **2 milisegundos (< 2 ms)** con el volumen actual de 1,192+ mensajes.
- **RNF-02 (Huella del Árbol DOM Reducida en 90%: <= 2,500 Nodos en Mensajes):**
  Al paginar las tarjetas en `Messages.tsx` con un tamaño estándar de 50 mensajes, el total de nodos DOM renderizados en el contenedor `#msg-list` no debe exceder de **2,500 nodos concurrentes** (o **1,250 nodos** al seleccionar 25 mensajes), garantizando una reducción del 90% respecto a los más de 25,000 nodos previos y permitiendo un desplazamiento fluido a 60 fps en cualquier dispositivo.
- **RNF-03 (Bundle Inicial Optimizado con Code-Splitting < 350 kB):**
  El tamaño del archivo JavaScript inicial cargado en la primera visita debe situarse por debajo de **350 kB** (con una reducción mayor al 60% respecto al bundle monolítico anterior de 997 kB).
- **RNF-04 (Desacoplamiento Asíncrono de Operaciones Pesadas):**
  Toda operación de red hacia proveedores externos (Discord API, Supabase Enoc, OCI Object Storage) debe ejecutarse de forma 100% asíncrona mediante tareas en segundo plano (`asyncio.create_task`), garantizando que la respuesta HTTP hacia el usuario se emita en menos de 100 ms.
- **RNF-05 (Compatibilidad de Tipos y Pruebas Unitarias):**
  El comando de compilación del frontend `npm run build` (`tsc -b && vite build`) debe compilar con código de salida 0 sin advertencias críticas de tipo. El conjunto completo de pruebas unitarias (`pytest`) debe mantenerse 100% en verde con cero regresiones.

---

## 4. Casos Límite y Manejo de Errores

### 4.1 Búsqueda y Filtros Combinados con Cero Resultados en Mensajes
- **SI** el usuario aplica filtros cruzados (ej. Canal `#pqrs`, Sentimiento Negativo, Palabra clave inexistente) que no arrojan ningún mensaje:
  - El sistema muestra el estado vacío estandarizado de CloudEdTech (`.c-empty`) con mensaje orientador: `"No se encontraron mensajes. Prueba con otros filtros o limpia la búsqueda."`.
  - La paginación oculta los botones de navegación o muestra `"Página 1 de 1"` con botones deshabilitados, impidiendo divisiones por cero (`0 / pageSize`).

### 4.2 Navegación a una Página Inexistente al Modificar Filtros
- **SI** el usuario se encontraba en la página 15 de 24 y luego aplica un filtro que reduce el total a 20 mensajes (1 sola página):
  - El sistema restablece automáticamente la página activa a `currentPage = 1`.
  - El usuario visualiza de inmediato los resultados filtrados sin quedar atrapado en una página vacía fuera de rango.

### 4.3 Radar Semántico, Tópicos y Emojis Vacíos en Análisis
- **SI** en el período seleccionado no existen mensajes con polaridades temáticas o el arreglo de `topics` está vacío:
  - El sistema no invoca a Recharts y renderiza en su lugar un contenedor `.c-empty` con icono y mensaje: `"No hay datos suficientes para generar el radar semántico en este período"`.
  - Se eliminan por completo los warnings de consola relativos a coordenadas con valor `NaN`.
  - Si no hay emojis registrados, se despliega una tarjeta informativa compacta indicando ausencia de reacciones en el rango analizado.

### 4.4 Peticiones Concurrentes de Sincronización Discord (HTTP 409)
- **SI** el usuario pulsa repetidamente el botón de sincronización de Discord o si la auto-sincronización de fondo coincide con un sync manual:
  - El backend retorna HTTP 409 con detalle `"Sincronización en curso"`.
  - El frontend captura dicho código y muestra una notificación informativa o de advertencia suave (`"Ya hay una comprobación de Discord en curso"`), impidiendo la aparición de banners rojos de error crítico.

### 4.5 Modales Abiertos en Pantallas Pequeñas (Viewport <= 768px de alto)
- **SI** el usuario abre el modal de redacción o confirmación en una laptop con resolución vertical reducida:
  - El diálogo aplica `max-h-[90vh]` con `flex flex-col`.
  - El cuerpo del modal (`.c-modal__body`) absorbe el scroll (`max-h-[70vh]` con `overflow-y-auto`), manteniendo el encabezado y los botones de acción fijos y clickeables en la base.
  - El cierre mediante `Escape` o backdrop se mantiene habilitado a menos que se esté publicando activamente (`isPublishingAnnouncement === true` o `complaintPublishing === true`).

### 4.6 Fallos de Conexión de Red, Error en Chunks Dinámicos y Servidor Offline
- **SI** la conexión falla al descargar un chunk asíncrono (`ChunkLoadError`):
  - `LazyRouteErrorBoundary` captura el fallo y despliega una interfaz limpia con el botón `"Reintentar carga"`.
- **SI** el servidor backend no responde (`TypeError: Failed to fetch`):
  - Las funciones de API capturan el error y notifican al usuario de forma clara sin romper la reactividad de la vista.

---

## 5. Criterios de Aceptación, Verificación y Estrategia Test-First (TDD)

### 5.1 Suite de Pruebas Automatizadas Unitarias (`tests/test_unificacion_motor_ia.py`)
En estricto cumplimiento del **Principio 6 de la Constitución (Diseño Test-First / TDD)**, se incorporarán pruebas unitarias automatizadas en `tests/test_unificacion_motor_ia.py` que precederán y validarán las optimizaciones de backend:

1. `test_indices_sqlite_creacion_idempotente`:
   - Verifica que la ejecución de `_asegurar_esquema_sqlite()` crea exitosamente en la base de datos local SQLite los 6 índices estratégicos (`idx_interacciones_enviado_id`, `idx_interacciones_canal`, `idx_interacciones_curaduria`, `idx_interacciones_etapa`, `idx_interacciones_id_desc`, `idx_contenidos_interaccion_estado`).
   - Verifica que invocar la función múltiples veces es 100% idempotente y no produce errores de colisión.
2. `test_sqlite_indices_explain_query_plan`:
   - Ejecuta sentencias `EXPLAIN QUERY PLAN` sobre consultas frecuentes filtrando por `canal`, `estado_curaduria` y ordenamiento `enviado_en DESC, id DESC`.
   - Verifica que el optimizador de SQLite reporte `USING INDEX` para cada índice creado, erradicando los `SCAN TABLE interacciones` secuenciales.
3. `test_endpoint_messages_limite_cero_sin_tope`:
   - Invoca el endpoint `GET /api/community/messages?limite=0` y valida que la cantidad de mensajes devuelta en `messages` sea idéntica al total existente en la base de datos (superando 1,000 registros y entregando la totalidad de los 1,192+ mensajes).
4. `test_endpoint_messages_paginacion_pagina_offset`:
   - Invoca `GET /api/community/messages?limite=50&pagina=2` y valida que el backend calcule correctamente `offset = 50`, retornando los 50 elementos correspondientes a la segunda página.
   - Verifica el cálculo defensivo ante valores negativos de offset o límites nulos.
5. `test_endpoint_messages_retrocompatibilidad_estructura_json`:
   - Valida que la respuesta de `GET /api/community/messages` preserve con fidelidad absoluta las cuatro claves canónicas exigidas por el Principio 3 de la Constitución: `total`, `omitted_bots_count`, `real_messages_count` y `messages`.
6. `test_endpoints_lectura_latencia_sub_2ms`:
   - Mide el tiempo de ejecución en microsegundos de las consultas de lectura a `communitylab.db` con los índices aplicados, comprobando que se resuelven en un tiempo medio inferior a **2 milisegundos (< 2 ms)**.

### 5.2 Criterios de Aceptación y Verificación (Definition of Done)

1. **Paginación Reactiva en Cliente y Preservación de KPIs (`Messages.tsx`):**
   - La ingesta de mensajes solicita `?limite=0` y carga la totalidad de mensajes en memoria.
   - La paginación se realiza en cliente con selector de 25, 50 y 100 mensajes por página (por defecto 50).
   - El renderizado de tarjetas en `#msg-list` se limita a la página activa, reduciendo los nodos DOM concurrentes a un máximo de 2,500 nodos (para 50 tarjetas) o 1,250 nodos (para 25 tarjetas).
   - Los 4 KPI Cards superiores (`Analizados`, `Positivos`, `Preguntas`, `Destacados`) y el contador de bots/reales se calculan con exactitud del 100% sobre el total en memoria.
   - `filteredMessages` envuelto en `useMemo` con dependencias estrictas.
   - Controles de Anterior, Siguiente, salto numérico y selector de tamaño completamente operativos.
2. **Índices de Base de Datos y Supresión de Topes en Backend (`puente_motor_ia.py`):**
   - Creación idempotente de los 6 índices SQLite verificada con `EXPLAIN QUERY PLAN`.
   - `GET /api/community/messages` admite `limite=0` retornando todos los mensajes sin tope forzado a 1,000.
   - Preservación íntegra de la estructura JSON canónica preexistente.
   - Consultas de lectura respondiendo en menos de 2 ms sin llamadas externas bloqueantes.
3. **División de Código (Code-Splitting) con Suspense Interior y Error Boundary (`App.tsx`):**
   - Rutas principales cargadas diferidamente con `React.lazy()`.
   - Contenedor `<Suspense>` ubicado dentro de `MainLayout`, manteniendo fijos y visibles la barra superior y el Sidebar sin parpadeos.
   - `LazyRouteErrorBoundary` integrado para capturar fallos de red (`ChunkLoadError`) con botón de reintento.
   - Bundle inicial reducido a menos de 350 kB, resolviendo la advertencia de Vite chunk size.
4. **Resiliencia en Dashboard, Análisis, ContentStudio y OCI Storage:**
   - En `Analytics.tsx`, visualización de `.c-empty` cuando `topics` o el radar carecen de datos numéricos, eliminando warnings de `NaN` en consola.
   - Modales acotados a `max-h-[90vh]` con cuerpo interno `.c-modal__body` en `max-h-[75vh]` (o `max-h-[70vh]` en viewports <= 768px) con `overflow-y-auto`.
   - Cabeceras y botones de acción siempre fijos y visibles fuera del scroll.
   - Bloqueo de cierre restringido exclusivamente a publicaciones irreversibles activas.
   - Notificaciones amigables ante HTTP 409 y banner local no crítico en modo offline de OCI.
5. **Inviolabilidad Constitucional y Cero Secretos:**
   - Cero modificaciones a los 17 archivos protegidos de la raíz, `backend/`, `motor-ia/` y `src/`.
   - Cero credenciales expuestas en código duro.
   - Suite de pruebas `pytest` 100% en verde (incluyendo los nuevos tests en `tests/test_unificacion_motor_ia.py`) y build de TypeScript `npm run build` exitoso con código 0.
