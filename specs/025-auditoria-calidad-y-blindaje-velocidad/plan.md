# Plan de Implementación — Spec 025: Auditoría Integral de Calidad, Resiliencia de Interfaz y Blindaje de Alta Velocidad

## 1. Resumen Arquitectónico y Diagnóstico Técnico

### 1.1 Contexto del Ecosistema y Flujo de Datos
La plataforma CloudEdTech / CommunityLab opera con una base de datos activa de más de **1,192 mensajes reales** (1,210 interacciones registradas) distribuidas en canales canónicos de Discord (`#general`, `#faq`, `#pqrs`, `#notificaciones`, `#chat-egresados`, `#oportunidades-laborales`).

El sistema articula su operación en torno a tres capas principales:
1. **Capa de Persistencia Local SQLite (`communitylab.db` / `motor-ia/communitylab.db`):** Motor transaccional de lectura ultrarrápida (< 2 ms) para todas las vistas operativas (Dashboard, Ingesta de Mensajes, Análisis, ContentStudio y OCI Storage).
2. **Capa de Replicación y Enriquecimiento Asíncrono en Supabase Enoc (`swdoucawdasxmnomlcfu`):** Persistencia desacoplada en segundo plano (`asyncio.create_task`) para copys multicanal (LinkedIn, Discord, X) e histórico semanal (`public.historial_reportes_semanales`).
3. **Capa de Interfaz React / Vite (`frontend/src/`):** Aplicación de una sola página (SPA) con 16 rutas operativas que brindan curaduría Human-in-the-Loop, telemetría y distribución editorial.

```
                                      [ Usuario / Operador Comunitario ]
                                                      │
                                                      ▼
                                       ┌──────────────────────────────┐
                                       │    Frontend SPA (React 18)   │
                                       │   Code-Splitting + Suspense  │
                                       └──────────────┬───────────────┘
                                                      │
                                                      ▼ (HTTP REST / Axios / Fetch)
                                       ┌──────────────────────────────┐
                                       │      puente_motor_ia.py      │
                                       │    (FastAPI Gateway Local)   │
                                       └──────────────┬───────────────┘
                                                      │
                              ┌───────────────────────┴───────────────────────┐
                              ▼                                               ▼ (asyncio.create_task)
               ┌─────────────────────────────┐                 ┌─────────────────────────────┐
               │ SQLite Local communitylab.db│                 │  Supabase Enoc PostgreSQL   │
               │  (6 Índices Estratégicos)   │                 │ (historial_reportes_semanal)│
               │      Lectura < 2 ms         │                 │       Persistencia WAN      │
               └─────────────────────────────┘                 └─────────────────────────────┘
```

### 1.2 Diagnóstico de Cuellos de Botella y Puntos Críticos

1. **Ingesta de Mensajes (`Messages.tsx`) — DOM Clutter y Saturación de Nodos:**
   - La vista consumía mensajes mediante `?limite=500` e intentaba renderizar hasta 500 tarjetas completas en el contenedor `#msg-list`. Con ~50 nodos DOM por tarjeta (chips, badges, medidores de relevancia, desplegables de redacción), el árbol superaba los **25,000 nodos activos**, degradando los cuadros por segundo (jank) al hacer scroll.
   - En el backend (`puente_motor_ia.py`), un tope artificial rígido (`max_limite = min(..., 1000)`) ocultaba más de 210 mensajes reales de la base comunitaria.
   - La matriz de filtros `filteredMessages` se recalculaba en cada ciclo de render sin memoización explícita.
   - **Solución:** Consumir `GET /api/community/messages?limite=0` para tener el universo completo en memoria, computar los 4 KPI Cards superiores sobre el total global y aplicar una paginación reactiva en cliente con selector de 25, 50 y 100 elementos (default 50), acotando los nodos en `#msg-list` a un máximo de **2,500 nodos concurrentes** (reducción del 90%).

2. **Base de Datos SQLite — Escaneo Secuencial (`SCAN interacciones`):**
   - La tabla `interacciones` carecía de índices en `enviado_en`, `canal`, `estado_curaduria`, `etapa_flujo` e `id DESC`. La tabla `contenidos_generados` carecía de índice compuesto por interacción y estado.
   - Las consultas cotidianas incurrían en escaneos secuenciales completos (`SCAN TABLE`).
   - **Solución:** Crear de forma idempotente (`CREATE INDEX IF NOT EXISTS`) 6 índices estratégicos durante `_asegurar_esquema_sqlite()`, asegurando que el optimizador de SQLite use `USING INDEX` y reduzca las lecturas a tiempos deterministas estrictamente inferiores a **2 milisegundos (< 2 ms)**.

