# Spec 013: Análisis Integral, Historias Destacadas del Dashboard y Webhook de Anuncios en Redacción

## 1. Contexto y Propósito (QUÉ y POR QUÉ)

### ¿Qué se solicita?
Consolidar tres módulos clave del sistema para garantizar una experiencia 100% fidedigna, operativa y conectada a datos reales:
1. **Pestaña de Análisis (`frontend/src/pages/Analytics.tsx`)**:
   - Eliminar por completo las secciones obsoletas "Bandeja de mensajes en Análisis" y "Revisión de mensajes y curaduría", dado que el paso intermedio de curaduría/aprobación manual fue suprimido del sistema y los flujos van directo de la Ingesta a la Redacción de Contenidos.
   - Poner en funcionamiento real la sección "Scorecards de Emojis Destacados en la Comunidad", sustituyendo el arreglo vacío provisional por telemetría genuina extraída de los mensajes reales de Discord (conteo de uso, sentimiento asociado, frecuencia relativa y tendencia).
   - Precisar la extracción de emojis tanto Unicode (soportando secuencias Zero Width Joiner - ZWJ y modificadores de tono) como emojis personalizados de Discord (`<:nombre:id>` y `<a:nombre:id>`).
   - Calcular la tendencia (`trend`) comparando la frecuencia relativa con muestras históricas (con valor neutro por defecto `'0%'` en muestras iniciales) y dotar a cada emoji de un catálogo semántico con fallback automático según el sentimiento predominante.
   - Reemplazar el banner informativo final por un texto fidedigno y actualizado que describa con precisión lo que la pantalla de Análisis monitorea en tiempo real, sin aludir a aprobaciones ni etapas inexistentes.
   - Reconciliar todas las métricas globales, incluyendo "Alineación de marca", con blindaje determinista contra división por cero cuando no existan interacciones evaluadas.
2. **Historias Destacadas del Dashboard (`frontend/src/components/FeaturedStories.tsx` / `puente_motor_ia.py`)**:
   - Aclarar técnicamente el origen de los mensajes de `usuario_uno` y `usuario_tres` (residuos sintéticos de pruebas tempranas con IDs 31 y 34 en la tabla `lotes_ia_kpis` de Supabase) y filtrar en `puente_motor_ia.py` cualquier autor sintético o de prueba para que el carrusel exhiba exclusivamente mensajes de miembros humanos genuinos de Discord.
   - Mantener `GET /api/v1/community/live-summary` como ruta canónica existente en FastAPI y habilitar `GET /api/community/summary` como alias idéntico para garantizar interoperabilidad completa con todos los componentes frontend y clientes API.
   - En caso de que el carrusel quede sin historias reales tras aplicar el filtro o la historia activa tenga identificador 0, deshabilitar la acción de redacción mostrando el mensaje explicativo "Sin historias disponibles".
   - Eliminar el botón redundante "Ver mensaje" para evitar derivaciones genéricas sin foco.
   - Dotar al botón "Generar publicación" de navegación contextual que redirija a `/content?interaction={id}` pasando el identificador numérico (`currentStory.id_mensaje || currentStory.id`). En `ContentStudio.tsx`, leer el parámetro, buscar y seleccionar la interacción de inmediato (incluso durante la carga de la bandeja o mediante resolución directa) para enfocar la tarjeta "Mensaje original de Discord".
   - Indicar visualmente si la historia destacada ya fue publicada, detallando las plataformas de destino (Discord, X, LinkedIn) y ofreciendo la opción de volver a publicarla o distribuirla en una plataforma adicional.
3. **Módulo de Anuncios Oficiales de la Comunidad con Webhook de Discord (`frontend/src/pages/ContentStudio.tsx` / `puente_motor_ia.py`)**:
   - Incorporar en `ContentStudio.tsx`, inmediatamente arriba de la "Bandeja de mensajes en Redacción", la sección "Anuncios Oficiales de la Comunidad (Discord Webhook)" integrando el desarrollo de Samuel en `anuncios_discord.py`.
   - Consultar el estado del webhook oficial mediante `GET /api/v1/content-workflow/announcements/status`. Si `configured` es `false`, exhibir un banner preventivo en la UI informando que falta configurar la variable `DISCORD_WEBHOOK_ANUNCIOS` en el servidor y bloquear el despacho.
   - Permitir al usuario redactar un borrador de anuncio directamente en un editor de texto o cargar un archivo fuente en formato `.txt` o `.md`, con validación de tamaño máximo de 10,000 caracteres antes de enviarlo a IA.
   - Ofrecer un botón "Generar anuncio con IA" conectado mediante `puente_motor_ia.py` a la plantilla oficial de voz de marca de CloudEdTech y motor LLM configurado en `anuncios_discord.py`.
   - Disponer de un editor interactivo con contador dinámico de caracteres y semáforo cromático: verde ($\le 1500$ caracteres recomendados), ámbar ($1501 - 2000$ caracteres de longitud extendida permitida) y rojo con bloqueo estricto ($> 2000$ caracteres por limitación de Discord).
   - Habilitar el botón "Publicar anuncio en Discord" que despache el mensaje al canal oficial mediante webhook (`DISCORD_WEBHOOK_ANUNCIOS`), incorporando diálogos de confirmación, validación de estado y notificaciones visuales inmediatas.
   - Tras un despacho exitoso por webhook, persistir el registro del anuncio en la tabla SQLite `contenidos_generados` con formato `'discord'`, tipo de contenido `'anuncio_oficial'` y estado `'publicado'`, garantizando trazabilidad y auditoría institucional.
