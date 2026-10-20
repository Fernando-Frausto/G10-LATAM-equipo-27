# Spec 017 — Corrección Tipográfica Global, Terminología Intuitiva, Scroll de Mensajes, Telemetría Real de Bots y Navegación de Quejas

- **Estado:** Especificación Aprobada tras Revisión de QA (@reviewer)
- **Fecha:** 2026-10-19
- **Autor:** @planner
- **Rama objetivo:** `feature/optimizacion-ux-dashboard-analisis-ingesta`

---

## 1. Contexto y Justificación del Negocio (QUÉ y POR QUÉ)

### ¿Qué se necesita?
Optimizar integralmente la experiencia de usuario (UX), la precisión semántica y la robustez técnica en las vistas operativas de la plataforma CloudEdTech (`Ingesta de mensajes`, `Análisis` y `Redacción de contenidos`), resolviendo seis frentes clave validados por QA:
1. **Saneamiento tipográfico y de codificación UTF-8 en la UI:** Erradicar de raíz todos los caracteres `?` o artefactos corruptos generados por discrepancias de codificación que sustituyen a vocales acentuadas, letras especiales o signos en español en los textos estáticos de la interfaz, badges, modales, mensajes de error y clientes de API del frontend (`Messages.tsx`, `Analytics.tsx`, `ContentStudio.tsx`, `api/contentWorkflow.ts`, `api/messageCuration.ts`, `api/motorContent.ts`, etc.), preservando intacto el corpus de preguntas legítimas de la comunidad.
2. **Terminología intuitiva orientada a la publicación:** Reemplazar el tecnicismo interno "copy" por la acción clara de cara al usuario "publicar" / "publicación" en filtros, badges informativos y contadores de la pestaña Ingesta de Mensajes (`Messages.tsx`).
3. **Scroll vertical responsivo para ingesta:** Incorporar un contenedor con scroll vertical delimitado y responsivo (`max-h-[min(850px,70vh)] overflow-y-auto pr-2`) en el listado de interacciones de `Messages.tsx` para erradicar el scroll infinito de página completa tanto en pantallas de escritorio como en laptops de 768p, manteniendo los paneles de control siempre accesibles.
4. **Control dinámico del tamaño de lote para evaluación IA y blindaje backend:** Sustituir la casilla redundante "Solo pendientes de evaluar" por un selector de lote interactivo con opciones fijas (**1**, **5**, **10**) y una opción contextual dinámica `"Evaluar todos ({conteo})"` cuando existan entre 1 y 10 mensajes pendientes evaluables (sin duplicar opciones numéricas ya existentes). En el backend, garantizar que `ver_json.py` permanezca estrictamente inmutable y que `puente_motor_ia.py` aplique el corte exacto `[:limite]` sobre la lista filtrada de pendientes.
5. **Telemetría real de bots y mensajes humanos con contrato de API ampliado:** Extender el contrato JSON de `/api/community/messages` en `puente_motor_ia.py` para devolver `omitted_bots_count: int` y `real_messages_count: int` preservando retrocompatibilidad total, y transformar los apartados informativos contiguos al botón "Sincronizar Discord" en `Messages.tsx` para exhibir con datos reales calculados los **"Mensajes omitidos de bots"** y los **"Mensajes reales detectados"**.
6. **Métricas reales de insights y navegación asíncrona a soporte crítico:** Garantizar que las tres tarjetas de insights de `Analytics.tsx` muestren métricas calculadas con datos reales de la comunidad y dotar a la tarjeta de "Atención requerida" del botón interactivo unificado `"Gestionar quejas y reclamos"`, el cual conducirá al usuario hacia el ancla `#panel-quejas` en `ContentStudio.tsx` mediante un desplazamiento suave resiliente al renderizado asíncrono.
7. **Políticas de CI/CD, despliegue y TDD:** Eliminar la directiva `[skip netlify]` de los commits para garantizar despliegues continuos automáticos, aplicar diseño Test-First (TDD) para toda lógica de backend y documentar formalmente las variables de entorno requeridas para Enoc y la plataforma en Netlify y Render.

