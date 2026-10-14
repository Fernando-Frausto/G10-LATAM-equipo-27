# Especificación: Ciclo de Vida de Estados de Revisión HITL en Supabase

## Contexto y Alcance
Esta especificación define la arquitectura del ciclo de vida de los estados de revisión dentro del flujo Human-in-the-Loop (HITL) entre el motor de análisis de IA de CommunityLab y el equipo editorial de Copywriting (liderado por Enoc).
El objetivo es establecer un catálogo canónico de estados, garantizar la **prevalencia de la decisión humana por encima de la inferencia de la IA**, proteger los registros curados manualmente frente a re-análisis automáticos, y asegurar la consistencia y paridad de datos entre la base de datos Supabase (`lotes_ia_kpis`), el servicio backend (`evaluador_lotes.py`), el archivo local (`resultados_kpis.json`) y la API REST (`api.py`).

---

## Catálogo Canónico y Reglas de Normalización de Estados

### 1. Estados Automáticos de IA
- **`pendiente`**: Mensaje calificado por la IA con relevancia >= 70 (`decision_ia = 'aprobado'`), listo como insumo en la bandeja de entrada editorial.
- **`rechazado`**: Mensaje clasificado por la IA con relevancia < 70 (`decision_ia = 'descartado'`), archivado automáticamente sin requerir atención editorial.

### 2. Estados Editoriales Humanos (HITL)
- **`aprobado`**: Mensaje validado y confirmado manualmente por el redactor/revisor humano.
- **`desaprobado`**: Mensaje descartado manualmente por el redactor/revisor humano tras inspección.
- **`procesado`**: Mensaje cuyo copy final ya fue redactado, enriquecido y completado por el equipo editorial.

### 3. Reglas de Higiene y Fallback
- Toda comparación de estados en código SQL o Python debe realizarse de forma insensible a mayúsculas/minúsculas y libre de espacios en los extremos (`.strip().lower()`).
- Si un registro presenta un valor nulo o no reconocido, el sistema lo tratará como `'pendiente'` por defecto para garantizar que ningún mensaje se pierda de la vista de los revisores.

---

## Requerimientos Funcionales (EARS)

### 1. Asignación de Estado 'rechazado' para Descartados de IA (Event-driven Requirement)
- **QUÉ:** Cuando el sistema procese mensajes clasificados como descartados (relevancia < 70), el sistema deberá asignar explícitamente el valor `'rechazado'` en el atributo `estado_revision`, tanto en la persistencia de Supabase (`guardar_lote_ia_supabase`) como en la estructura de datos generada por el backend (`evaluador_lotes.py`).
- **POR QUÉ:** Para evitar que mensajes no cualificados por la IA ingresen a la bandeja de trabajo de Copywriting con el estado `'pendiente'`, ahorrando tiempo al equipo de redacción.

---

### 2. Asignación de Estado 'pendiente' para Aprobados de IA (Event-driven Requirement)
- **QUÉ:** Cuando el sistema procese mensajes clasificados como aprobados (relevancia >= 70), el sistema deberá asignar explícitamente el valor `'pendiente'` en el atributo `estado_revision`, tanto en la persistencia de Supabase (`guardar_lote_ia_supabase`) como en la estructura de datos generada por el backend (`evaluador_lotes.py`).
- **POR QUÉ:** Para que los mensajes calificados como valiosos estén inmediatamente disponibles en la bandeja de entrada de Enoc como insumos pendientes de redacción y curación.

---

### 3. Paridad y Consistencia en `evaluador_lotes.py` (Ubiquitous Requirement)
- **QUÉ:** Al ensamblar los diccionarios de cada mensaje analizado en `evaluador_lotes.py`, el sistema deberá inyectar explícitamente la clave `"estado_revision": "pendiente"` en los mensajes de la lista de `aprobados`, y `"estado_revision": "rechazado"` en los mensajes de la lista de `descartados`, antes de escribir en `resultados_kpis.json` y enviar a Supabase.
- **POR QUÉ:** Para garantizar paridad total entre los datos persistidos localmente en el archivo JSON y los registros almacenados en la tabla `lotes_ia_kpis` de Supabase.

