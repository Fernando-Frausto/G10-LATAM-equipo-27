"""
Pruebas unitarias para la detección automática de canales de Discord y preservación de ingesta.
Especificación: specs/004-canales-automaticos-discord/plan.md (RF-1 a RF-5)
"""
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

import bot_lote
from armar_json_bot_python import (
    CANALES,
    construir_paquete,
    detectar_canales,
    nombre_canal,
)


def crear_mock_canal(id_canal=1001, nombre="general", view_channel=True, read_message_history=True):
    """Crea un doble de prueba (Mock) de discord.TextChannel con permisos configurados."""
    canal = MagicMock()
    canal.id = id_canal
    canal.name = nombre
    permisos = MagicMock()
    permisos.view_channel = view_channel
    permisos.read_message_history = read_message_history
    canal.permissions_for.return_value = permisos
    return canal


def crear_mock_servidor(id_servidor=12345, canales=None):
    """Crea un doble de prueba (Mock) de discord.Guild con lista de canales de texto."""
    servidor = MagicMock()
    servidor.id = id_servidor
    servidor.me = MagicMock()
    servidor.text_channels = canales if canales is not None else []
    return servidor


def crear_mock_mensaje(
    autor="usuario_test",
    es_bot=False,
    webhook_id=None,
    contenido="Mensaje de prueba",
    canal=None,
    fecha=None,
):
    """Crea un doble de prueba (Mock) de discord.Message."""
    msg = MagicMock()
    msg.author = MagicMock()
    msg.author.bot = es_bot
    msg.author.__str__.return_value = autor
    msg.webhook_id = webhook_id
    msg.content = contenido
    msg.channel = canal or crear_mock_canal()
    msg.created_at = fecha or datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)
    return msg


# --- 1. Retrocompatibilidad ---

def test_retrocompatibilidad_canales_dict():
    """Verifica que CANALES exista como diccionario para asegurar retrocompatibilidad de imports."""
    assert isinstance(CANALES, dict)


# --- 2. Detección de Canales y Permisos ---

def test_detectar_canales_con_permisos_completos():
    """Canal con view_channel=True y read_message_history=True debe ser incluido."""
    canal_ok = crear_mock_canal(id_canal=101, nombre="general", view_channel=True, read_message_history=True)
    servidor = crear_mock_servidor(id_servidor=1, canales=[canal_ok])

    canales = detectar_canales([servidor])

    assert canal_ok in canales
    assert len(canales) == 1
    canal_ok.permissions_for.assert_called_once_with(servidor.me)


def test_detectar_canales_sin_permisos_es_excluido():
    """Canales sin view_channel o sin read_message_history deben ser omitidos."""
    c_ok = crear_mock_canal(id_canal=101, nombre="canal-ok", view_channel=True, read_message_history=True)
    c_no_view = crear_mock_canal(id_canal=102, nombre="canal-privado", view_channel=False, read_message_history=True)
    c_no_history = crear_mock_canal(id_canal=103, nombre="canal-sin-historial", view_channel=True, read_message_history=False)
    c_sin_nada = crear_mock_canal(id_canal=104, nombre="canal-bloqueado", view_channel=False, read_message_history=False)

    servidor = crear_mock_servidor(id_servidor=1, canales=[c_ok, c_no_view, c_no_history, c_sin_nada])

    canales = detectar_canales([servidor])

    assert canales == [c_ok]
    assert c_no_view not in canales
    assert c_no_history not in canales
    assert c_sin_nada not in canales


def test_detectar_canales_filtra_por_servidor():
    """Si se especifica id_servidor, solo se deben retornar canales de dicho servidor."""
    c1 = crear_mock_canal(id_canal=101, nombre="servidor1-canal")
    c2 = crear_mock_canal(id_canal=201, nombre="servidor2-canal")

    s1 = crear_mock_servidor(id_servidor=111, canales=[c1])
    s2 = crear_mock_servidor(id_servidor=222, canales=[c2])

    # Filtrar por string
    canales_s1 = detectar_canales([s1, s2], id_servidor="111")
    assert canales_s1 == [c1]

    # Filtrar con espacios o como int
    canales_s2 = detectar_canales([s1, s2], id_servidor=" 222 ")
    assert canales_s2 == [c2]

    canales_s2_int = detectar_canales([s1, s2], id_servidor=222)
    assert canales_s2_int == [c2]


