# Plan de Implementación Técnica: Spec 015 - Integración del Pipeline Mototradis MVP de Enoc con Backend y Redacción de Contenidos

## 1. Arquitectura General y Límites del Sistema

El objetivo de este plan es diseñar e implementar la integración completa, funcional y no invasiva del motor **Mototradis MVP** (rama `origin/mototradis-mvp`, commit `23699cf`) desarrollado por Enoc dentro del ecosistema de CloudEDTech. Se respetan de manera irrestricta los principios de **Inviolabilidad Constitucional** y **Aislamiento No Invasivo**:

- **Inviolabilidad Constitucional Estricta**: Cero modificaciones a los 17 archivos preexistentes en la raíz (`api.py`, `base_datos.py`, `modelos.py`, `evaluador_lotes.py`, `anuncios_discord.py`, `app.py`, etc.), así como a los directorios protegidos `backend/` y `motor-ia/`.
- **Integridad del Paquete de Enoc**: Los 17 archivos nuevos de la rama de Enoc (`src/`, `scripts/`, `docs/`, `app_demo.py`, `.env.example`) se incorporan de manera limpia. El paquete `src/` se mantiene canónico y no se altera; cualquier adaptación, conversión de esquemas, normalización y enrutamiento se resuelve exclusivamente en el adaptador `puente_motor_ia.py`.
- **Mandato de Usuario sobre Transparencia de Inteligencia Artificial**: *"quiero que en cada cosa diga el modelo de ia que esta utilizando para realizarla"*. Cada componente, tarjeta, panel y endpoint del sistema debe reportar y exhibir de forma visible, inequívoca y tipada el modelo de IA específico que ejecutó o está ejecutando la inferencia (`Orquestador`, `LinkedIn`, `X`, `Discord`, `Soporte PQRS` y `Procesamiento Masivo Gemma 4`), distinguiendo además entre el modelo configurado y el fallback efectivo en caso de contingencia.
- **Soberanía Humana Absoluta (HITL)**: Los textos editados manualmente por el redactor humano en el frontend (`copys_editados`) prevalecen sobre cualquier borrador algorítmico previo almacenado en checkpoints. Antes de despachar a redes, se actualiza el checkpoint (`checkpointer.update_state`) y se inyectan directamente al publicador.
- **Resiliencia de Infraestructura**: Conmutación automática de checkpointer (`PostgresSaver` hacia `MemorySaver` si la base de datos externa no responde), cascada jerárquica de 3 niveles para Discord con cita formal de autor en bloque (`> 💬 **Contexto de @autor:** *"{texto}"*`), y tolerancia ante la ausencia de credenciales opcionales de redes sociales (`X_API_KEY`, `LINKEDIN_ACCESS_TOKEN`) reportando `resultados_canales` sin arrojar error HTTP 500.

