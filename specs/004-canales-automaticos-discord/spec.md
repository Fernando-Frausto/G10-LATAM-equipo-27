# Especificación: Detección Automática de Canales de Discord y Preservación de Ingesta

## Contexto y Alcance
Esta especificación define la integración de la funcionalidad de detección dinámica de canales de texto de Discord (`feature/canales-automaticos` de Eduardo) en el pipeline de ingesta de CommunityLab (`armar_json_bot_python.py` y `bot_lote.py`). 
El objetivo es reemplazar la dependencia de identificadores fijos por un mecanismo basado en funciones puras y permisos de Discord (`detectar_canales`), incorporar un filtrado saneado por servidor (`DISCORD_GUILD_ID`), mantener retrocompatibilidad de importaciones (`CANALES = {}`), normalizar los nombres de canal evitando prefijos duplicados (`##`) para no alterar el cálculo de hashes en Supabase, y preservar de forma inmutable el descarte estricto de bots y webhooks.

---

## Requerimientos Funcionales (EARS)

### 1. Detección Dinámica de Canales con Verificación de Permisos (Event-driven Requirement)
- **QUÉ:** Al inicializar la extracción de mensajes en `bot_lote.py`, el sistema deberá delegar en una función pura `detectar_canales(servidores, id_servidor=None) -> list` en `armar_json_bot_python.py`, la cual deberá iterar sobre los servidores disponibles e inspeccionar sus canales de texto (`TextChannel`), seleccionando únicamente aquellos donde el bot (`servidor.me`) cuente con permisos activos de visualización (`permisos.view_channel == True`) y lectura de historial (`permisos.read_message_history == True`).
- **POR QUÉ:** Para dinamizar la ingesta de datos eliminando la configuración manual de identificadores de canal y prevenir excepciones por falta de permisos al intentar acceder a canales privados o restringidos.

---

### 2. Saneamiento y Aislamiento por Servidor mediante `DISCORD_GUILD_ID` (State-driven / Unwanted Behavior)
- **QUÉ:** Cuando se provea el parámetro de servidor (a través de la variable de entorno `DISCORD_GUILD_ID`), el sistema deberá sanear el valor eliminando espacios en blanco (`.strip() or None`). Si se especifica un `id_servidor` y este no coincide con ningún servidor conectado, el sistema deberá emitir una advertencia informativa y retornar una lista vacía `[]`, impidiendo la lectura de servidores ajenos por error. Si el bot está presente en más de un servidor y no se especifica `id_servidor`, el sistema deberá emitir un aviso informativo y proceder con la lectura de los servidores disponibles.
- **POR QUÉ:** Para garantizar que el bot solo extraiga mensajes de la comunidad de interés (`Discord_Grupo_ONE_G10`) y brindar un comportamiento seguro y predecible ante IDs de servidor inexistentes o mal configurados.

---

### 3. Preservación Inmutable del Filtro de Bots y Webhooks (Unwanted Behavior / Event-driven)
- **QUÉ:** Durante la construcción del paquete de interacciones en `construir_paquete` (`armar_json_bot_python.py`), el sistema deberá evaluar y descartar inmediatamente cualquier mensaje donde `getattr(m.author, "bot", False)` sea verdadero o donde `getattr(m, "webhook_id", None)` no sea nulo, garantizando que ninguna interacción automática sea registrada ni enviada al pipeline de persistencia.
- **POR QUÉ:** Para proteger la base de datos de mensajes crudos (`interacciones`) y el pipeline de análisis de IA contra la contaminación de anuncios generados por webhooks, mensajes del sistema o bots automatizados (como `Spidey Boy#0000`).

---

### 4. Normalización de Nombres de Canal y Retrocompatibilidad de Imports (Ubiquitous Requirement)
- **QUÉ:** El sistema deberá:
  1. Definir la función pura `nombre_canal(canal) -> str` en `armar_json_bot_python.py`, la cual deberá obtener `nombre = getattr(canal, "name", None)` y retornar `f"#{nombre.lstrip('#')}"` si existe nombre legible, o `f"#{canal.id}"` en caso contrario, eliminando cualquier riesgo de prefijos duplicados (`##`).
  2. Mantener la constante `CANALES = {}` (diccionario vacío de retrocompatibilidad) en `armar_json_bot_python.py` para evitar errores de importación (`ImportError`) en módulos o scripts heredados.
- **POR QUÉ:** Para preservar el cálculo determinista e idéntico de la función criptográfica `calcular_hash(origen_comunidad, canal, autor, texto)` evitando duplicados en Supabase, y cumplir con la Regla 3 de la Constitución (Retrocompatibilidad Obligatoria).

---

### 5. Suite de Pruebas Unitarias Automatizadas con Mocks de Discord (TDD) (Ubiquitous Requirement)
- **QUÉ:** El sistema deberá contar con una suite de pruebas automatizadas con `pytest` que valide mediante dobles de prueba (mocks) de los objetos de `discord.py` (`Guild`, `TextChannel`, `Permissions`, `Message`, `User`):
  1. `detectar_canales`: inclusión de canales con permisos completos (`view_channel=True`, `read_message_history=True`) y exclusión cuando falte cualquiera de ellos.
  2. `detectar_canales`: retorno de lista vacía `[]` ante `id_servidor` inexistente.
  3. `nombre_canal`: formateo correcto con `#`, eliminación de almohadillas duplicadas (`#general` a partir de `general` o `#general`), y fallback a `#{canal.id}`.
  4. `construir_paquete`: exclusión inmutable de bots (`author.bot = True`) y webhooks (`webhook_id is not None`).
  5. Retrocompatibilidad: presencia de la constante `CANALES`.
  Ninguna prueba unitaria deberá conectarse a internet ni consumir credenciales reales de Discord.
- **POR QUÉ:** Para dar cumplimiento a la Regla 6 de la Constitución (Diseño Test-First), certificando la robustez matemática del componente de ingesta sin depender de servidores activos ni tokens reales.

---

## Criterios de Aceptación y Retrocompatibilidad
1. El contrato devuelto por `construir_paquete(mensajes)` debe preservar idéntica la estructura de interacciones con el campo `canal` normalizado en formato `#nombre`.
2. Las pruebas preexistentes del repositorio deben continuar ejecutándose al 100% en verde.
3. El archivo `armar_json_bot_python.py` debe exponer `detectar_canales`, `nombre_canal`, `construir_paquete` y `CANALES = {}`.
