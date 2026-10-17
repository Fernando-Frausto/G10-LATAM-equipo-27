# Especificación 009: Auditoría y Consistencia Funcional de la Pestaña de Dashboard

## 1. Contexto y Propósito

### ¿Qué se busca lograr?
Garantizar la consistencia operativa, integridad visual, resiliencia defensiva y funcionalidad al 100% de todos los controles de la pestaña de Dashboard (`frontend/src/pages/Dashboard.tsx`), eliminando textos provisionales o placeholders inactivos, integrando el carrusel interactivo vivo de Historias Destacadas (`<FeaturedStories key={analyticsVersion} />`), sincronizando integralmente la acción del botón "Actualizar datos" sobre todos los componentes de la pantalla, corrigiendo la anomalía en la métrica de Audiencia Total (`total_audience`) mediante un fallback estricto con blindaje antibot para reflejar los 10 miembros humanos únicos reales en lugar de reportar 0, asegurando coalescencia nula defensiva y formateo con separador de miles en las 6 tarjetas de KPIs, y blindando la solución mediante una nueva prueba unitaria/integración bajo enfoque Test-First (TDD), todo bajo estricto cumplimiento constitucional e inmutabilidad del código preexistente.

### ¿Por qué es necesario?
1. **Eliminación de Textos Provisionales y Secciones Inertes:** En `Dashboard.tsx` (líneas 200-208) persiste un contenedor estático con el texto `"Esta sección se conectará con los mensajes destacados del Motor IA durante la integración de Ingesta Discord."`. Esta sección debe ser sustituida por el componente interactivo `<FeaturedStories />` de `frontend/src/components/FeaturedStories.tsx`, el cual consume `getCommunityLiveSummary()` de forma reactiva y asíncrona, con carrusel funcional (botones Anterior, Siguiente y dots con deshabilitación preventiva si `stories.length <= 1`), métricas de relevancia y sentimiento, citas reales de autores y enlaces funcionales hacia `/messages` y `/approvals`.
2. **Sincronización Reactiva Desacoplada del Botón "Actualizar datos":** El botón principal de actualización en `Dashboard.tsx` recarga las métricas del dashboard e incrementa el contador reactivo `analyticsVersion` para refrescar los cuatro gráficos analíticos (`SentimentChart`, `TopicsChart`, `SentimentEvolution`, `AudienceHeatmap`). Al dotar a `<FeaturedStories />` de la propiedad `key={analyticsVersion}`, el componente se desmonta y remonta automáticamente ejecutando su propio ciclo de vida (`useEffect`) de forma asíncrona e independiente, logrando que una sola pulsación actualice todos los paneles sin demorar la resolución del botón "Actualizar datos".
3. **Fidelidad, Precisión y Blindaje Antibot en Audiencia Total:** En `/api/community/dashboard`, la métrica `total_audience` reportaba erróneamente 0 porque en las interacciones de Supabase/SQLite el identificador del autor reside en la columna `autor` mientras `author_id` viene nulo o vacío. En `puente_motor_ia.py` se debe consolidar el fallback `str(raw.get("author_id") or raw.get("autor") or "")` tanto en la sincronización hacia SQLite como al servir datos en `listar_interacciones_puente`, aplicando el filtro antibot estricto para ignorar bots y webhooks (`cloudedtech community bot`, `Spidey Boy#0000`, terminados en `#0000` o `tipo in ("bot", "webhook")`), permitiendo que `servicio_dashboard.autores_unicos` compute con exactitud la audiencia humana real de 10 miembros únicos.
4. **Coherencia, Formateo Defensivo y Null Safety en las 6 Tarjetas de KPIs:** Para evitar pantallas en blanco o caídas de renderizado ante respuestas inesperadas del backend, se exige coalescencia nula defensiva (`optional chaining ?.toLocaleString("es-CO") ?? "0"`) en todas las tarjetas de KPIs. Asimismo, se debe tratar explícitamente la variación neutra: si el cambio porcentual o de puntos es exactamente `0.0`, se desplegará `"0% esta semana"` o `"0 puntos esta semana"`, reservando `"Sin comparación"` exclusivamente para valores `null`.
5. **Diseño Test-First (TDD) y Cumplimiento de la Regla 6:** Siguiendo la Constitución, debe crearse una prueba automatizada en `tests/test_unificacion_motor_ia.py` que verifique que `/api/community/dashboard` retorne `total_audience` igual a 10 y valide el fallback de `author_id` ante valores nulos o vacíos, elevando la suite a 78 pruebas en verde.
6. **Inmutabilidad Constitucional Absoluta:** Blindaje estricto de los **17 archivos `.py` preexistentes en la raíz del proyecto**, así como todo el código en las carpetas `backend/` y `motor-ia/`. Las intervenciones técnicas quedan rigurosamente delimitadas a `puente_motor_ia.py`, `frontend/src/pages/Dashboard.tsx`, `frontend/src/components/FeaturedStories.tsx` y `tests/test_unificacion_motor_ia.py`.

