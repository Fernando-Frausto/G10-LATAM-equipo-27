# Especificación 005: Unificación Beta mediante Puente Adaptador No Invasivo (`puente_motor_ia.py`)

## 1. Contexto y Propósito

### ¿Qué se busca lograr?
Unificar de manera **100% no invasiva** en la rama `unificacion-beta` el ecosistema de interfaz y servicios desarrollado en `origin/main` (`frontend/`, `backend/`, `motor-ia/` y `netlify.toml`) con el backend productivo en la raíz del repositorio conectado a las bases de datos reales en Supabase (Ingesta de Discord y Bandeja HITL de Copywriting).

Toda la integración entre las mejoras de la rama `feature/ia-resultados-supabase` y el ecosistema de `origin/main` se realizará exclusivamente a través de un módulo adaptador nuevo en la raíz llamado `puente_motor_ia.py` (y su suite de pruebas `tests/test_unificacion_motor_ia.py`), garantizando **cero modificaciones** a los archivos de `frontend/`, `backend/`, `motor-ia/`, `netlify.toml` y **cero modificaciones** a los archivos existentes de la raíz.

### ¿Por qué es necesario?
1. **Inmutabilidad Total y Cero Conflictos de Merge:** Al no tocar ni una sola línea de `frontend/`, `backend/` ni `motor-ia/` respecto a `origin/main`, ni alterar ningún archivo existente de nuestra raíz respecto a `feature/ia-resultados-supabase`, se elimina por completo el riesgo de conflictos de git o regresiones en el código de cualquier integrante del equipo.
2. **Conexión en Vivo a Supabase para el Dashboard de React:** Originalmente, `motor-ia/base_datos.py` solo lee de SQLite local (`motor-ia/communitylab.db`). Mediante la interceptación en memoria en `puente_motor_ia.py`, el servicio FastAPI de `motor-ia` (en el puerto `8002`) alimentará automáticamente a `backend/` y `frontend/` con las interacciones reales de `interacciones` y las evaluaciones/curadurías reales de `lotes_ia_kpis` en Supabase, manteniendo sincronizada la caché SQLite local y el fallback transparente.
3. **Homologación de Modelos e Ingesta Automática de Canales en Memoria:** `puente_motor_ia.py` inyecta en memoria el contrato completo `FormatoSalida` (con `sentiment_score` y `tema`) y las variables `GEMINI_MODEL` / `GEMMA_MODEL` en los módulos Gemini y Gemma de `motor-ia/`, además de conectar la sincronización de Discord (`/api/discord/sync`) con la autodetección de canales (`detectar_canales`) de `armar_json_bot_python.py`.

---

## 2. Requerimientos Funcionales (Formato EARS)

### RF-01: Incorporación Íntegra e Inmutabilidad Total de `frontend/`, `backend/`, `motor-ia/` y Archivos de Raíz
- **QUÉ:**
  - **CUANDO** se realice la integración de la rama `origin/main` hacia `unificacion-beta` (rama autorizada explícitamente por el usuario como excepción a la convención `feature/` de la Regla 1, respetando la prohibición de no hacer push directo a `main`), **EL SISTEMA DEBERÁ** incorporar íntegramente los directorios `frontend/`, `backend/`, `motor-ia/` y el archivo `netlify.toml` exactamente como existen en `origin/main`.
  - **EN TODO MOMENTO**, **EL SISTEMA DEBERÁ** mantener sin ninguna modificación todos los archivos dentro de `frontend/`, `backend/`, `motor-ia/` y `netlify.toml` (de modo que `git diff origin/main -- frontend backend motor-ia netlify.toml` sea vacío) y preservar intactos al 100% todos los archivos existentes en la raíz del proyecto (`base_datos.py`, `evaluador_lotes.py`, `prompts_ia.py`, `app.py`, `api.py`, `bot_lote.py`, `armar_json_bot_python.py`, `reporte_semanal.py`, `oci_uploader.py`, `requirements.txt` y los 48 tests existentes en `tests/`).
- **POR QUÉ:**
  - Para garantizar una unificación limpia, auditable y libre de colisiones entre el trabajo de `origin/main` y el pipeline de Supabase en la raíz.

