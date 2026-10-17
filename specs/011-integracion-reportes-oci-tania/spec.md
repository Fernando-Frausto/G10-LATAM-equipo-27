# Spec 011: Integración Funcional de Informes y Almacenamiento OCI (Flujo de Tania)

## 1. Contexto y Propósito (QUÉ y POR QUÉ)

### ¿Qué se solicita?
Transformar la pestaña **Informes y Almacenamiento** (`/oci-storage`) del frontend React para que deje de ser una maqueta estática desconectada y opere al 100% con el flujo real desarrollado por Tania para reportes semanales y distribución en **Oracle Cloud Infrastructure (OCI) Object Storage** (`reporte_semanal.py` y `oci_uploader.py`), expuesto a través del puente unificado (`puente_motor_ia.py`).

### ¿Por qué es necesario?
Actualmente, la vista de Informes y Almacenamiento presenta múltiples problemas de usabilidad y veracidad técnica:
1. **Estado bloqueado permanentemente**: El indicador principal compara `status === "ready"`, mientras que el backend responde `status: "connected"`, dejando la pantalla estancada en *"Verificando..."* con alerta amarilla perpetua.
2. **Métricas vacías quemadas en código**: Los cuatro contadores del encabezado (*JSON*, *Reportes*, *Assets IA*, *Exportaciones*) muestran guiones fijos (`—`) sin consultar los reportes generados ni los activos evaluados.
3. **Cuatro bloques decorativos muertos**: Las secciones *"Servicios CloudEdTech"*, *"Gestión administrativa"*, *"Panel de Automatización de Envíos de Reportes (LangGraph Cron Dispatcher)"* y *"Carga y Respaldo Manual"* contienen etiquetas falsas, interruptores sin estado y botones permanentemente deshabilitados que no corresponden a ninguna funcionalidad del proyecto y confunden al usuario.
4. **Sincronización silenciosa e incompleta**: El botón *"Preparar sincronización"* no permite indicar ni validar la etiqueta de la semana (`AAAA-semana-NN`), únicamente imprime la respuesta en la consola del navegador (`console.log`) y no ofrece visor de métricas, inspección del JSON generado ni descarga directa del archivo `{semana}.json` como sí lo hacía el módulo original de Tania en Streamlit.
5. **Tabla de historial vacía y sin acciones**: La tabla de informes semanales tiene quemado el texto *"Aún no hay informes almacenados"*, sus botones de filtro carecen de estado y no existe forma de consultar, descargar o reintentar la subida de los reportes semanales almacenados en `reportes/*.json` o consolidados desde `lotes_ia_kpis` en Supabase.

Con esta especificación se unifica la experiencia de Tania dentro del dashboard principal para que el equipo pueda elegir la etiqueta semanal, empaquetar las métricas y activos de copywriting, subirlos a OCI Object Storage (o preservarlos con aviso claro en Modo Offline/Respaldo Local), inspeccionar su estructura JSON, descargarlos y gestionar el historial completo de reportes semanales.

---

## 2. Requerimientos Funcionales (Formato EARS)

