# Tareas de Implementación: Spec 015 - Integración del Pipeline Mototradis MVP de Enoc con Backend y Redacción de Contenidos

Lista de tareas secuenciales de ~20 minutos cada una siguiendo la metodología Test-Driven Development (TDD), el principio de inviolabilidad constitucional de código legado y el mandato explícito de transparencia de modelos de Inteligencia Artificial (*"quiero que en cada cosa diga el modelo de ia que esta utilizando para realizarla"*).

---

### [x] Tarea 1: Incorporación Íntegra de Archivos de `origin/mototradis-mvp` y Dependencias en `requirements.txt` (RF-01, RF-07)
- **Estimación**: ~20 minutos
- **Requerimientos**: RF-01, RF-07
- **Descripción**: Incorporar de forma limpia en la rama de trabajo los 17 archivos desarrollados por Enoc en la rama `origin/mototradis-mvp` (commit `23699cf`) y actualizar las dependencias en `requirements.txt`, manteniendo estrictamente intactos los 17 archivos preexistentes en la raíz, `backend/` y `motor-ia/`.
- **Detalle técnico**:
  1. Extraer e incorporar los 17 archivos de la rama `origin/mototradis-mvp`:
     - Paquete `src/`: `__init__.py`, `config.py`, `schemas.py`, `database.py`, `checkpoints.py`, `publishers.py`, `gemma.py`, `nodes.py`, `graph.py`.
     - Carpeta `scripts/`: `run_hitl.py`, `run_mass.py`, `reset_thread.py`.
     - Carpeta `docs/`: `contrato-pipeline.md`, `informe_archivos.md`, `leeme.md`.
     - Raíz: `app_demo.py` y `.env.example`.
  2. Actualizar el archivo `requirements.txt` en la raíz para incluir las dependencias requeridas por el pipeline de LangGraph de Enoc:
     - `langgraph>=0.2.0`
     - `langgraph-checkpoint-postgres>=2.0.0`
     - `psycopg[binary,pool]>=3.2.0`
     - `supabase>=2.0.0`
     - `json-repair>=0.30.0`
     - `tweepy>=4.14.0`
     - `nest-asyncio>=1.6.0`
     - `google-genai>=1.0.0`
  3. Ejecutar `git status` y verificar que los 17 archivos preexistentes en la raíz (`api.py`, `base_datos.py`, `modelos.py`, `evaluador_lotes.py`, `anuncios_discord.py`, `app.py`, etc.) y las carpetas `backend/` y `motor-ia/` permanezcan sin modificación.
- **Hecho cuando**: Los 17 archivos de Enoc están presentes en el árbol de trabajo, las dependencias están agregadas en `requirements.txt`, y `git diff --exit-code <archivos_raiz>` certifica cero alteraciones en los archivos preexistentes.

---

