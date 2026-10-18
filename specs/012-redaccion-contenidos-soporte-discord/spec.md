# Spec 012: Redacción de Contenidos, Soporte a Quejas con Selector de IA y Publicación en Discord

## 1. Contexto y Propósito (QUÉ y POR QUÉ)

### ¿Qué se solicita?
Transformar la pestaña de **Redacción de Contenidos** (`frontend/src/pages/ContentStudio.tsx` - espacio de trabajo de Enoc) en un entorno 100% operativo y conectado a datos reales que permita:
1. **Atención y soporte crítico a quejas de Discord con selector de IA multimodelo**: Habilitar en el modal de quejas la selección entre los tres proveedores de IA del sistema (Groq Llama 3.3, Google Gemma 4 y Google Gemini Flash Lite), garantizando que el selector se deshabilite durante peticiones en curso, generar propuestas empáticas y contextualizadas mediante el endpoint `POST /api/v1/content-workflow/complaints/generate-response` sin sustituciones silenciosas de modelo, verificar el canal destino y mensaje original con `GET /api/v1/content-workflow/complaints/{interaccion_id}/publish-preview` (notificando con precisión si el bot no está configurado o si el mensaje no existe en Discord), publicar la respuesta directamente en Discord usando el bot oficial (`POST /api/v1/content-workflow/complaints/publish-response`), y excluir automáticamente las quejas ya respondidas mediante `GET /api/v1/content-workflow/complaints/published-responses` con persistencia en SQLite.
2. **Revisión integral de la mesa de trabajo de copywriting con selector de IA**: Erradicar el uso de datos simulados (`mockCommunityData.content_studio[0]`) para que la mesa de trabajo y los editores de formato (LinkedIn, X, Discord) operen con el mensaje real seleccionado de la bandeja (`selectedWorkflowMessage`), incorporar un selector de modelo de IA en la cabecera de la mesa de trabajo para controlar la regeneración de contenidos mediante `POST /api/v1/content-workflow/regenerate` garantizando una longitud estricta `<= 280` caracteres para el formato X, y persistir borradores avanzando la interacción a la etapa de aprobación mediante `POST /api/v1/content-workflow/drafts` de forma independiente por cada formato sin expulsar prematuramente la interacción de la mesa de trabajo.
3. **Respeto absoluto a la Constitución del Proyecto**: Garantizar la inmutabilidad de los 17 archivos preexistentes en la raíz, así como de las carpetas `backend/` y `motor-ia/`, concentrando la adaptación técnica en `puente_motor_ia.py`, `frontend/src/` y `tests/`.

### ¿Por qué es necesario?
Actualmente, el flujo de trabajo de Redacción y Soporte presenta bloqueos críticos identificados directamente por los usuarios y el equipo de operaciones:
1. **Fallo en generación de respuestas a quejas ("Not Found")**: Al pulsar el botón "Generar con IA" dentro del modal "Preparar respuesta", el frontend invoca `POST /api/v1/content-workflow/complaints/generate-response`, el cual no existe en el adaptador unificado (`puente_motor_ia.py`), produciendo un error HTTP 404 que imposibilita la asistencia automática al operador de comunidad.
2. **Ausencia de selección del motor de IA**: El usuario solicitó expresamente que la persona que atiende la queja pueda decidir qué inteligencia artificial utilizar (Groq Llama 3.3, Google Gemma 4 o Google Gemini Flash Lite). Actualmente el sistema no ofrece ningún selector visual ni parámetro en la petición para elegir el motor generador, ni en las quejas ni en la mesa de trabajo.
3. **Botón de publicación en Discord permanentemente deshabilitado**: Aunque el operador redacte una respuesta de forma manual en el modal, el botón "Enviar respuesta a Discord" permanece inactivo debido a que falta el endpoint `GET /api/v1/content-workflow/complaints/{interaccion_id}/publish-preview` que comprueba la existencia y permisos del canal de Discord, y falta el endpoint `POST /api/v1/content-workflow/complaints/publish-response` que ejecuta el envío.
4. **Uso no canalizado de integraciones de Discord**: El usuario instruyó formalmente que el envío de respuestas se realice exclusivamente mediante el bot oficial de anuncios y comunidad configurado en el sistema (`DISCORD_BOT_TOKEN` / `DISCORD_TOKEN`), garantizando que las respuestas se envíen como contestaciones directas (*reply*) vinculadas al mensaje original en el canal correspondiente.
5. **Persistencia y eliminación de quejas atendidas**: La lista de posibles quejas no oculta aquellas que ya han sido respondidas porque el endpoint `GET /api/v1/content-workflow/complaints/published-responses` devuelve una lista vacía fija (`{"interaction_ids": []}`), lo que genera confusión y riesgo de respuestas duplicadas. Se requiere persistir las quejas atendidas en una tabla SQLite (`respuestas_quejas_discord`) para que sobrevivan a reinicios.
6. **Mesa de trabajo desacoplada de la selección de mensajes**: En `ContentStudio.tsx`, la carga inicial y varios estados de los editores continúan amarrados al objeto estático de prueba `mockCommunityData.content_studio[0]` en lugar de consumir dinámicamente los datos del mensaje en redacción activo, y los botones de regeneración de contenido y guardado de borradores no cuentan con sus respectivos endpoints activos en el puente unificado.