### RF-01: Reconciliación del Estado de OCI Object Storage y Contadores Deterministas en Cabecera
- **CUANDO** el usuario acceda a la pestaña de Informes y Almacenamiento (`/oci-storage`), **EL SISTEMA DEBERÁ** consultar `GET /api/v1/oci-storage/status` y `GET /api/v1/oci-storage/reports`.
- **MIENTRAS** se procese la respuesta de `GET /api/v1/oci-storage/status`, **EL SISTEMA DEBERÁ** mantener de forma retrocompatible las llaves `status: "connected"` y `message`, añadiendo de forma aditiva `oci_configured: bool`, `mode: "online" | "offline"`, `bucket: str` (valor de `OCI_BUCKET_NAME` o `"communitylab-assets"`) y `region: str` (por defecto `"Colombia Central (Bogotá)"`).
- **SI** el endpoint de estado responde con `status === "connected"` o `status === "ready"`, **EL SISTEMA DEBERÁ** mostrar la insignia de estado activa en el encabezado, diferenciando claramente si las credenciales de OCI están configuradas (`oci_configured: true` -> *"Conectado a OCI"*) o si opera con bypass seguro local (`oci_configured: false` -> *"Modo Offline / Respaldo Local"*), junto con el nombre del bucket destino.
- **MIENTRAS** se renderice la cabecera de métricas, **EL SISTEMA DEBERÁ** reemplazar los guiones estáticos (`—`) de las 4 tarjetas superiores utilizando la siguiente fórmula determinista basada en el historial de reportes (`reports`) y el reporte activo/más reciente:
  1. **Reportes Semanales**: Cantidad total de reportes disponibles en el historial (`reports.length`, o `0` si aún no existen reportes).
  2. **Mensajes Consolidados**: Valor de `resumen_metricas.total_mensajes` del reporte actualmente seleccionado en el visor (o del reporte más reciente del historial si ninguno ha sido seleccionado manualmente; `0` si no existen reportes).
  3. **Activos Aprobados**: Valor de `resumen_metricas.total_aprobados` del reporte actualmente seleccionado en el visor (o del reporte más reciente del historial; `0` si no existen reportes).
  4. **Sincronizados OCI / Respaldos**: Conteo desglosado de reportes subidos a OCI frente a los respaldados localmente en formato `"X OCI / Y Local"` (donde `X` es la cantidad de reportes con `subido_oci === true` e `Y` es la cantidad con `subido_oci === false`).

### RF-02: Eliminación de Maquetas Estáticas y Controles Sin Respaldo Funcional
- **MIENTRAS** el usuario navegue en la vista de Informes y Almacenamiento (`/oci-storage`), **EL SISTEMA DEBERÁ** omitir por completo los cuatro bloques estáticos sin funcionalidad real en el proyecto:
  1. Tarjeta *"Servicios CloudEdTech"* (etiquetas fijas Admin API / Motor IA / HTTPS).
  2. Tarjeta *"Gestión administrativa"* (etiquetas fijas PostgreSQL / Sesiones activas / Auditoría).
  3. Bloque *"Panel de Automatización de Envíos de Reportes (LangGraph Cron Dispatcher)"* con interruptores decorativos y botón deshabilitado.
  4. Bloque *"Carga y Respaldo Manual"* con zona de arrastre inactiva y botón *"Seleccionar archivo"* deshabilitado.
- **EL SISTEMA DEBERÁ** presentar exclusivamente secciones 100% operativas vinculadas al flujo de generación, inspección, descarga y distribución de reportes semanales de Tania.