### [x] Tarea 2: Fase Red TDD — Tests Automatizados en `tests/test_unificacion_motor_ia.py` (RF-02, RF-03, RF-04, RF-05, RF-07)
- **Estimación**: ~20 minutos
- **Requerimientos**: RF-02, RF-03, RF-04, RF-05, RF-07
- **Descripción**: Diseñar e implementar la batería de pruebas automatizadas en `tests/test_unificacion_motor_ia.py` que especifiquen los contratos de API, la trazabilidad de modelos de IA, la soberanía HITL, la cascada de Discord y la resiliencia de checkpointer antes de escribir la lógica en el backend.
- **Detalle técnico**:
  1. Diseñar `test_homologacion_entorno_y_checkpointer_resiliente`:
     - Verifica que la homologación de variables (`GOOGLE_API_KEY` $\rightarrow$ `GEMINI_API_KEY`, `DATABASE_URL` $\rightarrow$ `SUPABASE_DB_URL`) ocurra sin excepciones.
     - Verifica que ante la ausencia de conexión PostgreSQL externa, `obtener_checkpointer_resiliente()` devuelva una instancia funcional de `MemorySaver` en memoria sin romper la ejecución.
  2. Diseñar `test_mototradis_checkpoint_desacoplado_pendiente`:
     - Invoca `GET /api/v1/mototradis/checkpoint/{id}` para un mensaje sin checkpoint ni historial.
     - Verifica respuesta HTTP 200 con `has_checkpoint: false`, `estado_pipeline: "pendiente"` y `borradores_ui: {}`, desacoplado de `lotes_ia_kpis`.
  3. Diseñar `test_mototradis_execute_pipeline_y_trazabilidad_modelos`:
     - Mockea o ejecuta `POST /api/v1/mototradis/execute-pipeline` para un mensaje válido.
     - Verifica respuesta HTTP 200 con `estado_pipeline: "procesado"`, `borradores_ui` con estructura uniforme (`linkedin`, `x`, `discord`) y el mapa `modelos_utilizados` detallando los modelos de IA exactos (Orquestador, LinkedIn, X, Discord).
  4. Diseñar `test_mototradis_hitl_soberania_humana_y_publicacion`:
     - Invoca `POST /api/v1/mototradis/hitl-decision` enviando `decision: "aprobar"` y `copys_editados` modificados manualmente.
     - Verifica que los textos suministrados al despachador sean los editados por el humano y que la respuesta reporte `resultados_canales` tolerando credenciales opcionales ausentes de X/LinkedIn sin arrojar error HTTP 500.
  5. Diseñar `test_mototradis_hitl_precondicion_sin_borradores`:
     - Intenta aprobar un lote sin borradores ni checkpoint previo.
     - Verifica que la API responda con código HTTP 400 Bad Request y mensaje explicativo.
  6. Diseñar `test_mototradis_hitl_desaprobar_y_limpieza_checkpoint`:
     - Invoca `POST /api/v1/mototradis/hitl-decision` con `decision: "desaprobar"`.
     - Verifica que marque `estado_revision: "desaprobado"` y confirme la purga del hilo (`checkpoint_limpiado: true`).
  7. Diseñar `test_mototradis_run_mass_gemma_trazabilidad`:
     - Invoca `POST /api/v1/mototradis/run-mass`.
     - Verifica que responda con `modelo_ia: "Google Gemma 4 · gemma-4-31b-it"` y métricas de procesamiento masivo.
- **Hecho cuando**: Los nuevos tests están escritos en `tests/test_unificacion_motor_ia.py` y fallan de manera predecible con código HTTP 404 (Fase Red) al no existir aún los endpoints en `puente_motor_ia.py`, sin quebrar los 113 tests existentes del proyecto.

---