def test_detectar_canales_servidor_inexistente_retorna_vacio():
    """Si id_servidor no coincide con ninguno de los conectados, retorna lista vacía []."""
    c1 = crear_mock_canal(id_canal=101, nombre="canal-valido")
    s1 = crear_mock_servidor(id_servidor=111, canales=[c1])

    canales = detectar_canales([s1], id_servidor="999999")
    assert canales == []


# --- 3. Normalización y Formato del Nombre del Canal ---

def test_nombre_canal_limpia_dobles_hashes():
    """Canal 'general' produce '#general' y '#preguntas' produce '#preguntas' sin '##'."""
    c1 = MagicMock()
    c1.name = "general"
    assert nombre_canal(c1) == "#general"

    c2 = MagicMock()
    c2.name = "#preguntas"
    assert nombre_canal(c2) == "#preguntas"

    c3 = MagicMock()
    c3.name = "###avisos"
    assert nombre_canal(c3) == "#avisos"


def test_nombre_canal_fallback_sin_nombre():
    """Si el canal no tiene nombre o está vacío, fallback a f'#{canal.id}'."""
    c_sin_nombre = MagicMock()
    c_sin_nombre.name = None
    c_sin_nombre.id = 987654321
    assert nombre_canal(c_sin_nombre) == "#987654321"

    c_nombre_vacio = MagicMock()
    c_nombre_vacio.name = ""
    c_nombre_vacio.id = 12345
    assert nombre_canal(c_nombre_vacio) == "#12345"

    c_desconocido = MagicMock(spec=[])
    assert nombre_canal(c_desconocido) == "#desconocido"


# --- 4. Exclusión Inmutable de Bots y Webhooks en Paquete ---

def test_construir_paquete_excluye_bots_y_webhooks():
    """Mensajes con author.bot=True o webhook_id no None deben ser completamente ignorados."""
    c = crear_mock_canal(id_canal=101, nombre="general")

    m_humano1 = crear_mock_mensaje(
        autor="alice",
        es_bot=False,
        webhook_id=None,
        contenido="Primer aporte",
        canal=c,
        fecha=datetime(2026, 10, 1, 10, 0, 0, tzinfo=timezone.utc),
    )
    m_bot = crear_mock_mensaje(
        autor="spidey_bot",
        es_bot=True,
        webhook_id=None,
        contenido="Notificación automática",
        canal=c,
        fecha=datetime(2026, 10, 1, 10, 1, 0, tzinfo=timezone.utc),
    )
    m_webhook = crear_mock_mensaje(
        autor="github_app",
        es_bot=False,
        webhook_id=12345678,
        contenido="Commit pushed",
        canal=c,
        fecha=datetime(2026, 10, 1, 10, 2, 0, tzinfo=timezone.utc),
    )
    m_humano2 = crear_mock_mensaje(
        autor="bob",
        es_bot=False,
        webhook_id=None,
        contenido="Segundo aporte relevante",
        canal=c,
        fecha=datetime(2026, 10, 1, 10, 3, 0, tzinfo=timezone.utc),
    )

    paquete = construir_paquete([m_humano1, m_bot, m_webhook, m_humano2])

    assert paquete is not None
    interacciones = paquete["interacciones"]
    assert len(interacciones) == 2

    autores = [i["autor"] for i in interacciones]
    assert autores == ["alice", "bob"]
    assert "spidey_bot" not in autores
    assert "github_app" not in autores

    # Verifica que el canal haya sido normalizado con '#'
    for i in interacciones:
        assert i["canal"] == "#general"


def test_construir_paquete_solo_bots_retorna_none():
    """Si todos los mensajes provienen de bots o webhooks, construir_paquete retorna None."""
    c = crear_mock_canal(id_canal=101, nombre="general")
    m_bot = crear_mock_mensaje(autor="bot", es_bot=True, canal=c)
    m_webhook = crear_mock_mensaje(autor="hook", webhook_id=999, canal=c)

    paquete = construir_paquete([m_bot, m_webhook])
    assert paquete is None