---

## 2. Requerimientos Funcionales (Formato EARS)

### RF-01: Selector de Proveedor de IA y Generación de Respuestas a Quejas
- **CUANDO** el usuario abra el modal "Preparar respuesta" de una interacción en el Panel de Quejas, Reclamos y Soporte Crítico, **EL SISTEMA DEBERÁ** presentar un control selector que permita escoger explícitamente entre los tres proveedores de IA del sistema:
  1. Groq (Llama 3.3) — Opción predeterminada.
  2. Google Gemma 4.
  3. Google Gemini Flash Lite.
- **CUANDO** el usuario pulse el botón "Generar con IA", **EL SISTEMA DEBERÁ** mostrar un indicador visual de generación en progreso ("Generando respuesta...") e invocar `POST /api/v1/content-workflow/complaints/generate-response` enviando el identificador de la interacción (`interaccion_id`) y el identificador o nombre normalizado del proveedor seleccionado (`proveedor`).
- **MIENTRAS** la generación de respuesta esté en curso ("Generando respuesta..."), **EL SISTEMA DEBERÁ** deshabilitar tanto el botón de acción "Generar con IA" como el propio control selector de proveedor de IA (Groq, Gemma, Gemini), impidiendo modificaciones de modelo desfasadas durante la petición en vuelo.
- **MIENTRAS** el backend procese la solicitud de generación, **EL SISTEMA DEBERÁ** buscar la interacción en el repositorio de datos (SQLite / Supabase), extraer su texto y canal, normalizar el proveedor de IA solicitado mediante la función de mapeo unificado, y generar un borrador estructurado de respuesta aplicando las pautas institucionales de atención (empatía, claridad, no inventar hechos ni promesas no autorizadas, y no solicitar credenciales sensibles).
- **SI** la interacción solicitada no existe, **EL SISTEMA DEBERÁ** responder con código **HTTP 404 Not Found** y el mensaje descriptivo correspondiente.
- **SI** la interacción carece de texto o su contenido está compuesto únicamente por espacios en blanco, **EL SISTEMA DEBERÁ** responder con código **HTTP 422 Unprocessable Entity**.
- **SI** el proveedor de IA seleccionado carece de credenciales configuradas en el entorno (por ejemplo, `GROQ_API_KEY` o `GOOGLE_API_KEY`) o su API externa falla (por límite de cuota o indisponibilidad), **EL SISTEMA DEBERÁ** responder con código **HTTP 502 Bad Gateway** o **HTTP 503 Service Unavailable** detallando explícitamente qué proveedor falló y la causa técnica reportada.
- **EL SISTEMA DEBERÁ** abstenerse categóricamente de realizar sustituciones o fallbacks silenciosos hacia otros motores de IA no seleccionados por el usuario, preservando la transparencia técnica y la soberanía del operador.
- **CUANDO** la generación concluya exitosamente, **EL SISTEMA DEBERÁ** poblar el área de texto editable ("Respuesta editable") con el texto devuelto, permitiendo al operador humano modificarlo libremente antes de confirmar cualquier envío.