```mermaid
flowchart TD
    subgraph Frontend ["Frontend (React / Vite / Tailwind)"]
        CS["ContentStudio.tsx<br/>- Encabezado con estado desacoplado<br/>- Badge Orquestador IA (modelo visible)<br/>- Tarjetas con Badges de Modelo IA:<br/>  * LinkedIn (Google Gemini 3.6 / 3.5)<br/>  * X / Twitter (Groq Qwen 27B / Llama)<br/>  * Discord / PQRS (Groq GPT-OSS / Gemini)<br/>- Editores de copys con contador 280 chars en X<br/>- Previa en vivo cita Discord (> 💬 Contexto)<br/>- Barra HITL Global (Aprobar / Desaprobar)<br/>- Modal Gemma 4 Masivo (Modelo visible)"]
        CW["contentWorkflow.ts<br/>- Cliente tipado Mototradis<br/>- MototradisCheckpointResponse<br/>- MototradisExecuteResponse<br/>- MototradisHitlResponse<br/>- MototradisRunMassResponse"]
    end

    subgraph Backend ["Adaptador: puente_motor_ia.py (FastAPI)"]
        HOM["Homologación de Entorno<br/>(GOOGLE_API_KEY → GEMINI_API_KEY)<br/>(DATABASE_URL → SUPABASE_DB_URL)"]
        TRK["Rastreador de Modelos IA<br/>(modelos_utilizados map)"]
        
        EP1["GET /api/v1/mototradis/checkpoint/{id}<br/>- Evalúa checkpoints y reportes<br/>- Desacopla pendiente vs lotes_ia_kpis<br/>- Retorna borradores_ui y modelos"]
        EP2["POST /api/v1/mototradis/execute-pipeline<br/>- Grafo LangGraph con interrupt HITL<br/>- Fan-out a nodos y validador de marca<br/>- Normaliza borradores_ui y modelos"]
        EP3["POST /api/v1/mototradis/generate-channel<br/>- Inferencia por canal con modelo elegido<br/>- Retorna contenido y modelo_utilizado"]
        EP4["POST /api/v1/mototradis/publish-channel<br/>- Publicación individual con texto activo<br/>- Cascada Discord de 3 niveles"]
        EP5["POST /api/v1/mototradis/hitl-decision<br/>- Soberanía Humana (copys_editados)<br/>- update_state en checkpointer<br/>- Despacho multicanal resiliente<br/>- Registro en historial_reportes_semanales<br/>- Limpieza si es desaprobado"]
        EP6["POST /api/v1/mototradis/run-mass<br/>- scripts/run_mass.py bajo demanda<br/>- Google Gemma 4 (gemma-4-31b-it)<br/>- Resumen estadístico y modelo"]
    end

    subgraph LangGraph ["Motor Canónico: src/ (Enoc)"]
        CFG["src/config.py (Validación de entorno)"]
        GRP["src/graph.py (build_graph con Fábrica)"]
        CHK["src/checkpoints.py (PostgresSaver / MemorySaver)"]
        NOD["src/nodes.py (Orquestador, LinkedIn, X, Discord, Gemma)"]
        PUB["src/publishers.py (Discord, X, LinkedIn)"]
        GEM["src/gemma.py (Gemma 4 resiliente)"]
    end

    subgraph Canales ["Distribución Externa"]
        DISC["Discord Webhooks / Bot<br/>1. Webhook Canal (#general, #faq, #pqrs)<br/>2. Webhook General (#anuncios)<br/>3. Bot Oficial (DISCORD_TOKEN)"]
        XTW["X API v2 (Tweepy / Truncado ≤ 280)"]
        LNK["LinkedIn API (ugcPosts / URN)"]
    end

    subgraph Persistencia ["Almacenamiento y Auditoría"]
        PG[("Supabase PostgreSQL<br/>- public.checkpoints<br/>- public.lotes_ia_kpis<br/>- public.historial_reportes_semanales")]
        SQL[("SQLite local (communitylab.db)<br/>- contenidos_generados")]
    end

    CS -->|fetch / axios| CW
    CW -->|HTTP REST| Backend
    HOM --> GRP
    EP1 --> CHK & PG
    EP2 --> GRP & NOD & TRK
    EP3 --> NOD & TRK
    EP4 --> PUB & DISC
    EP5 --> CHK & PUB & DISC & XTW & LNK & PG & SQL
    EP6 --> GEM & PUB & DISC & PG


---

## 2. Incorporación de Archivos de Enoc y Dependencias

### 2.1 Archivos Canónicos de `origin/mototradis-mvp` (Commit `23699cf`)
Se incorporarán en la rama de trabajo los 17 archivos de Enoc sin modificar su código interno:
1. `src/__init__.py`: Paquete Python inicializado.
2. `src/config.py`: Gestor centralizado de variables de entorno y validación de credenciales críticas y opcionales.
3. `src/schemas.py`: Esquemas Pydantic tipados (`AgentState`, `RouterOutput`, `RespuestaComunidadLinkedin`, `RespuestaComunidadX`, `RespuestaComunidadDiscord`, `RespuestaComunidadPQRS`).
4. `src/database.py`: Utilidad para actualización de estado en `public.lotes_ia_kpis`.
5. `src/checkpoints.py`: Funciones de purga y limpieza de checkpoints (`limpiar_checkpoint_hilo`, `limpiar_todos_los_checkpoints`).
6. `src/publishers.py`: Despachadores para Discord (con cita de autor), X (vía Tweepy con truncado a 280) y LinkedIn (vía UGC API).
7. `src/gemma.py`: Cliente de Google GenAI con `generar_con_gemma_resiliente`, extracción JSON robusta y prompt de baja relevancia.
8. `src/nodes.py`: Nodos del grafo (`nodo_orquestador`, `nodo_linkedin`, `nodo_x`, `nodo_discord`, `nodo_reclamos`, `nodo_validador`, `nodo_publicador`, `nodo_gemma_automatico`) con inicialización de modelos y matrices defensivas.
9. `src/graph.py`: Fábrica `build_graph(checkpointer=..., interrupt_before=...)` y enrutador condicional de plataformas.
10. `scripts/run_hitl.py`: Orquestador de consola para evaluación y decisión HITL con PostgresSaver.
11. `scripts/run_mass.py`: Procesador masivo para mensajes con relevancia < 35 mediante Gemma 4.
12. `scripts/reset_thread.py`: Script de utilidad para purgar hilos residuales.
13. `docs/contrato-pipeline.md`: Contrato de integración y ciclo de vida de los estados.
14. `docs/informe_archivos.md`: Inventario detallado de la arquitectura de archivos.
15. `docs/leeme.md`: Guía de ejecución y despliegue del pipeline.
16. `app_demo.py`: Aplicación demostrativa Streamlit creada por Enoc.
17. `.env.example`: Plantilla de variables de entorno del pipeline.

### 2.2 Sincronización de `requirements.txt`
Se actualizará el `requirements.txt` de la raíz agregando de forma limpia las dependencias del pipeline:
```text
# Dependencias Pipeline Mototradis (Enoc)
langgraph>=0.2.0
langgraph-checkpoint-postgres>=2.0.0
psycopg[binary,pool]>=3.2.0
supabase>=2.0.0
json-repair>=0.30.0
tweepy>=4.14.0
nest-asyncio>=1.6.0
google-genai>=1.0.0
```

---

## 3. Diseño Técnico del Backend (`puente_motor_ia.py`)

### 3.1 Homologación de Entorno y Resiliencia de Checkpointer (RF-02)
1. **Homologación de Variables de Entorno**:
   - Antes de realizar cualquier importación del paquete `src`, `puente_motor_ia.py` asegura la paridad de claves:
     ```python
     if not os.environ.get("GEMINI_API_KEY") and os.environ.get("GOOGLE_API_KEY"):
         os.environ["GEMINI_API_KEY"] = os.environ["GOOGLE_API_KEY"]
     if not os.environ.get("SUPABASE_DB_URL") and os.environ.get("DATABASE_URL"):
         os.environ["SUPABASE_DB_URL"] = os.environ["DATABASE_URL"]
     ```
   - Si tras la homologación alguna variable crítica no está disponible, se capturan las excepciones de configuración permitiendo al adaptador operar en modo degradado controlado o simulación segura sin colapsar el proceso del servidor.

2. **Fábrica de Checkpointers con Fallback a `MemorySaver`**:
   - Para garantizar que la suite de pruebas unitarias y entornos de desarrollo sin Postgres activo funcionen fluidamente, se implementa una función proveedora de checkpointer:
     ```python
     def obtener_checkpointer_resiliente():
         db_url = os.environ.get("SUPABASE_DB_URL") or os.environ.get("DATABASE_URL")
         if db_url and "postgres" in db_url:
             try:
                 from langgraph.checkpoint.postgres import PostgresSaver
                 # Probar conectividad rápida con timeout de 3s
                 checkpointer = PostgresSaver.from_conn_string(db_url)
                 checkpointer.setup()
                 return checkpointer, "postgres"
             except Exception as exc:
                 logger.warning(f"⚠️ PostgresSaver no disponible ({exc}). Conmutando a MemorySaver.")
         from langgraph.checkpoint.memory import MemorySaver
         return MemorySaver(), "memory"
     ```

### 3.2 Trazabilidad Explícita de Modelos de IA (`modelos_utilizados`) (RF-02, RF-03)
En cumplimiento directo del mandato del usuario (*"quiero que en cada cosa diga el modelo de ia que esta utilizando para realizarla"*), el backend mantendrá un registro formal de los modelos involucrados:
1. **Definición de Modelos por Defecto**:
   - `orquestador`: `Groq · qwen/qwen3.8-27b` (Fallback: `Google Gemini · gemini-3.6-flash`).
   - `linkedin`: `Google Gemini · gemini-3.5-flash-lite` (Fallback: `Google Gemini · gemini-3.1-flash-lite`).
   - `x`: `Groq · qwen/qwen3.8-27b` / `Google Gemini · gemini-3.5-flash-lite`.
   - `discord`: `Groq · openai/gpt-oss-120b` (Fallback: `Google Gemini · gemini-3.1-flash-lite`).
   - `pqrs`: `Groq · qwen/qwen3.8-27b` (Fallback: `Google Gemini · gemini-3.5-flash-lite`).
   - `masivo`: `Google Gemma 4 · gemma-4-31b-it`.
2. **Estructura de Retorno**:
   - Cada respuesta de checkpoint o ejecución entregará el diccionario `modelos_utilizados`:
     ```json
     "modelos_utilizados": {
       "orquestador": "Google Gemini · gemini-3.6-flash",
       "linkedin": "Google Gemini · gemini-3.5-flash-lite",
       "x": "Groq · qwen/qwen3.8-27b",
       "discord": "Groq · openai/gpt-oss-120b"
     }
     ```
   - Si un canal individual es regenerado con un proveedor específico (ej. "Google Gemma 4"), el endpoint `generate-channel` retorna `modelo_utilizado: "Google Gemma 4 · gemma-4-31b-it"`.

### 3.3 Normalización de Datos y Contratos de Endpoints (RF-03)

#### 1. `GET /api/v1/mototradis/checkpoint/{id_mensaje}`
- **Desacoplamiento de Estado**:
  - Verifica si existe registro en `public.historial_reportes_semanales`. Si existe $\rightarrow$ `estado_pipeline = "aprobado"`, `estado_revision = "aprobado"`.
  - Si no está en historial, consulta el estado en `grafo.get_state({"configurable": {"thread_id": f"sesion_{id_mensaje}"}})` o `public.checkpoints`.
  - Si no existe checkpoint (`has_checkpoint = False`) $\rightarrow$ retorna `estado_pipeline = "pendiente"`, sin importar que en `lotes_ia_kpis` figure como `'aprobado'` o `'pendiente'`.
  - Si existe checkpoint $\rightarrow$ `estado_pipeline = "procesado"`, extrayendo los copys canónicos y formateando `borradores_ui` junto a `modelos_utilizados`.
- **Estructura Normalizada `borradores_ui`**:
  ```python
  borradores_ui = {
      "linkedin": {
          "titulo": post_lk.get("titulo", ""),
          "texto_copy": post_lk.get("texto_copy", ""),
          "copy_tono": post_lk.get("copy_tono", ""),
          "newsletter": post_lk.get("newsletter", {}),
          "faq": post_lk.get("faq", {})
      },
      "x": {
          "titulo": post_x.get("titulo", ""),
          "texto_copy": post_x.get("texto_copy", "")
      },
      "discord": {
          "canal_seleccionado": activos_disc.get("canal_seleccionado", "#general"),
          "titulo": post_disc.get("titulo", ""),
          "texto_copy": post_disc.get("texto_copy", "")
      }
  }
  ```

#### 2. `POST /api/v1/mototradis/execute-pipeline`
- Parámetros: `id_mensaje: int`, `proveedor: Optional[str]`.
- Obtiene la interacción desde SQLite o Supabase, extrayendo `autor`, `semana`, `fecha_envio`, `fecha_extraccion` y `json_precurado` (con `relevancia`, `sentimiento`, `texto_original`).
- Instancia el checkpointer resiliente y compila `build_graph(checkpointer=checkpointer, interrupt_before=["publicador"])`.
- Ejecuta `grafo.stream(estado_inicial, {"configurable": {"thread_id": f"sesion_{id_mensaje}"}})`.
- Se detiene automáticamente en la pausa HITL antes del publicador.
- Actualiza `estado_revision = 'procesado'` en `lotes_ia_kpis`.
- Extrae el estado, construye `borradores_ui` y `modelos_utilizados` y retorna el payload HTTP 200.

#### 3. `POST /api/v1/mototradis/generate-channel`
- Parámetros: `id_mensaje: int`, `canal: str`, `proveedor: Optional[str]`.
- Invoca el nodo especializado para el canal (`nodo_linkedin`, `nodo_x`, `nodo_discord` o `nodo_reclamos`), utilizando el modelo solicitado o sus fallbacks.
- Retorna el objeto formateado de `contenido`, `borradores_ui` actualizado y `modelo_utilizado`.

### 3.4 Soberanía Humana (HITL), Cascada Discord de 3 Niveles y Tolerancia a Redes Opcionales (RF-04)

#### 1. Soberanía Humana Absoluta en `POST /api/v1/mototradis/hitl-decision`
- **Precondición**: Si `decision == 'aprobar'` y no se reciben borradores en `copys_editados` ni existen en el checkpoint $\rightarrow$ responder con código **HTTP 400 Bad Request** (*"No existen borradores válidos para aprobar en este lote"*).
- **Inyección Prioritaria**:
  - Si el usuario editó textos en el editor del frontend, se reconstruye el diccionario canónico `copys_actualizados`:
    ```python
    # Sobreescribir el estado del checkpoint para que el hilo quede consistente
    checkpointer.update_state(
        {"configurable": {"thread_id": f"sesion_{id_mensaje}"}},
        {"copys_generados": copys_actualizados}
    )
    ```
  - Al despachar a las funciones de publicación, se suministran **estrictamente** los textos editados por el humano (`copys_actualizados`), evitando cualquier regresión a los borradores originales de la IA.

#### 2. Cascada Jerárquica de 3 Niveles para Discord con Citas en Bloque
Para cada envío a Discord, se garantiza la entrega mediante la cascada:
1. **Nivel 1**: Webhook específico del canal (`DISCORD_WEBHOOK_GENERAL`, `DISCORD_WEBHOOK_FAQ`, `DISCORD_WEBHOOK_NOTIFICACIONES`, `DISCORD_WEBHOOK_PQRS`).
2. **Nivel 2**: Webhook general de la plataforma (`DISCORD_WEBHOOK_ANUNCIOS`).
3. **Nivel 3**: Bot Oficial de Discord (`DISCORD_TOKEN` o `DISCORD_BOT_TOKEN`) mediante petición REST directa a la API de Discord al ID de canal correspondiente.
- **Formato del Mensaje**: Siempre incluye la citación del autor:
  ```text
  > 💬 **Contexto de @{autor}:** *"{texto_snippet}"*

  **{titulo}**

  {texto_copy}
  ```

#### 3. Armonización de Límites en X (Twitter)
- Meta del generador: `titulo <= 70` y `texto_copy <= 210`.
- Despacho: `enviar_tweet_x` evalúa `len(f"{titulo}\n\n{texto_copy}")`. Si supera 280 caracteres, aplica truncamiento preventivo inteligente a 277 caracteres añadiendo `...`.

#### 4. Tolerancia a Credenciales Opcionales
- Si `X_API_KEY` o `LINKEDIN_ACCESS_TOKEN` no están presentes en `.env`:
  - No arrojar error HTTP 500.
  - Registrar en `resultados_canales`:
    ```json
    {
      "discord": { "ok": true, "detalle": "Publicado en Discord #general vía webhook" },
      "linkedin": { "ok": false, "detalle": "Credenciales opcionales LINKEDIN_ACCESS_TOKEN no configuradas" },
      "x": { "ok": false, "detalle": "Credenciales opcionales X_API_KEY no configuradas" }
    }
    ```
  - Si Discord o la persistencia en base de datos fueron exitosos, registrar en `public.historial_reportes_semanales`, actualizar `estado_revision = 'aprobado'` y registrar en `contenidos_generados` en SQLite local.

#### 5. Desaprobación y Purga
- Si `decision == 'desaprobar'`:
  - Actualizar `estado_revision = 'desaprobado'` en `public.lotes_ia_kpis`.
  - Invocar `limpiar_checkpoint_hilo(f"sesion_{id_mensaje}")` de `src/checkpoints.py` para purgar `public.checkpoints`, `public.checkpoint_blobs` y `public.checkpoint_writes`.
  - Retornar `{ "exito": true, "decision": "desaprobar", "checkpoint_limpiado": true }`.

### 3.5 Procesamiento Masivo Autónomo con Gemma 4 (RF-05)
- Endpoint `POST /api/v1/mototradis/run-mass`:
  - Recibe `limite: int = 10`.
  - Invoca la lógica de `scripts/run_mass.py` (`obtener_lotes_pendientes_masivos` y `nodo_gemma_automatico`).
  - Para cada interacción con relevancia $< 35$, evalúa spam vs soporte, despachando respuestas válidas a Discord con la cita del autor.
  - Retorna resumen con `procesados`, `publicados_directo`, `descartados` y `modelo_ia: "Google Gemma 4 · gemma-4-31b-it"`.

---

## 4. Diseño Técnico del Frontend (`frontend/src/`)

### 4.1 Cliente de API Tipado: `frontend/src/api/contentWorkflow.ts`
Se enriquecerá el módulo `contentWorkflow.ts` incorporando las interfaces TypeScript y funciones de consumo:
- Interfaces: `MototradisUiDrafts`, `MototradisCheckpointResponse`, `MototradisExecuteResponse`, `MototradisHitlResponse`, `MototradisRunMassResponse`.
- Métodos:
  - `getMototradisCheckpoint(messageId: number): Promise<MototradisCheckpointResponse>`
  - `executeMototradisPipeline(messageId: number, provider?: string): Promise<MototradisExecuteResponse>`
  - `generateMototradisChannel(messageId: number, channel: string, provider?: string): Promise<any>`
  - `publishMototradisChannel(messageId: number, channel: string, channelData: any): Promise<any>`
  - `submitMototradisHitlDecision(messageId: number, decision: 'aprobar' | 'desaprobar', editedDrafts?: MototradisUiDrafts): Promise<MototradisHitlResponse>`
  - `runMototradisMassGemma(limit?: number): Promise<MototradisRunMassResponse>`

### 4.2 Mesa de Trabajo y Badges de Modelos en `ContentStudio.tsx` (RF-06)
1. **Preservación Intacta**:
   - Se mantienen al 100% las secciones existentes: "Panel de Anuncios Oficiales de la Comunidad (Discord Webhook)" y "Panel de Quejas, Reclamos y Soporte Crítico".
2. **Encabezado de Mesa de Trabajo**:
   - Insignia de estado del pipeline desacoplada:
     - `⏳ Pendiente de ejecutar pipeline` (amarillo tenue / slate) si `has_checkpoint === false` y no está publicado.
     - `⚙️ Procesado / En revisión HITL` (azul) si tiene checkpoint activo.
     - `✅ Aprobado / Publicado` (verde esmeralda) si ya fue publicado.
     - `🚫 Desaprobado` (rojo).
   - Insignia de Rutas Activas (ej. `[LinkedIn, X, Discord]`).
   - **Insignia Visible del Orquestador**:
     ```tsx
     <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200">
       <Sparkles className="w-3.5 h-3.5 text-indigo-500" />
       <span>Orquestador IA: {pipelineData?.modelos_utilizados?.orquestador || "Google Gemini · gemini-3.6-flash"}</span>
     </div>
     ```
   - Botón de Acción Principal:
     ```tsx
     <button onClick={handleExecutePipeline} className="bg-indigo-600 hover:bg-indigo-700 text-white font-medium px-4 py-2 rounded-xl flex items-center gap-2">
       <Play className="w-4 h-4" />
       Ejecutar Pipeline Mototradis (Orquestador IA)
     </button>
     ```
3. **Carga Reactiva de Checkpoint**:
   - Al seleccionar un mensaje en la bandeja horizontal o ingresar vía `/content?interaction={id}`, se dispara `getMototradisCheckpoint(id)` para hidratar inmediatamente los borradores si ya existían, enfocando la tarjeta de "Mensaje Original de Discord" con desplazamiento suave.

### 4.3 Tarjetas Multicanal y Editores con Badges de Modelos IA (RF-06)
Cada tarjeta exhibirá en su cabecera un badge destacado indicando el modelo de IA:
1. **Tarjeta LinkedIn**:
   - Badge de Modelo: `Modelo IA: Google Gemini · gemini-3.5-flash-lite` (o el reportado en `modelos_utilizados.linkedin`).
   - Editores para Título del post y Copy persuasivo.
   - Plegables para Copy de tono CloudEDTech, Destaque de Newsletter Semanal y Sugerencia FAQ.
   - Botón directo "Publicar en LinkedIn", botón "Regenerar" con selector de modelo IA y botón "Copiar".
2. **Tarjeta X (Twitter)**:
   - Badge de Modelo: `Modelo IA: Groq · qwen/qwen3.8-27b` (o el reportado en `modelos_utilizados.x`).
   - Editores para Título/Hook y Tweet.
   - Contador dinámico de caracteres sobre el total combinado (`{titulo}\n\n{texto_copy}`) respecto a los 280 caracteres técnicos con alerta ámbar (> 250) o roja (> 280).
   - Botón directo "Publicar en X", botón "Regenerar" y botón "Copiar".
3. **Tarjeta Discord**:
   - Badge de Modelo: `Modelo IA: Groq · openai/gpt-oss-120b` (o `Google Gemini · gemini-3.5-flash-lite` para reclamos).
   - Selector de canal (`#general`, `#faq`, `#notificaciones`).
   - Editores para Título y Cuerpo del post.
   - **Vista previa en vivo de la Cita en Bloque**:
     ```tsx
     <div className="bg-slate-50 border-l-4 border-indigo-400 p-2 text-xs italic text-slate-600 rounded">
       &gt; 💬 <strong>Contexto de @{selectedMessage.autor}:</strong> "{selectedMessage.texto_original?.slice(0, 110)}..."
     </div>
     ```
   - Botón directo "Publicar en Discord", botón "Regenerar" y botón "Copiar".

