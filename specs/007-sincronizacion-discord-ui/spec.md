# Especificación 007: Sincronización de Discord desde la UI y Flujo Integral de Extremo a Extremo

## 1. Contexto y Propósito

### ¿Qué se busca lograr?
Proporcionar a los usuarios y administradores la capacidad de sincronizar y jalar nuevos mensajes desde los canales autorizados de Discord directamente desde la interfaz web de React (`frontend/`), sin necesidad de ejecutar comandos manuales en la terminal (`bot_lote.py`).

Asimismo, se busca habilitar de forma funcional la recuperación selectiva de mensajes históricos en el modal de recuperación (`RecoverDiscordMessagesModal.tsx`), asegurando que todo el ciclo operativo de la plataforma encaje de punta a punta:
1. **Ingesta:** Extracción manual o bajo demanda desde Discord hacia la base de datos (Supabase e SQLite local como degradación resiliente) con deduplicación criptográfica SHA-256.
2. **Evaluación IA:** Análisis automático por lotes acotado por fechas (`desde` / `hasta`) utilizando cualquiera de los 3 cerebros configurados (`Groq Llama 3.3`, `Google Gemma 4`, `Google Gemini Flash Lite`), con contador dinámico reactivo en la UI (paridad con Streamlit) y filtrado blindado de mensajes pendientes contra `lotes_ia_kpis` en Supabase e SQLite local.
3. **Curaduría Humana (HITL):** Aprobación, descarte y redacción de copys optimizados (`copy_final`) por parte del equipo de Copywriting (Enoc) preservando la soberanía de las decisiones humanas.
4. **Reportes y Almacenamiento OCI:** Generación de resúmenes semanales consolidados y respaldo en OCI Object Storage (módulos de Tania).
5. **Métricas en Vivo y Exportación:** Visualización en tiempo real de actividades, segmentos de comunidad, historias destacadas y descarga estructurada en JSON (`/api/v1/export/community-data`).

Todo el procesamiento del backend se implementará exclusivamente en `puente_motor_ia.py`, preservando **completamente intactos los 17 archivos `.py` preexistentes en la raíz del proyecto**, así como los módulos en `motor-ia/` y `backend/`.

### ¿Por qué es necesario?
1. **Operación Autónoma desde la Web:** Actualmente, la ingesta de mensajes de Discord depende de la ejecución en consola del script `bot_lote.py`. En la vista de mensajes de React (`frontend/src/pages/Messages.tsx`) existe un indicador de conexión pero carece de un botón interactivo que desencadene la sincronización hacia la base de datos.
2. **Habilitación de Recuperación Histórica:** El componente `RecoverDiscordMessagesModal.tsx` permite previsualizar e inspeccionar mensajes pasados de Discord pero su botón de acción ("Recuperar seleccionados") se encuentra deshabilitado con un aviso de funcionalidad pendiente, impidiendo rescatar conversaciones específicas no importadas.
3. **Consistencia y Fluidez End-to-End:** Es indispensable garantizar que cada mensaje recién importado o recuperado ingrese de inmediato al flujo de datos (`etapa = 'ingesta'`, `estado_revision = 'pendiente'`), sea evaluable por los 3 cerebros de IA y fluya de manera natural hacia la curaduría de Enoc y los reportes de Tania.
4. **Prevención de Bloqueos y Condiciones de Carrera:** La integración de `discord.py` dentro de un servidor web asíncrono (FastAPI) exige el uso de un cliente efímero en el bucle de eventos (`client.start()` y `client.close()`) y un control estricto de concurrencia (`asyncio.Lock`) para evitar saturación, bloqueos del event loop o múltiples sincronizaciones simultáneas.
5. **Apego a la Constitución del Proyecto:** Se mantiene la inviolabilidad de `main` (Regla 1), el desacoplamiento de interfaces (Regla 2), la retrocompatibilidad con Supabase y SQLite (Regla 3), la protección de credenciales (Regla 4) y la verificación rigurosa mediante pruebas automatizadas Test-First (Regla 6).
6. **Paridad Reactiva con Streamlit y Blindaje de Evaluación:** En la versión original de Streamlit (`app.py`), la selección de fechas calcula inmediatamente la cantidad de mensajes disponibles e inhabilita la acción si el conteo es cero. En la aplicación React (`Messages.tsx`), se requiere replicar dicho contador reactivo en tiempo real ('📊 X mensajes disponibles para evaluar (Y pendientes)') y blindar la casilla 'Solo pendientes de evaluar' para que tanto la UI como el backend filtren contra los IDs ya evaluados en `lotes_ia_kpis` tanto de Supabase como de SQLite local, impidiendo evaluaciones redundantes o botones habilitados sin mensajes.

