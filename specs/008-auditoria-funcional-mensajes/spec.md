# Especificación 008: Auditoría y Consistencia Funcional de la Pestaña de Mensajes

## 1. Contexto y Propósito

### ¿Qué se busca lograr?
Garantizar la consistencia operativa, integridad visual y funcionalidad al 100% de todos los controles de la pestaña de Mensajes (`frontend/src/pages/Messages.tsx`), eliminando botones duplicados o inoperativos, removiendo elementos desconectados sin funcionalidad (checkboxes huérfanos), corrigiendo el filtrado de mensajes descartados, habilitando la acción bidireccional de restauración de descartes mediante el icono `RotateCcw`, deshabilitando preventivamente acciones incompatibles en mensajes descartados, desbloqueando la navegación hacia Analytics en mensajes en etapas avanzadas y reconciliando las métricas del bloque de Estado de Discord con los datos reales procesados.

### ¿Por qué es necesario?
1. **Eliminación de Redundancias Operativas:** El botón de sincronización con Discord aparece dos veces de forma idéntica en la misma pantalla (en el bloque de estado de Discord y en la barra de filtros), lo que satura la interfaz de usuario y genera confusión sobre la acción a realizar.
2. **Remoción de Controles Inútiles:** El botón "Añadir interacción" permanece indefinidamente deshabilitado al no existir una vía backend de creación manual, y las tarjetas de mensaje contienen casillas de verificación (`<input type="checkbox">`) huérfanas sin estado, sin controladores de eventos y sin barra de acciones masivas, generando una falsa expectativa operativa.
3. **Restitución de la Auditabilidad y Coexistencia de Filtros:** Una condición de exclusión estricta en el filtrado de la vista oculta los mensajes descartados incluso cuando el operador selecciona intencionalmente la opción "Descartado" en el filtro de curaduría. Es indispensable que al seleccionar dicho filtro se muestren los mensajes descartados combinados armoniosamente con el filtro de etapa (`stageFilter`) y que la cabecera de la cola informe explícitamente "Mostrando X mensajes descartados".
4. **Capacidad de Corrección Humana (HITL Bidireccional):** Actualmente el operador solo cuenta con la opción de descartar un mensaje; si se comete un error, se debe contar con un botón de reversión visible (`RotateCcw`) con estilo diferenciado (`text-emerald-600 hover:bg-emerald-50 hover:text-emerald-700`) y tooltip "Restaurar mensaje a pendientes" que llame a `updateMessageCuration(message.interactionId, 'pending')` con rollback y alerta descriptiva ante fallos.
5. **Prevención de Excepciones y Acceso Universal a Analytics:** En lugar de lanzar errores y mostrar banners rojos molestos cuando se interactúa con mensajes descartados o avanzados:
   - En mensajes descartados, los botones "Analytics" y "Evaluar IA" deben deshabilitarse preventivamente (`disabled`, `opacity-50`) con mensajes informativos en el `title` instruyendo al usuario a restaurar el mensaje primero.
   - En mensajes activos o ya analizados (incluyendo etapas `'en_analisis'`, `'en_redaccion'` y `'en_aprobacion'`), el botón "Analytics" debe navegar de inmediato a `/analytics?interaction={id}` con el estado de la interacción sin arrojar excepciones bloqueantes.
6. **Fidelidad y Coherencia de Métricas en Estado Discord:** Los contadores del panel de Discord deben unificarse bajo definiciones precisas: "Pendientes en Copy" debe contabilizar exclusivamente mensajes ya analizados (`isAnalyzed === true`) que no estén completados (no `'en_redaccion'`, no `'en_aprobacion'`, no `'curated'`) y no descartados. "Incidentes prioritarios" debe computar mensajes evaluados con sentimiento negativo y relevancia $\ge 70$ no descartados, excluyendo inmutablemente bots (`'cloudedtech community bot'`).
7. **Cumplimiento Constitucional e Inmutabilidad Absoluta:** Asegurar que ningún archivo `.py` de la raíz ni de las carpetas `backend/` o `motor-ia/` sea modificado, restringiendo todas las intervenciones exclusivamente a `frontend/src/pages/Messages.tsx`, cumpliendo con las Reglas 1 a 6 de `docs/constitution.md`.

---

## 2. Requerimientos Funcionales (Formato EARS)