---

## 2. Requerimientos Funcionales (Formato EARS)

### RF-01: Reemplazo del Placeholder Estático por Carrusel Vivo y Resiliente de Historias Destacadas
- **QUÉ:**
  - **CUANDO** el usuario visualice la pestaña de Dashboard (`frontend/src/pages/Dashboard.tsx`), **EL SISTEMA DEBERÁ** renderizar el componente interactivo de Historias Destacadas (`<FeaturedStories key={analyticsVersion} />`) en la posición donde residía el contenedor provisional estático.
  - **EL SISTEMA DEBERÁ** suprimir definitivamente el bloque estático con el texto provisional `"Esta sección se conectará con los mensajes destacados del Motor IA durante la integración de Ingesta Discord."`.
  - **CUANDO** el carrusel de Historias Destacadas se monte o remonte por cambio en `analyticsVersion`, **EL SISTEMA DEBERÁ** disparar su propio `useEffect` invocando de forma asíncrona e independiente `getCommunityLiveSummary()`, sin bloquear ni demorar la resolución del botón "Actualizar datos".
  - **SI** la respuesta del resumen contiene historias válidas (`highlights.length > 0`), **EL SISTEMA DEBERÁ** desplegarlas con sus citas textuales entrecomilladas, autor, canal, sentimiento, relevancia y distintivo temático.
  - **SI** la respuesta no contiene historias destacadas (`highlights: []`) o la API no responde, **EL SISTEMA DEBERÁ** activar automáticamente el fallback seguro predefinido en el componente sin arrojar errores visuales.
  - **CUANDO** la cantidad de historias sea menor o igual a una (`stories.length <= 1`), **EL SISTEMA DEBERÁ** deshabilitar preventivamente los botones de navegación anterior y siguiente (`disabled`, `opacity-50`, cursor no permitido).
  - **CUANDO** el usuario accione el botón "Ver mensaje" en la historia destacada, **EL SISTEMA DEBERÁ** navegar hacia `/messages` transmitiendo el contexto de la interacción correspondiente.
  - **CUANDO** el usuario accione el botón "Generar publicación", **EL SISTEMA DEBERÁ** navegar hacia `/approvals` para iniciar el flujo de generación o aprobación.
- **POR QUÉ:**
  - Para erradicar textos provisionales y dotar a la interfaz de historias dinámicas enriquecidas con enlaces funcionales a las demás vistas operativas y alta tolerancia a fallos.