---

## 2. Requerimientos Funcionales (Formato EARS)

### RF-01: Endpoint Backend de Sincronización Asíncrona de Discord (`POST /api/v1/discord/sync`)
- **QUÉ:**
  - **CUANDO** el cliente HTTP realice una petición `POST` al endpoint `/api/v1/discord/sync` en `puente_motor_ia.py` con una carga opcional conteniendo el parámetro `limite_por_canal` (entero opcional, por defecto `100`), **EL SISTEMA DEBERÁ** iniciar la sesión de extracción ejecutando un cliente efímero de Discord (`discord.Client`) directamente sobre el bucle de eventos existente de FastAPI con `client.start()` y `client.close()`, con un tiempo límite de espera (timeout) de seguridad no mayor a 30 segundos, asegurando no bloquear el event loop y reutilizando las rutinas de lectura y saneamiento de `armar_json_bot_python.py` y `procesamiento.py`, sin modificar ni invocar el script standalone `bot_lote.py`.
  - **MIENTRAS** exista una sincronización activa en progreso, **EL SISTEMA DEBERÁ** rechazar cualquier nueva petición concurrente a `/api/v1/discord/sync` mediante un cerrojo asíncrono (`asyncio.Lock`), retornando de inmediato un código HTTP `409 Conflict` con el cuerpo `{"exito": false, "mensaje": "Sincronización en curso", "detail": "Sincronización en curso"}`.
  - **CUANDO** se procesen los mensajes recolectados de los canales de texto autorizados, **EL SISTEMA DEBERÁ** validar el contenido, limpiar el texto, calcular los hashes criptográficos SHA-256 e insertar en la base de datos únicamente las interacciones que no hayan sido registradas previamente, descartando mensajes vacíos, bots y webhooks.
  - **CUANDO** se persistan los mensajes, **EL SISTEMA DEBERÁ** aplicar un mecanismo de degradación dual resiliente: insertar en Supabase (`interacciones`) y, en caso de desconexión o fallo en la base remota, persistir de forma transparente en SQLite local (`communitylab.db`), garantizando cero pérdida de datos.
  - **CUANDO** la sincronización finalice con éxito e incorpore nuevos mensajes, **EL SISTEMA DEBERÁ** responder con un código HTTP `200` y la siguiente estructura JSON:
    - `exito`: valor booleano `true`.
    - `total_recibidas`: número entero de mensajes leídos desde Discord.
    - `guardadas_nuevas`: número entero de mensajes nuevos insertados efectivamente (> 0).
    - `repetidas_omitidas`: número entero de mensajes descartados por hash duplicado.
    - `vacias_omitidas`: número entero de mensajes descartados por falta de texto.
    - `periodo_referencia`: identificador del periodo asignado (ej. `"Semana_XX"`).
    - `mensaje`: texto descriptivo del resultado (ej. `"Sincronización exitosa: X mensajes nuevos guardados"`).
  - **CUANDO** la sincronización finalice exitosamente pero todos los mensajes extraídos ya existan en la base de datos (cero mensajes nuevos), **EL SISTEMA DEBERÁ** responder con HTTP `200`, `guardadas_nuevas: 0` y el mensaje `"Todos los mensajes están al día"`.
  - **CUANDO** no se localicen canales de texto autorizados o accesibles con el bot, **EL SISTEMA DEBERÁ** responder con HTTP `200`, `total_recibidas: 0`, `guardadas_nuevas: 0`, `repetidas_omitidas: 0` y el mensaje `"No se encontraron canales de texto autorizados o accesibles"`.
  - **SI** el token de Discord (`DISCORD_BOT_TOKEN` o `DISCORD_TOKEN`) no está configurado en las variables de entorno o si falla el inicio de sesión con Discord (`discord.errors.LoginFailure`), **EL SISTEMA DEBERÁ** retornar un código HTTP `502 Bad Gateway` con el cuerpo `{"exito": false, "mensaje": "Fallo de autenticación con Discord: token ausente o inválido"}` de forma controlada y sin provocar la caída del servidor.
