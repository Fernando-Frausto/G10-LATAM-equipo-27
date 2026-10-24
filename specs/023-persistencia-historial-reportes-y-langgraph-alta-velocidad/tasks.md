# Tareas de Implementación — Spec 023: Persistencia en Historial de Reportes Semanales y LangGraph Checkpointer en Supabase Enoc con Garantía de Alta Velocidad

## [x] T1: Fase Red TDD en `tests/test_unificacion_motor_ia.py` (~20 min)
- **Rol:** `@implementer`
- **Archivos involucrados:**
  - `tests/test_unificacion_motor_ia.py`
- **Requerimientos Funcionales:** `RF-01`, `RF-02`, `RF-03`, `RF-04`, `RF-05`, `RF-06`
- **Descripción:**
  1. Diseñar e implementar pruebas unitarias y de integración en `tests/test_unificacion_motor_ia.py` para blindar los requerimientos de la Spec 023:
     - **Normalización de Registro para `historial_reportes_semanales`:** Verificar la construcción canónica del diccionario de 12 campos canónicos (`id_mensaje` normalizado a `str`, autor, semana, fechas ISO UTC, `rutas_activas` como lista de canales, estado `'publicado'`, `contenido_original` JSON, `copys_generados` JSON indexado por canal, y `cw_modelo_ia` resuelto mediante catálogo).
     - **Replicación Asíncrona en Publicación Individual:** Simular una publicación exitosa en `/api/v1/mototradis/publish-channel` (`estado_canal = 'enviado'`) y verificar que se despache en segundo plano la tarea asíncrona hacia Supabase sin retrasar la respuesta interactiva HTTP (< 100 ms de sobrecarga interna).
     - **Replicación Asíncrona en Aprobación Global HITL:** Simular una decisión de aprobación en `/api/v1/mototradis/hitl-decision` (`decision = 'aprobar'`) y validar que, si al menos un canal fue exitoso, se despache la replicación consolidada con `rutas_activas` exactas y copys aprobados por el humano (Soberanía Humana).
     - **Checkpointer Resiliente y Mitigación de Prepared Statements:** Verificar que `obtener_checkpointer_resiliente()` configure Session Mode (puerto `:5432`) o desactive sentencias preparadas automáticas con `prepare_threshold=None` en `psycopg 3`, y conmute transparentemente a `MemorySaver` con `logger.warning` ante desconexión o fallo simulado de red.
     - **Resiliencia ante Fallos en Segundo Plano:** Simular que la tarea asíncrona de inserción remota en Supabase falla por timeout o error de red, comprobando que se capture con `logger.warning`, se conserve el estado pendiente en SQLite local y la respuesta al usuario permanezca exitosa de inmediato.
  2. Ejecutar `pytest tests/test_unificacion_motor_ia.py -k spec023` y verificar que las nuevas pruebas fallen de forma controlada y documentada (Fase Red TDD).
- **Hecho cuando:** Las pruebas de la Spec 023 están escritas en `tests/test_unificacion_motor_ia.py` y fallan de manera controlada y demostrada en la ejecución de `pytest`.

---

## [x] T2: Fábrica de Checkpointer Resiliente y Mitigación de Prepared Statements en `puente_motor_ia.py` (~20 min)
- **Rol:** `@implementer`
- **Archivos involucrados:**
  - `puente_motor_ia.py`
- **Requerimientos Funcionales:** `RF-03`, `RF-04`, `RF-06`
- **Descripción:**
  1. Implementar la función de utilidad `resolver_url_session_mode(url: str | None = None) -> str | None` en `puente_motor_ia.py` para convertir URLs que utilicen el puerto `:6543` (Transaction Pooler) al puerto `:5432` (Session Mode Pooler de Supabase Enoc), garantizando aislamiento de sesión para conexiones de LangGraph.
  2. Refactorizar `obtener_checkpointer_resiliente()` en `puente_motor_ia.py` para:
     - Resolver la URL en Session Mode `:5432`.
     - Instanciar la conexión o `PostgresSaver` configurando explícitamente `prepare_threshold=None` en el driver `psycopg 3`, suprimiendo sentencias preparadas automáticas y previniendo la excepción `psycopg.errors.DuplicatePreparedStatement: prepared statement "_pg3_0" already exists`.
     - Envolver la inicialización y el método `setup()` en bloques `try...except Exception as exc:`, registrando una advertencia estructurada (`logger.warning`) y conmutando de forma inmediata y automática a `MemorySaver()` sin colapsar el proceso.
  3. Ejecutar `pytest tests/test_unificacion_motor_ia.py -k test_spec023_checkpointer` y verificar que pase a verde.
- **Hecho cuando:** `obtener_checkpointer_resiliente()` se conecta a Supabase Enoc en Session Mode (:5432) con `prepare_threshold=None`, conmuta a `MemorySaver` ante fallos de conexión y sus tests específicos pasan a verde.

---

## [x] T3: Persistencia Desacoplada en Segundo Plano para Publicación Individual en `puente_motor_ia.py` (~20 min)
- **Rol:** `@implementer`
- **Archivos involucrados:**
  - `puente_motor_ia.py`
