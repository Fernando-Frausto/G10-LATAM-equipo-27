# Spec 014: Optimización de Filtros, Redirección a Publicación y Participación por Canal en Dashboard

## 1. Contexto y Propósito (QUÉ y POR QUÉ)

### ¿Qué se solicita?
Consolidar tres optimizaciones críticas en la experiencia de usuario y en la telemetría operativa de la plataforma CloudEdTech:

1. **Pestaña de Ingesta de Mensajes (`frontend/src/pages/Messages.tsx`) - Redirección a Redacción**:
   - En cada tarjeta de mensaje individual (sección de cola *"Mostrando N mensajes..."*):
     - Eliminar definitivamente el botón *"Analytics"* que derivaba de forma genérica a la vista de analíticas.
     - Mostrar un botón *"Generar publicación"* cuando el mensaje ya fue analizado (`isAnalyzed === true`).
     - **Estado habilitado / deshabilitado con title preventivo**: Si el mensaje se encuentra en estado descartado (`curation_status === "discarded"`), el botón *"Generar publicación"* debe estar deshabilitado (`disabled`) exhibiendo el atributo informativo `title="Restaura el mensaje para generar publicación"`.
     - **Soberanía editorial ante baja relevancia**: Si un mensaje evaluado posee relevancia $< 70\%$ pero no ha sido descartado (o fue restaurado por el operador humano a estado `'pending'`), se permite la navegación activa con *"Generar publicación"*, posibilitando que Enoc fuerce la redacción de un copy editorial si lo considera pertinente, aprovechando la capacidad nativa de `ContentStudio.tsx` para inyectar y seleccionar cualquier interacción referenciada por URL.
     - Al pulsar *"Generar publicación"*, redirigir directamente a la pestaña de Redacción de Contenidos (`/content?interaction=${message.interactionId}` con estado de navegación `{ state: { interactionId: message.interactionId } }`), posicionando y enfocando automáticamente dicho mensaje en la tarjeta de *"Mensaje original de Discord"* con desplazamiento suave (*smooth scroll*).
     - Para mensajes aún no analizados (`isAnalyzed === false`), mantener disponible exclusivamente el botón *"Evaluar IA"* sin mostrar el botón de publicación hasta completar la inferencia.

2. **Pestaña de Ingesta de Mensajes (`frontend/src/pages/Messages.tsx`) - Depuración y Reorganización de Filtros con Precedencia Humana**:
   - En la sección *"Panel de filtrado de mensajes"*:
     - Eliminar el filtro redundante (`stageFilter`) ubicado al lado del selector *"Todos los sentimientos"*.
     - Conservar el filtro situado debajo de la etiqueta *"Estado del mensaje"* (`curationFilter`) y reestructurar sus opciones con las siguientes 5 opciones exactas en este estricto orden de arriba a abajo:
       1. **Todos los estados** (todos los mensajes registrados: pendientes, analizados, completos y descartados)
       2. **Pendientes de evaluar** (mensajes sin evaluar por IA y no descartados)
       3. **Pendientes de copy** (mensajes analizados pendientes de redacción editorial y no descartados)
       4. **Proceso completo** (mensajes con redacción finalizada, listos, aprobados o publicados y no descartados)
       5. **Descartado** (mensajes descartados por IA o manualmente por el operador)
     - **Precedencia Humana (HITL)**: La decisión manual del operador (`curation_status` / `curationStatus[message.id]`) tiene máxima precedencia sobre la inferencia algorítmica:
       * Un mensaje pertenece a *"Descartado"* si `curation_status === "discarded"` O si fue analizado con relevancia $< 70\%$ y el operador no ha emitido una decisión expresa distinta (`curation_status !== "curated"` y `curation_status !== "pending"`).
       * Si un mensaje con baja relevancia es restaurado por el operador (pasando `curation_status` a `'pending'`), deja de catalogarse como *"Descartado"* e ingresa inmediatamente a *"Pendientes de copy"*.
     - **Rótulos contextuales en la cabecera de la cola**: Presentar rótulos descriptivos específicos y exactos según la opción seleccionada:
       * `'all'`: *"mensajes en total (Todos los mensajes)"*
       * `'pending_eval'`: *"mensajes pendientes de evaluar"*
       * `'pending_copy'`: *"mensajes en la cola de copy"*
       * `'completos'`: *"mensajes con proceso completo"*
       * `'descartados'`: *"mensajes descartados"*
       manteniendo el sufijo complementario de fechas `(en rango: X a Y)` cuando existan filtros temporales activos.

