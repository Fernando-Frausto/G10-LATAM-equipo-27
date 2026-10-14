# Tareas de Implementación: Robustez, Desacoplamiento y Resiliencia del Backend

## Tarea 1: Preparación del entorno de pruebas e higiene del repositorio
- **RF:** RF-9, RF-10
- **Descripción:** Registrar formalmente las dependencias de prueba `pytest` y `httpx` en `requirements.txt`. Agregar la regla para ignorar `resultados_kpis.json` en `.gitignore` (descomentar o fijar). Eliminar físicamente el script residual `update_app.py`.
- [x] **Hecho cuando:** `requirements.txt` incluya `pytest` y `httpx`, `.gitignore` contenga la regla activa para `resultados_kpis.json`, `update_app.py` ya no exista en el sistema de archivos y `pytest --version` responda exitosamente en consola.

---

## Tarea 2: Tests unitarios para unificación de esquema y configuración de modelos (TDD)
- **RF:** RF-7, RF-8, RF-10
- **Descripción:** Crear el archivo `tests/test_modelos_ia.py` con pruebas unitarias para validar:
  1. La serialización y validación del modelo Pydantic `FormatoSalida` y la plantilla de prompt común.
  2. La lectura independiente y saneada de `GEMMA_MODEL` en `cerebro_ia_gemma_4` y `GEMINI_MODEL` en `cerebro_ia_gemini_flash` (verificando que cadenas vacías o con espacios recurran al default institucional o secundariamente a `GOOGLE_MODEL`).
- [x] **Hecho cuando:** El archivo `tests/test_modelos_ia.py` exista y sus pruebas fallen inicialmente (rojo) por no existir aún el módulo centralizado ni la parametrización desacoplada.

---

## Tarea 3: Implementar unificación de esquemas/prompts y resolución de variables de IA
- **RF:** RF-7, RF-8
- **Descripción:** Crear el módulo `prompts_ia.py` conteniendo la definición canónica de `FormatoSalida` y `template_filtro`. Refactorizar `cerebro_ia.py`, `cerebro_ia_gemma_4.py` y `cerebro_ia_gemini_flash.py` para importar desde `prompts_ia.py`, eliminando código duplicado e implementando la resolución limpia e independiente de `GEMMA_MODEL` y `GEMINI_MODEL`.
- [x] **Hecho cuando:** Todas las pruebas de `tests/test_modelos_ia.py` se ejecuten al 100% en verde.

---

## Tarea 4: Tests unitarios para filtrado de bots y protección de estados en Supabase (TDD)
- **RF:** RF-1, RF-6, RF-10
- **Descripción:** Crear el archivo `tests/test_base_datos_filtros.py` utilizando mocks de `psycopg2` para verificar:
  1. Que la consulta `listar_interacciones` excluya mensajes originados por bots o webhooks (`Spidey Boy#0000`, coincidencias `%bot%`, discriminadores `#0000`, y campo `tipo IN ('bot', 'webhook')`).
  2. Que la consulta de actualización `guardar_lote_ia_supabase` proteja las filas revisadas, asegurando que la cláusula `ON CONFLICT` incluya la condición `WHERE lotes_ia_kpis.estado_revision = 'pendiente'`.
- [x] **Hecho cuando:** El archivo `tests/test_base_datos_filtros.py` exista y sus pruebas fallen al ejecutarse sobre las consultas SQL actuales.

---

## Tarea 5: Implementar filtrado de bots y protección de estados en `base_datos.py` y `ver_json.py`
- **RF:** RF-1, RF-6
- **Descripción:** Actualizar `listar_interacciones` en `base_datos.py` y las validaciones de `ver_json.py` para excluir mensajes de bots y webhooks en las consultas destinadas al análisis. Actualizar la sentencia de inserción/actualización en `guardar_lote_ia_supabase` para no sobrescribir registros cuyo `estado_revision != 'pendiente'`.
- [x] **Hecho cuando:** Todas las pruebas de `tests/test_base_datos_filtros.py` pasen al 100% en verde.

---