### ¿Por qué es necesario?
- **Calidad profesional y legibilidad sin alteración de datos:** La presencia de signos de interrogación (`?`) en palabras cotidianas como "curaduría", "interacción", "válida", "atención" o "crítico" devalúa la presentación profesional ante los usuarios y dificulta la comprensión. Al mismo tiempo, debe protegerse estrictamente el contenido redactado por los usuarios para no desvirtuar las preguntas auténticas del corpus.
- **Claridad cognitiva en el flujo editorial:** Para los operadores y moderadores, el concepto de "copy" resulta ambiguo; la semántica natural de la plataforma es preparar el contenido para su "publicación" en Discord, LinkedIn y X.
- **Ergonomía de navegación adaptable a cualquier pantalla:** Conforme el volumen de mensajes en Discord crece, navegar decenas o cientos de tarjetas obliga a desplazarse verticalmente por toda la pantalla perdiendo de vista los filtros y las acciones superiores. Una altura máxima responsiva basada en viewport (`max-h-[min(850px,70vh)]`) garantiza una experiencia consistente tanto en monitores de alta resolución como en laptops estándar.
- **Eficiencia y exactitud en el consumo de IA:** Evaluar mensajes con modelos de lenguaje densos (como Google Gemma 4 de 31B) toma entre 30 y 45 segundos por mensaje. Permitir al usuario elegir con precisión si evalúa 1, 5, 10 o todo el lote remanente evita esperas excesivas. Garantizar que el backend corte sobre los pendientes reales asegura que el límite seleccionado se cumpla rigurosamente sin violar la inmutabilidad de los módulos raíz.
- **Transparencia en el filtrado de comunidad:** El equipo necesita constatar que el motor de ingesta discrimina efectivamente la actividad ruidosa de bots/webhooks frente a las intervenciones humanas reales que alimentan los análisis, contando con un contrato formal de API que respalde estos indicadores.
- **Resolución fluida de quejas críticas:** La navegación anclada entre el diagnóstico de riesgo en Análisis y la resolución operativa en Redacción agiliza la atención de soporte crítico, debiendo ser tolerante a cargas asíncronas para que el scroll siempre alcance su objetivo.

---

## 2. Requerimientos Funcionales (Formato EARS)

### RF-001: Saneamiento Tipográfico y de Codificación UTF-8 en la UI con Preservación del Corpus
- **MIENTRAS** el usuario interactúe con cualquier vista, modal, notificación, tooltip o elemento de la aplicación frontend (`Messages.tsx`, `Analytics.tsx`, `ContentStudio.tsx`, `api/contentWorkflow.ts`, `api/messageCuration.ts`, `api/motorContent.ts` y componentes asociados), **EL SISTEMA DEBERÁ** exhibir todas las cadenas de texto estáticas y generadas por el sistema con la ortografía y acentuación correctas en idioma español, reemplazando de manera exhaustiva cualquier signo `?` o carácter corrupto por su grafía correspondiente (incluyendo explícitamente: `curaduría`, `interacción`, `válida`, `inválido`, `confirmó`, `Atención`, `crítico`, `Señales`, `revisión`, `aquí`, `envían`, `telemetría`, `semántica` y variantes).
- **MIENTRAS** se ejecute dicho saneamiento, **EL SISTEMA DEBERÁ** preservar inalterados los contenidos de mensajes genuinos redactados por los usuarios de la comunidad (`message.content` o corpus crudo de Discord), manteniendo íntegros los signos de interrogación auténticos utilizados en preguntas ciudadanas.
- **POR QUÉ:** Asegura una experiencia de usuario impecable, coherente y profesional en la interfaz sin corromper ni alterar la autenticidad de los datos textuales de la comunidad.