### RF-02: Verificación y Vista Previa de Destino en Discord
- **CUANDO** se abra el modal de preparación de respuesta para una queja (`activeComplaint !== null`), **EL SISTEMA DEBERÁ** invocar de forma automática y asíncrona `GET /api/v1/content-workflow/complaints/{interaccion_id}/publish-preview`.
- **MIENTRAS** se procese la verificación del destino, **EL SISTEMA DEBERÁ** mostrar un estado visual de comprobación en curso ("Verificando el destino con el backend...").
- **CUANDO** `GET /api/v1/content-workflow/complaints/{interaccion_id}/publish-preview` reciba la consulta, **EL SISTEMA DEBERÁ** verificar la existencia de la interacción, su identificador de canal (`channel_id`), nombre de canal (`channel_name`), identificador del mensaje de origen en Discord (`source_message_id`), autor original y contenido textual.
- **SI** las credenciales del bot de Discord (`DISCORD_BOT_TOKEN` o `DISCORD_TOKEN`) no están configuradas en las variables de entorno, **EL SISTEMA DEBERÁ** responder con código **HTTP 200 OK**, `ready: false`, y el mensaje descriptivo `"Bot de Discord no configurado en el servidor"`, permitiendo que la interfaz informe con precisión la falta de credenciales sin arrojar un error HTTP 500 no controlado.
- **SI** el bot se encuentra activo pero el mensaje original no existe o fue eliminado de Discord (`discord.NotFound`), **EL SISTEMA DEBERÁ** responder con código **HTTP 404 Not Found** y el detalle `"El mensaje original ya no existe en Discord"`, sin intentar envíos huérfanos sin referencia ni aplicar fallbacks silenciosos.
- **SI** la interacción contiene los metadatos de canal y mensaje necesarios para responder y el bot de Discord cuenta con credenciales activas y acceso verificado, **EL SISTEMA DEBERÁ** retornar un objeto con `ready: true`, el identificador y nombre del canal verificado, el autor y el extracto del mensaje original.
- **CUANDO** la verificación de destino resulte afirmativa (`ready: true`), **EL SISTEMA DEBERÁ** mostrar el panel verde de "Destino verificado por el backend" con el canal (`#nombre-canal`), autor original y mensaje, habilitando el botón "Enviar respuesta a Discord" una vez que el usuario haya ingresado o generado un texto de respuesta.
- **SI** la verificación del destino resulta fallida (`ready: false`) o pendiente, **EL SISTEMA DEBERÁ** mantener deshabilitado el botón "Enviar respuesta a Discord" e informar al usuario la causa exacta para impedir publicaciones accidentales en canales incorrectos o inexistentes.

### RF-03: Publicación Oficial de Respuestas Mediante el Bot de Discord
- **MIENTRAS** el texto de la respuesta esté vacío, contenga solo espacios en blanco, o supere los 2000 caracteres (límite estricto de Discord), **EL SISTEMA DEBERÁ** mantener deshabilitado el botón "Enviar respuesta a Discord".
- **CUANDO** el usuario pulse "Enviar respuesta a Discord" con el destino verificado (`ready: true`) y un texto válido, **EL SISTEMA DEBERÁ** solicitar una confirmación explícita mediante diálogo de advertencia mostrando el canal de destino y el contenido exacto a enviar.
- **SI** el usuario rechaza o cancela la confirmación, **EL SISTEMA DEBERÁ** abortar la operación sin alterar el estado del formulario ni realizar llamadas de red.
- **CUANDO** el usuario confirme la publicación, **EL SISTEMA DEBERÁ** bloquear inmediatamente la interfaz contra clics repetidos, mostrar el estado "Publicando..." e invocar `POST /api/v1/content-workflow/complaints/publish-response` enviando `{"interaccion_id": int, "respuesta": str, "confirmado": true}`.
- **MIENTRAS** el backend ejecute `POST /api/v1/content-workflow/complaints/publish-response`, **EL SISTEMA DEBERÁ** autenticarse contra la API de Discord utilizando el bot oficial configurado mediante `DISCORD_BOT_TOKEN` o `DISCORD_TOKEN`, ubicar el canal correspondiente y publicar la respuesta como contestación directa (*reply* / *message reference*) al mensaje original de Discord (`source_message_id`), asegurando que las menciones accidentales masivas queden deshabilitadas (`allowed_mentions=none`).
- **SI** las credenciales del bot de Discord no están configuradas en el entorno (`DISCORD_BOT_TOKEN` ni `DISCORD_TOKEN`), **EL SISTEMA DEBERÁ** responder con código **HTTP 502 Bad Gateway** indicando la falta de configuración de autenticación.
- **SI** Discord rechaza el envío debido a falta de permisos, canal inexistente o mensaje original eliminado, **EL SISTEMA DEBERÁ** capturar la excepción y responder con código **HTTP 502 Bad Gateway** o **HTTP 404 Not Found** detallando la razón del rechazo.
- **CUANDO** la publicación en Discord culmine satisfactoriamente, **EL SISTEMA DEBERÁ** registrar la respuesta en la tabla persistente de SQLite `respuestas_quejas_discord`, asociar el identificador del mensaje retornado por Discord (`discord_message_id`), marcar la interacción como atendida, y responder con estado **HTTP 200 OK** conteniendo `estado: "publicado"`, `interaccion_id`, `discord_message_id` y `channel_id`.
- **CUANDO** el frontend reciba la confirmación de publicación exitosa, **EL SISTEMA DEBERÁ** mostrar el mensaje de éxito en verde indicando el canal y el identificador del mensaje en Discord, bloquear el editor para evitar reenvíos, y actualizar el listado de quejas pendientes.