3. **Empaquetado Frontend (`App.tsx`) — Bundle Monolítico y Advertencias de Vite:**
   - Las 16 rutas eran importadas de manera estática en `App.tsx`, produciendo un chunk único minificado de **997.29 kB** (`(!) Some chunks are larger than 500 kB after minification`).
   - **Solución:** Implementar división de código (`React.lazy()`) para las 16 rutas. Ubicar el contenedor `<Suspense>` **dentro** del layout principal (`MainLayout`), manteniendo la cabecera móvil y el Sidebar fijos e inmutables durante transiciones. Proteger con `LazyRouteErrorBoundary` ante posibles errores de red (`ChunkLoadError`), reduciendo el bundle inicial a **< 350 kB** (gzip < 100 kB).

4. **Resiliencia en Visualizaciones (`Analytics.tsx` y `Dashboard.tsx`):**
   - En `Analytics.tsx`, el radar semántico (`RadarChart`) y el gráfico de barras horizontales de hashtags intentaban renderizarse aun con colecciones de datos vacías, generando advertencias en consola de coordenadas `<path d="..." NaN />`.
   - **Solución:** Desplegar directamente el estado visual `.c-empty` cuando `topics` o `radarTopicsData` estén vacíos o carezcan de valores numéricos, cancelando además peticiones con `AbortController` al desmontar. En `Dashboard.tsx`, desacoplar la carga agregada para que retardos en endpoints secundarios de mensajes no bloqueen los 6 KPI Cards.

5. **Estandarización Canónica de Modales (`ContentStudio.tsx` y `OCIStorage.tsx`):**
   - Diversidad de alturas y desbordamientos en diálogos modales (confirmación de anuncios, visor JSON, inspección y redacción paralela).
   - **Solución:** Estandarizar la estructura canónica: contenedor exterior con `max-h-[90vh]` y `flex flex-col`, cabecera y pie con botones de acción fijos fuera del scroll, y cuerpo con scroll interno (`.c-modal__body`) acotado a `max-h-[75vh]` (`max-h-[70vh]` en pantallas <= 768px) con `overflow-y-auto`. Cierre por `Escape` o backdrop habilitado en todo momento excepto durante publicaciones irreversibles activas.

6. **Inviolabilidad Constitucional y Cero Secretos:**
   - Cumplimiento irrestricto de `docs/constitution.md` y `AGENTS.md`. Queda prohibido alterar los 17 archivos protegidos de la raíz, `backend/`, `motor-ia/` y `src/`.
   - Todas las credenciales deben provenir exclusivamente de `os.environ` y `.env`.

---

## 2. Decisiones de Diseño y Solución Técnica

### 2.1 Paginación Reactiva en Cliente y Preservación Integral de Métricas en `Messages.tsx`
- **Carga de Datos:**
  El hook de carga invoca `GET /api/community/messages?limite=0`. El backend interpreta `limite=0` como la instrucción de entregar todas las interacciones registradas (1,192+ mensajes).
- **Cálculo Global de KPIs:**
  Los contadores superiores (`Analizados`, `Positivos`, `Preguntas`, `Destacados`) y la telemetría de mensajes reales vs bots se computan sobre el arreglo completo en memoria (`messageItems` o `filteredMessages`), preservando la exactitud del 100% sin importar qué página se esté visualizando.
- **Memoización con `useMemo`:**
  ```typescript
  const filteredMessages = useMemo(() => {
    return messageItems.filter((message) => {
      // Reglas de filtrado por autor, canal, sentimiento, búsqueda, curaduría y fecha
      ...
    });
  }, [messageItems, searchTerm, channelFilter, sentimentFilter, curationFilter, dateRange]);
  ```
