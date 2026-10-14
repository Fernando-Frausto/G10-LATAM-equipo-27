import json
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from api import app

client = TestClient(app)


@patch("psycopg2.connect")
def test_guardar_lote_ia_asigna_estados_pendiente_y_rechazado(mock_connect, monkeypatch):
    """Valida que guardar_lote_ia_supabase asigne explícitamente estado_revision='pendiente' a los aprobados y 'rechazado' a los descartados."""
    monkeypatch.setenv("SUPABASE_DB_URL", "postgresql://fake:fake@fake:5432/fake")
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    paquete = {
        "aprobados": [
            {
                "id_mensaje": 10,
                "autor": "user1",
                "canal_origen": "#general",
                "texto_original": "Mensaje relevante",
                "kpis": {"relevancia": 80, "sentimiento": "Positivo"},
            }
        ],
        "descartados": [
            {
                "id_mensaje": 20,
                "autor": "user2",
                "canal_origen": "#general",
                "texto_original": "Mensaje descartado",
                "kpis": {"relevancia": 30, "sentimiento": "Neutral"},
            }
        ],
    }

    from base_datos import guardar_lote_ia_supabase
    guardar_lote_ia_supabase(paquete)

    # Filtrar las llamadas a cursor.execute que corresponden a INSERT INTO lotes_ia_kpis
    inserts = [
        call_args[0]
        for call_args in mock_cursor.execute.call_args_list
        if "INSERT INTO lotes_ia_kpis" in call_args[0][0]
    ]

    assert len(inserts) == 2, "Deben haberse ejecutado 2 inserciones (1 aprobado, 1 descartado)"

    # Comprobar que en la consulta SQL se incluya estado_revision en las columnas del INSERT
    sql_insert = inserts[0][0]
    assert "estado_revision" in sql_insert, "La consulta INSERT debe incluir explícitamente la columna estado_revision"

    # Comprobar los parámetros de la primera inserción (aprobados) -> 'pendiente'
    params_aprobado = inserts[0][1]
    assert "pendiente" in params_aprobado, "El mensaje aprobado debe tener 'pendiente' en sus parámetros de inserción"

    # Comprobar los parámetros de la segunda inserción (descartados) -> 'rechazado'
    params_descartado = inserts[1][1]
    assert "rechazado" in params_descartado, "El mensaje descartado debe tener 'rechazado' en sus parámetros de inserción"


@patch("psycopg2.connect")
def test_guardar_lote_ia_on_conflict_protege_estados_humanos(mock_connect, monkeypatch):
    """Valida que ON CONFLICT DO UPDATE incluya estado_revision=EXCLUDED.estado_revision y la condición WHERE lotes_ia_kpis.estado_revision IN ('pendiente', 'rechazado')."""
    monkeypatch.setenv("SUPABASE_DB_URL", "postgresql://fake:fake@fake:5432/fake")
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    paquete = {
        "aprobados": [
            {
                "id_mensaje": 1,
                "autor": "user",
                "texto_original": "texto",
                "kpis": {"relevancia": 90},
            }
        ],
        "descartados": [],
    }

    from base_datos import guardar_lote_ia_supabase
    guardar_lote_ia_supabase(paquete)

    inserts = [
        call_args[0][0]
        for call_args in mock_cursor.execute.call_args_list
        if "INSERT INTO lotes_ia_kpis" in call_args[0][0]
    ]
    assert len(inserts) > 0
    sql_normalizado = " ".join(inserts[0].split())

    # Debe incluir actualización de estado_revision
    assert "estado_revision = EXCLUDED.estado_revision" in sql_normalizado, (
        "DO UPDATE SET debe incluir 'estado_revision = EXCLUDED.estado_revision'"
    )

    # Debe incluir la cláusula de protección condicional con IN ('pendiente', 'rechazado')
    assert "WHERE lotes_ia_kpis.estado_revision IN ('pendiente', 'rechazado')" in sql_normalizado, (
        "La cláusula de protección debe ser: WHERE lotes_ia_kpis.estado_revision IN ('pendiente', 'rechazado')"
    )