### RF-002: Estandarización de Terminología Hacia "Publicar" en Ingesta de Mensajes
- **MIENTRAS** el usuario navegue en la pestaña `"Ingesta de mensajes"` (`Messages.tsx`), **EL SISTEMA DEBERÁ** presentar una terminología orientada a la publicación en lugar del término técnico "copy", aplicando las siguientes sustituciones exactas:
  1. En el panel de "Evaluación por Lote con Inteligencia Artificial": sustituir el indicador de etapa `"pendientes de copy"` por `"Pendientes de publicar"`.
  2. En el panel de filtrado, en el selector desplegable `"Estado del mensaje"`: sustituir la opción `"Pendientes de copy"` por `"Pendientes de publicar"`.
  3. En las tarjetas individuales de mensajes del listado: sustituir el badge de etapa que indicaba `"Copy"` por `"Publicar"`.
  4. En la insignia informativa de estado superior al bloque de descartar/copiar: sustituir el texto `"Falta redacción de copy"` por `"Falta redacción de publicación"`.
- **POR QUÉ:** Unifica la semántica de la interfaz hacia el objetivo final del contenido (la difusión en canales oficiales), reduciendo la fricción conceptual del equipo.

### RF-003: Contenedor con Scroll Vertical Delimitado y Responsivo en Listado de Mensajes
- **MIENTRAS** el listado de mensajes en la pestaña `"Ingesta de mensajes"` (`Messages.tsx`) contenga una o múltiples interacciones, **EL SISTEMA DEBERÁ** confinar las tarjetas dentro de un contenedor con altura máxima delimitada y responsiva utilizando la clase `max-h-[min(850px,70vh)] overflow-y-auto pr-2`, garantizando que el scroll vertical opere exclusivamente sobre la lista de mensajes sin desplazar la página completa tanto en monitores de escritorio como en laptops con pantallas de 768p, y manteniendo visibles los encabezados, KPIs y paneles superiores.
- **POR QUÉ:** Mejora ergonómicamente la navegación del operador al evitar el scroll infinito de la página completa, asegurando adaptabilidad multidispositivo.

### RF-004: Control Dinámico de Tamaño de Lote y Blindaje en Backend Inmutable
- **CUANDO** el usuario visualice el panel `"Evaluación por Lote con Inteligencia Artificial"` en `Messages.tsx`:
  1. **EL SISTEMA DEBERÁ** retirar definitivamente la casilla de verificación (checkbox) y la etiqueta `"Solo pendientes de evaluar"`, manteniendo en el backend la regla de evaluar exclusivamente interacciones pendientes de análisis.
  2. **EL SISTEMA DEBERÁ** incorporar un selector desplegable estilizado (`<select>`) para definir la cantidad de mensajes a procesar por lote, ofreciendo las opciones numéricas fijas de **1**, **5** y **10** mensajes.
  3. **MIENTRAS** la cantidad de mensajes evaluables pendientes ($C$) satisfaga $1 \le C \le 10$ y no coincida con los valores numéricos fijos ($C \notin \{1, 5, 10\}$), **EL SISTEMA DEBERÁ** incluir dinámicamente en el selector la opción `"Evaluar todos ({conteo})"` (por ejemplo: `"Evaluar todos (7)"`).
  4. **EL SISTEMA DEBERÁ** fijar el valor seleccionado por defecto en `5` (o en el conteo total de pendientes disponibles si este es menor a 5).
  5. **SI** el conteo de mensajes pendientes evaluables es igual a `0`, **EL SISTEMA DEBERÁ** deshabilitar el `<select>` mostrando la opción informativa `"Sin pendientes"` y deshabilitar el botón de evaluación por lote.
  6. **CUANDO** el usuario pulse el botón `"Evaluar mensajes con IA"`, **EL SISTEMA DEBERÁ** despachar la solicitud `POST /api/v1/ai/evaluate-batch` enviando en el campo `limite` el valor seleccionado en dicho selector desplegable.
  7. **EN EL BACKEND**, preservando estrictamente la inmutabilidad de `ver_json.py` (archivo protegido de la raíz), **EL SISTEMA DEBERÁ** en `puente_motor_ia.py` solicitar a `ver_json.py` un universo holgado de mensajes y aplicar el corte exacto `[:limite]` sobre la lista filtrada de pendientes de evaluación, garantizando que siempre se evalúe exactamente la cantidad solicitada.