- **Paginación en Cliente:**
  - Estados: `pageSize` (25, 50, 100; default: 50) y `currentPage` (entero >= 1; default: 1).
  - Cálculo:
    ```typescript
    const totalPages = Math.max(1, Math.ceil(filteredMessages.length / pageSize));
    const paginatedMessages = useMemo(() => {
      const start = (currentPage - 1) * pageSize;
      return filteredMessages.slice(start, start + pageSize);
    }, [filteredMessages, currentPage, pageSize]);
    ```
  - Controles de UI:
    - Selector `<select>` con opciones 25, 50, 100 por página.
    - Botones "Anterior" (`currentPage > 1`) y "Siguiente" (`currentPage < totalPages`).
    - Indicador textual: `"Mostrando {start + 1}–{Math.min(end, total)} de {total} mensajes"`.
    - Paginador con botones numéricos y salto a primera/última página.
  - Reset automático: todo cambio en `searchTerm`, `channelFilter`, `sentimentFilter`, `curationFilter`, `dateRange` o `pageSize` restablece automáticamente `currentPage = 1`.

### 2.2 Indexación Idempotente y Supresión de Topes en `puente_motor_ia.py`
- **6 Índices Estratégicos SQLite:**
  Dentro de `_asegurar_esquema_sqlite()`, se crean de forma idempotente con `CREATE INDEX IF NOT EXISTS`:
  1. `idx_interacciones_enviado_id` ON `interacciones(enviado_en DESC, id DESC)`
  2. `idx_interacciones_canal` ON `interacciones(canal, id DESC)`
  3. `idx_interacciones_curaduria` ON `interacciones(estado_curaduria)`
  4. `idx_interacciones_etapa` ON `interacciones(etapa_flujo)`
  5. `idx_interacciones_id_desc` ON `interacciones(id DESC)`
  6. `idx_contenidos_interaccion_estado` ON `contenidos_generados(interaccion_id, estado, estado_publicacion)`
- **Verificación con `EXPLAIN QUERY PLAN`:**
  Las consultas frecuentes en SQLite ejecutan con `USING INDEX`, suprimiendo los `SCAN TABLE` y garantizando que el procesamiento backend de lecturas se complete en **menos de 2 milisegundos (< 2 ms)**.
- **Ampliación de `consultar_mensajes_comunidad_enriquecido`:**
  - Parámetros: `limite: int = 500`, `limit: int | None = None`, `offset: int = 0`, `pagina: int = 1`.
  - Tratamiento de límite:
    - Si el valor efectivo (`limit` si no es `None`, o `limite`) es `0`: no se aplica cláusula `LIMIT` a la consulta de `interacciones`, retornando todos los registros sin tope forzado a 1000.
    - Si es `> 0`: se respeta el límite solicitado.
  - Cálculo de desplazamiento:
    - Si `pagina > 1` y `offset == 0`: `offset = (pagina - 1) * limite`.
    - Sanitización: `offset = max(0, offset)`.
  - Salida canónica intacta:
    ```json
    {
      "total": 1192,
      "omitted_bots_count": 18,
      "real_messages_count": 1192,
      "messages": [...]
    }
    ```

### 2.3 Code-Splitting por Rutas con `<Suspense>` Interior y `LazyRouteErrorBoundary`
- **Importaciones Dinámicas (`React.lazy`):**
  En `frontend/src/App.tsx`, las 16 rutas se importan mediante:
  ```typescript
  const Dashboard = lazy(() => import('./pages/Dashboard'));
  const Messages = lazy(() => import('./pages/Messages'));
  const Analytics = lazy(() => import('./pages/Analytics'));
  const ContentStudio = lazy(() => import('./pages/ContentStudio'));
  const OCIStorage = lazy(() => import('./pages/OCIStorage'));
  // ... resto de rutas
  ```
- **Preservación Estructural del Layout:**
  Para evitar parpadeos desagradables del Sidebar y de la cabecera móvil durante transiciones de página, `<Suspense>` se ubica **dentro** de `MainLayout` envolviendo a `<Outlet />`:
  ```tsx
  <LazyRouteErrorBoundary>
    <Suspense fallback={<RouteLoadingFallback />}>
      <Outlet />
    </Suspense>
  </LazyRouteErrorBoundary>
  ```
- **Defensiva ante Fallos de Red (`LazyRouteErrorBoundary`):**
  Captura errores de tipo `ChunkLoadError` derivados de interrupciones de red o nuevas versiones desplegadas en producción, ofreciendo un estado visual limpio con el botón `"Reintentar carga"` (forzando una recarga suave de la vista).
- **Resultado en Bundle:**
  El paquete JS principal se reduce de 997 kB a **< 350 kB** (gzip < 100 kB), eliminando por completo la advertencia de Vite sobre chunks mayores a 500 kB.

