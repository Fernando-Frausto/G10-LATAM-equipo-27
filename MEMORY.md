# MEMORY.md - Análisis de Comunidad con IA (Código Unificado)
Memoria del proyecto entre sesiones. Máximo ~50 líneas: resume o elimina lo que ya no aporte.

## Estado actual
- **Arquitectura desacoplada (Regla 2):** `app.py` funciona como carrocería Streamlit limpia. La orquestación y el bucle de IA viven en `evaluador_lotes.py` con tolerancia a fallos por mensaje (try/except) y protección ante fallo total.
- **Backend y API REST (`api.py`):** `/api/kpis` y `/api/reporte-semanal` consultan prioritariamente Supabase (`lotes_ia_kpis` e `historial_reportes_semanales`) con fallback local transparente y contrato canónico garantizado (`{"aprobados": [...], "descartados": [...]}` con `copy_final`). CORS configurable.
- **Filtrado de bots:** Exclusión de bots (`Spidey Boy#0000`, `%bot%`, discriminadores `#0000`, tipos `bot`/`webhook`) en `base_datos.py` y `ver_json.py`.
- **Integración HITL con Enoc:** Mensajes aprobados por IA van con `estado_revision = 'pendiente'`; descartados van con `'rechazado'`. Protección en Supabase `WHERE estado_revision IN ('pendiente', 'rechazado')` (estados humanos `'procesado'`, `'aprobado'`, `'desaprobado'` no se sobrescriben). Soberanía humana en `/api/kpis`.
- **DRY en Prompts y Modelos:** `prompts_ia.py` centraliza `FormatoSalida` y `template_filtro`. Modelos leen `GEMMA_MODEL` y `GEMINI_MODEL` con saneamiento `.strip()` y fallback limpio.
- **Canales automáticos de Discord:** Detección dinámica de canales de texto por permisos (`view_channel`, `read_message_history`), aislamiento con `DISCORD_GUILD_ID`, normalización `#nombre` para no romper hashes SHA-256 en Supabase y filtro de bots/webhooks inmutable.
- **Tests (TDD):** 48 pruebas unitarias y de integración asíncrona automáticas en `tests/` con mocks (`pytest`), sin llamadas de red ni dependencias externas.
- **Persistencia e integraciones:** Ingesta de Discord a Supabase (`DATABASE_URL`), bandeja HITL en Supabase de Copywriting (`SUPABASE_DB_URL`), reportes en OCI Object Storage y anuncios vía webhook de Discord.

## Decisiones (y por qué)
- **Aislamiento Constitucional:** Lógica pesada de IA y persistencia en `evaluador_lotes.py`, no en `app.py`, garantizando modularidad y testabilidad.
- **Resiliencia de Datos:** Si un mensaje falla por rate limit, se omite y el resto del lote se guarda; si el 100% falla, se protege el archivo previo sin sobrescribirlo.
- **Doble Supabase:** Ingesta centralizada en `DATABASE_URL` (puerto 6543) y bandeja de curación de Copywriting en `SUPABASE_DB_URL` (puerto 5432).
- **TDD Estricto:** Cada cambio funcional debe estar precedido por su test y validado al 100% en verde por QA (@reviewer) antes de considerarse terminado.

## Errores a evitar
- Nunca saltarse el flujo formal (SDD) ni asumir que un cambio es "demasiado pequeño" para planificarse: siempre genera deuda técnica o cabos sueltos.
- Nunca hacer push directo a `main` (Regla 1). Todo el trabajo se mantiene en ramas `feature/`.
- Nunca escribir credenciales en código duro (Regla 4).
