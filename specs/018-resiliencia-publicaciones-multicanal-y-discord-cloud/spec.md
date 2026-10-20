# Spec 018 — Resiliencia de Publicaciones Multicanal, Diagnóstico de Despacho Real y Manejo de Rate-Limit Discord en la Nube

- **Estado:** Especificación Perfeccionada tras Revisión QA (@reviewer) y Feedback de Identidad del Usuario — Lista para Aprobación
- **Fecha:** 2026-10-20
- **Autor:** @planner
- **Rama objetivo:** `beta-pruebas`

---

## 1. Contexto y Objetivo de Negocio (QUÉ y POR QUÉ)

### ¿Qué se necesita?
Resolver de raíz los incidentes de publicación y sincronización identificados en la versión desplegada en la nube (Render y Netlify) garantizando **veracidad absoluta de despacho** (cero falsos positivos), **resiliencia integral ante límites de tasa (Rate Limits / Cloudflare Error 1015)** e **identidad unificada de emisión oficial** en cinco áreas neurálgicas:

1. **Sincronización de Mensajes de Discord (`/messages` y `POST /api/v1/discord/sync`):**
   - Interceptar de forma determinista y estructurada los bloqueos transitorios por rate limit que Discord y Cloudflare imponen sobre las direcciones IP compartidas de servidores en la nube (HTTP 429 / Cloudflare Error 1015).
   - Manejar defensivamente el cuerpo devuelto por Cloudflare, el cual se entrega típicamente en formato `text/html` y no `application/json`, evitando excepciones de decodificación (`JSONDecodeError`) y retornando siempre cabeceras CORS válidas (`Access-Control-Allow-Origin: *`) con un mensaje explicativo y accionable para el usuario en lugar de crasheos genéricos de red como `Failed to fetch`.

2. **Identidad Unificada del Emisor en Discord (`CloudEdTech_Oficial`) y Separación de Agente Extractor:**
   - Establecer taxativamente que **toda comunicación saliente hacia Discord** (ya sean Anuncios Oficiales de la Comunidad, Publicaciones Multicanal desde la Mesa de Trabajo, o Respuestas a Quejas y Reclamos de Soporte) DEBERÁ emitirse obligatoriamente bajo la identidad oficial institucional y avatar de **`CloudEdTech_Oficial`** mediante su integración y webhook correspondiente (`DISCORD_WEBHOOK_ANUNCIOS` / `DISCORD_WEBHOOK_OFICIAL`, `DISCORD_WEBHOOK_GENERAL`, `DISCORD_WEBHOOK_PQRS`).
   - El bot extractor de mensajes de Discord (`DISCORD_TOKEN` / `DISCORD_BOT_TOKEN`) opera **exclusivamente como agente pasivo de lectura e ingesta en segundo plano**, sin intervenir jamás en la publicación de contenidos salientes.

3. **Panel de Anuncios Oficiales de la Comunidad (`/content` y `POST /api/v1/content-workflow/announcements/publish`):**
   - Emitir los anuncios bajo la identidad de `CloudEdTech_Oficial` mediante su webhook oficial (`DISCORD_WEBHOOK_ANUNCIOS`), anexando el parámetro `?wait=true` para auditar la recepción con `message_id` y código HTTP 200/201.
   - Si la API es rechazada por rate limit o bloqueo de Cloudflare, manejar de forma resiliente posibles respuestas HTML sin arrojar `JSONDecodeError` y notificar de forma clara y no disruptiva en el panel, preservando el borrador del anuncio.