- **POR QUÉ:** Proporciona un control granular sobre el tiempo de procesamiento y consumo de cuotas de las IAs, retirando opciones superfluas, evitando duplicidad en el selector y garantizando en backend el cumplimiento del lote sin alterar el código protegido.

### RF-005: Extensión de Contrato de API y Telemetría Real de Bots y Mensajes Humanos
- **CUANDO** se consulte el endpoint de listado de mensajes (`GET /api/community/messages`), **EL SISTEMA DEBERÁ** retornar un contrato JSON ampliado y 100% retrocompatible que incluya:
  - `total: int` (conteo total de mensajes devueltos en la colección actual).
  - `omitted_bots_count: int` (cifra real acumulada de mensajes originados por bots y webhooks discriminados mediante `_es_cuenta_bot`).
  - `real_messages_count: int` (cifra real acumulada de interacciones provenientes de miembros humanos genuinos de la comunidad almacenadas en SQLite).
  - `messages: list[dict]` (colección de mensajes con su análisis y trazabilidad).
- **CUANDO** se cargue la sección informativa contigua al botón `"Sincronizar Discord"` en la pestaña `"Ingesta de mensajes"` (`Messages.tsx`), **EL SISTEMA DEBERÁ**:
  1. Sustituir el apartado `"Pendientes en Copy"` por el apartado `"Mensajes omitidos de bots"`.
  2. Sustituir el apartado `"Incidentes prioritarios"` por el apartado `"Mensajes reales detectados"`.
  3. Mostrar en `"Mensajes omitidos de bots"` el valor de `omitted_bots_count` provisto por el backend (o su cálculo correspondiente sobre interacciones).
  4. Mostrar en `"Mensajes reales detectados"` el valor de `real_messages_count` provisto por el backend.
- **POR QUÉ:** Establece un contrato formal de API transparente y retrocompatible, dotando a la cabecera de ingesta de indicadores directos sobre la efectividad del filtrado de ruido y el volumen genuino de conversaciones de la comunidad.

### RF-006: Tarjetas de Insights con Métricas Reales en Análisis
- **MIENTRAS** el usuario consulte la sección inferior de insights en la pestaña `"Análisis"` (`Analytics.tsx`), **EL SISTEMA DEBERÁ** calcular y exhibir métricas con base en los datos reales de la comunidad:
  1. **Insight principal:** Informar el tema con mayor presencia semántica porcentual y volumen relativo según los mensajes analizados de la comunidad.
  2. **Preguntas frecuentes:** Reportar el conteo consolidado de preguntas detectadas en las conversaciones y desglosar el tema recurrente donde más dudas se concentran.
  3. **Atención requerida:** Cuantificar el volumen de mensajes con sentimiento negativo detectados y el número de incidentes de relevancia prioritaria ($\ge 70\%$).
- **POR QUÉ:** Asegura que las conclusiones analíticas reflejen la telemetría viva de la comunidad y no dependan de textos genéricos ni suposiciones estáticas.