### RF-03: Generación y Subida de Reporte Semanal con Etiqueta Editable (`AAAA-semana-NN`) y Correspondencia de Semanas
- **CUANDO** se cargue la sección de generación de reporte semanal, **EL SISTEMA DEBERÁ** consultar `GET /api/v1/oci-storage/weekly-period`, el cual conservará intactas las llaves `semana_nombre`, `week_label`, `start_date`, `end_date` y `status: "ready"` por retrocompatibilidad con las pruebas existentes, añadiendo de forma aditiva `iso_week_label` (calculado con `isocalendar()` en formato `AAAA-semana-NN` tal como en `app.py` de Tania), y pre-rellenar el campo editable **"Etiqueta de la Semana"**.
- **SI** el usuario ingresa una etiqueta que no cumple el patrón `^\d{4}-semana-\d{2}$` (validado con `reporte_semanal.validar_etiqueta`), **EL SISTEMA DEBERÁ** mostrar un mensaje de validación claro indicando el formato requerido (`AAAA-semana-NN`) en el frontend, y si se invoca `POST /api/v1/oci-storage/weekly-sync` con una etiqueta inválida, el backend capturará el `ValueError` y responderá con código **HTTP 400 Bad Request** y un `detail` descriptivo.
- **CUANDO** el usuario pulse el botón **"Generar y Subir Reporte a OCI"**, **EL SISTEMA DEBERÁ** deshabilitar temporalmente los controles de acción mostrando el estado de carga (*"Empaquetando y subiendo..."*) e invocar `POST /api/v1/oci-storage/weekly-sync` con el payload `{"semana": "<etiqueta>"}`.
- **MIENTRAS** `POST /api/v1/oci-storage/weekly-sync` prepara el paquete de datos para `reporte_semanal.generar_reporte_semanal(etiqueta, paquete)`, **EL SISTEMA DEBERÁ** buscar en el lote de mensajes evaluados (`lotes_ia_kpis` de Supabase / SQLite) aquellos registros cuya semana coincida de forma exacta (`AAAA-semana-NN`), por sufijo numérico equivalente (`Semana_NN`, donde `NN` son los dos últimos dígitos de la etiqueta) o por la semana ISO de su `fecha_envio`; y **SI** no existen registros para esa etiqueta específica, **EL SISTEMA DEBERÁ** aplicar como fallback seguro el lote consolidado completo de mensajes analizados disponibles (de Supabase o `resultados_kpis.json`, idéntico al comportamiento de `app.py`), garantizando que el usuario siempre pueda empaquetar y generar el reporte.
- **SI** no existen mensajes analizados en ninguna fuente (ni en Supabase, ni en SQLite, ni en `resultados_kpis.json`), **EL SISTEMA DEBERÁ** capturar el `ValueError` de `generar_reporte_semanal` y responder con **HTTP 400 Bad Request** y un mensaje claro en la interfaz indicando que primero deben evaluarse mensajes con IA.
- **CUANDO** `POST /api/v1/oci-storage/weekly-sync` finalice con éxito, **EL SISTEMA DEBERÁ** retornar todas las llaves retrocompatibles (`exito`, `status`, `semana`, `subido_oci`, `bucket`, `ruta_oci`, `resumen`, `sync_id`, `message`) añadiendo la clave `reporte` con el diccionario completo retornado por `generar_reporte_semanal` (`metadata`, `resumen_metricas`, `activos_copywriting`).
- **SI** la subida a Oracle Cloud Infrastructure Object Storage resulta exitosa (`subido_oci: true`), **EL SISTEMA DEBERÁ** mostrar un banner de confirmación en verde indicando el bucket y la ruta destino (`{bucket}/activos/{semana}/paquete-distribucion.json`).
- **SI** el entorno no cuenta con credenciales de OCI configuradas o se activa el bypass seguro (`subido_oci: false`), **EL SISTEMA DEBERÁ** mostrar un aviso informativo claro de **Modo Offline / Respaldo Local**, confirmando que el reporte oficial fue generado y preservado exitosamente en `reportes/{semana}.json` y está listo para visualización y descarga inmediata.

### RF-04: Visor Interactivo de Reporte JSON, Resumen de Métricas y Descarga Directa
- **CUANDO** se genere un reporte semanal o el usuario seleccione la opción **"Ver JSON"** de cualquier reporte del historial, **EL SISTEMA DEBERÁ** desplegar un panel de inspección interactivo que muestre:
  1. **Resumen ejecutivo del paquete**: Total de mensajes procesados (`total_mensajes`), total de aprobados (`total_aprobados`), total de descartados (`total_descartados`), desglose de `sentimiento`, top 5 `temas_tendencia` y distribución por `segmentos`.
  2. **Metadatos de distribución OCI**: Etiqueta de `semana`, fecha UTC `generado_en`, nombre del `bucket`, `ruta` de objeto OCI (`activos/{semana}/paquete-distribucion.json`) y estado booleano `subido`.
  3. **Visor del JSON completo**: El objeto íntegro del reporte (`metadata`, `resumen_metricas` y `activos_copywriting`) formateado y legible.
- **CUANDO** el usuario pulse el botón **"Descargar `{semana}.json`"**, **EL SISTEMA DEBERÁ** iniciar la descarga directa en el navegador del archivo JSON con codificación UTF-8 e indentación de 2 espacios, idéntico al archivo generado por `reporte_semanal.py`.