### RF-04: Exclusión Automática y Registro Persistente de Quejas Atendidas
- **CUANDO** una respuesta a una queja sea publicada en Discord mediante `POST /api/v1/content-workflow/complaints/publish-response`, **EL SISTEMA DEBERÁ** registrar el evento de forma persistente en la tabla SQLite `respuestas_quejas_discord` (almacenando `interaccion_id`, `canal_id`, `discord_message_id`, `respuesta`, `publicado_en`, `autor_respuesta`).
- **CUANDO** el backend reciba una consulta a `GET /api/v1/content-workflow/complaints/published-responses`, **EL SISTEMA DEBERÁ** consultar la tabla persistente `respuestas_quejas_discord` y retornar la lista de enteros correspondiente: `{"interaction_ids": [id1, id2, ...]}`.
- **CUANDO** el frontend consulte `GET /api/community/complaints` para listar las posibles quejas e invoque simultáneamente `getPublishedComplaintIds()`, **EL SISTEMA DEBERÁ** filtrar automáticamente el arreglo excluyendo todas aquellas interacciones cuyo identificador figure en el conjunto de respuestas publicadas (`publishedSet`).
- **CUANDO** una queja sea publicada exitosamente en el modal, **EL SISTEMA DEBERÁ** incorporar de inmediato su identificador en el registro de publicadas y removerla del listado activo en pantalla sin requerir una recarga completa de la página.
- **EL SISTEMA DEBERÁ** garantizar que las quejas atendidas permanezcan excluidas del panel activo de forma determinista, sobreviviendo a recargas de pantalla, reinicios del backend y sesiones concurrentes.

### RF-05: Conexión Real de la Mesa de Trabajo y Erradicación de Mocks en Redacción
- **MIENTRAS** el usuario trabaje en la pestaña de Redacción de Contenidos (`/content`), **EL SISTEMA DEBERÁ** prescindir por completo de datos quemados o estáticos procedentes de `mockCommunityData.content_studio[0]`.
- **CUANDO** se cargue la bandeja de mensajes en redacción (`workflow_stage === 'en_redaccion'`), **EL SISTEMA DEBERÁ** seleccionar automáticamente la primera interacción disponible (o preservar la interacción previamente seleccionada) y alimentar con sus valores reales (`author`, `channel`, `content`, `topic`, `sentiment`, `relevance`, `attachments`) la tarjeta "Mensaje original de Discord".
- **CUANDO** el usuario seleccione una interacción de la bandeja o pulse "Usar para redactar" / "Preparar contenido en el editor", **EL SISTEMA DEBERÁ** inicializar los borradores de los tres formatos de distribución (LinkedIn, X, Discord) tomando como base directa el texto real, autor, canal y temas de la interacción seleccionada.
- **SI** no existen mensajes con etapa `en_redaccion` en el sistema, **EL SISTEMA DEBERÁ** presentar un estado vacío informativo ("No hay mensajes pendientes de redacción") en lugar de recurrir a contenidos ficticios pregrabados.

### RF-06: Selector de IA en Mesa de Trabajo y Regeneración de Copys Adaptados por Formato
- **CUANDO** el usuario visualice la cabecera de la sección "Contenido generado" en la mesa de trabajo (`ContentStudio.tsx`), **EL SISTEMA DEBERÁ** presentar un control selector de modelo de IA (Groq Llama 3.3, Google Gemma 4, Google Gemini Flash Lite) que determine el motor generador para todas las tarjetas de copy.
- **CUANDO** el usuario pulse el botón "Regenerar" en cualquiera de las tarjetas de formato (LinkedIn, X o Discord), **EL SISTEMA DEBERÁ** invocar `POST /api/v1/content-workflow/regenerate` enviando el texto del mensaje original seleccionado, el canal de Discord de origen, el formato solicitado (`linkedin`, `x`, `discord`), el tono deseado (`profesional`, `cercano`, etc.) y el proveedor de IA seleccionado en dicho control (`proveedor`).
- **MIENTRAS** se procese la regeneración de cualquiera de los formatos, **EL SISTEMA DEBERÁ** deshabilitar el selector de IA de la mesa de trabajo, así como los botones de acción de la tarjeta afectada, mostrando una animación de giro en el ícono de recarga ("Regenerando...").
- **MIENTRAS** el backend elabore el contenido, **EL SISTEMA DEBERÁ** utilizar la plantilla de copy especializada de CloudEdTech y el motor de IA correspondiente para producir:
  1. Si el formato es **LinkedIn**: Una publicación estructurada con gancho, desarrollo profesional, llamada a la acción clara y entre 3 y 5 hashtags representativos.
  2. Si el formato es **X**: Un texto conversacional conciso garantizado en `<= 280` caracteres.
  3. Si el formato es **Discord**: Un mensaje comunitario, amigable y cercano, que fomente la participación colectiva.