### RF-01: Consolidación y Desduplicación del Control de Sincronización de Discord
- **QUÉ:**
  - **CUANDO** el usuario visualice la pestaña de Mensajes (`frontend/src/pages/Messages.tsx`), **EL SISTEMA DEBERÁ** renderizar un único botón principal de sincronización con Discord ubicado exclusivamente dentro del contenedor de estado de Discord ("Estado Discord").
  - **EL SISTEMA DEBERÁ** suprimir la instancia duplicada del botón "📥 Sincronizar Discord" ubicada en el panel de filtrado de mensajes.
  - **CUANDO** el usuario accione el botón de sincronización consolidado, **EL SISTEMA DEBERÁ** mantener el comportamiento interactivo: deshabilitación inmediata durante la solicitud, animación de progreso (spinner), despliegue de retroalimentación contextual del resultado y actualización reactiva de los mensajes en pantalla.
- **POR QUÉ:**
  - Para erradicar la duplicidad de controles idénticos en la misma vista, concentrando la acción de ingesta en el bloque dedicado al estado del canal de Discord y ofreciendo una interfaz despejada y coherente.

### RF-02: Remoción de Controles Inoperativos y Elementos Huérfanos
- **QUÉ:**
  - **EL SISTEMA DEBERÁ** eliminar de la barra de acciones el botón inoperativo "Añadir interacción", el cual carece de funcionalidad backend asociada y permanece permanentemente bloqueado.
  - **EL SISTEMA DEBERÁ** retirar de cada tarjeta de mensaje individual el elemento de selección tipo checkbox (`<input type="checkbox">`) desprovisto de estado reactivo, manejadores de eventos o barra de acciones en lote.
  - **CUANDO** se renderice la lista de mensajes, **EL SISTEMA DEBERÁ** desplegar directamente el avatar/iniciales y el contenido de la interacción sin dejar espacios en blanco o desalineaciones visuales resultantes del retiro del checkbox.
- **POR QUÉ:**
  - Para evitar la presencia de elementos inertes o "muertos" en la interfaz que confunden a los usuarios y degradan la calidad visual y operativa del producto.

### RF-03: Coexistencia de Filtros y Visualización de Mensajes Descartados
- **QUÉ:**
  - **CUANDO** el usuario seleccione la opción "Descartado" en el selector de curaduría (`curationFilter === 'discarded'`), **EL SISTEMA DEBERÁ** permitir la visualización de los mensajes cuyo estado sea descartado (`curationStatus === 'discarded'`).
  - **SI** el filtro de etapa está configurado en "Todas" (`stageFilter === 'all'`), **EL SISTEMA DEBERÁ** listar la totalidad de los mensajes descartados que satisfagan los criterios de búsqueda, canal, sentimiento y fechas.
  - **SI** el filtro de etapa está configurado en una etapa específica (ejemplo: `'pending_eval'`, `'pending_copy'`, `'completos'`), **EL SISTEMA DEBERÁ** aplicar una evaluación combinada (`AND`), mostrando únicamente aquellos mensajes descartados que pertenezcan simultáneamente a la etapa seleccionada.
  - **CUANDO** el selector de curaduría tenga cualquier valor diferente de "Descartado" (por ejemplo `'all'`, `'pending'`, `'curated'`), **EL SISTEMA DEBERÁ** excluir automáticamente de la vista principal todos los mensajes descartados para no saturar la operativa diaria.
  - **CUANDO** `curationFilter === 'discarded'`, **EL SISTEMA DEBERÁ** adaptar el texto del encabezado de la cola de mensajes indicando expresamente: `"Mostrando X mensajes descartados"` (o la variante singular ante un único mensaje).
- **POR QUÉ:**
  - Para restituir la auditabilidad completa de mensajes descartados bajo demanda explícita, asegurando la coexistencia lógica y predecible entre filtros y clarificando el contexto visual de la bandeja.

### RF-04: Acción Bidireccional de Curaduría y Restauración de Mensajes Descartados
- **QUÉ:**
  - **CUANDO** un mensaje no esté descartado (`status !== 'discarded'`), **EL SISTEMA DEBERÁ** renderizar en la cuadrícula de acciones compactas (`grid-cols-2`) el botón de descarte (`X`) junto al botón de copiar contenido.
  - **CUANDO** un mensaje esté descartado (`status === 'discarded'`), **EL SISTEMA DEBERÁ** reemplazar el botón de descarte por un botón de restauración que incorpore:
    - El icono exacto `RotateCcw` de la librería `lucide-react`.
    - Estilo visual diferenciado con clases de color esmeralda: `text-emerald-600 hover:bg-emerald-50 hover:text-emerald-700`.
    - Atributo descriptivo `title` con el texto: `"Restaurar mensaje a pendientes"`.
  - **CUANDO** el usuario pulse el botón de restauración, **EL SISTEMA DEBERÁ** despachar la llamada `updateMessageCuration(message.interactionId, 'pending')`, activar el identificador de guardado en curso (`savingCurationId`), actualizar el estado de forma inmediata y, en caso de fallo o excepción en la API, ejecutar rollback del estado local y desplegar una alerta descriptiva del error.
  - **MIENTRAS** la petición de cambio de estado (descarte o restauración) esté en proceso, **EL SISTEMA DEBERÁ** deshabilitar el botón correspondiente para evitar llamadas duplicadas concurrentes.
