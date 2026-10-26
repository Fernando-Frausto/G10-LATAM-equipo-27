# Especificación 027: Resolución de Bloqueos en Gemma 4, Inclusión Automática de Links y Sincronización de Reportes OCI

## 1. Contexto y Justificación (El POR QUÉ)

Durante las pruebas integrales de control de calidad (QA) y validaciones operativas realizadas por Enoc Ramírez sobre el entorno unificado conectado a Supabase (`public.interacciones`, `public.lotes_ia_kpis`, `public.historial_reportes_semanales`), el Orquestador Multi-LLM LangGraph (`src/`) y el almacenamiento en la nube Oracle Cloud Infrastructure (OCI Storage), se identificaron tres problemas críticos documentados mediante trazas de LangSmith, capturas de pantalla de redes sociales y auditoría de reportes en OCI:

1. **Problema 1 — Bucle infinito y cuelgues de Gemma 4 en Ingesta/Análisis en segundo plano:**
   - Al ejecutar la evaluación por lote en la vista de Ingesta seleccionando el motor "Google Gemma 4 (Google)", el pipeline quedó colgado indefinidamente a nivel de socket de red en `ChatGoogleGenerativeAI(model='gemma-4-31b-it')` dentro de `evaluador_lotes.evaluar_lote`.
   - La API pública gratuita de Google AI Studio presenta inestabilidad recurrente (errores `500 INTERNAL`, `503 UNAVAILABLE`, `429 RESOURCE_EXHAUSTED` y sockets TCP colgados sin timeout de lectura a nivel de transporte).
   - Además, la interfaz de Ingesta (`frontend/src/pages/Messages.tsx`) carece de un mecanismo de cancelación activa (`AbortController` / botón "Cancelar Evaluación") y de un timeout del cliente; en consecuencia, la UI queda permanentemente deshabilitada en estado "Evaluando con IA...", mientras en el backend persisten procesos o hilos bloqueados consumiendo recursos.
   - **Decisión adoptada:** Descartar definitivamente Gemma 4 como motor de análisis en la etapa pesada de Ingesta/Análisis (**Opción B** solicitada por Enoc). Reservar Gemma 4 exclusivamente para copywriting masivo y reevaluación autónoma de baja relevancia (`< 35%`) en `nodo_gemma_automatico` donde Enoc verificó que opera con total éxito, dejando como motores estables y únicos en Ingesta a **Groq (Llama 3.3 70B / GPT-OSS 120B)** y **Google Gemini Flash Lite** (`gemini-3.1-flash-lite` / `gemini-3.5-flash-lite`), complementados con un mecanismo de cancelación cooperativa y timeout defensivo.

2. **Problema 2 — Ausencia de links oficiales automáticos y residuos de marca en LinkedIn y X:**
   - Durante las pruebas del flujo con el mensaje ID 2441, se generaron los 3 copys multicanal, pero ni LinkedIn ni X incluyeron los links institucionales de forma automática.
   - En la especificación previa (Spec 026), la inyección de enlaces se limitó a la acción manual individual (`publish-channel` y botón `➕ Insertar mención de links` en `ContentStudio.tsx`), dejando desprovistos los prompts y post-procesamiento de los nodos automáticos de LangGraph (`nodo_linkedin` y `nodo_x` en `src/nodes.py`) y las funciones de publicación final (`enviar_linkedin` y `enviar_tweet_x` en `src/publishers.py`).
   - Se requiere superar y armonizar la directriz de la Spec 026: **la inclusión de links institucionales debe ser obligatoria y 100% automática** tanto en la generación de copys como en la publicación multicanal. En LinkedIn debe inyectarse el bloque "Más Información" con los 3 links oficiales (`https://lnkd.in/gX2m2Rhq`, `https://lnkd.in/gvbqJiF4`, `https://lnkd.in/gU7h7xyG`), en X los 2 links oficiales de No Country y GitHub (`https://lnkd.in/gvbqJiF4`, `https://lnkd.in/gU7h7xyG`) garantizando un límite estricto de 280 caracteres sin mutilar los enlaces, y erradicando de forma absoluta cualquier mención residual a "Alura" / "Alura Latam" / "#Alura" -> "CloudEDTech".

