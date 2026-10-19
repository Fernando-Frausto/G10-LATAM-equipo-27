# Spec 015: Integración del Pipeline Mototradis MVP de Enoc con Backend y Redacción de Contenidos

## 1. Contexto y Propósito (QUÉ y POR QUÉ)

### ¿Qué se solicita?
Integrar de manera completa y funcional el motor de transformación y distribución digital (**Mototradis MVP**) desarrollado por Enoc en la rama `origin/mototradis-mvp` (commit `23699cf`) dentro del ecosistema unificado de CloudEdTech:

1. **Incorporación Limpia de Componentes y Dependencias**:
   - Incorporar en la rama de trabajo los 17 archivos nuevos desarrollados por Enoc:
     - Paquete `src/`: `__init__.py`, `config.py`, `schemas.py`, `database.py`, `checkpoints.py`, `publishers.py`, `gemma.py`, `nodes.py` y `graph.py`.
     - Carpeta `scripts/`: `run_hitl.py`, `run_mass.py` y `reset_thread.py`.
     - Documentación y utilidades: `app_demo.py`, `.env.example`, `docs/contrato-pipeline.md`, `docs/informe_archivos.md` y `docs/leeme.md`.
     - Dependencias de `requirements.txt`: incorporar las librerías especializadas del pipeline (`langgraph`, `langgraph-checkpoint-postgres`, `psycopg[binary,pool]`, `supabase`, `json-repair`, `tweepy`, `nest-asyncio`, `google-genai[aiohttp]`) asegurando compatibilidad con el entorno local y de producción.

2. **Homologación de Entorno, Resiliencia de Checkpointer y Trazabilidad de Modelos en el Puente (`puente_motor_ia.py`)**:
   - Garantizar que `GEMINI_API_KEY` se inicialice automáticamente a partir de `GOOGLE_API_KEY` en caso de no encontrarse definida explícitamente, y que `SUPABASE_DB_URL` tome el valor de `DATABASE_URL` como respaldo (*fallback*), evitando excepciones de importación o fallos al cargar `src/config.py` y `src/gemma.py`.
   - **Resiliencia de Checkpointer**: Si la conexión con `PostgresSaver` hacia Supabase no está disponible (por ejemplo, en tests locales desconectados), conmutar automáticamente a `MemorySaver` en memoria para no quebrar la ejecución.
   - **Trazabilidad Explícita del Modelo de IA Utilizado**: Registrar y retornar en todas las etapas del pipeline el mapa `modelos_utilizados` detallando el nombre exacto del modelo que realizó cada tarea (`orquestador`, `linkedin`, `x`, `discord`, `pqrs`, `masivo`), indicando tanto el modelo configurado como el modelo efectivo si se activó algún fallback de resiliencia (`Groq Llama 3.3`, `Google Gemini 2.5 Flash Lite`, `Google Gemma 4`).
   - Preservar con rigurosidad los esquemas Pydantic de `src/schemas.py` (`RouterOutput`, `RespuestaComunidadLinkedin`, `RespuestaComunidadX`, `RespuestaComunidadDiscord`, `RespuestaComunidadPQRS`).

3. **Orquestación LangGraph, Recuperación de Checkpoints y Normalización Uniforme**:
   - Exponer en `puente_motor_ia.py` endpoints para consultar el estado del pipeline y ejecutar el flujo de LangGraph para cualquier interacción seleccionada:
     - **Desacoplamiento del Estado del Pipeline frente al Triaje Inicial**: Si el mensaje no cuenta con un checkpoint en `public.checkpoints` (`has_checkpoint: false`) ni registro en `public.historial_reportes_semanales`, el estado del pipeline Mototradis para la interfaz de redacción debe reportarse estrictamente como `pendiente` (*"⏳ Pendiente de ejecutar pipeline"*), independientemente de que en `lotes_ia_kpis` su `estado_revision` figure como `aprobado` por el triaje inicial de IA. Si ya se encuentra en `public.historial_reportes_semanales`, su estado debe ser `aprobado` (*"✅ Publicado"*).
     - Ejecutar bajo demanda el grafo de LangGraph compilado con pausa antes de publicación (`interrupt_before=["publicador"]`), activando el Orquestador inteligente (`nodo_orquestador`) con su matriz de cuatro prioridades:
       * Relevancia $\ge 70$: flujo multicanal (LinkedIn, X, Discord).
       * Relevancia $35 - 69$: canalización hacia Discord con revisión humana (HITL).
       * Relevancia $11 - 34$: automatización mediante Gemma 4.
       * Relevancia $\le 10$ o spam: descarte técnico automático (`desaprobado`).
     - Almacenar el estado intermedio en los checkpoints (`thread_id = sesion_{id_mensaje}`) y actualizar el estado a `procesado` en `public.lotes_ia_kpis`.
     - **Normalización Estructural Uniforme (`borradores_ui`)**: En las respuestas de consulta de checkpoints, ejecución del pipeline y regeneración por canal, incluir junto al objeto canónico `copys_generados` un objeto aplanado y predecible `borradores_ui` adaptado al consumo del frontend, acompañado del mapa `modelos_utilizados`.
     - **Armonización de Caracteres en X**: La generación de IA (`nodo_x`) persigue metas óptimas de `titulo <= 70` caracteres y `texto_copy <= 210` caracteres, mientras que el editor del frontend y el despachador validan que el tweet combinado (`{titulo}\n\n{texto_copy}`) no supere el límite estricto de 280 caracteres de la API de X.