3. **Pestaña de Dashboard (`frontend/src/pages/Dashboard.tsx`) - Sección Participación por Canal Modular y Reactiva**:
   - Incorporar en el Dashboard un componente modular dedicado (`frontend/src/components/ChannelParticipation.tsx`) montado con clave reactiva `<ChannelParticipation key={`channels-${analyticsVersion}`} />` para refrescarse automáticamente al presionar *"Actualizar datos"*.
   - Encabezado con glifo `#` destacado en acento naranja (`text-orange-500 font-bold`) y título *"Participación por canal"* con subtítulo *"Distribución de mensajes registrados en los seis canales de Discord"*.
   - Desglose ordenado para los seis (6) canales oficiales de Discord en su orden estricto:
     1. `#general`
     2. `#faq`
     3. `#pqrs`
     4. `#notificaciones`
     5. `#chat-egresados`
     6. `#oportunidades-laborales`
   - Cada fila de canal exhibe:
     - Nombre del canal alineado a la izquierda (con prefijo `#`).
     - Porcentaje relativo con un decimal y conteo numérico a la derecha (ej. `"43.3% · 42"` o `"0.0% · 0"`).
     - Barra de progreso horizontal con contenedor `bg-slate-100 rounded-full h-2` y relleno naranja `bg-orange-500 rounded-full`, garantizando que si un canal posee 0 mensajes (0.0%), la barra tenga un ancho estricto de `0%` (`width: 0%`) sin bordes ni rellenos residuales.
   - **Denominador oficial canónico**: El total (`total_messages`) y los porcentajes se calculan estrictamente sobre la sumatoria de mensajes de los 6 canales canónicos oficiales, garantizando que la suma de porcentajes sea exactamente 100.0% (o 0.0% si el total es 0).
   - **Resiliencia ante fallos**: En caso de error o latencia de red, aplicar un estado de reserva degradado (*graceful fallback*) con los 6 canales en 0.0% sin romper el resto de gráficas del Dashboard.

4. **Inviolabilidad Constitucional y Calidad**:
   - Mantener inmutables los 17 archivos preexistentes en la raíz, `backend/` y `motor-ia/`.
   - Desarrollar las soluciones exclusivamente en `puente_motor_ia.py`, `frontend/src/` y `tests/`.

### ¿Por qué es necesario?
1. **Flujo de Trabajo Fluido y Sin Rupturas (Ingesta $\rightarrow$ Redacción)**:
   El botón anterior *"Analytics"* desviaba al operador hacia gráficos globales que no guardaban relación con la tarea concreta de actuar sobre un mensaje específico analizado. El objetivo operativo de Enoc al revisar un mensaje en la Ingesta es convertirlo de inmediato en un post de LinkedIn, hilo de X o anuncio de Discord. Ofrecer el botón directo *"Generar publicación"* reduce la fricción operativa a un solo clic y preselecciona de forma transparente la tarjeta del mensaje original en la mesa de redacción, respetando además la soberanía de Enoc para redactar sobre cualquier mensaje rescatado.
2. **Claridad Cognitiva, Soberanía Humana y Eliminación de Filtros Duplicados**:
   La presencia simultánea de dos menús desplegables para filtrar el estado del mensaje generaba confusión conceptual y condiciones excluyentes. Unificar toda la lógica en el selector *"Estado del mensaje"* bajo una nomenclatura transparente y ordenada permite al usuario auditar rápidamente cada fase del embudo editorial, garantizando que una decisión humana explícita (como restaurar un mensaje) prime siempre sobre los umbrales algorítmicos.
