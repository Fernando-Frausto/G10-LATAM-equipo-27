# Plan de Arquitectura: Detección Automática de Canales de Discord y Preservación de Ingesta

## 1. Visión General y Objetivos
Este plan detalla el diseño técnico para integrar la detección dinámica de canales de texto de Discord (`feature/canales-automaticos`) en el pipeline de ingesta de CommunityLab.
Los principios arquitectónicos rectores son:
- **Dinamismo y Resiliencia:** Descubrimiento automático de canales de texto con permisos efectivos (`view_channel` y `read_message_history`), eliminando la fragilidad de configuraciones manuales fijas.
- **Aislamiento Comunitario:** Filtrado opcional y saneado por servidor (`DISCORD_GUILD_ID`) con comportamiento defensivo ante servidores desconocidos.
- **Inmutabilidad del Filtro de Ruido:** Preservación inalterable del descarte inmediato de mensajes provenientes de bots y webhooks.
- **Retrocompatibilidad Criptográfica:** Normalización uniforme `#nombre` sin duplicaciones (`##`) para no alterar los hashes SHA-256 de deduplicación en Supabase, y preservación de la constante `CANALES = {}`.
- **Diseño Test-First (Regla 6):** Suite completa de pruebas unitarias con dobles de prueba (mocks) de Discord.

---

## 2. Diagrama de Flujo del Pipeline de Ingesta

```mermaid
flowchart TD
    subgraph Inicializacion["1. Conexión y Descubrimiento"]
        BOT["bot_lote.py (on_ready)"]
        ENV["Lectura saneada de DISCORD_GUILD_ID<br/>.strip() or None"]
        DETECT["armar_json_bot_python.py<br/>detectar_canales(servidores, id_servidor)"]
        
        BOT --> ENV
        ENV --> DETECT
    end

    subgraph Filtro_Canales["2. Verificación de Permisos"]
        PERMS{"¿canal es TextChannel y<br/>permisos_for(me) tiene<br/>view_channel y read_message_history?"}
        GUILD{"¿Coincide con id_servidor<br/>(si fue especificado)?"}
        LISTA["Lista de Canales Autorizados"]
        EMPTY["Retorna [] y emite aviso"]

        DETECT --> GUILD
        GUILD -->|No coincide| EMPTY
        GUILD -->|Sí coincide o no especificado| PERMS
        PERMS -->|Sí| LISTA
        PERMS -->|No| DISCARD_CH["Omite canal sin permisos"]
    end

    subgraph Extraccion_Mensajes["3. Recolección y Filtrado de Mensajes"]
        READ_MSG["Lectura asíncrona: canal.history()"]
        CONSTRUCT["armar_json_bot_python.py<br/>construir_paquete(mensajes)"]
        BOT_CHECK{"¿m.author.bot o<br/>m.webhook_id?"}
        NAME_CH["nombre_canal(m.channel)<br/>f'#{nombre.lstrip(\"#\")}'"]
        PAQUETE["Paquete de Interacciones Limpio"]

        LISTA --> READ_MSG
        READ_MSG --> CONSTRUCT
        CONSTRUCT --> BOT_CHECK
        BOT_CHECK -->|Sí| DISCARD_MSG["DESCARTAR INMEDIATAMENTE<br/>(No almacenar)"]
        BOT_CHECK -->|No| NAME_CH
        NAME_CH --> PAQUETE
    end

    subgraph Procesamiento["4. Deduplicación y Persistencia"]
        PROC["procesamiento.py<br/>procesar_actividad(paquete)"]
        HASH["calcular_hash(comunidad, #canal, autor, texto)"]
        SUPABASE[("Supabase: tabla interacciones")]

        PAQUETE --> PROC
        PROC --> HASH
        HASH --> SUPABASE
    end
```

---

## 3. Especificación Técnica de Componentes

### 3.1 Módulo `armar_json_bot_python.py`
Se refactoriza incorporando las siguientes funciones puras y constantes:
1. **Constante de retrocompatibilidad:**
   ```python
   CANALES = {}
   ```
2. **Función `nombre_canal(canal) -> str`:**
   ```python
   def nombre_canal(canal) -> str:
       """Formatea el canal con prefijo '#' sin generar duplicados '##'."""
       nombre = getattr(canal, "name", None)
       if nombre:
           return f"#{nombre.lstrip('#')}"
       return f"#{getattr(canal, 'id', 'desconocido')}"
   ```
3. **Función `detectar_canales(servidores, id_servidor=None) -> list`:**
   ```python
   def detectar_canales(servidores, id_servidor=None) -> list:
       """Retorna los canales de texto legibles por el bot."""
       id_servidor_str = str(id_servidor).strip() if id_servidor else None
       
       # Si se especificó un ID y no está en los servidores conectados, retorna vacío
       if id_servidor_str and not any(str(getattr(s, "id", "")) == id_servidor_str for s in servidores):
           return []
           
       canales = []
       for servidor in servidores:
           if id_servidor_str and str(getattr(servidor, "id", "")) != id_servidor_str:
               continue
           for canal in getattr(servidor, "text_channels", []):
               permisos = canal.permissions_for(servidor.me)
               if getattr(permisos, "view_channel", False) and getattr(permisos, "read_message_history", False):
                   canales.append(canal)
       return canales
   ```
4. **Función `construir_paquete(mensajes: list) -> dict | None`:**
   - Mantiene la exclusión inmutable:
     ```python
     if getattr(m.author, "bot", False) or getattr(m, "webhook_id", None):
         continue
     ```
   - Asigna `"canal": nombre_canal(m.channel)`.

### 3.2 Módulo `bot_lote.py`
- Sanea la lectura de `DISCORD_GUILD_ID`:
  ```python
  ID_SERVIDOR = (os.getenv("DISCORD_GUILD_ID") or "").strip() or None
  ```
- En `on_ready`:
  - Invoca `canales = detectar_canales(cliente.guilds, ID_SERVIDOR)`.
  - Si `not canales`: emite log informativo indicando verificación de permisos o ID de servidor.
  - Si `len(cliente.guilds) > 1 and not ID_SERVIDOR`: emite aviso recordando configurar `DISCORD_GUILD_ID`.
  - Itera sobre `canales` y procesa el paquete resultante con `procesar_actividad`.

---

## 4. Estrategia de Pruebas Unitarias (TDD con Mocks)

Siguiendo la Regla 6 de la Constitución, se creará `tests/test_canales_discord.py` utilizando `unittest.mock.MagicMock` para modelar objetos de Discord:
1. `test_detectar_canales_con_permisos_completos`: Canal con `view_channel=True` y `read_message_history=True` es incluido.
2. `test_detectar_canales_sin_permisos_es_excluido`: Canal con `view_channel=False` o `read_message_history=False` es omitido.
3. `test_detectar_canales_filtra_por_servidor`: Solo incluye canales del servidor cuyo ID coincida con `id_servidor`.
4. `test_detectar_canales_servidor_inexistente_retorna_vacio`: Si `id_servidor` no existe en `servidores`, retorna `[]`.
5. `test_nombre_canal_limpia_dobles_hashes`: Canal `"general"` produce `"#general"` y canal `"#preguntas"` produce `"#preguntas"` (sin `##`). Fallback a `#{canal.id}` si no tiene nombre.
6. `test_construir_paquete_excluye_bots_y_webhooks`: Mensajes con `author.bot=True` o `webhook_id != None` son descartados del paquete.
7. `test_retrocompatibilidad_canales_dict`: Verifica que `CANALES` exista como diccionario en el módulo.