- **POR QUÉ:**
  - Para permitir la ingesta programática y bajo demanda de mensajes de Discord de forma no bloqueante, idempotente, segura ante concurrencia y con resiliencia ante contingencias de red o de credenciales.

### RF-02: Control de Sincronización, Concurrencia, Contador Reactivo y Blindaje de Evaluación en la UI (`frontend/src/pages/Messages.tsx`)
- **QUÉ:**
  - **Sincronización de Discord:**
    - **CUANDO** el usuario visualice la vista de Mensajes (`frontend/src/pages/Messages.tsx`), **EL SISTEMA DEBERÁ** renderizar un botón interactivo y visible ("Sincronizar Discord" / "📥 Extraer mensajes de Discord") en la barra de acciones superior.
    - **CUANDO** el usuario haga clic en el botón de sincronización, **EL SISTEMA DEBERÁ** deshabilitar inmediatamente el botón, mostrar un indicador visual de carga (spinner o animación de progreso) para prevenir múltiples clics (race conditions en UI), y despachar la petición `POST /api/v1/discord/sync`.
    - **CUANDO** la petición concluya exitosamente (HTTP `200`), **EL SISTEMA DEBERÁ** reestablecer el botón, ocultar el indicador de carga, mostrar un mensaje o notificación con el resultado (`mensaje` devuelto por la API) y refrescar automáticamente la tabla de mensajes en pantalla sin requerir una recarga completa del navegador.
    - **SI** la petición recibe un código HTTP `409 Conflict`, **EL SISTEMA DEBERÁ** reestablecer el botón, ocultar el spinner y alertar al usuario que ya existe una sincronización en curso ejecutándose en segundo plano.
    - **SI** la petición falla con HTTP `502 Bad Gateway` o error de red, **EL SISTEMA DEBERÁ** reestablecer el botón, ocultar el spinner y desplegar un mensaje de error descriptivo con la causa reportada por el backend.
  - **Contador Dinámico Reactivo al Seleccionar Fechas (Paridad Streamlit):**
    - **CUANDO** el usuario modifique los selectores de fecha ("Desde" o "Hasta") o alterne la casilla "Solo pendientes de evaluar", **EL SISTEMA DEBERÁ** calcular y mostrar de manera reactiva e inmediata en la interfaz la cantidad exacta de mensajes disponibles para evaluar y el subtotal de mensajes pendientes dentro de ese rango (ej: `📊 X mensajes disponibles para evaluar (Y pendientes)`).
    - **CUANDO** el conteo de mensajes disponibles para evaluar en el rango o filtro seleccionado sea cero (`0`), o **SI** la fecha "Desde" es posterior a la fecha "Hasta", **EL SISTEMA DEBERÁ** mostrar un aviso visual informativo (alerta o badge contextual claro indicando la ausencia de mensajes a evaluar o error de fechas) y deshabilitar inmediatamente el botón de evaluación ("Evaluar mensajes con IA") para prevenir peticiones vacías, errores de ejecución o consumo innecesario de tokens.
    - **CUANDO** existan uno o más mensajes evaluables (> 0) y no existan errores de rango de fechas, **EL SISTEMA DEBERÁ** mantener habilitado el botón de evaluación ("Evaluar mensajes con IA") reflejando claramente su disponibilidad operativa.
  - **Confirmación y Blindaje de la Casilla 'Solo pendientes de evaluar':**
    - **CUANDO** la casilla "Solo pendientes de evaluar" esté seleccionada (`solo_pendientes = true`), **EL SISTEMA DEBERÁ** en el Frontend computar y proyectar con precisión el subtotal de mensajes pendientes en el contador reactivo, y al despachar `POST /api/v1/ai/evaluate-batch`, **EL SISTEMA (Backend en `puente_motor_ia.py`) DEBERÁ** filtrar rigurosamente las interacciones excluyendo los IDs de mensaje que ya existan registrados en la tabla `lotes_ia_kpis` consultando de forma consolidada tanto Supabase como la base de datos local SQLite (`communitylab.db`), garantizando blindaje y consistencia dual ante contingencias de conectividad o ejecuciones locales.
    - **CUANDO** la casilla esté desmarcada (`solo_pendientes = false`), **EL SISTEMA DEBERÁ** permitir evaluar la totalidad de mensajes comprendidos en el rango de fechas seleccionado sin descartar aquellos con evaluaciones previas.