3. **Visibilidad Holística de la Comunidad en el Dashboard con Normalización Matemática**:
   El Dashboard carecía de una visualización clara sobre la distribución de las conversaciones en los distintos canales temáticos del servidor de Discord. Al calcular la telemetría sobre el universo de los seis canales canónicos oficiales, se garantiza consistencia estadística (suma exacta de 100.0%), visualización precisa de canales con cero actividad (ancho estricto de 0%) y refresco reactivo automático ante cualquier ingesta.
4. **Cumplimiento de la Constitución del Proyecto**:
   La preservación estricta del backend original y motor-ia exige que cualquier cálculo de porcentajes y agrupación por canal se implemente de forma desacoplada en el puente FastAPI (`puente_motor_ia.py`), validado exhaustivamente mediante pruebas TDD.

---

## 2. Requerimientos Funcionales (Formato EARS)

### RF-01: Redirección Contextual a Redacción y Sustitución de Botón en Ingesta de Mensajes
- **MIENTRAS** el usuario explore la lista de mensajes en la pestaña de Ingesta (`/messages`), **EL SISTEMA DEBERÁ** omitir categóricamente el botón *"Analytics"* en todas las tarjetas de mensajes.
- **CUANDO** un mensaje no haya sido evaluado por IA (`isAnalyzed === false`), **EL SISTEMA DEBERÁ** presentar exclusivamente el botón *"Evaluar IA"*, permitiendo ejecutar la inferencia individual.
- **CUANDO** un mensaje haya sido evaluado exitosamente por la IA (`isAnalyzed === true`), **EL SISTEMA DEBERÁ** presentar un botón visible con la etiqueta *"Generar publicación"*, estilizado con diseño interactivo y tipografía clara.
- **SI** el mensaje se encuentra en estado descartado (`curation === 'discarded'` o `status === 'discarded'`), **EL SISTEMA DEBERÁ** deshabilitar el botón *"Generar publicación"* (`disabled={true}`) y asignarle el texto explicativo de tooltip `title="Restaura el mensaje para generar publicación"`.
- **SI** un mensaje analizado posee una relevancia evaluada $< 70\%$ pero no está descartado (por ejemplo, porque el operador humano decidió restaurarlo a estado `'pending'`), **EL SISTEMA DEBERÁ** mantener habilitado el botón *"Generar publicación"*, permitiendo al redactor forzar la redacción de copy editorial si así lo determina.
- **CUANDO** el usuario pulse el botón habilitado *"Generar publicación"*, **EL SISTEMA DEBERÁ** navegar inmediatamente a la ruta `/content?interaction=${message.interactionId}` pasando el identificador de la interacción mediante query param y estado de navegación (`{ state: { interactionId: message.interactionId } }`).
- **CUANDO** la pantalla de Redacción de Contenidos (`ContentStudio.tsx`) se monte recibiendo dicho identificador, **EL SISTEMA DEBERÁ** seleccionar la interacción en la bandeja de redacción y enfocar mediante desplazamiento suave (*smooth scroll*) la tarjeta de *"Mensaje original de Discord"*.

### RF-02: Depuración de Selectores Redundantes, Precedencia Humana y Conteo Contextual en Ingesta
- **MIENTRAS** el usuario interactúe con el *"Panel de filtrado de mensajes"* en `/messages`, **EL SISTEMA DEBERÁ** suprimir el selector desplegable de etapas (`stageFilter`) previamente situado al lado del menú de *"Todos los sentimientos"*.
- **EL SISTEMA DEBERÁ** ubicar el control de filtrado de estado exclusivamente debajo de la etiqueta *"Estado del mensaje"* (`curationFilter`) en la cuadrícula principal de filtros.
- **CUANDO** el usuario despliegue el selector *"Estado del mensaje"*, **EL SISTEMA DEBERÁ** presentar exactamente cinco (5) opciones en el siguiente orden estricto de arriba a abajo:
  1. `Todos los estados` (valor clave: `'all'`)
  2. `Pendientes de evaluar` (valor clave: `'pending_eval'`)
  3. `Pendientes de copy` (valor clave: `'pending_copy'`)
  4. `Proceso completo` (valor clave: `'completos'`)
  5. `Descartado` (valor clave: `'descartados'`)