### RF-05: Historial Real de Informes Semanales, Reconstrucción Resiliente y Filtros Activos
- **CUANDO** el frontend consulte `GET /api/v1/oci-storage/reports`, **EL SISTEMA DEBERÁ** escanear el directorio local `reportes/*.json` (ignorando de forma segura cualquier archivo JSON corrupto o ilegible sin interrumpir la respuesta) y, adicionalmente, verificar los lotes evaluados de Supabase (`lotes_ia_kpis`) para asegurar que exista al menos el reporte semanal correspondiente a los datos evaluados cuando el contenedor efímero (como Render) aún no tenga archivos en `reportes/`, retornando el contrato JSON `{"reports": [...], "total": int}` ordenado cronológicamente (más reciente primero), donde cada elemento contiene:
  - `semana`: Etiqueta en formato `AAAA-semana-NN`.
  - `nombre_archivo`: Nombre del archivo (`{semana}.json`).
  - `tamano_bytes`: Tamaño en bytes del JSON serializado.
  - `generado_en`: Fecha y hora ISO UTC de generación.
  - `bucket`: Nombre del bucket OCI asociado.
  - `ruta_oci`: Ruta destino en el bucket (`activos/{semana}/paquete-distribucion.json`).
  - `subido_oci`: Booleano que indica si fue sincronizado con OCI Object Storage (`true`) o si permanece en respaldo local / Modo Offline (`false`).
  - `resumen_metricas`: Objeto con `total_mensajes`, `total_aprobados`, `total_descartados`, `sentimiento`, `temas_tendencia` y `segmentos`.
  - `reporte`: El diccionario completo del reporte semanal para previsualización y descarga inmediata.
- **CUANDO** el usuario seleccione uno de los botones de filtro de la tabla (**"Todos"**, **"Subido a OCI"**, **"Respaldo Local / Offline"**), **EL SISTEMA DEBERÁ** filtrar dinámicamente las filas mostradas en la tabla de informes semanales según su estado real de sincronización (`subido_oci === true` para *"Subido a OCI"* y `subido_oci === false` para *"Respaldo Local / Offline"*).
- **MIENTRAS** se visualice cada fila de la tabla de informes semanales, **EL SISTEMA DEBERÁ** mostrar la etiqueta de semana, el nombre del archivo (`{semana}.json`) y su ruta OCI, el tamaño en KB/bytes junto con la fecha de generación y el conteo de mensajes/aprobados, la insignia de estado (**"Subido a OCI"** en esmeralda o **"Respaldo Local (Modo Offline)"** en ámbar) y los botones de acción funcional:
  1. **Ver JSON**: Abre y enfoca el visor interactivo con el contenido de ese reporte y actualiza los contadores de detalle.
  2. **Descargar `.json`**: Descarga inmediatamente el archivo `{semana}.json`.
  3. **Subir / Reintentar OCI**: Invoca `POST /api/v1/oci-storage/weekly-sync` con `{"semana": fila.semana}`, deshabilitando el botón durante la petición para evitar clics concurrentes, y refresca el estado en la tabla y el visor.

### RF-06: Aislamiento Constitucional e Inmutabilidad de Módulos Originales
- **MIENTRAS** se implementen las mejoras de backend y frontend para la pestaña de Tania, **EL SISTEMA DEBERÁ** mantener intactos y sin modificaciones los archivos originales `reporte_semanal.py`, `oci_uploader.py`, `app.py` y demás módulos raíz, `backend/` y `motor-ia/`, concentrando los cambios exclusivamente en el adaptador `puente_motor_ia.py`, el cliente `frontend/src/api/ociStorage.ts`, la vista `frontend/src/pages/OciStorage.tsx` y la suite de pruebas automatizadas en `tests/`.

---

## 3. Contratos de API y Casos Límite (Edge Cases)