- **MIENTRAS** el backend elabore o entregue el contenido para el formato X, **EL SISTEMA DEBERÁ** garantizar de manera determinista y estricta que la longitud final del texto sea menor o igual a 280 caracteres (`len(contenido) <= 280`).
- **SI** el texto retornado por el modelo de IA para el formato X excede los 280 caracteres, **EL SISTEMA DEBERÁ** recortar o truncar el texto en el servidor respetando las fronteras de palabras completas antes de entregarlo al cliente, asegurando que el frontend nunca reciba un contenido que exceda los 280 caracteres.
- **CUANDO** la regeneración finalice exitosamente, **EL SISTEMA DEBERÁ** actualizar el contenido editable de la tarjeta correspondiente sin alterar los borradores de los otros formatos ni sobreescribir modificaciones de otras tarjetas.

### RF-07: Persistencia Independiente de Borradores y Avance del Flujo a Aprobación
- **MIENTRAS** el redactor trabaje en la mesa de trabajo, **EL SISTEMA DEBERÁ** gestionar el estado de cada formato (LinkedIn, X, Discord) de forma totalmente independiente, permitiendo guardar el borrador de cada uno en `contenidos_generados` mediante `POST /api/v1/content-workflow/drafts` con su respectivo identificador autoincremental (`savedId`).
- **CUANDO** el redactor pulse el botón "Enviar a aprobación" en cualquiera de las tarjetas de formato con un texto válido (y que en el caso de X no supere los 280 caracteres), **EL SISTEMA DEBERÁ** invocar `POST /api/v1/content-workflow/drafts` enviando la información estructurada del borrador:
  - `interaccion_id`: Identificador numérico de la interacción de origen (si aplica).
  - `plataforma`: Identificador del formato (`linkedin`, `x`, `discord`).
  - `titulo`: Título descriptivo generado o editado.
  - `contenido`: Texto definitivo redactado por el usuario.
  - `llamada_accion`: Frase de cierre o llamado a la acción.
  - `hashtags`: Lista de etiquetas temáticas.
  - `tono`: Tono de redacción empleado.
  - `tipo_contenido`: Tipo de publicación.
- **MIENTRAS** el backend procese la solicitud, **EL SISTEMA DEBERÁ** registrar el borrador en la tabla `contenidos_generados` asignándole el estado inicial `pendiente_revision`, y responder con **HTTP 200 OK** (o **HTTP 201 Created**) conteniendo `id: int`, `estado: "pendiente_revision"` y un mensaje de éxito.
- **CUANDO** el borrador haya sido persistido exitosamente, **EL SISTEMA DEBERÁ** marcar la tarjeta correspondiente como "Enviado a aprobación" en color verde y mostrar la insignia "Borrador #ID guardado para revisión".
- **CUANDO** se confirme el guardado y avance de un formato, **EL SISTEMA DEBERÁ** mantener la interacción activa y seleccionada en la mesa de trabajo para que el redactor continúe trabajando y guardando los formatos restantes sin expulsar prematuramente la interacción de la pantalla.
- **EL SISTEMA DEBERÁ** actualizar la etapa de la interacción original a `en_aprobacion` en la base de datos sin interrumpir la sesión de edición activa del usuario en los demás formatos del mensaje.

### RF-08: Inviolabilidad Constitucional, Aislamiento de Código y Calidad TDD
- **MIENTRAS** se implementen todas las soluciones de backend y frontend para la pestaña de Redacción y Soporte, **EL SISTEMA DEBERÁ** mantener intactos e inalterados los 17 archivos históricos preexistentes en la raíz del proyecto (`armar_json_bot_python.py`, `anuncios_discord.py`, `base_datos.py`, `modelos.py`, etc.), así como las carpetas `backend/` y `motor-ia/`.
- **EL SISTEMA DEBERÁ** incorporar toda la lógica de adaptación, endpoints y orquestación exclusivamente en `puente_motor_ia.py`, en los componentes y clientes de `frontend/src/` y en las suites de pruebas automatizadas de `tests/`.
- **EL SISTEMA DEBERÁ** validar cada funcionalidad implementada mediante pruebas automatizadas rigurosas antes de dar por concluida la especificación, preservando el 100% de las pruebas existentes en estado verde.