- **MIENTRAS** se evalúe el estado de cada mensaje, **EL SISTEMA DEBERÁ** aplicar la siguiente jerarquía de precedencia humana (HITL):
  1. La decisión del operador (`curation_status` / `curationStatus[message.id]`) prevalece sobre cualquier decisión automática de IA.
  2. Un mensaje es catalogado como `Descartado` **SI Y SÓLO SI**:
     - `curation_status === "discarded"`, O
     - `isAnalyzed === true` Y `relevance < 70` Y `curation_status !== "curated"` Y `curation_status !== "pending"`.
  3. **SI** un mensaje con baja relevancia ($< 70\%$) es restaurado por el operador humano (su `curation_status` pasa a `'pending'`), **EL SISTEMA DEBERÁ** removerlo inmediatamente de la categoría *"Descartado"* e incluirlo en la categoría *"Pendientes de copy"*.
- **CUANDO** se seleccione `Todos los estados`, **EL SISTEMA DEBERÁ** mostrar todos los mensajes registrados (pendientes, evaluados, listos y descartados).
- **CUANDO** se seleccione `Pendientes de evaluar`, **EL SISTEMA DEBERÁ** mostrar exclusivamente los mensajes sin analizar (`!isAnalyzed` o etapa `ingesta`/`en_ingesta`) que no estén descartados.
- **CUANDO** se seleccione `Pendientes de copy`, **EL SISTEMA DEBERÁ** mostrar exclusivamente los mensajes analizados (`isAnalyzed === true`) que no estén descartados y cuyo flujo de redacción no esté completado (incluyendo mensajes restaurados por humanos).
- **CUANDO** se seleccione `Proceso completo`, **EL SISTEMA DEBERÁ** mostrar exclusivamente los mensajes cuyo flujo editorial haya finalizado (`curation_status === 'curated'` o etapas de aprobación/publicación finalizada) y que no estén descartados.
- **CUANDO** el usuario visualice la cabecera de la cola de mensajes (*"Mostrando N..."*), **EL SISTEMA DEBERÁ** adaptar el texto descriptivo según la opción seleccionada:
  - Para `'all'`: *"Mostrando {N} mensajes en total (Todos los mensajes)"*
  - Para `'pending_eval'`: *"Mostrando {N} mensajes pendientes de evaluar"*
  - Para `'pending_copy'`: *"Mostrando {N} mensajes en la cola de copy"*
  - Para `'completos'`: *"Mostrando {N} mensajes con proceso completo"*
  - Para `'descartados'`: *"Mostrando {N} mensajes descartados"*
  manteniendo el sufijo complementario de fechas `(en rango: X a Y)` si hay fechas filtradas.
- **CUANDO** el usuario pulse el botón *"Deseleccionar"*, **EL SISTEMA DEBERÁ** restablecer el selector de estado al valor `'all'`.

### RF-03: Endpoint de Telemetría de Participación por Canal con Denominador Canónico Oficial (`puente_motor_ia.py`)
- **CUANDO** se consulte la participación por canal a través de `GET /api/community/channel-participation` (o su alias `GET /api/v1/community/channels-participation`), **EL SISTEMA DEBERÁ** retornar la distribución estadística de mensajes registrados para los seis (6) canales oficiales de Discord:
  1. `#general`
  2. `#faq`
  3. `#pqrs`
  4. `#notificaciones`
  5. `#chat-egresados`
  6. `#oportunidades-laborales`