### 2.4 Blindaje contra Gráficos Vacíos y Resiliencia en Visualizaciones
- **Control de Estados Vacíos en `Analytics.tsx`:**
  - Si `topics` no contiene registros o si `radarTopicsData.length === 0`: se renderiza directamente un bloque `.c-empty` con mensaje orientador, omitiendo la instanciación de `<RadarChart>` para evitar advertencias de coordenadas `NaN` (`<path d="..." NaN />`) en la consola del navegador.
  - El gráfico de barras horizontales de hashtags despliega igualmente un contenedor `.c-empty` cuando no existen menciones registradas.
  - Se incorpora limpieza de suscripciones asíncronas con `AbortController` al desmontar.
- **Desacoplamiento en `Dashboard.tsx`:**
  - La visualización de los 6 KPI Cards principales y del gráfico de sentimiento se apoya en los agregados de `/api/community/dashboard` y `/api/community/analytics`.
  - Si la llamada de soporte a `/api/community/messages` falla o tarda, la página maneja el estado de forma degradada y silenciosa sin romper el renderizado general.

### 2.5 Estandarización Canónica de Modales y Resiliencia UX
- **Estructura Canónica en `ContentStudio.tsx` y `OCIStorage.tsx`:**
  - Contenedor modal: `.c-modal__dialog` con clases `max-h-[90vh] flex flex-col`.
  - Cabecera: `.c-modal__head` fija con título y botón de cierre.
  - Cuerpo desplazable: `.c-modal__body` con `max-h-[75vh] overflow-y-auto` en escritorio y `max-h-[70vh]` en viewports <= 768px.
  - Pie: `.c-modal__foot` fijo con botones de acción ("Confirmar", "Cancelar", "Publicar").
- **Regla de Cierre Defensivo:**
  - El usuario puede cerrar el diálogo pulsando `Escape` o haciendo click en el backdrop semitransparente.
  - Dicho cierre se bloquea exclusivamente cuando existe una mutación de red irreversible en progreso (`isPublishingAnnouncement === true` o `complaintPublishing === true`).
- **Resiliencia en Discord y OCI:**
  - Manejo informativo de colisiones concurrentes (código HTTP 409) en la sincronización manual de Discord.
  - Presentación de banners no críticos en modo offline de OCI (`saved_locally`).

---

## 3. Matriz de Requerimientos Funcionales vs Componentes

| Requerimiento Funcional | Archivos y Componentes Involucrados | Estrategia de Verificación Automatizada |
| :--- | :--- | :--- |
| **RF-01**: Blindaje de Ingesta y Paginación Reactiva en Cliente | `frontend/src/pages/Messages.tsx` | Verificación en cliente con `npm run build` y prueba de renderizado por página (<= 2,500 nodos). |
| **RF-02**: Indexación SQLite y Supresión de Topes en Backend | `puente_motor_ia.py` (`_asegurar_esquema_sqlite`, `consultar_mensajes_comunidad_enriquecido`) | Pruebas unitarias en `tests/test_unificacion_motor_ia.py` con `EXPLAIN QUERY PLAN` y consultas con `limite=0`. |
| **RF-03**: Code-Splitting con `<Suspense>` Interior y Error Boundary | `frontend/src/App.tsx`, `frontend/src/layouts/MainLayout.tsx`, `frontend/src/components/LazyRouteErrorBoundary.tsx` | `npm run build` generando chunks independientes y chunk inicial < 350 kB. |
| **RF-04**: Blindaje contra Gráficos Vacíos en Dashboard y Análisis | `frontend/src/pages/Analytics.tsx`, `frontend/src/pages/Dashboard.tsx` | Validación visual de `.c-empty` con datos vacíos y ausencia de advertencias `NaN` en consola. |
| **RF-05**: Estandarización Canónica de Alturas de Modales | `frontend/src/pages/ContentStudio.tsx`, `frontend/src/pages/OCIStorage.tsx` | Inspección CSS: `max-h-[90vh]` exterior, `max-h-[75vh]` en `.c-modal__body` y cabeceras/pies fijos. |
| **RF-06**: Inviolabilidad Constitucional y Cero Secretos | `docs/constitution.md`, `puente_motor_ia.py` | `git status --porcelain` asegurando 0 modificaciones en archivos protegidos de raíz, `backend/` y `motor-ia/`. |

---

## 4. Estrategia de Implementación TDD Estricta (Red -> Green -> Refactor)

