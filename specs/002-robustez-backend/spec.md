# Especificación: Robustez, Desacoplamiento y Resiliencia del Backend

## Contexto y Alcance
Esta especificación define los requerimientos de arquitectura, robustez, desacoplamiento y resiliencia para el backend de CommunityLab, resolviendo los hallazgos de la revisión de código y asegurando el estricto apego a la Constitución del proyecto (Aislamiento de Interfaz, Retrocompatibilidad, Seguridad de Secretos, Control de Dependencias y Diseño Test-First).

---

## Requerimientos Funcionales (EARS)

### 1. Filtrado de Bots y Webhooks en Consultas para Análisis (Unwanted Behavior / Event-driven)
- **QUÉ:** Cuando el sistema consulte o liste las interacciones disponibles para análisis (`base_datos.py` y `ver_json.py`), el sistema deberá excluir de los resultados cualquier mensaje generado por bots o webhooks (incluyendo autores históricos conocidos como `Spidey Boy#0000`, usuarios cuyo nombre coincida con patrones como `%bot%`, discriminadores de Discord terminados en `#0000`, o registros con tipo `bot`/`webhook`), garantizando que solo mensajes de miembros humanos sean suministrados al flujo de evaluación.
- **POR QUÉ:** Para evitar el desperdicio innecesario de tokens y llamadas de API en mensajes automatizados, anuncios o notificaciones del sistema, impidiendo que la actividad de bots contamine las métricas de sentimiento y relevancia de la comunidad.

---

### 2. Aislamiento de Lógica de Negocio y Orquestación en Backend (Ubiquitous Requirement)
- **QUÉ:** El sistema deberá encapsular toda la lógica de orquestación del análisis por lotes, llamadas a los motores LLM, captura de errores individuales, clasificación por umbral y persistencia en un módulo backend dedicado (`evaluador_lotes.py`). El archivo `app.py` deberá limitarse a actuar como interfaz de usuario (UI), invocando este servicio y recibiendo actualizaciones de progreso mediante callbacks o iteradores.
- **POR QUÉ:** Para cumplir con la Regla 2 de la Constitución ("Aislamiento de Interfaz"), asegurando que `app.py` funcione únicamente como carrocería de Streamlit sin lógica pesada de negocio o IA embebida, facilitando pruebas unitarias desacopladas y mantenimiento modular.

---

### 3. Desacoplamiento y Consistencia de Esquema en `/api/kpis` (State-driven / Unwanted Behavior)
- **QUÉ:** Cuando un cliente realice una solicitud HTTP GET a `/api/kpis`, el sistema deberá consultar prioritariamente los mensajes analizados desde la base de datos Supabase (tabla `lotes_ia_kpis`), reconstruir la estructura canónica `{"aprobados": [...], "descartados": [...]}` e inyectar el campo `copy_final` en los mensajes aprobados. Si no hay conexión con Supabase o la consulta falla, el sistema deberá realizar un fallback elegante leyendo el archivo local `resultados_kpis.json`. El endpoint deberá devolver SIEMPRE la estructura `{"aprobados": [...], "descartados": [...]}` (nunca una lista vacía `[]`) con códigos HTTP consistentes (200 ante éxito o estructura vacía, 500 ante error irrecuperable).
- **POR QUÉ:** Para desacoplar el servicio API del sistema de archivos local permitiendo despliegues en contenedores efímeros o la nube, preservando la retrocompatibilidad y consistencia del contrato de datos consumido por el frontend de Netlify.

---

### 4. Desacoplamiento y Disponibilidad de `/api/reporte-semanal` (State-driven / Unwanted Behavior)
- **QUÉ:** Cuando un cliente realice una solicitud HTTP GET a `/api/reporte-semanal`, el sistema deberá consultar prioritariamente el reporte consolidado más reciente desde la base de datos Supabase (tabla `historial_reportes_semanales`). Si la conexión no está disponible o la tabla no contiene registros, el sistema deberá realizar un fallback elegante al archivo JSON más reciente en el directorio local `reportes/`. Si ninguna fuente contiene datos, el sistema deberá retornar una respuesta estándar con código HTTP 404. Asimismo, el sistema deberá permitir la configuración de orígenes permitidos (CORS) mediante variables de entorno para entornos de producción.
- **POR QUÉ:** Para centralizar el consumo de métricas semanales desde la base de datos compartida y asegurar un comportamiento REST predecible y seguro para clientes externos.

---

### 5. Resiliencia de Inferencia y Protección ante Fallo Total del Lote (Unwanted Behavior / Event-driven)
- **QUÉ:** Durante la evaluación de un lote de mensajes con la IA, el sistema deberá encapsular la inferencia de cada mensaje en un bloque de control de excepciones individual. Si un mensaje individual falla (rate limits HTTP 429, timeout o error de proveedor), el sistema deberá registrar el error, omitir dicho mensaje y continuar evaluando el resto del lote. Al finalizar:
  - Si al menos un mensaje fue procesado con éxito, el sistema deberá persistir los mensajes analizados en `resultados_kpis.json` y en la base de datos Supabase.
  - Si el 100% de los mensajes del lote fallan, el sistema NO deberá sobrescribir el archivo `resultados_kpis.json` previo con datos vacíos, preservando el estado anterior y emitiendo una alerta clara de error en la interfaz.
