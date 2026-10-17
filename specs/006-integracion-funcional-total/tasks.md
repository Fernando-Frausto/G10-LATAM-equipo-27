# Tareas de Implementación 006: Integración Funcional Total

> **Regla de Oro:** Máximo 6 tareas ordenadas de ~20 minutos cada una. **CERO modificaciones** a los 12 archivos `.py` preexistentes de la raíz, ni a los archivos de `backend/` y `motor-ia/`. Diseño **Test-First (TDD)** obligatorio.

---

### Tarea 1: Creación de la Suite de Pruebas TDD en Fase Red (`tests/test_unificacion_motor_ia.py`)
- **RF Asociado:** RF-01, RF-02, RF-03, RF-04, RF-05
- **Descripción:** Escribir en `tests/test_unificacion_motor_ia.py` las pruebas unitarias y de integración con mocks para:
  1. `GET /api/v1/ai/models`: Lista de los 3 proveedores de IA (`"Groq (Llama 3.3)"`, `"Google Gemma 4"`, `"Google Gemini Flash Lite"`) con modelos limpios y disponibilidad.
  2. `POST /api/v1/ai/evaluate-batch`: Delegación dinámica en `ver_json.obtener_json` con filtro `desde` / `hasta`, selección de cerebro IA, invocación de `evaluador_lotes.evaluar_lote`, persistencia en `lotes_ia_kpis` de Supabase y refresco de caché.
  3. `POST /api/v1/oci-storage/weekly-sync` y `GET /api/v1/oci-storage/weekly-period`: Cálculo de la semana actual con `periodos.py` y delegación en `reporte_semanal.py` y `oci_uploader.py`.
  4. `GET /api/v1/community/live-summary` y `GET /api/v1/export/community-data`: Agregación en vivo de highlights (con `copy_final` de Enoc), audiencia, calendario y reportes semanales.
- [x] **Hecho cuando:** Los nuevos tests existen en `tests/test_unificacion_motor_ia.py` y fallan de forma controlada (Fase Red) debido a la ausencia de los endpoints y lógica en `puente_motor_ia.py`.

---

### Tarea 2: Implementación Backend de Modelos de IA y Evaluación por Lote con Fechas en `puente_motor_ia.py` (Fase Green)
- **RF Asociado:** RF-01
- **Descripción:** Implementar en `puente_motor_ia.py` los endpoints:
  1. `GET /api/v1/ai/models`: Resolviendo dinámicamente los 3 cerebros de la raíz (`cerebro_ia`, `cerebro_ia_gemma_4`, `cerebro_ia_gemini_flash`), modelos configurados y disponibilidad.
  2. `POST /api/v1/ai/evaluate-batch`: Procesando payload con `proveedor`, `desde`, `hasta`, `solo_pendientes` y `limite`, invocando `ver_json.obtener_json`, el módulo cerebro seleccionado, `evaluador_lotes.evaluar_lote`, persistiendo en `base_datos.guardar_lote_ia_supabase` y disparando `sincronizar_supabase_a_sqlite()`.
- [x] **Hecho cuando:** Las pruebas de `GET /api/v1/ai/models` y `POST /api/v1/ai/evaluate-batch` en `tests/test_unificacion_motor_ia.py` pasan en verde al 100%.

---

### Tarea 3: Implementación Backend de OCI Storage Sync/Period y Resumen/Exportación Dinámica en Vivo en `puente_motor_ia.py` (Fase Green)
- **RF Asociado:** RF-02, RF-03
- **Descripción:** Implementar en `puente_motor_ia.py`:
  1. `GET /api/v1/oci-storage/weekly-period`: Rango de fechas de la semana actual y etiqueta `AAAA-semana-NN` calculada mediante `periodos.py`.
  2. `POST /api/v1/oci-storage/weekly-sync`: Delegación dinámica en `reporte_semanal.generar_reporte_semanal` y `oci_uploader.subir_json_a_oci` usando datos reales de Supabase.
  3. `GET /api/v1/community/live-summary` y `GET /api/v1/export/community-data`: Agregación y cálculo dinámico de `highlights` (integrando `copy_final` de Enoc), `highlights_summary`, `audience` (desglose por actividad y segmentos de IA), `calendar` (agrupación diaria) y `reports` (historial semanal).
