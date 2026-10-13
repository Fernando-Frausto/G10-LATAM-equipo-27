# 📋 Bitácora de Integración y Cambios del Backend (CommunityLab)

Este documento detalla **todas las funcionalidades, ajustes y mejoras técnicas** implementadas en el backend y la arquitectura de datos, preparado especialmente como guía para **Andrés (Frontend)** y el resto del equipo al momento de consolidar la rama `main`.

---

## 📌 1. Integración de Tania (Persistencia y Almacenamiento en la Nube)

* **Supabase PostgreSQL (Ingesta):**
  * Migración definitiva de SQLite local (`communitylab.db`) hacia **PostgreSQL en Supabase** a través del Session Pooler (`puerto 6543`), eliminando la dependencia de archivos locales.
  * La tabla `interacciones` almacena los mensajes crudos extraídos de Discord de forma centralizada para todo el equipo.
* **Oracle Cloud Infrastructure (OCI Object Storage):**
  * Creación de `oci_uploader.py` y `reporte_semanal.py` para empaquetar los resultados analizados en reportes semanales oficiales (`reportes/AAAA-semana-NN.json`) y depositarlos en el bucket `communitylab-assets` de OCI.

---

## 🛠️ 2. Ajustes y Mejoras aplicadas a la parte de Tania

Para evitar errores en entornos locales o despliegues sin credenciales completas, se realizaron los siguientes blindajes:

1. **Modo Offline tolerante en OCI (`reporte_semanal.py` y `app.py`):**
   * Anteriormente, si un desarrollador no tenía la llave `.pem` de Oracle en su máquina, la aplicación lanzaba un `RuntimeError` bloqueante que impedía ver o descargar el reporte.
   * **Mejora:** Ahora el sistema registra `"subido": False` en los metadatos y muestra una advertencia amarilla amigable en Streamlit, **permitiendo visualizar el JSON y descargarlo localmente** sin interrumpir el flujo.
2. **Validación amigable de Base de Datos (`base_datos.py`):**
   * Se agregó validación en `obtener_conexion()` para que, si falta configurar `DATABASE_URL` en `.env`, el sistema lance un mensaje claro y descriptivo en lugar de un error críptico de timeout de red.
3. **Coexistencia en la interfaz (`app.py`):**
   * Se resolvió el conflicto de Git estructurando en orden la **Sección 4** (Anuncios de Discord vía Webhook de Samuel) y la **Sección 5** (Reporte Semanal y OCI de Tania).
4. **Unificación de Dependencias (`requirements.txt`):**
   * Se consolidaron `psycopg2-binary`, `oci`, `fastapi` y `uvicorn` en un solo archivo limpio.

---

## 🌐 3. Servidor y Endpoints creados para Andrés (`api.py`)

Se implementó un servidor ligero y moderno con **FastAPI** (`api.py`) para servir de backend administrativo al frontend de React/Vite/Netlify:

* **Configuración CORS:** Habilitado para permitir peticiones desde cualquier origen (Netlify / `localhost`).
* **Endpoints disponibles:**
  1. `GET /api/kpis`: Retorna el listado completo de mensajes aprobados y descartados analizados por la IA, inyectando el campo temporal `"copy_final": "Pendiente de redacción por Enoc..."` para que el frontend pueda maquetar tarjetas y estilos sin esperar la fase de copy.
  2. `GET /api/reporte-semanal`: Retorna el reporte semanal más reciente con el bloque `resumen_metricas` (totales, conteo de sentimientos, top 5 hashtags en tendencia y segmentos de usuarios), ideal para pintar gráficas y tarjetas analíticas en el Dashboard.
  3. `GET /`: Health check del servidor.

---

## 🤖 4. Integración con Enoc (Copywriting + HITL)

Para conectar el motor de IA con el flujo de Copywriting con revisión humana (*Human-in-the-Loop*):

1. **Doble conexión a Supabase en `.env`:**
   * `DATABASE_URL`: Conecta al Supabase de Ingesta (Tania) para **leer** los mensajes de Discord.
   * `SUPABASE_DB_URL`: Conecta al Supabase de Copywriting (Enoc) para **escribir** los lotes analizados.
2. **Bandeja de Entrada automatizada (`lotes_ia_kpis`):**
   * Cada vez que se ejecuta el análisis en la interfaz, se crea y alimenta la tabla `lotes_ia_kpis` en el Supabase de Enoc con los mensajes evaluados (aprobados y descartados).
   * La tabla incluye `id_mensaje UNIQUE` con `ON CONFLICT DO UPDATE`, permitiendo re-analizar lotes sin duplicar filas.
   * Incluye la columna de control `estado_revision` (por defecto `'pendiente'`) para que el agente de Enoc gestione el flujo HITL.
3. **Trazabilidad de Modelos (`modelo_ia`):**
   * Se añadió la columna `modelo_ia` tanto en `lotes_ia_kpis` como en `resultados_kpis.json`, registrando exactamente cuál de los 3 modelos (Groq, Gemma 4 o Gemini Flash) generó cada score y razonamiento.

---

## 🚫 5. Filtrado de Bots y Webhooks en la Ingesta de Discord

* **Archivo modificado:** `armar_json_bot_python.py`
* **Problema resuelto:** Los anuncios enviados por el bot o por webhooks (ej. `Spidey Boy`) eran leídos por el extractor de Discord y re-analizados por la IA como si fueran mensajes de alumnos.
* **Solución aplicada:** Se añadió la condición de exclusión para descartar automáticamente cualquier mensaje proveniente de bots (`m.author.bot`) o webhooks (`m.webhook_id`), garantizando que la IA solo procese interacciones reales de la comunidad.

---

## 🔒 6. Seguridad y Limpieza del Repositorio

* **Protección de Secretos (`.gitignore`):** Se bloquearon llaves privadas (`*.pem`) y la carpeta de reportes locales (`reportes/`) para evitar filtraciones accidentales de credenciales OCI.
* **Eliminación de código obsoleto:**
  * Se borró el cuaderno de Colab original (`Codigo_con_imports.ipynb`).
  * Se eliminó el script huérfano de SQLite (`renumerar_ids.py`).

---

## 🚀 Guía rápida para levantar el Backend (Para Andrés)

1. **Descargar cambios y dependencias:**
   ```bash
   git pull origin main
   pip install -r requirements.txt
   ```
2. **Encender la API:**
   ```bash
   python -m uvicorn api:app --reload
   ```
3. **Consumir los datos:**
   * KPIs y mensajes: `http://localhost:8000/api/kpis`
   * Métricas y resumen: `http://localhost:8000/api/reporte-semanal`