4. **Inviolabilidad Constitucional**:
   - Garantizar de forma estricta que ninguno de los 17 archivos preexistentes en la raíz (incluyendo `anuncios_discord.py`), ni el contenido de `backend/` o `motor-ia/`, sea modificado. Toda la integración debe residir en `puente_motor_ia.py`, `frontend/src/` y `tests/`.

### ¿Por qué es necesario?
1. **Inconsistencias y componentes muertos en Análisis**: La pestaña de Análisis conserva vestigios del modelo editorial previo en el que un operador debía "aprobar curaduría" antes de permitir la redacción. Al haber adoptado un flujo directo (donde las interacciones con relevancia $\ge 70$ pasan automáticamente a redacción), la bandeja de análisis y el panel de curaduría resultan confusos, innecesarios y bloquean la comprensión del flujo. Asimismo, los scorecards de emojis mapean un arreglo vacío en código duro (`[]`), desaprovechando la rica señal expresiva presente en los mensajes de Discord.
2. **Contaminación sintética y desvinculación en el Dashboard**: El usuario detectó la presencia de autores como `usuario_uno` y `usuario_tres` en las historias destacadas, lo que resta credibilidad a la promesa de datos reales de la comunidad. Además, el botón "Generar publicación" redirigía a `/content` de manera ciega (sin seleccionar la historia en cuestión), obligando al operador a buscar manualmente el mensaje entre la lista, mientras que el botón "Ver mensaje" generaba redundancia operativa. La falta de visibilidad sobre si un contenido ya fue publicado genera riesgo de republicaciones accidentales o desconocimiento del alcance editorial.
3. **Desconexión del flujo de Anuncios Oficiales de Samuel**: Samuel implementó un mecanismo robusto en `anuncios_discord.py` para reescribir borradores con la voz oficial de marca y despacharlos al canal de anuncios mediante webhooks. Sin embargo, esta capacidad no está integrada en la aplicación web (`ContentStudio.tsx`), obligando a ejecutar scripts aislados por consola y privando al equipo de un espacio unificado para redactar, optimizar, publicar y auditar comunicados oficiales.
4. **Respeto a la gobernanza y estabilidad del sistema**: La arquitectura del proyecto exige que el código legado permanezca congelado para evitar regresiones en otras dependencias y scripts de evaluación. La unificación debe realizarse mediante adaptadores limpios y pruebas automatizadas tipo TDD.

---

## 2. Requerimientos Funcionales (Formato EARS)

### RF-01: Limpieza Integral y Supresión de Curaduría Manual en Análisis
- **MIENTRAS** el usuario navegue en la pestaña de Análisis (`/analytics`), **EL SISTEMA DEBERÁ** omitir categóricamente las secciones "Bandeja de mensajes en Análisis" y "Revisión de mensajes y curaduría", erradicando botones, estados y llamadas a endpoints de curaduría manual (`updateMessageCuration`).
- **CUANDO** se monte la vista de Análisis, **EL SISTEMA DEBERÁ** presentar un diseño limpio centrado exclusivamente en telemetría de comunidad: métricas globales, scorecards de emojis reales, ranking de hashtags más populares, temas clave detectados e insights estratégicos.
- **EL SISTEMA DEBERÁ** asegurar que todos los botones y enlaces restantes en la pantalla (como "Ver en Ingesta" en la sección de hashtags) cuenten con navegación funcional activa hacia sus respectivas vistas sin rutas muertas ni errores de ejecución.

### RF-02: Scorecards de Emojis Reales de la Comunidad, Sintaxis ZWJ/Discord y Tendencias
- **CUANDO** el frontend consulte la telemetría de la comunidad (`/api/community/analytics`), **EL SISTEMA DEBERÁ** analizar el corpus de mensajes reales de Discord y retornar una lista estructurada con los emojis más utilizados en la comunidad.
- **MIENTRAS** el backend compute las estadísticas de emojis, **EL SISTEMA DEBERÁ** extraer y reconocer:
  1. Emojis Unicode estándar y secuencias compuestas con Zero Width Joiner (ZWJ, p. ej. 👨‍👩‍👧, 🧑‍💻) y modificadores de tono de piel.
  2. Emojis personalizados de Discord en formato `<:nombre:id>` o animados `<a:nombre:id>`, normalizando su presentación visual.