4. **Soberanía Humana (HITL), Publicación Multicanal y Cascada de Respaldo**:
   - **Soberanía Humana Absoluta sobre Ediciones Manuales**:
     * En `POST /api/v1/mototradis/hitl-decision`, antes de reanudar el grafo o despachar publicaciones, inyectar los textos editados por el operador humano (`copys_editados`) en el estado del checkpoint (`update_state`) y suministrarlos directamente a las funciones de publicación, garantizando que SIEMPRE se despache el contenido final editado por el usuario en la interfaz y NUNCA se sobreescriba con el borrador generado previo.
     * En `POST /api/v1/mototradis/publish-channel`, publicar estrictamente el contenido recibido en `datos_canal` desde el editor activo.
   - **Tolerancia a Credenciales Opcionales y Reporte Detallado**:
     * Si faltan credenciales opcionales de X (`X_API_KEY`) o LinkedIn (`LINKEDIN_ACCESS_TOKEN`), la API no debe arrojar HTTP 500, sino reportar un desglose detallado `resultados_canales` indicando qué canales se publicaron en vivo y cuáles requieren configurar credenciales en `.env`, registrando el lote en el historial cuando al menos la red principal (Discord) o el almacenamiento se complete con éxito.
   - **Cascada Jerárquica para Discord con Citas de Contexto**:
     * Aplicar formalmente tres niveles de envío para Discord con citación en bloque (`> 💬 **Contexto de @autor:** *"{texto}"*`):
       1. Webhook específico del canal (`DISCORD_WEBHOOK_GENERAL`, `DISCORD_WEBHOOK_FAQ`, `DISCORD_WEBHOOK_NOTIFICACIONES`, `DISCORD_WEBHOOK_PQRS`).
       2. Webhook general configurado en el servidor (`DISCORD_WEBHOOK_ANUNCIOS`).
       3. Bot Oficial de Discord (`DISCORD_TOKEN` / `DISCORD_BOT_TOKEN`) hacia el canal oficial canónico.
   - **Precondición de Aprobación**: Si se intenta aprobar un lote sin borradores ni en el payload ni en el checkpoint, retornar código HTTP 400 Bad Request.
   - **Desaprobación y Limpieza**: Actualizar `estado_revision = 'desaprobado'` y purgar el hilo mediante `limpiar_checkpoint_hilo("sesion_{id_mensaje}")`.

5. **Procesamiento Masivo Autónomo de Baja Relevancia con Gemma 4 y Trazabilidad**:
   - Exponer un endpoint en `puente_motor_ia.py` para disparar bajo demanda el flujo masivo de `scripts/run_mass.py` (`obtener_lotes_pendientes_masivos` y `nodo_gemma_automatico` para interacciones con relevancia $< 35$), identificando explícitamente el modelo utilizado (`Google Gemma 4 · gemma-4-31b-it`) y retornando la cantidad de lotes procesados, publicados automáticamente o descartados.

6. **Integración Viva y Visibilidad de Modelos de IA en `ContentStudio.tsx`**:
   - Preservar al 100% las secciones existentes: "Panel de Anuncios Oficiales de la Comunidad (Discord Webhook)" y "Panel de Quejas, Reclamos y Soporte Crítico".
   - **Insignias Visibles de Modelo de IA en Cada Componente / Tarjeta**:
     * **Orquestador de Rutas**: Badge visible indicando el modelo utilizado para la orquestación (ej. `Orquestador IA: Google Gemini · gemini-3.6-flash` o el fallback efectivo).
     * **Tarjeta LinkedIn**: Badge visible indicando el modelo de IA que redactó el post (ej. `Modelo IA: Google Gemini · gemini-3.6-flash` o el modelo seleccionado/efectivo).
     * **Tarjeta X (Twitter)**: Badge visible indicando el modelo de IA que redactó el tweet (ej. `Modelo IA: Groq · qwen/qwen3.8-27b` o el modelo seleccionado/efectivo).
     * **Tarjeta Discord / Soporte PQRS**: Badge visible indicando el modelo de IA que redactó la respuesta (ej. `Modelo IA: Groq · openai/gpt-oss-120b` para comunidad o `Google Gemini · gemini-3.5-flash-lite` para PQRS).
     * **Panel de Procesamiento Masivo (< 35)**: Badge visible indicando el modelo ejecutor (`Modelo IA: Google Gemma 4 · gemma-4-31b-it`).
   - Botón principal "Ejecutar Pipeline Mototradis (Orquestador IA)" que ejecute el grafo de LangGraph, con recuperación automática de checkpoints preexistentes al seleccionar cualquier mensaje.
   - Tarjetas enriquecidas multicanal (LinkedIn con Título, Copy persuasivo, Copy de tono y extras; X con editor dinámico validando $\le 280$ caracteres combinados; Discord con selector de canal `#general`/`#faq`/`#notificaciones` y vista previa en vivo de la cita en bloque), con botones directos de publicación individual.
   - Barra de Decisión Global HITL ("Aprobar y Publicar todo (HITL)", "Desaprobar lote y limpiar checkpoint" y modal "Procesar cola de baja relevancia con Gemma 4").

7. **Inviolabilidad Constitucional y Calidad TDD**:
   - Cero modificaciones a los 17 archivos preexistentes en la raíz, `backend/` y `motor-ia/`.
   - Mantener intactos los archivos de Enoc en `src/`, resolviendo adaptaciones o fallbacks de forma desacoplada desde `puente_motor_ia.py`.
   - Validar la integración mediante tests automatizados en `tests/` que garanticen el 100% de la suite en verde y compilación limpia del frontend (`npm run build`).

### ¿Por qué es necesario?
1. **Transparencia Total de Inteligencia Artificial para el Usuario**: El usuario solicitó expresamente saber con exactitud qué modelo de IA está realizando o realizó cada acción (*"quiero que en cada cosa diga el modelo de ia que esta utilizando para realizarla"*). Mostrar insignias visibles e inequívocas en cada tarjeta y panel (Orquestador, LinkedIn, X, Discord, PQRS y procesamiento masivo) brinda confianza técnica, trazabilidad editorial y claridad sobre qué cerebro produjo cada contenido.
2. **Soberanía Humana Inquebrantable (HITL)**: La premisa angular del Human-In-The-Loop es que las modificaciones que un redactor humano introduce sobre el borrador de la IA son soberanas y constituyen la verdad final que debe viajar a las redes sociales. Descartar el borrador viejo del checkpoint e inyectar las ediciones manuales en el despachador garantiza fidelidad absoluta.
3. **Claridad del Estado Operativo y Desacoplamiento**: Separar el estado del pipeline Mototradis (`pendiente` si no tiene checkpoint ni publicación) elimina falsos positivos de mensajes marcados como aprobados en el triaje inicial de Colab/Supabase.
4. **Consistencia de Datos en el Frontend**: Exponer `borradores_ui` estandarizado junto a `modelos_utilizados` simplifica la reactividad de `ContentStudio.tsx`, evitando conversiones frágiles en cada componente.
5. **Resiliencia Operativa ante Entornos Heterogéneos**: Soportar publicación parcial con desglose transparente y utilizar respaldos en cascada previene bloqueos en entornos de prueba o despliegues parciales.
6. **Cumplimiento de la Constitución del Proyecto**: El código legado permanece congelado. La unificación se realiza mediante adaptadores limpios en `puente_motor_ia.py` y pruebas TDD.