- **POR QUÉ:**
  - Para brindar un mecanismo inmediato, robusto y seguro de corrección humana (HITL) ante decisiones erróneas de descarte, con retroalimentación visual clara y manejo resiliente de errores.

### RF-05: Deshabilitación Preventiva y Navegación Resiliente a Analytics
- **QUÉ:**
  - **CUANDO** un mensaje se encuentre en estado descartado (`status === 'discarded'`), **EL SISTEMA DEBERÁ** deshabilitar de forma preventiva los botones de acción para impedir excepciones o banners de error innecesarios:
    - El botón "Analytics" deberá estar deshabilitado (`disabled`, `opacity-50`, cursor no permitido) con el atributo `title`: `"Restaura el mensaje para ver su análisis"`.
    - El botón "Evaluar IA" deberá estar deshabilitado (`disabled`, `opacity-50`, cursor no permitido) con el atributo `title`: `"Restaura el mensaje para evaluarlo con IA"`.
  - **CUANDO** un mensaje NO esté descartado y el usuario pulse el botón "Analytics":
    - **SI** el mensaje se encuentra en etapa inicial cruda (`'ingesta'` o `'en_ingesta'`), **EL SISTEMA DEBERÁ** solicitar la transición a `'en_analisis'` en el backend y navegar hacia `/analytics?interaction={id}` con el estado de la interacción.
    - **SI** el mensaje ya se encuentra evaluado o en etapas subsecuentes (incluyendo `'en_analisis'`, `'en_redaccion'`, `'en_aprobacion'` o `'completado'`), **EL SISTEMA DEBERÁ** omitir transiciones de estado redundantes y navegar directamente hacia `/analytics?interaction={id}` con los datos y métricas analíticas existentes, sin lanzar excepciones ni bloquear la navegación.
- **POR QUÉ:**
  - Para eliminar los bloqueos y alertas de error cuando se desea consultar el análisis de un mensaje avanzado, guiando preventivamente al usuario en mensajes descartados sin provocar fallos en la experiencia.

### RF-06: Unificación de Definiciones de Métricas en el Bloque de Estado Discord
- **QUÉ:**
  - **CUANDO** el sistema calcule el indicador "Pendientes en Copy" en el bloque de estado de Discord, **EL SISTEMA DEBERÁ** contabilizar rigurosamente los mensajes que cumplan simultáneamente las siguientes condiciones:
    1. Estar analizados por el motor de IA (`isAnalyzed === true`).
    2. No estar completados (no encontrarse en `'en_redaccion'`, no encontrarse en `'en_aprobacion'`, y no tener estado de curaduría `'curated'`).
    3. No tener estado de curaduría descartado (`curationStatus !== 'discarded'`).
  - **CUANDO** el sistema calcule el indicador "Incidentes prioritarios" en el bloque de estado de Discord, **EL SISTEMA DEBERÁ** contabilizar rigurosamente los mensajes que cumplan simultáneamente:
    1. Estar debidamente evaluados por la IA (`isAnalyzed === true`).
    2. Tener clasificación de sentimiento negativo (`sentiment === 'negative'`).
    3. Tener un nivel de relevancia crítica o alta (`relevance >= 70`).
    4. No tener estado de curaduría descartado (`curationStatus !== 'discarded'`).
  - **EN TODO MOMENTO**, **EL SISTEMA DEBERÁ** excluir estrictamente los mensajes generados por bots (`'cloudedtech community bot'`) del cálculo de todas las métricas e indicadores.
- **POR QUÉ:**
  - Para corregir la inversión metodológica previa que asignaba mensajes crudos a pendientes de copy y buscaba incidentes críticos en mensajes sin clasificar, asegurando que las cifras presentadas reflejen el estado verídico de la comunidad.

### RF-07: Inmutabilidad Constitucional y Aislamiento de Código
- **QUÉ:**
  - **EN TODO MOMENTO**, **EL SISTEMA DEBERÁ** mantener 100% inalterados los **17 archivos `.py` preexistentes en la raíz del proyecto**, así como todo el código en las carpetas `backend/` y `motor-ia/`.
  - **EL SISTEMA DEBERÁ** concentrar la totalidad de las modificaciones exclusivamente en el componente de interfaz `frontend/src/pages/Messages.tsx`, consumiendo los clientes y contratos de API existentes sin alteraciones en backend.
- **POR QUÉ:**
  - En estricto cumplimiento de las Reglas 2 y 3 de la Constitución (`docs/constitution.md`), salvaguardando la arquitectura modular y la estabilidad de las áreas del equipo.