- **EL SISTEMA DEBERÁ** calcular para cada emoji destacado:
  1. El caracter, glifo o token del emoji (`emoji`).
  2. Su frecuencia absoluta de aparición (`value`).
  3. El sentimiento predominante asociado al contexto en que se utilizó (`sentiment`: `positive`, `neutral` o `negative`).
  4. Una etiqueta semántica descriptiva (`label`), utilizando un catálogo predeterminado para emojis comunes (p. ej. 🚀 $\rightarrow$ "Lanzamiento / Progreso", ✨ $\rightarrow$ "Inspiración / Logro", 🎉 $\rightarrow$ "Celebración", 💡 $\rightarrow$ "Idea / Innovación", 👋 $\rightarrow$ "Bienvenida / Saludo", ❤️/🔥 $\rightarrow$ "Entusiasmo / Pasión", 🐛/⚠️ $\rightarrow$ "Alerta / Reporte") y un fallback automático derivado del sentimiento predominante del contexto (positivo $\rightarrow$ "Optimismo / Aprobación", neutral $\rightarrow$ "Informativo / Participación", negativo $\rightarrow$ "Inquietud / Reporte").
  5. Una breve explicación del comportamiento contextual detectado (`description`).
  6. La tendencia o variación porcentual relativa (`trend`) respecto a muestras históricas previas; en caso de tratarse del primer lote o carecer de histórico comparativo, **EL SISTEMA DEBERÁ** asignar deterministamente el valor neutro `"0%"`.
- **SI** la comunidad no contiene mensajes con emojis o el volumen es insuficiente, **EL SISTEMA DEBERÁ** presentar un estado vacío elegante indicando que aún no se detectan patrones de emojis en las conversaciones recientes, en lugar de romper el renderizado o mostrar datos artificiales.
- **CUANDO** el componente reciba los datos de emojis, **EL SISTEMA DEBERÁ** renderizar los scorecards dinámicamente con sus colores e indicadores de sentimiento respectivos (esmeralda para sentimiento positivo, azul para neutral y rosa/rojo para negativo).

### RF-03: Actualización Informativa, Métricas Fidedignas y Blindaje contra División por Cero
- **CUANDO** el usuario visualice el pie informativo de la pestaña de Análisis, **EL SISTEMA DEBERÁ** presentar un texto fidedigno y representativo que describa con exactitud el comportamiento actual del sistema:
  > *"CloudEdTech analiza continuamente el pulso de la comunidad de Discord mediante IA: distribución de sentimiento, detección de temas clave, tendencias de hashtags y telemetría de interacción. Las interacciones con alta relevancia ($\ge 70\%$) se canalizan directamente a la mesa de Redacción de Contenidos para su adaptación y distribución multicanal."*
- **EL SISTEMA DEBERÁ** erradicar el texto obsoleto que aludía a curadurías intermedias, pasos de aprobación suprimidos o métricas pendientes de integración.
- **MIENTRAS** se calculen las métricas globales superiores en el backend, **EL SISTEMA DEBERÁ** computar el porcentaje de "Alineación de marca" (`brand_alignment_percentage`) evaluando la proporción de mensajes con sentimiento positivo o neutral dentro de los temas clave de CloudEdTech.
- **SI** no existen interacciones analizadas en el corpus (total = 0), **EL SISTEMA DEBERÁ** blindar el cálculo contra excepciones de división por cero (`ZeroDivisionError`) retornando deterministamente `100.0%` (o `0.0%` acompañado de `analizados: 0`) para garantizar que la interfaz de usuario nunca reciba `NaN`, `null` ni genere fallos de renderizado.

### RF-04: Rutas Canónicas/Alias y Depuración de Historias Destacadas del Dashboard (Carrusel Vacío Resiliente)
- **EL SISTEMA DEBERÁ** mantener `GET /api/v1/community/live-summary` como ruta canónica activa del dashboard en FastAPI y registrar `GET /api/community/summary` como ruta alias idéntica para asegurar total compatibilidad entre versiones del frontend y clientes HTTP.
- **CUANDO** el servicio del Dashboard recopile las interacciones candidatas para "Historias destacadas" (`highlights`), **EL SISTEMA DEBERÁ** filtrar y descartar rigurosamente cualquier registro cuyo autor o identificador corresponda a usuarios sintéticos de pruebas tempranas (específicamente autores que contengan o coincidan con `usuario_uno`, `usuario_tres`, nombres que inicien con prefijos `usuario_` o `test_`, o identificadores residuales 31 y 34).
- **EL SISTEMA DEBERÁ** garantizar que el 100% de las historias destacadas mostradas en el carrusel provengan exclusivamente de miembros humanos reales de Discord (como `danitower`, `carlos_g`, `mariana_dev`, entre otros).
- **SI** tras aplicar el filtro de autores sintéticos la cantidad de historias destacadas es mayor a cero, **EL SISTEMA DEBERÁ** ordenar las historias priorizando mayor relevancia y frescura temporal.
- **SI** tras filtrar los autores sintéticos el carrusel queda sin historias reales (lista vacía o historia activa con `id: 0`), **EL SISTEMA DEBERÁ** deshabilitar el botón de acción "Generar publicación" y exhibir de forma destacada el mensaje "Sin historias disponibles", evitando la navegación con identificadores inválidos.

