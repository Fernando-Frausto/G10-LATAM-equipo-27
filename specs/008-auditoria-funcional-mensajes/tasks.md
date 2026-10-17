# Tareas de Implementación: Spec 008
## Auditoría y Consistencia Funcional de la Pestaña de Mensajes

---

### [x] Tarea 1: Limpieza visual y desduplicación de controles
- **RF Asociado:** RF-01, RF-02
- **Estimación:** ~20 minutos
- **Archivos a modificar:** `frontend/src/pages/Messages.tsx`
- **Descripción:**
  1. Suprimir la instancia duplicada del botón "📥 Sincronizar Discord" ubicada en el panel de filtrado de mensajes (alrededor de la línea 1108), conservando como punto de acceso único el botón con spinner ubicado en el bloque de "Estado Discord" (línea 880).
  2. Remover de la barra de acciones el botón deshabilitado "Añadir interacción" (alrededor de la línea 1122), eliminando controles inoperativos.
  3. Eliminar de cada tarjeta de mensaje el elemento checkbox huérfano (`<input type="checkbox">`, línea 1373), garantizando que el avatar/iniciales y el contenido textual queden alineados de forma limpia y equilibrada.
- [x] **Hecho cuando:**
  En la interfaz de Mensajes ya no aparezca el botón duplicado de sincronización ni el botón muerto "Añadir interacción", y las tarjetas de mensaje no contengan casillas de selección desconectadas, manteniendo la estética limpia y responsiva.

---

### [x] Tarea 2: Corrección del filtro de descartados y cabecera de cola adaptativa
- **RF Asociado:** RF-03
- **Estimación:** ~20 minutos
- **Archivos a modificar:** `frontend/src/pages/Messages.tsx`
- **Descripción:**
  1. Modificar la condición de filtrado en `filteredMessages`:
     - Cuando `curationFilter === 'discarded'`, permitir el listado de los mensajes cuyo estado de curaduría sea `'discarded'`.
     - Cuando `curationFilter !== 'discarded'`, excluir de la visualización los mensajes con estado `'discarded'`.
  2. Implementar la coexistencia lógica con `stageFilter`:
     - Si `curationFilter === 'discarded'` y `stageFilter === 'all'`, mostrar todos los mensajes descartados.
     - Si `stageFilter` define una etapa específica (ej: `'pending_eval'`, `'pending_copy'`, `'completos'`), aplicar filtro conjunto (`AND`) para permitir auditar descartados por cada fase editorial.
  3. Actualizar la cabecera dinámica de la cola de mensajes:
     - Cuando `curationFilter === 'discarded'`, mostrar el texto contextual adaptativo: `"Mostrando X mensajes descartados"` (o singular si corresponde a 1).
- [x] **Hecho cuando:**
  Al seleccionar "Estado del mensaje: Descartado" en el filtro de curaduría, se visualicen en pantalla todos los mensajes descartados que coincidan con los filtros activos y la cabecera informe claramente "Mostrando X mensajes descartados", permaneciendo ocultos en cualquier otro filtro de curaduría.

---

### [x] Tarea 3: Acción de restauración bidireccional y deshabilitación preventiva en descartados
- **RF Asociado:** RF-04, RF-05
- **Estimación:** ~20 minutos
- **Archivos a modificar:** `frontend/src/pages/Messages.tsx`
- **Descripción:**
  1. Importar el icono `RotateCcw` desde `lucide-react`.
  2. En el panel lateral de acciones de cada tarjeta de mensaje (cuadrícula `grid-cols-2`), implementar el renderizado condicional:
     - Si `status !== 'discarded'`: mostrar el botón de descarte (`<X size={15} />`) que llama a `markCuration(message, 'discarded')`.
     - Si `status === 'discarded'`: reemplazarlo por el botón de restauración con icono `<RotateCcw size={15} />`, estilo `text-emerald-600 hover:bg-emerald-50 hover:text-emerald-700`, tooltip `"Restaurar mensaje a pendientes"` y llamada a `markCuration(message, 'pending')`.
  3. Blindar la función `markCuration` para gestionar el estado de carga `savingCurationId`, asegurar rollback del estado local ante fallos de la API y desplegar la causa del error en `curationError`.
  4. Aplicar deshabilitación preventiva en tarjetas descartadas:
     - Botón "Analytics": `disabled`, `opacity-50`, `cursor-not-allowed` y `title="Restaura el mensaje para ver su análisis"`.
     - Botón "Evaluar IA": `disabled`, `opacity-50`, `cursor-not-allowed` y `title="Restaura el mensaje para evaluarlo con IA"`.