4. **Mesa de Trabajo Multicanal — LangGraph / Enoc (`/content`, `publish-channel` y `hitl-decision`):**
   - Erradicar definitivamente cualquier retorno de falso positivo en el backend (como retornos incondicionales de éxito ante fallos no capturados en cascadas de Discord).
   - Exigir validación estricta de respuestas exitosas de las APIs externas antes de marcar cualquier contenido o canal como publicado:
     * **Discord:** Emitir como `CloudEdTech_Oficial` vía Webhook/API con `?wait=true`, confirmando respuesta HTTP 200 o 201 y presencia de identificador de mensaje (`message_id`).
     * **LinkedIn:** Confirmar respuesta HTTP 201 de `ugcPosts` con el URN generado (`urn:li:share:...` o `urn:li:ugcPost:...`) y generar el enlace de acceso directo canónico `https://www.linkedin.com/feed/update/{urn}`.
     * **X (Twitter):** Confirmar respuesta exitosa de creación de tweet con el ID devuelto por la API v2 y generar el enlace directo `https://x.com/CloudEdTech_1/status/{id}`.
   - Preservar inmutable el archivo protegido `src/publishers.py`, implementando los adaptadores autónomos de validación y captura de IDs/URNs directamente dentro de `puente_motor_ia.py`.
   - En la interfaz de usuario, nunca marcar tarjetas con insignias verdes `✓ Publicado en {Red}` a menos que el canal haya sido confirmado con `estado_canal === "enviado"`. Manejar publicaciones parciales manteniendo habilitadas las tarjetas fallidas para su reintento inmediato.

5. **Panel de Quejas, Reclamos y Soporte Crítico (`/content` y `POST /api/v1/content-workflow/complaints/publish-response`):**
   - Emitir las respuestas oficiales a quejas y soporte hacia Discord bajo la identidad de `CloudEdTech_Oficial` mediante webhook (`DISCORD_WEBHOOK_PQRS` con `?wait=true`) o API oficial. Manejar con precisión el error HTTP 429 de Discord y respuestas HTML de Cloudflare, mostrando diagnósticos directos y amigables al operador sin dejar la interfaz en estado bloqueado o roto.

6. **Inviolabilidad Arquitectónica y Constitucional:**
   - Mantener intactos los 17 archivos protegidos de la raíz, la carpeta `src/` (incluyendo taxativamente `src/publishers.py`), `backend/` y `motor-ia/`, concentrando la adaptación backend en `puente_motor_ia.py` y la adaptación visual en `frontend/src/`.

---

### ¿Por qué es necesario?
1. **Identidad de Marca y Coherencia Institucional:** La comunidad de estudiantes y egresados requiere claridad absoluta sobre la procedencia de los avisos y respuestas. Permitir que distintos bots o nombres genéricos publiquen fragmenta la imagen de la plataforma; canalizar todas las emisiones a través de `CloudEdTech_Oficial` unifica la voz oficial y garantiza reconocimiento inmediato.
2. **Separación de Responsabilidades:** El bot extractor requiere permisos específicos de lectura de historial y telemetría en múltiples canales. Desacoplarlo de las publicaciones salientes evita riesgos de seguridad, elimina colisiones de rate limit entre ingesta y publicación, y asegura que la ingesta continúe operando independientemente del estado de los webhooks de salida.
3. **Confianza y Veracidad en la Difusión de Contenidos:** El equipo de community managers y redactores no puede depender de una interfaz que señale falsamente que un mensaje fue difundido en redes sociales cuando en realidad la API externa rechazó la solicitud por credenciales, permisos o saturación. Una confirmación falsa detiene el flujo operativo y deja a la comunidad sin la comunicación requerida.
4. **Mitigación de Bloqueos en Entornos Cloud Compartidos:** Plataformas PaaS como Render comparten rangos de direcciones IP que con frecuencia sufren restricciones de Cloudflare (Error 1015). Si el backend lanza excepciones no controladas o asume erróneamente que las respuestas de error son JSON en estos escenarios, se produce `JSONDecodeError` y el navegador pierde las cabeceras CORS reportando un error opaco de red (`Failed to fetch`). La aplicación debe manejar estos eventos como estados controlados de negocio, ofreciendo diagnóstico inmediato y la alternativa de operar desde el entorno local.
5. **Auditabilidad y Acceso Directo a Publicaciones:** Al capturar los identificadores reales de cada red social (ID de tweet en X y URN en LinkedIn), el sistema puede ofrecer enlaces directos canónicos inmediatos para que el operador verifique y supervise la repercusión de la publicación en tiempo real con un solo clic.