### RF-02: Puente en Vivo de Interacciones y KPIs desde Supabase en `puente_motor_ia.py`
- **QUÉ:**
  - **CUANDO** se cargue el servicio `motor-ia` a través de `puente_motor_ia.py` (exponiendo la aplicación FastAPI `app` lista para ejecutarse en el puerto `8002`), **EL SISTEMA DEBERÁ** interceptar y envolver en memoria las funciones de interacciones de `motor-ia/base_datos.py` (`listar_interacciones`, `obtener_interaccion`, `contar_interacciones`, `actualizar_curaduria`, `actualizar_etapa_flujo` y `guardar_evaluacion`).
  - **CUANDO** las variables de entorno `DATABASE_URL` y/o `SUPABASE_DB_URL` estén configuradas, **EL SISTEMA DEBERÁ** consultar los mensajes reales de la tabla `interacciones` (Supabase de Ingesta, excluyendo bots, webhooks, discriminadores `#0000` y `Spidey Boy#0000`) y cruzarlos en memoria por `interacciones.id == lotes_ia_kpis.id_mensaje` con las evaluaciones de la tabla `lotes_ia_kpis` (Supabase de Copywriting: `relevancia`, `sentimiento`, `temas_clave`, `segmento`, `razonamiento`, `decision_ia`, `estado_revision`, `analizado_en`).
  - **CUANDO** una interacción se encuentre evaluada en `lotes_ia_kpis`, **EL SISTEMA DEBERÁ** exponer `estado='analizado'` y transformar determinísticamente sus campos hacia el contrato esperado por `motor-ia/servicio_dashboard.py` y `motor-ia/api.py`:
    - `sentiment_score`: `0.85` cuando `sentimiento` sea `'Positivo'` o `'Negativo'`, `0.75` cuando sea `'Neutral'`, y `None` si no ha sido evaluado.
    - `tema`: una de las 7 categorías cerradas (`'EMPLEO'`, `'EDUCACION'`, `'IA'`, `'DESARROLLO'`, `'PLATAFORMA'`, `'COMUNIDAD'`, `'OTRO'`), inferida determinísticamente a partir de `temas_clave`, `canal` y `texto`.
    - `estado_curaduria`: `'curated'` si `estado_revision` es `'aprobado'` o `'procesado'`; `'discarded'` si es `'rechazado'` o `'desaprobado'`; y `'pending'` si es `'pendiente'`.
    - `etapa_flujo`: `'en_aprobacion'` si `estado_revision` es `'aprobado'`; `'en_redaccion'` si es `'procesado'`; y `'en_analisis'` si está en `lotes_ia_kpis` como `'pendiente'` o `'rechazado'`/`'desaprobado'`.
  - **SI** una interacción no tiene registro en `lotes_ia_kpis`, **EL SISTEMA DEBERÁ** conservar `estado='pendiente'`, `relevancia=None`, `sentimiento=None`, `sentiment_score=None`, `tema=None`, `estado_curaduria='pending'` y `etapa_flujo='ingesta'`.
  - **SI** `enviado_en` es `NULL` en `interacciones`, **EL SISTEMA DEBERÁ** usar `creado_en` como fallback para no interrumpir `motor-ia/servicio_dashboard.py`.
  - **CUANDO** se sincronicen interacciones desde Supabase o se invoquen mutaciones (`actualizar_curaduria`, `actualizar_etapa_flujo`, `guardar_evaluacion`), **EL SISTEMA DEBERÁ** sincronizar la caché SQLite local (`motor-ia/communitylab.db`) respetando las mutaciones locales y propagando las actualizaciones de curaduría/evaluación hacia `lotes_ia_kpis` en Supabase cuando exista conexión; **SI** no hay conexión a Supabase, **EL SISTEMA DEBERÁ** operar mediante fallback limpio sobre SQLite local.
- **POR QUÉ:**
  - Para que los endpoints `/api/community/messages`, `/api/community/dashboard`, `/api/community/analytics` y `/api/community/complaints` de `motor-ia/api.py` entreguen al Frontend de React los datos reales de Supabase sin modificar `motor-ia/base_datos.py` ni `motor-ia/api.py`.

