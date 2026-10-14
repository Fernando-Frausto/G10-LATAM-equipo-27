import json
import pytest
from unittest.mock import MagicMock, patch


class MockRespuestaLLM:
    """Simula la respuesta estructurada de un LLM con método model_dump."""

    def __init__(self, relevancia, sentimiento="Positivo", temas_clave="#test", segmento="Devs", razonamiento="Justificación"):
        self.datos = {
            "relevancia": relevancia,
            "sentimiento": sentimiento,
            "temas_clave": temas_clave,
            "segmento": segmento,
            "razonamiento": razonamiento,
        }

    def model_dump(self):
        return self.datos


@pytest.fixture
def mensajes_muestra():
    return [
        {
            "id": 1,
            "autor": "usuario_uno",
            "canal": "#general",
            "origen_comunidad": "Discord",
            "enviado_en": "2026-10-01T10:00:00Z",
            "creado_en": "2026-10-01T10:05:00Z",
            "periodo_referencia": "Semana_01",
            "texto": "Mensaje de alto valor técnico y discusión profunda",
        },
        {
            "id": 2,
            "autor": "usuario_dos",
            "canal": "#general",
            "origen_comunidad": "Discord",
            "enviado_en": "2026-10-01T10:10:00Z",
            "creado_en": "2026-10-01T10:15:00Z",
            "periodo_referencia": "Semana_01",
            "texto": "Hola buenas tardes",
        },
        {
            "id": 3,
            "autor": "usuario_tres",
            "canal": "#dudas",
            "origen_comunidad": "Discord",
            "enviado_en": "2026-10-01T10:20:00Z",
            "creado_en": "2026-10-01T10:25:00Z",
            "periodo_referencia": "Semana_01",
            "texto": "Consulta técnica sobre despliegue en la nube",
        },
    ]


def test_evaluacion_exitosa_lote_completo_clasificacion_umbral(monkeypatch, tmp_path, mensajes_muestra):
    """Valida evaluación exitosa de lote completo y clasificación por umbral (>=70 aprobados, <70 descartados)."""
    monkeypatch.chdir(tmp_path)

    from evaluador_lotes import evaluar_lote

    mock_modulo = MagicMock()
    mock_modulo.cadena.invoke.side_effect = [
        MockRespuestaLLM(relevancia=85),  # >= 70 -> aprobados
        MockRespuestaLLM(relevancia=45),  # < 70 -> descartados
    ]

    with patch("base_datos.guardar_lote_ia_supabase", return_value=2) as mock_supabase, \
         patch("evaluador_lotes.importlib.import_module", return_value=mock_modulo), \
         patch("evaluador_lotes.importlib.reload", return_value=mock_modulo):

        resultado = evaluar_lote(
            mensajes=mensajes_muestra[:2],
            nombre_modulo_cerebro="cerebro_ia",
            nombre_cerebro_legible="Groq",
            limite=2,
        )

        assert resultado["exito"] is True
        assert resultado["total_evaluados"] == 2
        assert resultado["exitosos"] == 2
        assert resultado["fallidos"] == 0
        assert len(resultado["aprobados"]) == 1
        assert len(resultado["descartados"]) == 1
        assert resultado["aprobados"][0]["id_mensaje"] == 1
        assert resultado["descartados"][0]["id_mensaje"] == 2
        assert resultado["guardados_supabase"] == 2
        assert mock_supabase.called

        # Verificar persistencia en archivo local
        archivo_salida = tmp_path / "resultados_kpis.json"
        assert archivo_salida.exists()
        datos_guardados = json.loads(archivo_salida.read_text(encoding="utf-8"))
        assert len(datos_guardados["aprobados"]) == 1
        assert len(datos_guardados["descartados"]) == 1