---

## 3. Contratos de API, Modelos de Datos y Casos Límite (Edge Cases)

### 3.1 Contratos de API

#### 1. `POST /api/v1/content-workflow/complaints/generate-response`
- **Descripción**: Genera una propuesta de respuesta a una queja o reclamo empleando el proveedor de IA seleccionado por el operador, sin sustituciones silenciosas.
- **Campos de Entrada (JSON)**:
  - `interaccion_id` (entero, obligatorio): ID de la interacción en la base de datos.
  - `proveedor` (cadena, opcional, por defecto `"Groq (Llama 3.3)"`): Nombre o identificador del modelo (`"Groq (Llama 3.3)"`, `"Google Gemma 4"`, `"Google Gemini Flash Lite"`).
- **Campos de Salida Exitosa (HTTP 200 OK)**:
  - `interaccion_id` (entero): ID de la interacción.
  - `respuesta` (cadena): Texto propuesto en español, empático y profesional.
  - `proveedor_usado` (cadena): Nombre del proveedor de IA que generó el texto.
  - `estado` (cadena): `"borrador"`.
  - `requiere_revision` (booleano): `true`.
- **Errores Posibles**:
  - `400 Bad Request`: Si el proveedor indicado no es reconocido o el ID es inválido.
  - `404 Not Found`: Si la interacción no existe en la base de datos.
  - `422 Unprocessable Entity`: Si la interacción no tiene texto para responder.
  - `502 Bad Gateway`: Si el servicio de IA seleccionado carece de credenciales o falla externamente (indicando el proveedor exacto en el detalle).
  - `503 Service Unavailable`: Si el proveedor seleccionado no está disponible temporalmente.

#### 2. `GET /api/v1/content-workflow/complaints/{interaccion_id}/publish-preview`
- **Descripción**: Inspecciona y verifica el canal de Discord, mensaje original y autorización del bot antes de habilitar la publicación.
- **Parámetro de Ruta**: `interaccion_id` (entero).
- **Campos de Salida Exitosa (HTTP 200 OK)**:
  - `interaccion_id` (entero): ID de la interacción verificada.
  - `guild_id` (cadena): ID del servidor de Discord asociado.
  - `channel_id` (cadena): ID numérico del canal de Discord (ej. `"1559244209884504245"`).
  - `channel_name` (cadena): Nombre legible del canal (ej. `"pqrs"` o `"general"`).
  - `source_message_id` (cadena): ID del mensaje de Discord al que se responderá.
  - `author` (cadena): Nombre o identificador del autor original.
  - `original_content` (cadena): Texto original de la queja.
  - `ready` (booleano): `true` si el destino es válido y el bot puede publicar; `false` si el bot no está configurado en el servidor o faltan datos.
  - `detail` (cadena, opcional): Mensaje explicativo cuando `ready` es `false` (ej. `"Bot de Discord no configurado en el servidor"`).
- **Errores Posibles**:
  - `400 Bad Request`: Si el `interaccion_id` no es un entero positivo válido.
  - `404 Not Found`: Si la interacción no existe en el sistema o si el mensaje original no existe en Discord (`discord.NotFound`).

#### 3. `POST /api/v1/content-workflow/complaints/publish-response`
- **Descripción**: Publica la respuesta confirmada en el canal de Discord mediante el bot oficial del sistema como respuesta directa al mensaje original.
- **Campos de Entrada (JSON)**:
  - `interaccion_id` (entero, obligatorio): ID de la interacción.
  - `respuesta` (cadena, obligatoria, entre 1 y 2000 caracteres): Texto final revisado.
  - `confirmado` (booleano, obligatorio, debe ser `true`): Bandera de confirmación explícita del operador humano.
- **Campos de Salida Exitosa (HTTP 200 OK)**:
  - `estado` (cadena): `"publicado"`.
  - `interaccion_id` (entero): ID de la interacción atendida.
  - `discord_message_id` (cadena): ID del mensaje generado y entregado por Discord.
  - `channel_id` (cadena): ID del canal donde se publicó la respuesta.
- **Errores Posibles**:
  - `400 Bad Request`: Si `confirmado` es falso, la respuesta está vacía o excede 2000 caracteres.
  - `404 Not Found`: Si la interacción original o el mensaje original en Discord no existen.
  - `502 Bad Gateway`: Si Discord rechaza la autenticación del bot o el envío del mensaje.