- [x] **Hecho cuando:** Las pruebas correspondientes a OCI Storage, live summary y exportación en `tests/test_unificacion_motor_ia.py` pasan en verde al 100%.

---

### Tarea 4: Integración en Frontend de Evaluación IA por Lotes, Filtro de Fechas y Modelos Reales (`Messages.tsx` y `Settings.tsx`)
- **RF Asociado:** RF-01
- **Descripción:** Actualizar en `frontend/src/`:
  1. `Messages.tsx`: Añadir panel interactivo con inputs de fecha `Desde` y `Hasta`, selector desplegable de los 3 cerebros de IA consumido desde `GET /api/v1/ai/models`, botón de acción para ejecutar `POST /api/v1/ai/evaluate-batch` con estado de carga y refresco automático, y ajustar el filtro de etapas para mostrar mensajes tanto en `'ingesta'` / `'en_ingesta'` como en `'en_analisis'`.
  2. `Settings.tsx`: Conectar la sección de Inteligencia Artificial al endpoint `GET /api/v1/ai/models`, mostrando dinámicamente los 3 cerebros reales del proyecto con sus modelos activos en lugar de opciones estáticas.
- [x] **Hecho cuando:** `Messages.tsx` y `Settings.tsx` compilan sin errores de TypeScript, permiten seleccionar fechas y cerebros reales para evaluar lotes, y muestran mensajes en ingesta y análisis.

---

### Tarea 5: Integración en Frontend de Consumo Dinámico en Vivo y Exportación con Fallback Seguro
- **RF Asociado:** RF-03, RF-04
- **Descripción:** Actualizar en `frontend/src/`:
  1. `Highlights.tsx` y `FeaturedStories.tsx`: Consumir en vivo `GET /api/v1/community/live-summary`, mostrando `highlights` reales con `copy_final` de Enoc y fallback a `mockCommunityData.ts` si la API no está disponible.
  2. `Audience.tsx`: Consumir en vivo métricas de audiencia y segmentos desde `GET /api/v1/community/live-summary` con fallback a `mockCommunityData.audience`.
  3. `Calendar.tsx`: Consumir actividad diaria real desde `GET /api/v1/community/live-summary` con fallback a `mockCommunityData.calendar`.
  4. `MyReports.tsx`: Consumir historial de reportes reales desde `GET /api/v1/community/live-summary` con fallback a `mockCommunityData.reports`.
  5. `Export.tsx`: Conectar botón de exportación a `GET /api/v1/export/community-data` para descargar el JSON real de la comunidad, con fallback de exportación local ante fallos de conexión.
- [x] **Hecho cuando:** Las 6 vistas compilan sin errores de TypeScript, consumen los endpoints en vivo al estar disponible el backend y mantienen fallback fluido a `mockCommunityData.ts` ante desconexión.

---

### Tarea 6: Verificación Integral de Regresión, Inmutabilidad y Actualización de `MEMORY.md`
- **RF Asociado:** RF-01, RF-02, RF-03, RF-04, RF-05
- **Descripción:**
  1. Ejecutar la suite completa de pruebas automáticas con `pytest` para garantizar el 100% de tests en verde sin regresiones.
  2. Ejecutar `git diff` para confirmar que ninguno de los 12 archivos `.py` preexistentes de la raíz (`api.py`, `app.py`, `base_datos.py`, etc.) ni los directorios `motor-ia/` y `backend/` hayan sido modificados.
  3. Actualizar `MEMORY.md` documentando la finalización de la integración funcional total (Spec 006), endpoints añadidos, decisiones arquitectónicas y estado del proyecto.
- [x] **Hecho cuando:** `pytest` reporta 100% de tests en verde, `git diff` confirma inmutabilidad estricta en los archivos protegidos y `MEMORY.md` refleja fielmente el nuevo estado y decisiones del sistema.
