# 📌 Guía de Mejoras Técnicas Pendientes (Backlog de Optimización)

Este documento contiene el detalle técnico de los **8 puntos de mejora** identificados en la auditoría de código del proyecto, listos para implementarse en el futuro si el equipo decide abordarlos con calma después de la entrega final.

---

## 📋 Resumen Rápido

| # | Área | Problema | Solución Resumida |
|---|---|---|---|
| **1** | Base de Datos | Hash frágil: cambiar el nombre a un canal duplica mensajes | Usar el ID numérico nativo de Discord (`id_mensaje_discord`) |
| **2** | Ingesta Discord | El bot lee canales privados o de staff si tiene permisos | Soporte para `DISCORD_CANALES_EXCLUIDOS` en `.env` |
| **3** | Reportes Locales | `resultados_kpis.json` se sobrescribe con el último lote | Merge acumulativo por `id_mensaje` sin borrar lotes previos |
| **4** | Ahorro de Tokens | La IA vuelve a evaluar los mismos mensajes recientes | Usar `estado = 'analizado'` en la tabla `interacciones` |
| **5** | Seguridad API | CORS abierto a cualquier origen (`*`) | Restringir orígenes permitidos con `ALLOWED_ORIGINS` (.env) |
| **6** | Integración Copy | `copy_final` de Enoc no se lee de la BD | Incluir `copy_final` en el `SELECT` de `/api/kpis` |
| **7** | Mantenibilidad | Imports sin uso en cerebros de IA y bot de lote | Limpiar `import json` y `CANALES` residuales |
| **8** | Dependencias | `requirements.txt` no tiene versiones fijadas | Congelar versiones estables compatibles con el entorno actual |

---

## 🛠️ Detalle Técnico de cada Punto

---

### 1. Deduplicación Inmutable con `id_mensaje_discord` (Problema A1)

* **Diagnóstico:**  
  Actualmente el hash se calcula con: `SHA256(origen | nombre_canal | autor | texto)`. Si en Discord renombren un canal (ej: `#preguntas` a `#faq`) o un usuario cambia su apodo, el hash cambia y la base de datos vuelve a insertar mensajes que ya existían.
* **Archivos a modificar:** `base_datos.py`, `armar_json_bot_python.py`, `modelos.py` y `procesamiento.py`.
* **Solución técnica:**
  1. En Supabase (`DATABASE_URL`), agregar la columna:
     ```sql
     ALTER TABLE interacciones ADD COLUMN IF NOT EXISTS id_mensaje_discord VARCHAR(64) UNIQUE;
     ```
  2. En `armar_json_bot_python.py` (`construir_paquete`), capturar el ID nativo del mensaje:
     ```python
     "id_mensaje_discord": str(m.id)
     ```
  3. En `modelos.py`, agregar a la clase `Interaccion`:
     ```python
     id_mensaje_discord: str | None = None
     ```
  4. En `base_datos.py` (`guardar_interaccion`), deduplicar por `id_mensaje_discord`:
     ```python
     # Si ya existe id_mensaje_discord, no se inserta duplicado
     ```
* **Coordinación requerida:** Visto bueno de Tania para alterar la tabla en Supabase.

---

### 2. Exclusión de Canales Privados o de Staff (Problema A2)

* **Diagnóstico:**  
  La detección automática lee cualquier canal de texto donde el bot tenga permiso, con riesgo de leer canales de staff, pruebas o moderación.
* **Archivos a modificar:** `bot_lote.py` y `armar_json_bot_python.py`.
* **Solución técnica:**
  1. Definir en `.env`:
     ```env
     DISCORD_CANALES_EXCLUIDOS=staff,admin,moderacion,pruebas,notificaciones
     ```
  2. En `detectar_canales()`, verificar si el nombre del canal está en la lista de exclusión y saltarlo antes de leer el historial.

---

### 3. Acumulación Inteligente (Merge) en `resultados_kpis.json` (Problema A3)

* **Diagnóstico:**  
  Cada corrida del evaluador sobrescribe el archivo local con solo los últimos mensajes analizados (del slider 1–20), truncando el histórico para el reporte semanal local.
* **Archivos a modificar:** `evaluador_lotes.py`.
* **Solución técnica:**
  1. Al guardar localmente, leer el JSON existente si existe.
  2. Indexar por `id_mensaje` y combinar los resultados nuevos con los previos.
  3. Guardar el archivo consolidado para que conserve toda la historia.