- **POR QUÉ:**
  - Para dotar al operador de control interactivo en tiempo real sobre la ingesta de mensajes, prevenir condiciones de carrera en la interfaz, emular la experiencia reactiva e intuitiva de Streamlit (`app.py`), evitar llamadas infructuosas a las APIs de IA cuando no existan mensajes y garantizar que la exclusión de mensajes ya evaluados sea confiable, bidireccional y blindada contra inconsistencias entre Supabase e SQLite.

### RF-03: Endpoint Estandarizado y Habilitación de Recuperación Selectiva (`POST /api/v1/discord/recover` y `RecoverDiscordMessagesModal.tsx`)
- **QUÉ:**
  - **CUANDO** el cliente realice una petición `POST` al endpoint `/api/v1/discord/recover` en `puente_motor_ia.py`, **EL SISTEMA DEBERÁ** requerir y validar el siguiente esquema JSON exacto en el cuerpo de la petición (payload):
    ```json
    {
      "mensajes": [
        {
          "canal_id": "string",
          "message_id": "string",
          "autor": "string",
          "texto": "string",
          "fecha": "string"
        }
      ]
    }
    ```
  - **CUANDO** se procese la carga de recuperación, **EL SISTEMA DEBERÁ** calcular el hash SHA-256 de cada elemento, insertar los mensajes nuevos en la tabla `interacciones` asignándoles obligatoriamente la etapa `'ingesta'` y el estado de revisión `'pendiente'`, con degradación dual (Supabase con fallback a SQLite local).
  - **CUANDO** la recuperación culmine, **EL SISTEMA DEBERÁ** responder con un código HTTP `200` y el siguiente esquema JSON exacto:
    ```json
    {
      "exito": true,
      "guardados_nuevos": 1,
      "repetidos_omitidos": 0,
      "mensaje": "Se recuperaron 1 mensajes nuevos (0 ya existían)"
    }
    ```
  - **EN EL BACKEND** `puente_motor_ia.py`, **EL SISTEMA DEBERÁ** definir alias de compatibilidad idénticos para previsualización de recuperación en las rutas `/api/v1/content-workflow/discord/recovery-preview` y `/api/v1/discord/recovery-preview`, permitiendo paginar e inspeccionar los mensajes históricos disponibles en Discord.
  - **CUANDO** el usuario abra el componente `RecoverDiscordMessagesModal.tsx` y seleccione uno o más mensajes no recuperados, **EL SISTEMA DEBERÁ** habilitar el botón de acción "Recuperar seleccionados" (el cual permanecerá deshabilitado cuando la selección esté vacía o durante el envío de la petición).
  - **CUANDO** el usuario pulse "Recuperar seleccionados", **EL SISTEMA DEBERÁ** enviar los mensajes seleccionados a `POST /api/v1/discord/recover`, mostrar retroalimentación de progreso, actualizar en el modal el estado de los mensajes marcándolos visualmente con `recuperado: true` (con etiqueta "Ya recuperado" y casilla deshabilitada), y refrescar de inmediato la bandeja principal en `Messages.tsx` reflejando los nuevos mensajes en etapa `'ingesta'`.
