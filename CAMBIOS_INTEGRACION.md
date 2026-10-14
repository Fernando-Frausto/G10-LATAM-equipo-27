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

## 🛡️ 7. Paquete de Robustez, Desacoplamiento y Resiliencia del Backend

En esta fase se consolidó la estabilidad técnica de todo el sistema mediante arquitectura modular, protección de datos y desarrollo guiado por pruebas (TDD):

1. **Desacoplamiento de UI y nuevo Servicio Backend (`evaluador_lotes.py`):**
   * Se extrajo toda la orquestación de inferencia de IA, el bucle de mensajes, el manejo de errores y la persistencia fuera de `app.py`.
   * `app.py` opera exclusivamente como carrocería visual (Streamlit) consumiendo `evaluar_lote(...)` mediante callbacks reactivos de progreso, dando estricto cumplimiento a la Regla 2 de la Constitución.
2. **Resiliencia ante Fallos de Inferencia y Protección de Datos:**
   * La evaluación con LLMs encapsula cada mensaje en un bloque de excepción individual: si un mensaje sufre *rate limit* (HTTP 429) o *timeout*, se omite y el lote continúa procesando los restantes, guardando los exitosos.
   * Si el 100% de los mensajes de un lote fallan, el sistema **no sobrescribe** `resultados_kpis.json` con listas vacías, preservando intacto el lote anterior.
3. **Desacoplamiento Total de la API REST (`api.py`):**
   * **`GET /api/kpis`:** Consulta prioritariamente la tabla `lotes_ia_kpis` de Supabase, reconstruye el árbol canónico de datos e inyecta `copy_final`. Si no hay conexión o datos, realiza fallback transparente a `resultados_kpis.json`. Ante cualquier escenario vacío devuelve de forma predecible `{"aprobados": [], "descartados": []}` (HTTP 200, eliminando respuestas de tipo lista `[]`).
   * **`GET /api/reporte-semanal`:** Consulta prioritariamente la tabla `historial_reportes_semanales` en Supabase. Si no hay registros, recurre al `.json` más reciente en `reportes/`. Si ninguna fuente tiene reportes, retorna una respuesta HTTP 404 estructurada.
   * **CORS Seguro:** Parametrizable en producción mediante la variable de entorno `ALLOWED_ORIGINS`.
4. **Filtrado Histórico de Bots y Webhooks en Consultas (`base_datos.py` y `ver_json.py`):**
   * Se blindó la función `listar_interacciones` y `obtener_json` con exclusión de autores históricos (`Spidey Boy#0000`, patrones `%bot%`, discriminadores de Discord `#0000` y registros de tipo `bot`/`webhook`).
5. **Protección del Trabajo Editorial HITL en Supabase:**
   * En `guardar_lote_ia_supabase`, la cláusula de actualización ante conflicto (`ON CONFLICT`) incluye la condición `WHERE lotes_ia_kpis.estado_revision = 'pendiente'`, impidiendo que un re-análisis automático sobrescriba mensajes ya editados o aprobados por el equipo de Copywriting.
6. **Centralización DRY de Esquemas y Prompts (`prompts_ia.py`):**
   * Creación del módulo compartido `prompts_ia.py` que centraliza `FormatoSalida`, `template_filtro` y `prompt_filtro`, eliminando la duplicación en los motores `cerebro_ia.py`, `cerebro_ia_gemma_4.py` y `cerebro_ia_gemini_flash.py`.
7. **Aislamiento de Variables de Entorno por Motor:**
   * `cerebro_ia_gemma_4.py` lee `GEMMA_MODEL` y `cerebro_ia_gemini_flash.py` lee `GEMINI_MODEL` con saneamiento de espacios (`.strip()`) y fallbacks jerárquicos a defaults institucionales o `GOOGLE_MODEL`.
8. **Suite Completa de Pruebas Unitarias Automatizadas (TDD):**
   * Se incorporaron `pytest` y `httpx` en `requirements.txt`.
   * Se desarrolló una suite de 31 pruebas unitarias en `tests/` con dobles de prueba (`unittest.mock`), ejecutándose al 100% en verde de forma aislada sin consumir tokens ni conexiones a bases de datos de producción.
9. **Higiene del Repositorio:**
   * Eliminación física del script residual `update_app.py` y activación de `resultados_kpis.json` en `.gitignore`.

---

## ✍️ 8. Integración del Ciclo de Vida HITL con Enoc (Copywriting)