### RF-05: Navegación Contextual Robusta a Redacción y Trazabilidad de Publicaciones en Historias Destacadas
- **CUANDO** el usuario visualice una tarjeta de Historia Destacada en `FeaturedStories.tsx`, **EL SISTEMA DEBERÁ** omitir el botón "Ver mensaje", concentrando la acción editorial exclusivamente en "Generar publicación".
- **CUANDO** el usuario pulse el botón "Generar publicación" sobre una historia válida, **EL SISTEMA DEBERÁ** redirigir a `/content?interaction={id}` pasando el identificador numérico de la interacción (evaluando `currentStory.id_mensaje || currentStory.id`) tanto por query param como por estado de navegación (`location.state: { interactionId: number }`).
- **CUANDO** `ContentStudio.tsx` se cargue con el parámetro `interaction` en la URL o en `location.state`, **EL SISTEMA DEBERÁ**:
  1. Extraer el identificador numérico de la interacción solicitada.
  2. Buscar inmediatamente la interacción en la lista de mensajes de la bandeja de redacción y seleccionarla.
  3. Si la lista de mensajes aún está cargando o el mensaje requiere resolución individual, resolverlo de inmediato para enfocar y desplegar la tarjeta "Mensaje original de Discord" sin requerir intervención manual del operador.
- **MIENTRAS** una historia destacada sea visualizada en el carrusel del Dashboard, **EL SISTEMA DEBERÁ** verificar si el mensaje asociado ya ha sido publicado en una o más plataformas (Discord, X, LinkedIn) consultando la persistencia de publicaciones (`contenidos_generados` y `respuestas_quejas_discord`).
- **SI** el mensaje ya fue publicado, **EL SISTEMA DEBERÁ** exhibir una insignia visible de estado (ej. `"✓ Publicado en Discord"` o `"✓ Publicado en X, LinkedIn"`), cambiar la etiqueta del botón de acción a `"Volver a publicar"` (o `"Publicar en otra plataforma"`) y mantener la navegación hacia `/content` permitiendo al redactor generar una nueva variante o despacharla a otro canal.

### RF-06: Módulo de Anuncios Oficiales de la Comunidad con Discord Webhook y Trazabilidad en SQLite
- **CUANDO** el usuario acceda a la pestaña de Redacción de Contenidos (`/content`), **EL SISTEMA DEBERÁ** desplegar, inmediatamente arriba de la "Bandeja de mensajes en Redacción", la sección "Anuncios Oficiales de la Comunidad (Discord Webhook)".
- **CUANDO** se monte la sección de anuncios, **EL SISTEMA DEBERÁ** consultar el estado del webhook oficial mediante `GET /api/v1/content-workflow/announcements/status`.
- **SI** la propiedad `configured` retornada es `false`, **EL SISTEMA DEBERÁ** mostrar un banner preventivo destacado en la interfaz advirtiendo que falta configurar la variable `DISCORD_WEBHOOK_ANUNCIOS` en el servidor y deshabilitar preventivamente el botón de publicación en Discord.
- **EL SISTEMA DEBERÁ** ofrecer en dicha sección dos modalidades de ingreso del borrador de anuncio:
  1. Redacción directa en un área de texto de entrada ("Borrador del anuncio").
  2. Carga de un archivo local en formato `.txt` o `.md` mediante selector de archivos ("Subir archivo .txt / .md"), leyendo su contenido de forma inmediata y poblando el borrador.
- **SI** el usuario intenta subir un archivo con extensión distinta de `.txt` o `.md`, **EL SISTEMA DEBERÁ** rechazar la carga y advertir amigablemente sobre el formato permitido.
- **MIENTRAS** el borrador esté vacío o contenga únicamente espacios en blanco, **EL SISTEMA DEBERÁ** mantener deshabilitado el botón "Generar anuncio con IA".
- **CUANDO** un anuncio sea publicado exitosamente vía webhook en Discord a través de `POST /api/v1/content-workflow/announcements/publish`, **EL SISTEMA DEBERÁ** registrar inmediatamente el evento en la base de datos SQLite local dentro de la tabla `contenidos_generados` con:
  - `formato: 'discord'`
  - `tipo_contenido: 'anuncio_oficial'`
  - `estado: 'publicado'`
  - `estado_publicacion: 'publicado'`
  - `publicado_en: datetime` (marca temporal ISO)
  - `contenido: string` (texto final despachado)

### RF-07: Generación de Anuncios con IA Basada en el Manual de Marca CloudEdTech y Límites de Entrada
- **EL SISTEMA DEBERÁ** limitar el texto del borrador de entrada a un máximo estricto de 10,000 caracteres antes de enviarlo al modelo de IA, rechazando con código **HTTP 400 Bad Request** cualquier solicitud que sobrepase este umbral para prevenir desbordamientos de ventana de contexto o latencias extremas.
- **CUANDO** el usuario pulse "Generar anuncio con IA" con un borrador válido ($\le 10,000$ caracteres), **EL SISTEMA DEBERÁ** mostrar un indicador visual de procesamiento en curso ("Generando anuncio con voz de marca...") e invocar el endpoint `POST /api/v1/content-workflow/announcements/generate`.
- **MIENTRAS** el backend procese la solicitud de generación, **EL SISTEMA DEBERÁ** invocar la función `anuncios_discord.generar_anuncio` sin alterar el archivo original, aplicando las directrices institucionales del Manual de Marca de CloudEdTech (voz cercana, clara, motivadora y responsable; tuteo obligatorio; prohibición de clichés vacíos; y máximo 2 emojis pertinentes).
- **SI** la clave de API requerida (`GOOGLE_API_KEY`) no está configurada o el servicio del LLM no está disponible, **EL SISTEMA DEBERÁ** retornar código **HTTP 502 Bad Gateway** o **HTTP 503 Service Unavailable** con un mensaje explicativo, notificando al usuario en la interfaz sin bloqueos silenciosos.
- **CUANDO** la generación concluya exitosamente, **EL SISTEMA DEBERÁ** cargar el texto generado en el "Editor del Anuncio Final", permitiendo al usuario realizar ajustes manuales antes de proceder a la publicación.