---

## 2. Requerimientos Funcionales (Formato EARS)

### RF-001: Captura Determinista de Rate-Limit Discord / Cloudflare 1015 y Tolerancia a Respuestas HTML
- **CUANDO** el usuario ejecute la sincronización manual de mensajes desde la interfaz (`POST /api/v1/discord/sync`) y **SI** la conexión con la API de Discord es rechazada por límite de tasa (HTTP 429, Cloudflare Error 1015, Timeout de conexión o fallo de sesión):
  1. **EL SISTEMA DEBERÁ** capturar la excepción en el backend (`puente_motor_ia.py`) e inspeccionar el código de estado HTTP y el contenido en texto plano, tolerando defensivamente cuerpos en formato `text/html` típicos de Cloudflare sin intentar parsearlos ciegamente como JSON para evitar errores de tipo `JSONDecodeError`.
  2. **EL SISTEMA DEBERÁ** garantizar la inclusión de cabeceras CORS (`Access-Control-Allow-Origin: *`) y retornar una respuesta HTTP 429 estructurada en formato JSON con la siguiente información:
     * `exito: false`
     * `codigo_error: "RATE_LIMIT_CLOUDFLARE_1015"`
     * `mensaje: "Discord o Cloudflare ha limitado temporalmente la IP del servidor en la nube (Error 1015 / Rate Limit). Sincroniza desde tu entorno local o intenta en unos minutos."`
     * `detail: "Discord o Cloudflare ha limitado temporalmente la IP del servidor en la nube (Error 1015 / Rate Limit). Sincroniza desde tu entorno local o intenta en unos minutos."`
- **POR QUÉ:** Previene excepciones 500 no capturadas y fallos de parseo JSON que suprimen las cabeceras CORS en navegadores provocando el error `Failed to fetch`, e informa con exactitud la causa externa del bloqueo.

---

### RF-002: Notificación Amigable y Resiliente en la Interfaz de Ingesta (`Messages.tsx`)
- **CUANDO** la acción de sincronización de Discord en `Messages.tsx` reciba una respuesta HTTP 429 o un mensaje de error asociado a Cloudflare Error 1015 / Rate Limit, **EL SISTEMA DEBERÁ** mostrar un banner de advertencia contextual con el mensaje exacto: *"Discord o Cloudflare ha limitado temporalmente la IP del servidor en la nube (Error 1015 / Rate Limit). Sincroniza desde tu entorno local o intenta en unos minutos."*, restablecer de inmediato el estado del botón (`isSyncing = false`) y mantener la lista de mensajes existentes visible y plenamente interactiva.
- **POR QUÉ:** Brinda tranquilidad y claridad al operador en producción (Render/Netlify), guiándolo a utilizar la sincronización local o reintentar sin suponer una caída de la aplicación.

---

### RF-003: Publicación Resiliente de Anuncios Oficiales con Emisor Unificado `CloudEdTech_Oficial`
- **CUANDO** el usuario confirme la publicación de un anuncio oficial en la comunidad (`POST /api/v1/content-workflow/announcements/publish`):
  1. **EL SISTEMA DEBERÁ** despachar el mensaje obligatoriamente bajo la identidad y avatar oficial de **`CloudEdTech_Oficial`** a través de su integración webhook oficial (`DISCORD_WEBHOOK_ANUNCIOS`), anexando el parámetro `?wait=true` para forzar a Discord a devolver el payload JSON del mensaje con su `message_id` y código HTTP 200/201.
  2. **SI** el despacho es rechazado con código HTTP 429 o bloqueo Cloudflare 1015, **EL SISTEMA DEBERÁ** capturar la respuesta inspeccionando texto y código HTTP sin arrojar `JSONDecodeError` ante respuestas HTML.
  3. **SI** el webhook responde satisfactoriamente (HTTP 200), **EL SISTEMA DEBERÁ** registrar la publicación en la base de datos indicando que se completó vía webhook bajo `CloudEdTech_Oficial` y notificar el éxito al frontend.
  4. **SI** el webhook es rechazado por bloqueo de IP en la nube (Error 1015 / 429), **EL SISTEMA DEBERÁ** retornar una respuesta HTTP 429 estructurada con cabeceras CORS completas y el detalle explicativo del bloqueo.