- **Requerimientos Funcionales:** `RF-01`, `RF-05`, `RF-06`
- **Descripción:**
  1. Implementar `construir_registro_historial_reporte(...)` en `puente_motor_ia.py` normalizando con exactitud los 12 campos canónicos de la tabla `public.historial_reportes_semanales` (`id_mensaje` siempre como `str`, autor, semana, fechas ISO UTC, `rutas_activas` como lista de canales, estado `'publicado'`, `contenido_original` JSON, `copys_generados` JSON indexado por canal, y `cw_modelo_ia` resuelto mediante `resolver_modelo_canal`).
  2. Implementar `replicar_historial_reportes_semanales_supabase(registro: dict) -> bool` y el despachador asíncrono no bloqueante `despachar_replicacion_historial_reportes(registro: dict)` utilizando `asyncio.create_task(asyncio.to_thread(...))` (o ejecutor en hilo no bloqueante como respaldo).
  3. Integrar la invocación desacoplada en `api_mototradis_publish_channel`: tras registrar síncronamente en SQLite en < 100 ms, si `res.get("ok") and res.get("estado_canal") == "enviado"`, disparar la replicación asíncrona a Supabase sin añadir latencia a la respuesta HTTP interactiva.
  4. Ejecutar `pytest tests/test_unificacion_motor_ia.py -k "test_spec023_normalizacion or test_spec023_publish_channel"` y comprobar que pasen a verde.
- **Hecho cuando:** La publicación individual de un canal exitoso persiste en SQLite local en < 100 ms, despacha en segundo plano la réplica a `historial_reportes_semanales` y sus pruebas pasan a verde.

---

## [x] T4: Persistencia Desacoplada en Segundo Plano para Aprobación Global HITL y Purga de Hilos en `puente_motor_ia.py` (~20 min)
- **Rol:** `@implementer`
- **Archivos involucrados:**
  - `puente_motor_ia.py`
- **Requerimientos Funcionales:** `RF-02`, `RF-04`, `RF-05`, `RF-06`
- **Descripción:**
  1. Actualizar `api_mototradis_hitl_decision` en `puente_motor_ia.py` para que, ante `decision == "aprobar"`, una vez completado el despacho interactivo y la persistencia síncrona en SQLite en < 100 ms:
     - Filtre los canales con `estado_canal == "enviado"`.
     - Si hay al menos un canal enviado con éxito, construya el registro histórico consolidado conteniendo las `rutas_activas` exitosas y los copys finales editados por el operador (Soberanía Humana).
     - Despache la tarea en segundo plano vía `despachar_replicacion_historial_reportes(...)`.
  2. Asegurar que ante `decision == "desaprobar"`, se ejecute la purga del hilo en el checkpointer (`thread_id = f"sesion_{id_msg}"`) y la actualización del estado local en SQLite sin invocar la replicación a `historial_reportes_semanales`.
  3. Ejecutar `pytest tests/test_unificacion_motor_ia.py -k test_spec023_hitl` y comprobar que pase a verde.
- **Hecho cuando:** La aprobación HITL multicanal despacha en segundo plano la inserción consolidada en `historial_reportes_semanales` cuando hay envíos exitosos, la desaprobación purga el hilo en el checkpointer y los tests pasan a verde.

---

## [x] T5: Resiliencia de Red, Manejo Defensivo y Trazabilidad en SQLite Local (~20 min)
- **Rol:** `@implementer`
- **Archivos involucrados:**
  - `puente_motor_ia.py`
- **Requerimientos Funcionales:** `RF-04`, `RF-05`, `RF-06`
- **Descripción:**
  1. Reforzar el manejo de errores en `replicar_historial_reportes_semanales_supabase`: ante fallos de conexión WAN, timeout o autenticación en Supabase Enoc, capturar la excepción defensivamente con `logger.warning(...)`.
  2. Implementar la marca local en SQLite: actualizar el registro en `contenidos_generados` o tabla auxiliar de auditoría con `sync_supabase = 'pendiente'` para habilitar reconciliación diferida sin degradar la experiencia de usuario.
  3. Garantizar que todos los endpoints GET de lectura continúen respondiendo en < 2 ms desde SQLite local y memoria caché, prohibiendo cualquier consulta de red remota en la ruta crítica.
  4. Ejecutar `pytest tests/test_unificacion_motor_ia.py -k test_spec023_resiliencia` y verificar que pase a verde.
- **Hecho cuando:** Ante indisponibilidad transitoria de Supabase durante la tarea de fondo, se registra una advertencia en log, se conserva el estado pendiente local y la respuesta al usuario permanece inmediata y exitosa.

---

## [x] T6: Fase Refactor, Verificación Global de Regresión y Certificación de Inviolabilidad (~20 min)
- **Rol:** `@implementer`
- **Archivos involucrados:**
  - `tests/test_unificacion_motor_ia.py`
  - `puente_motor_ia.py`
  - `frontend/`
- **Requerimientos Funcionales:** `RF-01`, `RF-02`, `RF-03`, `RF-04`, `RF-05`, `RF-06`
- **Descripción:**
  1. Revisar y optimizar el código implementado en `puente_motor_ia.py`, verificando tipado estático, comentarios, docstrings y limpieza de imports.
  2. Ejecutar la suite completa de pruebas unitarias e integración de backend con `pytest tests/test_unificacion_motor_ia.py`, comprobando que el 100% de los tests (114+ tests) pasen en verde.
  3. Ejecutar `npm --prefix frontend run build` y certificar compilación limpia de frontend con código de salida 0.
  4. Auditar `git status` para certificar la inmutabilidad de los 17 archivos protegidos de la raíz (`base_datos.py`, `reporte_semanal.py`, `procesamiento.py`, `api.py`), `backend/`, `motor-ia/` y `src/`.
- **Hecho cuando:** El 100% de la suite de `pytest` (114+ tests) pasa en verde, el build de frontend finaliza con código 0 y `git status` certifica la inalterabilidad de todos los archivos protegidos.
