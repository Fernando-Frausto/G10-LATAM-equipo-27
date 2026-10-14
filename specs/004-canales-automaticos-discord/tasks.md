# Tareas de Implementación: Detección Automática de Canales de Discord y Preservación de Ingesta

## Tarea 1: Suite de pruebas unitarias TDD con mocks de Discord
- **RF:** RF-1, RF-2, RF-3, RF-4, RF-5
- **Descripción:** Crear el archivo `tests/test_canales_discord.py` con pruebas unitarias usando `unittest.mock.MagicMock` para modelar objetos de Discord (`Guild`, `TextChannel`, `Permissions`, `Message`, `User`):
  1. `detectar_canales`: inclusión de canales con `view_channel=True` y `read_message_history=True`.
  2. `detectar_canales`: exclusión de canales con permisos insuficientes.
  3. `detectar_canales`: filtrado por `id_servidor` y retorno de lista vacía `[]` si el servidor no existe.
  4. `nombre_canal`: formateo de nombre anteponiendo `#`, evitando duplicaciones (`##`) y fallback a `#{canal.id}`.
  5. `construir_paquete`: exclusión inmutable de mensajes de bots (`author.bot=True`) y webhooks (`webhook_id is not None`).
  6. Existencia de `CANALES` como diccionario para retrocompatibilidad de imports.
- [x] **Hecho cuando:** `tests/test_canales_discord.py` exista y sus pruebas fallen inicialmente (rojo) por faltar la implementación en el código.

---

## Tarea 2: Implementación de funciones puras y retrocompatibilidad en `armar_json_bot_python.py`
- **RF:** RF-1, RF-3, RF-4
- **Descripción:** Modificar `armar_json_bot_python.py`:
  1. Definir la constante vacía `CANALES = {}`.
  2. Implementar la función pura `nombre_canal(canal) -> str` que sanea `nombre = getattr(canal, "name", None)` y devuelve `f"#{nombre.lstrip('#')}"` o `f"#{canal.id}"`.
  3. Implementar la función pura `detectar_canales(servidores, id_servidor=None) -> list` verificando permisos `view_channel` y `read_message_history` en `canal.permissions_for(servidor.me)`.
  4. En `construir_paquete`, asignar `"canal": nombre_canal(m.channel)` preservando estrictamente la exclusión de `m.author.bot` y `m.webhook_id`.
- [x] **Hecho cuando:** Las pruebas de `nombre_canal`, `detectar_canales`, `CANALES` y `construir_paquete` de la Tarea 1 pasen al 100% en verde.

---

## Tarea 3: Integración y manejo defensivo en `bot_lote.py`
- **RF:** RF-1, RF-2
- **Descripción:** Modificar `bot_lote.py`:
  1. Importar `detectar_canales` y `construir_paquete` desde `armar_json_bot_python.py`.
  2. Leer y sanear `DISCORD_GUILD_ID` usando `(os.getenv("DISCORD_GUILD_ID") or "").strip() or None` (tanto en entorno local como Colab).
  3. En `on_ready`, invocar `canales = detectar_canales(cliente.guilds, ID_SERVIDOR)`.
  4. Agregar logs informativos si no se encuentran canales o si existen múltiples servidores sin ID configurado.
  5. Iterar sobre `canales` extrayendo el historial de mensajes de forma asíncrona.
- [x] **Hecho cuando:** `bot_lote.py` descubra dinámicamente los canales de texto autorizados respetando `DISCORD_GUILD_ID` y las pruebas de integración con mocks pasen en verde.

---

## Tarea 4: Verificación global de no-regresión
- **RF:** RF-5
- **Descripción:** Ejecutar la suite completa de pruebas unitarias (`pytest`) para certificar que el pipeline de ingesta, el filtrado de bots/webhooks, la base de datos, los estados HITL y la API permanezcan completamente verdes y sin regresiones.
- [x] **Hecho cuando:** `pytest` finalice con código de salida 0 y reporte 100% de tests en verde (0 fallos, 0 errores, 0 regresiones).
