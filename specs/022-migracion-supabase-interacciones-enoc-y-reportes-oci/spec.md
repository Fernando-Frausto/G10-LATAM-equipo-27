# Especificación 022: Migración de Tabla de Interacciones a Cuenta de Supabase de Enoc y Unificación de Conexiones

## 1. Contexto y Propósito (El POR QUÉ)

### 1.1 Contexto y Petición del Usuario
El usuario ha establecido explícitamente el alcance prioritario e inmediato para esta especificación:
> *"Haz solo lo de la migracion de la tabla de interacciones, lo de oci esperare a respuesta de enoc"*

Conforme a esta instrucción operativa directa:
- Se **desacopla y pausa temporalmente** cualquier modificación referente al flujo de reportes de OCI y a la tabla `historial_reportes_semanales`. Dichos aspectos se abordarán en una especificación posterior una vez que Enoc remita las definiciones técnicas y esquemas correspondientes.
- La **Spec 022 se enfoca de manera exclusiva y rigurosa** en:
  1. La creación canónica de la tabla `interacciones` en la cuenta de Supabase de Enoc.
  2. La migración idempotente y sin pérdida de los 204 registros históricos desde la cuenta de Tania.
  3. La validación pre-flight y post-flight de paridad absoluta al 100% de registros y hashes.
  4. El ajuste defensivo de la secuencia autoincremental `interacciones_id_seq`.
  5. La unificación de variables de entorno en `.env` (apuntando `DATABASE_URL` al Transaction Pooler de Enoc en el puerto 6543 y preservando `TANIA_DATABASE_URL` para auditoría).
  6. La implementación de una salvaguarda de inicialización en `puente_motor_ia.py` para conmutar transparentemente si aún se detecta la referencia al proyecto de Tania.

---

### 1.2 Diagnóstico Técnico de Bases de Datos Reales

Tras auditar las instancias reales de PostgreSQL en Supabase configuradas en `.env` y la base de datos SQLite local, se constatan los siguientes hechos irrefutables:

1. **Instancia de Tania (`TANIA_DATABASE_URL` / `DATABASE_URL` histórico):**
   - **Host:** `aws-0-us-east-1.pooler.supabase.com:6543/postgres` (Proyecto `ietgilhtccvqlqglqazf`, Transaction Pooler).
   - **Tablas:** Contiene exclusivamente la tabla `public.interacciones`.
   - **Registros:** **204 filas activas** que representan el histórico íntegro de mensajes recolectados de la comunidad de Discord.
   - **Esquema canónico (11 columnas):**
     * `id`: SERIAL PRIMARY KEY
     * `hash`: VARCHAR(128) UNIQUE NOT NULL
     * `origen_comunidad`: VARCHAR(100) NOT NULL
     * `periodo_referencia`: VARCHAR(100) NOT NULL
     * `autor`: VARCHAR(100) NOT NULL
     * `canal`: VARCHAR(100) NOT NULL
     * `tipo`: VARCHAR(50)
     * `texto`: TEXT NOT NULL
     * `enviado_en`: VARCHAR(100)
     * `estado`: VARCHAR(50) NOT NULL DEFAULT 'pendiente'
     * `creado_en`: VARCHAR(100) NOT NULL

2. **Instancia de Enoc (`SUPABASE_DB_URL`):**
   - **Host:** `aws-0-us-east-1.pooler.supabase.com:6543/postgres` (Transaction Pooler) o `:5432/postgres` (Proyecto `swdoucawdasxmnomlcfu`).
   - **Tablas existentes:**
     * Tablas de LangGraph Checkpointer (`checkpoints`, `checkpoint_blobs`, `checkpoint_writes`, `checkpoint_migrations`).
     * `lotes_ia_kpis`: **13 filas** con evaluaciones de modelos IA.
     * `historial_reportes_semanales`: **0 filas** (tabla en espera de definición final).
   - **Diagnóstico:** Actualmente **NO existe** la tabla `public.interacciones` en esta cuenta.

---

### 1.3 Análisis de Viabilidad y Redituabilidad