- **POR QUÉ:**
  - Para completar de forma estandarizada la funcionalidad pendiente del modal de recuperación, garantizando compatibilidad de endpoints y facilitando el rescate manual de conversaciones históricas clave.

### RF-04: Continuidad e Integración del Flujo Integral de Extremo a Extremo
- **QUÉ:**
  - **CUANDO** nuevos mensajes sean incorporados a través de la sincronización general (RF-01/RF-02) o de la recuperación selectiva (RF-03), **EL SISTEMA DEBERÁ** ponerlos a disposición inmediata en el flujo de trabajo:
    1. **Bandeja de Entrada:** Aparecer reflejados en `Messages.tsx` clasificados en etapa `'ingesta'` con estado de revisión `'pendiente'`.
    2. **Evaluación de IA:** Quedar habilitados para análisis automático por lotes mediante el botón de evaluación (`POST /api/v1/ai/evaluate-batch`) seleccionando cualquiera de los 3 cerebros configurados (`Groq Llama 3.3`, `Google Gemma 4`, `Google Gemini Flash Lite`) dentro del rango de fechas definido.
    3. **Curaduría Humana (HITL):** Si la evaluación de IA califica el mensaje con relevancia suficiente o como destacado, transferirlo a la bandeja de curaduría de Copywriting (`Approvals.tsx`) con estado `'pendiente'`.
    4. **Aprobación y Copy Final:** Permitir al revisor humano (Enoc) redactar y registrar el `copy_final`, transitando el estado a `'aprobado'`, el cual alimentará de inmediato las vistas de historias destacadas (`FeaturedStories.tsx`, `Highlights.tsx`), el resumen dinámico (`/api/v1/community/live-summary`) y el módulo de publicación/reportes semanales de Tania (`/api/v1/oci-storage/weekly-sync`).
    5. **Métricas y Exportación:** Reflejar las estadísticas agregadas en las vistas analíticas (`Audience.tsx`, `Calendar.tsx`, `MyReports.tsx`) y permitir su exportación completa en `Export.tsx`.
- **POR QUÉ:**
  - Para asegurar la coherencia sistémica de toda la solución, garantizando que la ingesta de datos desde Discord active de manera fluida y sin fisuras las etapas de inteligencia artificial, curación humana, reportes a la nube y análisis de métricas.

### RF-05: Inmutabilidad de los 17 Archivos Preexistentes de Raíz y Aislamiento de Código
- **QUÉ:**
  - **EN TODO MOMENTO**, **EL SISTEMA DEBERÁ** mantener intactos y sin ninguna modificación los **17 archivos `.py` preexistentes en la raíz del proyecto**:
    1. `api.py`
    2. `app.py`
    3. `armar_json_bot_python.py`
    4. `base_datos.py`
    5. `bot_lote.py`
    6. `cerebro_ia.py`
    7. `cerebro_ia_gemini_flash.py`
    8. `cerebro_ia_gemma_4.py`
    9. `evaluador_lotes.py`
    10. `limpieza.py`
    11. `modelos.py`
    12. `oci_uploader.py`
    13. `periodos.py`
    14. `procesamiento.py`
    15. `prompts_ia.py`
    16. `reporte_semanal.py`
    17. `ver_json.py`
    así como la totalidad de los archivos ubicados en las carpetas `motor-ia/` y `backend/`.
  - **CUANDO** se implemente la sincronización, recuperación o endpoints auxiliares de Discord, **EL SISTEMA DEBERÁ** encapsular toda la lógica exclusivamente en `puente_motor_ia.py` y los clientes tipados correspondientes de `frontend/src/`.