## Tarea 6: Tests unitarios para el servicio backend `evaluador_lotes.py` (TDD)
- **RF:** RF-2, RF-5, RF-10
- **Descripción:** Crear el archivo `tests/test_evaluador_lotes.py` utilizando dobles de prueba (mocks) de las cadenas LangChain para validar:
  1. Evaluación exitosa de un lote completo y clasificación por umbral (>= 70 a aprobados, < 70 a descartados).
  2. Resiliencia y tolerancia ante fallos parciales: si un mensaje intermedio lanza excepción (rate limit/timeout), se captura, se continúa con el lote y se persisten los exitosos.
  3. Protección ante 100% de fallos: si todos los mensajes fallan, se verifica mediante mock de filesystem que el archivo preexistente `resultados_kpis.json` NO es sobrescrito con listas vacías.
  4. Invocación correcta del callback de progreso.
- [x] **Hecho cuando:** El archivo `tests/test_evaluador_lotes.py` exista y falle al ejecutarse por la ausencia del módulo `evaluador_lotes.py`.

---

## Tarea 7: Implementar módulo backend de orquestación `evaluador_lotes.py`
- **RF:** RF-2, RF-5
- **Descripción:** Crear el módulo `evaluador_lotes.py` con la función `evaluar_lote(...)`. Implementar la carga dinámica segura del motor seleccionado, el bucle con `try...except` individual por mensaje, la clasificación de KPIs, la sincronización de mensajes exitosos en `resultados_kpis.json` y Supabase, la protección de no-sobreescritura ante fallo total y el reporte estructurado de resultados.
- [x] **Hecho cuando:** Todas las pruebas de `tests/test_evaluador_lotes.py` pasen al 100% en verde.

---

## Tarea 8: Refactorizar `app.py` para cumplir aislamiento de interfaz UI
- **RF:** RF-2, RF-9
- **Descripción:** Modificar `app.py` eliminando el bucle manual de evaluación, la importación de cadenas LLM y el guardado directo de archivos. Conectar el botón de análisis para que invoque `evaluador_lotes.evaluar_lote(...)` enviando un callback a `st.progress()`. Mostrar alertas informativas si hubo fallos parciales o un error bloqueante si hubo fallo total del lote. Actualizar textos obsoletos en la interfaz.
- [x] **Hecho cuando:** `app.py` funcione estrictamente como capa UI sin lógica pesada de IA ni guardado directo, y el flujo visual de análisis funcione de forma reactiva e idéntica para el usuario.

---

## Tarea 9: Tests unitarios para endpoints desacoplados de `api.py` (TDD)
- **RF:** RF-3, RF-4, RF-10
- **Descripción:** Crear el archivo `tests/test_api.py` utilizando `fastapi.testclient.TestClient` para validar:
  1. GET `/api/kpis`: Lectura exitosa desde Supabase con reconstrucción de `{"aprobados": [...], "descartados": [...]}` e inyección de `copy_final`.
  2. GET `/api/kpis`: Fallback transparente a `resultados_kpis.json` cuando Supabase no está configurado o falla.
  3. GET `/api/kpis`: Contrato inmutable: verificar que ante base o archivo vacío NUNCA retorne `[]`, sino `{"aprobados": [], "descartados": []}` con código HTTP 200.
  4. GET `/api/reporte-semanal`: Lectura desde Supabase o fallback al archivo más reciente en `reportes/` (HTTP 200), y retorno de HTTP 404 estructurado si no hay reportes.
  5. Configuración de CORS permitiendo orígenes parametrizables.
- [x] **Hecho cuando:** El archivo `tests/test_api.py` exista y exponga los fallos de contrato y desacoplamiento del `api.py` actual.

---

## Tarea 10: Implementar desacoplamiento, persistencia en BD y consistencia en `api.py`
- **RF:** RF-3, RF-4
- **Descripción:** Añadir funciones de consulta de lotes y reportes en `base_datos.py` (`obtener_lote_kpis_supabase` y `obtener_ultimo_reporte_semanal_supabase`). Refactorizar `api.py` para consumir prioritariamente Supabase, implementar los fallbacks locales transparentes, garantizar la estructura canónica en `/api/kpis`, manejar códigos HTTP REST estándar (200, 404, 500) y configurar CORS mediante variable de entorno.
- [x] **Hecho cuando:** Todas las pruebas de `tests/test_api.py` pasen al 100% en verde y la suite completa de pruebas del proyecto (`pytest`) termine en verde sin fallos.