---

## 2. Requerimientos Funcionales (Formato EARS)

### RF-01: Incorporación Íntegra de la Rama mototradis-mvp y Dependencias
- **CUANDO** se sincronice la rama de trabajo con `origin/mototradis-mvp`, **EL SISTEMA DEBERÁ** incorporar la totalidad de los archivos del paquete `src/` (`__init__.py`, `config.py`, `schemas.py`, `database.py`, `checkpoints.py`, `publishers.py`, `gemma.py`, `nodes.py`, `graph.py`), de la carpeta `scripts/` (`run_hitl.py`, `run_mass.py`, `reset_thread.py`), de `docs/` (`contrato-pipeline.md`, `informe_archivos.md`, `leeme.md`), `app_demo.py` y `.env.example`.
- **MIENTRAS** se incorporen dichos archivos, **EL SISTEMA DEBERÁ** mantener estrictamente inalterados los 17 archivos preexistentes en la raíz (`api.py`, `base_datos.py`, `evaluador_lotes.py`, `anuncios_discord.py`, `app.py`, etc.), así como las carpetas `backend/` y `motor-ia/`.
- **EL SISTEMA DEBERÁ** actualizar el archivo `requirements.txt` de la raíz para incluir las librerías necesarias del pipeline (`langgraph`, `langgraph-checkpoint-postgres`, `psycopg[binary,pool]`, `supabase`, `json-repair`, `tweepy`, `nest-asyncio`, `google-genai[aiohttp]`) asegurando que la instalación de dependencias no genere conflictos en el entorno local.

### RF-02: Homologación de Entorno, Resiliencia de Checkpointer y Trazabilidad de Modelos de IA
- **MIENTRAS** el servidor inicialice o importe el módulo `puente_motor_ia.py`, **EL SISTEMA DEBERÁ** homologar las variables de entorno requeridas por `src/config.py`:
  1. Si `GEMINI_API_KEY` no se encuentra definida en el entorno, asignar automáticamente el valor de `GOOGLE_API_KEY`.
  2. Si `SUPABASE_DB_URL` no se encuentra definida, asignar automáticamente el valor de `DATABASE_URL`.
- **SI** la conexión a PostgreSQL con `PostgresSaver` falla o no está disponible en el entorno (por ejemplo, en tests unitarios locales desconectados), **EL SISTEMA DEBERÁ** instanciar automáticamente `MemorySaver` en memoria como checkpointer de respaldo, garantizando la continuidad operativa sin fallos de inicio.
- **SI** las credenciales críticas indispensables continúan ausentes tras evaluar los respaldos, **EL SISTEMA DEBERÁ** registrar una advertencia descriptiva en el registro de eventos (*logs*) y degradar a modo simulación controlada sin abortar la ejecución del servidor.
- **MIENTRAS** se invoquen los nodos de generación y validación de `src/nodes.py`, **EL SISTEMA DEBERÁ** garantizar respaldo automático (*fallback*) hacia los tres modelos LLM activos del proyecto (`Groq Llama 3.3`, `Google Gemini 2.5 Flash Lite`, `Google Gemma 4`), previniendo caídas por modelos no disponibles o cuotas agotadas.
- **EL SISTEMA DEBERÁ** registrar en cada paso del flujo el modelo de IA exacto que ejecutó la inferencia y retornarlo en el mapa `modelos_utilizados`:
  - `orquestador`: Modelo utilizado para el enrutamiento (ej. `Google Gemini · gemini-3.6-flash` o `Groq Llama 3.3`).
  - `linkedin`: Modelo utilizado para el copy de LinkedIn (ej. `Google Gemini · gemini-3.6-flash`).
  - `x`: Modelo utilizado para el tweet de X (ej. `Groq · qwen/qwen3.8-27b` o `Groq Llama 3.3`).
  - `discord`: Modelo utilizado para Discord comunidad (ej. `Groq · openai/gpt-oss-120b` o `Groq Llama 3.3`).
  - `pqrs`: Modelo utilizado para respuesta a reclamos (ej. `Google Gemini · gemini-3.5-flash-lite`).
  - `masivo`: Modelo utilizado para la cola de baja relevancia (`Google Gemma 4 · gemma-4-31b-it`).
- **EL SISTEMA DEBERÁ** asegurar que todas las salidas generadas preserven estrictamente los esquemas Pydantic tipados de `src/schemas.py` (`RouterOutput`, `RespuestaComunidadLinkedin`, `RespuestaComunidadX`, `RespuestaComunidadDiscord`, `RespuestaComunidadPQRS`).

### RF-03: Orquestación LangGraph, Recuperación de Checkpoints y Normalización Uniforme
- **CUANDO** el cliente consulte el estado de un mensaje en el pipeline mediante `GET /api/v1/mototradis/checkpoint/{id_mensaje}`, **EL SISTEMA DEBERÁ** evaluar la existencia de registros en `public.checkpoints` (`thread_id = sesion_{id_mensaje}`) y en `public.historial_reportes_semanales`.
- **SI** el mensaje no posee registros en los checkpoints de LangGraph (`has_checkpoint: false`) ni en el historial de reportes semanales, **EL SISTEMA DEBERÁ** reportar el estado del pipeline como `pendiente` (*"⏳ Pendiente de ejecutar pipeline"*), desacoplándolo de cualquier valor previo de `estado_revision` asignado en `lotes_ia_kpis` durante el triaje inicial.
- **SI** el mensaje ya cuenta con registro en `public.historial_reportes_semanales`, **EL SISTEMA DEBERÁ** reportar el estado como `aprobado` (*"✅ Publicado"*).
- **SI** se localiza un checkpoint activo en `public.checkpoints`, **EL SISTEMA DEBERÁ** reportar `procesado` (*"⚙️ Procesado / En revisión HITL"*), retornando los borradores estructurados originales, el objeto normalizado `borradores_ui` y el mapa `modelos_utilizados`.
- **EL SISTEMA DEBERÁ** incluir en las respuestas de consulta de checkpoints, ejecución del pipeline y regeneración de canales, el objeto normalizado `borradores_ui` con estructura plana y predecible:
  - `linkedin`: `{ titulo, texto_copy, copy_tono, newsletter, faq }`
  - `x`: `{ titulo, texto_copy }`
  - `discord`: `{ canal_seleccionado, titulo, texto_copy }`
  junto con `modelos_utilizados` identificando qué modelo generó cada uno de ellos.