Para coordinar perfectamente la IA con el agente de Copywriting de Enoc y su flujo de revisión humana (*Human-in-the-Loop*):

1. **Diferenciación de Estados de Revisión Iniciales (`estado_revision`):**
   * **`'pendiente'`:** Mensajes calificados con relevancia $\ge 70$ (aprobados por la IA). Quedan automáticamente en la bandeja de entrada para que el pipeline de Enoc los tome y redacte borradores.
   * **`'rechazado'`:** Mensajes calificados con relevancia $< 70$ (descartados por la IA). Quedan guardados para auditoría pero el agente de Enoc los ignora, ahorrando tokens y cómputo.
   * La clave `estado_revision` se inyecta simétricamente tanto en la tabla Supabase `lotes_ia_kpis` como en el archivo local `resultados_kpis.json`.
2. **Blindaje de la Curación Humana en Supabase:**
   * La actualización en caso de re-análisis (`ON CONFLICT DO UPDATE`) se restringió estrictamente a:
     ```sql
     WHERE lotes_ia_kpis.estado_revision IN ('pendiente', 'rechazado');
     ```
   * Si el redactor o el humano ya interactuó con el mensaje pasándolo a `'procesado'`, `'aprobado'` o `'desaprobado'`, una nueva corrida de la IA **jamás sobrescribirá ni destruirá** la decisión editorial humana.
3. **Soberanía Humana en la API (`/api/kpis` y `base_datos.py`):**
   * En `obtener_lote_kpis_supabase` y `_formatear_lote_kpis`, la decisión humana tiene precedencia absoluta sobre la IA: si un mensaje fue descartado originalmente por la IA pero un editor humano lo marcó como `'aprobado'` (o `'procesado'`), la API lo clasifica soberanamente dentro de `aprobados` inyectando su `copy_final`.
4. **Suite de Pruebas Ampliada:**
   * Se incorporó `tests/test_estados_revision_hitl.py` con 5 pruebas adicionales, totalizando **36 pruebas unitarias al 100% en verde**.

---

## 📡 9. Detección Automática de Canales de Discord (Aportación de Eduardo Alonso)

* **Archivos modificados:** `armar_json_bot_python.py`, `bot_lote.py` y `tests/test_canales_discord.py`.
* **Funcionalidad Integrada:**
  1. **Detección Dinámica (`detectar_canales`):** El bot ya no depende de una lista rígida de IDs (`CANALES`). Al conectarse a Discord, escanea automáticamente todos los canales de texto donde tiene permisos efectivos de `view_channel` y `read_message_history`.
  2. **Aislamiento por Servidor (`DISCORD_GUILD_ID`):** Configurable en `.env` (o Secrets de Colab). Si el bot vive en múltiples servidores, restringe la ingesta exclusivamente a la comunidad de CloudEdTech.
  3. **Preservación Inmutable de Hashes y Retrocompatibilidad:**
     - La función `nombre_canal(canal)` normaliza el formato a `#nombre` (evitando dobles almohadillas `##`), asegurando que la función `calcular_hash` no altere los hashes SHA-256 preexistentes en Supabase y previniendo duplicados accidentales.
     - Se mantiene `CANALES = {}` exportado como diccionario para retrocompatibilidad con scripts dependientes.
  4. **Preservación Inmutable del Filtro de Bots y Webhooks:**
     - Se mantuvo intacto el filtro implementado en el commit `ea566ed` (`getattr(m.author, "bot", False) or getattr(m, "webhook_id", None)`), de acuerdo con la decisión consensuada del equipo (Enoc y Eduardo) de descartar simulaciones y anuncios automáticos para preservar datos reales y limpios.
  5. **Suite de Pruebas con Mocks de Discord:**
     - 12 pruebas unitarias y de integración asíncrona en `tests/test_canales_discord.py` que validan permisos, filtrado, hashing y ciclo de vida de `on_ready`.
     - Suite global: **48 pruebas unitarias al 100% en verde**.

---

## 🚀 Guía rápida para levantar el Backend (Para Andrés)

1. **Descargar cambios y dependencias:**
   ```bash
   git pull origin main
   pip install -r requirements.txt
   ```
2. **Ejecutar suite de pruebas (opcional pero recomendado):**
   ```bash
   pytest
   ```
3. **Encender la API:**
   ```bash
   python -m uvicorn api:app --reload
   ```
4. **Consumir los datos:**
   * KPIs y mensajes: `http://localhost:8000/api/kpis`
   * Métricas y resumen: `http://localhost:8000/api/reporte-semanal`

