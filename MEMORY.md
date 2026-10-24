# MEMORY.md - Análisis de Comunidad con IA (Código Unificado)
Memoria del proyecto entre sesiones. Máximo ~50 líneas: resume o elimina lo que ya no aporte.

## Estado actual
- **Auditoría de Calidad y Blindaje de Alta Velocidad (Spec 025):** Indexación SQLite (`idx_interacciones_enviado_id`, `canal`, `curaduria`, `etapa`, `id_desc`, `contenidos_estado`) garantizando lecturas GET en < 2 ms y supresión de topes artificiales (`limite=0`). Paginación reactiva cliente en `Messages.tsx` (25/50/100, default 50) reduciendo huella DOM de 25k a < 2,500 nodos (-90%) con KPIs al 100%. Code-splitting dinámico (`React.lazy` + `Suspense` dentro de `MainLayout`) reduciendo bundle inicial de 1 MB a 263 kB (< 350 kB). Blindaje contra gráficos vacíos en `Analytics.tsx` (.c-empty) erradicando advertencias NaN. Modales canónicos `max-h-[90vh]/[75vh]` con scroll interno y escape defensivo. 128 tests pasando (128/128 en verde), build exitoso con código 0. Trabajo retenido localmente sin git push por instrucción del usuario.
- **Reportes OCI desde Historial Semanal (Spec 024):** Generación de reportes OCI extrayendo de `public.historial_reportes_semanales` en Supabase Enoc, copys reales (LinkedIn > Discord > X) y descarte complementado en SQLite local. Regla de Oro en `GET /reports`: cero llamadas WAN bloqueantes a OCI, lectura en < 2 ms (caché 5 min). Sincronización background de bucket OCI al inicio.
- **Persistencia en Historial y LangGraph Checkpointer (Spec 023):** Replicación en segundo plano (`asyncio.create_task`) a `public.historial_reportes_semanales` en Supabase Enoc. Session Mode (`:5432`) y `prepare_threshold=None` en LangGraph mitigando colisiones de prepared statements.
- **Migración Supabase Enoc y Unificación (Spec 022):** 204 interacciones en Enoc con paridad 100% de hashes y secuencia sincronizada.
- **Sincronización Discord de Alta Velocidad (Spec 021):** Sync manual ultrarrápido (< 1.5s) con Keep-Alive y réplica en segundo plano.
- **UI Homologada 1:1 con Cristian (Spec 020):** Dashboard (6 KPI cards, sparklines), Ingesta (4 KPIs, medidores), Análisis (Insights, radar semántico, emojis), ContentStudio (Mesa de Trabajo, anuncios Discord Live Embed) y OCI Storage.
- **Infraestructura y Tests:** 128/128 tests en verde (`pytest`), build frontend exitoso con código 0 (`npm run build`). Inviolabilidad absoluta de los 17 archivos protegidos de la raíz, `backend/`, `motor-ia/` y `src/`.

## Decisiones (y por qué)
- **Paginación en Cliente con Carga Total `?limite=0` (Spec 025):** Permite calcular los 4 KPI Cards y telemetría de bots con exactitud del 100% en memoria mientras se renderizan solo 50 tarjetas a la vez en el DOM, eliminando jank y sobrecarga de memoria.
- **Indexación Idempotente en SQLite (Spec 025):** La creación de 6 índices dedicados asegura que `EXPLAIN QUERY PLAN` use índices cubiertos (`USING INDEX`), manteniendo las lecturas sub-2ms incluso con miles de interacciones.
- **Code-Splitting dentro de `MainLayout` (Spec 025):** Al ubicar `<Suspense>` envolviendo exclusivamente a `<Outlet />`, la barra de navegación y el Sidebar permanecen fijos sin parpadeo visual al cambiar de pestaña, rebajando el bundle inicial de 1 MB a 263 kB.
- **Estandarización Canónica de Modales `max-h-[90vh]/[75vh]` (Spec 025):** Garantiza que cabecera y pie con botones queden permanentemente visibles en laptops y tablets, desplazando únicamente el cuerpo interno.
- **Inyección de Copys Reales desde `historial_reportes_semanales` (Spec 024):** Reemplazo de placeholders por copy curado aprobado.
- **Aislamiento WAN en `GET /reports` (Spec 024):** Respuesta en < 2 ms desde memoria o JSON local, desacoplada de la red externa.
- **Aislamiento Constitucional:** Cero modificaciones a los 17 archivos protegidos de la raíz ni `backend/`; compatibilidad en `puente_motor_ia.py` y `frontend/src/`.

## Errores a evitar
- Nunca modificar los archivos preexistentes de la raíz, `backend/` ni `motor-ia/`.
- Nunca saltarse el flujo ni asumir que un cambio es "demasiado pequeño".
- Nunca hacer push directo a `main` (Regla 1). Todo el trabajo se mantiene en ramas `feature/` o `beta-pruebas`.
- Nunca escribir credenciales en código duro (Regla 4).
- Nunca introducir llamadas de red bloqueantes en endpoints GET ni polling agresivo (<30s) en frontend (Regla de Oro de Alta Velocidad).
- Respetar la instrucción del usuario: no hacer git push hasta que lo autorice tras su junta.