3. **Problema 3 — Lotes de OCI desfasados, datos ficticios de fallback y bloqueo por fallos parciales:**
   - Al inspeccionar los lotes de OCI (`reportes/2026-semana-42.json`), el archivo contenía únicamente datos ficticios de prueba (`id_mensaje: "999"`, `autor: "fallback_user"`, `texto_original: "Texto de fallback"`), sin incluir ninguno de los mensajes reales recientemente aprobados y publicados por Enoc.
   - Causas detectadas:
     * En `src/nodes.py`, `nodo_publicador` condicionaba la inserción en `public.historial_reportes_semanales` a que `todas_exitosas` fuera `True`. Si un canal no poseía credenciales (ej. X API) o fallaba transitoriamente, pero otro canal (ej. Discord) publicaba con éxito, el registro completo se descartaba y nunca se persistía en Supabase.
     * Desalineación de formato de semana: mientras OCI consulta por el formato canónico `YYYY-semana-WW` (ej. `2026-semana-42`), `nodo_publicador` y partes del puente almacenaban la semana como `"Semana_01"` o `"Semana_05"`, provocando que las consultas SQL con filtro rígido no encontraran filas.
     * En `puente_motor_ia.py`, la función `_cargar_lote_para_reporte_semanal` recurría a mocks estáticos en lugar de consultar las tablas locales SQLite (`contenidos_generados` e `interacciones`), impidiendo reconstruir reportes semanales con copys reales cuando Supabase no responde o no contiene datos para la semana solicitada.
   - Restricción constitucional inviolable: El archivo preexistente `reporte_semanal.py` en la raíz está estrictamente protegido por la Constitución y AGENTS.md; toda normalización y adaptación debe implementarse en `puente_motor_ia.py`, `src/nodes.py` y `src/schemas.py`.

---

## 2. Requisitos Funcionales en Formato EARS (El QUÉ)

### RF-01: Descarte de Gemma 4 en Ingesta y Blindaje de Motores Estables (Opción B)
- **CUANDO** el usuario accede al selector de modelos de IA en la vista de Ingesta (`frontend/src/pages/Messages.tsx`), **EL SISTEMA DEBERÁ** habilitar como motores activos de análisis únicamente a **Groq (Llama 3.3 70B)** y **Google Gemini Flash Lite** (`gemini-3.1-flash-lite` / `gemini-3.5-flash-lite`); **SI** se visualiza la opción de Google Gemma 4 en el selector, **ENTONCES EL SISTEMA DEBERÁ** presentarla deshabilitada (`disabled`) acompañada de un distintivo visual o tooltip explicativo: *"Reservado para copywriting masivo (<35%). En Ingesta usa Groq o Gemini Flash Lite"*.
- **CUANDO** el backend (`puente_motor_ia.py`) recibe una petición de evaluación individual (`POST /api/v1/ai/evaluate-message`) o por lote (`POST /api/v1/ai/evaluate-batch`) solicitando `cerebro_ia_gemma_4` o `"Google Gemma 4"`, **EL SISTEMA DEBERÁ** rechazar la petición con código `HTTP 400 Bad Request` indicando claramente que Gemma 4 está reservado para la cola de copywriting masivo, **O BIEN** ejecutar un fallback transparente inmediato hacia Groq (Llama 3.3) o Gemini Flash Lite sin colgar la petición.
- **MIENTRAS** opera la cola de copywriting masivo y reevaluación autónoma de baja relevancia (`< 35%`, Prioridad 3 / rescate en `nodo_gemma_automatico` dentro de `src/nodes.py`), **EL SISTEMA DEBERÁ** mantener a Google Gemma 4 como motor especializado con temperatura `0.1`, `max_output_tokens=800` y timeout estricto de 20 segundos por invocación.

### RF-02: Contrato y Semántica del Endpoint de Cancelación y Timeout en Ingesta
- **CUANDO** el cliente solicita abortar una evaluación en curso mediante el endpoint formal:
  ```http
  POST /api/v1/ai/cancel-evaluation
  Content-Type: application/json

  {
    "batch_id": "opcional-uuid-o-identificador"
  }
  ```
  **EL SISTEMA DEBERÁ** activar una señal cooperativa en memoria (`_cancelar_evaluacion_evento = threading.Event()` o booleano atómico en `puente_motor_ia.py`), interrumpir la iteración de mensajes pendientes en el hilo de evaluación y responder de forma inmediata con:
  ```json
  {
    "status": "cancelled",
    "message": "Evaluación cancelada exitosamente"
  }
  ```
- **MIENTRAS** la evaluación por lote esté en curso en la interfaz (`isEvaluatingBatch === true`), **EL SISTEMA DEBERÁ** mostrar un botón visible e interactivo de **"Cancelar Evaluación"** junto al indicador de estado en `Messages.tsx`.
- **CUANDO** el operador presione "Cancelar Evaluación", **EL SISTEMA DEBERÁ**:
  1. Abortar la petición HTTP activa mediante un `AbortController` nativo de JavaScript.
  2. Disparar `POST /api/v1/ai/cancel-evaluation` hacia el backend.
  3. Restablecer de inmediato `isEvaluatingBatch = false`.
  4. Ejecutar `loadMessages()` para refrescar la tabla y reflejar las evaluaciones parciales consolidadas hasta el momento del aborto.
  5. Desplegar un mensaje informativo: *"Evaluación cancelada por el usuario. Los mensajes analizados hasta el momento fueron conservados"*.