### RF-08: Editor con Validación de Caracteres, Alertas Cromáticas y Publicación Segura Vía Webhook
- **MIENTRAS** el usuario edite el anuncio final en la sección de anuncios, **EL SISTEMA DEBERÁ** mostrar un contador dinámico de caracteres con alertas cromáticas diferenciadas:
  1. **Color verde o neutro** ($\le 1500$ caracteres): longitud óptima recomendada por el Manual de Marca.
  2. **Color ámbar** ($1501$ a $2000$ caracteres): advertencia visual preventiva indicando longitud extensa pero técnicamente permitida por Discord.
  3. **Color rojo** ($> 2000$ caracteres): alerta crítica por exceder el límite absoluto de la API de Discord.
- **MIENTRAS** el texto del anuncio final esté vacío o supere los 2000 caracteres, **EL SISTEMA DEBERÁ** mantener estrictamente deshabilitado el botón "Publicar anuncio en Discord".
- **CUANDO** el usuario pulse "Publicar anuncio en Discord" con un texto válido ($\le 2000$ caracteres) y el webhook esté configurado, **EL SISTEMA DEBERÁ** solicitar una confirmación modal preventiva mostrando una vista previa del mensaje y advirtiendo que será publicado en el canal oficial de anuncios.
- **SI** el usuario confirma la publicación, **EL SISTEMA DEBERÁ** invocar `POST /api/v1/content-workflow/announcements/publish` enviando el texto final y la confirmación explícita.
- **MIENTRAS** el backend despache el anuncio, **EL SISTEMA DEBERÁ** utilizar `anuncios_discord.publicar_en_discord` ejecutando la llamada HTTP POST al webhook configurado en `DISCORD_WEBHOOK_ANUNCIOS` con `allowed_mentions={"parse": []}` para evitar menciones masivas no autorizadas.
- **SI** la variable `DISCORD_WEBHOOK_ANUNCIOS` no está configurada en el servidor, **EL SISTEMA DEBERÁ** responder con código **HTTP 503 Service Unavailable** y el mensaje *"Webhook de anuncios no configurado en el servidor"*.
- **SI** la API de Discord rechaza la petición o responde con un error HTTP, **EL SISTEMA DEBERÁ** capturar la excepción y responder con código **HTTP 502 Bad Gateway** detallando la respuesta de Discord.
- **CUANDO** la publicación resulte exitosa (Discord responde HTTP 204), **EL SISTEMA DEBERÁ** registrar el anuncio en la base SQLite `contenidos_generados`, notificar visualmente al usuario con una confirmación en verde ("¡Anuncio publicado exitosamente en Discord!") y ofrecer la opción de limpiar el formulario o iniciar un nuevo comunicado.

### RF-09: Inviolabilidad Constitucional, Aislamiento de Código y Calidad TDD
- **MIENTRAS** se implementen las soluciones de backend y frontend para Análisis, Historias Destacadas y Anuncios por Webhook, **EL SISTEMA DEBERÁ** mantener rigurosamente intactos e inalterados los 17 archivos preexistentes en la raíz del proyecto (`anuncios_discord.py`, `base_datos.py`, `modelos.py`, `api.py`, etc.), así como las carpetas `backend/` y `motor-ia/`.
- **EL SISTEMA DEBERÁ** articular toda la orquestación, nuevos endpoints y adaptaciones de datos exclusivamente en `puente_motor_ia.py`, los componentes de `frontend/src/` y las suites de prueba automatizadas en `tests/`.
- **EL SISTEMA DEBERÁ** validar cada funcionalidad implementada mediante pruebas unitarias y de integración que garanticen el mantenimiento del 100% de la suite de pruebas del proyecto en estado verde.

---

## 3. Contratos de API y Modelos de Datos

### 3.1 Contratos de API

#### 1. `GET /api/community/analytics` (Enriquecido en `puente_motor_ia.py`)
- **Descripción**: Provee las analíticas globales de la comunidad, incorporando la distribución real de emojis detectados en los mensajes de Discord (Unicode, ZWJ y sintaxis Discord) y el blindaje de la alineación de marca ante corpus vacíos.
- **Parámetros**: Ninguno.
- **Campos de Salida Exitosa (HTTP 200 OK)**:
  ```json
  {
    "sentiment": {
      "distribution": [
        { "name": "Positivo", "value": 45 },
        { "name": "Neutral", "value": 35 },
        { "name": "Negativo", "value": 20 }
      ]
    },
    "topics": [
      { "topic": "IA", "percentage": 38.5 },
      { "topic": "DESARROLLO", "percentage": 25.0 }
    ],
    "hashtags": [
      { "id": 1, "name": "#python", "mentions": 12, "growth": 15 }
    ],
    "emojis": [
      {
        "emoji": "✨",
        "value": 6,
        "sentiment": "positive",
        "label": "Inspiración / Logro",
        "description": "Utilizado en logros y nuevos aprendizajes",
        "trend": "+25%"
      },
      {
        "emoji": "🚀",
        "value": 4,
        "sentiment": "positive",
        "label": "Lanzamiento / Progreso",
        "description": "Proyectos y metas completadas",
        "trend": "+12%"
      },
      {
        "emoji": "👋",
        "value": 3,
        "sentiment": "neutral",
        "label": "Bienvenida / Saludo",
        "description": "Presentaciones y saludos comunitarios",
        "trend": "0%"
      }
    ],
    "brand_alignment_percentage": 88.5,
    "analizados": 42
  }
  ```