---

### 4. Protección de Curación Humana en Sincronización SQL (State-driven / Unwanted Behavior)
- **QUÉ:** En la función `guardar_lote_ia_supabase`, la sentencia de inserción y actualización (`ON CONFLICT (id_mensaje) DO UPDATE`) deberá incluir la columna `estado_revision = EXCLUDED.estado_revision` en el bloque `SET`, condicionada estrictamente a la cláusula:
  ```sql
  WHERE lotes_ia_kpis.estado_revision IN ('pendiente', 'rechazado')
  ```
  Si el registro en Supabase posee un estado editorial humano (`'procesado'`, `'aprobado'` o `'desaprobado'`), la sentencia no deberá actualizar ningún campo del registro.
- **POR QUÉ:** Para garantizar que una re-ejecución automática del análisis de IA no sobreescriba ni destruya el trabajo manual, las notas ni las decisiones editoriales tomadas previamente por los redactores.

---

### 5. Jerarquía HITL y Prevalencia Humana en Clasificación de APIs (State-driven Requirement)
- **QUÉ:** Al consultar o normalizar mensajes analizados (`obtener_lote_kpis_supabase` en `base_datos.py` y `_formatear_lote_kpis` en `api.py`), el sistema deberá aplicar la siguiente jerarquía de resolución con prevalencia humana:
  1. Si `estado_revision` es `'aprobado'` o `'procesado'`, el mensaje DEBE clasificarse en `aprobados` (con `copy_final`), independientemente de la opinión original de la IA (`decision_ia`).
  2. Si `estado_revision` es `'desaprobado'` o `'rechazado'`, el mensaje DEBE clasificarse en `descartados`.
  3. Si `estado_revision` es `'pendiente'`, el mensaje se clasifica en `aprobados` (por haber sido pre-seleccionado por la IA).
  4. Si el registro carece de `estado_revision` (archivos locales antiguos de retrocompatibilidad), la clasificación se resolverá mediante `decision_ia == 'aprobado'` o la lista donde resida el elemento.
- **POR QUÉ:** Para implementar el principio fundamental de Human-in-the-Loop donde la decisión del revisor humano es soberana y tiene prioridad sobre el modelo generativo.

---

### 6. Suite de Pruebas Unitarias Automatizadas con Mocks (TDD) (Ubiquitous Requirement)
- **QUÉ:** El sistema deberá contar con una suite de pruebas automatizadas con `pytest` que valide mediante dobles de prueba (mocks):
  1. La asignación e inserción explícita de `estado_revision` (`'pendiente'` y `'rechazado'`) en `guardar_lote_ia_supabase`.
  2. La actualización del campo `estado_revision` y la protección estricta `WHERE lotes_ia_kpis.estado_revision IN ('pendiente', 'rechazado')`.
  3. La inyección de `estado_revision` en `evaluador_lotes.py` tanto en memoria como en el JSON local.
  4. La jerarquía HITL en `obtener_lote_kpis_supabase` y `api.py`, verificando que un mensaje con `decision_ia = 'descartado'` pero `estado_revision = 'aprobado'` se entregue como aprobado, y viceversa.
  5. La sincronización y no-regresión de las pruebas preexistentes en `tests/test_base_datos_filtros.py` y `tests/test_api.py`.
- **POR QUÉ:** Para cumplir con la Regla 6 de la Constitución (Diseño Test-First) y certificar que la jerarquía HITL y la no-regresión estén matemáticamente garantizadas.

---

## Criterios de Aceptación y Retrocompatibilidad
1. El contrato canónico devuelto por `/api/kpis` debe mantener la estructura fija `{"aprobados": [...], "descartados": [...]}` con `copy_final` en aprobados.
2. Los registros antiguos que no posean la clave `estado_revision` no deben provocar excepciones de ejecución (`KeyError`), recurriendo a `decision_ia`.
3. Todos los tests de la suite (`pytest`) deben ejecutarse al 100% en verde sin dependencias de red ni claves activas.
