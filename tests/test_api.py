import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from api import app

client = TestClient(app)


def test_get_kpis_desde_supabase_con_copy_final():
    """Valida que GET /api/kpis consulte Supabase y reconstruya {"aprobados": [...], "descartados": [...]} con copy_final."""
    filas_simuladas = [
        {
            "id_mensaje": 101,
            "autor": "usuario_aprobado",
            "canal_origen": "#general",
            "comunidad": "Discord",
            "semana": "Semana_01",
            "fecha_envio": "2026-10-01T12:00:00Z",
            "fecha_extraccion": "2026-10-01T12:05:00Z",
            "modelo_ia": "Groq",
            "texto_original": "Propuesta técnica muy completa",
            "relevancia": 85,
            "sentimiento": "Positivo",
            "temas_clave": "#tech",
            "segmento": "Devs",
            "razonamiento": "Aporta valor profundo",
            "decision_ia": "aprobado",
            "estado_revision": "pendiente",
        },
        {
            "id_mensaje": 102,
            "autor": "usuario_descartado",
            "canal_origen": "#general",
            "comunidad": "Discord",
            "semana": "Semana_01",
            "fecha_envio": "2026-10-01T12:10:00Z",
            "fecha_extraccion": "2026-10-01T12:15:00Z",
            "modelo_ia": "Groq",
            "texto_original": "Hola a todos",
            "relevancia": 25,
            "sentimiento": "Neutral",
            "temas_clave": "N/A",
            "segmento": "N/A",
            "razonamiento": "Saludo simple",
            "decision_ia": "descartado",
            "estado_revision": "rechazado",
        },
    ]

    with patch("base_datos.obtener_lote_kpis_supabase", return_value=filas_simuladas, create=True) as mock_sb:
        response = client.get("/api/kpis")

        assert mock_sb.called, "GET /api/kpis debe consultar obtener_lote_kpis_supabase prioritariamente"
        assert response.status_code == 200
        data = response.json()
        assert "aprobados" in data
        assert "descartados" in data
        assert len(data["aprobados"]) == 1
        assert len(data["descartados"]) == 1
        assert data["aprobados"][0]["id_mensaje"] == 101
        assert "copy_final" in data["aprobados"][0]
        assert data["aprobados"][0]["copy_final"] == "Pendiente de redacción por Enoc..."
        assert data["descartados"][0]["id_mensaje"] == 102


def test_get_kpis_fallback_archivo_local(tmp_path, monkeypatch):
    """Valida que GET /api/kpis recurra a resultados_kpis.json si Supabase no está disponible."""
    monkeypatch.chdir(tmp_path)

    archivo = tmp_path / "resultados_kpis.json"
    archivo.write_text(
        json.dumps({
            "aprobados": [
                {
                    "id_mensaje": 201,
                    "autor": "usuario_local",
                    "texto_original": "Feedback local",
                    "kpis": {"relevancia": 75, "sentimiento": "Positivo"},
                }
            ],
            "descartados": [
                {
                    "id_mensaje": 202,
                    "autor": "usuario_local_dos",
                    "texto_original": "Queja breve",
                    "kpis": {"relevancia": 40, "sentimiento": "Negativo"},
                }
            ],
        }),
        encoding="utf-8",
    )

    with patch("base_datos.obtener_lote_kpis_supabase", return_value=None, create=True):
        response = client.get("/api/kpis")

        assert response.status_code == 200
        data = response.json()
        assert len(data["aprobados"]) == 1
        assert len(data["descartados"]) == 1
        assert data["aprobados"][0]["id_mensaje"] == 201
        assert "copy_final" in data["aprobados"][0]


def test_get_kpis_base_y_archivo_vacios_retorna_estructura_canonica(tmp_path, monkeypatch):
    """Valida que ante base vacía/nula y sin archivo local, retorne 200 con {"aprobados": [], "descartados": []} (NUNCA [])."""
    monkeypatch.chdir(tmp_path)

    with patch("base_datos.obtener_lote_kpis_supabase", return_value=None, create=True):
        response = client.get("/api/kpis")

        assert response.status_code == 200
        data = response.json()
        assert data == {"aprobados": [], "descartados": []}, f"Esperado dict canónico pero se obtuvo: {data}"


def test_get_reporte_semanal_desde_supabase():
    """Valida que GET /api/reporte-semanal consulte Supabase y retorne el reporte consolidado más reciente."""
    reporte_esperado = {
        "etiqueta": "2026-semana-42",
        "metadata": {"total_mensajes": 15},
        "metricas": {"relevancia_promedio": 78.5},
    }

    with patch("base_datos.obtener_ultimo_reporte_semanal_supabase", return_value=reporte_esperado, create=True) as mock_rep:
        response = client.get("/api/reporte-semanal")

        assert mock_rep.called, "GET /api/reporte-semanal debe consultar obtener_ultimo_reporte_semanal_supabase prioritariamente"
        assert response.status_code == 200
        data = response.json()
        assert data["etiqueta"] == "2026-semana-42"
        assert data["metadata"]["total_mensajes"] == 15


def test_get_reporte_semanal_fallback_archivos_locales(tmp_path, monkeypatch):
    """Valida que GET /api/reporte-semanal recurra al archivo más reciente en reportes/ si Supabase no está disponible."""
    monkeypatch.chdir(tmp_path)

    dir_reportes = tmp_path / "reportes"
    dir_reportes.mkdir()

    (dir_reportes / "2026-semana-40.json").write_text(
        json.dumps({"etiqueta": "2026-semana-40", "version": 1}), encoding="utf-8"
    )
    (dir_reportes / "2026-semana-41.json").write_text(
        json.dumps({"etiqueta": "2026-semana-41", "version": 2}), encoding="utf-8"
    )

    with patch("base_datos.obtener_ultimo_reporte_semanal_supabase", return_value=None, create=True):
        response = client.get("/api/reporte-semanal")

        assert response.status_code == 200
        data = response.json()
        assert data["etiqueta"] == "2026-semana-41"


def test_get_reporte_semanal_inexistente_retorna_404(tmp_path, monkeypatch):
    """Valida que GET /api/reporte-semanal retorne HTTP 404 estructurado cuando no hay reportes en BD ni en filesystem."""
    monkeypatch.chdir(tmp_path)

    with patch("base_datos.obtener_ultimo_reporte_semanal_supabase", return_value=None, create=True):
        response = client.get("/api/reporte-semanal")

        assert response.status_code == 404, f"Se esperaba código HTTP 404 pero se obtuvo: {response.status_code}"
        data = response.json()
        assert "error" in data