- **POR QUÉ:**
  - Para cumplir estrictamente con las Reglas 2 y 3 de la Constitución (`docs/constitution.md`), previniendo efectos secundarios indeseados y garantizando que las contribuciones de los distintos miembros del equipo coexistan sin colisiones.

### RF-06: Verificación Automatizada mediante Pruebas Test-First (TDD)
- **QUÉ:**
  - **CUANDO** se ejecute la suite de pruebas del proyecto (`pytest tests/`), **EL SISTEMA DEBERÁ** verificar mediante pruebas automatizadas con mocks en `tests/test_unificacion_motor_ia.py`:
    1. La ejecución de `POST /api/v1/discord/sync`, validando el ciclo asíncrono con cliente efímero (`client.start()` / `client.close()`), deduplicación por hash SHA-256, inserción dual (Supabase con fallback a SQLite) y estructura de respuesta.
    2. El control de concurrencia mediante `asyncio.Lock`, comprobando que un intento de sincronización concurrente devuelva HTTP `409 Conflict`.
    3. El manejo de contingencias y casos límite: HTTP `502 Bad Gateway` ante fallos de login/token ausente, HTTP `200` con mensaje `"Todos los mensajes están al día"` cuando no existan mensajes nuevos, HTTP `200` cuando no existan canales autorizados, y respeto del parámetro `limite_por_canal` y timeout.
    4. La ejecución de `POST /api/v1/discord/recover` validando el esquema estricto de entrada, deduplicación e inserción en etapa `'ingesta'` con estado `'pendiente'`.
    5. La disponibilidad de los alias de ruta `/api/v1/content-workflow/discord/recovery-preview` y `/api/v1/discord/recovery-preview`.
    6. El filtrado robusto de `solo_pendientes` en `POST /api/v1/ai/evaluate-batch`, validando que se consulten y excluyan los IDs registrados en `lotes_ia_kpis` tanto desde Supabase como desde SQLite local (`communitylab.db`).
    7. La conservación del 100% de las pruebas preexistentes en verde, sin llamadas de red externas reales durante los tests.
  - **CUANDO** se ejecute la verificación de compilación en el Frontend (`npm run build`), **EL SISTEMA DEBERÁ** compilar de forma estricta sin errores de tipado de TypeScript ni fallos de dependencias.
- **POR QUÉ:**
  - Para certificar la estabilidad de la rama `unificacion-beta` bajo el estándar de calidad definido en la Regla 6 de la Constitución.

---

## 3. Restricciones y Cumplimiento Constitucional

1. **Inviolabilidad del Main (Regla 1):** Todo el desarrollo se realiza en la rama `unificacion-beta`, sin pushes directos a `main`.
2. **Aislamiento de Interfaz (Regla 2):** Las responsabilidades de presentación se restringen a los componentes de `frontend/src/`, delegando la lógica de negocio al backend `puente_motor_ia.py`.
3. **Retrocompatibilidad Obligatoria (Regla 3):** Los formatos de salida de datos para Supabase, SQLite y el esquema de copywriting se mantienen estrictamente compatibles con la estructura preexistente.
4. **Seguridad de Secretos (Regla 4):** La autenticación con la API de Discord se realiza exclusivamente a través de variables de entorno (`DISCORD_BOT_TOKEN` o `DISCORD_TOKEN`) gestionadas mediante `os.environ` y `.env`.
5. **Control de Dependencias (Regla 5):** No se introducirán dependencias externas que no formen parte del entorno ya validado del proyecto.
6. **Diseño Test-First (Regla 6):** Ninguna funcionalidad se dará por aceptada sin contar previamente con su batería de pruebas automatizadas asociadas y verificadas.