#### 4. `GET /api/v1/content-workflow/complaints/published-responses`
- **Descripción**: Retorna la lista de identificadores de interacciones cuyas respuestas ya fueron publicadas en Discord, consultando la tabla persistente `respuestas_quejas_discord`.
- **Campos de Salida Exitosa (HTTP 200 OK)**:
  - `interaction_ids` (lista de enteros): Arreglo de IDs de interacciones atendidas (ej. `[12, 45, 89]`).

#### 5. `POST /api/v1/content-workflow/regenerate`
- **Descripción**: Regenera una propuesta de contenido adaptada para LinkedIn, X o Discord a partir del mensaje original, garantizando `<= 280` caracteres para X.
- **Campos de Entrada (JSON)**:
  - `texto` (cadena, obligatoria): Mensaje original de la comunidad.
  - `canal` (cadena, obligatoria): Nombre del canal de Discord de procedencia.
  - `formato` (cadena, obligatoria): Uno de `"linkedin"`, `"x"`, `"discord"`.
  - `tono` (cadena, opcional, por defecto `"profesional"`): Tono de comunicación.
  - `proveedor` (cadena, opcional): Proveedor de IA seleccionado (`"Groq (Llama 3.3)"`, `"Google Gemma 4"`, `"Google Gemini Flash Lite"`).
- **Campos de Salida Exitosa (HTTP 200 OK)**:
  - `formato` (cadena): El formato solicitado (`"linkedin"`, `"x"`, `"discord"`).
  - `titulo` (cadena): Título propuesto.
  - `contenido` (cadena): Texto del copy adaptado (para `"x"` garantizado estrictamente en `<= 280` caracteres mediante truncado de palabras en backend si excede).
  - `llamada_accion` (cadena): Llamado a la acción generado.
  - `hashtags` (lista de cadenas): Etiquetas temáticas recomendadas.
- **Errores Posibles**:
  - `400 Bad Request`: Si el formato no es válido o los campos requeridos están ausentes.
  - `422 Unprocessable Entity`: Si el texto está vacío.
  - `502 Bad Gateway`: Si el proveedor de IA falla externamente.

#### 6. `POST /api/v1/content-workflow/drafts`
- **Descripción**: Guarda un borrador de contenido de forma independiente en `contenidos_generados` y lo deja en estado `pendiente_revision`.
- **Campos de Entrada (JSON)**:
  - `interaccion_id` (entero, opcional): ID de la interacción vinculada.
  - `plataforma` (cadena, obligatoria): `"linkedin"`, `"x"` o `"discord"`.
  - `titulo` (cadena, obligatoria): Título de la pieza.
  - `contenido` (cadena, obligatoria): Contenido textual.
  - `llamada_accion` (cadena, opcional): Llamado a la acción.
  - `hashtags` (lista de cadenas, opcional): Arreglo de etiquetas.
  - `tono` (cadena, opcional): Tono utilizado.
  - `tipo_contenido` (cadena, opcional): Tipo de publicación.
- **Campos de Salida Exitosa (HTTP 200 OK o 201 Created)**:
  - `id` (entero): Identificador autoincremental del borrador creado.
  - `estado` (cadena): `"pendiente_revision"`.
  - `message` (cadena): Mensaje de confirmación de guardado.
- **Errores Posibles**:
  - `400 Bad Request`: Si faltan campos requeridos o el contenido está vacío.

---

### 3.2 Casos Límite (Edge Cases) y Mitigaciones

1. **Límite de caracteres en Discord (máximo 2000 caracteres)**:
   - *Riesgo*: Una respuesta que sobrepase 2000 caracteres provocará el rechazo inmediato de la API de Discord con código HTTP 400.
   - *Mitigación*: Validación preventiva en el cliente frontend (deshabilitando el botón de envío) y en el endpoint del backend (rechazando con HTTP 400 si excede el límite).
2. **Límite de caracteres en X / Twitter (máximo 280 caracteres)**:
   - *Riesgo*: Un copy regenerado que supere 280 caracteres rompería la validación estricta de `frontend/src/api/contentWorkflow.ts`.
   - *Mitigación*: El backend asume la responsabilidad de garantizar `len(contenido) <= 280`; si el modelo de IA excede la longitud, el backend trunca respetando palabras completas antes de responder, garantizando que el frontend siempre reciba un texto válido.
3. **Pérdida o borrado del mensaje original en Discord**:
   - *Riesgo*: Si el autor original eliminó su mensaje en Discord antes de que el operador envíe la respuesta, el intento de *reply* (`reference`) fallará.
   - *Mitigación*: El backend captura `discord.NotFound` y responde HTTP 404 informando explícitamente que el mensaje de origen ya no existe en Discord, sin recurrir a fallbacks silenciosos ni crear publicaciones huérfanas sin referencia.
