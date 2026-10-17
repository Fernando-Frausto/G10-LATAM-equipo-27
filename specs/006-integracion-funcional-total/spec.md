# Especificación 006: Integración Funcional Total (Frontend React + 3 Cerebros IA + Filtro de Fechas + OCI Tania + Copywriting Enoc)

## 1. Contexto y Propósito

### ¿Qué se busca lograr?
Dotar de funcionalidad real en vivo a todas las pantallas del Frontend de React (`frontend/`) en la rama `unificacion-beta`, conectándolas con los 3 cerebros de IA del proyecto (`"Groq (Llama 3.3)"`, `"Google Gemma 4"`, `"Google Gemini Flash Lite"`), el filtrado por rango de fechas (`desde` / `hasta`), la sincronización de reportes semanales hacia OCI Object Storage (`reporte_semanal.py` y `oci_uploader.py` de Tania) y la curación de copywriting en Supabase (`lotes_ia_kpis.copy_final` y `estado_revision` de Enoc).

Todo el procesamiento del lado del servidor se concentrará exclusivamente en `puente_motor_ia.py`, manteniendo **100% intactos los 12 archivos `.py` preexistentes de la raíz**, así como todos los archivos de `motor-ia/` y `backend/`.

### ¿Por qué es necesario?
1. **Funcionalidad Real de Extremo a Extremo en la UI de React:** Varias vistas del Frontend (`Highlights.tsx`, `Audience.tsx`, `Calendar.tsx`, `MyReports.tsx`, `Export.tsx`, `FeaturedStories.tsx`) consumen actualmente datos fijos de `mockCommunityData.ts`, y la pantalla `Messages.tsx` carece de los controles interactivos que sí tenía Streamlit (`app.py`) para elegir entre los 3 cerebros de IA y filtrar por rango de fechas (`Desde` / `Hasta`).
2. **Compatibilidad Automática y Cero Conflictos con Enoc y Tania:** Al no modificar ni una sola línea de los módulos `.py` de la raíz (`base_datos.py`, `evaluador_lotes.py`, `reporte_semanal.py`, `oci_uploader.py`, `armar_json_bot_python.py`, etc.) e invocarlos dinámicamente desde `puente_motor_ia.py`, cualquier mejora futura que Tania suba a `reporte_semanal.py` / `oci_uploader.py` o que Enoc actualice en la tabla `lotes_ia_kpis` de Supabase se integrará automáticamente sin conflictos de merge en Git.
3. **Cumplimiento Constitucional:** Se preserva el aislamiento de responsabilidades (Regla 2), la retrocompatibilidad total con Streamlit y el contrato de Copywriting (Regla 3), la lectura de credenciales desde variables de entorno (Regla 4) y la validación mediante pruebas automatizadas Test-First (Regla 6).

---

## 2. Requerimientos Funcionales (Formato EARS)