---

## 4. Criterios de Aceptación Globales

- [ ] Existe el endpoint `POST /api/v1/discord/sync` en `puente_motor_ia.py` ejecutado de manera asíncrona no bloqueante con cliente efímero (`client.start()` / `client.close()`), deduplicación por hashes SHA-256 y persistencia dual (Supabase con fallback a SQLite local).
- [ ] El endpoint `POST /api/v1/discord/sync` implementa `asyncio.Lock` y responde con HTTP `409 Conflict` si ya hay una sincronización activa en progreso.
- [ ] La pantalla `Messages.tsx` incluye un botón funcional de sincronización de Discord con deshabilitación inmediata, spinner visual ante concurrencia, notificación con el mensaje retornado y refresco automático de la lista de mensajes.
- [ ] La pantalla `Messages.tsx` cuenta con un contador reactivo dinámico que, al seleccionar o alterar las fechas ('Desde' / 'Hasta') o alternar la casilla 'Solo pendientes de evaluar', calcula y muestra en tiempo real la cantidad exacta de mensajes disponibles para evaluar y el subtotal de mensajes pendientes (ej: `📊 X mensajes disponibles para evaluar (Y pendientes)`).
- [ ] En `Messages.tsx`, cuando el conteo de mensajes a evaluar es 0 o cuando la fecha 'Desde' es posterior a 'Hasta', se muestra un aviso visual informativo y el botón de evaluación con IA se deshabilita automáticamente.
- [ ] Cuando la casilla 'Solo pendientes de evaluar' está activa, el backend en `puente_motor_ia.py` (`POST /api/v1/ai/evaluate-batch`) filtra y excluye rigurosamente las interacciones contrastándolas contra los IDs de mensajes existentes en la tabla `lotes_ia_kpis` tanto de Supabase como de SQLite local (`communitylab.db`), y la UI refleja con exactitud el subtotal de mensajes pendientes.
- [ ] Existe el endpoint `POST /api/v1/discord/recover` con esquema validado de entrada (`mensajes: [...]`) y salida (`exito`, `guardados_nuevos`, `repetidos_omitidos`, `mensaje`), incorporando los mensajes recuperados en etapa `'ingesta'` y estado `'pendiente'`.
- [ ] Existen los alias coincidentes `/api/v1/content-workflow/discord/recovery-preview` y `/api/v1/discord/recovery-preview` en `puente_motor_ia.py`.
- [ ] El botón "Recuperar seleccionados" en `RecoverDiscordMessagesModal.tsx` está habilitado para mensajes seleccionados, actualiza el estado local a `recuperado: true` y refresca la bandeja principal de `Messages.tsx`.
- [ ] Se gestionan todos los casos límite: HTTP 502 por token ausente/inválido, HTTP 200 con `guardadas_nuevas: 0` y mensaje `"Todos los mensajes están al día"` ante idempotencia total, HTTP 200 ante ausencia de canales autorizados, parámetro `limite_por_canal` con valor por defecto de 100 y timeout de 30 segundos.
- [ ] Los mensajes ingresados quedan inmediatamente disponibles para ser evaluados con los 3 cerebros de IA, curados con `copy_final` por Enoc, integrados a los reportes semanales OCI de Tania y reflejados en el live summary y exportación.
- [ ] Los **17 archivos `.py` preexistentes de la raíz**, `motor-ia/` y `backend/` se mantienen completamente inalterados.
- [ ] El 100% de las pruebas automatizadas en `pytest` pasan en verde y el build de TypeScript en `frontend/` se ejecuta con cero errores.