---

### 4. Transición de Estado para Evitar Reanálisis y Gasto de Tokens (Problema A4)

* **Diagnóstico:**  
  Cada vez que se oprime el botón de análisis sin filtro de fechas, la IA evalúa los mismos 20 mensajes más recientes una y otra vez, gastando tokens de API innecesariamente.
* **Archivos a modificar:** `base_datos.py` y `evaluador_lotes.py`.
* **Solución técnica:**
  1. En `base_datos.py` (`listar_interacciones_para_analisis`), filtrar:
     ```sql
     WHERE estado = 'pendiente'
     ```
  2. Cuando el evaluador analice un mensaje con éxito, actualizar su estado:
     ```sql
     UPDATE interacciones SET estado = 'analizado' WHERE id = %s;
     ```
  *(Nota: La columna `estado` ya existe en la tabla de Tania desde el inicio con valor por defecto `'pendiente'`, por lo que no se requiere crear columnas nuevas).*

---

### 5. Restricción de Orígenes CORS en `api.py` (Problema B1)

* **Diagnóstico:**  
  Actualmente la API tiene `allow_origins=["*"]`, exponiendo los mensajes de la comunidad a cualquier sitio web externo.
* **Archivos a modificar:** `api.py` y `.env`.
* **Solución técnica:**
  1. Definir en `.env`:
     ```env
     ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000,https://tu-frontend.netlify.app
     ```
  2. En `api.py`:
     ```python
     origenes = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]
     app.add_middleware(CORSMiddleware, allow_origins=origenes or ["*"], ...)
     ```

---

### 6. Lectura Dinámica del Copy Real de Enoc en la API (Problema C1)

* **Diagnóstico:**  
  La consulta a `lotes_ia_kpis` no pide la columna `copy_final`, por lo que la API siempre devuelve el texto provisional *"Pendiente de redacción por Enoc..."*.
* **Archivos a modificar:** `base_datos.py`.
* **Solución técnica:**
  1. Asegurar la columna en la tabla de Copywriting:
     ```sql
     ALTER TABLE lotes_ia_kpis ADD COLUMN IF NOT EXISTS copy_final TEXT;
     ```
  2. En `base_datos.py` (`obtener_lote_kpis_supabase`), incluir `copy_final` en el `SELECT`:
     ```sql
     SELECT ..., copy_final FROM lotes_ia_kpis ...
     ```
  3. Si `copy_final` tiene texto, devolverlo; si es `None` o vacío, mantener el placeholder temporal.

---

### 7. Limpieza de Imports Residuales (Problema C2)

* **Diagnóstico:**  
  Existen módulos con imports que ya no se usan.
* **Archivos a modificar:** `cerebro_ia.py`, `cerebro_ia_gemma_4.py`, `cerebro_ia_gemini_flash.py`, `bot_lote.py`.
* **Solución técnica:**
  * Remover `import json` en los tres archivos de cerebros de IA.
  * Remover `from armar_json_bot_python import CANALES` en `bot_lote.py` (ya no se usa ahí).

---

### 8. Fijación de Versiones Estables en `requirements.txt` (Problema D1)

* **Diagnóstico:**  
  Las librerías están declaradas sin límites de versión, lo que podría provocar incompatibilidades si alguna librería se actualiza en el futuro con cambios drásticos.
* **Archivos a modificar:** `requirements.txt`.
* **Solución técnica:**
  * Acotar las versiones compatibles probadas actualmente:
    ```text
    fastapi>=0.110.0,<1.0.0
    uvicorn>=0.28.0,<1.0.0
    pydantic>=2.0.0,<3.0.0
    langchain>=0.1.0,<0.4.0
    langchain-groq>=0.1.0,<0.3.0
    langchain-google-genai>=1.0.0,<3.0.0
    streamlit>=1.30.0,<2.0.0
    psycopg2-binary>=2.9.0,<3.0.0
    python-dotenv>=1.0.0,<2.0.0
    discord.py>=2.3.0,<3.0.0
    oci>=2.115.0,<3.0.0
    pytest>=8.0.0,<10.0.0
    httpx>=0.27.0,<1.0.0
    ```