- **SI** la petición de evaluación por lote no responde en un lapso de 60 segundos en el cliente, **ENTONCES EL SISTEMA DEBERÁ** abortar automáticamente la espera por timeout, notificar al operador sobre la degradación de la API externa y restaurar la disponibilidad de la interfaz sin requerir recargar la página.

### RF-03: Automatización de Links y Sanitización de Marca en LinkedIn (Extensión de Spec 026)
- **CUANDO** el nodo de LinkedIn (`nodo_linkedin` en `src/nodes.py`) redacta una publicación a partir de un mensaje precurado, **EL SISTEMA DEBERÁ**:
  - Instruir obligatoriamente en el `<system_prompt>` la inclusión al final del cuerpo del post (`texto_copy`) del bloque canónico de "Más Información" con los 3 enlaces institucionales:
    ```text
    Más Información:
    https://lnkd.in/gX2m2Rhq
    https://lnkd.in/gvbqJiF4
    https://lnkd.in/gU7h7xyG
    ```
  - Aplicar un post-procesamiento defensivo e idempotente: verificar la presencia íntegra de los 3 enlaces en `texto_copy`; si faltan o el bloque fue omitido por el LLM, anexarlo automáticamente al final sin duplicar links preexistentes.
  - Sanitizar de forma irrevocable cualquier mención a `"Alura"`, `"Alura Latam"`, `"#Alura"` o `"#AluraLatam"` transformándolas en `"CloudEDTech"` y `"#CloudEDTech"`.
- **CUANDO** se despache una publicación hacia LinkedIn mediante `enviar_linkedin` (`src/publishers.py`) o a través de `puente_motor_ia.py` (generación automática o manual), **EL SISTEMA DEBERÁ** validar y asegurar de forma idempotente la presencia del bloque de 3 links y la sanitización de marca antes de emitir la petición a la API corporativa de LinkedIn, superando la limitación de la Spec 026 para que la inclusión sea 100% automática en todos los flujos.

### RF-04: Automatización de Links y Límite Estricto de 280 Caracteres en X (Extensión de Spec 026)
- **CUANDO** el nodo de X (`nodo_x` en `src/nodes.py`) redacta un post para la red social X, **EL SISTEMA DEBERÁ**:
  - Instruir en el `<system_prompt>` la inclusión obligatoria de exactamente los 2 enlaces institucionales de No Country y GitHub:
    ```text
    https://lnkd.in/gvbqJiF4
    https://lnkd.in/gU7h7xyG
    ```
  - Aplicar un post-procesamiento defensivo e idempotente que garantice:
    1. La presencia íntegra de los 2 links oficiales (`https://lnkd.in/gvbqJiF4` y `https://lnkd.in/gU7h7xyG`).
    2. Longitud total combinada (`titulo` + `texto_copy` + enlaces) estrictamente menor o igual a **280 caracteres**.
    3. **SI** el mensaje excede los 280 caracteres, recortar exclusivamente el cuerpo del texto en el límite de palabra más cercano añadiendo puntos suspensivos (`...`), **garantizando que las URLs de los 2 enlaces permanezcan íntegras, intactas y al final del tweet sin cortarse jamás**.
    4. Sanitización automática de `"Alura"` -> `"CloudEDTech"`.
- **CUANDO** se despache un tweet a través de `enviar_tweet_x` (`src/publishers.py`) o `puente_motor_ia.py`, **EL SISTEMA DEBERÁ** revalidar la regla de 280 caracteres con preservación absoluta de los enlaces y sanitización de marca antes de llamar a Tweepy / API v2 de X, garantizando automatización plena tanto en flujos automáticos de LangGraph como en publicaciones individuales.

