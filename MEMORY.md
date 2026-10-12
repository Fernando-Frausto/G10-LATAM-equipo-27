# MEMORY.md - Análisis de Comunidad con IA (Código Unificado)
Memoria del proyecto entre sesiones. Máximo ~50 líneas: resume o elimina lo que ya no aporte.

## Estado actual
- Aplicación web interactiva con **Streamlit (`app.py`)** para unificar el flujo de trabajo entre los equipos de frontend y copywriting.
- La extracción de Discord (`bot_lote.py`) es independiente de Colab. 
- **Nuevo:** Integración exitosa del código de ingesta de Eduardo (Pull Request fusionado). Ahora el motor extrae el historial completo sin límite de mensajes, y guarda las fechas reales de Discord (`enviado_en`) en UTC.
- Base de datos migrada de SQLite a **Supabase (PostgreSQL)** en la nube (`base_datos.py` vía Session Pooler puerto 6543).
- Sección 4 de `app.py` + `anuncios_discord.py`: subir .txt/.md → Gemma 4 lo reescribe con el Manual de Marca → editar → publicar vía webhook (`DISCORD_WEBHOOK_ANUNCIOS`).
- Sección 5 de `app.py` + `reporte_semanal.py` + `oci_uploader.py`: empaqueta métricas semanales y sube el JSON al bucket `communitylab-assets` en Oracle Cloud (OCI) con soporte de modo offline local.
- **Conexión con Copywriting (HITL):** Al finalizar el análisis en `app.py`, los resultados (`aprobados` y `descartados`) se guardan tanto en `resultados_kpis.json` como en la tabla `lotes_ia_kpis` del Supabase de Copywriting (`SUPABASE_DB_URL`).

## Decisiones (y por qué)
- **Persistencia Híbrida y Doble Supabase:** Mensajes crudos en el Supabase de Ingesta (`DATABASE_URL`), lotes pre-curados por IA en la tabla `lotes_ia_kpis` del Supabase de Copywriting (`SUPABASE_DB_URL` puerto 5432 para revisión HITL), y reportes finales en OCI Object Storage.
- **Despliegue a Producción:** Se subió la app a Streamlit Cloud inyectando el `.env` como Secretos, permitiendo acceso web a todo el equipo.
- **Aislamiento Asíncrono:** `bot_lote.py` se ejecuta mediante `sys.executable` y `subprocess.run` desde Streamlit para aislar su loop de eventos (`asyncio`) y funcionar correctamente en la nube.

## Decisiones extra
- Anuncios: reglas del Manual de Marca incrustadas en el prompt (sin RAG); webhook con `urllib` para no añadir dependencias; menciones (@everyone) bloqueadas.

## Próximos pasos
- [x] Aprovechar el nuevo parámetro `desde` y `hasta` en `obtener_json()` para añadir un selector de fechas visual en la pantalla de Streamlit. (Implementado vía flujo SDD)
- [x] Levantar un servidor FastAPI (`api.py`) para consumir el JSON desde el Frontend (Integración Iterativa).
- [x] Probar anuncios con la GOOGLE_API_KEY real y el webhook del servidor de pruebas.
- [x] Integrar y validar persistencia en Supabase y subida de reportes semanales a OCI (`feature/supabase-persistencia`).
- [x] Conectar salida del Cerebro de IA con la tabla `lotes_ia_kpis` en el Supabase de Copywriting (`feature/ia-resultados-supabase`).