### 4.4 Barra de Decisión Global HITL y Modal de Gemma 4 (RF-04, RF-05, RF-06)
- Ubicada inmediatamente después de las tarjetas de canales:
  - Botón Principal: `✅ Aprobar y Publicar todo (HITL)` (llama a `submitMototradisHitlDecision(id, 'aprobar', borradoresEditados)`).
  - Botón de Descarte: `❌ Desaprobar lote y limpiar checkpoint` (llama a `submitMototradisHitlDecision(id, 'desaprobar')`).
  - Botón Secundario con Badge: `⚡ Procesar cola de baja relevancia (< 35) con Gemma 4 (gemma-4-31b-it)`.
- **Modal de Procesamiento Masivo con Gemma 4**:
  - Diálogo modal con selector de límite de mensajes (5, 10, 20).
  - Badge visible destacado: `Modelo IA Ejecutor: Google Gemma 4 · gemma-4-31b-it`.
  - Explicación de que evaluará y canalizará automáticamente mensajes con relevancia $< 35$.
  - Despliegue de resultados estadísticos (`procesados`, `publicados_directo`, `descartados`).

---

## 5. Estrategia de Pruebas Automatizadas (TDD) y Verificación

### 5.1 Batería TDD en `tests/test_unificacion_motor_ia.py`
Se diseñarán pruebas rigurosas cubriendo los requerimientos de la especificación:
1. `test_homologacion_entorno_y_checkpointer_resiliente`: Verifica que `GEMINI_API_KEY` y `SUPABASE_DB_URL` se homologuen correctamente y que `obtener_checkpointer_resiliente()` retorne `MemorySaver` en entorno desconectado sin arrojar excepción.
2. `test_mototradis_checkpoint_desacoplado_pendiente`: Valida que `GET /api/v1/mototradis/checkpoint/{id}` retorne `estado_pipeline: "pendiente"` cuando no existe checkpoint en `public.checkpoints` ni registro en historial, independientemente de `lotes_ia_kpis`.
3. `test_mototradis_execute_pipeline_y_trazabilidad_modelos`: Ejecuta el pipeline hasta la interrupción HITL, verificando que la respuesta incluya `borradores_ui` estructurado y el diccionario `modelos_utilizados` con nombres de modelos explícitos.
4. `test_mototradis_hitl_soberania_humana_y_publicacion`: Envía `copys_editados` al endpoint `POST /api/v1/mototradis/hitl-decision`, verificando que se inyecten los textos editados por el humano en lugar de los borradores originales y que se tolere la ausencia de credenciales opcionales de X/LinkedIn mediante `resultados_canales`.
5. `test_mototradis_hitl_precondicion_sin_borradores`: Verifica que intentar aprobar un lote sin borradores ni checkpoint retorne código HTTP 400 Bad Request.
6. `test_mototradis_hitl_desaprobar_y_limpieza_checkpoint`: Valida que al desaprobar se actualice el estado a `desaprobado` y se invoque la limpieza del hilo.
7. `test_mototradis_run_mass_gemma_trazabilidad`: Verifica que el endpoint de procesamiento masivo invoque el nodo de Gemma 4 y retorne `modelo_ia: "Google Gemma 4 · gemma-4-31b-it"`.

### 5.2 Verificación de Frontend y Verificación Constitucional
1. Compilación de TypeScript en `frontend/`: `npm run build` certificando cero errores de sintaxis o tipos.
2. Comprobación Git de Inmutabilidad:
   ```bash
   git diff --exit-code api.py base_datos.py modelos.py evaluador_lotes.py anuncios_discord.py app.py
   git diff --exit-code backend motor-ia
   ```
   Garantizando que ninguno de los 17 archivos preexistentes en la raíz ni las carpetas protegidas hayan sido alterados.