- **POR QUÉ:** Para proteger el cómputo y los tokens consumidos en corridas parciales, garantizando que un fallo transitorio de red o proveedor no destruya los resultados analizados con anterioridad ni descarte mensajes ya procesados.

---

### 6. Protección de Estados Revisados por Humanos en Supabase (State-driven Requirement)
- **QUÉ:** Al sincronizar o re-analizar mensajes en la tabla `lotes_ia_kpis` de Supabase, el sistema deberá omitir la sobreescritura de aquellas filas cuyo `estado_revision` sea diferente de `'pendiente'` (por ejemplo, registros ya aprobados o editados por el equipo de Copywriting en su flujo HITL).
- **POR QUÉ:** Para salvaguardar el trabajo manual de curación y revisión realizado por el equipo editorial, evitando que un re-análisis automatizado destruya datos validados por humanos.

---

### 7. Unificación de Esquema Pydantic y Prompt Template de IA (Ubiquitous Requirement)
- **QUÉ:** El sistema deberá centralizar la definición del modelo de datos `FormatoSalida` y la plantilla de evaluación `template_filtro` en un único módulo compartido del backend (ej. `prompts_ia.py` o `modelos_ia.py`). Los tres módulos de ejecución de IA (`cerebro_ia.py`, `cerebro_ia_gemma_4.py` y `cerebro_ia_gemini_flash.py`) deberán importar estas definiciones desde dicha fuente única.
- **POR QUÉ:** Para eliminar la triplicación de código, garantizar la consistencia en los criterios de análisis entre modelos y facilitar futuras actualizaciones de las directrices de evaluación en un solo lugar.

---

### 8. Aislamiento e Higiene de Variables de Entorno por Motor de IA (Ubiquitous Requirement)
- **QUÉ:** El sistema deberá gestionar de manera independiente la parametrización de modelos:
  - El módulo `cerebro_ia_gemma_4.py` deberá leer `GEMMA_MODEL` (valor por defecto: `gemma-4-31b-it`).
  - El módulo `cerebro_ia_gemini_flash.py` deberá leer `GEMINI_MODEL` (valor por defecto: `gemini-3.5-flash-lite`).
  El sistema deberá sanear los valores eliminando espacios en blanco (`.strip()`) y, si el valor configurado está vacío o no está definido, deberá recurrir a su valor por defecto o secundariamente a `GOOGLE_MODEL`.
- **POR QUÉ:** Para prevenir colisiones donde una sola variable (`GOOGLE_MODEL`) imponga nombres de modelos incompatibles a distintos motores de inferencia, evitando errores de inicialización en tiempo de ejecución.

---

### 9. Limpieza e Higiene del Repositorio (Ubiquitous Requirement)
- **QUÉ:** El sistema deberá depurar archivos residuales de versiones anteriores:
  - Eliminar el script de parcheo obsoleto `update_app.py`.
  - Asegurar que `resultados_kpis.json` se encuentre activo en `.gitignore` para no versionar salidas de ejecución efímeras en Git.
  - Eliminar menciones y textos desactualizados en `app.py`.
- **POR QUÉ:** Para mantener la higiene del repositorio, prevenir commits accidentales de datos de pruebas o de desarrollo y mantener una base de código profesional y limpia.

---

### 10. Dependencias y Suite de Pruebas Unitarias Automatizadas (TDD) (Ubiquitous Requirement)
- **QUÉ:** El sistema deberá incorporar `pytest` y `httpx` (o el cliente de pruebas de FastAPI) en `requirements.txt` y contar con una suite completa de pruebas unitarias automatizadas que valide mediante dobles de prueba (mocks):
  1. El filtrado de autores de bots/webhooks en `base_datos.py` y `ver_json.py`.
  2. La extracción de lógica a `evaluador_lotes.py` y el manejo resiliente ante fallos parciales y fallo total (100%).
  3. Los endpoints `/api/kpis` y `/api/reporte-semanal` bajo consulta Supabase, fallback a archivo local y respuestas consistentes.
  4. La protección de filas revisadas en Supabase (`estado_revision != 'pendiente'`).
  5. La resolución aislada y saneada de las variables de entorno de los modelos.
  Ningún test unitario deberá realizar llamadas de red reales a APIs externas ni a bases de datos de producción.
- **POR QUÉ:** Para dar estricto cumplimiento a las Reglas 5 (Control de Dependencias) y 6 (Diseño Test-First) de la Constitución, garantizando la no regresión y la robustez del sistema en entornos CI/CD sin costo ni fragilidad de red.

---

## Criterios de Aceptación y Retrocompatibilidad
1. El contrato JSON devuelto por `/api/kpis` debe mantener intacta la estructura `{"aprobados": [...], "descartados": [...]}` con el atributo `copy_final` en cada aprobado.
2. `app.py` no debe contener llamadas directas de invocación a cadenas LLM ni loops de análisis de IA.
3. La ejecución de la suite de pruebas mediante `pytest` debe ejecutarse al 100% en verde de forma aislada y sin requerir conexión a internet ni variables de entorno activas.