### [x] Tarea 3: Fase Green Backend — Adaptador Mototradis, Checkpointer Resiliente y Trazabilidad de Modelos IA en `puente_motor_ia.py` (RF-02, RF-03)
- **Estimación**: ~20 minutos
- **Requerimientos**: RF-02, RF-03
- **Descripción**: Implementar en `puente_motor_ia.py` la homologación de entorno, la fábrica de checkpointer resiliente (`PostgresSaver` con fallback a `MemorySaver`), el rastreo de modelos de IA (`modelos_utilizados`), y los endpoints `GET /checkpoint/{id}`, `POST /execute-pipeline` y `POST /generate-channel`.
- **Detalle técnico**:
  1. Homologación de variables de entorno antes de importar `src`:
     - Mapear `GOOGLE_API_KEY` a `GEMINI_API_KEY` y `DATABASE_URL` a `SUPABASE_DB_URL`.
     - Encapsular la importación de `src.config` y `src.graph` con manejo preventivo de excepciones.
  2. Implementar `obtener_checkpointer_resiliente()`:
     - Evalúa conectividad PostgreSQL; si falla o no está configurada, instancia y retorna `MemorySaver()`.
  3. Implementar el mapa de trazabilidad `modelos_utilizados`:
     - Registrar por defecto:
       * `orquestador`: `Groq · qwen/qwen3.8-27b` (Fallback: `Google Gemini · gemini-3.6-flash`).
       * `linkedin`: `Google Gemini · gemini-3.5-flash-lite` (Fallback: `gemini-3.1-flash-lite`).
       * `x`: `Groq · qwen/qwen3.8-27b` / `Google Gemini · gemini-3.5-flash-lite`.
       * `discord`: `Groq · openai/gpt-oss-120b` (Fallback: `gemini-3.1-flash-lite`).
       * `pqrs`: `Groq · qwen/qwen3.8-27b` (Fallback: `Google Gemini · gemini-3.5-flash-lite`).
       * `masivo`: `Google Gemma 4 · gemma-4-31b-it`.
  4. Implementar `GET /api/v1/mototradis/checkpoint/{id_mensaje}`:
     - Consultar historial en Supabase; si existe $\rightarrow$ `estado_pipeline = "aprobado"`.
     - Si no, consultar checkpoint; si no existe $\rightarrow$ `has_checkpoint = false`, `estado_pipeline = "pendiente"`.
     - Si existe $\rightarrow$ retornar `borradores_ui` aplanado junto a `modelos_utilizados` y `copys_generados`.
  5. Implementar `POST /api/v1/mototradis/execute-pipeline`:
     - Construir el grafo mediante `build_graph(checkpointer=checkpointer, interrupt_before=["publicador"])`.
     - Cargar datos del mensaje, ejecutar hasta la pausa HITL, persistir checkpoint y actualizar `lotes_ia_kpis` a `procesado`.
     - Retornar `borradores_ui`, `modelos_utilizados` y `rutas_activas`.
  6. Implementar `POST /api/v1/mototradis/generate-channel`:
     - Invocar el nodo individual para el canal seleccionado con el modelo provisto.
     - Retornar el contenido generado y la clave `modelo_utilizado`.
- **Hecho cuando**: Los tests unitarios de homologación, checkpoints, ejecución de pipeline y generación por canal pasan a verde (`pytest tests/test_unificacion_motor_ia.py`).

---

### [x] Tarea 4: Fase Green Backend — Soberanía HITL, Publicación Multicanal, Cascada Discord y Procesamiento Masivo Gemma en `puente_motor_ia.py` (RF-04, RF-05)
- **Estimación**: ~20 minutos
- **Requerimientos**: RF-04, RF-05
- **Descripción**: Implementar en `puente_motor_ia.py` los endpoints de decisión humana HITL con inyección prioritaria de textos editados, la cascada jerárquica de 3 niveles para Discord con cita en bloque, la tolerancia a credenciales de redes opcionales, y el procesamiento masivo autónomo de baja relevancia con Gemma 4.
- **Detalle técnico**:
  1. Implementar `POST /api/v1/mototradis/hitl-decision`:
     - Validar precondición: Si `decision == 'aprobar'` y no hay copys en payload ni checkpoint, responder HTTP 400 Bad Request.
     - Soberanía humana: Si se envían `copys_editados`, actualizar el estado del hilo (`checkpointer.update_state`) y suministrar directamente estos textos al publicador para garantizar que jamás se sobreescriban con borradores previos.
     - Tolerancia a credenciales opcionales: Invocar despachadores capturando faltantes de `X_API_KEY` o `LINKEDIN_ACCESS_TOKEN`, retornando el desglose `resultados_canales` sin arrojar error HTTP 500.
     - Persistir en `public.historial_reportes_semanales`, actualizar `lotes_ia_kpis` a `aprobado` y registrar en SQLite `contenidos_generados`.
     - Si `decision == 'desaprobar'`, actualizar `lotes_ia_kpis` a `desaprobado` y ejecutar `limpiar_checkpoint_hilo`.
  2. Implementar la Cascada Jerárquica de 3 Niveles para Discord con Cita en Bloque:
     - Formatear el prefijo de contexto: `> 💬 **Contexto de @{autor}:** *"{texto_snippet}"*\n\n`.
     - Nivel 1: Webhook específico del canal (`DISCORD_WEBHOOK_GENERAL`, `DISCORD_WEBHOOK_FAQ`, etc.).
     - Nivel 2: Webhook general (`DISCORD_WEBHOOK_ANUNCIOS`).
     - Nivel 3: Bot Oficial de Discord (`DISCORD_TOKEN` / `DISCORD_BOT_TOKEN`) hacia el canal oficial canónico.
  3. Implementar `POST /api/v1/mototradis/publish-channel`:
     - Publicar directamente el contenido recibido en `datos_canal` desde el editor en la plataforma indicada.
  4. Implementar `POST /api/v1/mototradis/run-mass`:
     - Ejecutar el flujo de `scripts/run_mass.py` para mensajes pendientes con relevancia $< 35$.
     - Despachar mensajes útiles a Discord con cita del autor y descartar spam.
     - Retornar resumen de procesados con `modelo_ia: "Google Gemma 4 · gemma-4-31b-it"`.