### RF-01: Evaluación de Mensajes con los 3 Cerebros de IA y Filtro por Rango de Fechas desde el Frontend (`puente_motor_ia.py` + `Messages.tsx` + `Settings.tsx`)
- **QUÉ:**
  - **CUANDO** el Frontend consulte `GET /api/v1/ai/models` en `puente_motor_ia.py`, **EL SISTEMA DEBERÁ** devolver la lista de los 3 proveedores/cerebros reales configurados en la raíz del proyecto (`"Groq (Llama 3.3)"`, `"Google Gemma 4"`, `"Google Gemini Flash Lite"`), indicando su identificador, nombre legible, modelo activo resuelto desde variables de entorno y disponibilidad.
  - **CUANDO** el usuario ejecute una evaluación por lote desde el Frontend mediante `POST /api/v1/ai/evaluate-batch` enviando `proveedor` (uno de los 3 cerebros), `desde` (fecha inicial opcional), `hasta` (fecha final opcional) y `solo_pendientes` (booleano), **EL SISTEMA DEBERÁ** invocar dinámicamente los módulos de la raíz (`ver_json.obtener_json(desde=..., hasta=...)`, el módulo cerebro seleccionado, `evaluador_lotes.evaluar_mensajes_lote` y `base_datos.guardar_lote_ia_kpis`) para evaluar los mensajes reales del rango solicitado, persistir los KPIs en `lotes_ia_kpis` (Supabase de Copywriting) y sincronizar inmediatamente la caché de `puente_motor_ia.py`.
  - **CUANDO** el usuario acceda a `frontend/src/pages/Messages.tsx`, **EL SISTEMA DEBERÁ** presentar un panel interactivo con selector de fecha inicial (`Desde`), selector de fecha final (`Hasta`), selector desplegable de los 3 cerebros de IA y un botón de acción para lanzar el análisis con IA sobre el rango seleccionado, además de mostrar en la bandeja tanto los mensajes en etapa `'ingesta'` (pendientes de análisis) como los que se encuentran `'en_analisis'`.
  - **CUANDO** el usuario acceda a `frontend/src/pages/Settings.tsx`, **EL SISTEMA DEBERÁ** mostrar los 3 cerebros reales del proyecto obtenidos desde `GET /api/v1/ai/models` en lugar de información estática desconectada.
- **POR QUÉ:**
  - Para trasladar al Frontend de React toda la potencia operativa que poseía el panel de Streamlit (`app.py`), permitiendo evaluar lotes reales con cualquiera de los 3 modelos de IA y acotar por fechas sin tocar los módulos base de la raíz.

### RF-02: Conexión Real con el Módulo OCI y Reportes Semanales de Tania y Copywriting de Enoc (`puente_motor_ia.py`)
- **QUÉ:**
  - **CUANDO** se invoque `POST /api/v1/oci-storage/weekly-sync` o `GET /api/v1/oci-storage/weekly-period` en `puente_motor_ia.py`, **EL SISTEMA DEBERÁ** delegar dinámicamente en las funciones reales de `reporte_semanal.py` (`generar_reporte_semanal`, `generar_y_subir_reporte`, `obtener_rango_semana_actual`) y `oci_uploader.py` de la raíz, retornando el periodo semanal real, el estado de subida a OCI Object Storage (o respaldo local cuando OCI no esté configurado) y los registros almacenados en `historial_reportes_semanales`.
  - **CUANDO** el flujo de Copywriting de Enoc inserte o actualice los campos `copy_final` o `estado_revision` en la tabla `lotes_ia_kpis` de Supabase, **EL SISTEMA DEBERÁ** reflejar dichos valores de forma inmediata y sin necesidad de reiniciar servicios en `/api/content`, `/api/v1/community/live-summary` y `/api/v1/export/community-data`.
- **POR QUÉ:**
  - Para asegurar que el trabajo de Tania (reportes semanales y almacenamiento en OCI Object Storage) y el de Enoc (curación HITL y `copy_final` en Supabase) queden conectados en vivo con el Frontend de React manteniendo 0% de modificaciones sobre sus archivos `.py` de la raíz.

### RF-03: Endpoints de Resumen Dinámico en Vivo y Exportación (`/api/v1/community/live-summary` y `/api/v1/export/community-data`) en `puente_motor_ia.py`
- **QUÉ:**
  - **CUANDO** el Frontend consulte `GET /api/v1/community/live-summary` o `GET /api/v1/export/community-data` en `puente_motor_ia.py`, **EL SISTEMA DEBERÁ** calcular y retornar en tiempo real a partir de los datos reales de `interacciones` y `lotes_ia_kpis` en Supabase (con fallback a SQLite/JSON local):
    1. `highlights` y `highlights_summary`: lista y métricas de mensajes destacados reales con `relevancia >= 70` (incluyendo `id`, `author`/`autor`, `channel`/`canal`, `content`/`texto`, `relevancia`, `sentiment`/`sentimiento`, `tema`, `temas_clave`, `razonamiento`, `copy_final` si existe, `estado_revision` y fecha).
    2. `audience`: métricas reales de audiencia compuestas por el total de autores únicos, miembros activos, tasa de participación y distribución real por segmentos de actividad (`Muy activos`, `Activos`, `Ocasionales`, `Baja actividad`) además de la distribución por segmento de IA (`segmento`).
    3. `calendar`: actividad diaria real agrupada por fecha (`date`, `day`, `messages`, `sentiment` predominante o promedio y lista de `highlights` del día).
    4. `reports`: historial real de reportes semanales obtenido desde `historial_reportes_semanales` en Supabase y/o `reporte_semanal.generar_reporte_semanal()`.