- **CUANDO** el usuario solicite la ejecución del pipeline para un mensaje mediante `POST /api/v1/mototradis/execute-pipeline`, **EL SISTEMA DEBERÁ** ensamblar y ejecutar el grafo de LangGraph utilizando `build_graph(checkpointer=..., interrupt_before=["publicador"])`.
- **MIENTRAS** se ejecute el pipeline, **EL SISTEMA DEBERÁ**:
  1. Invocar el `nodo_orquestador` aplicando la matriz de 4 prioridades basada en relevancia y sentimiento.
  2. Distribuir la generación en abanico (*fan-out*) hacia los nodos de los canales correspondientes (`nodo_linkedin`, `nodo_x`, `nodo_discord`, `nodo_reclamos` o `nodo_gemma_automatico`).
  3. Converger en el `nodo_validador` para auditar el tono y la voz de marca CloudEdTech.
  4. Detener la ejecución inmediatamente antes del `nodo_publicador` debido a la pausa HITL programada.
  5. Persistir el estado intermedio en los checkpoints (`thread_id = sesion_{id_mensaje}`).
  6. Actualizar el estado de revisión en `public.lotes_ia_kpis` a `procesado`.
- **CUANDO** se genere o regenere contenido para X (`nodo_x`), **EL SISTEMA DEBERÁ** orientar la inferencia hacia `titulo <= 70` caracteres y `texto_copy <= 210` caracteres, permitiendo que la combinación `{titulo}\n\n{texto_copy}` se mantenga estrictamente dentro de los 280 caracteres técnicos de X.
- **CUANDO** el usuario solicite la regeneración individual de un canal mediante `POST /api/v1/mototradis/generate-channel`, **EL SISTEMA DEBERÁ** invocar el nodo específico con el modelo de IA seleccionado por el usuario (Groq, Gemma 4, Gemini Flash Lite) y retornar tanto el esquema canónico de Enoc como `borradores_ui` y la actualización correspondiente en `modelos_utilizados`.

### RF-04: Soberanía Humana (HITL), Publicación Multicanal y Cascada de Respaldo
- **CUANDO** el usuario confirme la decisión global "Aprobar y Publicar todo (HITL)" mediante `POST /api/v1/mototradis/hitl-decision` con acción `'aprobar'`, **EL SISTEMA DEBERÁ**:
  1. Verificar que existan borradores generados válidos en el payload (`copys_editados`) o en el checkpoint persistido; **SI** no existen borradores, responder con código **HTTP 400 Bad Request** y el mensaje *"No existen borradores para aprobar en este lote"*.
  2. Inyectar de forma prioritaria los textos editados por el humano (`copys_editados`) en el estado del checkpoint (`checkpointer.update_state`), asegurando que las ediciones manuales prevalezcan sobre los borradores algorítmicos previos.
  3. Suministrar los copys editados a las funciones de publicación de `src/publishers.py` para todas las rutas activas (`rutas_activas`).
  4. Registrar el evento en `public.historial_reportes_semanales` con marcas temporales, contenido original, copys finales aprobados y modelos de IA utilizados.
  5. Actualizar `estado_revision = 'aprobado'` en `public.lotes_ia_kpis`.
  6. Sincronizar un registro de auditoría en la tabla SQLite local `contenidos_generados` con formato multicanal y estado `'publicado'`.
- **CUANDO** se despachen publicaciones a Discord (ya sea en publicación individual o global HITL), **EL SISTEMA DEBERÁ** aplicar la siguiente cascada jerárquica:
  1. Webhook específico configurado para el canal destino (`DISCORD_WEBHOOK_GENERAL`, `DISCORD_WEBHOOK_FAQ`, `DISCORD_WEBHOOK_NOTIFICACIONES`, `DISCORD_WEBHOOK_PQRS`).
  2. Webhook general configurado en el servidor (`DISCORD_WEBHOOK_ANUNCIOS`).
  3. Despacho directo vía Bot Oficial de Discord (`DISCORD_TOKEN` / `DISCORD_BOT_TOKEN`) hacia el canal oficial canónico.
- **MIENTRAS** se publique en Discord, **EL SISTEMA DEBERÁ** anteponer la citación formal en bloque del mensaje original del autor (`> 💬 **Contexto de @autor:** *"{texto}"*`).
- **CUANDO** se publique en X mediante `enviar_tweet_x`, **EL SISTEMA DEBERÁ** validar que la suma de título y cuerpo no exceda 280 caracteres, aplicando truncamiento preventivo inteligente si fuera necesario.
- **SI** faltan credenciales opcionales para redes sociales en el entorno (`X_API_KEY`, `LINKEDIN_ACCESS_TOKEN`), **EL SISTEMA DEBERÁ** evitar responder con error HTTP 500, retornando en su lugar el desglose estructurado `resultados_canales` señalando qué plataformas se publicaron en vivo y cuáles requieren configurar credenciales en `.env`, consolidando el estado del lote en `aprobado` si el canal principal (Discord) o el guardado en base de datos concluyó exitosamente.
- **CUANDO** el usuario solicite la publicación individual de un canal mediante `POST /api/v1/mototradis/publish-channel`, **EL SISTEMA DEBERÁ** publicar estrictamente el contenido provisto en `datos_canal` desde el editor activo del frontend.
- **CUANDO** el usuario confirme la decisión "Desaprobar lote y limpiar checkpoint" mediante `POST /api/v1/mototradis/hitl-decision` con acción `'desaprobar'`, **EL SISTEMA DEBERÁ**:
  1. Actualizar `estado_revision = 'desaprobado'` en `public.lotes_ia_kpis`.
  2. Ejecutar `limpiar_checkpoint_hilo("sesion_{id_mensaje}")` para eliminar los registros correspondientes en `public.checkpoints`, `public.checkpoint_blobs` y `public.checkpoint_writes`.
  3. Retornar confirmación de limpieza garantizando que no queden estados residuales del lote.

