# Tareas de Implementación 005: Unificación Beta (`puente_motor_ia.py`)

> **Regla de Oro:** Máximo 10 tareas de ~20 minutos cada una. **CERO modificaciones** a `frontend/`, `backend/`, `motor-ia/`, `netlify.toml` y a los archivos existentes de la raíz. Diseño **Test-First (TDD)** obligatorio.

---

### Tarea 1: Incorporación Íntegra de `origin/main` (`frontend/`, `backend/`, `motor-ia/`, `netlify.toml`)
- **RF Asociado:** RF-01
- **Descripción:** Traer desde `origin/main` a la rama `unificacion-beta` los directorios `frontend/`, `backend/`, `motor-ia/` y el archivo `netlify.toml` mediante `git checkout origin/main -- frontend backend motor-ia netlify.toml`, sin modificar ningún archivo existente en la raíz del proyecto.
- [x] **Hecho cuando:** Existen `frontend/`, `backend/`, `motor-ia/` y `netlify.toml` en el árbol de trabajo, `git diff origin/main -- frontend backend motor-ia netlify.toml` está completamente vacío, y las 48 pruebas existentes en `tests/` siguen pasando al 100%.

---

### Tarea 2: Creación de la Suite de Pruebas TDD en Fase Red (`tests/test_unificacion_motor_ia.py`)
- **RF Asociado:** RF-02, RF-03, RF-04, RF-05
- **Descripción:** Escribir la suite de pruebas unitarias y de integración con mocks en `tests/test_unificacion_motor_ia.py` que valide:
  1. Carga aislada de `puente_motor_ia` sin colisionar con `base_datos` ni `api` de la raíz.
  2. Lectura en vivo desde mocks de Supabase (`interacciones` y `lotes_ia_kpis`), exclusión de bots/webhooks, mapeo exacto de `sentiment_score` (`0.85`, `0.75`, `None`), las 7 categorías cerradas de `tema`, `estado_curaduria`, `etapa_flujo`, interacciones no evaluadas (`estado='pendiente'`), fallback de `enviado_en` nulo a `creado_en` y fallback limpio a SQLite local.
  3. Sincronización de `lotes_ia_kpis` hacia `contenidos_generados` (`listar_contenidos`, `contar_contenidos`, `actualizar_estado_contenido`) con los estados `'pendiente_revision'`, `'aprobado'` y `'rechazado'`.
  4. Respuestas de los endpoints de `puente_motor_ia.app` (`/api/community/messages`, `/api/community/dashboard`, `/api/community/analytics`, `/api/content`) con la estructura esperada por React.
  5. Homologación en memoria de `FormatoSalida` (`sentiment_score`, `tema`) y lectura de `GEMINI_MODEL` (`'gemini-3.5-flash-lite'`) y `GEMMA_MODEL` (`'gemma-4-31b-it'`) con `.strip()`, además de la interceptación de sincronización de Discord.
- [x] **Hecho cuando:** El archivo `tests/test_unificacion_motor_ia.py` existe y al ejecutar `pytest tests/test_unificacion_motor_ia.py` falla de forma controlada (Fase Red) por la ausencia de `puente_motor_ia.py`.

---

### Tarea 3: Implementación del Cargador Aislado y Puente de Interacciones Supabase <-> SQLite en `puente_motor_ia.py`
- **RF Asociado:** RF-01, RF-02
- **Descripción:** Crear `puente_motor_ia.py` en la raíz con el cargador aislado de módulos de `motor-ia/` (protegiendo `sys.modules` para no colisionar con la raíz) e implementar los wrappers en memoria para `listar_interacciones`, `obtener_interaccion`, `contar_interacciones`, `actualizar_curaduria`, `actualizar_etapa_flujo` y `guardar_evaluacion`, incluyendo la consulta a `interacciones` (`DATABASE_URL`) y `lotes_ia_kpis` (`SUPABASE_DB_URL`), el filtrado antibots, todos los mapeos deterministas aprobados por QA y la sincronización/fallback en `motor-ia/communitylab.db`.
- [x] **Hecho cuando:** Las pruebas de carga aislada y del puente de interacciones/dashboard/analytics en `tests/test_unificacion_motor_ia.py` pasan en verde.

---

### Tarea 4: Implementación del Puente de Contenidos Curados (`/api/content`) en `puente_motor_ia.py`
- **RF Asociado:** RF-03
- **Descripción:** Añadir en `puente_motor_ia.py` la sincronización de registros de `lotes_ia_kpis` hacia la tabla `contenidos_generados` de `motor-ia/communitylab.db` y los wrappers en memoria para `listar_contenidos`, `obtener_contenido`, `contar_contenidos` y `actualizar_estado_contenido`, mapeando los estados (`'pendiente_revision'`, `'aprobado'`, `'rechazado'`) y sintetizando todos los campos requeridos por `/api/content` y `servicio_dashboard.py`.
- [x] **Hecho cuando:** Las pruebas de `listar_contenidos`, `contar_contenidos`, `actualizar_estado_contenido` y del endpoint `/api/content` en `tests/test_unificacion_motor_ia.py` pasan en verde.

---

### Tarea 5: Homologación en Memoria de Cerebros IA (`FormatoSalida`) e Ingesta de Discord en `puente_motor_ia.py`
- **RF Asociado:** RF-04
- **Descripción:** Completar `puente_motor_ia.py` inyectando en memoria el esquema `FormatoSalida` completo (`sentiment_score` y `tema`) y la lectura de `GEMINI_MODEL` / `GEMMA_MODEL` con `.strip()` en `cerebro_ia_gemini_flash` y `cerebro_ia_gemma_4` de `motor-ia`, e interceptando `recolectar_mensajes` para delegar en `armar_json_bot_python.py` de la raíz (con autodetección de canales y persistencia en Supabase).
- [x] **Hecho cuando:** El 100% de las pruebas en `tests/test_unificacion_motor_ia.py` pasa en verde (Fase Green completa).

---

### Tarea 6: Verificación Integral de Regresión, Inmutabilidad y Actualización de `MEMORY.md`
- **RF Asociado:** RF-01, RF-05
- **Descripción:** Ejecutar la suite completa de `pytest` (las 48 pruebas previas + `tests/test_unificacion_motor_ia.py`), verificar con `git diff` que ningún archivo de `frontend/`, `backend/`, `motor-ia/`, `netlify.toml` ni de la raíz existente haya sido modificado, y actualizar `MEMORY.md` documentando la arquitectura de unificación mediante `puente_motor_ia.py`.
- [x] **Hecho cuando:** `pytest` reporta el 100% de los tests en verde, `git diff origin/main -- frontend backend motor-ia netlify.toml` es vacío, `git diff feature/ia-resultados-supabase` solo muestra los archivos nuevos autorizados y `MEMORY.md` está actualizado.