### RF-08: Verificación Automatizada y Control de Calidad
- **QUÉ:**
  - **CUANDO** se ejecute la suite de pruebas automatizadas del proyecto (`pytest tests/ -v`), **EL SISTEMA DEBERÁ** certificar el 100% de las 77 pruebas preexistentes en verde.
  - **CUANDO** se ejecute la compilación del frontend (`npm run build`), **EL SISTEMA DEBERÁ** compilar de forma estricta con cero errores de TypeScript y empaquetado de producción exitoso.
- **POR QUÉ:**
  - Para dar cumplimiento a la Regla 6 de la Constitución asegurando que no se introducen regresiones funcionales ni de tipado.

---

## 3. Restricciones y Cumplimiento Constitucional

1. **Inviolabilidad del Main (Regla 1):** Todo el desarrollo se efectúa sobre la rama autorizada (`unificacion-beta`), sin modificaciones directas a `main`.
2. **Aislamiento de Interfaz (Regla 2):** Toda la lógica de interacción visual y filtrado reactivo se mantiene contenida en `frontend/src/pages/Messages.tsx`.
3. **Retrocompatibilidad Obligatoria (Regla 3):** Las invocaciones al endpoint `PATCH /api/v1/content-workflow/messages/{id}/curation` preservan el esquema tipado estándar (`status: 'pending' | 'curated' | 'discarded'`).
4. **Seguridad de Secretos (Regla 4):** Cero credenciales, claves o datos sensibles en componentes o repositorios.
5. **Control de Dependencias (Regla 5):** Reutilización estricta de las dependencias ya instaladas en `frontend/package.json` (`lucide-react`, Tailwind CSS).
6. **Diseño Test-First y Verificación (Regla 6):** Validación rigurosa de calidad mediante ejecución integral de tests y build de TypeScript antes de dar por aceptada la especificación.

---

## 4. Criterios de Aceptación Globales

- [ ] Se eliminó la instancia duplicada del botón "📥 Sincronizar Discord" del panel de filtrado, conservándose únicamente en el encabezado de "Estado Discord".
- [ ] Se removió el botón inactivo "Añadir interacción" de la cabecera de filtros.
- [ ] Se removieron los checkboxes huérfanos sin estado en las tarjetas de mensaje, preservando la alineación visual del avatar y texto.
- [ ] Al seleccionar "Descartado" en el filtro de curaduría (`curationFilter === 'discarded'`), se despliegan los mensajes descartados; si `stageFilter === 'all'` se muestran todos, y si `stageFilter` especifica una etapa, se aplica filtro conjunto (AND).
- [ ] Cuando `curationFilter === 'discarded'`, el texto de la cabecera de la cola indica: `"Mostrando X mensajes descartados"`.
- [ ] En cualquier filtro de curaduría distinto de "Descartado", los mensajes descartados permanecen ocultos del listado.
- [ ] En tarjetas de mensajes descartados, se muestra el botón de restauración con icono `RotateCcw`, estilo `text-emerald-600 hover:bg-emerald-50 hover:text-emerald-700`, tooltip `"Restaurar mensaje a pendientes"` y llamada a `updateMessageCuration(id, 'pending')` con rollback y alerta ante errores.
- [ ] En tarjetas de mensajes descartados, los botones "Analytics" y "Evaluar IA" están deshabilitados preventivamente (`opacity-50`, cursor no permitido) con sus respectivos tooltips explicativos indicando que se debe restaurar el mensaje.
- [ ] En mensajes no descartados ya analizados (etapas `'en_analisis'`, `'en_redaccion'`, `'en_aprobacion'`, `'completado'`), el botón "Analytics" navega directamente a `/analytics?interaction={id}` con el estado de la interacción sin arrojar excepciones ni bloquear la navegación.
- [ ] La métrica "Pendientes en Copy" contabiliza únicamente mensajes analizados (`isAnalyzed === true`), no completados (no `'en_redaccion'`, no `'en_aprobacion'`, no `'curated'`) y no descartados.
- [ ] La métrica "Incidentes prioritarios" contabiliza únicamente mensajes analizados (`isAnalyzed === true`) con sentimiento negativo, relevancia >= 70 y no descartados.
- [ ] Todas las métricas excluyen permanentemente los mensajes de bots (`'cloudedtech community bot'`).
- [ ] Los 17 archivos `.py` de la raíz, `backend/` y `motor-ia/` permanecen 100% inalterados.
- [ ] El 100% de los tests del backend (`pytest tests/ -v`, 77 pruebas) se mantienen en verde.
- [ ] La compilación del frontend (`npm run build`) culmina con 0 errores de TypeScript.