- **POR QUÉ:** Asegura identidad institucional unificada en anuncios prioritarios, audita la entrega mediante `message_id` y previene caídas por rate limit en la nube.

---

### RF-004: Banner Informativo y Preservación de Borrador en Panel de Anuncios (`ContentStudio.tsx`)
- **CUANDO** la publicación de un anuncio en el Panel de Anuncios Oficiales falle por bloqueo de rate limit o Cloudflare 1015, **EL SISTEMA DEBERÁ** mostrar en el banner del panel la notificación: *"Discord ha bloqueado temporalmente el envío por límite de peticiones de Cloudflare (Error 1015). Intenta en unos minutos o realiza la publicación desde local"*, cancelar el estado de publicación en progreso y conservar el texto del anuncio en el editor sin borrarlo ni reiniciar el formulario.
- **POR QUÉ:** Impide la pérdida accidental del anuncio redactado y proporciona diagnóstico directo al operador de comunidad.

---

### RF-005: Erradicación de Falsos Positivos, Inviolabilidad de `src/publishers.py` y Validación Estricta
- **CUANDO** se invoque la publicación de contenido hacia canales externos (Discord, LinkedIn, X), ya sea por despacho individual (`POST /api/v1/mototradis/publish-channel` / `/api/v1/content-workflow/publish-channel`) o por aprobación colectiva HITL (`POST /api/v1/mototradis/hitl-decision` / `/api/v1/content-workflow/hitl-decision`), **EL SISTEMA DEBERÁ** verificar rigurosamente la respuesta de cada API externa y NUNCA reportar `ok: true` ni `estado_canal: "enviado"` a menos que se cumplan las siguientes condiciones específicas:
  1. **Discord (Emisor `CloudEdTech_Oficial` con `?wait=true`):** La petición debe emitirse como `CloudEdTech_Oficial` y retornar código de estado HTTP 200 o 201 conteniendo un identificador de mensaje válido (`message_id`). Para envíos vía Webhook, la URL deberá incluir taxativamente el parámetro `?wait=true` para forzar a Discord a retornar el objeto del mensaje publicado con su `id`, evitando el código 204 sin cuerpo.
  2. **LinkedIn (Adaptador Autónomo en `puente_motor_ia.py`):** Sin modificar `src/publishers.py`, la petición al endpoint `ugcPosts` debe ejecutarse mediante un adaptador autónomo en el puente que verifique código HTTP 201 y capture el URN de recurso generado (`urn:li:share:...` o `urn:li:ugcPost:...`).
  3. **X / Twitter (Adaptador Autónomo en `puente_motor_ia.py`):** Sin modificar `src/publishers.py`, la petición de creación de tweet debe ejecutarse mediante un adaptador autónomo en el puente que verifique el éxito de la llamada y capture el identificador numérico devuelto por la API v2 de X.
  4. **SI** cualquiera de los despachos falla por credenciales ausentes o inválidas, rechazo de red, rate limit o excepción técnica, **EL SISTEMA DEBERÁ** retornar estrictamente `ok: false`, asignar `estado_canal: "error"` (u `"omitido_sin_credenciales"`) e incluir en `detalle` el mensaje exacto del motivo del fallo, suprimiendo cualquier retorno estático que asuma publicación exitosa sin confirmación de la API.
- **POR QUÉ:** Cumple la Constitución protegiendo `src/publishers.py`, garantiza identidad unificada en Discord, corrige la falla de falsos positivos en el backend y certifica publicaciones que existen fácticamente en las redes sociales.