- **Caso Límite (0 interacciones analizadas)**:
  ```json
  {
    "sentiment": { "distribution": [] },
    "topics": [],
    "hashtags": [],
    "emojis": [],
    "brand_alignment_percentage": 100.0,
    "analizados": 0
  }
  ```

#### 2. `GET /api/v1/community/live-summary` y Alias `GET /api/community/summary`
- **Descripción**: Retorna el resumen del dashboard en tiempo real. `GET /api/v1/community/live-summary` es la ruta canónica y `GET /api/community/summary` es el alias unificado. Garantiza la exclusión de autores sintéticos (`usuario_uno`, `usuario_tres`, etc.) en `highlights` e informa el estado de publicación de cada historia destacada.
- **Campos de Salida Exitosa (HTTP 200 OK)**:
  ```json
  {
    "highlights": [
      {
        "id": 15,
        "id_mensaje": 15,
        "author": "danitower",
        "autor": "danitower",
        "channel": "general",
        "canal": "general",
        "content": "Acabo de terminar mi primera red neuronal y el modelo convergió perfectamente.",
        "message": "Acabo de terminar mi primera red neuronal y el modelo convergió perfectamente.",
        "sentiment": "Positivo",
        "sentiment_score": 0.85,
        "relevance": 92,
        "relevancia": 92,
        "topic": "IA",
        "tema": "IA",
        "title": "Destacado: Ia (general)",
        "titulo": "Destacado: Ia (general)",
        "estado_revision": "aprobado",
        "is_published": true,
        "published_platforms": ["discord", "linkedin"]
      }
    ],
    "highlights_summary": {
      "detected": 10,
      "high_relevance": 6,
      "ready_for_content": 4
    },
    "audience": {
      "total_audience": 10,
      "active_members": 8
    },
    "calendar": [],
    "reports": []
  }
  ```
- **Caso Límite (Sin historias reales disponibles tras filtrado)**:
  ```json
  {
    "highlights": [],
    "highlights_summary": {
      "detected": 0,
      "high_relevance": 0,
      "ready_for_content": 0
    }
  }
  ```

#### 3. `GET /api/v1/content-workflow/announcements/status`
- **Descripción**: Inspecciona el estado de configuración del webhook oficial de anuncios de Discord y proporciona los límites operativos.
- **Campos de Salida Exitosa (HTTP 200 OK)**:
  ```json
  {
    "configured": true,
    "channel_hint": "anuncios",
    "max_characters_recommended": 1500,
    "max_characters_limit": 2000
  }
  ```
- **Caso Webhook no configurado (HTTP 200 OK)**:
  ```json
  {
    "configured": false,
    "channel_hint": null,
    "max_characters_recommended": 1500,
    "max_characters_limit": 2000,
    "warning": "Variable de entorno DISCORD_WEBHOOK_ANUNCIOS no configurada"
  }
  ```

#### 4. `POST /api/v1/content-workflow/announcements/generate`
- **Descripción**: Genera una propuesta de anuncio oficial aplicando la voz de marca CloudEdTech mediante `anuncios_discord.generar_anuncio`.
- **Campos de Entrada (JSON)**:
  ```json
  {
    "borrador": "Mañana a las 6pm tendremos workshop de LangChain y agentes con Enoc por Discord."
  }
  ```
- **Campos de Salida Exitosa (HTTP 200 OK)**:
  ```json
  {
    "borrador_original": "Mañana a las 6pm tendremos workshop de LangChain y agentes con Enoc por Discord.",
    "anuncio_generado": "**¡Construye tus propios agentes inteligentes con LangChain!** 🚀\n\n¿Quieres llevar tus proyectos al siguiente nivel? Conéctate mañana a las 6:00 PM y aprende en vivo con Enoc cómo implementar flujos de agentes y memoria contextual aplicable a escenarios reales de la industria.\n\nElige tu ruta de aprendizaje y participa en el canal de voz de la comunidad.\n\n#CloudEdTech #LangChain #InteligenciaArtificial",
    "caracteres": 435,
    "modelo_usado": "gemma-4-31b-it"
  }
  ```
- **Errores Posibles**:
  - `400 Bad Request`: Si el borrador está vacío, contiene solo espacios o supera los 10,000 caracteres.
  - `502 Bad Gateway`: Si el modelo LLM falla o las credenciales no son válidas.