### RF-05: Procesamiento Masivo Autónomo de Baja Relevancia con Gemma 4 y Trazabilidad
- **CUANDO** el usuario solicite procesar la cola de baja relevancia mediante `POST /api/v1/mototradis/run-mass`, **EL SISTEMA DEBERÁ** ejecutar el flujo autónomo de `scripts/run_mass.py` para los mensajes con relevancia $< 35$.
- **MIENTRAS** se procese la cola masiva, **EL SISTEMA DEBERÁ**:
  1. Consultar lotes pendientes de baja relevancia mediante `obtener_lotes_pendientes_masivos(limite)`.
  2. Procesar cada interacción a través del `nodo_gemma_automatico` empleando explícitamente el motor `Google Gemma 4 · gemma-4-31b-it`.
  3. Clasificar la acción como descarte de spam (`desaprobado`) o publicación directa en canal de soporte (`aprobado`).
  4. Para los mensajes aprobados, despachar la respuesta al canal de Discord correspondiente con la cita del autor.
- **CUANDO** concluya el procesamiento masivo, **EL SISTEMA DEBERÁ** retornar un resumen estadístico detallando la cantidad total de mensajes evaluados, aprobados y descartados, identificando `modelo_ia: "Google Gemma 4 · gemma-4-31b-it"`.

### RF-06: Integración Viva y Visibilidad de Modelos de IA en `ContentStudio.tsx`
- **MIENTRAS** el usuario trabaje en la pestaña de Redacción de Contenidos (`/content`), **EL SISTEMA DEBERÁ** mantener intactos e inalterados el "Panel de Anuncios Oficiales de la Comunidad (Discord Webhook)" y el "Panel de Quejas, Reclamos y Soporte Crítico".
- **CUANDO** el usuario seleccione un mensaje en la bandeja de redacción o ingrese mediante redirección `/content?interaction={id}`, **EL SISTEMA DEBERÁ** consultar de inmediato `GET /api/v1/mototradis/checkpoint/{id_mensaje}` y desplegar los borradores si ya existían, enfocando la tarjeta de "Mensaje original de Discord" con desplazamiento suave.
- **EL SISTEMA DEBERÁ** mostrar en la cabecera de la mesa de trabajo:
  - Una insignia indicadora del estado del pipeline (`⏳ Pendiente de ejecutar pipeline`, `⚙️ Procesado / En revisión HITL`, `✅ Aprobado / Publicado`, `🚫 Desaprobado`).
  - Las rutas activas dictadas por el Orquestador (ej. `[LinkedIn, X, Discord]`).
  - **Insignia visible del Orquestador**: Exhibir el modelo de IA que realizó el enrutamiento (ej. `Orquestador IA: Google Gemini · gemini-3.6-flash` o el modelo efectivo reportado en `modelos_utilizados.orquestador`).
  - Un botón de acción principal "Ejecutar Pipeline Mototradis (Orquestador IA)" que ejecute el pipeline completo sobre el mensaje seleccionado con retroalimentación visual de progreso.
- **MIENTRAS** se rendericen las tarjetas de contenido generado:
  - **Tarjeta LinkedIn**:
    * **Insignia visible de Modelo IA**: Exhibir en la cabecera de la tarjeta una etiqueta destacada con el modelo utilizado (ej. `Modelo IA: Google Gemini · gemini-3.6-flash` o `Groq Llama 3.3`).
    * Campos de entrada editables para "Título del post" y "Copy persuasivo".
    * Visualización desplegable del "Copy de tono CloudEDTech", "Destaque Newsletter Semanal" y "Sugerencia Contenido FAQ".
    * Botón directo "Publicar en LinkedIn", botón "Guardar borrador", botón "Regenerar" con selector de modelo IA y botón "Copiar".
  - **Tarjeta X (Twitter)**:
    * **Insignia visible de Modelo IA**: Exhibir en la cabecera de la tarjeta una etiqueta destacada con el modelo utilizado (ej. `Modelo IA: Groq · qwen/qwen3.8-27b` o `Groq Llama 3.3`).
    * Campos de entrada editables para "Título / Hook" y "Tweet".
    * Contador dinámico de caracteres con advertencia cromática calculada sobre el total del tweet (`{titulo}\n\n{texto_copy}`) respecto a los 280 caracteres permitidos.
    * Botón directo "Publicar en X", botón "Guardar borrador", botón "Regenerar" y botón "Copiar".
  - **Tarjeta Discord**:
    * **Insignia visible de Modelo IA**: Exhibir en la cabecera de la tarjeta una etiqueta destacada con el modelo utilizado (ej. `Modelo IA: Groq · openai/gpt-oss-120b` para comunidad o `Google Gemini · gemini-3.5-flash-lite` para soporte PQRS).
    * Selector de canal de destino (`#general`, `#faq`, `#notificaciones`).
    * Campos editables para "Título" y "Cuerpo del post".
    * Vista previa visual en tiempo real de la cita en bloque del mensaje original del autor (`> 💬 Contexto de @autor`).
    * Botón directo "Publicar en Discord", botón "Guardar borrador", botón "Regenerar" y botón "Copiar".
- **EL SISTEMA DEBERÁ** desplegar una Barra de Decisión Global HITL inmediatamente después de las tarjetas de canales:
  - Botón destacado "✅ Aprobar y Publicar todo (HITL)" que despache el lote con las ediciones manuales activas.
  - Botón "❌ Desaprobar lote y limpiar checkpoint" que marque el lote como desaprobado y limpie su hilo.
  - Botón secundario con **insignia de modelo visible**: "⚡ Procesar cola de baja relevancia (< 35) con Gemma 4 (gemma-4-31b-it)" que abra el diálogo modal para ejecutar el procesamiento masivo bajo demanda.