- **MIENTRAS** el backend compute la telemetría, **EL SISTEMA DEBERÁ** normalizar los nombres de canal de las interacciones almacenadas (soportando variantes con o sin prefijo `#`, así como insensibilidad a mayúsculas/minúsculas).
- **EL SISTEMA DEBERÁ** excluir mensajes provenientes de bots o webhooks del sistema (`es_mensaje_bot_o_webhook`).
- **EL SISTEMA DEBERÁ** calcular el denominador total (`total_messages`) como la sumatoria exacta de mensajes válidos pertenecientes a los seis (6) canales oficiales.
- **EL SISTEMA DEBERÁ** calcular para cada canal oficial:
  - `channel`: Nombre formal con prefijo `#` (ej. `"#general"`).
  - `name`: Identificador normalizado en minúsculas sin prefijo (ej. `"general"`).
  - `count`: Conteo absoluto de mensajes válidos registrados en dicho canal.
  - `percentage`: Proporción porcentual calculada sobre `total_messages`, redondeada estrictamente a un (1) decimal (ej. `43.3`).
- **EL SISTEMA DEBERÁ** garantizar que, cuando `total_messages > 0`, la sumatoria de los porcentajes de los 6 canales sume exactamente 100.0% (con ajuste de redondeo al canal mayoritario si existieran discrepancias decimales).
- **SI** `total_messages === 0`, **EL SISTEMA DEBERÁ** retornar `percentage: 0.0` y `count: 0` para los 6 canales, previniendo cualquier error de división por cero (`ZeroDivisionError`).

### RF-04: Componente Modular `ChannelParticipation.tsx` en Dashboard
- **CUANDO** se renderice la pestaña de Dashboard (`frontend/src/pages/Dashboard.tsx`), **EL SISTEMA DEBERÁ** delegar la visualización de la participación por canal en un componente modular desacoplado: `frontend/src/components/ChannelParticipation.tsx`.
- **EL SISTEMA DEBERÁ** montar dicho componente en `Dashboard.tsx` utilizando la propiedad reactiva `key={`channels-${analyticsVersion}`}`, asegurando su desmontaje y recarga automática cada vez que se incremente `analyticsVersion`.
- **EL SISTEMA DEBERÁ** renderizar en `ChannelParticipation.tsx`:
  - Contenedor con borde (`border border-slate-200`), fondo blanco (`bg-white`) y esquinas redondeadas (`rounded-2xl`).
  - Encabezado con glifo `#` en acento naranja destacado (`text-orange-500 font-bold text-lg`), título *"Participación por canal"* (`font-bold text-slate-900`) y subtítulo descriptivo *"Distribución de mensajes registrados en los seis canales de Discord"* (`text-xs text-slate-500`).
  - Las seis (6) filas en estricto orden oficial: `#general`, `#faq`, `#pqrs`, `#notificaciones`, `#chat-egresados`, `#oportunidades-laborales`.
- **MIENTRAS** se renderice cada fila de canal, **EL SISTEMA DEBERÁ** exhibir:
  1. Nombre del canal a la izquierda con prefijo `#` (ej. `#general`).
  2. Porcentaje y conteo a la derecha en formato `XX.X% · N` (ej. `43.3% · 42`).
  3. Barra horizontal de progreso con contenedor gris claro (`bg-slate-100 rounded-full h-2`) y barra interior de relleno naranja (`bg-orange-500 rounded-full`).
- **SI** un canal registra cero mensajes (`0` mensajes / `0.0%`), **EL SISTEMA DEBERÁ** aplicar un ancho estricto de 0% (`style={{ width: '0%' }}`), garantizando que no se visualicen bordes, residuos ni bloques de relleno naranja para canales vacíos.