def test_evaluador_lotes_inyecta_clave_estado_revision(monkeypatch, tmp_path):
    """Valida que evaluar_lote inyecte 'estado_revision': 'pendiente' en aprobados y 'rechazado' en descartados."""
    monkeypatch.chdir(tmp_path)

    from evaluador_lotes import evaluar_lote

    class MockRespuesta:
        def __init__(self, rel):
            self.rel = rel

        def model_dump(self):
            return {"relevancia": self.rel, "sentimiento": "Positivo"}

    mock_modulo = MagicMock()
    mock_modulo.cadena.invoke.side_effect = [
        MockRespuesta(85),  # >= 70 -> aprobado
        MockRespuesta(40),  # < 70 -> descartado
    ]

    mensajes = [
        {"id": 1, "autor": "u1", "canal": "#gen", "texto": "muy relevante"},
        {"id": 2, "autor": "u2", "canal": "#gen", "texto": "poco relevante"},
    ]

    with patch("base_datos.guardar_lote_ia_supabase", return_value=2), \
         patch("evaluador_lotes.importlib.import_module", return_value=mock_modulo), \
         patch("evaluador_lotes.importlib.reload", return_value=mock_modulo):

        resultado = evaluar_lote(mensajes, "cerebro_ia", "Groq")

        assert len(resultado["aprobados"]) == 1
        assert resultado["aprobados"][0].get("estado_revision") == "pendiente", (
            "Los mensajes aprobados deben tener 'estado_revision': 'pendiente'"
        )

        assert len(resultado["descartados"]) == 1
        assert resultado["descartados"][0].get("estado_revision") == "rechazado", (
            "Los mensajes descartados deben tener 'estado_revision': 'rechazado'"
        )


@patch("psycopg2.connect")
def test_obtener_lote_kpis_jerarquia_hitl_soberania_humana(mock_connect, monkeypatch):
    """Valida que en obtener_lote_kpis_supabase la decisión humana prevalezca sobre la de IA."""
    monkeypatch.setenv("SUPABASE_DB_URL", "postgresql://fake:fake@fake:5432/fake")
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    filas_bd = [
        {
            "id_mensaje": 1,
            "autor": "user1",
            "decision_ia": "descartado",
            "estado_revision": "aprobado",
            "relevancia": 40,
            "texto_original": "Recuperado por humano",
        },
        {
            "id_mensaje": 2,
            "autor": "user2",
            "decision_ia": "descartado",
            "estado_revision": "procesado",
            "relevancia": 35,
            "texto_original": "Procesado por humano",
        },
        {
            "id_mensaje": 3,
            "autor": "user3",
            "decision_ia": "aprobado",
            "estado_revision": "desaprobado",
            "relevancia": 95,
            "texto_original": "Rechazado por humano aunque score alto",
        },
        {
            "id_mensaje": 4,
            "autor": "user4",
            "decision_ia": "aprobado",
            "estado_revision": "rechazado",
            "relevancia": 90,
            "texto_original": "Rechazado explícito",
        },
    ]
    mock_cursor.fetchall.return_value = filas_bd

    from base_datos import obtener_lote_kpis_supabase
    resultado = obtener_lote_kpis_supabase()

    ids_aprobados = [m["id_mensaje"] for m in resultado["aprobados"]]
    ids_descartados = [m["id_mensaje"] for m in resultado["descartados"]]

    # Mensajes 1 y 2 deben estar en aprobados por decisión humana
    assert 1 in ids_aprobados, "Mensaje 1 (estado_revision='aprobado') debe estar en aprobados"
    assert 2 in ids_aprobados, "Mensaje 2 (estado_revision='procesado') debe estar en aprobados"
    for m in resultado["aprobados"]:
        assert "copy_final" in m, "Todos los aprobados deben tener copy_final"

    # Mensajes 3 y 4 deben estar en descartados por decisión humana
    assert 3 in ids_descartados, "Mensaje 3 (estado_revision='desaprobado') debe estar en descartados"
    assert 4 in ids_descartados, "Mensaje 4 (estado_revision='rechazado') debe estar en descartados"


def test_api_kpis_jerarquia_hitl_soberania_humana():
    """Valida que GET /api/kpis en api.py respete la jerarquía HITL devolviendo la clasificación humana."""
    filas_bd = [
        {
            "id_mensaje": 100,
            "autor": "user1",
            "decision_ia": "descartado",
            "estado_revision": "aprobado",
            "relevancia": 50,
            "texto_original": "Recuperado por Enoc",
        },
        {
            "id_mensaje": 200,
            "autor": "user2",
            "decision_ia": "aprobado",
            "estado_revision": "desaprobado",
            "relevancia": 88,
            "texto_original": "Rechazado por Enoc",
        },
    ]

    with patch("base_datos.obtener_lote_kpis_supabase", return_value=filas_bd, create=True):
        response = client.get("/api/kpis")

        assert response.status_code == 200
        data = response.json()

        ids_aprobados = [m["id_mensaje"] for m in data["aprobados"]]
        ids_descartados = [m["id_mensaje"] for m in data["descartados"]]

        assert 100 in ids_aprobados, "Mensaje con estado_revision='aprobado' debe estar en aprobados"
        assert 200 in ids_descartados, "Mensaje con estado_revision='desaprobado' debe estar en descartados"
        assert data["aprobados"][0]["id_mensaje"] == 100
        assert "copy_final" in data["aprobados"][0]