### RF-07: Inviolabilidad Constitucional, Aislamiento No Invasivo y Verificación TDD
- **MIENTRAS** se implementen todas las conexiones y componentes, **EL SISTEMA DEBERÁ** mantener estrictamente intactos los 17 archivos preexistentes en la raíz del repositorio, así como las carpetas `backend/` y `motor-ia/`.
- **EL SISTEMA DEBERÁ** mantener los archivos de Enoc en `src/` como el paquete canónico del pipeline de LangGraph, realizando todas las adaptaciones, conversiones de tipo y homologación de variables de entorno de forma no invasiva dentro de `puente_motor_ia.py`.
- **EL SISTEMA DEBERÁ** estructurar pruebas automatizadas en `tests/` que validen:
  1. La homologación de variables de entorno y resiliencia de checkpointer (`PostgresSaver` con fallback a `MemorySaver`).
  2. La respuesta correcta de los endpoints del pipeline Mototradis (`checkpoint`, `execute-pipeline`, `publish-channel`, `hitl-decision` y `run-mass`).
  3. La presencia de `modelos_utilizados` identificando con precisión qué IA ejecutó cada componente.
  4. La inyección soberana de copys editados por humanos antes de publicar.
  5. La tolerancia ante credenciales opcionales de redes y la cascada de Discord.
  6. La no regresión de la suite de pruebas completa del proyecto (`pytest tests/ -v`).
  7. La compilación exitosa del frontend (`npm run build`).

---

## 3. Contratos de API y Modelos de Datos

### 3.1 Contratos de API en `puente_motor_ia.py`

#### 1. `GET /api/v1/mototradis/checkpoint/{id_mensaje}`
- **Descripción**: Recupera el estado del pipeline, los borradores generados canónicos, el objeto normalizado `borradores_ui` y el mapa `modelos_utilizados` desde los checkpoints de Supabase (`public.checkpoints`) o `public.historial_reportes_semanales`.
- **Respuesta Exitosa (HTTP 200 OK - Con Checkpoint Existente en Proceso HITL)**:
  ```json
  {
    "has_checkpoint": true,
    "id_mensaje": 15,
    "estado_pipeline": "procesado",
    "estado_revision": "procesado",
    "rutas_activas": ["linkedin", "x", "discord"],
    "modelos_utilizados": {
      "orquestador": "Google Gemini · gemini-3.6-flash",
      "linkedin": "Google Gemini · gemini-3.6-flash",
      "x": "Groq · qwen/qwen3.8-27b",
      "discord": "Groq · openai/gpt-oss-120b"
    },
    "borradores_ui": {
      "linkedin": {
        "titulo": "Virtualización Enterprise: Cómo Reducir la Latencia",
        "texto_copy": "En infraestructura hiperconvergente, cada milisegundo cuenta...",
        "copy_tono": "En CloudEDTech formamos líderes técnicos...",
        "newsletter": { "titular": "Optimización de Latencia en Servidores", "resumen": "Caso práctico de implementación en la comunidad" },
        "faq": { "tema": "Buenas prácticas de despliegue", "origen": "Preguntas frecuentes de infraestructura" }
      },
      "x": {
        "titulo": "TWEET TÉCNICO DE ALTO IMPACTO",
        "texto_copy": "Reducción de latencia del 64% en clústeres empresariales. ¿Cómo optimizas tus nodos? Te leemos en CloudEDTech 🚀"
      },
      "discord": {
        "canal_seleccionado": "#general",
        "titulo": "Optimización de Infraestructura Cloud",
        "texto_copy": "¡Excelente aporte de @danitower! Revisen las recomendaciones compartidas."
      }
    },
    "copys_generados": { "...": "esquema estructurado canónico de Enoc" },
    "origen": "checkpoint_supabase"
  }
  ```

- **Respuesta Sin Checkpoint (HTTP 200 OK - Mensaje no procesado por Mototradis)**:
  ```json
  {
    "has_checkpoint": false,
    "id_mensaje": 15,
    "estado_pipeline": "pendiente",
    "estado_revision": "pendiente",
    "rutas_activas": [],
    "modelos_utilizados": {},
    "borradores_ui": {},
    "copys_generados": {},
    "origen": "sin_datos"
  }
  ```

#### 2. `POST /api/v1/mototradis/execute-pipeline`
- **Descripción**: Ejecuta el grafo de LangGraph de Enoc sobre el mensaje indicado hasta el punto de interrupción HITL (`interrupt_before=['publicador']`), reportando los modelos de IA exactos utilizados.
- **Entrada (JSON)**:
  ```json
  {
    "id_mensaje": 15,
    "proveedor": "Groq (Llama 3.3)"
  }
  ```
- **Respuesta Exitosa (HTTP 200 OK)**:
  ```json
  {
    "exito": true,
    "id_mensaje": 15,
    "estado_pipeline": "procesado",
    "estado_revision": "procesado",
    "rutas_activas": ["linkedin", "x", "discord"],
    "modelos_utilizados": {
      "orquestador": "Google Gemini · gemini-3.6-flash",
      "linkedin": "Google Gemini · gemini-3.6-flash",
      "x": "Groq · qwen/qwen3.8-27b",
      "discord": "Groq · openai/gpt-oss-120b"
    },
    "borradores_ui": {
      "linkedin": { "titulo": "...", "texto_copy": "...", "copy_tono": "..." },
      "x": { "titulo": "...", "texto_copy": "..." },
      "discord": { "canal_seleccionado": "#general", "titulo": "...", "texto_copy": "..." }
    },
    "copys_generados": { "...": "estructura de copys de Enoc" },
    "thread_id": "sesion_15",
    "mensaje": "Pipeline ejecutado con éxito. Borradores listos para revisión humana (HITL)."
  }
  ```

#### 3. `POST /api/v1/mototradis/generate-channel`
- **Descripción**: Genera o regenera el contenido para un canal individual respetando los esquemas Pydantic de Enoc y reportando el modelo utilizado.
- **Entrada (JSON)**:
  ```json
  {
    "id_mensaje": 15,
    "canal": "linkedin",
    "proveedor": "Google Gemini Flash Lite"
  }
  ```
- **Respuesta Exitosa (HTTP 200 OK)**:
  ```json
  {
    "exito": true,
    "canal": "linkedin",
    "modelo_utilizado": "Google Gemini Flash Lite · gemini-2.5-flash-lite",
    "contenido": {
      "titulo": "Virtualización Enterprise...",
      "texto_copy": "En infraestructura hiperconvergente...",
      "copy_tono": "En CloudEDTech formamos líderes técnicos...",
      "newsletter": { "titular": "...", "resumen": "..." },
      "faq": { "tema": "...", "origen": "..." }
    }
  }
  ```