### RF-007: Navegación Asíncrona desde Atención Requerida Hacia Panel de Quejas
- **CUANDO** el usuario visualice la tarjeta `"Atención requerida"` en la pestaña `"Análisis"` (`Analytics.tsx`), **EL SISTEMA DEBERÁ** presentar un botón de acción interactivo con la etiqueta exacta `"Gestionar quejas y reclamos"`.
- **CUANDO** el usuario pulse dicho botón de acción, **EL SISTEMA DEBERÁ** redirigir la navegación hacia la ruta `/content#panel-quejas` en `"Redacción de contenidos"`.
- **EN `ContentStudio.tsx`**, **EL SISTEMA DEBERÁ** asignar el atributo identificador `id="panel-quejas"` al contenedor principal de la sección `"Panel de Quejas, Reclamos y Soporte Crítico"` e implementar un hook `useEffect` que escuche los cambios en `location.hash` para ejecutar un desplazamiento suave (`scrollIntoView({ behavior: 'smooth' })`), garantizando resiliencia ante el renderizado asíncrono o la carga diferida de datos de quejas.
- **POR QUÉ:** Conecta de forma fluida y confiable el hallazgo analítico de inconformidades con la mesa de respuesta operativa de Enoc, garantizando que el scroll alcance el elemento incluso si los datos terminan de montarse milisegundos después de la navegación.

### RF-008: Eliminación de [skip netlify] en Commits y Automatización de CI/CD
- **MIENTRAS** se registren commits y se gestionen ramas de características, **EL SISTEMA DEBERÁ** prescindir de la etiqueta de omisión `[skip netlify]` en los mensajes de commit, permitiendo que cada actualización sobre el repositorio dispare los pipelines de compilación y despliegue del frontend en Netlify.
- **POR QUÉ:** Garantiza la disponibilidad inmediata y continua de la interfaz en el entorno de despliegue en la nube para auditorías de producción.

### RF-009: Documentación de Despliegue y Variables de Entorno para Enoc
- **AL FINALIZAR** la implementación de la especificación, **EL SISTEMA DEBERÁ** proveer una guía exhaustiva y documentada con la lista exacta de variables de entorno, claves de API (`GROQ_API_KEY`, `GEMINI_API_KEY`, `SUPABASE_DB_URL`, tokens de Discord) y pasos de configuración necesarios tanto para el despliegue del motor en Render como para el frontend en Netlify.
- **POR QUÉ:** Facilita la réplica del entorno, previene caídas por omisión de configuración de secretos y cumple con la directiva de seguridad de `docs/constitution.md`.

### RF-010: Inviolabilidad Constitucional, Aislamiento y Diseño Test-First (TDD)
- **MIENTRAS** se ejecuten las tareas de corrección, refinamiento y navegación:
  1. **EL SISTEMA DEBERÁ** preservar sin alteraciones los 17 archivos protegidos de la raíz (incluyendo estrictamente `ver_json.py` y `base_datos.py`), la carpeta `backend/`, `motor-ia/` y el directorio `src/` canónico de Enoc, implementando cualquier soporte de servidor en `puente_motor_ia.py` y las mejoras de experiencia en `frontend/src/`.
  2. Siguiendo la Regla 6 de la Constitución (Diseño Test-First), **EL SISTEMA DEBERÁ** asegurar que la extensión del contrato JSON de `/api/community/messages` y la lógica del límite de evaluación por lote en `puente_motor_ia.py` cuenten con sus correspondientes pruebas unitarias automatizadas (`pytest`) antes de dar por completada la implementación.
- **POR QUÉ:** Asegura el cumplimiento riguroso de `docs/constitution.md` (Reglas 1, 3, 4 y 6) y `AGENTS.md`, salvaguardando la estabilidad y verificabilidad de todo el sistema.

---

## 3. Criterios de Aceptación y Escenarios de Verificación

1. **Escenario 1: Inspección Tipográfica y Ortográfica Exhaustiva**
   - **Dado** que se inspeccionan visualmente las pestañas `Ingesta de mensajes`, `Análisis` y `Redacción de contenidos`.
   - **Cuando** se examinen textos, badges, botones, tooltips y modales de soporte o curaduría.
   - **Entonces** no debe existir ningún carácter `?` o de reemplazo en lugar de acentos (verificando palabras como `curaduría`, `interacción`, `válida`, `inválido`, `confirmó`, `Atención`, `crítico`, etc.).
   - **Y además**, los textos redactados por los usuarios de la comunidad que contengan preguntas reales deben conservar sus signos de interrogación intactos.

