# Tareas de Implementación — Spec 025: Auditoría Integral de Calidad, Resiliencia de Interfaz y Blindaje de Alta Velocidad

## [x] T1: Fase Red TDD en `tests/test_unificacion_motor_ia.py` (~20 min)
- **Rol:** `@implementer`
- **Archivos involucrados:**
  - `tests/test_unificacion_motor_ia.py`
- **Requerimientos Funcionales:** `RF-01`, `RF-02`, `RF-06`
- **Descripción:**
  1. Diseñar e implementar pruebas unitarias automatizadas exhaustivas en `tests/test_unificacion_motor_ia.py` para la Spec 025:
     - **Creación Idempotente de Índices:** `test_spec025_indices_sqlite_creacion_idempotente` que verifique que la ejecución de `_asegurar_esquema_sqlite()` crea exitosamente en la base de datos local SQLite los 6 índices estratégicos (`idx_interacciones_enviado_id`, `idx_interacciones_canal`, `idx_interacciones_curaduria`, `idx_interacciones_etapa`, `idx_interacciones_id_desc`, `idx_contenidos_interaccion_estado`) y que su ejecución repetida es 100% idempotente sin colisiones.
     - **Optimización con `EXPLAIN QUERY PLAN`:** `test_spec025_sqlite_indices_explain_query_plan` que ejecute sentencias `EXPLAIN QUERY PLAN` sobre consultas frecuentes filtrando por `canal`, `estado_curaduria`, `etapa_flujo` y ordenando por `enviado_en DESC, id DESC`, validando que el optimizador de SQLite reporte `USING INDEX` para cada índice creado, erradicando los `SCAN TABLE interacciones` secuenciales.
     - **Supresión de Tope en Límite Cero:** `test_spec025_endpoint_messages_limite_cero_sin_tope` que invoque `GET /api/community/messages?limite=0` y verifique que devuelva la totalidad absoluta de mensajes comunitarios (> 1,000 registros, entregando los 1,192+ mensajes actuales) sin truncar a 1,000.
     - **Paginación Backend por Página y Desplazamiento:** `test_spec025_endpoint_messages_paginacion_pagina_offset` que invoque `GET /api/community/messages?limite=50&pagina=2` y valide que el backend calcule correctamente `offset = 50`, retornando los 50 elementos correspondientes a la segunda página, con sanitización ante offsets negativos o límites nulos.
     - **Retrocompatibilidad de Estructura JSON:** `test_spec025_endpoint_messages_retrocompatibilidad_estructura_json` que valide que la respuesta preserve al 100% las cuatro claves canónicas exigidas por el Principio 3 de la Constitución: `total`, `omitted_bots_count`, `real_messages_count` y `messages`.
     - **Latencia Sub-2ms de Lectura:** `test_spec025_endpoints_lectura_latencia_sub_2ms` que mida la latencia de procesamiento backend en consultas de lectura a `communitylab.db` con los índices aplicados, comprobando una resolución inferior a 2 milisegundos (< 2 ms) sin llamadas WAN bloqueantes.
  2. Ejecutar pytest y confirmar que las pruebas fallen inequívocamente en la fase roja por falta de implementación en `puente_motor_ia.py`.
- **Criterio de verificación:**
  ```powershell
  pytest tests/test_unificacion_motor_ia.py -k "spec025" -v
  ```
- **Hecho cuando:** Todas las pruebas unitarias de la Spec 025 están redactadas en `tests/test_unificacion_motor_ia.py` y fallan en la fase Red con `AssertionError` por ausencia de la implementación requerida.

---

## [x] T2: Indexación Idempotente en SQLite y Paginación Sin Topes en `puente_motor_ia.py` (~20 min)
- **Rol:** `@implementer`
- **Archivos involucrados:**
  - `puente_motor_ia.py`