### RF-05: Sincronización Reactiva, Consistencia Temporal y Tolerancia a Errores
- **CUANDO** el usuario pulse el botón *"Actualizar datos"* en el Dashboard, **EL SISTEMA DEBERÁ** incrementar `analyticsVersion`, desencadenando la consulta en vivo de `ChannelParticipation.tsx` en sincronía con KPIs, gráficos e historias destacadas.
- **SI** la petición de participación por canal experimenta una falla de red o error HTTP del backend, **EL SISTEMA DEBERÁ** mantener la integridad de la interfaz aplicando un estado de reserva degradado (*graceful fallback*) con los seis canales oficiales inicializados en `0.0% · 0` y `total_messages: 0`, sin interrumpir ni bloquear el renderizado del resto de módulos del Dashboard.
- **MIENTRAS** los datos se encuentren en proceso de carga inicial, **EL SISTEMA DEBERÁ** desplegar un estado sutil de carga (esqueleto o spinner) para evitar desplazamientos bruscos en la interfaz.

### RF-06: Inviolabilidad Constitucional, Aislamiento de Código y Verificación TDD
- **MIENTRAS** se implementen las soluciones de backend y frontend, **EL SISTEMA DEBERÁ** mantener estrictamente intactos e inalterados los 17 archivos preexistentes en la raíz, así como las carpetas `backend/` y `motor-ia/`.
- **EL SISTEMA DEBERÁ** estructurar toda la lógica exclusivamente en `puente_motor_ia.py`, `frontend/src/` y `tests/`.
- **EL SISTEMA DEBERÁ** añadir pruebas unitarias y de integración en `tests/test_unificacion_motor_ia.py` que comprueben:
  1. Cálculo de porcentajes sobre los 6 canales oficiales y verificación de suma 100.0%.
  2. Manejo determinista ante 0 mensajes (prevención de `ZeroDivisionError`).
  3. Exclusión de bots y webhooks en el cálculo de canales.
  4. Contratos de respuesta JSON (`total_messages` y lista de `channels`).
- **EL SISTEMA DEBERÁ** certificar que el 100% de la suite de pruebas del proyecto permanezca en verde (`pytest tests/ -v`) y que el frontend compile sin errores de tipado (`npm run build`).

---

## 3. Contratos de API y Modelos de Datos

### 3.1 Contrato de API: Telemetría de Canales

#### `GET /api/community/channel-participation` y Alias `GET /api/v1/community/channels-participation`
- **Descripción**: Provee la distribución consolidada de mensajes en los 6 canales canónicos oficiales de Discord.
- **Parámetros**: Ninguno.
- **Respuesta Exitosa (HTTP 200 OK)**:
  ```json
  {
    "total_messages": 55,
    "channels": [
      {
        "channel": "#general",
        "name": "general",
        "count": 22,
        "percentage": 40.0
      },
      {
        "channel": "#faq",
        "name": "faq",
        "count": 14,
        "percentage": 25.5
      },
      {
        "channel": "#pqrs",
        "name": "pqrs",
        "count": 0,
        "percentage": 0.0
      },
      {
        "channel": "#notificaciones",
        "name": "notificaciones",
        "count": 0,
        "percentage": 0.0
      },
      {
        "channel": "#chat-egresados",
        "name": "chat-egresados",
        "count": 11,
        "percentage": 20.0
      },
      {
        "channel": "#oportunidades-laborales",
        "name": "oportunidades-laborales",
        "count": 8,
        "percentage": 14.5
      }
    ]
  }
  ```

- **Respuesta en Caso Límite (0 mensajes registrados)**:
  ```json
  {
    "total_messages": 0,
    "channels": [
      { "channel": "#general", "name": "general", "count": 0, "percentage": 0.0 },
      { "channel": "#faq", "name": "faq", "count": 0, "percentage": 0.0 },
      { "channel": "#pqrs", "name": "pqrs", "count": 0, "percentage": 0.0 },
      { "channel": "#notificaciones", "name": "notificaciones", "count": 0, "percentage": 0.0 },
      { "channel": "#chat-egresados", "name": "chat-egresados", "count": 0, "percentage": 0.0 },
      { "channel": "#oportunidades-laborales", "name": "oportunidades-laborales", "count": 0, "percentage": 0.0 }
    ]
  }
  ```