4. **Respuestas duplicadas por clics concurrentes**:
   - *Riesgo*: Múltiples clics simultáneos en "Enviar respuesta a Discord" podrían disparar peticiones paralelas y publicar mensajes repetidos en el canal.
   - *Mitigación*: Bloqueo inmediato del botón mediante referencia inmutable (`complaintPublishLockedIds`) y deshabilitación visual hasta que concluya la llamada de red.
5. **Indisponibilidad de tokens o API Keys de IA sin sustitución silenciosa**:
   - *Riesgo*: Si el usuario selecciona un proveedor cuyas credenciales no están configuradas en `.env` (o cuya cuota se agotó), una sustitución no anunciada violaría la soberanía del usuario.
   - *Mitigación*: El backend valida las credenciales y el estado del motor elegido; si no está disponible, responde HTTP 502/503 informando qué variable o servicio falló, sin cambiar de modelo en secreto.
6. **Desconexión del bot de Discord o credenciales ausentes**:
   - *Riesgo*: Si el entorno carece de `DISCORD_BOT_TOKEN` / `DISCORD_TOKEN`, `publish-preview` podría fallar con error 500 no controlado.
   - *Mitigación*: `publish-preview` responde HTTP 200 con `ready: false` y detalle explicativo (`"Bot de Discord no configurado en el servidor"`), dejando el botón inactivo e informando con total claridad al usuario.
7. **Persistencia determinista de respuestas publicadas**:
   - *Riesgo*: Si el registro de quejas atendidas se conserva en memoria volátil, un reinicio del servidor volvería a mostrar quejas ya respondidas.
   - *Mitigación*: Registro transaccional en la tabla SQLite `respuestas_quejas_discord`, asegurando que `GET /api/v1/content-workflow/complaints/published-responses` mantenga la consistencia entre reinicios y sesiones concurrentes.

---

## 4. Criterios de Aceptación Globales

1. **Selector de IA en el modal de quejas**:
   - El modal exhibe un selector con Groq Llama 3.3, Google Gemma 4 y Google Gemini Flash Lite.
   - Durante la generación de respuesta, tanto el botón "Generar con IA" como el selector de modelo permanecen deshabilitados.
2. **Generación de respuestas exitosa y transparente**:
   - `POST /api/v1/content-workflow/complaints/generate-response` genera la respuesta con el proveedor seleccionado.
   - Si el proveedor falla o no tiene clave, responde HTTP 502/503 informando el fallo exacto sin sustitución silenciosa.
3. **Verificación de destino funcional y robusta**:
   - Si las credenciales del bot faltan, `GET /api/v1/content-workflow/complaints/{interaccion_id}/publish-preview` responde HTTP 200 con `ready: false` y mensaje claro.
   - Si el mensaje original fue eliminado en Discord, responde HTTP 404 con mensaje explicativo.
   - Si todo es correcto, muestra el panel verde de destino verificado y habilita el botón de publicación.
4. **Publicación real en Discord con el Bot oficial**:
   - La publicación utiliza exclusivamente el bot oficial (`DISCORD_BOT_TOKEN` / `DISCORD_TOKEN`) respondiendo directamente al mensaje original.
   - Se solicita confirmación previa y se bloquea el reenvío concurrente.
5. **Persistencia y desaparición de quejas atendidas**:
   - La respuesta publicada se guarda en `respuestas_quejas_discord` en SQLite.
   - `GET /api/v1/content-workflow/complaints/published-responses` retorna la lista real y la queja desaparece del listado activo sin recargar la página.
6. **Mesa de trabajo desacoplada de mocks y con selector de IA**:
   - Se erradica `mockCommunityData.content_studio[0]`; la mesa de trabajo opera con `selectedWorkflowMessage`.
   - La cabecera de la mesa de trabajo incluye un selector de modelo de IA que gobierna la regeneración de copys.
   - Para el formato X, el backend garantiza estrictamente que el texto no exceda los 280 caracteres.
   - Cada formato (LinkedIn, X, Discord) guarda su borrador de forma independiente en `contenidos_generados` sin expulsar la interacción antes de que el usuario termine los otros formatos.
7. **Inviolabilidad constitucional y cobertura de pruebas**:
   - Los 17 archivos históricos preexistentes de la raíz, `backend/` y `motor-ia/` permanecen inalterados.
   - Toda la adaptación se concentra en `puente_motor_ia.py`, `frontend/src/` y `tests/`.
   - Se mantiene el 100% de la suite de pruebas del proyecto en verde.