- **Requerimientos Funcionales:** `RF-02`, `RF-06`
- **Descripción:**
  1. En `puente_motor_ia.py`, dentro de la función `_asegurar_esquema_sqlite()`, incorporar la creación idempotente de los 6 índices estratégicos de alto rendimiento:
     - `CREATE INDEX IF NOT EXISTS idx_interacciones_enviado_id ON interacciones(enviado_en DESC, id DESC);`
     - `CREATE INDEX IF NOT EXISTS idx_interacciones_canal ON interacciones(canal, id DESC);`
     - `CREATE INDEX IF NOT EXISTS idx_interacciones_curaduria ON interacciones(estado_curaduria);`
     - `CREATE INDEX IF NOT EXISTS idx_interacciones_etapa ON interacciones(etapa_flujo);`
     - `CREATE INDEX IF NOT EXISTS idx_interacciones_id_desc ON interacciones(id DESC);`
     - `CREATE INDEX IF NOT EXISTS idx_contenidos_interaccion_estado ON contenidos_generados(interaccion_id, estado, estado_publicacion);`
  2. En la función `consultar_mensajes_comunidad_enriquecido`:
     - Admitir los parámetros de consulta `limite: int = 500`, `limit: int | None = None`, `offset: int = 0` y `pagina: int = 1`, manteniendo `limite = 500` por defecto.
     - Determinar el límite solicitado: `limite_solicitado = limit if limit is not None else limite`.
     - Si `limite_solicitado == 0`: no aplicar restricción numérica (`limite = None`), solicitando a `motor_bd.listar_interacciones(limite=None)` todas las interacciones de la base de datos sin tope artificial forzado a 1,000.
     - Si `limite_solicitado > 0`: respetar el límite solicitado.
     - Si `pagina > 1` y `offset == 0`: calcular `offset = (pagina - 1) * limite_solicitado`.
     - Sanitizar desplazamiento: `offset = max(0, offset)`.
     - Aplicar desplazamiento y límite a la colección de interacciones de forma eficiente.
     - Preservar la telemetría de mensajes omitidos por bots y retornar el JSON canónico con las claves `total`, `omitted_bots_count`, `real_messages_count` y `messages`.
- **Criterio de verificación:**
  ```powershell
  pytest tests/test_unificacion_motor_ia.py -k "spec025" -v
  ```
- **Hecho cuando:** Todas las pruebas de la Spec 025 pasan en verde (Green), certificando la creación de índices con planes `USING INDEX`, supresión del límite artificial a 1,000, soporte de offset/página y latencia < 2 ms.

---

## [x] T3: Paginación Reactiva en Cliente, Optimización de Renderizado y Huella DOM en `Messages.tsx` (~20 min)
- **Rol:** `@implementer`
- **Archivos involucrados:**
  - `frontend/src/pages/Messages.tsx`
- **Requerimientos Funcionales:** `RF-01`, `RF-06`
- **Descripción:**
  1. En `frontend/src/pages/Messages.tsx`, modificar la petición de consulta de mensajes a `${API_BASE_URL}/api/community/messages?limite=0` para cargar la colección completa de mensajes en memoria cliente.
  2. Garantizar que el cómputo de los 4 KPI Cards superiores (`Analizados`, `Positivos`, `Preguntas`, `Destacados`) y el contador de mensajes reales vs bots se sigan realizando de forma global sobre el 100% de la colección en memoria, sin afectarse por la página visualizada.
  3. Envolver la evaluación de `filteredMessages` en un `useMemo` con dependencias estrictas (`messageItems`, `searchTerm`, `channelFilter`, `sentimentFilter`, `curationFilter`, `dateRange`), evitando recálculos innecesarios por eventos efímeros.
  4. Implementar los estados reactivos de paginación en cliente:
     - `pageSize`: con selector de 25, 50 y 100 mensajes por página (por defecto: 50).
     - `currentPage`: entero representativo de la página activa (por defecto: 1).
  5. Calcular `totalPages = Math.max(1, Math.ceil(filteredMessages.length / pageSize))` y `paginatedMessages = useMemo(() => filteredMessages.slice((currentPage - 1) * pageSize, currentPage * pageSize), [filteredMessages, currentPage, pageSize])`.
  6. Restablecer automáticamente `currentPage = 1` cada vez que el usuario alterne cualquier criterio de filtro o modifique `pageSize`.
  7. Renderizar en el contenedor `#msg-list` estrictamente las tarjetas de `paginatedMessages`, acotando la huella concurrente en el DOM a un máximo de 2,500 nodos (para 50 tarjetas) o 1,250 nodos (para 25 tarjetas).
  8. Añadir la barra de controles de paginación canónica accesible:
     - Selector `<select>` con tamaños 25, 50, 100 por página.
     - Botón "Anterior" (deshabilitado en página 1).
     - Indicador cuantitativo `"Mostrando {start}–{end} de {total} mensajes"`.
     - Botones numéricos de salto de página.
     - Botón "Siguiente" (deshabilitado en última página).