- **Consolidación en una Sola Cuenta Remota:** Elimina la dispersión arquitectónica de mantener dos proyectos Supabase independientes (`ietgilhtccvqlqglqazf` y `swdoucawdasxmnomlcfu`). Al consolidar en la cuenta de Enoc, tanto las evaluaciones de IA (`lotes_ia_kpis`) como las interacciones comunitarias (`interacciones`) residen en el mismo clúster.
- **Optimización de Conexiones WAN:** Reduce el uso de conexiones remotas simultáneas desde el backend en Render y entornos de desarrollo, mitigando el riesgo de agotar pools de conexiones.
- **Cero Pérdida de Datos y Máxima Seguridad:** Protocolo estricto con validación de hashes pre/post migración que garantiza que no se pierde ni altera ningún registro de la comunidad.

---

### 1.4 Garantía de Preservación de Alta Velocidad (Regla de Oro)

Para cumplir con la directriz fundamental (*"no quiero que por cambiar conexiones salgan las cosas mal o se quiten de como esta de rapido actualmente"*):
1. **Lectura Inmediata Local (< 2 ms):**
   - Todos los endpoints GET (`/api/v1/messages`, `/api/v1/dashboard/kpis`, etc.) responden de inmediato consultando exclusivamente SQLite local (`communitylab.db`) y memoria caché, prohibiendo terminantemente llamadas WAN bloqueantes a Supabase en lecturas.
2. **Replicación Asíncrona en Segundo Plano:**
   - La sincronización o replicación hacia `interacciones` en Supabase Enoc ante nuevos mensajes se delega de forma desacoplada vía `asyncio.create_task`, respondiendo al cliente en < 50 ms.
3. **Resiliencia ante Caídas WAN:**
   - Si la red o Supabase presentan latencia o intermitencia, el sistema continúa operando localmente sin interrupción del servicio.

---

### 1.5 Inviolabilidad Constitucional y Aislamiento Arquitectónico

- **Respeto Estricto a los 17 Archivos Protegidos:** `base_datos.py`, `reporte_semanal.py`, `procesamiento.py`, `api.py` y las carpetas `backend/`, `motor-ia/` y `src/` permanecen 100% inalterados.
- **Ubicación del Script de Migración:** El script se alojará exclusivamente en `scripts/migrar_interacciones_enoc.py`.
- **Seguridad de Secretos (Regla Constitucional 4):** Queda terminantemente prohibido almacenar credenciales en código duro. Todas las URLs y claves se cargan exclusivamente desde `os.environ` mediante `.env`.

---

## 2. Requerimientos Funcionales (El QUÉ — Formato EARS)

### RF-01: Creación de la Tabla `interacciones` en la Cuenta de Supabase de Enoc
- **CUANDO** se ejecute el procedimiento de migración hacia la cuenta de Enoc (`swdoucawdasxmnomlcfu`), **EL SISTEMA DEBERÁ** crear la tabla `public.interacciones` si no existe en dicha base de datos, replicando exactamente la estructura canónica de 11 columnas:
  - `id SERIAL PRIMARY KEY`
  - `hash VARCHAR(128) UNIQUE NOT NULL`
  - `origen_comunidad VARCHAR(100) NOT NULL`
  - `periodo_referencia VARCHAR(100) NOT NULL`
  - `autor VARCHAR(100) NOT NULL`
  - `canal VARCHAR(100) NOT NULL`
  - `tipo VARCHAR(50)`
  - `texto TEXT NOT NULL`
  - `enviado_en VARCHAR(100)`
  - `estado VARCHAR(50) NOT NULL DEFAULT 'pendiente'`
  - `creado_en VARCHAR(100) NOT NULL`
- **CUANDO** la tabla sea creada o validada, **EL SISTEMA DEBERÁ** asegurar la existencia de un índice único sobre la columna `hash` (`CREATE UNIQUE INDEX IF NOT EXISTS idx_interacciones_hash ON public.interacciones(hash)`), blindando la base ante duplicaciones concurrentes.

---