- **Hecho cuando**: El 100% de los tests de backend nuevos y preexistentes en `tests/test_unificacion_motor_ia.py` pasan en verde.

---

### [x] Tarea 5: Frontend — Cliente Tipado en `frontend/src/api/contentWorkflow.ts` con Trazabilidad de Modelos IA y Checkpoints (RF-03, RF-04, RF-05)
- **Estimación**: ~20 minutos
- **Requerimientos**: RF-03, RF-04, RF-05
- **Descripción**: Actualizar `frontend/src/api/contentWorkflow.ts` con interfaces TypeScript completas y métodos de llamada para consumir los endpoints de Mototradis con soporte de checkpoints, soberanía HITL y trazabilidad explícita de modelos de IA.
- **Detalle técnico**:
  1. Declarar las interfaces TypeScript:
     - `MototradisUiDrafts`: Estructura plana para LinkedIn, X y Discord.
     - `MototradisCheckpointResponse`: Soporte de `has_checkpoint`, `estado_pipeline`, `modelos_utilizados`, `borradores_ui`.
     - `MototradisExecuteResponse`: Soporte de `rutas_activas`, `modelos_utilizados`, `borradores_ui`.
     - `MototradisHitlResponse`: Soporte de `resultados_canales`, `checkpoint_limpiado`.
     - `MototradisRunMassResponse`: Soporte de `procesados`, `publicados_directo`, `descartados`, `modelo_ia`.
  2. Implementar funciones tipadas con manejo de errores y fallbacks seguros:
     - `getMototradisCheckpoint(messageId: number)`
     - `executeMototradisPipeline(messageId: number, provider?: string)`
     - `generateMototradisChannel(messageId: number, channel: string, provider?: string)`
     - `publishMototradisChannel(messageId: number, channel: string, channelData: any)`
     - `submitMototradisHitlDecision(messageId: number, decision: 'aprobar' | 'desaprobar', editedDrafts?: MototradisUiDrafts)`
     - `runMototradisMassGemma(limit?: number)`
- **Hecho cuando**: Las interfaces y funciones están exportadas y compiladas sin errores de TypeScript en el cliente del frontend.

---