- **POR QUÉ:**
  - Para proveer una fuente de verdad unificada y en tiempo real que alimente todas las pantallas analíticas, de calendario, audiencia, historias destacadas, reportes y exportación del Frontend de React con datos verdaderos de la comunidad.

### RF-04: Conexión Dinámica de las Pantallas del Frontend (`Highlights.tsx`, `Audience.tsx`, `Calendar.tsx`, `MyReports.tsx`, `Export.tsx`, `FeaturedStories.tsx`)
- **QUÉ:**
  - **CUANDO** el usuario navegue a cualquiera de las vistas `Highlights.tsx`, `Audience.tsx`, `Calendar.tsx`, `MyReports.tsx`, `Export.tsx` o `FeaturedStories.tsx` en `frontend/`, **EL SISTEMA DEBERÁ** consultar en vivo `GET /api/v1/community/live-summary` (y `GET /api/v1/export/community-data` en `Export.tsx`) para renderizar los indicadores, tablas, tarjetas, segmentos, eventos de calendario, historias con `copy_final` y reportes reales.
  - **CUANDO** el usuario solicite descargar datos desde `Export.tsx`, **EL SISTEMA DEBERÁ** generar y descargar el archivo JSON con los datos reales de la comunidad, evaluaciones de IA, piezas de copywriting y reportes semanales obtenidos desde `/api/v1/export/community-data`.
  - **SI** ocurre un error de red o el backend no responde al cargar cualquiera de estas vistas, **EL SISTEMA DEBERÁ** aplicar un fallback controlado a los datos de respaldo (`mockCommunityData.ts`) sin bloquear ni romper el renderizado de la interfaz.
- **POR QUÉ:**
  - Para eliminar la dependencia de datos estáticos simulados en el Frontend de React y garantizar que cada pantalla refleje el estado real de la comunidad en Discord y Supabase.

### RF-05: Inmutabilidad de los Módulos `.py` de Raíz (Compatibilidad con Enoc y Tania) y Suite de Pruebas TDD
- **QUÉ:**
  - **EN TODO MOMENTO**, **EL SISTEMA DEBERÁ** mantener sin ninguna modificación los 12 archivos `.py` preexistentes en la raíz del proyecto (`api.py`, `app.py`, `armar_json_bot_python.py`, `base_datos.py`, `bot_lote.py`, `cerebro_ia.py`, `cerebro_ia_gemini_flash.py`, `cerebro_ia_gemma_4.py`, `evaluador_lotes.py`, `limpieza.py`, `modelos.py`, `oci_uploader.py`, `periodos.py`, `procesamiento.py`, `prompts_ia.py`, `reporte_semanal.py`, `ver_json.py`), así como todos los archivos dentro de `motor-ia/` y `backend/`.
  - **CUANDO** se ejecute `pytest`, **EL SISTEMA DEBERÁ** validar mediante pruebas automatizadas con mocks en `tests/test_unificacion_motor_ia.py`:
    1. `GET /api/v1/ai/models` listando los 3 cerebros reales.
    2. `POST /api/v1/ai/evaluate-batch` verificando la invocación con filtro de fechas (`desde`, `hasta`), selección de cualquiera de los 3 cerebros y persistencia en `lotes_ia_kpis`.
    3. `POST /api/v1/oci-storage/weekly-sync` y `GET /api/v1/oci-storage/weekly-period` verificando la delegación dinámica hacia `reporte_semanal.py` y `oci_uploader.py`.
    4. `GET /api/v1/community/live-summary` y `GET /api/v1/export/community-data` verificando el cálculo real de `highlights` (con `copy_final` de Enoc), `audience`, `calendar` y `reports`.
    5. La inmutabilidad de los módulos `.py` preexistentes de la raíz, manteniendo el 100% de la suite global de pruebas (`pytest`) en verde.
