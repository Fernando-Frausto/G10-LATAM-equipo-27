# Tareas de Implementación: Ciclo de Vida de Estados de Revisión HITL en Supabase

## Tarea 1: Suite de pruebas unitarias TDD para estados HITL y jerarquía editorial
- **RF:** RF-1, RF-2, RF-3, RF-4, RF-5, RF-6
- **Descripción:** Crear el archivo `tests/test_estados_revision_hitl.py` con pruebas unitarias usando mocks de `psycopg2` para verificar:
  1. Inserción explícita de `estado_revision = 'pendiente'` para aprobados y `'rechazado'` para descartados en `guardar_lote_ia_supabase`.
  2. Cláusula de actualización `ON CONFLICT DO UPDATE SET estado_revision = EXCLUDED.estado_revision` condicionada a `WHERE lotes_ia_kpis.estado_revision IN ('pendiente', 'rechazado')`, comprobando que no sobrescriba registros con `'procesado'`, `'aprobado'` ni `'desaprobado'`.
  3. Prevalencia de la jerarquía HITL en `obtener_lote_kpis_supabase` (por ejemplo, si un mensaje fue descartado por IA pero aprobado por un humano, debe catalogarse en aprobados).
  4. Prevalencia de la jerarquía HITL en `_formatear_lote_kpis` de `api.py`.
  5. Inyección de la clave `estado_revision` en los diccionarios generados por `evaluador_lotes.py`.
- [x] **Hecho cuando:** `tests/test_estados_revision_hitl.py` exista y sus pruebas fallen inicialmente (rojo) por no estar implementadas aún las modificaciones en el backend.

---

## Tarea 2: Paridad de estados de revisión en `evaluador_lotes.py`
- **RF:** RF-1, RF-2, RF-3
- **Descripción:** Modificar `evaluador_lotes.py` dentro de la función `evaluar_lote`:
  - Asignar `dato["estado_revision"] = "pendiente"` para mensajes con relevancia >= 70 (aprobados).
  - Asignar `dato["estado_revision"] = "rechazado"` para mensajes con relevancia < 70 (descartados).
- [x] **Hecho cuando:** Los diccionarios generados por `evaluador_lotes.py` y el archivo `resultados_kpis.json` contengan la clave `estado_revision` consistente, y las pruebas correspondientes de la Tarea 1 pasen en verde.

---

## Tarea 3: Persistencia explícita y protección condicional en `base_datos.py`
- **RF:** RF-1, RF-2, RF-4
- **Descripción:** Modificar la función `guardar_lote_ia_supabase` en `base_datos.py`:
  - Incluir la columna `estado_revision` en el `INSERT INTO lotes_ia_kpis (...)` con valor `'pendiente'` para la lista de aprobados y `'rechazado'` para la lista de descartados.
  - Agregar `estado_revision = EXCLUDED.estado_revision` en el bloque `DO UPDATE SET`.
  - Actualizar la condición de protección a `WHERE lotes_ia_kpis.estado_revision IN ('pendiente', 'rechazado');`.
  - Sincronizar la aserción de la consulta en `tests/test_base_datos_filtros.py` para coincidir con la nueva cláusula `IN ('pendiente', 'rechazado')`.
- [x] **Hecho cuando:** `guardar_lote_ia_supabase` persista los estados explícitos, proteja los estados editoriales humanos, y las pruebas de persistencia de la Tarea 1 y `test_base_datos_filtros.py` pasen al 100% en verde.

---

## Tarea 4: Jerarquía HITL en consultas y formateo (`base_datos.py` y `api.py`)
- **RF:** RF-5
- **Descripción:** Implementar la lógica de resolución jerárquica con prevalencia humana en:
  - `obtener_lote_kpis_supabase` (`base_datos.py`): clasificar cada fila según `estado_revision` (`'aprobado'` o `'procesado'` -> aprobados; `'desaprobado'` o `'rechazado'` -> descartados; `'pendiente'` -> aprobados; fallback a `decision_ia == 'aprobado'`), inyectando `copy_final` en aprobados.
  - `_formatear_lote_kpis` (`api.py`): aplicar la misma jerarquía cuando se procesan listas planas o diccionarios con estados de revisión.
- [x] **Hecho cuando:** Las pruebas de jerarquía HITL para `base_datos.py` y `api.py` de la Tarea 1 pasen al 100% en verde, garantizando que la decisión humana prevalezca sobre la decisión de la IA.

---

## Tarea 5: Verificación integral y suite de regresión completa
- **RF:** RF-6
- **Descripción:** Ejecutar la suite completa de pruebas del proyecto (`pytest`) comprobando que todos los tests (antiguos y nuevos) pasen en verde sin dependencias externas ni llamadas reales de red.
- [x] **Hecho cuando:** `pytest` finalice con código de salida 0 y reporte 100% de tests en verde (0 fallos, 0 errores, 0 regresiones).