```
        ┌─────────────────────────────────────────────────────────────┐
        │  1. FASE RED: Pruebas unitarias en tests/ (T1)              │
        │     - Índices SQLite con EXPLAIN QUERY PLAN                 │
        │     - Endpoint /messages sin topes (limite=0 -> 1,192+ msgs)│
        │     - Paginación pagina/offset y retrocompatibilidad JSON   │
        │     - Verificación de latencia determinista < 2 ms          │
        └──────────────────────────────┬──────────────────────────────┘
                                       │
                                       ▼
        ┌─────────────────────────────────────────────────────────────┐
        │  2. FASE GREEN: Implementación en puente_motor_ia.py (T2)   │
        │     - Creación idempotente de 6 índices SQLite              │
        │     - Manejo de limite=0 y cálculo de offset                │
        │     - Validación de tests pasando en verde (100%)           │
        └──────────────────────────────┬──────────────────────────────┘
                                       │
                                       ▼
        ┌─────────────────────────────────────────────────────────────┐
        │  3. FASE CLIENTE: Paginación reactiva en Messages.tsx (T3)  │
        │     - Petición limite=0 y KPIs calculados sobre el 100%     │
        │     - Memoización useMemo de filtros                        │
        │     - Paginador con selector 25/50/100 y huella <= 2,500 nds│
        └──────────────────────────────┬──────────────────────────────┘
                                       │
                                       ▼
        ┌─────────────────────────────────────────────────────────────┐
        │  4. FASE RENDIMIENTO: Code-Splitting en App.tsx (T4)        │
        │     - React.lazy() en las 16 rutas                          │
        │     - Suspense + LazyRouteErrorBoundary dentro de MainLayout│
        │     - Reducción del bundle inicial a < 350 kB               │
        └──────────────────────────────┬──────────────────────────────┘
                                       │
                                       ▼
        ┌─────────────────────────────────────────────────────────────┐
        │  5. FASE RESILIENCIA: Estados Vacíos y Modales (T5 & T6)    │
        │     - .c-empty en Analytics.tsx sin warnings NaN            │
        │     - Estandarización canónica de modales (max-h-[90vh/75vh])│
        │     - Cierre seguro Escape/backdrop                         │
        └──────────────────────────────┬──────────────────────────────┘
                                       │
                                       ▼
        ┌─────────────────────────────────────────────────────────────┐
        │  6. REFACTOR & CERTIFICACIÓN GLOBAL                         │
        │     - 100% tests pytest pasando en verde                    │
        │     - npm run build exitoso con código 0                    │
        │     - Auditoría git de archivos protegidos intactos         │
        └─────────────────────────────────────────────────────────────┘
```

---

## 5. Análisis de Impacto y Mitigación de Riesgos

1. **Riesgo: Romper la retrocompatibilidad del formato JSON en `/api/community/messages`.**
   - *Mitigación:* Se preservan rigurosamente las claves `total`, `omitted_bots_count`, `real_messages_count` y `messages`. Si el cliente no especifica `limite`, se mantiene el valor por defecto de 500 para clientes heredados.
2. **Riesgo: Parpadeo de la barra lateral (Sidebar) al cambiar de página por el Code-Splitting.**
   - *Mitigación:* El `<Suspense>` no envuelve al router ni a `MainLayout`, sino únicamente al contenedor de las vistas hijas (`<Outlet />`), asegurando que el Sidebar y la cabecera se mantengan montados de forma permanente.
3. **Riesgo: Fallo al descargar un chunk por problemas de conexión intermitente.**
   - *Mitigación:* El componente `LazyRouteErrorBoundary` atrapa la excepción y presenta una interfaz orientadora con un botón para reintentar la carga sin dejar la pantalla en blanco.
4. **Riesgo: Cómputo erróneo de KPIs al paginar en el cliente.**
   - *Mitigación:* Los KPI Cards superiores se calculan exclusivamente sobre el arreglo global en memoria (`filteredMessages` o `messageItems`), desconectando el resumen cuantitativo de la paginación visual activa.
5. **Riesgo: Violación de la Constitución por edición de archivos protegidos.**
   - *Mitigación:* Cero ediciones en los 17 archivos protegidos de la raíz, `backend/`, `motor-ia/` y `src/`. Todas las modificaciones se concentran en `puente_motor_ia.py`, `tests/` y `frontend/src/`.
