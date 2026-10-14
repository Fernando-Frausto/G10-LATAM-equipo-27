import os
import pytest
from unittest.mock import MagicMock, patch


@patch("psycopg2.connect")
def test_listar_interacciones_filtra_bots_en_sql(mock_connect, monkeypatch):
    """Valida que listar_interacciones ejecute una consulta SQL con filtros explícitos para excluir bots y webhooks."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://fake:fake@fake:5432/fake")
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_cursor.fetchall.return_value = []

    from base_datos import listar_interacciones
    listar_interacciones()

    assert mock_cursor.execute.called, "cursor.execute debió haber sido llamado"
    consulta_sql, _ = mock_cursor.execute.call_args[0]
    consulta_upper = consulta_sql.upper()

    # Debe contener filtros de autor para Spidey Boy#0000, patrones bot y #0000
    assert "SPIDEY BOY#0000" in consulta_upper, "La consulta debe excluir explícitamente a 'Spidey Boy#0000'"
    assert "%BOT%" in consulta_upper, "La consulta debe excluir coincidencias de '%bot%'"
    assert "%#0000" in consulta_upper, "La consulta debe excluir discriminadores '%#0000'"

    # Debe excluir tipos bot y webhook
    assert "BOT" in consulta_upper and "WEBHOOK" in consulta_upper, (
        "La consulta debe excluir los tipos 'bot' y 'webhook'"
    )


@patch("psycopg2.connect")
def test_listar_interacciones_combina_filtros_canal_y_bots(mock_connect, monkeypatch):
    """Valida que los filtros de canal y estado se combinen adecuadamente con la exclusión de bots en el WHERE."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://fake:fake@fake:5432/fake")
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_cursor.fetchall.return_value = []

    from base_datos import listar_interacciones
    listar_interacciones(canal="#general", estado="pendiente")

    consulta_sql, parametros = mock_cursor.execute.call_args[0]
    consulta_upper = consulta_sql.upper()

    assert "CANAL = %S" in consulta_upper
    assert "ESTADO = %S" in consulta_upper
    assert "%BOT%" in consulta_upper
    assert "#0000" in consulta_upper


@patch("psycopg2.connect")
def test_obtener_json_no_incluye_mensajes_de_bots(mock_connect, monkeypatch):
    """Valida que obtener_json en ver_json.py aplique y herede el filtrado limpio sin incluir mensajes de bots ni webhooks."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://fake:fake@fake:5432/fake")
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    filas_simuladas = [
        {"id": 1, "autor": "Spidey Boy#0000", "tipo": "webhook", "texto": "Alerta automática"},
        {"id": 2, "autor": "alumnos_bot#1234", "tipo": "bot", "texto": "Comando !ayuda"},
        {"id": 3, "autor": "estudiante_real", "tipo": "user", "texto": "Hola, tengo una consulta legítima"},
    ]
    mock_cursor.fetchall.return_value = filas_simuladas

    from ver_json import obtener_json
    resultado = obtener_json()

    # 1. La consulta SQL ejecutada debió solicitar exclusión de bots
    consulta_sql, _ = mock_cursor.execute.call_args[0]
    assert "%BOT%" in consulta_sql.upper(), "La consulta ejecutada debe contener exclusión de bots"

    # 2. El resultado estructurado no debe contener mensajes de bots
    autores_resultado = [msg.get("autor") for msg in resultado["interacciones"]]
    tipos_resultado = [msg.get("tipo") for msg in resultado["interacciones"]]
    assert "Spidey Boy#0000" not in autores_resultado
    assert "alumnos_bot#1234" not in autores_resultado
    assert "bot" not in tipos_resultado
    assert "webhook" not in tipos_resultado
    assert len(resultado["interacciones"]) == 1
    assert resultado["interacciones"][0]["autor"] == "estudiante_real"


@patch("psycopg2.connect")
def test_guardar_lote_ia_supabase_protege_estado_revision_pendiente(mock_connect, monkeypatch):
    """Valida que guardar_lote_ia_supabase incluya la cláusula WHERE lotes_ia_kpis.estado_revision = 'pendiente' en ON CONFLICT DO UPDATE."""
    monkeypatch.setenv("SUPABASE_DB_URL", "postgresql://fake:fake@fake:5432/fake")
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    paquete_prueba = {
        "aprobados": [
            {
                "id_mensaje": 101,
                "autor": "usuario1",
                "canal_origen": "#general",
                "comunidad": "Discord",
                "semana": "Semana_01",
                "fecha_envio": "2026-10-01T12:00:00Z",
                "fecha_extraccion": "2026-10-01T12:05:00Z",
                "modelo_ia": "gemma-4-31b-it",
                "texto_original": "Excelente contenido",
                "kpis": {
                    "relevancia": 85,
                    "sentimiento": "Positivo",
                    "temas_clave": "#curso",
                    "segmento": "Estudiantes",
                    "razonamiento": "Buen feedback",
                },
            }
        ],
        "descartados": [],
    }

    from base_datos import guardar_lote_ia_supabase
    guardar_lote_ia_supabase(paquete_prueba)

    # Buscar entre las llamadas a execute la que contiene 'INSERT INTO lotes_ia_kpis'
    inserts_ia = [
        call_args[0][0]
        for call_args in mock_cursor.execute.call_args_list
        if "INSERT INTO lotes_ia_kpis" in call_args[0][0]
    ]

    assert len(inserts_ia) > 0, "Debe ejecutarse un INSERT INTO lotes_ia_kpis"
    sql_insert = inserts_ia[0]
    sql_insert_normalizado = " ".join(sql_insert.split())

    clausula_esperada = "WHERE lotes_ia_kpis.estado_revision IN ('pendiente', 'rechazado')"
    assert clausula_esperada in sql_insert_normalizado, (
        f"La sentencia ON CONFLICT DO UPDATE debe incluir la cláusula de protección: {clausula_esperada}"
    )