---

### RF-006: Captura de Identificadores y Enlaces Directos Canónicos de Publicación
- **CUANDO** una publicación en LinkedIn o X se complete exitosamente conforme al RF-005, **EL SISTEMA DEBERÁ** construir y retornar en el objeto de resultado la URL canónica y directa a la publicación efectuada:
  * Para **LinkedIn:** La URL directa con formato canónico exacto: `https://www.linkedin.com/feed/update/{urn}` utilizando el URN retornado por la API corporativa.
  * Para **X (Twitter):** La URL directa con formato canónico: `https://x.com/CloudEdTech_1/status/{id}` utilizando el identificador numérico retornado por la API v2.
- **POR QUÉ:** Permite a los redactores y revisores auditar de inmediato la publicación en vivo mediante un enlace directo oficial sin requerir búsquedas manuales.

---

### RF-007: Fidelidad Visual de la Mesa de Trabajo, Ciclo de Vida y Reintento en Publicaciones Parciales
- **MIENTRAS** el operador interactúe con la Mesa de Trabajo Multicanal en `ContentStudio.tsx`:
  1. **SI** un canal individual o un canal dentro de un despacho global HITL resulta en `estado_canal === "enviado"`:
     * **EL SISTEMA DEBERÁ** marcar la tarjeta de dicho canal con la insignia verde `✓ Publicado en {Red}`, inhabilitar su botón de publicación individual para evitar duplicados y mostrar el enlace verificado directo devuelto por la API (RF-006).
  2. **SI** un canal individual o un canal dentro de un despacho global HITL resulta en `estado_canal === "error"` o `ok === false` (Publicación Parcial):
     * **EL SISTEMA DEBERÁ** mantener la tarjeta del canal fallido plenamente activa y editable.
     * **EL SISTEMA DEBERÁ** mostrar dentro de la tarjeta o en el encabezado un banner de error rojo destacado con el motivo técnico devuelto por el servidor y un botón visible de reintento (`Reintentar publicación en {Red}`).
     * **EL SISTEMA DEBERÁ** garantizar que el reintento despache exclusivamente el canal seleccionado sin re-ejecutar las publicaciones en los canales que ya tuvieron éxito.
  3. **EL SISTEMA DEBERÁ** excluir el mensaje de la *Bandeja de mensajes en Redacción* únicamente si al menos un canal fue confirmado con `estado_canal === "enviado"`, manteniéndolo siempre activo en la Mesa de Trabajo hasta que el operador complete o descarte los canales pendientes. Si todos los canales fallaron, el mensaje permanecerá visible en la bandeja como pendiente.
- **POR QUÉ:** Garantiza transparencia total en la interfaz, evita duplicación de publicaciones exitosas ante fallos de canales hermanos y proporciona una experiencia de reintento granular y fluida.

---

### RF-008: Resiliencia, Tolerancia HTML y Respuestas de Soporte bajo `CloudEdTech_Oficial`
- **CUANDO** el operador confirme el envío de una respuesta a una queja comunitaria (`POST /api/v1/content-workflow/complaints/publish-response`):
  1. **EL SISTEMA DEBERÁ** canalizar la respuesta en Discord bajo la identidad de `CloudEdTech_Oficial` mediante el webhook de soporte/PQRS configurado (`DISCORD_WEBHOOK_PQRS`) anexando `?wait=true`, o mediante la Bot API oficial si cuenta con permisos directos en el canal.
  2. **SI** la petición es rechazada con código HTTP 429 (Cloudflare Error 1015 / Rate Limit), **EL SISTEMA DEBERÁ** capturar la excepción tolerando respuestas en formato HTML sin emitir `JSONDecodeError` y garantizando la inclusión de cabeceras CORS.
  3. **SI** el envío falla por límite de tasa, **EL SISTEMA DEBERÁ** retornar una respuesta HTTP 429 estructurada explicando que Discord limitó temporalmente las peticiones en la nube y recomendando reintentar en unos minutos o responder desde local.
  4. En la interfaz de `ContentStudio.tsx`, **EL SISTEMA DEBERÁ** capturar la respuesta sin romper la vista del panel de quejas y notificar claramente el diagnóstico al usuario.