### RF-03: Puente de Contenidos Curados para `/api/content` en `puente_motor_ia.py`
- **QUÉ:**
  - **CUANDO** se invoquen `listar_contenidos`, `obtener_contenido`, `contar_contenidos` o `actualizar_estado_contenido` a través de `puente_motor_ia.py` y exista conexión a Supabase (`SUPABASE_DB_URL` y/o `DATABASE_URL`), **EL SISTEMA DEBERÁ** sincronizar los registros de `lotes_ia_kpis` hacia la tabla `contenidos_generados` de la caché SQLite (`motor-ia/communitylab.db`) usando los estados válidos de `motor-ia/base_datos.py` (`'pendiente_revision'`, `'aprobado'`, `'rechazado'`, `'ajustes_solicitados'`):
    - `estado_revision == 'aprobado'` -> `'aprobado'`.
    - `estado_revision` en `('rechazado', 'desaprobado')` -> `'rechazado'`.
    - `estado_revision` en `('pendiente', 'procesado')` -> `'pendiente_revision'`.
  - **CUANDO** se sintetice un contenido desde `lotes_ia_kpis`, **EL SISTEMA DEBERÁ** poblar `id` (id de `lotes_ia_kpis`), `interaccion_id` (`id_mensaje`), `formato` y `plataforma` (`'discord'` / `'linkedin'` / `'x'`), `titulo` (derivado de `temas_clave`, `canal` y `autor`), `contenido` (`copy_final` si existe, o síntesis de `texto_original` + `razonamiento`), `llamada_accion`, `hashtags` (lista de strings extraída de `temas_clave`), `tono` (`'profesional'`), `estado`, `creado_en` y `actualizado_en` (`analizado_en`), `tipo_contenido` (`'publicacion'`), `observaciones_revision` (`razonamiento`), `version` (`1`), `estado_publicacion` (`'no_publicado'`), `publicado_en` (`None`), `source_channel_id`, `source_message_id` y `attachments` (`[]`).
  - **CUANDO** se actualice el estado de un contenido desde la UI (`actualizar_estado_contenido`), **EL SISTEMA DEBERÁ** preservar el cambio en SQLite local y reflejar el estado homologado (`'aprobado'`, `'rechazado'`, `'pendiente'`) en `lotes_ia_kpis` de Supabase si hay conexión disponible.
- **POR QUÉ:**
  - Para que la pantalla de Aprobaciones (`/api/content`) y los KPIs de contenido del Dashboard en React reflejen y gestionen las piezas reales de Supabase sin alterar `motor-ia/`, `backend/` ni `frontend/`.

### RF-04: Homologación en Memoria de Cerebros IA (`FormatoSalida`) y Autodetección de Canales de Discord en `puente_motor_ia.py`
- **QUÉ:**
  - **CUANDO** `puente_motor_ia.py` inicialice el entorno de `motor-ia`, **EL SISTEMA DEBERÁ** envolver/homologar en memoria los módulos `cerebro_ia_gemini_flash` y `cerebro_ia_gemma_4` de `motor-ia` para que su esquema `FormatoSalida` incluya obligatoriamente `sentiment_score` (`float`) y `tema` (`Literal["EMPLEO", "EDUCACION", "IA", "DESARROLLO", "PLATAFORMA", "COMUNIDAD", "OTRO"]`) además de `relevancia`, `sentimiento`, `temas_clave`, `segmento`, `razonamiento` y `decision_ia`, y para que lean `GEMINI_MODEL` (default `'gemini-3.5-flash-lite'`) y `GEMMA_MODEL` (default `'gemma-4-31b-it'`) con fallback secundario a `GOOGLE_MODEL` y saneamiento `.strip()`.
  - **CUANDO** se invoque la sincronización de Discord (`/api/discord/sync` / `recolectar_mensajes` de `motor_ia`), **EL SISTEMA DEBERÁ** interceptarla en memoria desde `puente_motor_ia.py` para delegar la extracción en `armar_json_bot_python.py` de la raíz (aprovechando la autodetección dinámica de canales `detectar_canales` y la persistencia en `interacciones` de Supabase) y sincronizar los mensajes recolectados hacia `motor-ia/base_datos.py`.
- **POR QUÉ:**
  - Para evitar errores `KeyError` al evaluar con Gemini o Gemma en `motor-ia/` y dotar al endpoint `/api/discord/sync` de autodetección de canales de Discord y persistencia en Supabase sin editar ningún archivo dentro de `motor-ia/`.