- **POR QUÉ:**
  - Para cumplir estrictamente con las Reglas 3 (Retrocompatibilidad Obligatoria) y 6 (Diseño Test-First / TDD) de `docs/constitution.md`, asegurando que las ramas de Enoc y Tania puedan integrarse sin conflictos de Git.

---

## 3. Restricciones y Cumplimiento Constitucional

1. **Rama de Trabajo (Regla 1):** El desarrollo se mantiene en `unificacion-beta` por instrucción explícita del usuario, respetando la prohibición de no hacer push directo a `main`.
2. **Inmutabilidad de los Módulos `.py` de Raíz, `motor-ia/` y `backend/` (Reglas 2 y 3):** Ningún archivo `.py` preexistente de la raíz ni ningún archivo de `motor-ia/` o `backend/` será modificado. Solo se editarán `puente_motor_ia.py`, los componentes de `frontend/src/`, `tests/test_unificacion_motor_ia.py`, `MEMORY.md` y los documentos en `specs/006-integracion-funcional-total/`.
3. **Seguridad de Secretos (Regla 4):** Todas las credenciales de Supabase, OCI y proveedores de IA se leen exclusivamente desde `os.environ`.
4. **Control de Dependencias (Regla 5):** No se añadirán paquetes externos no declarados.
5. **TDD Estricto (Regla 6):** Las nuevas pruebas en `tests/test_unificacion_motor_ia.py` deberán escribirse y verificarse antes de dar por completada la implementación.

---

## 4. Criterios de Aceptación Globales

- [ ] `GET /api/v1/ai/models` devuelve los 3 cerebros reales (`"Groq (Llama 3.3)"`, `"Google Gemma 4"`, `"Google Gemini Flash Lite"`) y `POST /api/v1/ai/evaluate-batch` evalúa mensajes reales filtrados por `desde` y `hasta` usando el cerebro elegido y guardando en `lotes_ia_kpis`.
- [ ] `Messages.tsx` cuenta con selectores de fecha (`Desde`, `Hasta`), selector de los 3 cerebros de IA, botón de evaluación por lote y visualización de mensajes en `'ingesta'` y `'en_analisis'`; `Settings.tsx` muestra los 3 cerebros reales.
- [ ] `POST /api/v1/oci-storage/weekly-sync` y `GET /api/v1/oci-storage/weekly-period` invocan dinámicamente `reporte_semanal.py` y `oci_uploader.py` de Tania, y los cambios de `copy_final` / `estado_revision` de Enoc en `lotes_ia_kpis` se reflejan automáticamente en los endpoints de contenido, resumen y exportación.
- [ ] `GET /api/v1/community/live-summary` y `GET /api/v1/export/community-data` calculan en tiempo real `highlights`, `audience`, `calendar` y `reports` desde Supabase, y las vistas `Highlights.tsx`, `Audience.tsx`, `Calendar.tsx`, `MyReports.tsx`, `Export.tsx` y `FeaturedStories.tsx` consumen dichos endpoints en vivo con fallback seguro.
- [ ] Ninguno de los archivos `.py` preexistentes de la raíz ni de `motor-ia/` o `backend/` ha sido modificado, y el 100% de los tests en `pytest` pasa en verde.