#### 4. `POST /api/v1/mototradis/publish-channel`
- **Descripción**: Publica directamente en una de las plataformas activas individuales (LinkedIn, X, Discord) utilizando estrictamente el contenido enviado desde el editor.
- **Entrada (JSON)**:
  ```json
  {
    "id_mensaje": 15,
    "canal": "discord",
    "datos_canal": {
      "canal_seleccionado": "#general",
      "titulo": "Optimización Cloud",
      "texto_copy": "¡Gran avance del equipo!..."
    }
  }
  ```
- **Respuesta Exitosa (HTTP 200 OK)**:
  ```json
  {
    "exito": true,
    "canal": "discord",
    "metodo_envio": "webhook_especifico",
    "mensaje": "Publicado exitosamente en Discord #general con citación de contexto"
  }
  ```

#### 5. `POST /api/v1/mototradis/hitl-decision`
- **Descripción**: Ejecuta la decisión editorial humana global sobre el lote, inyectando las ediciones manuales en el checkpoint y despachando a las redes activas con tolerancia a credenciales opcionales.
- **Entrada (JSON)**:
  ```json
  {
    "id_mensaje": 15,
    "decision": "aprobar",
    "copys_editados": {
      "linkedin": { "titulo": "...", "texto_copy": "...", "copy_tono": "..." },
      "x": { "titulo": "...", "texto_copy": "..." },
      "discord": { "canal_seleccionado": "#general", "titulo": "...", "texto_copy": "..." }
    }
  }
  ```
- **Respuesta Exitosa para Aprobación (HTTP 200 OK)**:
  ```json
  {
    "exito": true,
    "decision": "aprobar",
    "id_mensaje": 15,
    "estado_pipeline": "aprobado",
    "estado_revision": "aprobado",
    "resultados_canales": {
      "discord": { "ok": true, "detalle": "Publicado en Discord #general vía webhook" },
      "linkedin": { "ok": false, "detalle": "Credenciales opcionales LINKEDIN_ACCESS_TOKEN no configuradas" },
      "x": { "ok": false, "detalle": "Credenciales opcionales X_API_KEY no configuradas" }
    },
    "registrado_en_historial": true,
    "mensaje": "Lote aprobado y publicado en las redes activas disponibles."
  }
  ```
- **Respuesta Error de Precondición (HTTP 400 Bad Request)**:
  ```json
  {
    "detail": "No existen borradores válidos para aprobar en este lote. Ejecute el pipeline previamente."
  }
  ```
- **Respuesta Exitosa para Desaprobación (HTTP 200 OK)**:
  ```json
  {
    "exito": true,
    "decision": "desaprobar",
    "id_mensaje": 15,
    "estado_pipeline": "desaprobado",
    "estado_revision": "desaprobado",
    "checkpoint_limpiado": true,
    "mensaje": "Lote marcado como desaprobado y checkpoints del hilo sesion_15 purgados."
  }
  ```

#### 6. `POST /api/v1/mototradis/run-mass`
- **Descripción**: Dispara bajo demanda el flujo masivo autónomo de Gemma 4 para mensajes de baja relevancia ($< 35$), identificando explícitamente el modelo utilizado.
- **Entrada (JSON)**:
  ```json
  {
    "limite": 10
  }
  ```
- **Respuesta Exitosa (HTTP 200 OK)**:
  ```json
  {
    "exito": true,
    "procesados": 8,
    "publicados_directo": 5,
    "descartados": 3,
    "modelo_ia": "Google Gemma 4 · gemma-4-31b-it",
    "mensaje": "Procesamiento masivo con Gemma 4 completado exitosamente."
  }
  ```

---

### 3.2 Modelos de Datos en TypeScript (`frontend/src/api/contentWorkflow.ts` y `communityLive.ts`)

```typescript
export interface MototradisUiDrafts {
  linkedin?: {
    titulo?: string
    texto_copy?: string
    copy_tono?: string
    newsletter?: { titular: string; resumen: string }
    faq?: { tema: string; origen: string }
  }
  x?: {
    titulo?: string
    texto_copy?: string
  }
  discord?: {
    canal_seleccionado?: string
    titulo?: string
    texto_copy?: string
  }
}

export interface MototradisCheckpointResponse {
  has_checkpoint: boolean
  id_mensaje: number
  estado_pipeline: 'pendiente' | 'procesado' | 'aprobado' | 'desaprobado'
  estado_revision: string
  rutas_activas: string[]
  modelos_utilizados: Record<string, string>
  borradores_ui: MototradisUiDrafts
  copys_generados: Record<string, any>
  origen: string
}

export interface MototradisExecuteResponse {
  exito: boolean
  id_mensaje: number
  estado_pipeline: string
  estado_revision: string
  rutas_activas: string[]
  modelos_utilizados: Record<string, string>
  borradores_ui: MototradisUiDrafts
  copys_generados: Record<string, any>
  thread_id: string
  mensaje: string
}

export interface ChannelPublishResult {
  ok: boolean
  detalle: string
}

export interface MototradisHitlResponse {
  exito: boolean
  decision: 'aprobar' | 'desaprobar'
  id_mensaje: number
  estado_pipeline: string
  estado_revision: string
  resultados_canales?: Record<string, ChannelPublishResult>
  checkpoint_limpiado?: boolean
  registrado_en_historial?: boolean
  mensaje: string
}

export interface MototradisRunMassResponse {
  exito: boolean
  procesados: number
  publicados_directo: number
  descartados: number
  modelo_ia: string
  mensaje: string
}
```

---

## 4. Casos Límite (Edge Cases) y Mitigaciones

1. **Ausencia de `GEMINI_API_KEY` o `SUPABASE_DB_URL` en el entorno**:
   - *Riesgo*: `src/config.py` lanza `ValueError` al importarse si faltan estas variables, quebrando el servidor FastAPI.
   - *Mitigación*: En `puente_motor_ia.py`, antes de importar `src`, se ejecuta la homologación de variables copiando `GOOGLE_API_KEY` a `GEMINI_API_KEY` y `DATABASE_URL` a `SUPABASE_DB_URL`. Si alguna falta, se captura la excepción y se asignan cadenas vacías o fallbacks seguros sin detener la API.
2. **Entorno local o de tests sin base de datos PostgreSQL activa**:
   - *Riesgo*: Al compilar el grafo de LangGraph, `PostgresSaver` intenta conectarse y lanza excepción de red o socket.
   - *Mitigación*: `puente_motor_ia.py` evalúa la conectividad; si la conexión a PostgreSQL no se establece, utiliza `MemorySaver` en memoria como checkpointer transparente, garantizando que los tests y la ejecución local continúen sin requerir una base externa.
