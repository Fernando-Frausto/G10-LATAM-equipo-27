import os
import importlib
import pytest
from unittest.mock import patch
from pydantic import ValidationError


def test_prompts_ia_modulo_existe_y_exporta_componentes():
    """Valida la existencia e importación de FormatoSalida, template_filtro y prompt_filtro desde prompts_ia."""
    import prompts_ia

    assert hasattr(prompts_ia, "FormatoSalida"), "prompts_ia debe exportar FormatoSalida"
    assert hasattr(prompts_ia, "template_filtro"), "prompts_ia debe exportar template_filtro"
    assert hasattr(prompts_ia, "prompt_filtro"), "prompts_ia debe exportar prompt_filtro"


def test_formato_salida_validacion_campos():
    """Valida que FormatoSalida contenga y valide los campos requeridos (relevancia, sentimiento, temas_clave, segmento, razonamiento)."""
    from prompts_ia import FormatoSalida

    instancia = FormatoSalida(
        relevancia=85,
        sentimiento="Positivo",
        temas_clave="#python #backend",
        segmento="Desarrolladores",
        razonamiento="Mensaje con propuesta técnica detallada.",
    )

    assert instancia.relevancia == 85
    assert instancia.sentimiento == "Positivo"
    assert instancia.temas_clave == "#python #backend"
    assert instancia.segmento == "Desarrolladores"
    assert instancia.razonamiento == "Mensaje con propuesta técnica detallada."

    # Falla si falta algún campo obligatorio
    with pytest.raises(ValidationError):
        FormatoSalida(relevancia=90, sentimiento="Positivo")

    # Falla si el tipo cuantitativo de relevancia es incompatible
    with pytest.raises(ValidationError):
        FormatoSalida(
            relevancia="muy_alto",
            sentimiento="Positivo",
            temas_clave="#test",
            segmento="Comunidad",
            razonamiento="Falla esperada.",
        )


def test_template_filtro_y_prompt_filtro_estructura():
    """Valida que template_filtro y prompt_filtro configuren adecuadamente las variables texto y canal."""
    import prompts_ia

    assert "{texto}" in prompts_ia.template_filtro
    assert "{canal}" in prompts_ia.template_filtro
    assert set(prompts_ia.prompt_filtro.input_variables) == {"texto", "canal"}


@pytest.mark.parametrize(
    "env_vars,modelo_esperado",
    [
        ({"GEMMA_MODEL": "  gemma-custom-model  ", "GOOGLE_MODEL": "otro"}, "gemma-custom-model"),
        ({"GEMMA_MODEL": "   ", "GOOGLE_MODEL": "  google-fallback-model  "}, "google-fallback-model"),
        ({"GEMMA_MODEL": "   ", "GOOGLE_MODEL": "   "}, "gemma-4-31b-it"),
        ({}, "gemma-4-31b-it"),
    ],
)
def test_cerebro_ia_gemma_4_resolucion_modelo(monkeypatch, env_vars, modelo_esperado):
    """Valida que cerebro_ia_gemma_4 resuelva GEMMA_MODEL independientemente, con fallback a GOOGLE_MODEL o default institucional."""
    monkeypatch.delenv("GEMMA_MODEL", raising=False)
    monkeypatch.delenv("GOOGLE_MODEL", raising=False)
    for k, v in env_vars.items():
        monkeypatch.setenv(k, v)

    with patch("langchain_google_genai.ChatGoogleGenerativeAI"):
        import cerebro_ia_gemma_4
        importlib.reload(cerebro_ia_gemma_4)
        assert (
            cerebro_ia_gemma_4._modelo == modelo_esperado
        ), f"Esperado: {modelo_esperado}, obtenido: {cerebro_ia_gemma_4._modelo}"


@pytest.mark.parametrize(
    "env_vars,modelo_esperado",
    [
        ({"GEMINI_MODEL": "  gemini-custom-flash  ", "GOOGLE_MODEL": "otro"}, "gemini-custom-flash"),
        ({"GEMINI_MODEL": "   ", "GOOGLE_MODEL": "  google-fallback-model  "}, "google-fallback-model"),
        ({"GEMINI_MODEL": "   ", "GOOGLE_MODEL": "   "}, "gemini-3.5-flash-lite"),
        ({}, "gemini-3.5-flash-lite"),
    ],
)
def test_cerebro_ia_gemini_flash_resolucion_modelo(monkeypatch, env_vars, modelo_esperado):
    """Valida que cerebro_ia_gemini_flash resuelva GEMINI_MODEL independientemente, con fallback a GOOGLE_MODEL o default institucional."""
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.delenv("GOOGLE_MODEL", raising=False)
    for k, v in env_vars.items():
        monkeypatch.setenv(k, v)

    with patch("langchain_google_genai.ChatGoogleGenerativeAI"):
        import cerebro_ia_gemini_flash
        importlib.reload(cerebro_ia_gemini_flash)
        assert (
            cerebro_ia_gemini_flash._modelo == modelo_esperado
        ), f"Esperado: {modelo_esperado}, obtenido: {cerebro_ia_gemini_flash._modelo}"


def test_motores_usan_componentes_centralizados_prompts_ia():
    """Valida que los motores cerebro_ia, cerebro_ia_gemma_4 y cerebro_ia_gemini_flash importen FormatoSalida y prompt_filtro desde prompts_ia."""
    import prompts_ia
    import cerebro_ia
    import cerebro_ia_gemma_4
    import cerebro_ia_gemini_flash

    assert cerebro_ia.FormatoSalida is prompts_ia.FormatoSalida
    assert cerebro_ia.prompt_filtro is prompts_ia.prompt_filtro
    assert cerebro_ia_gemma_4.FormatoSalida is prompts_ia.FormatoSalida
    assert cerebro_ia_gemma_4.prompt_filtro is prompts_ia.prompt_filtro
    assert cerebro_ia_gemini_flash.FormatoSalida is prompts_ia.FormatoSalida
    assert cerebro_ia_gemini_flash.prompt_filtro is prompts_ia.prompt_filtro