- **Criterio de verificación:**
  ```powershell
  cd frontend; npm run build; cd ..
  ```
- **Hecho cuando:** La aplicación compila sin errores, `Messages.tsx` solicita `?limite=0`, renderiza únicamente los mensajes de la página activa reduciendo la huella DOM en un 90% (<= 2,500 nodos), los KPI Cards mantienen exactitud global del 100% y los controles de paginación operan de forma reactiva.

---

## [x] T4: Code-Splitting por Rutas con `<Suspense>` Interior y `LazyRouteErrorBoundary` en `App.tsx` y `MainLayout.tsx` (~20 min)
- **Rol:** `@implementer`
- **Archivos involucrados:**
  - `frontend/src/components/LazyRouteErrorBoundary.tsx`
  - `frontend/src/components/RouteLoadingFallback.tsx`
  - `frontend/src/App.tsx`
  - `frontend/src/layouts/MainLayout.tsx`
- **Requerimientos Funcionales:** `RF-03`, `RF-06`
- **Descripción:**
  1. Crear el componente `frontend/src/components/LazyRouteErrorBoundary.tsx` que capture fallos de descarga de fragmentos dinámicos (`ChunkLoadError`), presentando una interfaz limpia con botón de acción `"Reintentar carga"`.
  2. Crear el componente `frontend/src/components/RouteLoadingFallback.tsx` con un indicador de carga minimalista y discreto empleando los colores de CloudEdTech (`#080A27` y `#FF7400`).
  3. En `frontend/src/App.tsx`, reemplazar las importaciones estáticas de las 16 rutas por importaciones diferidas con `React.lazy()`.
  4. En `frontend/src/layouts/MainLayout.tsx` (o en `App.tsx`), envolver el área del `<Outlet />` con `<LazyRouteErrorBoundary>` y `<Suspense fallback={<RouteLoadingFallback />}>`, asegurando que el Sidebar y la cabecera superior permanezcan fijos, visibles y montados sin parpadeos durante las transiciones de ruta.
  5. Validar que la compilación de Vite divida el paquete JS en chunks individuales por ruta y que el bundle inicial transferido sea estrictamente inferior a **350 kB** (gzip < 100 kB), resolviendo la advertencia de chunks mayores a 500 kB.
- **Criterio de verificación:**
  ```powershell
  cd frontend; npm run build; cd ..
  ```
- **Hecho cuando:** La compilación de Vite finaliza con código 0 generando chunks asíncronos para cada ruta, el bundle inicial no supera los 350 kB y se erradica la advertencia de Vite sobre chunks mayores a 500 kB.

---

## [x] T5: Blindaje contra Gráficos Vacíos y Resiliencia en `Analytics.tsx` y `Dashboard.tsx` (~20 min)
- **Rol:** `@implementer`
- **Archivos involucrados:**
  - `frontend/src/pages/Analytics.tsx`
  - `frontend/src/pages/Dashboard.tsx`