### RF-05: Suite de Pruebas Automatizadas TDD de Unificación e Inmutabilidad (`tests/test_unificacion_motor_ia.py`)
- **QUÉ:**
  - **CUANDO** se ejecute `pytest`, **EL SISTEMA DEBERÁ** validar mediante pruebas unitarias y de integración con mocks en `tests/test_unificacion_motor_ia.py`:
    1. La carga aislada de `puente_motor_ia.py` sin colisionar con `base_datos.py` ni `api.py` de la raíz.
    2. El puente de lectura y enriquecimiento de interacciones (`interacciones` + `lotes_ia_kpis`), mapeos deterministas (`sentiment_score`, las 7 categorías de `tema`, `estado_curaduria`, `etapa_flujo`, interacciones no evaluadas, fallback de `enviado_en` a `creado_en`) y fallback a SQLite local.
    3. El puente de contenidos (`listar_contenidos`, `contar_contenidos`, `actualizar_estado_contenido`) hacia `contenidos_generados` y su exposición en `/api/content`.
    4. La respuesta de los endpoints de `motor-ia/api.py` expuestos por `puente_motor_ia.app` (`/api/community/messages`, `/api/community/dashboard`, `/api/community/analytics`, `/api/content`) con la estructura esperada por el Frontend de React.
    5. La homologación en memoria de `FormatoSalida`, `GEMINI_MODEL` y `GEMMA_MODEL`, la delegación de ingesta de Discord con autodetección de canales, y la verificación de inmutabilidad de los archivos de `origin/main` y de la raíz.
  - **EN TODO MOMENTO**, **EL SISTEMA DEBERÁ** mantener en verde el 100% de las 48 pruebas existentes en `tests/`.
- **POR QUÉ:**
  - Para cumplir con las Reglas 3 (Retrocompatibilidad) y 6 (Diseño Test-First / TDD) de `docs/constitution.md`.

---

## 3. Restricciones y Cumplimiento Constitucional

1. **Rama de Trabajo (Regla 1):** Se trabaja en la rama `unificacion-beta` por instrucción explícita del usuario, respetando la inviolabilidad de `main`.
2. **Inmutabilidad Total de `origin/main` y Raíz (Reglas 2 y 3):** Cero modificaciones a `frontend/`, `backend/`, `motor-ia/`, `netlify.toml` y a los archivos existentes de la raíz. Solo se crean `puente_motor_ia.py`, `tests/test_unificacion_motor_ia.py` y la documentación en `specs/005-unificacion-beta/` (más actualización de `MEMORY.md`).
3. **Seguridad de Secretos (Regla 4):** Todas las credenciales y configuraciones (`DATABASE_URL`, `SUPABASE_DB_URL`, `GEMINI_MODEL`, `GEMMA_MODEL`, `GROQ_MODEL`) se consumen desde `os.environ`.
4. **Control de Dependencias (Regla 5):** Se utilizan únicamente las librerías ya declaradas en el entorno (`psycopg2-binary`, `fastapi`, `pydantic`, etc. ya presentes en `requirements.txt` de la raíz).
5. **TDD Estricto (Regla 6):** `tests/test_unificacion_motor_ia.py` se escribe primero (Fase Red) antes de implementar `puente_motor_ia.py` (Fase Green).

---

## 4. Criterios de Aceptación Globales

- [ ] `git diff origin/main -- frontend backend motor-ia netlify.toml` no arroja ninguna diferencia (inmutabilidad 100% de los archivos de `origin/main`).
- [ ] Ningún archivo productivo existente en la raíz (`base_datos.py`, `evaluador_lotes.py`, `prompts_ia.py`, `app.py`, `api.py`, `bot_lote.py`, `armar_json_bot_python.py`, `reporte_semanal.py`, `oci_uploader.py`) ha sido modificado respecto a `feature/ia-resultados-supabase`.
- [ ] `puente_motor_ia.py` expone la aplicación FastAPI (`app`) compatible con `uvicorn puente_motor_ia:app --port 8002` y conecta en memoria `motor-ia` con `interacciones` y `lotes_ia_kpis` de Supabase, con caché y fallback en SQLite local.
- [ ] `puente_motor_ia.py` homologa en memoria `FormatoSalida` (`sentiment_score`, `tema`) y `GEMINI_MODEL` / `GEMMA_MODEL` en los cerebros de `motor-ia`, e integra la autodetección de canales de Discord.
- [ ] La suite completa de `pytest` (las 48 pruebas existentes más las nuevas pruebas en `tests/test_unificacion_motor_ia.py`) pasa al 100% en verde.