### RF-02: Migración Idempotente y Preservación Íntegra de Datos Históricos
- **CUANDO** se inicie el script `scripts/migrar_interacciones_enoc.py`, **EL SISTEMA DEBERÁ** ejecutar un pre-vuelo (Pre-Flight Check) verificando que el conteo de registros en la cuenta de Tania sea exactamente de 204 registros (`SELECT COUNT(*) FROM interacciones` == 204) y obteniendo el conjunto completo de sus 204 hashes únicos.
- **CUANDO** se ejecute la transferencia de datos hacia la cuenta de Enoc, **EL SISTEMA DEBERÁ** insertar los registros preservando íntegramente sus valores de `id`, `hash`, `origen_comunidad`, `periodo_referencia`, `autor`, `canal`, `tipo`, `texto`, `enviado_en`, `estado` y `creado_en`.
- **SI** un registro a transferir ya existe en destino evaluado por su columna `hash`, **EL SISTEMA DEBERÁ** omitir la inserción de dicho registro mediante `ON CONFLICT (hash) DO NOTHING`, garantizando idempotencia absoluta en reejecuciones.
- **CUANDO** finalice la transferencia, **EL SISTEMA DEBERÁ** ejecutar un post-vuelo (Post-Flight Check) validando que:
  1. El conteo total de registros en la tabla `interacciones` de Enoc sea exactamente de 204 filas.
  2. El 100% de los 204 hashes únicos de origen coincidan idénticamente con los hashes presentes en destino (`set(hashes_origen) == set(hashes_destino)`).
- **CUANDO** el post-vuelo confirme la coincidencia exacta de registros y hashes, **EL SISTEMA DEBERÁ** reajustar la secuencia autoincremental en Enoc mediante la sentencia canónica:
  ```sql
  SELECT setval('interacciones_id_seq', COALESCE((SELECT MAX(id) FROM interacciones), 1), (SELECT COUNT(*) > 0 FROM interacciones));
  ```
  asegurando que las siguientes inserciones generen IDs correlativos superiores al máximo actual (`MAX(id) + 1`), previniendo colisiones de clave primaria.

---

### RF-03: Unificación Centralizada de Cadenas de Conexión en `.env`
- **EN TODO MOMENTO**, el script `scripts/migrar_interacciones_enoc.py` **DEBERÁ** obtener sus credenciales de conexión exclusivamente desde `os.environ` (ej. `TANIA_DATABASE_URL` y `DATABASE_URL` / `SUPABASE_DB_URL`), prohibiendo absolutamente contraseñas o tokens en código duro en cumplimiento de la Regla 4 de la Constitución.
- **DONDE** esté disponible, **EL SISTEMA DEBERÁ** priorizar y configurar la conexión al Transaction Pooler de Enoc en el puerto `6543` (`aws-0-us-east-1.pooler.supabase.com:6543/postgres`) para soportar alta concurrencia y reutilización de conexiones en Render y local.
- **CUANDO** la migración sea validada exitosamente al 100% por el post-vuelo, **EL SISTEMA DEBERÁ** actualizar el archivo `.env`:
  - `DATABASE_URL`: Apuntando a la cuenta de Enoc (`swdoucawdasxmnomlcfu`) en el Transaction Pooler (puerto 6543).
  - `TANIA_DATABASE_URL`: Preservada como respaldo histórico inmutable.

---

### RF-04: Salvaguarda de Inicialización y Resiliencia en `puente_motor_ia.py`
- **CUANDO** el backend `puente_motor_ia.py` arranque o inicialice su configuración de base de datos, **EL SISTEMA DEBERÁ** inspeccionar el contenido de `DATABASE_URL`.
- **SI** `DATABASE_URL` contiene la referencia o identificador del proyecto de Tania (`ietgilhtccvqlqglqazf`), **EL SISTEMA DEBERÁ** conmutar automáticamente la conexión activa hacia `SUPABASE_DB_URL` (Enoc) y registrar un log de advertencia informativo (`logger.warning`), evitando interrupciones operativas ante configuraciones de entorno no actualizadas en servidores remotos.

---

