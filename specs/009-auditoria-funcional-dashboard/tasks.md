# Tareas de Implementación: Spec 009
## Auditoría y Consistencia Funcional de la Pestaña de Dashboard

---

### [x] Tarea 1: Fase Red TDD (Prueba de reconciliación de audiencia y fallback de autor)
- **RF Asociado:** RF-03, RF-06
- **Estimación:** ~20 minutos
- **Archivos a modificar:** `tests/test_unificacion_motor_ia.py`
- **Descripción:**
  1. Diseñar e incorporar en `tests/test_unificacion_motor_ia.py` la prueba automatizada `test_dashboard_total_audience_reconciliacion_y_fallback_autor`.
  2. Simular un conjunto de interacciones en Supabase donde los usuarios humanos tengan `autor` válido pero `author_id` nulo o vacío (`None` / `""`), además de interacciones provenientes de bots y webhooks (`"cloudedtech community bot"`, `"Spidey Boy#0000"`).
  3. Consultar el endpoint `GET /api/community/dashboard` utilizando `TestClient` sobre la app de FastAPI en `puente_motor_ia`.
  4. Afirmar que `total_audience` sea exactamente igual a 10 (audiencia humana real) y que las cuentas de bot queden excluidas.
  5. Ejecutar `pytest tests/test_unificacion_motor_ia.py -k test_dashboard_total_audience_reconciliacion_y_fallback_autor` para certificar la **Fase Red** (fallo esperado previo a la implementación del adaptador).
- [x] **Hecho cuando:**
  La nueva prueba automatizada esté implementada, falle de manera controlada al comprobar que `total_audience` reporta 0 en lugar de 10, y valide con precisión el comportamiento esperado para la reconciliación de autores y la exclusión de bots.

---

### [x] Tarea 2: Fase Green Backend (Fallback de autor y filtro antibot en puente)
- **RF Asociado:** RF-03, RF-06
- **Estimación:** ~20 minutos
- **Archivos a modificar:** `puente_motor_ia.py`
- **Descripción:**
  1. En la función `_sincronizar_supabase_a_sqlite` de `puente_motor_ia.py`:
     - Asegurar el fallback en la tupla de inserción SQLite para la columna `author_id`: `str(raw.get("author_id") or raw.get("autor") or "")`.
  2. En la función `listar_interacciones_puente` de `puente_motor_ia.py`:
     - Asegurar que en los registros procesados se garantice `if not it.get("author_id") and it.get("autor"): it["author_id"] = str(it["autor"])`.
     - Preservar el filtro estricto antibot `_es_cuenta_bot(it)` para que los bots queden descartados antes de computar `servicio_dashboard.autores_unicos`.
  3. Ejecutar la prueba creada en la Tarea 1 para validar la **Fase Green** (paso a verde).
- [x] **Hecho cuando:**
  La prueba unitaria de la Tarea 1 pase a verde (`PASSED`), el endpoint `/api/community/dashboard` retorne `total_audience == 10` y se mantenga la inmutabilidad de los módulos de `motor-ia/` y `backend/`.

---

### [x] Tarea 3: Integración de `<FeaturedStories />` en `Dashboard.tsx` y botones interactivos en `FeaturedStories.tsx`
- **RF Asociado:** RF-01, RF-02
- **Estimación:** ~20 minutos
- **Archivos a modificar:** `frontend/src/pages/Dashboard.tsx`, `frontend/src/components/FeaturedStories.tsx`
- **Descripción:**
  1. En `frontend/src/pages/Dashboard.tsx`:
     - Importar `FeaturedStories` desde `../components/FeaturedStories`.
     - Reemplazar el contenedor estático provisional con el texto `"Esta sección se conectará con los mensajes destacados..."` por `<FeaturedStories key={analyticsVersion} />`.
     - Verificar que el botón "Actualizar datos" mantenga su animación en `RefreshCw`, estado `"Actualizando..."` e incremente `analyticsVersion`, sincronizando el remontado reactivo de las historias con las tarjetas y gráficos.
  2. En `frontend/src/components/FeaturedStories.tsx`:
     - Importar `useNavigate` de `react-router-dom`.
     - Deshabilitar preventivamente los botones de navegación anterior y siguiente si `stories.length <= 1` con `disabled={stories.length <= 1}` y clases `disabled:opacity-50 disabled:cursor-not-allowed`.
     - En el botón "Ver mensaje": asignar navegación a `/messages` pasando la interacción en el estado de navegación.
     - En el botón "Generar publicación": asignar navegación hacia `/approvals`.
- [x] **Hecho cuando:**
  El bloque provisional estático quede erradicado, `<FeaturedStories key={analyticsVersion} />` se visualice e interactúe de forma fluida, los botones de navegación se deshabiliten ante una sola historia, los botones de acción naveguen correctamente a `/messages` y `/approvals`, y el botón "Actualizar datos" refresque simultáneamente toda la pantalla.

---

### [x] Tarea 4: Formateo defensivo (Null Safety) y variaciones neutras en los 6 KPIs de `Dashboard.tsx`
- **RF Asociado:** RF-04
- **Estimación:** ~20 minutos
- **Archivos a modificar:** `frontend/src/pages/Dashboard.tsx`
- **Descripción:**
  1. Aplicar coalescencia nula defensiva (`optional chaining ?.toLocaleString("es-CO") ?? "0"`) en el valor de las 6 tarjetas de KPIs:
     - `messages_processed?.toLocaleString("es-CO") ?? "0"`
     - `total_audience?.toLocaleString("es-CO") ?? "0"`
     - `positive_sentiment != null ? `${dashboardData.positive_sentiment}%` : "0%"`
     - `topics_detected?.toLocaleString("es-CO") ?? "0"`
     - `content_generated?.toLocaleString("es-CO") ?? "0"`
     - `pending_approvals?.toLocaleString("es-CO") ?? "0"`
  2. Normalizar el despliegue de las variaciones:
     - Si el cambio es `null` o indefinido: proyectar `"Sin comparación"`.
     - Si el cambio es numéricamente igual a `0` o `0.0`: desplegar `"0% esta semana"` (en mensajes y audiencia) o `"0 puntos esta semana"` (en sentimiento).
     - Si el cambio es mayor a `0`: anteponer signo `+`.
     - Si el cambio es menor a `0`: desplegar el valor negativo.
- [x] **Hecho cuando:**
  Las 6 tarjetas de KPIs rendericen valores seguros contra nulos evitando cualquier riesgo de pantalla blanca, y las variaciones neutras de 0% o 0 puntos se muestren de forma transparente y legible.

---

### [x] Tarea 5: Verificación global de regresión, tipado e inmutabilidad
- **RF Asociado:** RF-05, RF-06
- **Estimación:** ~20 minutos
- **Archivos a modificar:** Ninguno (validación y control de calidad)
- **Descripción:**
  1. Ejecutar la suite completa de pruebas automatizadas del backend con `pytest tests/ -v`, certificando el paso del 100% de las 78 pruebas en verde (incluida la nueva de TDD).
  2. Ejecutar la compilación del cliente web con `npm run build` en el directorio `frontend/`, verificando código de salida 0 sin advertencias ni fallos de TypeScript.
  3. Ejecutar `git status` y verificar que los 17 archivos preexistentes en la raíz, la carpeta `backend/` y `motor-ia/` se mantengan 100% inalterados.
- [x] **Hecho cuando:**
  Las 78 pruebas de backend pasen en verde, la compilación del frontend termine con 0 errores y se certifique la total inmutabilidad de los módulos protegidos por la Constitución.