- [x] **Hecho cuando:**
  Los mensajes descartados presenten el botón esmeralda con icono `RotateCcw` que restaura el mensaje a pendiente tanto en frontend como en backend, y los botones "Analytics" y "Evaluar IA" aparezcan preventivamente deshabilitados con sus tooltips explicativos sin emitir errores de ejecución.

---

### [x] Tarea 4: Navegación resiliente a Analytics y unificación de métricas de Estado Discord
- **RF Asociado:** RF-05, RF-06
- **Estimación:** ~20 minutos
- **Archivos a modificar:** `frontend/src/pages/Messages.tsx`
- **Descripción:**
  1. Modificar `handleAnalyze`:
     - Si el mensaje se encuentra en etapas `'en_analisis'`, `'en_redaccion'`, `'en_aprobacion'` o `'completado'`, omitir la llamada de transición de etapa y ejecutar directamente la navegación `navigate('/analytics?interaction=' + message.interactionId, { state: ... })`.
     - Si el mensaje está en `'ingesta'` o `'en_ingesta'`, mantener la llamada a `updateMessageWorkflow(message.interactionId, 'en_analisis')` antes de navegar.
     - Si el mensaje estuviera descartado, salir de forma defensiva sin levantar alertas en rojo.
  2. Reconciliar el cálculo de las métricas en el bloque "Estado Discord":
     - Métrica "Pendientes en Copy": filtrar `messageItems` contabilizando los que cumplan: `isAnalyzed === true`, no completados (`workflowStage !== 'en_redaccion'`, `workflowStage !== 'en_aprobacion'`, `curationStatus !== 'curated'`), no descartados y no emitidos por `'cloudedtech community bot'`.
     - Métrica "Incidentes prioritarios": filtrar `messageItems` contabilizando los que cumplan: `isAnalyzed === true`, `sentiment === 'negative'`, `relevance >= 70`, no descartados y no emitidos por bots.
     - Asegurar la exclusión inmutable de mensajes de bots en todos los cómputos.
- [x] **Hecho cuando:**
  Al pulsar "Analytics" en un mensaje que ya ha sido evaluado o está en redacción/aprobación se navegue fluidamente a la vista analítica sin errores bloqueantes, y las métricas de "Pendientes en Copy" e "Incidentes prioritarios" coincidan rigurosamente con los datos procesados en la plataforma.

---

### [x] Tarea 5: Verificación global de regresión, tipado e inmutabilidad
- **RF Asociado:** RF-07, RF-08
- **Estimación:** ~20 minutos
- **Archivos a modificar:** Ninguno (validación y control de calidad)
- **Descripción:**
  1. Ejecutar la suite de pruebas automatizadas del backend con `pytest tests/ -v` certificando el paso del 100% de las 77 pruebas en verde.
  2. Ejecutar la compilación del frontend con `npm run build` en `frontend/` verificando código de salida 0 sin fallos de TypeScript ni dependencias rotas.
  3. Ejecutar `git status` y verificar que los 17 archivos preexistentes en la raíz, la carpeta `backend/` y `motor-ia/` no hayan sufrido modificaciones accidentales.
- [x] **Hecho cuando:**
  Las 77 pruebas de backend pasen en verde, la compilación de frontend culmine con 0 errores y se verifique la total inmutabilidad de los módulos protegidos por la Constitución.
