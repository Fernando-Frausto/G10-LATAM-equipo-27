# Lista de Tareas (SDD) — Spec 011: Integración Funcional de Informes y Almacenamiento OCI (Flujo de Tania)

> Máximo 10 tareas de ~20 minutos cada una, siguiendo ciclo estricto TDD (Red -> Green -> Refactor) y preservando la inmutabilidad de los módulos raíz.

---

### [x] Tarea 1: Fase Red TDD — Pruebas de Contratos Enriquecidos y Historial OCI
- **Estado:** `[x]` Completada
- **Tiempo estimado:** 15 min
- **RFs cubiertos:** RF-01, RF-03, RF-04, RF-05, RF-06
- **Archivos a modificar:** [`tests/test_unificacion_motor_ia.py`](file:///c:/Users/jeova/OneDrive/Documentos/Alura/Codigo%20unificado%20con%20imports/tests/test_unificacion_motor_ia.py)
- **Descripción:**
  Añadir pruebas automatizadas en `tests/test_unificacion_motor_ia.py` que verifiquen:
  1. `GET /api/v1/oci-storage/status` conserva `status == "connected"` y `message`, e incluye `oci_configured` (`bool`), `mode` (`"online"` o `"offline"`), `bucket` y `region`.
  2. `GET /api/v1/oci-storage/weekly-period` conserva `semana_nombre`, `week_label`, `start_date`, `end_date`, `status == "ready"` e incluye `iso_week_label` con formato `^\d{4}-semana-\d{2}$`.
  3. `POST /api/v1/oci-storage/weekly-sync` con etiqueta válida genera el reporte y devuelve el objeto `reporte` completo (`metadata`, `resumen_metricas`, `activos_copywriting`) además de las llaves retrocompatibles, aplicando correspondencia de semana o fallback seguro al lote consolidado.
  4. `POST /api/v1/oci-storage/weekly-sync` con etiqueta inválida (ej. `"semana-invalida"`) devuelve código **HTTP 400 Bad Request**.
  5. `GET /api/v1/oci-storage/reports` devuelve `{"reports": [...], "total": int}` con los reportes generados en `reportes/*.json`, incluyendo `semana`, `nombre_archivo`, `tamano_bytes`, `generado_en`, `bucket`, `ruta_oci`, `subido_oci`, `resumen_metricas` y `reporte`, e ignora de forma segura archivos `.json` corruptos.
- **Hecho cuando:** Las nuevas pruebas existen en `tests/test_unificacion_motor_ia.py` y al ejecutar `pytest tests/test_unificacion_motor_ia.py -k "oci"` fallan en los nuevos campos/endpoints aún no implementados (Fase Red confirmada).

---

### [x] Tarea 2: Fase Green Backend — Implementación de Endpoints OCI y Historial en `puente_motor_ia.py`
- **Estado:** `[x]` Completada
- **Tiempo estimado:** 20 min
- **RFs cubiertos:** RF-01, RF-03, RF-04, RF-05, RF-06
- **Archivos a modificar:** [`puente_motor_ia.py`](file:///c:/Users/jeova/OneDrive/Documentos/Alura/Codigo%20unificado%20con%20imports/puente_motor_ia.py)
- **Descripción:**
  Implementar en `puente_motor_ia.py`:
  1. Enriquecimiento aditivo de `GET /api/v1/oci-storage/status` (`oci_configured`, `mode`, `bucket`, `region`).
  2. Enriquecimiento aditivo de `GET /api/v1/oci-storage/weekly-period` (`iso_week_label`).
  3. Actualización de `POST /api/v1/oci-storage/weekly-sync` con validación de etiqueta (`HTTP 400` ante `ValueError`), función auxiliar `_construir_paquete_para_semana` (búsqueda por `AAAA-semana-NN`, `Semana_NN` o semana ISO de fecha de envío + fallback al lote consolidado completo), persistencia del flag `subido` en `reportes/{semana}.json` y retorno del campo `reporte`.
  4. Nuevo endpoint `GET /api/v1/oci-storage/reports` (y `/api/v1/oci-storage/reports/`) que escanea `reportes/*.json` ignorando corruptos, reconstruye el reporte inicial desde lotes evaluados si `reportes/` está vacío y retorna `{"reports": [...], "total": int}` ordenado del más reciente al más antiguo.
- **Hecho cuando:** `pytest tests/ -v` pasa al 100% en verde (incluyendo las 78 pruebas previas y las nuevas pruebas de Spec 011) sin tocar ningún archivo `.py` protegido de la raíz.

---

### [x] Tarea 3: Cliente API y Refactorización Funcional Completa de `OciStorage.tsx`
- **Estado:** `[x]` Completada
- **Tiempo estimado:** 20 min
- **RFs cubiertos:** RF-01, RF-02, RF-03, RF-04, RF-05
- **Archivos a modificar:** [`frontend/src/api/ociStorage.ts`](file:///c:/Users/jeova/OneDrive/Documentos/Alura/Codigo%20unificado%20con%20imports/frontend/src/api/ociStorage.ts), [`frontend/src/pages/OciStorage.tsx`](file:///c:/Users/jeova/OneDrive/Documentos/Alura/Codigo%20unificado%20con%20imports/frontend/src/pages/OciStorage.tsx)
- **Descripción:**
  1. Actualizar `frontend/src/api/ociStorage.ts` con los tipos enriquecidos (`OCIStorageStatus`, `WeeklyPeriod`, `OCIReportItem`, `OCIReportsListResponse`, `WeeklySyncResponse`) y las funciones `startWeeklySync(semana?: string)` y `getOCIReports()`.
  2. Refactorizar `frontend/src/pages/OciStorage.tsx`:
     - Reconciliar badge de estado OCI (`connected` / `ready`, Modo Online vs. Modo Offline/Respaldo Local, bucket y región) y los 4 contadores deterministas (*Reportes Semanales*, *Mensajes Consolidados*, *Activos Aprobados*, *Sincronizados OCI / Respaldos*).
     - Eliminar los 4 bloques decorativos estáticos (*Servicios CloudEdTech*, *Gestión administrativa*, *Panel de Automatización LangGraph Cron Dispatcher* y *Carga y Respaldo Manual*).
     - Implementar el panel de Tania con input editable **Etiqueta de la Semana** (`AAAA-semana-NN`), validación de formato, botón **📦 Generar y Subir Reporte a OCI** con bloqueo de concurrencia y banners claros de éxito OCI o Modo Offline.
     - Implementar el **Visor Interactivo de Reporte Semanal** con tarjetas de resumen de métricas (`total_mensajes`, `total_aprobados`, `total_descartados`, `sentimiento`, `temas_tendencia`, `segmentos`), visor `<pre>` del JSON completo y botón **⬇️ Descargar `{semana}.json`**.
     - Conectar la tabla de **Historial de Informes Semanales** a `getOCIReports()` con filtros funcionales (*Todos*, *Subido a OCI*, *Respaldo Local / Offline*) y acciones reales por fila (*Ver JSON*, *Descargar `.json`* y *Subir / Reintentar OCI*).
- **Hecho cuando:** `OciStorage.tsx` y `ociStorage.ts` compilan sin errores TypeScript (`npm run build` exitoso) y todos los controles de la vista son 100% interactivos y conectados al backend.

---

### [x] Tarea 4: Verificación Global de Regresión, Compilación, Inmutabilidad y Memoria
- **Estado:** `[x]` Completada
- **Tiempo estimado:** 10 min
- **RFs cubiertos:** RF-01 a RF-06
- **Archivos a modificar:** [`MEMORY.md`](file:///c:/Users/jeova/OneDrive/Documentos/Alura/Codigo%20unificado%20con%20imports/MEMORY.md)
- **Descripción:**
  1. Ejecutar la suite completa de pruebas con `pytest tests/ -v` y verificar 0 fallos.
  2. Ejecutar `npm run build` en `frontend/` y verificar compilación limpia.
  3. Ejecutar `git status` para auditar que ningún archivo `.py` original de la raíz (`reporte_semanal.py`, `oci_uploader.py`, `app.py`, etc.), `backend/` ni `motor-ia/` haya sido modificado.
  4. Actualizar `MEMORY.md` documentando el cierre de la Spec 011.
- **Hecho cuando:** Todos los tests pasan en verde, el build de producción de React finaliza con éxito, la auditoría de inmutabilidad reporta 0 violaciones y `MEMORY.md` está actualizado.