3. **Soberanía Humana ante Ediciones en el Frontend**:
   - *Riesgo*: El operador edita el título de LinkedIn y el texto de Discord en el navegador, pero al pulsar "Aprobar y Publicar todo", el sistema despacha los textos generados automáticamente por la IA en el checkpoint original.
   - *Mitigación*: `POST /api/v1/mototradis/hitl-decision` recibe `copys_editados`, ejecuta `checkpointer.update_state` para sobreescribir el estado previo del hilo y pasa los copys editados a `publishers.py`.
4. **Discord Webhook ausente o canal sin webhook configurado**:
   - *Riesgo*: Al intentar publicar en Discord un mensaje derivado a `#faq` o `#notificaciones` cuando la variable de entorno correspondiente no existe, la petición arroja error y aborta el flujo.
   - *Mitigación*: Se aplica la cascada de 3 niveles: webhook de canal $\rightarrow$ webhook general (`DISCORD_WEBHOOK_ANUNCIOS`) $\rightarrow$ Bot Oficial de Discord (`DISCORD_TOKEN`), garantizando entrega resiliente.
5. **Tweets que exceden 280 caracteres técnicos**:
   - *Riesgo*: La API v2 de Twitter rechaza cualquier publicación que exceda los 280 caracteres.
   - *Mitigación*: En el frontend, el editor de X valida la longitud combinada (`{titulo}\n\n{texto_copy}`) con contador reactivo; en el backend, `enviar_tweet_x` aplica truncamiento inteligente con puntos suspensivos asegurando $\le 280$ caracteres.
6. **Credenciales opcionales ausentes en X o LinkedIn**:
   - *Riesgo*: Al aprobar el lote multicanal, la falta de credenciales de redes opcionales provoca una excepción no controlada HTTP 500 y no se registra la publicación en Discord.
   - *Mitigación*: El despachador reporta un desglose detallado `resultados_canales`, completando la publicación en los canales configurados (Discord) y guardando la auditoría en Supabase y SQLite sin quebrar la petición.
7. **Invocación de aprobación sin borradores previos**:
   - *Riesgo*: Un operador pulsa "Aprobar y Publicar" en un mensaje que aún no ha corrido el pipeline y no tiene estado en checkpoints.
   - *Mitigación*: Validación preventiva en backend: si no existen copys en el payload ni en el checkpoint, responder inmediatamente con código HTTP 400 Bad Request.

---

## 5. Criterios de Aceptación Globales

1. **Incorporación Limpia y Estabilidad del Repositorio**:
   - Los archivos de `src/`, `scripts/`, `docs/`, `app_demo.py`, `.env.example` y dependencias de `requirements.txt` se integran sin alterar ninguno de los 17 archivos preexistentes en la raíz ni las carpetas `backend/` y `motor-ia/`.
   - La homologación de `GEMINI_API_KEY` y `SUPABASE_DB_URL` en `puente_motor_ia.py` previene errores de importación al cargar `src/config.py`.
2. **Orquestación LangGraph y Resiliencia de Checkpoints**:
   - El checkpointer conmuta automáticamente entre `PostgresSaver` y `MemorySaver` si no hay conectividad externa.
   - `GET /api/v1/mototradis/checkpoint/{id_mensaje}` reporta fielmente `pendiente` para mensajes sin checkpoint, y entrega `borradores_ui` estructurado junto al mapa `modelos_utilizados` cuando existe un estado en proceso HITL.
   - `POST /api/v1/mototradis/execute-pipeline` ejecuta el grafo de LangGraph, clasifica las rutas activas con la matriz de 4 prioridades, almacena en los checkpoints y marca el lote como `procesado`.
3. **Visibilidad Explícita del Modelo de IA en Toda la Experiencia**:
   - Cada sección, tarjeta y panel (`Orquestador`, `LinkedIn`, `X`, `Discord`, `PQRS` y `Procesamiento Masivo`) cuenta con una insignia visible y distinguible indicando con claridad qué modelo de IA realizó o está realizando la tarea.
4. **Soberanía HITL y Publicación Multicanal**:
   - La aprobación global HITL inyecta los textos editados por el humano antes de publicar, despachando el contenido final del editor a las redes disponibles.
   - La cascada de 3 niveles en Discord (webhook de canal $\rightarrow$ webhook general $\rightarrow$ Bot) asegura la entrega del mensaje con la citación en bloque `> 💬 Contexto de @autor`.
   - La falta de credenciales opcionales de X o LinkedIn entrega un reporte detallado `resultados_canales` sin arrojar HTTP 500, registrando la auditoría en `public.historial_reportes_semanales` y SQLite `contenidos_generados`.
   - La desaprobación global actualiza `lotes_ia_kpis` a `desaprobado` y purga limpiamente el hilo de checkpoints.
5. **Procesamiento Masivo Autónomo con Gemma 4**:
   - `POST /api/v1/mototradis/run-mass` procesa mensajes con relevancia $< 35$ mediante `Google Gemma 4 · gemma-4-31b-it`, publicando o descartando según la clasificación y entregando métricas de resumen con su modelo respectivo.
6. **Experiencia Integrada en `ContentStudio.tsx`**:
   - Los paneles de Anuncios Oficiales y Quejas permanecen 100% operativos.
   - La mesa de trabajo muestra la insignia desacoplada del pipeline, las rutas activas, el modelo IA del orquestador y el botón "Ejecutar Pipeline Mototradis (Orquestador IA)".
   - Cada tarjeta multicanal cuenta con insignia del modelo IA correspondiente, editores completos, visualización de copys de marca, selector de canal de Discord con vista previa de cita, y botones de publicación individual.
   - La barra de decisión global HITL permite aprobar/publicar todo con textos editados, desaprobar/limpiar y procesar baja relevancia con Gemma 4.
7. **Inviolabilidad Constitucional y Calidad**:
   - Ninguno de los 17 archivos protegidos de la raíz, `backend/` ni `motor-ia/` sufre modificaciones.
   - El 100% de la suite de pruebas del proyecto pasa en verde (`pytest tests/ -v`).
   - El frontend compila de manera limpia sin errores (`npm run build`).