### RF-05: Inviolabilidad Constitucional y Preservación Estricta de Alta Velocidad
- **EN TODO MOMENTO**, **EL SISTEMA DEBERÁ** mantener intactos y sin modificación alguna los 17 archivos protegidos de la raíz (`base_datos.py`, `reporte_semanal.py`, `procesamiento.py`, `api.py`, etc.), así como las carpetas `backend/`, `motor-ia/` y `src/`.
- **MIENTRAS** la aplicación atienda peticiones HTTP GET en la API (`/api/v1/messages`, `/api/v1/dashboard/kpis`, etc.), **EL SISTEMA DEBERÁ** responder en menos de 2 milisegundos consultando exclusivamente SQLite local y memoria caché, manteniendo la prohibición absoluta de ejecutar llamadas de red WAN sincrónicas a Supabase durante lecturas (Regla de Oro).
- **CUANDO** se ingesten o sincronicen mensajes nuevos desde Discord o la interfaz, **EL SISTEMA DEBERÁ** persistir inmediatamente en SQLite local y delegar la replicación hacia la tabla `interacciones` de Supabase Enoc en segundo plano (`asyncio.create_task`), respondiendo a la interfaz en menos de 50 milisegundos.

---

## 3. Casos Límite y Manejo de Errores

### 3.1 Idempotencia ante Reintentos de Migración
- **SI** el script de migración se ejecuta repetidamente o sufre una interrupción a mitad de la transferencia, la cláusula `ON CONFLICT (hash) DO NOTHING` garantiza que no se generen duplicados y que la base de datos de Enoc conserve exactamente 204 registros válidos.

### 3.2 Inconsistencia en Pre-Flight o Post-Flight
- **SI** en el pre-vuelo la cuenta de origen en Tania no devuelve exactamente 204 registros, el script aborta inmediatamente la ejecución con código de salida 1 sin escribir en Enoc.
- **SI** en el post-vuelo el conteo en Enoc no coincide con 204 o algún hash discrepa, el script emite un error explícito y no ejecuta la conmutación de `.env`.

### 3.3 Indisponibilidad Transitoria de Red o Supabase WAN
- **SI** la conexión a Supabase Enoc presenta latencia, corte de red o timeout durante la operación regular del backend, la base local SQLite absorbe la lectura y escritura, y el sistema registra una advertencia en logs sin colapsar el servicio.

### 3.4 Sincronización Defensiva de Secuencia Autoincremental
- **SI** tras la migración se inserta un nuevo registro desde el backend o scripts auxiliares, la ejecución previa de `SELECT setval('interacciones_id_seq', ...)` previene el error `duplicate key value violates unique constraint "interacciones_pkey"`, asignando el ID inmediatamente posterior al máximo existente.

---

## 4. Criterios de Aceptación y Verificación (Definition of Done)

1. **Tabla Creada y Validada en Enoc:**
   - La tabla `public.interacciones` existe en la cuenta de Enoc (`swdoucawdasxmnomlcfu`) con el DDL canónico de 11 columnas y el índice UNIQUE sobre `hash`.
2. **Transferencia Íntegra de 204 Registros:**
   - Pre-flight valida 204 registros en Tania.
   - Post-flight valida 204 registros en Enoc.
   - Coincidencia del 100% en el conjunto de hashes únicos entre ambas bases.
   - Secuencia `interacciones_id_seq` sincronizada al ID máximo.
3. **Cadenas de Conexión Unificadas:**
   - `.env` actualizado con `DATABASE_URL` apuntando a Enoc en Transaction Pooler (puerto 6543).
   - `TANIA_DATABASE_URL` respaldada para auditoría histórica.
   - Cero credenciales en código duro.
4. **Salvaguarda de Backend Activa:**
   - Salvaguarda en `puente_motor_ia.py` conmutando transparentemente a Enoc si detecta `ietgilhtccvqlqglqazf`.
5. **Preservación de Rendimiento y No Regresión:**
   - 100% de las pruebas unitarias y de integración de `pytest` pasando en verde.
   - `npm run build` en el frontend finaliza con código de salida 0.
   - Inviolabilidad absoluta de los 17 archivos protegidos y directorios reservados.