2. **Escenario 2: Verificación de Terminología "Publicar" y Scroll Responsivo en Ingesta**
   - **Dado** que el usuario abre `/messages`.
   - **Cuando** revisa el selector de etapas de filtrado, las tarjetas de mensajes y las insignias de estado.
   - **Entonces** debe leer `"Pendientes de publicar"` en lugar de `"Pendientes de copy"`, `"Publicar"` en lugar de `"Copy"` en el badge de tarjeta, y `"Falta redacción de publicación"` arriba de los botones de acción.
   - **Además**, el contenedor de tarjetas debe contar con la clase `max-h-[min(850px,70vh)] overflow-y-auto pr-2`, manteniendo un scroll contenido que evita desplazar toda la página tanto en pantallas grandes como en laptops de 768p.

3. **Escenario 3: Selección Dinámica del Lote de IA y Blindaje Backend**
   - **Dado** que hay mensajes pendientes de evaluar.
   - **Cuando** el usuario interactúa con el panel de evaluación por lote:
     - No debe existir la casilla `"Solo pendientes de evaluar"`.
     - El selector desplegable debe ofrecer las opciones fijas **1**, **5**, **10**.
     - Si el conteo de pendientes $C$ está entre 1 y 10 y no es 1, 5 ni 10 (ej. $C = 7$), debe exhibir adicionalmente `"Evaluar todos (7)"`.
     - Si $C = 5$, no debe duplicarse la opción de 5.
     - El valor por defecto debe ser `5` (o el total de pendientes si es menor a 5).
     - Si $C = 0$, el `<select>` debe deshabilitarse mostrando `"Sin pendientes"`.
   - **Cuando** se pulsa `"Evaluar mensajes con IA"`, la petición debe enviar el `limite` seleccionado.
   - **En el backend**, `puente_motor_ia.py` debe aplicar `[:limite]` sobre la lista filtrada de pendientes de evaluación sin alterar `ver_json.py`.

4. **Escenario 4: Extensión de Contrato de API y Métricas de Cabecera**
   - **Dado** que el frontend consulta `GET /api/community/messages`.
   - **Cuando** se recibe la respuesta JSON.
   - **Entonces** la respuesta contiene `omitted_bots_count`, `real_messages_count`, `total` y `messages`.
   - **Y en la interfaz**, al lado de `"Sincronizar Discord"`, se exhiben `"Mensajes omitidos de bots"` y `"Mensajes reales detectados"` alimentados con dichos valores calculados.

5. **Escenario 5: Navegación Asíncrona de Alertas de Análisis hacia Panel de Quejas**
   - **Dado** que el usuario visualiza la pestaña `/analytics`.
   - **Cuando** observa la tarjeta `"Atención requerida"`, visualiza el botón `"Gestionar quejas y reclamos"` y lo pulsa.
   - **Entonces** la aplicación navega a `/content#panel-quejas`.
   - **Y en `ContentStudio.tsx`**, el `useEffect` detecta `#panel-quejas` y desplaza suavemente la ventana hacia la sección `#panel-quejas`, posicionándola en pantalla incluso tras cargas asíncronas.

6. **Escenario 6: Despliegue en CI/CD, Pruebas TDD y Guía de Variables**
   - **Dado** que se implementan los cambios.
   - **Cuando** se ejecutan las pruebas automatizadas, se verifica el paso exitoso de los tests de contrato de mensajes y evaluación por lotes.
   - **Cuando** se registra el commit, este no contiene `[skip netlify]` y dispara la compilación en Netlify.
   - **Y al finalizar**, se entrega la guía documentada con las variables de entorno de Enoc para Render y Netlify.