#### 5. `POST /api/v1/content-workflow/announcements/publish`
- **Descripción**: Despacha el anuncio al canal oficial de Discord mediante webhook (`DISCORD_WEBHOOK_ANUNCIOS`) y registra inmediatamente la publicación en la tabla SQLite `contenidos_generados` para trazabilidad institucional.
- **Campos de Entrada (JSON)**:
  ```json
  {
    "contenido": "**¡Construye tus propios agentes inteligentes con LangChain!** 🚀...",
    "confirmado": true
  }
  ```
- **Campos de Salida Exitosa (HTTP 200 OK)**:
  ```json
  {
    "estado": "publicado",
    "id_contenido": 12,
    "caracteres": 435,
    "fecha_publicacion": "2026-10-19T01:45:00Z",
    "formato": "discord",
    "tipo_contenido": "anuncio_oficial",
    "mensaje": "Anuncio publicado exitosamente en el canal de anuncios de Discord"
  }
  ```
- **Errores Posibles**:
  - `400 Bad Request`: Si `confirmado` es falso, el contenido está vacío o supera 2000 caracteres.
  - `502 Bad Gateway`: Si la llamada HTTP a Discord rechaza el webhook o responde error.
  - `503 Service Unavailable`: Si `DISCORD_WEBHOOK_ANUNCIOS` no está definido en el servidor.

---

### 3.2 Modelos de Datos y Esquemas de Persistencia

#### 1. Estructura de Telemetría de Emojis (`EmojiScorecard`)
```typescript
interface EmojiScorecard {
  emoji: string;         // Caracter Unicode (con ZWJ soportado) o token de Discord <:nombre:id>
  value: number;         // Conteo de apariciones en el período analizado
  sentiment: 'positive' | 'neutral' | 'negative';
  label: string;         // Etiqueta semántica descriptiva (catálogo o fallback contextual)
  description: string;   // Explicación breve de uso contextual
  trend: string;         // "+15%", "-5%", o "0%" (neutro por defecto si no hay histórico)
}
```

#### 2. Registro de Auditoría en SQLite (`contenidos_generados`)
Al despachar con éxito un anuncio vía `POST /api/v1/content-workflow/announcements/publish`, `puente_motor_ia.py` inserta un registro en la tabla `contenidos_generados` existente con los siguientes campos:
- `id_mensaje`: `0` o `NULL` (anuncio autónomo institucional).
- `formato`: `'discord'`
- `tipo_contenido`: `'anuncio_oficial'`
- `contenido`: texto exacto despachado al canal de Discord.
- `estado`: `'publicado'`
- `estado_publicacion`: `'publicado'`
- `canal_publicacion`: `'discord'`
- `creado_en`: fecha y hora ISO actual.
- `publicado_en`: fecha y hora ISO actual.

---

## 4. Casos Límite (Edge Cases) y Mitigaciones

1. **Mensajes con autores sintéticos o duplicados de seed (`usuario_uno`, `usuario_tres`, IDs 31 y 34)**:
   - *Riesgo*: Registros residuales con `usuario_uno` o IDs 31 y 34 continúan apareciendo en el carrusel afectando la credibilidad ante el usuario final.
   - *Mitigación*: Filtro determinista en `puente_motor_ia.py` sobre `highlights` que descarta autores que contengan o coincidan con `usuario_uno`, `usuario_tres`, prefijo `usuario_`, `test_` o IDs de seed 31 y 34, asegurando que solo se presenten interacciones de miembros legítimos de Discord.
2. **Carrusel sin historias reales disponibles (Carrusel Vacío)**:
   - *Riesgo*: Si tras filtrar autores sintéticos no existen historias reales con relevancia $\ge 70$, o la historia activa posee `id: 0`, la UI intentaría navegar con un ID inexistente.
   - *Mitigación*: `FeaturedStories.tsx` evalúa `stories.length === 0` o `currentStory.id === 0`; en tal caso, deshabilita el botón de acción mostrando `"Sin historias disponibles"`, protegiendo la navegación contra estados indefinidos.
3. **División por cero en "Alineación de marca" (`brand_alignment_percentage`)**:
   - *Riesgo*: Si el corpus de mensajes analizados está vacío (0 mensajes), la división matemática produce `ZeroDivisionError` en Python o `NaN` en el cliente web.
   - *Mitigación*: Blindaje matemático en backend: si el divisor de interacciones es 0, retornar deterministamente `100.0%` (o `0.0%` con flag `analizados: 0`), entregando un número flotante válido y evitando rupturas en el frontend.
4. **Discord Webhook ausente o no configurado en el servidor**:
   - *Riesgo*: El operador intenta publicar un anuncio cuando la variable `DISCORD_WEBHOOK_ANUNCIOS` no existe en el entorno, provocando fallos HTTP 500 no controlados.
   - *Mitigación*: `GET /api/v1/content-workflow/announcements/status` expone `configured: false`. La UI despliega un banner preventivo claro indicando la ausencia de configuración y deshabilita el botón de publicación. Si se invoca el endpoint directo, este responde ordenadamente con `HTTP 503 Service Unavailable`.
5. **Borrador de anuncio excesivamente extenso ($\ge 10,000$ caracteres)**:
   - *Riesgo*: Un borrador gigantesco satura los tokens del LLM, generando tiempos de espera inaceptables o errores de cuota.
   - *Mitigación*: Validación estricta en `POST /api/v1/content-workflow/announcements/generate` limitando la entrada a un máximo de 10,000 caracteres con respuesta `HTTP 400 Bad Request` si se excede.