- **Requerimientos Funcionales:** `RF-04`, `RF-06`
- **Descripción:**
  1. En `frontend/src/pages/Analytics.tsx`:
     - Evaluar si `topics` está vacío o si `radarTopicsData.length === 0`.
     - En caso de arreglo vacío o datos numéricos no disponibles, omitir la invocación del componente `<RadarChart>` y renderizar un contenedor visual `.c-empty` con icono y mensaje: `"No hay datos suficientes para generar el radar semántico en este período"`, suprimiendo advertencias de coordenadas `<path d="..." NaN />` en la consola del navegador.
     - En el gráfico de barras horizontales de hashtags, desplegar el estado visual `.c-empty` cuando no existan menciones registradas.
     - Incorporar la cancelación defensiva de peticiones pendientes mediante `AbortController` al desmontar el componente.
  2. En `frontend/src/pages/Dashboard.tsx`:
     - Asegurar que la consulta secundaria de mensajes a `/api/community/messages` se ejecute de forma desacoplada y defensiva, de modo que cualquier retardo o fallo en este endpoint secundario no bloquee ni altere la visualización inmediata de los 6 KPI Cards principales ni del gráfico de evolución.
- **Criterio de verificación:**
  ```powershell
  cd frontend; npm run build; cd ..
  ```
- **Hecho cuando:** `npm run build` compila con código 0 y la inspección de `Analytics.tsx` y `Dashboard.tsx` confirma la visualización limpia de estados `.c-empty` ante datos vacíos sin advertencias `NaN` en la consola.

---

## [x] T6: Estandarización Canónica de Modales, Resiliencia UX y Certificación Global (~20 min)
- **Rol:** `@implementer`
- **Archivos involucrados:**
  - `frontend/src/pages/ContentStudio.tsx`
  - `frontend/src/pages/OCIStorage.tsx`
  - `puente_motor_ia.py`
  - `tests/test_unificacion_motor_ia.py`
- **Requerimientos Funcionales:** `RF-05`, `RF-06`
- **Descripción:**
  1. En `frontend/src/pages/ContentStudio.tsx`:
     - Estandarizar el modal de redacción paralela (`.c-modal__dialog` con clases `max-h-[90vh] flex flex-col`, cabecera y pie fijos, y `.c-modal__body` con `max-h-[75vh] overflow-y-auto` en escritorio o `max-h-[70vh]` en viewports <= 768px).
     - Estandarizar el diálogo modal de respuestas a quejas (`role="dialog"` con contenedor `max-h-[90vh] flex flex-col`, cabecera y pie fijos, y cuerpo desplazable `max-h-[75vh] overflow-y-auto`).
     - Estandarizar el diálogo modal de confirmación de anuncios oficiales de Discord con cabecera y pie fijos y cuerpo desplazable.
     - Asegurar el cierre mediante la tecla `Escape` o click en el fondo semitransparente, manteniendo dicho cierre habilitado siempre, salvo durante operaciones irreversibles de red (`isPublishingAnnouncement === true` o `complaintPublishing === true`).
  2. En `frontend/src/pages/OCIStorage.tsx`:
     - Estandarizar el modal de inspección y el visor de JSON aplicando la estructura canónica `max-h-[90vh]` exterior y `.c-modal__body` con `max-h-[75vh] overflow-y-auto`.
     - Garantizar que el modo offline de OCI (`saved_locally`) presente un banner informativo o de éxito local no crítico.
  3. Ejecutar la suite completa de pruebas unitarias y de integración (`pytest tests/test_unificacion_motor_ia.py`) asegurando 100% de éxito (122+ tests en verde).
  4. Ejecutar el build de frontend `npm run build` verificando compilación limpia con código de salida 0.
  5. Ejecutar `git status --porcelain` para certificar la inviolabilidad estricta de los 17 archivos protegidos de la raíz, `backend/`, `motor-ia/` y `src/`.
- **Criterio de verificación:**
  ```powershell
  pytest tests/test_unificacion_motor_ia.py
  cd frontend; npm run build; cd ..
  git status --porcelain
  ```
- **Hecho cuando:** Todos los modales cumplen la estandarización canónica de dimensiones y cierre seguro, el 100% de los tests unitarios pasan en verde, el build de TypeScript finaliza con código 0 y cero archivos protegidos han sido modificados.
