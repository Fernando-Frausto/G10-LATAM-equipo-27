# Tareas de Implementación — Spec 022: Migración de Interacciones a Supabase Enoc y Unificación de Conexiones

## [x] T1: Fase Red TDD en `tests/test_unificacion_motor_ia.py` (~20 min)
- **Rol:** `@implementer`
- **Archivos involucrados:**
  - `tests/test_unificacion_motor_ia.py`
- **Requerimientos Funcionales:** `RF-01`, `RF-02`, `RF-03`, `RF-04`, `RF-05`
- **Descripción:**
  1. Diseñar e implementar pruebas unitarias y de integración en `tests/test_unificacion_motor_ia.py` para blindar los requerimientos de la Spec 022 acotada:
     - **Validación de Estructura de `interacciones` en Enoc:** Verificar la creación de la tabla `public.interacciones` con el DDL canónico de 11 columnas e índice UNIQUE sobre `hash`.
     - **Verificación de Integridad de 204 Registros:** Validar la lógica de pre-flight (204 en Tania) y post-flight (204 en Enoc con 0 diferencias en hashes).
     - **Validación de Idempotencia:** Validar que la transferencia con `ON CONFLICT (hash) DO NOTHING` soporte ejecuciones repetidas sin generar duplicados.
     - **Sincronización de Secuencia Autoincremental:** Validar la fórmula `SELECT setval('interacciones_id_seq', COALESCE((SELECT MAX(id) FROM interacciones), 1), (SELECT COUNT(*) > 0 FROM interacciones))`.
     - **Salvaguarda de Inicialización de Cadenas de Conexión:** Validar que si `DATABASE_URL` contiene el host o ID de proyecto de Tania (`ietgilhtccvqlqglqazf`), el sistema conmute transparentemente hacia `SUPABASE_DB_URL` de Enoc con advertencia en logs.
  2. Ejecutar `pytest tests/test_unificacion_motor_ia.py` y verificar que las nuevas pruebas fallen de forma controlada y esperada debido a la ausencia inicial de la lógica en `puente_motor_ia.py` y del script de migración (Fase Red TDD).
- **Hecho cuando:** Las pruebas de la Spec 022 están escritas en `tests/test_unificacion_motor_ia.py` y fallan de manera controlada y demostrada en la ejecución de `pytest`.

---

## [x] T2: Script de Migración Idempotente y Ejecución Segura en `scripts/migrar_interacciones_enoc.py` (~20 min)
- **Rol:** `@implementer`
- **Archivos involucrados:**
  - `scripts/migrar_interacciones_enoc.py`
  - `.env`
- **Requerimientos Funcionales:** `RF-01`, `RF-02`, `RF-03`, `RF-05`
- **Descripción:**
  1. Crear el script `scripts/migrar_interacciones_enoc.py` fuera de los 17 archivos protegidos, consumiendo exclusivamente cadenas de conexión desde `os.environ` (prohibiendo secretos en código duro bajo la Regla 4 de la Constitución).
  2. Implementar la creación canónica de la tabla `public.interacciones` (11 columnas) e índice único sobre `hash` en la base de datos de Enoc (`swdoucawdasxmnomlcfu`).
  3. Ejecutar el protocolo de pre-vuelo (Pre-Flight Check): validar que la tabla de origen en Tania contenga exactamente 204 registros (`SELECT COUNT(*) FROM interacciones` == 204) y recolectar el conjunto total de sus hashes.
  4. Realizar la transferencia de datos por lotes de forma idempotente utilizando `ON CONFLICT (hash) DO NOTHING` preservando IDs originales, autor, canal, texto, fechas y estados.
  5. Ejecutar el protocolo de post-vuelo (Post-Flight Check): validar que en Enoc existan exactamente 204 registros y que la diferencia de conjuntos entre hashes de origen y destino sea estrictamente cero (`set(hashes_origen) == set(hashes_destino)`).
  6. Sincronizar defensivamente la secuencia autoincremental en Enoc:
     ```sql
     SELECT setval('interacciones_id_seq', COALESCE((SELECT MAX(id) FROM interacciones), 1), (SELECT COUNT(*) > 0 FROM interacciones));
     ```
  7. Ejecutar el script contra las bases de datos de Supabase asegurando salida exitosa y 100% de paridad.
  8. Conmutar de manera segura el archivo `.env`: asignar `DATABASE_URL` al endpoint de Enoc (Transaction Pooler puerto 6543) y preservar `TANIA_DATABASE_URL` como respaldo histórico.
- **Hecho cuando:** La tabla `interacciones` en Enoc contiene los 204 registros íntegros validados por post-flight, la secuencia `interacciones_id_seq` está sincronizada al ID máximo y `.env` apunta `DATABASE_URL` al Transaction Pooler de Enoc.

---

## [x] T3: Salvaguarda de Conexión y Resiliencia en `puente_motor_ia.py` (~20 min)
- **Rol:** `@implementer`
- **Archivos involucrados:**
  - `puente_motor_ia.py`
- **Requerimientos Funcionales:** `RF-03`, `RF-04`, `RF-05`
- **Descripción:**
  1. Implementar la salvaguarda en la inicialización de `puente_motor_ia.py` para comprobar si `DATABASE_URL` contiene la referencia obsoleta a Tania (`ietgilhtccvqlqglqazf`); de ser así, conmutar transparentemente a `SUPABASE_DB_URL` (Enoc) y registrar advertencia en logs (`logger.warning`).
  2. Verificar que las rutinas de sincronización y replicación en background hacia `interacciones` operen sin fisuras apuntando a la cuenta unificada de Enoc.
  3. Ejecutar `pytest tests/test_unificacion_motor_ia.py` y verificar que las pruebas pasen a verde (Fase Green TDD).
- **Hecho cuando:** `puente_motor_ia.py` conmuta automáticamente ante URLs obsoletas de Tania, opera con Supabase Enoc y las pruebas de `test_unificacion_motor_ia.py` pasan 100% en verde.

---

## [x] T4: Fase Refactor & Verificación Global de Regresión (~20 min)
- **Rol:** `@implementer`
- **Archivos involucrados:**
  - `tests/test_unificacion_motor_ia.py`
  - `puente_motor_ia.py`
  - `scripts/migrar_interacciones_enoc.py`
  - `frontend/`
- **Requerimientos Funcionales:** `RF-01`, `RF-02`, `RF-03`, `RF-04`, `RF-05`
- **Descripción:**
  1. Revisar y optimizar el código implementado, verificando typing, manejo defensivo de excepciones, documentación de funciones y limpieza de logs.
  2. Ejecutar la suite completa de pruebas unitarias e integración de backend con `pytest tests/test_unificacion_motor_ia.py`, verificando que la totalidad de los tests (106+ tests) pasen en verde.
  3. Ejecutar `npm --prefix frontend run build` y comprobar compilación limpia con código de salida 0.
  4. Realizar auditoría estricta de `git status` para certificar la inviolabilidad absoluta de los 17 archivos protegidos de la raíz (`base_datos.py`, `reporte_semanal.py`, `procesamiento.py`, `api.py`), `backend/`, `motor-ia/` y `src/`.
- **Hecho cuando:** La suite completa de `pytest` pasa al 100% en verde, el build de frontend finaliza con código 0 y `git status` confirma la inviolabilidad de los 17 archivos protegidos.