6. **Límites de caracteres de Discord en el Editor de Anuncios**:
   - *Riesgo*: Discord rechaza tajantemente con HTTP 400 cualquier mensaje que exceda 2000 caracteres.
   - *Mitigación*: Editor en `ContentStudio.tsx` con semáforo de longitud: verde ($\le 1500$), ámbar ($1501 - 2000$) y rojo ($> 2000$). El botón de publicación permanece deshabilitado si el texto supera 2000 caracteres, y el backend valida nuevamente rechazando con `HTTP 400 Bad Request` antes de contactar a Discord.
7. **Emojis complejos (Secuencias ZWJ y emojis de Discord `<:nombre:id>`)**:
   - *Riesgo*: Expresiones regulares simples de emojis pueden fragmentar secuencias Zero Width Joiner o ignorar emojis de Discord, distorsionando las métricas de sentimiento y uso.
   - *Mitigación*: Extractor con soporte de secuencias ZWJ Unicode y patrón regex para tokens `<:nombre:id>` y `<a:nombre:id>`, asignando tendencias neutras (`"0%"`) cuando no se dispone de histórico comparativo y etiquetas semánticas con fallback automático.
8. **Navegación contextual a Redacción desde Dashboard**:
   - *Riesgo*: Si el usuario llega a `/content?interaction={id}` y la bandeja aún no termina de cargar o el mensaje requiere búsqueda individual, la tarjeta de "Mensaje original" podría quedar desincronizada.
   - *Mitigación*: `ContentStudio.tsx` lee el parámetro de consulta o estado, espera la carga o resuelve el mensaje solicitado directamente, selecciona la interacción de forma atómica y hace scroll/foco en la tarjeta de "Mensaje original de Discord".

---

## 5. Criterios de Aceptación Globales

1. **Pestaña de Análisis depurada, fidedigna y blindada**:
   - Las secciones "Bandeja de mensajes en Análisis" y "Revisión de mensajes y curaduría" han sido removidas por completo de `Analytics.tsx`.
   - La sección "Scorecards de Emojis Destacados en la Comunidad" muestra datos reales calculados de las conversaciones de Discord (frecuencia, sentimiento asociado, etiqueta semántica y tendencia), soportando secuencias ZWJ y emojis de Discord.
   - Si no existen mensajes analizados, `brand_alignment_percentage` retorna deterministamente un valor numérico seguro (`100.0%` o `0.0%`), sin `NaN` ni errores de división por cero.
   - El texto informativo del pie describe con precisión el flujo analítico real de CloudEdTech y todos los botones restantes de la vista cuentan con navegación funcional.
2. **Historias Destacadas del Dashboard limpias, trazables y con rutas compatibles**:
   - `GET /api/v1/community/live-summary` funciona como ruta canónica y `GET /api/community/summary` como alias idéntico.
   - En el carrusel de historias destacadas no aparece ningún registro de `usuario_uno`, `usuario_tres` ni usuarios sintéticos.
   - Si no hay historias disponibles o la historia activa tiene `id: 0`, el botón "Generar publicación" queda deshabilitado mostrando "Sin historias disponibles".
   - El botón redundante "Ver mensaje" ha sido retirado.
   - El botón "Generar publicación" redirige a `/content?interaction={id}` con el ID numérico (`currentStory.id_mensaje || currentStory.id`).
   - Al cargar `/content?interaction={id}`, `ContentStudio.tsx` selecciona de inmediato la interacción indicada y despliega la tarjeta de "Mensaje original de Discord".
   - Si la historia ya fue publicada en Discord, X o LinkedIn, la tarjeta exhibe el indicador de publicación correspondiente y ofrece la acción de republicación o publicación multicanal.
3. **Módulo de Anuncios Oficiales integrado con Webhook y Auditoría**:
   - `ContentStudio.tsx` exhibe la sección de anuncios oficiales arriba de la bandeja de redacción.
   - `GET /api/v1/content-workflow/announcements/status` reporta si el webhook está configurado; si `configured: false`, la UI muestra un banner preventivo y desactiva el botón de publicación.
   - Permite ingresar borradores manualmente o subir archivos `.txt` / `.md`, con límite máximo de 10,000 caracteres antes de enviar al LLM.
   - El botón "Generar anuncio con IA" produce el copy con voz de marca mediante la integración con `anuncios_discord.py`.
   - El editor muestra contador dinámico de caracteres: verde ($\le 1500$), ámbar ($1501-2000$) y rojo con bloqueo estricto ($> 2000$).
   - El botón "Publicar anuncio en Discord" despacha el contenido vía webhook con confirmación modal previa, confirmación visual de éxito y persistencia inmediata en SQLite (`contenidos_generados` con formato `'discord'`, tipo `'anuncio_oficial'`, estado `'publicado'`).
4. **Inviolabilidad Constitucional y Calidad**:
   - Los 17 archivos preexistentes en la raíz, `backend/` y `motor-ia/` permanecen rigurosamente intactos.
   - El 100% de la suite de pruebas automatizadas se mantiene en verde.