- **POR QUÉ:** Mantiene la operatividad del canal de soporte comunitario bajo la identidad institucional oficial sin colapsar el flujo de atención al cliente.

---

### RF-009: Inviolabilidad Constitucional y Aislamiento Absoluto de Código Base
- **MIENTRAS** se implementen todas las directivas de resiliencia, diagnósticos de rate limit y validación de publicaciones, **EL SISTEMA DEBERÁ** mantener estrictamente inalterados los 17 archivos protegidos de la raíz (`armar_json_bot_python.py`, `anuncios_discord.py`, `base_datos.py`, `procesamiento.py`, etc.), así como las carpetas canónicas `src/` (con énfasis taxativo en la inmutabilidad de `src/publishers.py`), `backend/` y `motor-ia/`. Toda la lógica de servidor residirá como adaptadores autónomos en `puente_motor_ia.py` y toda la lógica de cliente residirá en `frontend/src/`.
- **POR QUÉ:** Cumple sin excepciones con `docs/constitution.md` y `AGENTS.md`, salvaguardando la integridad del pipeline histórico del proyecto.

---

### RF-010: Identidad Unificada del Emisor en Discord (`CloudEdTech_Oficial`) y Separación de Agente Extractor
- **CUANDO** el sistema despache cualquier comunicación hacia Discord (anuncios oficiales en `/content`, copys multicanal aprobados desde la mesa de trabajo o respuestas a quejas y soporte), **EL SISTEMA DEBERÁ** canalizar la emisión bajo la identidad pública oficial y avatar de **`CloudEdTech_Oficial`** mediante su integración de webhook configurada (`DISCORD_WEBHOOK_ANUNCIOS`, `DISCORD_WEBHOOK_GENERAL`, `DISCORD_WEBHOOK_PQRS` o `DISCORD_WEBHOOK_OFICIAL`), asegurando el parámetro `?wait=true` para auditar la recepción con código HTTP 200/201 y `message_id`.
- **MIENTRAS** el sistema ejecute la sincronización e ingesta de mensajes (`POST /api/v1/discord/sync`), **EL SISTEMA DEBERÁ** mantener al bot extractor de datos (`DISCORD_TOKEN` / `DISCORD_BOT_TOKEN`) restringido exclusivamente a tareas de extracción pasiva de historial y telemetría de canales, disociándolo por completo de la emisión pública de contenidos.
- **POR QUÉ:** Cumple el requerimiento expreso del usuario, unificando la presencia institucional de cara a la comunidad estudiantil para que todos los comunicados provengan inequívocamente de `CloudEdTech_Oficial`, eliminando la ambigüedad de remitentes y previniendo colisiones operativas con el bot extractor de datos.

---

## 3. Criterios de Aceptación y Escenarios de Verificación

### Escenario 1: Sincronización en la Nube con IP Rate-Limited (Cloudflare 1015 en HTML)
- **Acción:** El usuario pulsa *Sincronizar Discord* en `/messages` y el servidor en Render recibe un bloqueo HTTP 429 de Cloudflare con cuerpo `text/html`.
- **Resultado Esperado:** El backend procesa el cuerpo sin lanzar `JSONDecodeError`, retorna status HTTP 429 con cabeceras CORS y JSON estructurado. En la interfaz aparece un banner claro y amigable sugiriendo sincronizar desde local o esperar unos minutos; no aparece el mensaje opaco `Failed to fetch` y el botón vuelve a estar habilitado.