### RF-05: Persistencia Atómica de Publicaciones Parciales en `historial_reportes_semanales`
- **CUANDO** se ejecuta el `nodo_publicador` (`src/nodes.py`) sobre un conjunto de rutas activas (`discord`, `x`, `linkedin`, `reclamos`), **EL SISTEMA DEBERÁ** persistir la fila en `public.historial_reportes_semanales` de Supabase **SIEMPRE QUE al menos un canal haya sido publicado con éxito** (`al_menos_una_exitosa === true`), tolerando que otros canales fallen por falta de credenciales locales o errores transitorios de API.
- **CUANDO** se persista una publicación parcial o total en `public.historial_reportes_semanales`, **EL SISTEMA DEBERÁ** registrar con exactitud:
  - `rutas_activas`: lista de canales efectivamente publicados con éxito (ej. `["discord"]`).
  - `estado`: `"publicado"` si al menos 1 canal resultó exitoso, o `"error"` si todos fallaron.
  - `estado_publicacion`: representación JSON o estructurada del resultado detallado por canal (indicando canales con éxito y canales con omisión/fallo).
  - Actualizar el estado del lote en SQLite y Supabase a `"aprobado"` o `"publicado"` para los canales exitosos, evitando que un fallo aislado en X o LinkedIn impida la auditoría del mensaje despachado a Discord.

### RF-06: Normalización Canónica de Semana (`YYYY-semana-WW`) sin Modificar Archivos Raíz
- **EL SISTEMA DEBERÁ** estandarizar de forma homogénea en `src/nodes.py`, `src/schemas.py` y `puente_motor_ia.py` el identificador de semana bajo el formato canónico ISO: `YYYY-semana-WW` (ejemplo: `2026-semana-42`).
- **CUANDO** un mensaje ingrese al pipeline con formatos relativos preexistentes (como `"Semana_01"` o `"Semana_05"`), o contenga un campo de fecha (`fecha_envio`, `enviado_en`), **EL SISTEMA DEBERÁ** convertir dicha referencia a su representación canónica `YYYY-semana-WW` en `puente_motor_ia.py` y `src/nodes.py` antes de persistir en `public.historial_reportes_semanales` o en SQLite local.
- **CUANDO** el generador de reportes OCI consulte Supabase o SQLite mediante `_extraer_historial_reportes_semanales_supabase(semana_objetivo)` en `puente_motor_ia.py`, **EL SISTEMA DEBERÁ** aplicar una búsqueda normalizada bidireccional que coincida tanto con el formato canónico (`2026-semana-42`) como con variantes numéricas (`%semana%42%` y `Semana_42`), asegurando que ningún registro publicado quede omitido ante la consulta de OCI.
- **REGLA DE INVIOLABILIDAD ABSOLUTA:** Queda categóricamente prohibido modificar el archivo raíz `reporte_semanal.py`. Toda la lógica de adaptación, filtrado y normalización reside exclusivamente en `puente_motor_ia.py` y `src/`.

### RF-07: Reconstrucción de Reportes OCI desde SQLite y Erradicación Total de Registros Mock
- **CUANDO** se solicite generar o sincronizar un reporte semanal para OCI (`_cargar_lote_para_reporte_semanal` en `puente_motor_ia.py` y `POST /api/v1/oci-storage/weekly-sync`), **EL SISTEMA DEBERÁ**:
  1. Consultar en primer término los registros consolidados en `public.historial_reportes_semanales` de Supabase para la semana solicitada.
  2. **SI** Supabase no contiene registros o no está disponible para dicha semana, **ENTONCES EL SISTEMA DEBERÁ** reconstruir el lote consultando directamente las tablas locales de SQLite (`contenidos_generados` unida con `interacciones`), extrayendo los copys reales aprobados o publicados (`plataforma`, `titulo`, `contenido`, KPIs asociados).
  3. **PROHIBIR CATEGÓRICAMENTE** la inyección de registros mock o ficticios (`id_mensaje: "999"`, `autor: "fallback_user"`, `texto_original: "Texto de fallback"`).
  4. **SI** tras agotar Supabase y SQLite no existen registros reales para la semana indicada, responder con un mensaje informativo controlado (`HTTP 400`: *"No hay mensajes analizados para el período indicado"*), retornando listas vacías `[]` sin generar reportes corruptos con datos ficticios.
  5. Regenerar y sobrescribir físicamente el reporte `reportes/2026-semana-42.json` en disco local y sincronizarlo al bucket de OCI Storage conteniendo únicamente datos 100% reales de la base de datos.

---

## 3. Restricciones Constitucionales y Requisitos No Funcionales (RNF)