---

### 3.2 Modelos de Datos en TypeScript (`frontend/src/api/communityLive.ts`)

```typescript
export interface ChannelParticipationItem {
  channel: string      // e.g. "#general"
  name: string         // e.g. "general"
  count: number        // e.g. 42
  percentage: number   // e.g. 43.3
}

export interface ChannelParticipationResponse {
  total_messages: number
  channels: ChannelParticipationItem[]
}

export async function getChannelParticipation(): Promise<ChannelParticipationResponse> {
  // Consulta a /api/community/channel-participation con fallback resiliente
}
```

---

### 3.3 Modelo de Navegación Contextual (Ingesta $\rightarrow$ Redacción)

- **Origen**: `frontend/src/pages/Messages.tsx`
  - Acción: Click en botón *"Generar publicación"*.
  - Llamada:
    ```typescript
    navigate(`/content?interaction=${message.interactionId}`, {
      state: { interactionId: message.interactionId },
    })
    ```
- **Destino**: `frontend/src/pages/ContentStudio.tsx`
  - Recepción: Lectura de query param `interaction` o `location.state.interactionId`.
  - Acción: Selección inmediata de `selectedMessageId` y ejecución de scroll suave a `originalMessageRef`.

---

## 4. Casos Límite (Edge Cases) y Mitigaciones

1. **Canales con cero mensajes registrados en la base de datos**:
   - *Riesgo*: Si canales como `#pqrs` o `#notificaciones` aún no tienen mensajes, podrían omitirse del listado o mostrar barras residuales.
   - *Mitigación*: El backend itera deterministamente sobre la lista canónica de los 6 canales oficiales; si un canal no posee registros, se inicializa explícitamente con `count: 0` y `percentage: 0.0`. En la interfaz, se aplica `width: '0%'` sin margen ni padding interior.
2. **Corpus vacío (0 mensajes en total en la plataforma)**:
   - *Riesgo*: Una fórmula como `(count / total) * 100` lanzaría una excepción `ZeroDivisionError` en Python o `NaN` en JavaScript.
   - *Mitigación*: Condicional explícito en backend: si `total_messages == 0`, asignar de forma segura `0.0` a todos los porcentajes.
3. **Nombres de canales heterogéneos en los registros existentes**:
   - *Riesgo*: Variaciones en el almacenamiento como `'general'`, `'#general'`, `'GENERAL'` o `'#General'` podrían provocar discrepancias de agrupamiento.
   - *Mitigación*: Normalización preventiva con `.lstrip('#').strip().lower()` tanto al indexar como al asociar los conteos a la lista oficial.
4. **Mensajes de bots o webhooks**:
   - *Riesgo*: Mensajes automáticos de bot inflarían artificialmente los conteos de `#general` o `#notificaciones`.
   - *Mitigación*: Reutilización del filtro `es_mensaje_bot_o_webhook` o exclusión de autores con sufijo `#0000` y término `bot`, manteniendo coherencia con las métricas de audiencia humana.
5. **Mensaje analizado pero con ID ausente en la primera página de Redacción**:
   - *Riesgo*: Al redirigir desde Ingesta a Redacción, si el mensaje no está en la primera carga de la bandeja de Enoc, la tarjeta de *"Mensaje original de Discord"* podría quedar en blanco.
   - *Mitigación*: `ContentStudio.tsx` cuenta con mecanismo de resolución atómica de interacciones por ID (a través de búsqueda en corpus completo o fallback a `live-summary`), asegurando que cualquier mensaje analizado válido sea inyectado y seleccionado correctamente.
6. **Desincronización de filtros en Ingesta tras deselección**:
   - *Riesgo*: Si el usuario pulsa *"Deseleccionar"*, podrían quedar residuos de estados previos.
   - *Mitigación*: La función `clearFilters()` limpia de forma unificada el selector `curationFilter` a `'all'`, asegurando la presentación completa del listado de mensajes.