### Escenario 2: Despacho de Anuncios Oficiales bajo `CloudEdTech_Oficial` con `?wait=true`
- **Acción:** Se publica un anuncio oficial hacia `#notificaciones`.
- **Resultado Esperado:** El despacho se emite mediante el webhook oficial de `CloudEdTech_Oficial` con el parámetro `?wait=true`. Discord entrega status HTTP 200 con el `message_id`, el mensaje aparece en Discord con el avatar y nombre `CloudEdTech_Oficial`, y se audita en `contenidos_generados`.

### Escenario 3: Rechazo de Publicación en Redes Sociales (Cero Falsos Positivos)
- **Acción:** En la Mesa de Trabajo de Redacción, el usuario pulsa *Publicar en Discord*, *Publicar en X* o *Publicar en LinkedIn*, y la API externa rechaza la solicitud (por rate limit, credenciales inválidas o error de red).
- **Resultado Esperado:**
  1. El backend retorna `ok: false`, `estado_canal: "error"` y el detalle real del rechazo.
  2. En la UI, la tarjeta **NO** muestra la insignia verde `✓ Publicado en...` ni desactiva su botón en estado publicado.
  3. La UI despliega un banner rojo con el mensaje de error exacto.
  4. La base de datos SQLite no marca la interacción ni el contenido como "publicado".

### Escenario 4: Publicación Exitosa con Identificadores Reales y Enlaces Canónicos
- **Acción:** Se publica exitosamente un tweet en X o un artículo en LinkedIn.
- **Resultado Esperado:**
  1. Para X, la API v2 retorna el ID del tweet (ej. `123456789`), el backend lo captura y devuelve la URL canónica `https://x.com/CloudEdTech_1/status/123456789`.
  2. Para LinkedIn, la API confirma HTTP 201 con el URN generado (ej. `urn:li:share:987654321`) y se devuelve la URL canónica `https://www.linkedin.com/feed/update/urn:li:share:987654321`.
  3. La UI marca el badge verde `✓ Publicado en...` y ofrece el enlace directo para verificar la publicación en vivo.

### Escenario 5: Publicación Parcial HITL y Reintento Granular
- **Acción:** En la Mesa de Trabajo se aprueba un lote HITL donde Discord se publica con éxito pero X falla por límite de peticiones o credenciales.
- **Resultado Esperado:**
  1. La tarjeta de Discord se marca inmediatamente como `✓ Publicado en Discord` en verde con su enlace/id y botón inhabilitado.
  2. La tarjeta de X muestra un banner de error rojo con el motivo devuelto por la API de X y mantiene habilitado el botón de reintento (`Reintentar publicación en X`).
  3. Al pulsar reintentar en X tras solucionar el problema, se despacha únicamente a X sin duplicar el post en Discord.
  4. El mensaje desaparece de la bandeja de mensajes en redacción pero se conserva activo en la mesa de trabajo hasta finalizar.

### Escenario 6: Manejo de Rate Limit en el Panel de Quejas con Tolerancia HTML
- **Acción:** Se confirma el envío de respuesta a una queja hacia Discord cuando la IP del servidor sufre rate limit 429 con respuesta HTML de Cloudflare.
- **Resultado Esperado:** El sistema tolera el cuerpo HTML sin crashear, canaliza como `CloudEdTech_Oficial` con `?wait=true`; si falla o no está configurado, retorna status 429 estructurado con CORS y la UI exhibe el mensaje diagnóstico sin colapsar el formulario ni la lista de quejas.

### Escenario 7: Verificación de Identidad del Emisor Oficial (`CloudEdTech_Oficial`)
- **Acción:** Se inspecciona cualquier publicación saliente en Discord (anuncio oficial, publicación multicanal de mesa de trabajo o respuesta de quejas).
- **Resultado Esperado:** En el cliente de Discord, el autor del mensaje se muestra inequívocamente como `CloudEdTech_Oficial` con su avatar e indicador de aplicación/bot. El bot extractor de lectura (`DISCORD_TOKEN`) no emite mensajes públicos y opera únicamente en la ingesta pasiva de mensajes.