def test_resiliencia_fallos_individuales_continua_y_guarda(monkeypatch, tmp_path, mensajes_muestra):
    """Valida resiliencia ante excepciones por mensaje: captura error, continúa lote y persiste exitosos."""
    monkeypatch.chdir(tmp_path)

    from evaluador_lotes import evaluar_lote

    mock_modulo = MagicMock()
    mock_modulo.cadena.invoke.side_effect = [
        MockRespuestaLLM(relevancia=90),           # Exitoso (aprobado)
        Exception("Rate limit 429: Too Many Requests"),  # Fallo individual
        MockRespuestaLLM(relevancia=30),           # Exitoso (descartado)
    ]

    with patch("base_datos.guardar_lote_ia_supabase", return_value=2) as mock_supabase, \
         patch("evaluador_lotes.importlib.import_module", return_value=mock_modulo), \
         patch("evaluador_lotes.importlib.reload", return_value=mock_modulo):

        resultado = evaluar_lote(
            mensajes=mensajes_muestra,
            nombre_modulo_cerebro="cerebro_ia",
            nombre_cerebro_legible="Groq",
        )

        assert resultado["exito"] is True
        assert resultado["total_evaluados"] == 3
        assert resultado["exitosos"] == 2
        assert resultado["fallidos"] == 1
        assert len(resultado["errores"]) == 1
        assert "Rate limit 429" in resultado["errores"][0]
        assert len(resultado["aprobados"]) == 1
        assert len(resultado["descartados"]) == 1

        # Verifica que el archivo local contenga únicamente los exitosos
        archivo_salida = tmp_path / "resultados_kpis.json"
        assert archivo_salida.exists()
        datos_guardados = json.loads(archivo_salida.read_text(encoding="utf-8"))
        assert len(datos_guardados["aprobados"]) == 1
        assert len(datos_guardados["descartados"]) == 1
        assert mock_supabase.called


def test_proteccion_100_por_ciento_fallos_no_sobrescribe_archivo(monkeypatch, tmp_path, mensajes_muestra):
    """Valida que ante fallo del 100% de mensajes, resultados_kpis.json NO sea sobrescrito y reporte exito=False."""
    monkeypatch.chdir(tmp_path)

    archivo_salida = tmp_path / "resultados_kpis.json"
    contenido_previo = json.dumps({"aprobados": [{"id_mensaje": 999}], "descartados": []})
    archivo_salida.write_text(contenido_previo, encoding="utf-8")

    from evaluador_lotes import evaluar_lote

    mock_modulo = MagicMock()
    mock_modulo.cadena.invoke.side_effect = [
        Exception("Service Unavailable 503"),
        Exception("Connection Timeout"),
    ]

    with patch("base_datos.guardar_lote_ia_supabase") as mock_supabase, \
         patch("evaluador_lotes.importlib.import_module", return_value=mock_modulo), \
         patch("evaluador_lotes.importlib.reload", return_value=mock_modulo):

        resultado = evaluar_lote(
            mensajes=mensajes_muestra[:2],
            nombre_modulo_cerebro="cerebro_ia",
            nombre_cerebro_legible="Groq",
        )

        assert resultado["exito"] is False
        assert resultado["total_evaluados"] == 2
        assert resultado["exitosos"] == 0
        assert resultado["fallidos"] == 2
        assert len(resultado["errores"]) == 2
        assert not mock_supabase.called

        # El archivo original NO debe haber cambiado ni haber sido sobrescrito con listas vacías
        assert archivo_salida.read_text(encoding="utf-8") == contenido_previo


def test_callback_progreso_invocado_correctamente(monkeypatch, tmp_path, mensajes_muestra):
    """Valida la invocación progresiva del callback de progreso con (paso, total)."""
    monkeypatch.chdir(tmp_path)

    from evaluador_lotes import evaluar_lote

    mock_modulo = MagicMock()
    mock_modulo.cadena.invoke.side_effect = [
        MockRespuestaLLM(relevancia=80),
        MockRespuestaLLM(relevancia=60),
        MockRespuestaLLM(relevancia=70),
    ]

    mock_callback = MagicMock()

    with patch("base_datos.guardar_lote_ia_supabase", return_value=3), \
         patch("evaluador_lotes.importlib.import_module", return_value=mock_modulo), \
         patch("evaluador_lotes.importlib.reload", return_value=mock_modulo):

        evaluar_lote(
            mensajes=mensajes_muestra,
            nombre_modulo_cerebro="cerebro_ia",
            nombre_cerebro_legible="Groq",
            callback_progreso=mock_callback,
        )

        assert mock_callback.call_count == 3
        mock_callback.assert_any_call(1, 3)
        mock_callback.assert_any_call(2, 3)
        mock_callback.assert_any_call(3, 3)