### RF-02: Sincronización Integral y Reactiva del Botón "Actualizar datos"
- **QUÉ:**
  - **CUANDO** el usuario accione el botón "Actualizar datos" en el encabezado del Dashboard, **EL SISTEMA DEBERÁ** activar el estado de refresco visual (`refreshing = true`), desplegar la animación de rotación (`animate-spin`) en el icono `RefreshCw`, mostrar el texto `"Actualizando..."` y deshabilitar el botón para evitar pulsaciones duplicadas concurrentes.
  - **MIENTRAS** el botón esté en estado de actualización, **EL SISTEMA DEBERÁ** solicitar en paralelo los endpoints `/api/community/dashboard` y `/api/community/analytics`.
  - **CUANDO** dichas peticiones concluyan con éxito, **EL SISTEMA DEBERÁ** actualizar el estado `dashboardData` e incrementar el contador reactivo `analyticsVersion`.
  - **CUANDO** `analyticsVersion` se incremente, **EL SISTEMA DEBERÁ** desencadenar el refresco simultáneo y coordinado de:
    1. Las 6 tarjetas superiores de KPIs.
    2. El carrusel de Historias Destacadas (`<FeaturedStories key={analyticsVersion} />`) mediante remontado limpio.
    3. El gráfico de sentimiento comunitario (`<SentimentChart key={analyticsVersion} />`).
    4. El gráfico de distribución de temas (`<TopicsChart key={analyticsVersion} />`).
    5. El gráfico de evolución temporal del sentimiento (`<SentimentEvolution key={analyticsVersion} />`).
    6. El mapa de calor de actividad comunitaria (`<AudienceHeatmap key={analyticsVersion} />`).
  - **SI** se produce un error en la solicitud de actualización, **EL SISTEMA DEBERÁ** finalizar el estado de refresco, mantener visibles los últimos datos válidos cargados y presentar un mensaje de alerta accesible (`role="alert"`).
- **POR QUÉ:**
  - Para asegurar una experiencia de usuario perfectamente sincronizada donde una sola pulsación renueve la totalidad de los paneles del dashboard de manera ágil y desacoplada.

### RF-03: Reconciliación de Audiencia Total (`total_audience`) con Blindaje Antibot
- **QUÉ:**
  - **CUANDO** `puente_motor_ia.py` sincronice registros hacia SQLite (`_sincronizar_supabase_a_sqlite`) o consulte interacciones para el servicio de dashboard (`listar_interacciones_puente`), **EL SISTEMA DEBERÁ** aplicar el fallback estricto `str(raw.get("author_id") or raw.get("autor") or "")` garantizando que el identificador del autor nunca quede nulo o vacío ante la presencia del campo `autor`.
  - **EN TODO MOMENTO**, **EL SISTEMA DEBERÁ** ejecutar un filtro antibot riguroso que excluya permanentemente cuentas de bot y webhooks (incluyendo `'cloudedtech community bot'`, `'spidey boy#0000'`, usuarios terminados en `'#0000'` o tipos `'bot'`/`'webhook'`).
  - **CUANDO** el cálculo de autores únicos (`servicio_dashboard.autores_unicos`) sea ejecutado para responder a `/api/community/dashboard`, **EL SISTEMA DEBERÁ** retornar en `total_audience` el conteo verídico de los 10 miembros humanos únicos de la comunidad en lugar de reportar 0.
- **POR QUÉ:**
  - Para erradicar la discrepancia de nombres de columnas que producía una métrica nula ficticia, reflejando de forma transparente la participación real de la comunidad sin contaminación por bots.