### 3.1 Contratos de API Retrocompatibles
1. **`GET /api/v1/oci-storage/status`**:
   - Conserva `status: "connected"` y `message: str`.
   - Añade `oci_configured: bool`, `mode: "online" | "offline"`, `bucket: str`, `region: str`.
2. **`GET /api/v1/oci-storage/weekly-period`**:
   - Conserva `semana_nombre`, `week_label`, `start_date`, `end_date`, `status: "ready"`.
   - Añade `iso_week_label: str` (`AAAA-semana-NN` vía `isocalendar()`).
3. **`POST /api/v1/oci-storage/weekly-sync`**:
   - Entrada: `{"semana": "AAAA-semana-NN"}` (opcional; si se omite, calcula la semana actual).
   - Salida exitosa (HTTP 200): Conserva `exito`, `status`, `semana`, `subido_oci`, `bucket`, `ruta_oci`, `resumen`, `sync_id`, `message` y añade `reporte` (objeto completo generado por `reporte_semanal.generar_reporte_semanal`).
   - Errores controlados (HTTP 400): Cuando `validar_etiqueta` o `generar_reporte_semanal` lanzan `ValueError`.
4. **`GET /api/v1/oci-storage/reports`**:
   - Salida exitosa (HTTP 200): `{"reports": [...], "total": int}`.

### 3.2 Manejo de Casos Límite (Edge Cases)
- **Etiqueta de semana con formato inválido**: Si el usuario envía una etiqueta que no respeta `AAAA-semana-NN` (ej. `"semana-40"` o `"2026-40"`), el frontend muestra error de validación inmediato y el backend devuelve HTTP 400 Bad Request con el mensaje de `validar_etiqueta`.
- **Ausencia total de mensajes analizados**: Si ni Supabase (`lotes_ia_kpis`), ni SQLite, ni `resultados_kpis.json` contienen mensajes evaluados, el backend captura el `ValueError` de `generar_reporte_semanal` y responde HTTP 400 Bad Request indicando que primero debe ejecutarse el análisis de IA.
- **Discrepancia de nomenclatura de semana (`Semana_NN` vs `AAAA-semana-NN`)**: El filtro de paquetes reconoce tanto `AAAA-semana-NN` como `Semana_NN` o la semana derivada de `fecha_envio`, y si la etiqueta solicitada es una semana personalizada sin coincidencias directas, aplica fallback al lote consolidado disponible para no bloquear la generación del reporte.
- **Prevención de concurrencia y clics repetidos**: Mientras una operación de generación/sincronización está en curso, los botones de disparo permanecen deshabilitados (`disabled`) con indicador visual de progreso.
- **Tolerancia a archivos corruptos en `reportes/*.json`**: Si algún archivo en la carpeta `reportes/` está malformado o incompleto, el escáner de `GET /api/v1/oci-storage/reports` lo ignora de forma segura sin producir un error 500.

---

## 4. Criterios de Aceptación Globales
1. La insignia de estado superior de OCI Object Storage nunca se queda trabada en *"Verificando..."* cuando el backend responde `status: "connected"` o `status: "ready"`, y distingue entre Modo Online (credenciales OCI presentes) y Modo Offline (respaldo local).
2. Los 4 contadores superiores muestran valores numéricos reales y deterministas (`Reportes Semanales`, `Mensajes Consolidados`, `Activos Aprobados` y `Sincronizados OCI / Respaldos`).
3. No existe ningún bloque decorativo falso ni botones permanentemente deshabilitados en `OciStorage.tsx`.
4. El usuario puede editar la etiqueta `AAAA-semana-NN`, generar el reporte semanal con `reporte_semanal.py`, intentar la subida con `oci_uploader.py`, ver el aviso de éxito o Modo Offline, inspeccionar el JSON completo con sus métricas y descargar el archivo `{semana}.json`.
5. La tabla de informes semanales lista todos los reportes reales (`GET /api/v1/oci-storage/reports`), permite filtrarlos por estado y ejecutar las acciones *Ver JSON*, *Descargar* y *Subir / Reintentar OCI*.