7. **Precedencia Humana ante Baja Relevancia**:
   - *Riesgo*: Un mensaje de relevancia 45% restaurado por un operador humano podría ser filtrado incorrectamente como descartado por el sistema.
   - *Mitigación*: En `Messages.tsx`, la condición de descarte evalúa explícitamente `curation_status !== 'pending' && curation_status !== 'curated'`, de modo que una restauración humana sobreescribe el umbral algorítmico y traslada el mensaje a *"Pendientes de copy"*.

---

## 5. Criterios de Aceptación Globales

1. **Ingesta de Mensajes (`Messages.tsx`)**:
   - El botón *"Analytics"* ya no existe en ninguna tarjeta de mensaje.
   - Cada tarjeta cuyo mensaje fue analizado (`isAnalyzed === true`) muestra el botón *"Generar publicación"*.
   - Si el mensaje está descartado, *"Generar publicación"* está deshabilitado con `title="Restaura el mensaje para generar publicación"`.
   - Si el mensaje posee relevancia $< 70\%$ pero no está descartado (o fue restaurado por el operador), *"Generar publicación"* permanece habilitado permitiendo la redacción forzada de Enoc.
   - Al pulsar *"Generar publicación"*, la aplicación redirige a `/content?interaction=${message.interactionId}` con `{ state: { interactionId } }`, y la vista de Redacción enfoca la tarjeta del mensaje original seleccionado con scroll suave.
   - El selector redundante situado junto a *"Todos los sentimientos"* ha sido removido.
   - El selector bajo *"Estado del mensaje"* presenta exclusivamente las 5 opciones requeridas en su estricto orden:
     1. Todos los estados
     2. Pendientes de evaluar
     3. Pendientes de copy
     4. Proceso completo
     5. Descartado
   - La lista de mensajes responde fielmente filtrando según la etapa y condición real de cada mensaje, respetando la precedencia de decisiones humanas sobre las automáticas.
   - Los rótulos de conteo contextual en la cabecera de la cola exhiben con exactitud:
     * `'all'`: *"mensajes en total (Todos los mensajes)"*
     * `'pending_eval'`: *"mensajes pendientes de evaluar"*
     * `'pending_copy'`: *"mensajes en la cola de copy"*
     * `'completos'`: *"mensajes con proceso completo"*
     * `'descartados'`: *"mensajes descartados"*
2. **Dashboard (`Dashboard.tsx` y `ChannelParticipation.tsx`)**:
   - Se crea el componente modular `frontend/src/components/ChannelParticipation.tsx` y se monta en `Dashboard.tsx` con clave `<ChannelParticipation key={`channels-${analyticsVersion}`} />`.
   - Se exhibe la sección *"# Participación por canal"* con el símbolo `#` en acento naranja y su subtítulo descriptivo.
   - Se listan los 6 canales oficiales de Discord en su orden exacto: `#general`, `#faq`, `#pqrs`, `#notificaciones`, `#chat-egresados`, `#oportunidades-laborales`.
   - Cada fila muestra nombre a la izquierda, porcentaje con un decimal y conteo a la derecha (`XX.X% · N`), y barra de progreso con fondo gris claro y relleno naranja proporcional (ancho estricto de `0%` si el canal tiene 0 mensajes).
   - Los porcentajes y el total de mensajes se calculan sobre la sumatoria de mensajes de los 6 canales oficiales, sumando exactamente 100.0% (o 0.0% si la suma es 0).
   - Los datos se actualizan reactivamente al presionar *"Actualizar datos"*.
   - Ante errores de red o backend, se aplica fallback con los 6 canales en 0.0% sin romper el resto del Dashboard.
3. **Inviolabilidad Constitucional y Calidad**:
   - Los 17 archivos preexistentes en la raíz, `backend/` y `motor-ia/` permanecen estrictamente inmutables.
   - El 100% de la suite de pruebas automatizadas pasa en verde (`pytest tests/ -v`).
   - El frontend compila de manera limpia sin errores (`npm run build`).