### RF-04: Coherencia, Formateo Defensivo y Null Safety en las 6 Tarjetas de KPIs
- **QUÉ:**
  - **CUANDO** se renderice la cuadrícula de KPIs en el Dashboard (`frontend/src/pages/Dashboard.tsx`), **EL SISTEMA DEBERÁ** aplicar coalescencia nula defensiva (`optional chaining ?.toLocaleString("es-CO") ?? "0"`) para blindar el componente contra valores nulos o indefinidos y prevenir caídas de interfaz (pantallas blancas):
    1. **Mensajes procesados:** Valor formateado con separador de miles (`dashboardData.messages_processed?.toLocaleString('es-CO') ?? '0'`) y variación semanal.
    2. **Total de audiencia:** Valor verídico de audiencia formateado (`dashboardData.total_audience?.toLocaleString('es-CO') ?? '0'`) y variación semanal.
    3. **Sentimiento positivo:** Valor expresado como porcentaje (`dashboardData.positive_sentiment != null ? `${dashboardData.positive_sentiment}%` : '0%'`) y variación en puntos.
    4. **Temas detectados:** Conteo formateado (`dashboardData.topics_detected?.toLocaleString('es-CO') ?? '0'`) y nuevos temas detectados.
    5. **Contenidos generados:** Conteo formateado (`dashboardData.content_generated?.toLocaleString('es-CO') ?? '0'`) y descripción `"Esta semana"`.
    6. **Pendientes:** Conteo formateado (`dashboardData.pending_approvals?.toLocaleString('es-CO') ?? '0'`) y descripción `"Requieren aprobación"`.
  - **CUANDO** se evalúe la variación porcentual o de puntos en las tarjetas:
    - **SI** el valor de variación es estrictamente `null` o indefinido, **EL SISTEMA DEBERÁ** mostrar el texto `"Sin comparación"`.
    - **SI** el valor de variación es exactamente `0` o `0.0`, **EL SISTEMA DEBERÁ** mostrar `"0% esta semana"` (en mensajes y audiencia) o `"0 puntos esta semana"` (en sentimiento).
    - **SI** el valor de variación es mayor a `0`, **EL SISTEMA DEBERÁ** anteponer el prefijo `"+"` (ej. `"+5% esta semana"` o `"+3 puntos esta semana"`).
    - **SI** el valor de variación es menor a `0`, **EL SISTEMA DEBERÁ** desplegar la variación negativa (ej. `"-5% esta semana"` o `"-3 puntos esta semana"`).
- **POR QUÉ:**
  - Para garantizar una presentación de métricas robusta a prueba de fallos de datos, ofreciendo una lectura ejecutiva precisa tanto en variaciones positivas, negativas, neutras o sin histórico.

### RF-05: Inmutabilidad Arquitectónica y Cumplimiento Constitucional
- **QUÉ:**
  - **EN TODO MOMENTO**, **EL SISTEMA DEBERÁ** mantener estrictamente inalterados los **17 archivos `.py` preexistentes en la raíz del proyecto**, así como todo el código fuente en las carpetas `backend/` y `motor-ia/`.
  - **EL SISTEMA DEBERÁ** concentrar las modificaciones técnicas exclusivamente en:
    1. `puente_motor_ia.py` (adaptador de interoperabilidad y unificación no invasivo).
    2. `frontend/src/pages/Dashboard.tsx` (vista principal de métricas y KPIs).
    3. `frontend/src/components/FeaturedStories.tsx` (componente interactivo de historias).
    4. `tests/test_unificacion_motor_ia.py` (suite de pruebas automatizadas).
- **POR QUÉ:**
  - En estricto cumplimiento de las Reglas 2 y 3 de la Constitución (`docs/constitution.md`) y las pautas operativas de `AGENTS.md`.

### RF-06: Verificación Automatizada y Diseño Test-First (TDD)
- **QUÉ:**
  - **CUANDO** se apliquen los cambios en el backend, **EL SISTEMA DEBERÁ** incorporar previamente una prueba automatizada en `tests/test_unificacion_motor_ia.py` que certifique:
    1. Que la llamada `GET /api/community/dashboard` reporte un valor de `total_audience` estrictamente superior a 0, verificando la presencia de los 10 miembros humanos únicos reales.
    2. Que el mecanismo de fallback de `author_id` hacia `autor` en `puente_motor_ia.py` opere de manera efectiva ante registros donde `author_id` venga nulo o vacío.
  - **CUANDO** se ejecute la suite completa de pruebas del backend (`pytest tests/ -v`), **EL SISTEMA DEBERÁ** certificar el 100% de las pruebas en verde (78/78 tests pasando satisfactoriamente).
  - **CUANDO** se ejecute la compilación del cliente web (`npm run build` en el directorio `frontend/`), **EL SISTEMA DEBERÁ** compilar de forma estricta con cero errores de TypeScript y empaquetado de producción exitoso.
- **POR QUÉ:**
  - Para cumplir con la Regla 6 de la Constitución asegurando que la corrección de datos esté respaldada por pruebas de regresión automáticas y que el frontend conserve plena solidez de tipos.