### [x] Tarea 6: Frontend — Integración en `ContentStudio.tsx` con Insignias de Modelos IA en Cada Tarjeta, Editores y Barra HITL (RF-06)
- **Estimación**: ~20 minutos
- **Requerimientos**: RF-06
- **Descripción**: Integrar la mesa de trabajo de `ContentStudio.tsx` preservando intactos los paneles existentes de Anuncios y Quejas, e incorporando insignias visibles del modelo de IA en cada tarjeta y componente, editores multicanal, contador de caracteres en X, vista previa de Discord y barra de decisión global HITL.
- **Detalle técnico**:
  1. Preservar completamente las secciones de Anuncios Oficiales (`anuncios_discord.py`) y Soporte a Quejas / PQRS.
  2. Mesa de Trabajo Principal:
     - Mostrar insignia de estado del pipeline desacoplada (`⏳ Pendiente de ejecutar pipeline`, `⚙️ Procesado / En revisión HITL`, `✅ Aprobado / Publicado`).
     - **Insignia visible del Orquestador**: Exhibir en el encabezado el modelo de IA que realizó el enrutamiento (ej. `Orquestador IA: Google Gemini · gemini-3.6-flash` o el reportado en `modelos_utilizados.orquestador`).
     - Botón principal "Ejecutar Pipeline Mototradis (Orquestador IA)" con feedback visual de carga.
     - Carga automática de checkpoint al seleccionar un mensaje en la bandeja o navegar mediante `/content?interaction=ID` con desplazamiento suave.
  3. Tarjetas Multicanal con **Insignia Visible de Modelo IA en Cada Una**:
     - **Tarjeta LinkedIn**:
       * Badge destacado: `Modelo IA: Google Gemini · gemini-3.5-flash-lite` (o el reportado en `modelos_utilizados.linkedin`).
       * Campos editables para Título y Copy persuasivo.
       * Secciones plegables para Copy de tono, Newsletter y Sugerencia FAQ.
       * Botón directo "Publicar en LinkedIn", botón "Regenerar" con selector de modelo IA y botón "Copiar".
     - **Tarjeta X (Twitter)**:
       * Badge destacado: `Modelo IA: Groq · qwen/qwen3.8-27b` (o el reportado en `modelos_utilizados.x`).
       * Campos editables para Título/Hook y Tweet.
       * Contador dinámico sobre `{titulo}\n\n{texto_copy}` vs 280 caracteres técnicos con alerta de color.
       * Botón directo "Publicar en X", botón "Regenerar" y botón "Copiar".
     - **Tarjeta Discord**:
       * Badge destacado: `Modelo IA: Groq · openai/gpt-oss-120b` (o Gemini para soporte PQRS).
       * Selector de canal (`#general`, `#faq`, `#notificaciones`).
       * Campos editables para Título y Cuerpo del post.
       * **Vista previa visual en vivo** de la cita en bloque: `> 💬 Contexto de @autor: "..."`.
       * Botón directo "Publicar en Discord", botón "Regenerar" y botón "Copiar".
  4. Barra de Decisión Global HITL:
     - Botón "✅ Aprobar y Publicar todo (HITL)" que despacha el lote inyectando las ediciones manuales.
     - Botón "❌ Desaprobar lote y limpiar checkpoint" que descarta y limpia el hilo.
     - Botón "⚡ Procesar cola de baja relevancia (< 35) con Gemma 4 (gemma-4-31b-it)" que despliega un diálogo modal con badge destacado del modelo ejecutor y reporte estadístico.
- **Hecho cuando**: La pantalla `/content` renderiza todas las insignias de modelos de IA solicitadas por el usuario, permite ejecutar el pipeline, editar y publicar los borradores con plena soberanía humana, y la barra HITL funciona de extremo a extremo.

---

### [x] Tarea 7: Verificación Global, Compilación Limpia e Inviolabilidad Constitucional (RF-07)
- **Estimación**: ~20 minutos
- **Requerimientos**: RF-07
- **Descripción**: Ejecutar la verificación integral de pruebas unitarias y de integración de backend, compilación sin errores de TypeScript en el frontend y verificación Git de inmutabilidad estricta sobre el código constitucional protegido.
- **Detalle técnico**:
  1. Ejecutar la suite completa de pruebas: `pytest tests/ -v`, validando que el 100% de los tests (preexistentes y nuevos) pasen en verde.
  2. Ejecutar la compilación del frontend en `frontend/`: `npm run build`, certificando cero errores y cero advertencias de TypeScript.
  3. Ejecutar la auditoría Git de inmutabilidad:
     - `git diff --exit-code api.py base_datos.py modelos.py evaluador_lotes.py anuncios_discord.py app.py`
     - `git diff --exit-code backend motor-ia`
     garantizando que ninguno de los 17 archivos preexistentes en la raíz ni las carpetas protegidas hayan sido alterados.
- **Hecho cuando**: El 100% de los tests pasa en verde, el frontend compila sin errores y git status certifica que los 17 archivos protegidos de la raíz y las carpetas legadas se mantuvieron completamente inmutables.