- **RNF-01 (Inviolabilidad de Archivos Raíz y Ámbito Autorizado de Modificación):**
  - **Archivos Autorizados Exclusivamente:**
    * `src/nodes.py` (nodos de LinkedIn, X, publicador y orquestador).
    * `src/publishers.py` (despachos a LinkedIn y X con links y sanitización).
    * `src/schemas.py` (esquemas de estado y contratos de LangGraph).
    * `puente_motor_ia.py` (endpoints, normalización de semanas, cancelación y extracción de copys).
    * `frontend/src/pages/Messages.tsx` (deshabilitación de Gemma 4 y botón de cancelación).
    * Suite de pruebas automatizadas en `tests/`.
  - **Archivos Protegidos Inviolables:** Queda estrictamente prohibido modificar `reporte_semanal.py`, `base_datos.py`, `modelos.py`, `cerebro_ia.py`, `cerebro_ia_gemma_4.py`, `evaluador_lotes.py`, `app.py` o cualquier otro archivo preexistente de la raíz o de `motor-ia/`.
- **RNF-02 (Preservación Estricta de la Regla de Oro de Alta Velocidad):** Las lecturas de interfaz (`GET /api/v1/messages`, `GET /api/v1/oci-storage/reports`, etc.) deberán responder en `< 2 ms` desde memoria o SQLite local. Ninguna validación de links ni sanitización podrá introducir llamadas externas bloqueantes en el hilo principal de FastAPI.
- **RNF-03 (Compatibilidad Estricta de Esquemas de OCI):** La estructura del reporte JSON generado para OCI Storage (`metadata`, `resumen_metricas`, `activos_copywriting.aprobados`, `activos_copywriting.descartados`) debe conservarse 100% idéntica a la especificada en Spec 024, garantizando retrocompatibilidad total con los consumidores del bucket.
- **RNF-04 (Diseño Test-First - TDD):** Cada requerimiento funcional (RF-01 al RF-07) contará con pruebas automatizadas dedicadas en `tests/` verificadas mediante `pytest`, garantizando el 100% de la suite preexistente en verde y la compilación limpia de TypeScript (`npm run build`).

---

## 4. Decisiones Técnicas y de Arquitectura Resueltas

1. **Gemma 4 en Ingesta:** Descartado formalmente (Opción B). Groq y Gemini Flash Lite son los únicos motores de Ingesta activos. Gemma 4 se reserva para masivo `< 35%`.
2. **Endpoint de Cancelación:** Definido formalmente en `POST /api/v1/ai/cancel-evaluation` con detención cooperativa mediante señal en memoria y corte inmediato en el frontend vía `AbortController`.
3. **Persistencia Parcial:** `nodo_publicador` inserta en Supabase si `al_menos_una_exitosa` es True, registrando `rutas_activas` exitosas y `estado: "publicado"`.
4. **Automatización de Links:** Obligatoria y automática en `nodo_linkedin` (3 links con "Más Información") y `nodo_x` (2 links, <= 280 chars sin truncar URLs). Idempotente y libre de menciones a "Alura".
5. **Inviolabilidad de `reporte_semanal.py`:** Protegido al 100%. Toda normalización reside en `puente_motor_ia.py` y `src/`.
6. **Saneamiento OCI:** Erradicación total de `id_mensaje: "999"` y regeneración de `reporte_2026-semana-42.json` con datos reales.

---

## 5. Criterios de Aceptación Globales

1. El selector de modelos de Ingesta en `Messages.tsx` muestra Groq y Gemini Flash Lite activos; Gemma 4 aparece deshabilitado con el tooltip de reserva para copywriting masivo.
2. Iniciar una evaluación por lote muestra el botón "Cancelar Evaluación"; al pulsarlo, la petición se cancela en menos de 1 segundo, la UI recupera su interactividad y se refrescan los mensajes.
3. El endpoint `POST /api/v1/ai/cancel-evaluation` interrumpe cooperativamente la ejecución en el backend y responde con `{"status": "cancelled", "message": "Evaluación cancelada exitosamente"}`.
4. Generar copys con el mensaje 2441 produce en LinkedIn un texto con el bloque "Más Información" y los 3 links oficiales, sin menciones a "Alura".
5. Generar copys con el mensaje 2441 produce en X un texto con los 2 links oficiales de No Country y GitHub, con longitud total menor o igual a 280 caracteres y sin cortar los enlaces.
6. Publicar un contenido donde solo Discord tiene webhook configurado registra exitosamente la fila en `public.historial_reportes_semanales` con `rutas_activas: ["discord"]` y `estado: "publicado"`.
7. La columna `semana` en `public.historial_reportes_semanales` utiliza el formato canónico `YYYY-semana-WW` (ej. `2026-semana-42`).
8. El archivo `reportes/2026-semana-42.json` y el bucket OCI contienen los copys y KPIs reales de la comunidad, sin ninguna ocurrencia de `"999"` ni `"fallback_user"`.
9. Todos los tests en `tests/` finalizan en verde (`pytest`) y el build de frontend finaliza con código 0 (`npm run build`).