---

## 3. Restricciones y Cumplimiento Constitucional

1. **Inviolabilidad del Main (Regla 1):** Todo el trabajo se efectúa sobre la rama de desarrollo autorizada (`unificacion-beta`), sin push directo a `main`.
2. **Aislamiento de Interfaz (Regla 2):** Toda la lógica de interacción visual, navegación y refresco reactivo permanece encapsulada en el frontend (`frontend/src/pages/Dashboard.tsx` y `frontend/src/components/FeaturedStories.tsx`).
3. **Retrocompatibilidad Obligatoria (Regla 3):** Los contratos de respuesta de `/api/community/dashboard` y `/api/community/analytics` preservan su esquema JSON intacto, respetando la estructura esperada por la interfaz y clientes externos.
4. **Seguridad de Secretos (Regla 4):** Cero tokens, credenciales o datos sensibles guardados en código duro en frontend o backend.
5. **Control de Dependencias (Regla 5):** No se agregan nuevas librerías; se emplean exclusivamente las dependencias existentes (`lucide-react`, `react-router-dom`, Tailwind CSS).
6. **Diseño Test-First y Verificación Integral (Regla 6):** Creación previa de la prueba unitaria para validar la métrica de audiencia y verificación del 100% de las 78 pruebas en pytest y compilación TypeScript sin advertencias bloqueantes.

---

## 4. Criterios de Aceptación Globales

- [ ] Se eliminó en `Dashboard.tsx` el contenedor estático provisional con el texto `"Esta sección se conectará con los mensajes destacados del Motor IA durante la integración de Ingesta Discord."`.
- [ ] Se integró el componente interactivo `<FeaturedStories key={analyticsVersion} />` en `Dashboard.tsx`, ejecutando su propio `useEffect` de forma asíncrona e independiente sin retrasar el botón "Actualizar datos".
- [ ] Si la API de historias no retorna destacados o falla, `FeaturedStories` utiliza su fallback seguro predefinido sin arrojar errores visuales.
- [ ] En `FeaturedStories`, los botones de navegación anterior y siguiente se deshabilitan preventivamente si `stories.length <= 1`.
- [ ] En `FeaturedStories`, el botón "Ver mensaje" navega a `/messages` pasando la interacción, y "Generar publicación" navega a `/approvals`.
- [ ] Al pulsar "Actualizar datos", se activa la animación de giro en `RefreshCw`, el botón se deshabilita con `"Actualizando..."` y se refrescan sincronizadamente las 6 tarjetas de KPIs, `<FeaturedStories />` y los 4 gráficos analíticos al incrementarse `analyticsVersion`.
- [ ] Las 6 tarjetas de KPIs aplican coalescencia nula defensiva (`optional chaining ?.toLocaleString("es-CO") ?? "0"`), evitando caídas de React o pantallas blancas.
- [ ] Si la variación porcentual o de puntos en las tarjetas de KPIs es exactamente 0.0, se despliega `"0% esta semana"` o `"0 puntos esta semana"`; si es `null`, se muestra `"Sin comparación"`.
- [ ] En `puente_motor_ia.py`, el fallback `str(raw.get("author_id") or raw.get("autor") or "")` opera en la sincronización SQLite y en `listar_interacciones_puente`, con exclusión estricta de bots.
- [ ] La métrica de Audiencia Total (`total_audience`) en `/api/community/dashboard` reporta exactamente los 10 miembros humanos únicos reales.
- [ ] Se añadió en `tests/test_unificacion_motor_ia.py` la prueba unitaria/integración que valida `total_audience == 10` y el fallback de `author_id`.
- [ ] Los 17 archivos `.py` de la raíz, `backend/` y `motor-ia/` permanecen 100% inalterados.
- [ ] La suite de pruebas de backend (`pytest tests/ -v`) supera el 100% de las 78 pruebas en verde.
- [ ] La compilación del frontend (`npm run build`) culmina con 0 errores de TypeScript.