# --- 5. Integración con bot_lote y on_ready ---

def test_bot_lote_on_ready_flujo_completo():
    """Valida el flujo de on_ready en bot_lote.py: detección dinámica de canales, lectura asíncrona y procesamiento."""
    async def _test():
        c1 = crear_mock_canal(id_canal=101, nombre="general", view_channel=True, read_message_history=True)
        c2 = crear_mock_canal(id_canal=102, nombre="preguntas", view_channel=True, read_message_history=True)
        c_sin_permiso = crear_mock_canal(id_canal=103, nombre="privado", view_channel=False, read_message_history=True)

        servidor = crear_mock_servidor(id_servidor=12345, canales=[c1, c2, c_sin_permiso])

        # Simular historial asíncrono en c1
        m1 = crear_mock_mensaje(autor="usuario1", contenido="Pregunta 1", canal=c1)
        async def history_c1(limit=None):
            yield m1
        c1.history = history_c1

        # Simular historial asíncrono en c2
        m2 = crear_mock_mensaje(autor="usuario2", contenido="Pregunta 2", canal=c2)
        async def history_c2(limit=None):
            yield m2
        c2.history = history_c2

        mock_cliente = MagicMock()
        mock_cliente.user = "BotTest#0001"
        mock_cliente.guilds = [servidor]
        mock_cliente.close = AsyncMock()

        with patch("bot_lote.cliente", mock_cliente), \
             patch("bot_lote.ID_SERVIDOR", "12345"), \
             patch("bot_lote.procesar_actividad") as mock_proc:
            mock_proc.return_value = {"guardados": 2, "descartados": 0}

            await bot_lote.on_ready()

            # Debe haber invocado procesar_actividad con las 2 interacciones
            mock_proc.assert_called_once()
            paquete = mock_proc.call_args[0][0]
            assert len(paquete["interacciones"]) == 2
            canales_interacciones = [i["canal"] for i in paquete["interacciones"]]
            assert "#general" in canales_interacciones
            assert "#preguntas" in canales_interacciones

            # Debe cerrar el cliente
            mock_cliente.close.assert_awaited_once()

    asyncio.run(_test())


def test_bot_lote_on_ready_sin_canales_cierra_limpiamente():
    """Valida que si no hay canales autorizados, on_ready cierra el cliente y no llama a procesar_actividad."""
    async def _test():
        servidor = crear_mock_servidor(id_servidor=12345, canales=[])
        mock_cliente = MagicMock()
        mock_cliente.user = "BotTest#0001"
        mock_cliente.guilds = [servidor]
        mock_cliente.close = AsyncMock()

        with patch("bot_lote.cliente", mock_cliente), \
             patch("bot_lote.ID_SERVIDOR", "99999"), \
             patch("bot_lote.procesar_actividad") as mock_proc:

            await bot_lote.on_ready()

            mock_proc.assert_not_called()
            mock_cliente.close.assert_awaited_once()

    asyncio.run(_test())


def test_bot_lote_on_ready_multiples_servidores_sin_id_servidor(capsys):
    """Valida que si hay múltiples servidores sin ID_SERVIDOR se emite un aviso en consola."""
    async def _test():
        s1 = crear_mock_servidor(id_servidor=111, canales=[])
        s2 = crear_mock_servidor(id_servidor=222, canales=[])
        mock_cliente = MagicMock()
        mock_cliente.user = "BotTest#0001"
        mock_cliente.guilds = [s1, s2]
        mock_cliente.close = AsyncMock()

        with patch("bot_lote.cliente", mock_cliente), \
             patch("bot_lote.ID_SERVIDOR", None), \
             patch("bot_lote.procesar_actividad") as mock_proc:

            await bot_lote.on_ready()
            mock_proc.assert_not_called()

    asyncio.run(_test())
    captured = capsys.readouterr()
    assert "Aviso: Hay más de un servidor conectado" in captured.out

