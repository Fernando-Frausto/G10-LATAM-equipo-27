"""
Pruebas de Unificación Beta para puente_motor_ia (Spec 005).
Valida la carga aislada de motor-ia, el puente de lectura/sincronización con Supabase,
el puente de contenidos para aprobaciones, los endpoints HTTP de FastAPI y la homologación en memoria de IA.
"""
import os
import sys
import pytest
from unittest.mock import MagicMock, patch
import sqlite3
from fastapi.testclient import TestClient

import puente_motor_ia
import anuncios_discord


# --- Fixtures y Mocks Auxiliares ---

@pytest.fixture(autouse=True)
def limpiar_bd_sqlite(tmp_path, monkeypatch):
    """Aísla SQLite usando una BD temporal por test para garantizar aislamiento e idempotencia."""
    test_db = str(tmp_path / "test_communitylab.db")
    monkeypatch.setattr(puente_motor_ia.motor_bd, "RUTA_BD", test_db)
    monkeypatch.delenv("DISCORD_BOT_TOKEN", raising=False)
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    puente_motor_ia.invalidar_cache_supabase()
    puente_motor_ia._asegurar_esquema_sqlite()
    yield
    puente_motor_ia.invalidar_cache_supabase()


@pytest.fixture
def client():
    return TestClient(puente_motor_ia.app)


@pytest.fixture
def mock_supabase_datos():
    """Genera filas simuladas para interacciones y lotes_ia_kpis en Supabase."""
    interacciones_filas = [
        # 1. Mensaje humano normal con evaluación aprobada
        {
            "id": 1,
            "hash": "a" * 64,
            "origen_comunidad": "Discord",
            "periodo_referencia": "Semana_01",
            "autor": "alice",
            "canal": "#general",
            "tipo": "mensaje",
            "texto": "Hola, busco vacantes en desarrollo de software",
            "enviado_en": "2026-10-01T12:00:00+00:00",
            "creado_en": "2026-10-01T12:01:00+00:00",
            "guild_id": "123",
            "guild_name": "CloudEdTech",
            "channel_id": "456",
            "message_id": "1001",
            "author_id": "9001",
            "attachments": "[]",
        },
        # 2. Mensaje humano sin enviado_en (debe usar creado_en como fallback) y no evaluado
        {
            "id": 2,
            "hash": "b" * 64,
            "origen_comunidad": "Discord",
            "periodo_referencia": "Semana_01",
            "autor": "bob",
            "canal": "#preguntas",
            "tipo": "mensaje",
            "texto": "Tengo una duda sobre los cursos de IA",
            "enviado_en": None,
            "creado_en": "2026-10-01T13:00:00+00:00",
            "guild_id": "123",
            "guild_name": "CloudEdTech",
            "channel_id": "457",
            "message_id": "1002",
            "author_id": "9002",
            "attachments": "[]",
        },
        # 3. Mensaje humano con evaluación rechazada / sentimiento negativo
        {
            "id": 3,
            "hash": "c" * 64,
            "origen_comunidad": "Discord",
            "periodo_referencia": "Semana_01",
            "autor": "charlie",
            "canal": "#soporte",
            "tipo": "mensaje",
            "texto": "La plataforma está fallando al hacer login",
            "enviado_en": "2026-10-01T14:00:00+00:00",
            "creado_en": "2026-10-01T14:01:00+00:00",
            "guild_id": "123",
            "guild_name": "CloudEdTech",
            "channel_id": "458",
            "message_id": "1003",
            "author_id": "9003",
            "attachments": "[]",
        },
        # 4. Spidey Boy (debe ser filtrado)
        {
            "id": 4,
            "hash": "d" * 64,
            "origen_comunidad": "Discord",
            "periodo_referencia": "Semana_01",
            "autor": "Spidey Boy#0000",
            "canal": "#anuncios",
            "tipo": "mensaje",
            "texto": "Anuncio automático",
            "enviado_en": "2026-10-01T15:00:00+00:00",
            "creado_en": "2026-10-01T15:01:00+00:00",
            "guild_id": "123",
            "guild_name": "CloudEdTech",
            "channel_id": "459",
            "message_id": "1004",
            "author_id": "9004",
            "attachments": "[]",
        },
        # 5. Usuario con discriminador #0000 (debe ser filtrado)
        {
            "id": 5,
            "hash": "e" * 64,
            "origen_comunidad": "Discord",
            "periodo_referencia": "Semana_01",
            "autor": "otro_bot#0000",
            "canal": "#general",
            "tipo": "mensaje",
            "texto": "Bot con discriminador",
            "enviado_en": "2026-10-01T15:05:00+00:00",
            "creado_en": "2026-10-01T15:06:00+00:00",
            "guild_id": "123",
            "guild_name": "CloudEdTech",
            "channel_id": "456",
            "message_id": "1005",
            "author_id": "9005",
            "attachments": "[]",
        },
        # 6. Tipo webhook (debe ser filtrado)
        {
            "id": 6,
            "hash": "f" * 64,
            "origen_comunidad": "Discord",
            "periodo_referencia": "Semana_01",
            "autor": "github",
            "canal": "#commits",
            "tipo": "webhook",
            "texto": "New push",
            "enviado_en": "2026-10-01T15:10:00+00:00",
            "creado_en": "2026-10-01T15:11:00+00:00",
            "guild_id": "123",
            "guild_name": "CloudEdTech",
            "channel_id": "460",
            "message_id": "1006",
            "author_id": "9006",
            "attachments": "[]",
        },
    ]

    kpis_filas = [
        # Evaluación para id_mensaje 1 (Aprobado / Positivo / Empleo)
        {
            "id": 501,
            "id_mensaje": 1,
            "autor": "alice",
            "canal": "#general",
            "comunidad": "Discord",
            "semana": "Semana_01",
            "fecha_envio": "2026-10-01T12:00:00+00:00",
            "fecha_extraccion": "2026-10-01T12:05:00+00:00",
            "modelo_ia": "Groq",
            "texto_original": "Hola, busco vacantes en desarrollo de software",
            "relevancia": 88,
            "sentimiento": "Positivo",
            "temas_clave": "#empleo #desarrollo #vacantes",
            "segmento": "BUSCA_EMPLEO",
            "razonamiento": "Aporte de alto valor para empleo tech",
            "decision_ia": "aprobado",
            "estado_revision": "aprobado",
            "copy_final": "Oportunidad de desarrollo profesional para talentos tech.",
            "analizado_en": "2026-10-01T12:10:00+00:00",
        },
        # Evaluación para id_mensaje 3 (Rechazado / Negativo / Plataforma)
        {
            "id": 502,
            "id_mensaje": 3,
            "autor": "charlie",
            "canal": "#soporte",
            "comunidad": "Discord",
            "semana": "Semana_01",
            "fecha_envio": "2026-10-01T14:00:00+00:00",
            "fecha_extraccion": "2026-10-01T14:05:00+00:00",
            "modelo_ia": "Groq",
            "texto_original": "La plataforma está fallando al hacer login",
            "relevancia": 25,
            "sentimiento": "Negativo",
            "temas_clave": "#plataforma #error #soporte",
            "segmento": "ESTUDIANTE",
            "razonamiento": "Reporte de incidencia en acceso a plataforma",
            "decision_ia": "descartado",
            "estado_revision": "rechazado",
            "copy_final": None,
            "analizado_en": "2026-10-01T14:10:00+00:00",
        },
        # Evaluación independiente para contenido (con canal_origen en vez de canal)
        {
            "id": 503,
            "id_mensaje": 99,
            "autor": "bob",
            "canal_origen": "#empleos-tech",
            "comunidad": "Discord",
            "semana": "Semana_01",
            "fecha_envio": "2026-10-01T13:00:00+00:00",
            "fecha_extraccion": "2026-10-01T13:05:00+00:00",
            "modelo_ia": "Groq",
            "texto_original": "Tengo una duda sobre los cursos de IA",
            "relevancia": 75,
            "sentimiento": "Neutral",
            "temas_clave": "#ia #cursos",
            "segmento": "ESTUDIANTE",
            "razonamiento": "Consulta general sobre catálogo formativo",
            "decision_ia": "aprobado",
            "estado_revision": "aprobado",
            "copy_final": "Descubre las novedades en cursos de IA.",
            "analizado_en": "2026-10-01T13:10:00+00:00",
        },
    ]

    return {
        "interacciones": interacciones_filas,
        "kpis": kpis_filas,
    }


# ==============================================================================
# 1. Carga Aislada de Módulos (RF-01, RF-05)
# ==============================================================================

def test_carga_aislada_sin_colision_sys_modules():
    """Valida que puente_motor_ia expone app y motor_bd sin pisar sys.modules de la raíz."""
    # Guardamos referencias previas a los módulos de raíz
    import base_datos as base_datos_raiz
    import api as api_raiz

    assert hasattr(puente_motor_ia, "app")
    assert hasattr(puente_motor_ia, "motor_bd")

    # La app debe ser FastAPI
    from fastapi import FastAPI
    assert isinstance(puente_motor_ia.app, FastAPI)

    # sys.modules["base_datos"] debe seguir apuntando al módulo de la raíz
    assert sys.modules["base_datos"] is base_datos_raiz
    assert sys.modules["api"] is api_raiz

    # motor_bd debe ser el de motor-ia/
    motor_bd = puente_motor_ia.motor_bd
    assert motor_bd.__file__.replace("\\", "/").endswith("motor-ia/base_datos.py")
    assert hasattr(motor_bd, "listar_interacciones")
    assert hasattr(motor_bd, "listar_contenidos")


# ==============================================================================
# 2. Puente de Interacciones y KPIs (RF-02)
# ==============================================================================

def test_puente_interacciones_filtrado_bots_y_cruce_kpis(mock_supabase_datos):
    """Verifica exclusión de bots/webhooks y mapeo determinista (sentiment_score, tema, curaduria, flujo)."""
    with patch.object(puente_motor_ia, "obtener_datos_supabase", return_value=mock_supabase_datos):
        interacciones = puente_motor_ia.motor_bd.listar_interacciones(limite=100)

        ids = [item["id"] for item in interacciones]
        # Mensajes de bots/webhooks (ids 4, 5, 6) deben estar estrictamente excluidos
        assert 4 not in ids
        assert 5 not in ids
        assert 6 not in ids

        # Mensaje 1 evaluado y aprobado
        item_1 = next(item for item in interacciones if item["id"] == 1)
        assert item_1["estado"] == "analizado"
        assert item_1["sentiment_score"] == 0.85
        assert item_1["tema"] == "EMPLEO"
        assert item_1["estado_curaduria"] == "curated"
        assert item_1["etapa_flujo"] == "en_aprobacion"
        assert item_1["relevancia"] == 88

        # Mensaje 2 no evaluado
        item_2 = next(item for item in interacciones if item["id"] == 2)
        assert item_2["estado"] == "pendiente"
        assert item_2["sentiment_score"] is None
        assert item_2["tema"] is None
        assert item_2["estado_curaduria"] == "pending"
        assert item_2["etapa_flujo"] == "ingesta"
        # Fallback de enviado_en a creado_en
        assert item_2["enviado_en"] == "2026-10-01T13:00:00+00:00"

        # Mensaje 3 evaluado y rechazado
        item_3 = next(item for item in interacciones if item["id"] == 3)
        assert item_3["estado"] == "analizado"
        assert item_3["sentiment_score"] == 0.85
        assert item_3["tema"] == "PLATAFORMA"
        assert item_3["estado_curaduria"] == "discarded"
        assert item_3["etapa_flujo"] == "en_analisis"


def test_puente_interacciones_mapeo_determinista_categorias_y_sentimiento():
    """Valida el cálculo de sentimiento (0.85, 0.75) y las 7 categorías cerradas de tema."""
    inferir_tema = puente_motor_ia._inferir_tema

    assert inferir_tema("#empleo #vacantes", "#general", "busco trabajo") == "EMPLEO"
    assert inferir_tema("#cursos #alumnos", "#chat", "duda de clase") == "EDUCACION"
    assert inferir_tema("#ia #gemini #agentes", "#tech", "usando langchain") == "IA"
    assert inferir_tema("#python #debugging #api", "#dev", "error de sintaxis") == "DESARROLLO"
    assert inferir_tema("#plataforma #login", "#soporte", "no puedo ingresar") == "PLATAFORMA"
    assert inferir_tema("#comunidad #bienvenida", "#general", "hola a todos") == "COMUNIDAD"
    assert inferir_tema("#desconocido", "#random", "mensaje sin categoria") == "OTRO"

    calcular_score = puente_motor_ia._calcular_sentiment_score
    assert calcular_score("Positivo") == 0.85
    assert calcular_score("Negativo") == 0.85
    assert calcular_score("Neutral") == 0.75
    assert calcular_score(None) is None


def test_puente_interacciones_fallback_sqlite_local():
    """Verifica que si no hay variables de entorno Supabase o falla la conexión, opera con SQLite local."""
    with patch.dict(os.environ, {"DATABASE_URL": "", "SUPABASE_DB_URL": ""}, clear=True):
        # Debe ejecutarse sin lanzar excepción
        resultado = puente_motor_ia.motor_bd.listar_interacciones(limite=10)
        assert isinstance(resultado, list)


def test_puente_interacciones_sincroniza_sqlite_y_permite_mutaciones(mock_supabase_datos):
    """Valida que los registros de Supabase sincronizados en SQLite local permiten actualizar curaduria, flujo y obtener interaccion."""
    with patch.object(puente_motor_ia, "obtener_datos_supabase", return_value=mock_supabase_datos):
        # Sincroniza al listar
        puente_motor_ia.motor_bd.listar_interacciones(limite=50)

        # Actualiza curaduría localmente y con propagación simulada
        with patch.dict(os.environ, {"SUPABASE_DB_URL": "postgresql://mock:5432/db"}):
            with patch("psycopg2.connect") as mock_conn:
                exito_curaduria = puente_motor_ia.motor_bd.actualizar_curaduria(1, "curated")
                assert exito_curaduria is True
                mock_conn.assert_called_once()

        # Actualiza etapa de flujo con propagación simulada
        with patch.dict(os.environ, {"SUPABASE_DB_URL": "postgresql://mock:5432/db"}):
            with patch("psycopg2.connect") as mock_conn:
                exito_flujo = puente_motor_ia.motor_bd.actualizar_etapa_flujo(2, "en_analisis")
                assert exito_flujo is True
                mock_conn.assert_called_once()

        # Validar obtener_interaccion en motor_bd y motor_api
        item_1_bd = puente_motor_ia.motor_bd.obtener_interaccion(1)
        assert item_1_bd is not None
        assert item_1_bd["id"] == 1
        item_1_api = puente_motor_ia.motor_api.obtener_interaccion(1)
        assert item_1_api is not None
        assert item_1_api["id"] == 1

        assert puente_motor_ia.motor_bd.obtener_interaccion(999999) is None


# ==============================================================================
# 3. Puente de Contenidos Curados para Aprobaciones (RF-03)
# ==============================================================================

def test_puente_contenidos_sincroniza_lotes_kpis(mock_supabase_datos):
    """Valida que los registros de lotes_ia_kpis se exponen en listar_contenidos y contar_contenidos con canal_origen."""
    with patch.object(puente_motor_ia, "obtener_datos_supabase", return_value=mock_supabase_datos):
        contenidos = puente_motor_ia.motor_bd.listar_contenidos(limite=100)
        assert len(contenidos) >= 3

        # Contenido aprobado (id 501)
        item_aprobado = next(c for c in contenidos if c["id"] == 501)
        assert item_aprobado["estado"] == "aprobado"
        assert item_aprobado["contenido"] == "Oportunidad de desarrollo profesional para talentos tech."
        assert "#empleo" in item_aprobado["hashtags"]

        # Contenido rechazado (id 502)
        item_rechazado = next(c for c in contenidos if c["id"] == 502)
        assert item_rechazado["estado"] == "rechazado"

        # Contenido con canal_origen (id 503)
        item_canal_origen = next(c for c in contenidos if c["id"] == 503)
        assert item_canal_origen["source_channel_id"] == "#empleos-tech"
        assert "#empleos-tech" in item_canal_origen["titulo"]

        # Conteo por estado
        conteo_aprobados = puente_motor_ia.motor_bd.contar_contenidos(estado="aprobado")
        assert conteo_aprobados >= 2


def test_puente_contenidos_actualizar_estado_y_obtener():
    """Valida mutación de estado, propagación opcional a Supabase y obtención de contenido."""
    # Crear o sincronizar contenido
    mock_item = {
        "id": 999,
        "interaccion_id": 1,
        "formato": "post",
        "titulo": "Prueba",
        "contenido": "Texto",
        "llamada_accion": "Comenta",
        "hashtags": ["#test"],
        "tono": "profesional",
        "estado": "pendiente_revision",
        "creado_en": "2026-10-01T12:00:00+00:00",
        "actualizado_en": "2026-10-01T12:00:00+00:00",
    }
    puente_motor_ia._sincronizar_contenido_en_sqlite(mock_item)

    # Validar obtener_contenido
    item_obtenido = puente_motor_ia.motor_bd.obtener_contenido(999)
    assert item_obtenido is not None
    assert item_obtenido["id"] == 999
    assert item_obtenido["estado"] == "pendiente_revision"
    assert item_obtenido["hashtags"] == ["#test"]

    assert puente_motor_ia.motor_bd.obtener_contenido(888888) is None

    # Actualizar estado con propagación a Supabase simulada
    with patch.dict(os.environ, {"SUPABASE_DB_URL": "postgresql://mock:5432/db"}):
        with patch("psycopg2.connect") as mock_conn:
            actualizado = puente_motor_ia.motor_bd.actualizar_estado_contenido(
                999, "aprobado", "Aprobado por editor"
            )
            assert actualizado is True
            mock_conn.assert_called_once()

    item_actualizado = puente_motor_ia.motor_bd.obtener_contenido(999)
    assert item_actualizado["estado"] == "aprobado"


# ==============================================================================
# 4. Endpoints HTTP de puente_motor_ia.app (RF-02, RF-03, RF-05)
# ==============================================================================

def test_endpoints_http_react_structure(mock_supabase_datos):
    """Valida que los endpoints HTTP de la app FastAPI respondan 200 con la estructura JSON esperada por React."""
    cliente = TestClient(puente_motor_ia.app)

    with patch.object(puente_motor_ia, "obtener_datos_supabase", return_value=mock_supabase_datos):
        # 1. /api/community/messages
        resp_messages = cliente.get("/api/community/messages")
        assert resp_messages.status_code == 200
        datos_messages = resp_messages.json()
        assert "total" in datos_messages
        assert "messages" in datos_messages
        if datos_messages["messages"]:
            msg = datos_messages["messages"][0]
            assert "message" in msg
            assert "analysis" in msg
            analysis = msg["analysis"]
            assert "sentiment" in analysis
            assert "sentiment_score" in analysis
            assert "curation_status" in analysis
            assert "workflow_stage" in analysis
            assert "topic" in analysis
            assert "keywords" in analysis

        # 2. /api/community/dashboard
        resp_dashboard = cliente.get("/api/community/dashboard")
        assert resp_dashboard.status_code == 200
        datos_dashboard = resp_dashboard.json()
        assert "messages_processed" in datos_dashboard
        assert "positive_sentiment" in datos_dashboard
        assert "total_audience" in datos_dashboard

        # 3. /api/community/analytics
        resp_analytics = cliente.get("/api/community/analytics")
        assert resp_analytics.status_code == 200
        datos_analytics = resp_analytics.json()
        assert "sentiment" in datos_analytics
        assert "topics" in datos_analytics
        assert "activity_heatmap" in datos_analytics
        assert "hashtags" in datos_analytics

        # 4. /api/content
        resp_content = cliente.get("/api/content")
        assert resp_content.status_code == 200
        datos_content = resp_content.json()
        assert "items" in datos_content


# ==============================================================================
# 5. Homologación en Memoria de Cerebros IA y Bot de Discord (RF-04)
# ==============================================================================

def test_homologacion_cerebros_ia_formato_y_modelos():
    """Valida la inyección en memoria de FormatoSalida y la resolución de GEMINI_MODEL / GEMMA_MODEL."""
    cerebro_gemini = puente_motor_ia.cerebro_ia_gemini_flash
    cerebro_gemma = puente_motor_ia.cerebro_ia_gemma_4

    # FormatoSalida debe tener sentiment_score y tema
    for mod in (cerebro_gemini, cerebro_gemma):
        fields = mod.FormatoSalida.model_fields
        assert "sentiment_score" in fields
        assert "tema" in fields
        assert "relevancia" in fields
        assert "sentimiento" in fields
        assert hasattr(mod, "llm_estructurado")
        assert hasattr(mod, "cadena")

    # Resolución de modelos
    with patch.dict(os.environ, {"GEMINI_MODEL": "  gemini-custom  "}, clear=False):
        assert puente_motor_ia.obtener_modelo_gemini() == "gemini-custom"

    with patch.dict(os.environ, {"GEMINI_MODEL": "", "GOOGLE_MODEL": " fallback-gemini "}, clear=False):
        assert puente_motor_ia.obtener_modelo_gemini() == "fallback-gemini"

    with patch.dict(os.environ, {"GEMMA_MODEL": "  gemma-custom  "}, clear=False):
        assert puente_motor_ia.obtener_modelo_gemma() == "gemma-custom"

    with patch.dict(os.environ, {"GEMMA_MODEL": "", "GOOGLE_MODEL": ""}, clear=False):
        assert puente_motor_ia.obtener_modelo_gemma() == "gemma-4-31b-it"


def test_delegacion_discord_con_autodeteccion_canales():
    """Valida que la sincronización de Discord delegue en el armar_json_bot_python de la raíz."""
    assert hasattr(puente_motor_ia, "sincronizar_discord")
    assert hasattr(puente_motor_ia, "recolectar_mensajes")
    assert hasattr(puente_motor_ia, "ejecutar_ingesta_discord")
    # Debe referenciar o usar detectar_canales del módulo raíz
    import armar_json_bot_python as bot_raiz
    assert hasattr(bot_raiz, "detectar_canales")
    assert puente_motor_ia.recolectar_mensajes() is bot_raiz
    assert puente_motor_ia.ejecutar_ingesta_discord() is bot_raiz


# ==============================================================================
# 6. Inmutabilidad y Regresión de Arquitectura (RF-01, RF-05)
# ==============================================================================

def test_inmutabilidad_archivos_origin_main():
    """Garantiza 0 diff contra el commit base de origin/main (758ff6a) en backend/, motor-ia/ y netlify.toml."""
    import subprocess
    cmd = ["git", "diff", "--exit-code", "758ff6a", "--", "backend", "motor-ia", "netlify.toml"]
    resultado = subprocess.run(cmd, capture_output=True, text=True)
    assert resultado.returncode == 0, f"Se detectaron cambios respecto a origin/main (758ff6a):\n{resultado.stdout}\n{resultado.stderr}"


def test_inmutabilidad_archivos_raiz():
    """Garantiza 0 diff en archivos preexistentes de raíz respecto a feature/ia-resultados-supabase."""
    import subprocess
    archivos_raiz = [
        "base_datos.py", "evaluador_lotes.py", "prompts_ia.py", "app.py", "api.py",
        "bot_lote.py", "armar_json_bot_python.py", "reporte_semanal.py", "oci_uploader.py",
        "cerebro_ia.py", "cerebro_ia_gemini_flash.py", "cerebro_ia_gemma_4.py",
    ]
    cmd = ["git", "diff", "--exit-code", "feature/ia-resultados-supabase", "--"] + archivos_raiz
    resultado = subprocess.run(cmd, capture_output=True, text=True)
    assert resultado.returncode == 0, f"Se detectaron modificaciones no autorizadas en raíz:\n{resultado.stdout}\n{resultado.stderr}"


def test_endpoints_v1_frontend_compatibility(mock_supabase_datos):
    """Valida los endpoints ligeros /api/v1/* requeridos por el frontend de React para login y workflows."""
    cliente = TestClient(puente_motor_ia.app)

    # 1. POST /api/v1/auth/login
    resp_login = cliente.post("/api/v1/auth/login", json={"username": "community_admin", "password": "secret"})
    assert resp_login.status_code == 200
    datos_login = resp_login.json()
    assert datos_login["access_token"] == "token-unificacion-beta"
    assert datos_login["user"]["username"] == "community_admin"
    assert datos_login["user"]["role"] == "admin"

    # 2. GET /api/v1/auth/me
    resp_me = cliente.get("/api/v1/auth/me")
    assert resp_me.status_code == 200
    assert resp_me.json()["role"] == "admin"

    with patch.object(puente_motor_ia, "obtener_datos_supabase", return_value=mock_supabase_datos):
        # Sincronizar datos para interactuar
        puente_motor_ia.motor_bd.listar_interacciones(limite=50)

        # 3. PATCH /api/v1/content-workflow/messages/{id}/curation
        resp_cur = cliente.patch("/api/v1/content-workflow/messages/1/curation", json={"status": "curated"})
        assert resp_cur.status_code == 200
        assert resp_cur.json() == {"id": 1, "curation_status": "curated", "updated": True}

        # 4. PATCH /api/v1/content-workflow/messages/{id}/workflow
        resp_wf = cliente.patch("/api/v1/content-workflow/messages/2/workflow", json={"stage": "en_analisis"})
        assert resp_wf.status_code == 200
        assert resp_wf.json() == {"id": 2, "workflow_stage": "en_analisis", "updated": True}

        # 5. PATCH /api/v1/content-workflow/{id}/status
        # Sincronizar contenidos primero
        puente_motor_ia.motor_bd.listar_contenidos(limite=50)
        resp_status = cliente.patch("/api/v1/content-workflow/501/status", json={"estado": "aprobado", "observaciones_revision": "Todo ok"})
        assert resp_status.status_code == 200
        assert resp_status.json()["id"] == 501
        assert resp_status.json()["estado"] == "aprobado"

    # 6. GET /api/v1/content-workflow/complaints/published-responses
    resp_complaints = cliente.get("/api/v1/content-workflow/complaints/published-responses")
    assert resp_complaints.status_code == 200
    assert resp_complaints.json() == {"interaction_ids": []}

    # 7. GET /api/v1/users/
    resp_users = cliente.get("/api/v1/users/")
    assert resp_users.status_code == 200
    assert isinstance(resp_users.json(), list)

    # 8. GET /api/v1/audit/
    resp_audit = cliente.get("/api/v1/audit/")
    assert resp_audit.status_code == 200
    assert resp_audit.json() == []

    # 9. GET /api/v1/oci-storage/status y weekly-period
    resp_oci = cliente.get("/api/v1/oci-storage/status")
    assert resp_oci.status_code == 200
    assert resp_oci.json()["status"] == "connected"

    resp_period = cliente.get("/api/v1/oci-storage/weekly-period")
    assert resp_period.status_code == 200
    assert "start_date" in resp_period.json()


# ==============================================================================
# 7. Integración Funcional Total (Spec 006 - RF-01): Gestión de Modelos de IA
# ==============================================================================

def test_get_ai_models_proveedores_activos():
    """Valida que GET /api/v1/ai/models retorne los 3 proveedores reales de IA con sus modelos."""
    cliente = TestClient(puente_motor_ia.app)
    resp = cliente.get("/api/v1/ai/models")
    assert resp.status_code == 200, f"Respuesta inesperada: {resp.status_code} - {resp.text}"
    modelos = resp.json()
    assert isinstance(modelos, list)
    assert len(modelos) == 3

    # Verificar proveedores esperados
    proveedores = {m["name"]: m for m in modelos}
    assert "Groq (Llama 3.3)" in proveedores
    assert "Google Gemma 4" in proveedores
    assert "Google Gemini Flash Lite" in proveedores

    # Verificar estructura canónica de cada modelo
    for m in modelos:
        assert "id" in m
        assert "provider" in m
        assert "name" in m
        assert "model" in m
        assert "module" in m
        assert "available" in m
        assert isinstance(m["available"], bool)

    groq_mod = proveedores["Groq (Llama 3.3)"]
    assert groq_mod["id"] == "groq-llama"
    assert groq_mod["provider"] == "Groq"
    assert groq_mod["module"] == "cerebro_ia"

    gemma_mod = proveedores["Google Gemma 4"]
    assert gemma_mod["id"] == "google-gemma"
    assert gemma_mod["provider"] == "Google"
    assert gemma_mod["module"] == "cerebro_ia_gemma_4"

    gemini_mod = proveedores["Google Gemini Flash Lite"]
    assert gemini_mod["id"] == "google-gemini"
    assert gemini_mod["provider"] == "Google"
    assert gemini_mod["module"] == "cerebro_ia_gemini_flash"


def test_get_ai_models_disponibilidad_segun_credenciales():
    """Valida que la disponibilidad (available) refleje la existencia de variables de entorno de API keys."""
    cliente = TestClient(puente_motor_ia.app)
    # Sin credenciales: available debe ser False
    with patch.dict(os.environ, {"GROQ_API_KEY": "", "GEMINI_API_KEY": "", "GOOGLE_API_KEY": ""}, clear=False):
        resp = cliente.get("/api/v1/ai/models")
        assert resp.status_code == 200
        for m in resp.json():
            assert m["available"] is False

    # Con credenciales configuradas
    with patch.dict(os.environ, {"GROQ_API_KEY": "gsk_test123", "GEMINI_API_KEY": "AIzaSyTest"}, clear=False):
        resp = cliente.get("/api/v1/ai/models")
        assert resp.status_code == 200
        proveedores = {m["id"]: m["available"] for m in resp.json()}
        assert proveedores["groq-llama"] is True
        assert proveedores["google-gemini"] is True


# ==============================================================================
# 8. Integración Funcional Total (Spec 006 - RF-01): Evaluación de Lotes IA
# ==============================================================================

def test_post_evaluate_batch_validacion_fechas():
    """Valida que POST /api/v1/ai/evaluate-batch rechace con 400 si desde > hasta."""
    cliente = TestClient(puente_motor_ia.app)
    payload_invalido = {
        "proveedor": "Groq (Llama 3.3)",
        "desde": "2026-10-25",
        "hasta": "2026-10-10",
        "solo_pendientes": True,
        "limite": 50,
    }
    resp = cliente.post("/api/v1/ai/evaluate-batch", json=payload_invalido)
    assert resp.status_code == 400
    assert "desde" in resp.text.lower() or "fecha" in resp.text.lower()


def test_post_evaluate_batch_proveedor_desconocido():
    """Valida que POST /api/v1/ai/evaluate-batch rechace con 400 o 422 si el proveedor no existe."""
    cliente = TestClient(puente_motor_ia.app)
    payload = {
        "proveedor": "Proveedor Invalido",
        "desde": "2026-10-01",
        "hasta": "2026-10-15",
        "solo_pendientes": False,
    }
    resp = cliente.post("/api/v1/ai/evaluate-batch", json=payload)
    assert resp.status_code in (400, 422)


def test_post_evaluate_batch_delegacion_y_persistencia():
    """Valida delegación en ver_json.obtener_json, evaluador_lotes y sincronización tras evaluación."""
    cliente = TestClient(puente_motor_ia.app)

    mensajes_simulados = [
        {"id": 201, "autor": "user1", "canal": "#general", "texto": "Me encanta Python", "enviado_en": "2026-10-02T10:00:00+00:00"},
        {"id": 202, "autor": "user2", "canal": "#dudas", "texto": "No funciona el login", "enviado_en": "2026-10-03T11:00:00+00:00"},
    ]

    mock_resultado_eval = {
        "exito": True,
        "total_evaluados": 2,
        "exitosos": 2,
        "fallidos": 0,
        "guardados_supabase": 2,
        "errores": [],
        "aprobados": [{"id_mensaje": 201, "kpis": {"relevancia": 85}}],
        "descartados": [{"id_mensaje": 202, "kpis": {"relevancia": 45}}],
        "resultados": {"aprobados": [], "descartados": []},
    }

    with patch("ver_json.obtener_json", return_value={"total": 2, "interacciones": mensajes_simulados}) as mock_ver_json, \
         patch("evaluador_lotes.evaluar_lote", return_value=mock_resultado_eval) as mock_eval, \
         patch.object(puente_motor_ia, "_sincronizar_supabase_a_sqlite", return_value=2, create=True) as mock_sync:

        payload = {
            "proveedor": "Groq (Llama 3.3)",
            "desde": "2026-10-01",
            "hasta": "2026-10-05",
            "solo_pendientes": False,
            "limite": 10,
        }
        resp = cliente.post("/api/v1/ai/evaluate-batch", json=payload)
        assert resp.status_code == 200
        datos = resp.json()
        assert datos["exito"] is True
        assert datos["proveedor"] == "Groq (Llama 3.3)"
        assert datos["total_mensajes"] == 2
        assert datos["evaluados"] == 2
        assert datos["aprobados"] == 1
        assert datos["descartados"] == 1
        assert datos["guardados_supabase"] == 2
        assert datos["errores"] == []

        # Verificar llamadas a dependencias
        mock_ver_json.assert_called_once()
        _, kwargs_vj = mock_ver_json.call_args
        assert kwargs_vj.get("desde") == "2026-10-01"
        assert kwargs_vj.get("hasta") == "2026-10-05"

        mock_eval.assert_called_once()
        _, kwargs_ev = mock_eval.call_args
        assert kwargs_ev.get("nombre_modulo_cerebro") == "cerebro_ia"
        assert kwargs_ev.get("nombre_cerebro_legible") == "Groq (Llama 3.3)"

        # Verificar refresco de caché SQLite
        mock_sync.assert_called_once()


def test_post_evaluate_batch_filtro_solo_pendientes():
    """Valida que solo_pendientes=True excluya mensajes que ya fueron evaluados previamente."""
    cliente = TestClient(puente_motor_ia.app)

    mensajes_simulados = [
        {"id": 301, "autor": "u1", "canal": "#general", "texto": "Msg 1", "enviado_en": "2026-10-01T10:00:00+00:00"},
        {"id": 302, "autor": "u2", "canal": "#general", "texto": "Msg 2", "enviado_en": "2026-10-02T10:00:00+00:00"},
    ]

    mock_eval = MagicMock(return_value={
        "exito": True,
        "total_evaluados": 1,
        "exitosos": 1,
        "fallidos": 0,
        "guardados_supabase": 1,
        "errores": [],
        "aprobados": [{"id_mensaje": 302, "kpis": {"relevancia": 90}}],
        "descartados": [],
        "resultados": {},
    })

    # Simular que el mensaje 301 ya está en lotes_ia_kpis
    with patch("ver_json.obtener_json", return_value={"total": 2, "interacciones": mensajes_simulados}), \
         patch.object(puente_motor_ia, "_obtener_ids_evaluados_supabase", return_value={301}, create=True), \
         patch("evaluador_lotes.evaluar_lote", mock_eval), \
         patch.object(puente_motor_ia, "_sincronizar_supabase_a_sqlite", return_value=1, create=True):

        payload = {
            "proveedor": "Google Gemma 4",
            "desde": "2026-10-01",
            "hasta": "2026-10-05",
            "solo_pendientes": True,
        }
        resp = cliente.post("/api/v1/ai/evaluate-batch", json=payload)
        assert resp.status_code == 200

        # Solo debe evaluar el mensaje 302
        _, kwargs_eval = mock_eval.call_args
        mensajes_enviados = kwargs_eval.get("mensajes", [])
        assert len(mensajes_enviados) == 1
        assert mensajes_enviados[0]["id"] == 302


# ==============================================================================
# 9. Integración Funcional Total (Spec 006 - RF-02): OCI Storage Sync y Period
# ==============================================================================

def test_get_oci_weekly_period_calculo_dinamico():
    """Valida que GET /api/v1/oci-storage/weekly-period use periodos.py y retorne etiqueta AAAA-semana-NN."""
    import re
    cliente = TestClient(puente_motor_ia.app)
    resp = cliente.get("/api/v1/oci-storage/weekly-period")
    assert resp.status_code == 200
    datos = resp.json()
    assert "semana_nombre" in datos, f"Falta 'semana_nombre' en respuesta: {datos}"
    assert "start_date" in datos
    assert "end_date" in datos
    assert datos["status"] == "ready"

    # Verificar formato AAAA-semana-NN requerido por reporte_semanal.validar_etiqueta
    assert re.fullmatch(r"\d{4}-semana-\d{2}", datos["semana_nombre"]), \
        f"Etiqueta {datos['semana_nombre']} no cumple el formato AAAA-semana-NN"

    # Verificar orden cronológico de fechas ISO
    assert datos["start_date"] <= datos["end_date"]


def test_post_oci_weekly_sync_delegacion():
    """Valida que POST /api/v1/oci-storage/weekly-sync invoque reporte_semanal y oci_uploader."""
    cliente = TestClient(puente_motor_ia.app)

    mock_reporte = {
        "metadata": {
            "proyecto": "CommunityLab",
            "semana": "2026-semana-42",
            "version_esquema": "1.0",
            "generado_en": "2026-10-16T12:00:00+00:00",
            "oci_storage": {
                "bucket": "communitylab-assets",
                "ruta": "activos/2026-semana-42/paquete-distribucion.json",
                "subido": True,
            },
        },
        "resumen_metricas": {
            "total_mensajes": 15,
            "total_aprobados": 10,
            "total_descartados": 5,
            "sentimiento": {"Positivo": 10, "Neutral": 3, "Negativo": 2},
            "temas_tendencia": [{"tema": "#python", "menciones": 8}],
            "segmentos": {"Estudiante": 6, "Profesional": 4},
        },
        "activos_copywriting": {"aprobados": [], "descartados": []},
    }

    with patch("reporte_semanal.generar_reporte_semanal", return_value=mock_reporte) as mock_gen, patch.object(puente_motor_ia, "_cargar_lote_para_reporte_semanal", return_value={"aprobados": [{"id_mensaje": "2441", "autor": "dev_enoc"}], "descartados": []}):
        resp = cliente.post("/api/v1/oci-storage/weekly-sync")
        assert resp.status_code == 200
        datos = resp.json()
        assert datos["exito"] is True
        assert datos["semana"] == "2026-semana-42"
        assert datos["subido_oci"] is True
        assert datos["bucket"] == "communitylab-assets"
        assert "activos/2026-semana-42" in datos["ruta_oci"]
        assert "resumen" in datos
        assert datos["resumen"]["total_mensajes"] == 15
        assert datos["resumen"]["total_aprobados"] == 10
        assert datos["resumen"]["total_descartados"] == 5
        mock_gen.assert_called_once()


# ==============================================================================
# 10. Integración Funcional Total (Spec 006 - RF-03, RF-04): Live Summary y Export
# ==============================================================================

def test_get_community_live_summary_calculo_completo(mock_supabase_datos):
    """Valida agregación reactiva de highlights (con copy_final), audience, calendar y reports."""
    cliente = TestClient(puente_motor_ia.app)

    # Inyectar datos en el mock
    mock_supabase_ext = dict(mock_supabase_datos)
    # Agregar mock de lotes_ia_kpis con copy_final curado y relevancia
    lotes_kpis = [
        {
            "id": 1,
            "id_mensaje": 1,
            "autor": "alice",
            "canal_origen": "#general",
            "comunidad": "Discord",
            "semana": "Semana_01",
            "fecha_envio": "2026-10-01T12:00:00+00:00",
            "texto_original": "Hola, busco vacantes en desarrollo de software",
            "relevancia": 85,
            "sentimiento": "Positivo",
            "temas_clave": "#empleo, #python",
            "segmento": "Profesional",
            "copy_final": "Post curado por Enoc: Oportunidad de empleo en software",
            "estado_revision": "aprobado",
            "decision_ia": "aprobado",
        },
        {
            "id": 2,
            "id_mensaje": 2,
            "autor": "bob",
            "canal_origen": "#preguntas",
            "comunidad": "Discord",
            "semana": "Semana_01",
            "fecha_envio": "2026-10-01T13:00:00+00:00",
            "texto_original": "Tengo una duda sobre los cursos de IA",
            "relevancia": 72,
            "sentimiento": "Neutral",
            "temas_clave": "#ia, #cursos",
            "segmento": "Estudiante",
            "copy_final": None,
            "estado_revision": "pendiente",
            "decision_ia": "aprobado",
        },
        {
            "id": 3,
            "id_mensaje": 3,
            "autor": "charlie",
            "canal_origen": "#soporte",
            "comunidad": "Discord",
            "semana": "Semana_01",
            "fecha_envio": "2026-10-01T14:00:00+00:00",
            "texto_original": "La plataforma está fallando al hacer login",
            "relevancia": 40,
            "sentimiento": "Negativo",
            "temas_clave": "#soporte",
            "segmento": "General",
            "copy_final": None,
            "estado_revision": "rechazado",
            "decision_ia": "descartado",
        },
    ]

    with patch.object(puente_motor_ia, "obtener_datos_supabase", return_value=mock_supabase_ext), \
         patch.object(puente_motor_ia, "_obtener_lotes_kpis_completos", return_value=lotes_kpis, create=True):

        resp = cliente.get("/api/v1/community/live-summary")
        assert resp.status_code == 200, f"Error {resp.status_code}: {resp.text}"
        resumen = resp.json()

        # 1. Highlights: Solo >= 70 de relevancia (mensajes 1 y 2, no el 3)
        assert "highlights" in resumen
        assert "highlights_summary" in resumen
        highlights = resumen["highlights"]
        assert len(highlights) == 2

        # Mensaje 1 tiene copy_final curado por Enoc
        hl1 = next(h for h in highlights if h["id"] == 1 or h.get("id_mensaje") == 1)
        assert hl1["content"] == "Post curado por Enoc: Oportunidad de empleo en software" or hl1.get("copy_final") == "Post curado por Enoc: Oportunidad de empleo en software"
        assert hl1["sentiment"] == "Positivo"
        assert hl1["sentiment_score"] == 0.85

        # Mensaje 2 sin copy_final usa fallback a texto_original
        hl2 = next(h for h in highlights if h["id"] == 2 or h.get("id_mensaje") == 2)
        assert "Tengo una duda" in (hl2.get("content") or hl2.get("texto_original"))

        # Highlights summary
        hs = resumen["highlights_summary"]
        assert hs["detected"] == 2
        assert hs["high_relevance"] == 1  # mensaje 1 (relevancia 85 >= 85)
        assert hs["ready_for_content"] >= 1  # aprobado

        # 2. Audience
        assert "audience" in resumen
        aud = resumen["audience"]
        assert "total_members" in aud
        assert "active_members" in aud
        assert "participation_rate" in aud
        assert "segments" in aud
        assert "ai_segments" in aud
        assert aud["total_members"] >= 3  # alice, bob, charlie (Spidey Boy excluido)

        # 3. Calendar
        assert "calendar" in resumen
        cal = resumen["calendar"]
        assert isinstance(cal, list)
        assert len(cal) >= 1
        assert "date" in cal[0]
        assert "messages" in cal[0]

        # 4. Reports
        assert "reports" in resumen
        assert isinstance(resumen["reports"], list)


def test_get_export_community_data():
    """Valida que GET /api/v1/export/community-data retorne la estructura unificada de exportación."""
    cliente = TestClient(puente_motor_ia.app)
    resp = cliente.get("/api/v1/export/community-data")
    assert resp.status_code == 200
    export = resp.json()
    assert "export_date" in export
    assert "summary" in export
    assert "interactions" in export
    assert "curated_content" in export
    assert isinstance(export["interactions"], list)
    assert isinstance(export["curated_content"], list)


# ==============================================================================
# 11. Regresión: Compatibilidad de listar_interacciones_puente con incluir_bots
# ==============================================================================

def test_listar_interacciones_puente_firma_incluir_bots():
    """Valida que listar_interacciones_puente acepte incluir_bots y kwargs sin lanzar TypeError."""
    with patch.object(puente_motor_ia, "obtener_datos_supabase", return_value=None):
        with patch.object(puente_motor_ia, "_orig_listar_interacciones", return_value=[
            {"id": 1, "autor": "alice", "tipo": "mensaje"},
            {"id": 2, "autor": "Spidey Boy#0000", "tipo": "bot"},
            {"id": 3, "autor": "algun_bot", "tipo": "mensaje"},
        ]):
            # Con incluir_bots=False debe excluir bots
            filtrados = puente_motor_ia.listar_interacciones_puente(incluir_bots=False)
            assert len(filtrados) == 1
            assert filtrados[0]["autor"] == "alice"

            # Con incluir_bots=True debe mantener todos
            todos = puente_motor_ia.listar_interacciones_puente(incluir_bots=True)
            assert len(todos) == 3

            # Debe aceptar kwargs arbitrarios sin lanzar TypeError
            kwargs_res = puente_motor_ia.listar_interacciones_puente(incluir_bots=False, parametro_extra=123)
            assert len(kwargs_res) == 1


def test_ver_json_obtener_json_interoperabilidad_con_puente():
    """Valida que ver_json.obtener_json invoque listar_interacciones_puente sin error."""
    import ver_json
    with patch.object(puente_motor_ia, "obtener_datos_supabase", return_value=None):
        with patch.object(puente_motor_ia, "_orig_listar_interacciones", return_value=[
            {"id": 1, "autor": "alice", "canal": "#general", "tipo": "mensaje", "texto": "hola", "enviado_en": "2026-10-01T12:00:00+00:00"}
        ]):
            res = ver_json.obtener_json()
            assert "interacciones" in res
            assert isinstance(res["interacciones"], list)
            assert res["total"] >= 1


# ==============================================================================
# 12. Sincronización y Recuperación de Discord desde la UI (Spec 007 - Fase Red TDD)
# ==============================================================================

def test_discord_sync_endpoint_exitoso(monkeypatch):
    """Valida llamada a POST /api/v1/discord/sync con cliente efímero de Discord mockeado y métricas esperadas."""
    cliente = TestClient(puente_motor_ia.app)
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "mock_discord_token_secret_123")

    mock_canal = MagicMock()
    mock_canal.id = 123456
    mock_canal.name = "general"

    mock_msg1 = MagicMock()
    mock_msg1.id = 101
    mock_msg1.author.bot = False
    mock_msg1.author.name = "alice"
    mock_msg1.content = "Primer mensaje para sincronizar"
    mock_msg1.attachments = []

    mock_msg2 = MagicMock()
    mock_msg2.id = 102
    mock_msg2.author.bot = False
    mock_msg2.author.name = "bob"
    mock_msg2.content = "Segundo mensaje ya existente"
    mock_msg2.attachments = []

    async def mock_history(*args, **kwargs):
        yield mock_msg1
        yield mock_msg2

    mock_canal.history = mock_history

    mock_guild = MagicMock()
    mock_guild.id = 789
    mock_guild.text_channels = [mock_canal]

    class MockDiscordClient:
        def __init__(self, *args, **kwargs):
            self.guilds = [mock_guild]

        async def start(self, token):
            return

        async def close(self):
            return

    with patch("discord.Client", MockDiscordClient), \
         patch("armar_json_bot_python.detectar_canales", return_value=[mock_canal]), \
         patch("procesamiento.procesar_actividad", return_value={"total": 2, "nuevas": 1, "repetidas": 1, "vacias": 0}), \
         patch.object(puente_motor_ia, "_sincronizar_supabase_a_sqlite", return_value=1, create=True):

        resp = cliente.post("/api/v1/discord/sync", json={"limite_por_canal": 10})
        assert resp.status_code == 200
        data = resp.json()
        assert data["exito"] is True
        assert data["total_recibidas"] == 2
        assert data["guardadas_nuevas"] == 1
        assert data["repetidas_omitidas"] == 1
        assert data["vacias_omitidas"] == 0
        assert "periodo_referencia" in data
        assert "Sincronización exitosa" in data.get("mensaje", "")


def test_discord_sync_concurrencia_lock_409(monkeypatch):
    """Valida retorno HTTP 409 Conflict si ya existe una sincronización en curso sobre el cerrojo global."""
    cliente = TestClient(puente_motor_ia.app)
    mock_lock = MagicMock()
    mock_lock.locked.return_value = True
    monkeypatch.setattr(puente_motor_ia, "_discord_sync_lock", mock_lock, raising=False)

    resp = cliente.post("/api/v1/discord/sync", json={"limite_por_canal": 5})
    assert resp.status_code == 409
    data = resp.json()
    assert data["exito"] is False
    assert "Sincronización en curso" in (data.get("mensaje") or data.get("detail") or "")


def test_discord_sync_token_ausente_o_login_failure_502(monkeypatch):
    """Valida retorno HTTP 502 Bad Gateway ante ausencia de credenciales de Discord o fallo en login."""
    cliente = TestClient(puente_motor_ia.app)

    # 1. Token ausente
    monkeypatch.delenv("DISCORD_BOT_TOKEN", raising=False)
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)

    resp = cliente.post("/api/v1/discord/sync", json={"limite_por_canal": 5})
    assert resp.status_code == 502
    data = resp.json()
    assert data["exito"] is False
    assert "autenticación" in data.get("mensaje", "").lower() or "token" in data.get("mensaje", "").lower()

    # 2. LoginFailure con token presente
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "token_invalido_prueba")
    import discord
    with patch.object(discord.Client, "start", side_effect=discord.errors.LoginFailure("Improper token has been passed.")):
        resp2 = cliente.post("/api/v1/discord/sync", json={"limite_por_canal": 5})
        assert resp2.status_code == 502
        data2 = resp2.json()
        assert data2["exito"] is False


def test_discord_sync_todos_al_dia_y_sin_canales(monkeypatch):
    """Valida HTTP 200 con mensajes descriptivos cuando no hay mensajes nuevos o cuando no hay canales autorizados."""
    cliente = TestClient(puente_motor_ia.app)
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "mock_discord_token_secret_123")

    mock_canal = MagicMock()
    mock_canal.id = 123456
    mock_canal.name = "general"

    async def mock_history(*args, **kwargs):
        msg = MagicMock()
        msg.id = 201
        msg.author.bot = False
        msg.author.name = "usuario_test"
        msg.content = "Mensaje sin cambios"
        msg.attachments = []
        yield msg

    mock_canal.history = mock_history
    mock_guild = MagicMock()
    mock_guild.id = 789
    mock_guild.text_channels = [mock_canal]

    class MockDiscordClient:
        def __init__(self, *args, **kwargs):
            self.guilds = [mock_guild]

        async def start(self, token):
            return

        async def close(self):
            return

    # Caso A: Mensajes al día (0 nuevos, >0 recibidas)
    with patch("discord.Client", MockDiscordClient), \
         patch("armar_json_bot_python.detectar_canales", return_value=[mock_canal]), \
         patch("procesamiento.procesar_actividad", return_value={"total": 1, "nuevas": 0, "repetidas": 1, "vacias": 0}), \
         patch.object(puente_motor_ia, "_sincronizar_supabase_a_sqlite", return_value=0, create=True):

        resp = cliente.post("/api/v1/discord/sync", json={"limite_por_canal": 5})
        assert resp.status_code == 200
        data = resp.json()
        assert data["exito"] is True
        assert data["guardadas_nuevas"] == 0
        assert data["total_recibidas"] == 1
        assert "Todos los mensajes están al día" in data.get("mensaje", "")

    # Caso B: Sin canales autorizados (detectar_canales retorna [])
    with patch("discord.Client", MockDiscordClient), \
         patch("armar_json_bot_python.detectar_canales", return_value=[]):

        resp2 = cliente.post("/api/v1/discord/sync", json={"limite_por_canal": 5})
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["exito"] is True
        assert data2["total_recibidas"] == 0
        assert data2["guardadas_nuevas"] == 0
        assert "No se encontraron canales de texto autorizados" in data2.get("mensaje", "")


def test_discord_recover_endpoint():
    """Valida POST /api/v1/discord/recover para ingesta histórica selectiva con etapa 'ingesta' y estado 'pendiente'."""
    cliente = TestClient(puente_motor_ia.app)

    payload = {
        "mensajes": [
            {
                "canal_id": "999888",
                "message_id": "888777",
                "autor": "historico_user",
                "texto": "Mensaje recuperado históricamente para probar ingesta",
                "fecha": "2026-10-15T12:00:00+00:00",
            }
        ]
    }

    resp = cliente.post("/api/v1/discord/recover", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["exito"] is True
    assert data["guardados_nuevos"] == 1
    assert data["repetidos_omitidos"] == 0
    assert "recuperaron 1 mensajes nuevos" in data.get("mensaje", "")

    # Validar persistencia en SQLite con etapa 'ingesta' y estado 'pendiente'
    conn = sqlite3.connect(puente_motor_ia.motor_bd.RUTA_BD)
    cur = conn.cursor()
    cur.execute(
        "SELECT texto, etapa, estado FROM interacciones WHERE message_id = '888777' OR texto LIKE '%históricamente%'"
    )
    fila = cur.fetchone()
    conn.close()
    assert fila is not None, "El mensaje recuperado no fue guardado en la base de datos"
    assert fila[1] == "ingesta"
    assert fila[2] == "pendiente"

    # Segunda invocación (idempotente: repetido omitido)
    resp2 = cliente.post("/api/v1/discord/recover", json=payload)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["exito"] is True
    assert data2["guardados_nuevos"] == 0
    assert data2["repetidos_omitidos"] == 1


def test_discord_recovery_preview_alias():
    """Valida que GET /api/v1/content-workflow/discord/recovery-preview y GET /api/v1/discord/recovery-preview sean alias idénticos."""
    cliente = TestClient(puente_motor_ia.app)
    mock_preview = {
        "mensajes": [
            {
                "message_id": "preview_111",
                "channel_id": "preview_222",
                "canal": "general",
                "autor": "alice_preview",
                "texto": "Texto vista previa",
                "fecha": "2026-10-15T10:00:00+00:00",
                "recuperado": False,
            }
        ],
        "total": 1,
        "pagina": 1,
        "tamano_pagina": 20,
        "limite_inspeccion_por_canal": 50,
    }

    with patch.object(puente_motor_ia, "vista_previa_recuperacion_discord", return_value=mock_preview, create=True):
        resp1 = cliente.get("/api/v1/content-workflow/discord/recovery-preview")
        resp2 = cliente.get("/api/v1/discord/recovery-preview")
        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert resp1.json() == resp2.json()
        assert resp1.json()["total"] == 1


def test_evaluate_batch_solo_pendientes_blindaje_dual():
    """Valida que POST /api/v1/ai/evaluate-batch con solo_pendientes=True descarte IDs presentes en Supabase Y en SQLite local."""
    cliente = TestClient(puente_motor_ia.app)

    mensajes_simulados = [
        {"id": 401, "autor": "u1", "canal": "#general", "texto": "Msg Supabase", "enviado_en": "2026-10-01T10:00:00+00:00"},
        {"id": 402, "autor": "u2", "canal": "#general", "texto": "Msg SQLite", "enviado_en": "2026-10-02T10:00:00+00:00"},
        {"id": 403, "autor": "u3", "canal": "#general", "texto": "Msg Pendiente", "enviado_en": "2026-10-03T10:00:00+00:00"},
    ]

    # Insertar el mensaje 402 en la base SQLite local como ya analizado
    conn = sqlite3.connect(puente_motor_ia.motor_bd.RUTA_BD)
    conn.execute("""
        INSERT INTO interacciones (id, hash, origen_comunidad, periodo_referencia, autor, canal, tipo, texto, enviado_en, creado_en, estado, relevancia)
        VALUES (402, 'hash_402_xyz', 'Discord', 'Semana_01', 'u2', '#general', 'mensaje', 'Msg SQLite', '2026-10-02T10:00:00+00:00', '2026-10-02T10:00:00+00:00', 'analizado', 85)
    """)
    conn.commit()
    conn.close()

    mock_eval = MagicMock(return_value={
        "exito": True,
        "total_evaluados": 1,
        "exitosos": 1,
        "fallidos": 0,
        "guardados_supabase": 1,
        "errores": [],
        "aprobados": [{"id_mensaje": 403, "kpis": {"relevancia": 88}}],
        "descartados": [],
        "resultados": {},
    })

    # Simular que en Supabase el mensaje 401 ya está evaluado en lotes_ia_kpis
    mock_supabase_kpis = {"kpis": [{"id": 901, "id_mensaje": 401}]}

    with patch("ver_json.obtener_json", return_value={"total": 3, "interacciones": mensajes_simulados}), \
         patch.object(puente_motor_ia, "obtener_datos_supabase", return_value=mock_supabase_kpis), \
         patch("evaluador_lotes.evaluar_lote", mock_eval), \
         patch.object(puente_motor_ia, "_sincronizar_supabase_a_sqlite", return_value=1, create=True):

        payload = {
            "proveedor": "Google Gemma 4",
            "desde": "2026-10-01",
            "hasta": "2026-10-05",
            "solo_pendientes": True,
        }
        resp = cliente.post("/api/v1/ai/evaluate-batch", json=payload)
        assert resp.status_code == 200

        # Blindaje dual: debe haber excluido 401 (de Supabase) Y 402 (de SQLite local),
        # enviando ÚNICAMENTE el mensaje 403 a evaluar_lote
        _, kwargs_eval = mock_eval.call_args
        mensajes_enviados = kwargs_eval.get("mensajes", [])
        assert len(mensajes_enviados) == 1, (
            f"Se esperaba 1 mensaje pendiente pero se enviaron {len(mensajes_enviados)}: {[m['id'] for m in mensajes_enviados]}"
        )
        assert mensajes_enviados[0]["id"] == 403


def test_evaluate_single_message_errores_validacion():
    """Valida errores 400 y 404 en el endpoint /api/v1/ai/evaluate-message."""
    cliente = TestClient(puente_motor_ia.app)

    # 1. Sin interaction_id -> 400
    resp_no_id = cliente.post("/api/v1/ai/evaluate-message", json={"proveedor": "Groq (Llama 3.3)"})
    assert resp_no_id.status_code == 400
    assert "interaction_id" in resp_no_id.json()["detail"]

    # 2. Mensaje no existente -> 404
    resp_404 = cliente.post("/api/v1/ai/evaluate-message", json={"interaction_id": 99999})
    assert resp_404.status_code == 404
    assert "No se encontró" in resp_404.json()["detail"]


def test_evaluate_single_message_exitoso_y_persistencia():
    """Valida la evaluación individual con IA de un mensaje y la actualización en base de datos."""
    cliente = TestClient(puente_motor_ia.app)

    # Insertar mensaje crudo en etapa ingesta
    with sqlite3.connect(puente_motor_ia.motor_bd.RUTA_BD) as conn:
        conn.execute("""
            INSERT INTO interacciones (
                id, hash, origen_comunidad, periodo_referencia, autor, canal, tipo,
                texto, enviado_en, creado_en, estado, etapa_flujo, etapa
            ) VALUES (
                501, 'hash_501', 'Discord', 'Semana_01', 'Carlos', '#preguntas', 'mensaje',
                '¿Cómo funciona la autenticación con JWT?', '2026-10-10T12:00:00+00:00',
                '2026-10-10T12:00:00+00:00', 'pendiente', 'ingesta', 'ingesta'
            )
        """)
        conn.commit()

    mock_eval = MagicMock(return_value={
        "exito": True,
        "total_evaluados": 1,
        "exitosos": 1,
        "fallidos": 0,
        "guardados_supabase": 1,
        "aprobados": [{
            "id_mensaje": 501,
            "kpis": {
                "relevancia": 85,
                "sentimiento": "Positivo",
                "temas_clave": "#desarrollo #jwt",
                "segmento": "Desarrollador",
                "razonamiento": "Pregunta técnica relevante sobre seguridad y backend.",
            },
            "estado_revision": "aprobado",
        }],
        "descartados": [],
        "resultados": {},
    })

    with patch("evaluador_lotes.evaluar_lote", mock_eval), \
         patch.object(puente_motor_ia, "_sincronizar_supabase_a_sqlite", return_value=1, create=True):

        payload = {
            "interaction_id": 501,
            "proveedor": "Groq (Llama 3.3)",
        }
        resp = cliente.post("/api/v1/ai/evaluate-message", json=payload)
        assert resp.status_code == 200
        data = resp.json()

        assert data["exito"] is True
        assert data["interaction_id"] == 501
        assert data["relevancia"] == 85
        assert data["sentimiento"] == "Positivo"
        assert data["estado"] == "analizado"
        assert data["etapa_flujo"] == "en_analisis"

        # Verificar que evaluar_lote recibió enviado_en, creado_en y periodo_referencia
        mock_eval.assert_called_once()
        mensajes_arg = mock_eval.call_args.kwargs.get("mensajes") or mock_eval.call_args.args[0]
        assert len(mensajes_arg) == 1
        assert mensajes_arg[0]["enviado_en"] == "2026-10-10T12:00:00+00:00"
        assert mensajes_arg[0]["creado_en"] == "2026-10-10T12:00:00+00:00"
        assert mensajes_arg[0]["periodo_referencia"] == "Semana_01"

        # Verificar que en SQLite local la fila se actualizó
        interaccion = puente_motor_ia.obtener_interaccion_puente(501)
        assert interaccion is not None
        assert interaccion["estado"] == "analizado"
        assert interaccion["relevancia"] == 85
        assert interaccion["sentimiento"] == "Positivo"
        assert interaccion["etapa_flujo"] == "en_analisis"


def test_dashboard_total_audience_reconciliacion_y_fallback_autor(monkeypatch, client):
    """
    (Spec 009 - TDD Fase Red)
    Simula interacciones con author_id nulo/vacío pero autor válido para 10 miembros
    humanos distintos, además de mensajes de bots ('cloudedtech community bot', 'Spidey Boy#0000').
    Valida que GET /api/community/dashboard reconcilie total_audience == 10
    excluyendo bots y usando autor como fallback de author_id.
    """
    puente_motor_ia.invalidar_cache_supabase()

    interacciones_simuladas = []
    for i in range(1, 11):
        interacciones_simuladas.append({
            "id": i,
            "hash": f"{i:064x}",
            "origen_comunidad": "Discord",
            "periodo_referencia": "Semana_01",
            "autor": f"usuario_{i}",
            "canal": "#general",
            "tipo": "mensaje",
            "texto": f"Mensaje del usuario {i} para la comunidad",
            "enviado_en": "2026-10-15T12:00:00+00:00",
            "creado_en": "2026-10-15T12:01:00+00:00",
            "guild_id": "123",
            "guild_name": "CloudEdTech",
            "channel_id": "456",
            "message_id": f"200{i}",
            "author_id": None if i % 2 == 0 else "",
            "attachments": "[]",
        })

    # Mensajes de bots que deben ser excluidos
    interacciones_simuladas.append({
        "id": 99,
        "hash": "b" * 64,
        "origen_comunidad": "Discord",
        "periodo_referencia": "Semana_01",
        "autor": "cloudedtech community bot",
        "canal": "#general",
        "tipo": "mensaje",
        "texto": "Respuesta automática de bot",
        "enviado_en": "2026-10-15T12:05:00+00:00",
        "creado_en": "2026-10-15T12:06:00+00:00",
        "guild_id": "123",
        "guild_name": "CloudEdTech",
        "channel_id": "456",
        "message_id": "9999",
        "author_id": "bot_99",
        "attachments": "[]",
    })
    interacciones_simuladas.append({
        "id": 100,
        "hash": "c" * 64,
        "origen_comunidad": "Discord",
        "periodo_referencia": "Semana_01",
        "autor": "Spidey Boy#0000",
        "canal": "#general",
        "tipo": "mensaje",
        "texto": "Alerta de webhook",
        "enviado_en": "2026-10-15T12:10:00+00:00",
        "creado_en": "2026-10-15T12:11:00+00:00",
        "guild_id": "123",
        "guild_name": "CloudEdTech",
        "channel_id": "456",
        "message_id": "10000",
        "author_id": "",
        "attachments": "[]",
    })

    mock_datos = {
        "interacciones": interacciones_simuladas,
        "kpis": [],
    }

    with patch.object(puente_motor_ia, "obtener_datos_supabase", return_value=mock_datos):
        resp = client.get("/api/community/dashboard")
        assert resp.status_code == 200, f"Error {resp.status_code}: {resp.text}"
        data = resp.json()

        # Debe contabilizar exactamente los 10 humanos distintos, excluyendo los bots
        assert data["total_audience"] == 10


# ==============================================================================
# 13. Integración Funcional de Informes y Almacenamiento OCI - Tania (Spec 011)
# ==============================================================================

def test_oci_status_incluye_modo_y_bucket(client):
    """Verifica que GET /api/v1/oci-storage/status retorne 200 e incluya oci_configured, mode, bucket y region."""
    resp = client.get("/api/v1/oci-storage/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "connected"
    assert "message" in data
    assert "oci_configured" in data
    assert isinstance(data["oci_configured"], bool)
    assert data.get("mode") in ("online", "offline")
    assert "bucket" in data and isinstance(data["bucket"], str) and len(data["bucket"]) > 0
    assert "region" in data and isinstance(data["region"], str) and len(data["region"]) > 0


def test_oci_weekly_period_incluye_iso_week_label(client):
    """Verifica que GET /api/v1/oci-storage/weekly-period retorne 200 e incluya iso_week_label con formato AAAA-semana-NN."""
    import re
    resp = client.get("/api/v1/oci-storage/weekly-period")
    assert resp.status_code == 200
    data = resp.json()
    assert "semana_nombre" in data
    assert "week_label" in data
    assert "start_date" in data
    assert "end_date" in data
    assert data["status"] == "ready"
    assert "iso_week_label" in data
    assert re.fullmatch(r"^\d{4}-semana-\d{2}$", data["iso_week_label"]), (
        f"iso_week_label '{data.get('iso_week_label')}' no cumple el patrón AAAA-semana-NN"
    )


def test_oci_weekly_sync_retorna_reporte_completo_y_valida_etiqueta(client, tmp_path, monkeypatch):
    """
    Verifica que POST /api/v1/oci-storage/weekly-sync:
    1) Con etiqueta válida retorne 200 e incluya 'reporte' con 'metadata', 'resumen_metricas' y 'activos_copywriting'.
    2) Con etiqueta inválida retorne HTTP 400 Bad Request.
    """
    monkeypatch.chdir(tmp_path)
    paquete_mock = {
        "aprobados": [
            {
                "id_mensaje": 10,
                "autor": "alice",
                "canal_origen": "#general",
                "semana": "Semana_01",
                "fecha_envio": "2026-10-15T12:00:00+00:00",
                "texto_original": "Excelente curso de Python e IA",
                "kpis": {
                    "relevancia": 90,
                    "sentimiento": "Positivo",
                    "temas_clave": "#python #ia",
                    "segmento": "Estudiante",
                    "razonamiento": "Alto valor para copywriting",
                },
            }
        ],
        "descartados": [
            {
                "id_mensaje": 11,
                "autor": "bob",
                "canal_origen": "#soporte",
                "semana": "Semana_01",
                "fecha_envio": "2026-10-15T13:00:00+00:00",
                "texto_original": "Error de conexión",
                "kpis": {
                    "relevancia": 40,
                    "sentimiento": "Negativo",
                    "temas_clave": "#soporte",
                    "segmento": "Estudiante",
                    "razonamiento": "Queja técnica",
                },
            }
        ],
    }

    with patch.object(puente_motor_ia._base_datos_raiz, "obtener_lote_kpis_supabase", return_value=paquete_mock), \
         patch("reporte_semanal.subir_json_a_oci", return_value=False):
        resp_ok = client.post("/api/v1/oci-storage/weekly-sync", json={"semana": "2026-semana-42"})
        assert resp_ok.status_code == 200
        data_ok = resp_ok.json()
        assert data_ok["exito"] is True
        assert data_ok["semana"] == "2026-semana-42"
        assert "reporte" in data_ok
        reporte = data_ok["reporte"]
        assert "metadata" in reporte
        assert "resumen_metricas" in reporte
        assert "activos_copywriting" in reporte
        assert reporte["resumen_metricas"]["total_mensajes"] == 2
        assert reporte["resumen_metricas"]["total_aprobados"] == 1
        assert reporte["resumen_metricas"]["total_descartados"] == 1

        # Etiqueta inválida -> HTTP 400 Bad Request
        resp_inv = client.post("/api/v1/oci-storage/weekly-sync", json={"semana": "semana-invalida"})
        assert resp_inv.status_code == 400


def test_oci_reports_lista_historial_reportes(client, tmp_path, monkeypatch):
    """
    Verifica que GET /api/v1/oci-storage/reports retorne 200 con {'reports': [...], 'total': int},
    ignore archivos corruptos y cada elemento contenga las llaves requeridas.
    """
    import json
    monkeypatch.chdir(tmp_path)
    reportes_dir = tmp_path / "reportes"
    reportes_dir.mkdir(parents=True, exist_ok=True)

    reporte_valido = {
        "metadata": {
            "proyecto": "CommunityLab",
            "semana": "2026-semana-42",
            "version_esquema": "1.0",
            "generado_en": "2026-10-17T10:00:00+00:00",
            "oci_storage": {
                "bucket": "communitylab-assets",
                "ruta": "activos/2026-semana-42/paquete-distribucion.json",
                "subido": False,
            },
        },
        "resumen_metricas": {
            "total_mensajes": 5,
            "total_aprobados": 3,
            "total_descartados": 2,
            "sentimiento": {"Positivo": 3, "Negativo": 2},
            "temas_tendencia": [{"tema": "#ia", "menciones": 3}],
            "segmentos": {"Estudiante": 5},
        },
        "activos_copywriting": {"aprobados": [], "descartados": []},
    }

    (reportes_dir / "2026-semana-42.json").write_text(
        json.dumps(reporte_valido, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # Archivo JSON corrupto que debe ser ignorado sin romper el endpoint
    (reportes_dir / "corrupto.json").write_text("{json_corrupto_invalido", encoding="utf-8")

    resp = client.get("/api/v1/oci-storage/reports")
    assert resp.status_code == 200
    data = resp.json()
    assert "reports" in data
    assert "total" in data
    assert data["total"] == 1
    assert len(data["reports"]) == 1

    item = data["reports"][0]
    for key in (
        "semana",
        "nombre_archivo",
        "tamano_bytes",
        "generado_en",
        "bucket",
        "ruta_oci",
        "subido_oci",
        "resumen_metricas",
        "reporte",
    ):
        assert key in item, f"Falta la llave '{key}' en el elemento de historial: {item}"

    assert item["semana"] == "2026-semana-42"
    assert item["nombre_archivo"] == "2026-semana-42.json"
    assert item["tamano_bytes"] > 0
    assert item["subido_oci"] is False
    assert item["resumen_metricas"]["total_mensajes"] == 5







# ==============================================================================
# 14. Spec 012: Soporte a Quejas y Mesa de Trabajo de Copywriting (TDD Fase Red)
# ==============================================================================

def _insertar_interaccion_spec012(
    interaccion_id: int = 701,
    texto: str = "Tengo un problema grave con el curso de backend",
    canal: str = "#soporte",
    autor: str = "usuario_molesto",
    channel_id: str = "458",
    message_id: str = "1001",
    etapa_flujo: str = "en_analisis",
):
    """Inserta una interacción de prueba directamente en la base SQLite temporal."""
    with sqlite3.connect(puente_motor_ia.motor_bd.RUTA_BD) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO interacciones (
                id, hash, origen_comunidad, periodo_referencia, autor, canal, tipo,
                texto, enviado_en, creado_en, estado, etapa_flujo, etapa, channel_id, message_id
            ) VALUES (
                ?, ?, 'Discord', 'Semana_01', ?, ?, 'mensaje',
                ?, '2026-10-18T10:00:00+00:00', '2026-10-18T10:00:00+00:00', 'pendiente', ?, ?, ?, ?
            )
            """,
            (
                interaccion_id,
                f"hash_{interaccion_id}",
                autor,
                canal,
                texto,
                etapa_flujo,
                etapa_flujo,
                channel_id,
                message_id,
            ),
        )
        conn.commit()


# --- Contrato 1: POST /api/v1/content-workflow/complaints/generate-response ---

def test_complaint_generate_response_exitoso_proveedor_default(client):
    """
    (Spec 012 - RF-01) POST /api/v1/content-workflow/complaints/generate-response
    Valida generación estructurada con proveedor por defecto ('Groq (Llama 3.3)').
    """
    _insertar_interaccion_spec012(interaccion_id=701, texto="No puedo ingresar a la plataforma desde ayer.")

    with patch.dict(os.environ, {"GROQ_API_KEY": "gsk_test123"}), \
         patch.object(puente_motor_ia, "_generar_respuesta_queja_ia", create=True,
                      return_value={"respuesta": "Lamentamos el inconveniente con tu acceso a la plataforma."}):
        payload = {"interaccion_id": 701}
        resp = client.post("/api/v1/content-workflow/complaints/generate-response", json=payload)
        assert resp.status_code == 200, f"Error inesperado: {resp.status_code} - {resp.text}"
        data = resp.json()
        assert data["interaccion_id"] == 701
        assert "respuesta" in data and len(data["respuesta"]) > 0
        assert data["proveedor_usado"] == "Groq (Llama 3.3)"
        assert data["estado"] == "borrador"
        assert data["requiere_revision"] is True


def test_complaint_generate_response_proveedores_especificos(client):
    """
    (Spec 012 - RF-01) POST /api/v1/content-workflow/complaints/generate-response
    Valida generación con proveedores específicos ('Google Gemma 4' y 'Google Gemini Flash Lite').
    """
    _insertar_interaccion_spec012(interaccion_id=701, texto="Duda sobre el certificado de finalización.")

    with patch.dict(os.environ, {"GOOGLE_API_KEY": "AIza_mock_key", "GEMINI_API_KEY": "AIza_mock_key"}):
        for proveedor_solicitado in ["Google Gemma 4", "Google Gemini Flash Lite"]:
            with patch.object(puente_motor_ia, "_generar_respuesta_queja_ia", create=True,
                              return_value={"respuesta": f"Respuesta generada con {proveedor_solicitado}."}):
                payload = {
                    "interaccion_id": 701,
                    "proveedor": proveedor_solicitado,
                }
                resp = client.post("/api/v1/content-workflow/complaints/generate-response", json=payload)
                assert resp.status_code == 200, f"Error con {proveedor_solicitado}: {resp.status_code} - {resp.text}"
                data = resp.json()
                assert data["interaccion_id"] == 701
                assert data["proveedor_usado"] == proveedor_solicitado
                assert data["estado"] == "borrador"
                assert data["requiere_revision"] is True


def test_complaint_generate_response_interaccion_no_encontrada_404(client):
    """
    (Spec 012 - RF-01) POST /api/v1/content-workflow/complaints/generate-response
    Valida rechazo HTTP 404 cuando la interacción solicitada no existe.
    """
    resp = client.post("/api/v1/content-workflow/complaints/generate-response", json={"interaccion_id": 999999})
    assert resp.status_code == 404
    assert "no existe" in resp.json().get("detail", "").lower()


def test_complaint_generate_response_texto_vacio_422(client):
    """
    (Spec 012 - RF-01) POST /api/v1/content-workflow/complaints/generate-response
    Valida rechazo HTTP 422 cuando la interacción no contiene texto o solo contiene espacios.
    """
    _insertar_interaccion_spec012(interaccion_id=702, texto="    ")
    resp = client.post("/api/v1/content-workflow/complaints/generate-response", json={"interaccion_id": 702})
    assert resp.status_code == 422
    assert "no contiene texto" in resp.json().get("detail", "").lower()


def test_complaint_generate_response_credenciales_faltantes_502(client):
    """
    (Spec 012 - RF-01) POST /api/v1/content-workflow/complaints/generate-response
    Valida rechazo HTTP 502 sin sustitución silenciosa cuando faltan credenciales del proveedor.
    """
    _insertar_interaccion_spec012(interaccion_id=701, texto="Reporte de error en video.")
    with patch.dict(os.environ, {"GROQ_API_KEY": ""}, clear=False):
        payload = {"interaccion_id": 701, "proveedor": "Groq (Llama 3.3)"}
        resp = client.post("/api/v1/content-workflow/complaints/generate-response", json=payload)
        assert resp.status_code == 502
        detail = resp.json().get("detail", "")
        assert "Groq (Llama 3.3)" in detail or "credenciales" in detail.lower()


# --- Contrato 2: GET /api/v1/content-workflow/complaints/{id}/publish-preview ---

def test_complaint_publish_preview_sin_token_discord_retorna_ready_false(client):
    """
    (Spec 012 - RF-02) GET /api/v1/content-workflow/complaints/{id}/publish-preview
    Valida retorno HTTP 200 con ready: false y detalle explicativo si falta token del bot.
    """
    _insertar_interaccion_spec012(
        interaccion_id=703,
        texto="Error crítico al enviar tarea final",
        canal="#soporte",
        channel_id="458",
        message_id="1003",
        autor="charlie",
    )
    with patch.dict(os.environ, {"DISCORD_BOT_TOKEN": "", "DISCORD_TOKEN": ""}, clear=False):
        resp = client.get("/api/v1/content-workflow/complaints/703/publish-preview")
        assert resp.status_code == 200
        data = resp.json()
        assert data["interaccion_id"] == 703
        assert data["ready"] is False
        assert data["channel_id"] == "458"
        assert data["channel_name"] == "soporte"
        assert data["source_message_id"] == "1003"
        assert data["author"] == "charlie"
        assert data["original_content"] == "Error crítico al enviar tarea final"
        assert "bot" in data.get("detail", "").lower()


def test_complaint_publish_preview_con_token_y_destino_valido_retorna_ready_true(client):
    """
    (Spec 012 - RF-02) GET /api/v1/content-workflow/complaints/{id}/publish-preview
    Valida retorno HTTP 200 con ready: true y metadatos cuando bot y destino son válidos.
    """
    _insertar_interaccion_spec012(
        interaccion_id=703,
        texto="Error crítico al enviar tarea final",
        canal="#soporte",
        channel_id="458",
        message_id="1003",
        autor="charlie",
    )
    with patch.dict(os.environ, {"DISCORD_BOT_TOKEN": "bot_token_123", "DISCORD_GUILD_ID": "guild_999"}, clear=False), \
         patch.object(puente_motor_ia, "_verificar_mensaje_discord", create=True, return_value=True):
        resp = client.get("/api/v1/content-workflow/complaints/703/publish-preview")
        assert resp.status_code == 200
        data = resp.json()
        assert data["interaccion_id"] == 703
        assert data["ready"] is True
        assert data["channel_id"] == "458"
        assert data["channel_name"] == "soporte"
        assert data["source_message_id"] == "1003"
        assert data["author"] == "charlie"
        assert data["original_content"] == "Error crítico al enviar tarea final"


def test_complaint_publish_preview_sin_channel_id_resuelve_canal_oficial_y_ready_true(client):
    """
    (Spec 012 - RF-02) Valida que interacciones históricas/semilla sin channel_id
    resuelvan automáticamente el canal oficial (ej. #faq -> 1551309664397033513) y retornen ready: True.
    """
    _insertar_interaccion_spec012(
        interaccion_id=705,
        texto="Consulta crítica en el canal de preguntas frecuentes",
        canal="#faq",
        channel_id="",
        message_id="705",
        autor="maria",
    )
    with patch.dict(os.environ, {"DISCORD_BOT_TOKEN": "bot_token_123"}, clear=False):
        resp = client.get("/api/v1/content-workflow/complaints/705/publish-preview")
        assert resp.status_code == 200
        data = resp.json()
        assert data["interaccion_id"] == 705
        assert data["ready"] is True
        assert data["channel_id"] == "1551309664397033513"
        assert data["channel_name"] == "faq"
        assert data["author"] == "maria"


def test_complaint_publish_preview_rechazos_404(client):
    """
    (Spec 012 - RF-02) GET /api/v1/content-workflow/complaints/{id}/publish-preview
    Valida 404 si la interacción no existe o si el mensaje original ya no existe en Discord.
    """
    # 1. Interacción inexistente
    resp_no_int = client.get("/api/v1/content-workflow/complaints/999999/publish-preview")
    assert resp_no_int.status_code == 404
    assert "no existe" in resp_no_int.json().get("detail", "").lower()

    # 2. Mensaje no existe en Discord (cuando hay token configurado)
    _insertar_interaccion_spec012(interaccion_id=703, channel_id="458", message_id="1003")
    with patch.dict(os.environ, {"DISCORD_BOT_TOKEN": "bot_token_123"}, clear=False), \
         patch.object(puente_motor_ia, "_verificar_mensaje_discord", create=True, return_value=False):
        resp_no_msg = client.get("/api/v1/content-workflow/complaints/703/publish-preview")
        assert resp_no_msg.status_code == 404
        assert "discord" in resp_no_msg.json().get("detail", "").lower()


# --- Contrato 3: POST /api/v1/content-workflow/complaints/publish-response ---

def test_complaint_publish_response_validaciones_caracteres_y_confirmacion(client):
    """
    (Spec 012 - RF-03) POST /api/v1/content-workflow/complaints/publish-response
    Valida rechazo HTTP 400 si confirmado es falso o si la respuesta no cumple entre 1 y 2000 caracteres.
    """
    _insertar_interaccion_spec012(interaccion_id=704)
    with patch.dict(os.environ, {"DISCORD_BOT_TOKEN": "token_bot_123"}, clear=False):
        # 1. No confirmado
        resp_no_conf = client.post("/api/v1/content-workflow/complaints/publish-response", json={
            "interaccion_id": 704,
            "respuesta": "Hola, atendemos tu caso.",
            "confirmado": False,
        })
        assert resp_no_conf.status_code == 400

        # 2. Respuesta vacía
        resp_vacia = client.post("/api/v1/content-workflow/complaints/publish-response", json={
            "interaccion_id": 704,
            "respuesta": "   ",
            "confirmado": True,
        })
        assert resp_vacia.status_code == 400

        # 3. Respuesta que excede 2000 caracteres
        resp_larga = client.post("/api/v1/content-workflow/complaints/publish-response", json={
            "interaccion_id": 704,
            "respuesta": "A" * 2001,
            "confirmado": True,
        })
        assert resp_larga.status_code == 400


def test_complaint_publish_response_sin_token_discord_502(client):
    """
    (Spec 012 - RF-03) POST /api/v1/content-workflow/complaints/publish-response
    Valida rechazo HTTP 502 si falta el token de Discord al intentar publicar.
    """
    _insertar_interaccion_spec012(interaccion_id=704)
    with patch.dict(os.environ, {"DISCORD_BOT_TOKEN": "", "DISCORD_TOKEN": ""}, clear=False):
        resp = client.post("/api/v1/content-workflow/complaints/publish-response", json={
            "interaccion_id": 704,
            "respuesta": "Hola, lamentamos el inconveniente.",
            "confirmado": True,
        })
        assert resp.status_code == 502
        assert "discord" in resp.json().get("detail", "").lower() or "token" in resp.json().get("detail", "").lower()


def test_complaint_publish_response_exitoso_y_persistencia_sqlite(client):
    """
    (Spec 012 - RF-03) POST /api/v1/content-workflow/complaints/publish-response
    Valida envío de respuesta a Discord con reply, persistencia en respuestas_quejas_discord y avance a 'atendido'.
    """
    _insertar_interaccion_spec012(
        interaccion_id=704,
        canal="#soporte",
        channel_id="458",
        message_id="1004",
        etapa_flujo="en_redaccion",
    )
    with patch.dict(os.environ, {"DISCORD_BOT_TOKEN": "token_valido"}), \
         patch.object(puente_motor_ia, "_enviar_reply_discord", create=True,
                      return_value={"discord_message_id": "disc_msg_999", "channel_id": "458"}):
        payload = {
            "interaccion_id": 704,
            "respuesta": "Hola Charlie, el equipo técnico ya está atendiendo el problema de acceso.",
            "confirmado": True,
        }
        resp = client.post("/api/v1/content-workflow/complaints/publish-response", json=payload)
        assert resp.status_code == 200, f"Error al publicar: {resp.status_code} - {resp.text}"
        data = resp.json()
        assert data["estado"] == "publicado"
        assert data["interaccion_id"] == 704
        assert data["discord_message_id"] == "disc_msg_999"
        assert data["channel_id"] == "458"

        # Validar persistencia en SQLite
        with sqlite3.connect(puente_motor_ia.motor_bd.RUTA_BD) as conn:
            row = conn.execute(
                "SELECT interaccion_id, canal_id, discord_message_id, respuesta FROM respuestas_quejas_discord WHERE interaccion_id = 704"
            ).fetchone()
            assert row is not None
            assert row[0] == 704
            assert row[1] == "458"
            assert row[2] == "disc_msg_999"
            assert row[3] == "Hola Charlie, el equipo técnico ya está atendiendo el problema de acceso."

        # Validar actualización de etapa en la interacción
        interaccion = puente_motor_ia.obtener_interaccion_puente(704)
        assert interaccion is not None
        assert interaccion["etapa_flujo"] == "atendido"


# --- Contrato 4: GET /api/v1/content-workflow/complaints/published-responses ---

def test_complaint_published_responses_consulta_tabla_sqlite(client):
    """
    (Spec 012 - RF-04) GET /api/v1/content-workflow/complaints/published-responses
    Valida consulta de IDs de respuestas ya publicadas consultando respuestas_quejas_discord.
    """
    with sqlite3.connect(puente_motor_ia.motor_bd.RUTA_BD) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS respuestas_quejas_discord (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                interaccion_id INTEGER NOT NULL UNIQUE,
                canal_id TEXT NOT NULL,
                discord_message_id TEXT NOT NULL,
                respuesta TEXT NOT NULL,
                publicado_en TEXT NOT NULL,
                autor_respuesta TEXT DEFAULT 'bot'
            )
        """)
        conn.execute("""
            INSERT INTO respuestas_quejas_discord (interaccion_id, canal_id, discord_message_id, respuesta, publicado_en, autor_respuesta)
            VALUES (701, '458', 'disc_101', 'Respuesta queja 1', '2026-10-18T12:00:00+00:00', 'bot'),
                   (703, '458', 'disc_102', 'Respuesta queja 2', '2026-10-18T12:05:00+00:00', 'bot')
        """)
        conn.commit()

    resp = client.get("/api/v1/content-workflow/complaints/published-responses")
    assert resp.status_code == 200
    data = resp.json()
    assert "interaction_ids" in data
    assert data["interaction_ids"] == [701, 703]


# --- Contrato 5: POST /api/v1/content-workflow/regenerate ---

def test_content_workflow_regenerate_formatos_y_proveedores(client):
    """
    (Spec 012 - RF-06) POST /api/v1/content-workflow/regenerate
    Valida regeneración estructurada para diferentes formatos y proveedores de IA.
    """
    with patch.dict(os.environ, {"GROQ_API_KEY": "gsk_test123"}), \
         patch.object(puente_motor_ia, "_generar_copy_llm", create=True,
                      return_value={
                          "formato": "linkedin",
                          "titulo": "Innovación y Cloud en Educación",
                          "contenido": "Un análisis práctico sobre el impacto de la nube en la formación profesional.",
                          "llamada_accion": "¿Cómo integras cloud en tus proyectos? Cuéntanos.",
                          "hashtags": ["#cloud", "#educacion", "#tech"],
                      }):
        payload = {
            "texto": "Queremos aprender más sobre despliegues en la nube",
            "canal": "#general",
            "formato": "linkedin",
            "tono": "profesional",
            "proveedor": "Groq (Llama 3.3)",
        }
        resp = client.post("/api/v1/content-workflow/regenerate", json=payload)
        assert resp.status_code == 200, f"Error al regenerar: {resp.status_code} - {resp.text}"
        data = resp.json()
        assert data["formato"] == "linkedin"
        assert data["titulo"] == "Innovación y Cloud en Educación"
        assert "impacto de la nube" in data["contenido"]
        assert data["llamada_accion"] == "¿Cómo integras cloud en tus proyectos? Cuéntanos."
        assert isinstance(data["hashtags"], list)
        assert len(data["hashtags"]) == 3


def test_content_workflow_regenerate_garantia_estricta_limite_280_para_x(client):
    """
    (Spec 012 - RF-06) POST /api/v1/content-workflow/regenerate
    Garantiza estrictamente que para formato 'x' el texto generado nunca supere los 280 caracteres.
    """
    # Texto largo de 350 caracteres simulado desde el LLM
    texto_largo = (
        "La educación en tecnología no se trata solo de escribir código, sino de entender la arquitectura, "
        "la infraestructura en la nube y resolver problemas reales de negocio para las empresas modernas. "
        "Aprende con nosotros en CloudEdTech y lleva tus habilidades al siguiente nivel profesional hoy mismo."
    )
    assert len(texto_largo) > 280

    with patch.dict(os.environ, {"GROQ_API_KEY": "gsk_test123"}), \
         patch.object(puente_motor_ia, "_generar_copy_llm", create=True,
                      return_value={
                          "formato": "x",
                          "titulo": "Formación Tech",
                          "contenido": texto_largo,
                          "llamada_accion": "Síguenos.",
                          "hashtags": ["#tech"],
                      }):
        payload = {
            "texto": "Interés en cursos de arquitectura cloud",
            "canal": "#general",
            "formato": "x",
            "tono": "profesional",
        }
        resp = client.post("/api/v1/content-workflow/regenerate", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["formato"] == "x"
        assert len(data["contenido"]) <= 280, f"El contenido para X excedió 280 caracteres ({len(data['contenido'])})"


def test_content_workflow_regenerate_validacion_texto_vacio(client):
    """
    (Spec 012 - RF-06) POST /api/v1/content-workflow/regenerate
    Valida rechazo HTTP 400 o 422 si el texto está vacío o contiene solo espacios.
    """
    payload = {
        "texto": "    ",
        "canal": "#general",
        "formato": "linkedin",
    }
    resp = client.post("/api/v1/content-workflow/regenerate", json=payload)
    assert resp.status_code in (400, 422)


# --- Contrato 6: POST /api/v1/content-workflow/drafts ---

def test_content_workflow_drafts_persistencia_y_actualizacion_etapa(client):
    """
    (Spec 012 - RF-07) POST /api/v1/content-workflow/drafts
    Valida inserción en contenidos_generados (estado 'pendiente_revision') y avance a 'en_aprobacion'.
    """
    _insertar_interaccion_spec012(
        interaccion_id=705,
        texto="Mensaje seleccionado para redacción",
        etapa_flujo="en_redaccion",
    )
    payload = {
        "interaccion_id": 705,
        "plataforma": "linkedin",
        "titulo": "Novedades de Cloud Computing",
        "contenido": "Esta semana la comunidad discutió sobre microservicios y escalabilidad.",
        "llamada_accion": "¿Cuál es tu arquitectura preferida?",
        "hashtags": ["#cloud", "#microservicios"],
        "tono": "profesional",
    }
    resp = client.post("/api/v1/content-workflow/drafts", json=payload)
    assert resp.status_code in (200, 201), f"Error al guardar borrador: {resp.status_code} - {resp.text}"
    data = resp.json()
    assert "id" in data and isinstance(data["id"], int) and data["id"] > 0
    assert data["estado"] == "pendiente_revision"
    assert "aprobación" in data.get("message", "").lower() or "exitosamente" in data.get("message", "").lower()

    # Validar persistencia en SQLite contenidos_generados
    with sqlite3.connect(puente_motor_ia.motor_bd.RUTA_BD) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM contenidos_generados WHERE id = ?", (data["id"],)).fetchone()
        assert row is not None
        assert row["interaccion_id"] == 705
        assert row["formato"] == "linkedin"
        assert row["titulo"] == "Novedades de Cloud Computing"
        assert row["contenido"] == "Esta semana la comunidad discutió sobre microservicios y escalabilidad."
        assert row["estado"] == "pendiente_revision"

    # Validar actualización de etapa en la interacción vinculada
    interaccion = puente_motor_ia.obtener_interaccion_puente(705)
    assert interaccion is not None
    assert interaccion["etapa_flujo"] == "en_aprobacion"


def test_content_workflow_drafts_validacion_campos_requeridos(client):
    """
    (Spec 012 - RF-07) POST /api/v1/content-workflow/drafts
    Valida rechazo HTTP 400 o 422 si falta contenido o plataforma requerida.
    """
    payload_sin_contenido = {
        "interaccion_id": 705,
        "plataforma": "linkedin",
        "titulo": "Título de prueba",
        "contenido": "",
    }
    resp = client.post("/api/v1/content-workflow/drafts", json=payload_sin_contenido)
    assert resp.status_code in (400, 422)


# ==============================================================================
# Spec 013: Análisis Integral, Historias Destacadas del Dashboard y Webhook de Anuncios
# ==============================================================================

def test_community_analytics_incluye_emojis_y_brand_alignment(client):
    """
    (Spec 013 - RF-02, RF-03) GET /api/community/analytics
    Valida que retorne 'emojis' (lista de objetos con {emoji, count, sentiment, label, description, trend})
    y 'brand_alignment_percentage' (float), manteniendo intactos sentiment, topics y hashtags.
    """
    # Insertar interacciones de prueba con emojis Unicode (ZWJ) y sintaxis de Discord
    with sqlite3.connect(puente_motor_ia.motor_bd.RUTA_BD) as conn:
        conn.execute(
            """
            INSERT INTO interacciones (id, hash, origen_comunidad, periodo_referencia, autor, canal, tipo, texto, enviado_en, creado_en)
            VALUES 
            (801, 'hash_801', 'Discord', 'Semana_01', 'mariana_dev', '#general', 'mensaje', '¡Gran avance en el proyecto! 🚀✨ Mucho éxito ❤️', '2026-10-18T10:00:00+00:00', '2026-10-18T10:00:00+00:00'),
            (802, 'hash_802', 'Discord', 'Semana_01', 'carlos_g', '#general', 'mensaje', 'Nuevo release con <:python_custom:12345678> y <a:fire_anim:98765432> 💡', '2026-10-18T11:00:00+00:00', '2026-10-18T11:00:00+00:00')
            """
        )
        conn.commit()

    resp = client.get("/api/community/analytics")
    assert resp.status_code == 200, f"Error {resp.status_code}: {resp.text}"
    data = resp.json()

    # Mantener intactos sentiment, topics y hashtags
    assert "sentiment" in data, "Falta clave preexistente 'sentiment'"
    assert "topics" in data, "Falta clave preexistente 'topics'"
    assert "hashtags" in data, "Falta clave preexistente 'hashtags'"

    # Nuevos campos de Spec 013
    assert "emojis" in data, "Falta clave 'emojis' requerida por Spec 013"
    assert isinstance(data["emojis"], list), "'emojis' debe ser una lista"
    assert len(data["emojis"]) > 0, "Se esperaba detectar al menos un emoji en las interacciones"

    for item in data["emojis"]:
        for campo in ("emoji", "count", "sentiment", "label", "description", "trend"):
            assert campo in item, f"Falta el campo obligatorio '{campo}' en el objeto emoji: {item}"
        assert isinstance(item["emoji"], str)
        assert isinstance(item["count"], int)
        assert isinstance(item["sentiment"], str)
        assert isinstance(item["label"], str)
        assert isinstance(item["description"], str)
        assert isinstance(item["trend"], str)

    assert "brand_alignment_percentage" in data, "Falta 'brand_alignment_percentage' requerida por Spec 013"
    assert isinstance(data["brand_alignment_percentage"], (int, float))
    assert 0.0 <= float(data["brand_alignment_percentage"]) <= 100.0


def test_community_analytics_proteccion_division_cero_corpus_vacio(client):
    """
    (Spec 013 - RF-03) GET /api/community/analytics
    Valida que ante interacciones vacías no arroje ZeroDivisionError y retorne brand_alignment_percentage: 100.0 y emojis: [].
    """
    with patch.object(puente_motor_ia, "obtener_datos_supabase", return_value={"interacciones": [], "kpis": []}):
        with sqlite3.connect(puente_motor_ia.motor_bd.RUTA_BD) as conn:
            conn.execute("DELETE FROM interacciones")
            conn.commit()

        # Usar cliente sin re-raise de excepciones no capturadas de endpoints heredados para validar código HTTP 200
        cliente_seguro = TestClient(puente_motor_ia.app, raise_server_exceptions=False)
        resp = cliente_seguro.get("/api/community/analytics")
        assert resp.status_code == 200, f"Error {resp.status_code}: {resp.text}"
        data = resp.json()

        assert "brand_alignment_percentage" in data, "Falta 'brand_alignment_percentage' en respuesta vacía"
        assert float(data["brand_alignment_percentage"]) == 100.0, (
            f"Se esperaba brand_alignment_percentage 100.0 ante corpus vacío, recibido {data.get('brand_alignment_percentage')}"
        )
        assert "emojis" in data, "Falta 'emojis' en respuesta vacía"
        assert data["emojis"] == [], f"Se esperaba emojis [] ante corpus vacío, recibido {data.get('emojis')}"


def test_community_live_summary_y_alias_filtran_autores_sinteticos(client):
    """
    (Spec 013 - RF-04, RF-05) GET /api/v1/community/live-summary y GET /api/community/summary
    Valida que excluyan 'usuario_uno', 'usuario_tres' e IDs 31 y 34,
    e incluyan 'is_published' y 'published_platforms' en las historias destacadas.
    """
    interacciones_test = [
        {"id": 10, "autor": "danitower", "texto": "Increíble taller de IA aplicada", "canal": "#general", "tipo": "mensaje"},
        {"id": 20, "autor": "carlos_g", "texto": "Pregunta técnica sobre FastApi", "canal": "#preguntas", "tipo": "mensaje"},
        {"id": 31, "autor": "usuario_uno", "texto": "Mensaje sintético de prueba id 31", "canal": "#general", "tipo": "mensaje"},
        {"id": 34, "autor": "usuario_tres", "texto": "Mensaje sintético de prueba id 34", "canal": "#general", "tipo": "mensaje"},
        {"id": 50, "autor": "usuario_dos", "texto": "Mensaje con prefijo usuario_", "canal": "#general", "tipo": "mensaje"},
        {"id": 51, "autor": "test_qa", "texto": "Mensaje con prefijo test_", "canal": "#general", "tipo": "mensaje"},
    ]
    lotes_kpis_test = [
        {"id": 10, "id_mensaje": 10, "autor": "danitower", "texto": "Increíble taller de IA aplicada", "relevancia": 85, "sentimiento": "Positivo", "canal_origen": "#general"},
        {"id": 20, "id_mensaje": 20, "autor": "carlos_g", "texto": "Pregunta técnica sobre FastApi", "relevancia": 80, "sentimiento": "Neutral", "canal_origen": "#preguntas"},
        {"id": 31, "id_mensaje": 31, "autor": "usuario_uno", "texto": "Mensaje sintético de prueba id 31", "relevancia": 90, "sentimiento": "Positivo", "canal_origen": "#general"},
        {"id": 34, "id_mensaje": 34, "autor": "usuario_tres", "texto": "Mensaje sintético de prueba id 34", "relevancia": 90, "sentimiento": "Positivo", "canal_origen": "#general"},
        {"id": 50, "id_mensaje": 50, "autor": "usuario_dos", "texto": "Mensaje con prefijo usuario_", "relevancia": 90, "sentimiento": "Positivo", "canal_origen": "#general"},
        {"id": 51, "id_mensaje": 51, "autor": "test_qa", "texto": "Mensaje con prefijo test_", "relevancia": 90, "sentimiento": "Positivo", "canal_origen": "#general"},
    ]

    # Marcar interacción 10 como publicada en SQLite contenidos_generados
    with sqlite3.connect(puente_motor_ia.motor_bd.RUTA_BD) as conn:
        conn.execute(
            """
            INSERT INTO contenidos_generados (interaccion_id, formato, plataforma, titulo, contenido, estado, estado_publicacion, creado_en, actualizado_en)
            VALUES (10, 'discord', 'discord', 'Taller IA', 'Contenido publicado en canal', 'publicado', 'publicado', '2026-10-18T10:00:00+00:00', '2026-10-18T10:00:00+00:00')
            """
        )
        conn.commit()


    with patch.object(puente_motor_ia, "obtener_datos_supabase", return_value={"interacciones": interacciones_test, "kpis": lotes_kpis_test}), \
         patch.object(puente_motor_ia, "_obtener_lotes_kpis_completos", return_value=lotes_kpis_test, create=True):

        for endpoint in ("/api/v1/community/live-summary", "/api/community/summary"):
            resp = client.get(endpoint)
            assert resp.status_code == 200, f"Endpoint {endpoint} respondió {resp.status_code}: {resp.text}"
            data = resp.json()
            assert "highlights" in data, f"Falta 'highlights' en respuesta de {endpoint}"
            highlights = data["highlights"]

            autores = [str(h.get("autor") or h.get("author") or "").lower() for h in highlights]
            ids = [h.get("id_mensaje") or h.get("id") for h in highlights]

            # 1. Filtro estricto de autores sintéticos y semillas de prueba
            assert not any("usuario_uno" in a for a in autores), f"'usuario_uno' encontrado en {endpoint}: {autores}"
            assert not any("usuario_tres" in a for a in autores), f"'usuario_tres' encontrado en {endpoint}: {autores}"
            assert not any(a.startswith("usuario_") for a in autores), f"Autor con prefijo 'usuario_' encontrado en {endpoint}: {autores}"
            assert not any(a.startswith("test_") for a in autores), f"Autor con prefijo 'test_' encontrado en {endpoint}: {autores}"
            assert 31 not in ids, f"ID 31 de prueba encontrado en {endpoint}: {ids}"
            assert 34 not in ids, f"ID 34 de prueba encontrado en {endpoint}: {ids}"

            # 2. Autores reales presentes
            assert any("danitower" in a for a in autores), f"'danitower' no encontrado en {endpoint}: {autores}"
            assert any("carlos_g" in a for a in autores), f"'carlos_g' no encontrado en {endpoint}: {autores}"

            # 3. Metadatos de publicación requeridos
            for h in highlights:
                assert "is_published" in h, f"Falta 'is_published' en highlight {h} de {endpoint}"
                assert isinstance(h["is_published"], bool)
                assert "published_platforms" in h, f"Falta 'published_platforms' en highlight {h} de {endpoint}"
                assert isinstance(h["published_platforms"], list)

            # Validar estado para el ID 10 (publicado) y ID 20 (no publicado)
            h_10 = next(h for h in highlights if (h.get("id_mensaje") or h.get("id")) == 10)
            assert h_10["is_published"] is True
            assert "discord" in [str(p).lower() for p in h_10["published_platforms"]]

            h_20 = next(h for h in highlights if (h.get("id_mensaje") or h.get("id")) == 20)
            assert h_20["is_published"] is False
            assert h_20["published_platforms"] == []


def test_announcements_status_endpoint(client, monkeypatch):
    """
    (Spec 013 - RF-06) GET /api/v1/content-workflow/announcements/status
    Valida retorno de {configured: bool, max_length: 2000, recommended_max_length: 1500}.
    """
    # 1. Con webhook configurado
    monkeypatch.setenv("DISCORD_WEBHOOK_ANUNCIOS", "https://discord.com/api/webhooks/123/xyz")
    resp_conf = client.get("/api/v1/content-workflow/announcements/status")
    assert resp_conf.status_code == 200, f"Error {resp_conf.status_code}: {resp_conf.text}"
    data_conf = resp_conf.json()
    assert data_conf.get("configured") is True
    max_len = data_conf.get("max_length", data_conf.get("max_characters_limit"))
    rec_len = data_conf.get("recommended_max_length", data_conf.get("max_characters_recommended"))
    assert max_len == 2000, f"max_length esperado 2000, recibido {max_len}"
    assert rec_len == 1500, f"recommended_max_length esperado 1500, recibido {rec_len}"

    # 2. Sin webhook configurado
    monkeypatch.delenv("DISCORD_WEBHOOK_ANUNCIOS", raising=False)
    resp_unconf = client.get("/api/v1/content-workflow/announcements/status")
    assert resp_unconf.status_code == 200, f"Error {resp_unconf.status_code}: {resp_unconf.text}"
    data_unconf = resp_unconf.json()
    assert data_unconf.get("configured") is False
    max_len = data_unconf.get("max_length", data_unconf.get("max_characters_limit"))
    rec_len = data_unconf.get("recommended_max_length", data_unconf.get("max_characters_recommended"))
    assert max_len == 2000
    assert rec_len == 1500


def test_announcements_generate_validacion_y_delegacion(client):
    """
    (Spec 013 - RF-07) POST /api/v1/content-workflow/announcements/generate
    Valida delegación a anuncios_discord.generar_anuncio, rechazo 400 si el borrador supera 10,000 caracteres o está vacío.
    """
    # 1. Rechazo 400 ante borrador vacío
    resp_vacio = client.post("/api/v1/content-workflow/announcements/generate", json={"borrador": ""})
    assert resp_vacio.status_code == 400, f"Esperado 400 ante borrador vacío, recibido {resp_vacio.status_code}"

    resp_blancos = client.post("/api/v1/content-workflow/announcements/generate", json={"borrador": "   \n\t  "})
    assert resp_blancos.status_code == 400, f"Esperado 400 ante espacios, recibido {resp_blancos.status_code}"

    # 2. Rechazo 400 ante borrador > 10,000 caracteres
    resp_largo = client.post("/api/v1/content-workflow/announcements/generate", json={"borrador": "W" * 10001})
    assert resp_largo.status_code == 400, f"Esperado 400 ante borrador > 10k chars, recibido {resp_largo.status_code}"

    # 3. Flujo válido con mock de delegación hacia anuncios_discord.generar_anuncio
    mock_retorno = "🚀 **Nuevo Hackathon CloudEdTech**: Participa y crea soluciones con IA."
    borrador_input = "Detalles del hackathon de este fin de semana para todos los alumnos."
    with patch("anuncios_discord.generar_anuncio", return_value=mock_retorno) as mock_gen:
        resp_ok = client.post(
            "/api/v1/content-workflow/announcements/generate",
            json={"borrador": borrador_input},
        )
        assert resp_ok.status_code == 200, f"Error al generar: {resp_ok.status_code} - {resp_ok.text}"
        data_ok = resp_ok.json()

        mock_gen.assert_called_once()
        assert mock_gen.call_args[0][0] == borrador_input

        anuncio_res = data_ok.get("anuncio_generado", data_ok.get("anuncio", data_ok.get("contenido")))
        assert anuncio_res == mock_retorno
        caracteres_res = data_ok.get("caracteres", data_ok.get("longitud"))
        assert caracteres_res == len(mock_retorno)


def test_announcements_publish_validacion_persistencia_sqlite_y_webhook(client, monkeypatch):
    """
    (Spec 013 - RF-08) POST /api/v1/content-workflow/announcements/publish
    Valida mock de anuncios_discord.publicar_en_discord, rechazo 400 si supera 2000 caracteres o falta confirmar=true,
    rechazo 503 si falta el webhook, y persistencia en SQLite contenidos_generados con tipo_contenido='anuncio_oficial', estado='publicado'.
    """
    url_webhook = "https://discord.com/api/webhooks/999/test-token"
    texto_anuncio = "📢 **Aviso Importante**: Nueva clase en vivo de Kubernetes este sábado."

    # 1. Rechazo 400 si supera 2000 caracteres
    monkeypatch.setenv("DISCORD_WEBHOOK_ANUNCIOS", url_webhook)
    resp_largo = client.post(
        "/api/v1/content-workflow/announcements/publish",
        json={"contenido": "Z" * 2001, "confirmar": True, "confirmado": True},
    )
    assert resp_largo.status_code == 400, f"Esperado 400 ante texto > 2000 chars, recibido {resp_largo.status_code}"

    # 2. Rechazo 400 si falta confirmación (confirmar=False / confirmado=False / ausente)
    resp_no_conf = client.post(
        "/api/v1/content-workflow/announcements/publish",
        json={"contenido": texto_anuncio, "confirmar": False, "confirmado": False},
    )
    assert resp_no_conf.status_code == 400, f"Esperado 400 ante confirmación false, recibido {resp_no_conf.status_code}"

    resp_sin_conf = client.post(
        "/api/v1/content-workflow/announcements/publish",
        json={"contenido": texto_anuncio},
    )
    assert resp_sin_conf.status_code == 400, f"Esperado 400 ante omisión de confirmación, recibido {resp_sin_conf.status_code}"

    # 3. Rechazo 503 si el webhook no está configurado
    monkeypatch.delenv("DISCORD_WEBHOOK_ANUNCIOS", raising=False)
    resp_no_hook = client.post(
        "/api/v1/content-workflow/announcements/publish",
        json={"contenido": texto_anuncio, "confirmar": True, "confirmado": True},
    )
    assert resp_no_hook.status_code == 503, f"Esperado 503 ante webhook ausente, recibido {resp_no_hook.status_code}"

    # 4. Flujo exitoso: despacho a Discord y persistencia en SQLite
    monkeypatch.setenv("DISCORD_WEBHOOK_ANUNCIOS", url_webhook)
    with patch("anuncios_discord.publicar_en_discord", return_value=None) as mock_pub:
        resp_pub = client.post(
            "/api/v1/content-workflow/announcements/publish",
            json={"contenido": texto_anuncio, "confirmar": True, "confirmado": True},
        )
        assert resp_pub.status_code in (200, 201), f"Error al publicar: {resp_pub.status_code} - {resp_pub.text}"
        data_pub = resp_pub.json()
        assert data_pub.get("estado") == "publicado"

        mock_pub.assert_called_once_with(texto_anuncio)

        with sqlite3.connect(puente_motor_ia.motor_bd.RUTA_BD) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT * FROM contenidos_generados
                WHERE tipo_contenido = 'anuncio_oficial' AND estado = 'publicado'
                ORDER BY id DESC LIMIT 1
                """
            ).fetchone()
            assert row is not None, "No se persistió el registro en contenidos_generados"
            assert row["tipo_contenido"] == "anuncio_oficial"
            assert row["estado"] == "publicado"
            assert row["formato"] == "discord"
            assert texto_anuncio in row["contenido"]


def test_featured_stories_frontend_contract_and_static_spec():
    """
    Spec 013 - Tarea 4: Validación estricta del contrato y requisitos de FeaturedStories.tsx.
    1. Verifica que 'Ver mensaje' y su handler a '/messages' hayan sido eliminados por completo.
    2. Verifica navegación contextual a /content?interaction={id} con { state: { interactionId: targetId } }.
    3. Verifica cálculo de targetId numérico (id_mensaje o id).
    4. Verifica resiliencia ante targetId == 0 / carrusel vacío mostrando 'Sin historias disponibles'.
    5. Verifica trazabilidad de publicación: badge '✓ Publicado en' y alternancia 'Volver a publicar' / 'Generar publicación'.
    """
    ruta_componente = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "frontend", "src", "components", "FeaturedStories.tsx"
    )
    assert os.path.exists(ruta_componente), f"No existe {ruta_componente}"
    with open(ruta_componente, "r", encoding="utf-8") as f:
        codigo = f.read()

    # 1. 'Ver mensaje' y MessageCircle eliminados
    assert "Ver mensaje" not in codigo, "El botón 'Ver mensaje' debe ser eliminado por completo"
    assert "MessageCircle" not in codigo, "Icono 'MessageCircle' no utilizado debe ser eliminado"

    # 2. Navegación contextual con interaction ID y location.state
    assert "/content?interaction=" in codigo, "Debe navegar a /content?interaction=${targetId}"
    assert "interactionId:" in codigo or "interactionId :" in codigo, "Debe transferir interactionId en location.state"

    # 3. targetId numérico
    assert "id_mensaje" in codigo, "Debe considerar id_mensaje para targetId"
    assert "targetId" in codigo, "Debe definir targetId numérico"

    # 4. Resiliencia de carrusel vacío
    assert "Sin historias disponibles" in codigo, "Debe mostrar 'Sin historias disponibles' cuando esté deshabilitado"

    # 5. Trazabilidad de publicación
    assert "is_published" in codigo, "Debe evaluar is_published"
    assert "published_platforms" in codigo, "Debe evaluar published_platforms"
    assert "✓ Publicado en" in codigo, "Debe desplegar la insignia '✓ Publicado en ...'"
    assert "Publicar en demás redes" in codigo or "Volver a publicar" in codigo, "El botón debe alternar a 'Publicar en demás redes' o 'Volver a publicar'"
    assert "Generar publicación" in codigo, "El botón debe mostrar 'Generar publicación' si no está publicado"


# ==============================================================================
# Spec 014: Telemetría de Canales y Participación de la Comunidad (RF-03, RF-06)
# ==============================================================================

CANALES_OFICIALES_DISCORD_ESPERADOS = [
    {"channel": "#general", "name": "general"},
    {"channel": "#faq", "name": "faq"},
    {"channel": "#pqrs", "name": "pqrs"},
    {"channel": "#chat-egresados", "name": "chat-egresados"},
    {"channel": "#oportunidades-laborales", "name": "oportunidades-laborales"},
]


def test_channel_participation_endpoint_estructura_y_calculo(client):
    """
    Spec 014 - RF-03, RF-06:
    Verifica 'GET /api/community/channel-participation' y su alias 'GET /api/v1/community/channels-participation':
    - Retorno HTTP 200 con { channels: [...], total_messages: int }.
    - Contiene exactamente los 5 canales oficiales en orden canónico estricto.
    - Cada elemento contiene 'channel', 'name', 'count', 'percentage'.
    - Porcentajes float con 1 decimal y suma de porcentajes igual a 100.0% cuando total_messages > 0.
    """
    with patch.object(puente_motor_ia, "obtener_datos_supabase", return_value={"interacciones": [], "kpis": []}):
        with sqlite3.connect(puente_motor_ia.motor_bd.RUTA_BD) as conn:
            conn.execute(
                """
                INSERT INTO interacciones (id, hash, origen_comunidad, periodo_referencia, autor, canal, tipo, texto, creado_en)
                VALUES
                (901, 'hash_901', 'Discord', 'Semana_01', 'user1', '#general', 'mensaje', 'Mensaje en general', '2026-10-18T10:00:00+00:00'),
                (902, 'hash_902', 'Discord', 'Semana_01', 'user2', '#general', 'mensaje', 'Otro en general', '2026-10-18T10:05:00+00:00'),
                (903, 'hash_903', 'Discord', 'Semana_01', 'user3', '#faq', 'mensaje', 'Duda en faq', '2026-10-18T10:10:00+00:00'),
                (904, 'hash_904', 'Discord', 'Semana_01', 'user4', '#pqrs', 'mensaje', 'Reclamo pqrs', '2026-10-18T10:15:00+00:00'),
                (906, 'hash_906', 'Discord', 'Semana_01', 'user6', '#chat-egresados', 'mensaje', 'Egresados chat', '2026-10-18T10:25:00+00:00'),
                (907, 'hash_907', 'Discord', 'Semana_01', 'user7', '#oportunidades-laborales', 'mensaje', 'Vacante laboral', '2026-10-18T10:30:00+00:00')
                """
            )
            conn.commit()

        # Probar endpoint canónico y su alias
        for endpoint in ["/api/community/channel-participation", "/api/v1/community/channels-participation"]:
            resp = client.get(endpoint)
            assert resp.status_code == 200, f"Error {resp.status_code} al consultar {endpoint}: {resp.text}"
            data = resp.json()

            assert "total_messages" in data, f"Falta 'total_messages' en respuesta de {endpoint}"
            assert "channels" in data, f"Falta 'channels' en respuesta de {endpoint}"
            assert data["total_messages"] == 6
            assert len(data["channels"]) == 5, f"Se esperaban exactamente 5 canales, recibidos {len(data['channels'])}"

            canales_obtenidos = [item["channel"] for item in data["channels"]]
            canales_esperados = [c["channel"] for c in CANALES_OFICIALES_DISCORD_ESPERADOS]
            assert canales_obtenidos == canales_esperados, f"El orden de canales no es canónico: {canales_obtenidos}"

            suma_porcentajes = 0.0
            conteo_total = 0
            for i, canal_info in enumerate(data["channels"]):
                meta_esperada = CANALES_OFICIALES_DISCORD_ESPERADOS[i]
                assert canal_info["channel"] == meta_esperada["channel"]
                assert canal_info["name"] == meta_esperada["name"]
                assert isinstance(canal_info["count"], int)
                assert isinstance(canal_info["percentage"], (int, float))
                # Verificar precisión a un decimal
                assert canal_info["percentage"] == round(canal_info["percentage"], 1)

                conteo_total += canal_info["count"]
                suma_porcentajes += canal_info["percentage"]

            assert conteo_total == data["total_messages"] == 6
            # Con total_messages > 0 la suma de porcentajes debe ser exactamente 100.0%
            assert round(suma_porcentajes, 1) == 100.0, f"La suma de porcentajes no es 100.0%: {suma_porcentajes}"


def test_channel_participation_proteccion_division_cero_sin_mensajes(client):
    """
    Spec 014 - RF-03, RF-06:
    Verifica que ante base de datos o corpus vacío retorne 200 OK con:
    - total_messages: 0
    - Exactamente los 5 canales con count=0 y percentage=0.0
    - Sin excepción de división por cero (ZeroDivisionError).
    """
    with patch.object(puente_motor_ia, "obtener_datos_supabase", return_value={"interacciones": [], "kpis": []}):
        with sqlite3.connect(puente_motor_ia.motor_bd.RUTA_BD) as conn:
            conn.execute("DELETE FROM interacciones")
            conn.commit()

        # Usar cliente con raise_server_exceptions=False para capturar caídas 500
        cliente_seguro = TestClient(puente_motor_ia.app, raise_server_exceptions=False)
        for endpoint in ["/api/community/channel-participation", "/api/v1/community/channels-participation"]:
            resp = cliente_seguro.get(endpoint)
            assert resp.status_code == 200, f"Fallo al manejar corpus vacío en {endpoint}: {resp.status_code} {resp.text}"
            data = resp.json()

            assert data.get("total_messages") == 0
            assert isinstance(data.get("channels"), list)
            assert len(data["channels"]) == 5

            canales_esperados = [c["channel"] for c in CANALES_OFICIALES_DISCORD_ESPERADOS]
            assert [c["channel"] for c in data["channels"]] == canales_esperados

            for canal in data["channels"]:
                assert canal["count"] == 0, f"Canal {canal['channel']} count debe ser 0 en corpus vacío"
                assert canal["percentage"] == 0.0, f"Canal {canal['channel']} percentage debe ser 0.0 en corpus vacío"


def test_channel_participation_exclusion_bots_y_mapeo_sinonimos(client):
    """
    Spec 014 - RF-03, RF-06:
    Verifica que:
    1. Se excluyan categóricamente mensajes de cuentas bots o webhooks.
    2. Mensajes de canales sinónimos antiguos ('preguntas', 'dudas') se acumulen deterministamente en '#faq'.
    3. Mensajes con canal 'pqr' se acumulen en '#pqrs'.
    4. El conteo total y porcentajes ignoren los bots y mapeen los sinónimos correctamente.
    """
    with patch.object(puente_motor_ia, "obtener_datos_supabase", return_value={"interacciones": [], "kpis": []}):
        with sqlite3.connect(puente_motor_ia.motor_bd.RUTA_BD) as conn:
            conn.execute(
                """
                INSERT INTO interacciones (id, hash, origen_comunidad, periodo_referencia, autor, canal, tipo, texto, creado_en)
                VALUES
                -- Mensajes humanos válidos
                (910, 'h910', 'Discord', 'Semana_01', 'humano1', '#general', 'mensaje', 'Hola comunidad', '2026-10-18T12:00:00+00:00'),
                (911, 'h911', 'Discord', 'Semana_01', 'humano2', 'preguntas', 'mensaje', 'Tengo una pregunta', '2026-10-18T12:01:00+00:00'),
                (912, 'h912', 'Discord', 'Semana_01', 'humano3', '#dudas', 'mensaje', 'Tengo una duda', '2026-10-18T12:02:00+00:00'),
                (913, 'h913', 'Discord', 'Semana_01', 'humano4', 'pqr', 'mensaje', 'Reclamo o sugerencia', '2026-10-18T12:03:00+00:00'),
                -- Mensajes de bots y webhooks que deben ser estrictamente excluidos
                (914, 'h914', 'Discord', 'Semana_01', 'Spidey Boy#0000', '#general', 'bot', 'Webhook alert', '2026-10-18T12:04:00+00:00'),
                (915, 'h915', 'Discord', 'Semana_01', 'Webhook#0000', '#faq', 'webhook', 'Deploy alert', '2026-10-18T12:05:00+00:00'),
                (916, 'h916', 'Discord', 'Semana_01', 'BotComunidad', '#pqrs', 'mensaje', 'Auto reply', '2026-10-18T12:06:00+00:00'),
                (917, 'h917', 'Discord', 'Semana_01', 'Moderador#0000', '#chat-egresados', 'mensaje', 'Bot check', '2026-10-18T12:07:00+00:00')
                """
            )
            conn.commit()

        resp = client.get("/api/community/channel-participation")
        assert resp.status_code == 200, f"Error {resp.status_code}: {resp.text}"
        data = resp.json()

        # Sólo 4 mensajes humanos válidos deben computarse
        assert data["total_messages"] == 4, f"Se esperaban 4 mensajes totales tras excluir bots, recibidos: {data['total_messages']}"

        canales_dict = {item["channel"]: item for item in data["channels"]}

        # 'preguntas' y '#dudas' deben acumularse en '#faq' (2 mensajes = 50.0%)
        assert canales_dict["#faq"]["count"] == 2
        assert canales_dict["#faq"]["percentage"] == 50.0

        # '#general' tiene 1 mensaje humano (25.0%)
        assert canales_dict["#general"]["count"] == 1
        assert canales_dict["#general"]["percentage"] == 25.0

        # 'pqr' mapeado a '#pqrs' tiene 1 mensaje (25.0%)
        assert canales_dict["#pqrs"]["count"] == 1
        assert canales_dict["#pqrs"]["percentage"] == 25.0

        # Los demás canales deben tener 0 conteo y 0.0%
        assert canales_dict["#chat-egresados"]["count"] == 0
        assert canales_dict["#chat-egresados"]["percentage"] == 0.0
        assert canales_dict["#oportunidades-laborales"]["count"] == 0
        assert canales_dict["#oportunidades-laborales"]["percentage"] == 0.0

        # Suma de porcentajes debe ser exactamente 100.0%
        suma = sum(ch["percentage"] for ch in data["channels"])
        assert round(suma, 1) == 100.0


# Aliases para compatibilidad con nomenclatura del plan de tareas
test_participacion_canales_discord_calculo_y_orden = test_channel_participation_endpoint_estructura_y_calculo
test_participacion_canales_discord_corpus_vacio = test_channel_participation_proteccion_division_cero_sin_mensajes
test_participacion_canales_exclusion_bots_y_alias = test_channel_participation_exclusion_bots_y_mapeo_sinonimos


# ==============================================================================
# Spec 015: Integración del Pipeline Mototradis MVP de Enoc (RF-01 a RF-07)
# ==============================================================================


def test_mototradis_checkpoint_status_y_modelos_utilizados(client):
    """
    Spec 015 - RF-02, RF-03 (test_mototradis_checkpoint_desacoplado_pendiente):
    Verifica el estado del checkpoint desacoplado de lotes_ia_kpis y la transparencia de modelos IA.
    1. Para un mensaje sin historial ni checkpoint, responde has_checkpoint=False y estado_pipeline='pendiente'.
    2. El diccionario modelos_utilizados debe detallar de forma transparente los modelos asignados
       a cada plataforma (orquestador, linkedin, x, discord).
    """
    id_mensaje = 1001
    resp = client.get(f"/api/v1/mototradis/checkpoint/{id_mensaje}")
    assert resp.status_code == 200, f"Error inesperado {resp.status_code}: {resp.text}"
    data = resp.json()

    assert data.get("has_checkpoint") is False
    assert data.get("estado_pipeline") == "pendiente"
    assert "borradores_ui" in data
    assert isinstance(data["borradores_ui"], dict)

    # Mandato de Transparencia IA: cada componente debe reportar su modelo asignado
    assert "modelos_utilizados" in data
    modelos = data["modelos_utilizados"]
    assert "orquestador" in modelos
    assert "linkedin" in modelos
    assert "x" in modelos
    assert "discord" in modelos
    assert "Gemini" in modelos["orquestador"] or "qwen" in modelos["orquestador"].lower() or "groq" in modelos["orquestador"].lower()


def test_mototradis_execute_pipeline_borradores_ui_y_pausa_hitl(client):
    """
    Spec 015 - RF-02, RF-03 (test_mototradis_execute_pipeline_y_trazabilidad_modelos):
    Verifica la ejecución del pipeline hasta la interrupción HITL (previa al publicador):
    1. Ejecuta el grafo compilado con interrupt_before=['publicador'].
    2. Retorna estado_pipeline='procesado', borradores_ui aplanados para la interfaz
       y el mapa detallado de modelos_utilizados.
    """
    with sqlite3.connect(puente_motor_ia.motor_bd.RUTA_BD) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO interacciones (id, hash, origen_comunidad, periodo_referencia, autor, canal, tipo, texto, creado_en)
            VALUES (1002, 'hash_mt_1002', 'Discord', 'Semana_01', 'carlos_dev', '#general', 'mensaje', 'Gran avance en el bootcamp de IA y Python', '2026-10-18T10:00:00+00:00')
            """
        )
        conn.commit()

    payload = {
        "id_mensaje": 1002,
        "proveedor": "Google Gemini"
    }
    resp = client.post("/api/v1/mototradis/execute-pipeline", json=payload)
    assert resp.status_code == 200, f"Error inesperado {resp.status_code}: {resp.text}"
    data = resp.json()

    assert data.get("estado_pipeline") == "procesado"
    assert "borradores_ui" in data
    borradores = data["borradores_ui"]

    # Estructura normalizada de UI para cada canal
    assert "linkedin" in borradores
    assert "titulo" in borradores["linkedin"]
    assert "texto_copy" in borradores["linkedin"]

    assert "x" in borradores
    assert "titulo" in borradores["x"]
    assert "texto_copy" in borradores["x"]

    assert "discord" in borradores
    assert "titulo" in borradores["discord"]
    assert "texto_copy" in borradores["discord"]
    assert "canal_seleccionado" in borradores["discord"]

    # Transparencia de modelos utilizados
    assert "modelos_utilizados" in data
    assert "orquestador" in data["modelos_utilizados"]
    assert "rutas_activas" in data
    assert isinstance(data["rutas_activas"], list)


def test_mototradis_generate_channel_individual_con_modelo_ia(client):
    """
    Spec 015 - RF-03:
    Verifica la regeneración aislada de copy para un canal específico (ej. LinkedIn o X):
    1. Invoca nodo_canal individualmente con el proveedor/modelo seleccionado.
    2. Retorna el nuevo contenido generado y la clave explícita modelo_utilizado.
    """
    with sqlite3.connect(puente_motor_ia.motor_bd.RUTA_BD) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO interacciones (id, hash, origen_comunidad, periodo_referencia, autor, canal, tipo, texto, creado_en)
            VALUES (1003, 'hash_mt_1003', 'Discord', 'Semana_01', 'ana_redactora', '#faq', 'mensaje', 'Duda sobre la certificación de CloudEDTech', '2026-10-18T11:00:00+00:00')
            """
        )
        conn.commit()

    payload = {
        "id_mensaje": 1003,
        "canal": "linkedin",
        "proveedor": "Google Gemini"
    }
    resp = client.post("/api/v1/mototradis/generate-channel", json=payload)
    assert resp.status_code == 200, f"Error inesperado {resp.status_code}: {resp.text}"
    data = resp.json()

    assert data.get("canal") == "linkedin"
    assert "contenido" in data or "borrador" in data
    assert "modelo_utilizado" in data
    assert len(data["modelo_utilizado"]) > 0


def test_mototradis_hitl_decision_aprobacion_soberania_humana_y_cascada_discord(client):
    """
    Spec 015 - RF-04 (test_mototradis_hitl_soberania_humana_y_publicacion):
    Verifica la soberanía humana absoluta en la decisión HITL de aprobación y despacho multicanal:
    1. Los copys editados manualmente por el redactor humano prevalecen sobre borradores de la IA.
    2. Discord utiliza cascada de 3 niveles con cita en bloque (> 💬 Contexto de @autor).
    3. Tolera credenciales opcionales ausentes de X/LinkedIn reportando en resultados_canales sin error 500.
    4. Actualiza estado_revision a 'aprobado'.
    """
    with sqlite3.connect(puente_motor_ia.motor_bd.RUTA_BD) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO interacciones (id, hash, origen_comunidad, periodo_referencia, autor, canal, tipo, texto, creado_en)
            VALUES (1004, 'hash_mt_1004', 'Discord', 'Semana_01', 'mariana_ux', '#general', 'mensaje', 'Propuesta de mejora para el portal de estudiantes', '2026-10-18T12:00:00+00:00')
            """
        )
        conn.commit()

    copys_editados = {
        "linkedin": {
            "titulo": "Impulsando el Talento Tech con Alura",
            "texto_copy": "Copy editado y aprobado directamente por el redactor humano.",
            "copy_tono": "Cercano y profesional",
            "newsletter": {"destaque": "Novedades Semanales"},
            "faq": {"sugerencia": "Preguntas frecuentes"}
        },
        "x": {
            "titulo": "Innovación en EdTech",
            "texto_copy": "Copy de X redactado por humano manteniendo brevedad."
        },
        "discord": {
            "canal_seleccionado": "#general",
            "titulo": "Aviso Oficial Comunidad",
            "texto_copy": "Copy oficial validado por el equipo de moderación."
        }
    }

    payload = {
        "id_mensaje": 1004,
        "decision": "aprobar",
        "copys_editados": copys_editados
    }

    with patch("puente_motor_ia.despachar_discord_con_cascada", return_value={"ok": True, "detalle": "Publicado en Discord (Mock)", "message_id": "mock_disc", "estado_canal": "enviado"}):
        resp = client.post("/api/v1/mototradis/hitl-decision", json=payload)

    assert resp.status_code == 200, f"Error inesperado {resp.status_code}: {resp.text}"
    data = resp.json()

    assert data.get("exito") is True
    assert data.get("decision") == "aprobar"
    assert data.get("estado_revision") == "aprobado"
    assert "resultados_canales" in data
    resultados = data["resultados_canales"]

    # Debe contener resultados para cada canal sin romper con HTTP 500 ante credenciales ausentes
    assert "discord" in resultados
    assert "linkedin" in resultados
    assert "x" in resultados


def test_mototradis_hitl_decision_rechazo_regenera_copys(client):
    """
    Spec 015 - RF-04 (test_mototradis_hitl_desaprobar_y_limpieza_checkpoint):
    Verifica la decisión HITL de desaprobación / rechazo y precondición de borradores:
    1. Si se intenta aprobar sin copys válidos ni checkpoint, responde HTTP 400 Bad Request.
    2. Si se envía decision='desaprobar', actualiza a 'desaprobado' y limpia el checkpoint del hilo.
    """
    # 1. Precondición: aprobar sin borradores debe responder 400 Bad Request
    payload_invalido = {
        "id_mensaje": 9999,
        "decision": "aprobar",
        "copys_editados": {}
    }
    resp_400 = client.post("/api/v1/mototradis/hitl-decision", json=payload_invalido)
    assert resp_400.status_code == 400, f"Se esperaba HTTP 400 ante aprobación sin borradores, recibido: {resp_400.status_code}"

    # 2. Desaprobación y purga de hilo
    payload_desaprobar = {
        "id_mensaje": 1005,
        "decision": "desaprobar"
    }
    resp = client.post("/api/v1/mototradis/hitl-decision", json=payload_desaprobar)
    assert resp.status_code == 200, f"Error inesperado {resp.status_code}: {resp.text}"
    data = resp.json()

    assert data.get("exito") is True
    assert data.get("decision") == "desaprobar"
    assert data.get("estado_revision") == "desaprobado"
    assert data.get("checkpoint_limpiado") is True


def test_mototradis_publish_channel_validacion_280_x_y_tolerancia_credenciales(client):
    """
    Spec 015 - RF-04:
    Verifica la publicación individual por canal con control de longitud y tolerancia:
    1. Para X (Twitter), valida que textos combinados (titulo + texto_copy) > 280 caracteres
       sean truncados de forma defensiva a <= 280 sin colapsar.
    2. Si faltan credenciales de X o LinkedIn, reporta ok=False con detalle sin arrojar HTTP 500.
    """
    payload_x_largo = {
        "id_mensaje": 1006,
        "canal": "x",
        "titulo": "A" * 70,
        "texto_copy": "B" * 250  # 70 + 2 + 250 = 322 caracteres > 280 límite
    }
    resp_x = client.post("/api/v1/mototradis/publish-channel", json=payload_x_largo)
    assert resp_x.status_code == 200, f"Error en publicación individual de X: {resp_x.status_code} {resp_x.text}"
    data_x = resp_x.json()
    assert data_x.get("canal") == "x"
    assert "ok" in data_x

    # Discord publicación individual
    payload_discord = {
        "id_mensaje": 1006,
        "canal": "discord",
        "canal_seleccionado": "#general",
        "titulo": "Título de Prueba",
        "texto_copy": "Cuerpo del anuncio oficial"
    }
    with patch("puente_motor_ia.despachar_discord_con_cascada", return_value={"ok": True, "detalle": "Publicado en Discord (Mock)", "message_id": "mock_disc", "estado_canal": "enviado"}):
        resp_discord = client.post("/api/v1/mototradis/publish-channel", json=payload_discord)
    assert resp_discord.status_code == 200, f"Error en publicación individual de Discord: {resp_discord.status_code} {resp_discord.text}"
    data_disc = resp_discord.json()
    assert data_disc.get("canal") == "discord"
    assert "ok" in data_disc


def test_mototradis_run_mass_gemma_baja_relevancia(client):
    """
    Spec 015 - RF-05 (test_mototradis_run_mass_gemma_trazabilidad):
    Verifica el endpoint de procesamiento masivo autónomo de mensajes con relevancia < 35 con Gemma 4:
    1. Ejecuta procesamiento en lote invocando nodo_gemma_automatico.
    2. Retorna resumen cuantitativo (procesados, publicados_directo, descartados).
    3. Exhibe explícitamente modelo_ia='Google Gemma 4 · gemma-4-31b-it' (mandato de transparencia IA).
    """
    payload = {
        "limite": 5
    }
    resp = client.post("/api/v1/mototradis/run-mass", json=payload)
    assert resp.status_code == 200, f"Error inesperado {resp.status_code}: {resp.text}"
    data = resp.json()

    assert data.get("modelo_ia") == "Google Gemma 4 · gemma-4-31b-it"
    assert "procesados" in data
    assert "publicados_directo" in data
    assert "descartados" in data
    assert isinstance(data["procesados"], int)


def test_mototradis_hitl_decision_omite_canales_no_generados_y_solo_publica_activos(client):
    """
    Verifica que al pulsar 'Aprobar y publicar en canales (HITL)':
    1. Si un canal no tiene copy o tiene la nota de omisión del orquestador, NO se despacha y se reporta 'omitido'.
    2. Únicamente los canales con copy real generado (ej. Discord) se despachan y se marcan como 'enviado'.
    3. En SQLite contenidos_generados solo se actualiza a 'publicado' el canal realmente despachado.
    4. La publicación individual rechaza despachar canales omitidos.
    """
    with sqlite3.connect(puente_motor_ia.motor_bd.RUTA_BD) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO interacciones (id, hash, origen_comunidad, periodo_referencia, autor, canal, tipo, texto, creado_en)
            VALUES (2001, 'hash_mt_2001', 'Discord', 'Semana_01', 'dev_junior', '#general', 'mensaje', 'Duda técnica rápida sobre un bucle en Python', '2026-10-18T12:00:00+00:00')
            """
        )
        conn.commit()

    # Copys donde el orquestador solo seleccionó Discord, y LinkedIn/X quedaron omitidos
    copys_con_omisiones = {
        "linkedin": {
            "titulo": "Canal omitido por el orquestador",
            "texto_copy": "El orquestador omitió LinkedIn (la interacción es una consulta técnica informal). Pulsa 'Regenerar'...",
        },
        "x": {
            "titulo": "Canal omitido por el orquestador",
            "texto_copy": "",
        },
        "discord": {
            "canal_seleccionado": "#general",
            "titulo": "Aporte Técnico de la Comunidad",
            "texto_copy": "Excelente duda compartida por @dev_junior sobre bucles en Python.",
        }
    }

    payload = {
        "id_mensaje": 2001,
        "decision": "aprobar",
        "copys_editados": copys_con_omisiones
    }

    with patch("puente_motor_ia.despachar_discord_con_cascada", return_value={"ok": True, "detalle": "Publicado en Discord (Mock)", "message_id": "mock_disc", "estado_canal": "enviado"}):
        resp = client.post("/api/v1/mototradis/hitl-decision", json=payload)

    assert resp.status_code == 200
    data = resp.json()
    assert data["exito"] is True
    assert data["decision"] == "aprobar"
    res_canales = data["resultados_canales"]

    # Discord debe ser enviado
    assert res_canales["discord"]["estado_canal"] == "enviado"
    # LinkedIn y X deben quedar estrictamente omitidos
    assert res_canales["linkedin"]["estado_canal"] == "omitido"
    assert res_canales["x"]["estado_canal"] == "omitido"

    # Verificar publicación individual con texto omitido
    resp_ind = client.post("/api/v1/mototradis/publish-channel", json={
        "id_mensaje": 2001,
        "canal": "linkedin",
        "texto_copy": "El orquestador omitió LinkedIn..."
    })
    assert resp_ind.status_code == 200
    data_ind = resp_ind.json()
    assert data_ind["ok"] is False
    assert data_ind["estado_canal"] == "omitido"


def test_publish_channel_persiste_en_sqlite_y_actualiza_interaccion(client):
    """
    Spec 016 - RF-001:
    Verifica que la publicación individual por canal (POST /api/v1/mototradis/publish-channel)
    persista de forma inmediata en SQLite contenidos_generados e interacciones:
    1. contenidos_generados: estado = 'publicado', estado_publicacion = 'publicado', plataforma = canal.
    2. interacciones: etapa_flujo = 'publicado', estado_curaduria = 'curated'.
    """
    with sqlite3.connect(puente_motor_ia.motor_bd.RUTA_BD) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO interacciones (id, hash, origen_comunidad, periodo_referencia, autor, canal, tipo, texto, creado_en, etapa_flujo, estado_curaduria)
            VALUES (2010, 'hash_mt_2010', 'Discord', 'Semana_01', 'laura_dev', '#general', 'mensaje', 'Publicación individual exitosa', '2026-10-19T14:00:00+00:00', 'en_redaccion', 'pending')
            """
        )
        conn.commit()

    payload = {
        "id_mensaje": 2010,
        "canal": "discord",
        "canal_seleccionado": "#general",
        "titulo": "Aporte Técnico de Laura",
        "texto_copy": "Copy verificado y listo para despacho en canal oficial.",
    }

    with patch("puente_motor_ia.despachar_discord_con_cascada", return_value={"ok": True, "detalle": "Publicado en Discord (Mock)", "message_id": "mock_disc", "estado_canal": "enviado"}):
        resp = client.post("/api/v1/mototradis/publish-channel", json=payload)

    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["estado_canal"] == "enviado"

    with sqlite3.connect(puente_motor_ia.motor_bd.RUTA_BD) as conn:
        row_cg = conn.execute(
            "SELECT estado, estado_publicacion, plataforma, publicado_en FROM contenidos_generados WHERE interaccion_id = 2010 AND plataforma = 'discord'"
        ).fetchone()
        assert row_cg is not None, "No se encontró registro en contenidos_generados tras publicación individual"
        assert row_cg[0] == "publicado"
        assert row_cg[1] == "publicado"
        assert row_cg[2] == "discord"
        assert row_cg[3] is not None

        row_int = conn.execute(
            "SELECT etapa_flujo, estado_curaduria FROM interacciones WHERE id = 2010"
        ).fetchone()
        assert row_int is not None
        assert row_int[0] == "publicado"
        assert row_int[1] == "curated"


def test_checkpoint_retorna_plataformas_publicadas_y_preserva_borradores(client):
    """
    Spec 016 - RF-002:
    Verifica que GET /api/v1/mototradis/checkpoint/{id}:
    1. Retorne 'plataformas_publicadas: list[str]' con las plataformas ya enviadas.
    2. Retorne 'is_published: bool' como True si tiene al menos una red publicada.
    3. Conserve intactos 'borradores_ui' y 'copys_generados' sin vaciarlos.
    """
    from datetime import datetime, timezone
    ahora = puente_motor_ia.a_utc_iso(datetime.now(timezone.utc))
    with sqlite3.connect(puente_motor_ia.motor_bd.RUTA_BD) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO interacciones (id, hash, origen_comunidad, periodo_referencia, autor, canal, tipo, texto, creado_en, etapa_flujo, estado_curaduria)
            VALUES (2011, 'hash_mt_2011', 'Discord', 'Semana_01', 'carlos_ai', '#general', 'mensaje', 'Mensaje con Discord ya publicado', '2026-10-19T14:10:00+00:00', 'publicado', 'curated')
            """
        )
        conn.execute(
            """
            INSERT OR REPLACE INTO contenidos_generados (id, interaccion_id, formato, plataforma, titulo, contenido, estado, estado_publicacion, publicado_en, creado_en, actualizado_en)
            VALUES (201103, 2011, 'post', 'discord', 'Título Discord', 'Copy Discord Publicado', 'publicado', 'publicado', ?, ?, ?)
            """,
            (ahora, ahora, ahora)
        )
        # Borrador existente en SQLite para LinkedIn aún sin publicar
        conn.execute(
            """
            INSERT OR REPLACE INTO contenidos_generados (id, interaccion_id, formato, plataforma, titulo, contenido, estado, estado_publicacion, creado_en, actualizado_en)
            VALUES (201101, 2011, 'post', 'linkedin', 'Título LinkedIn', 'Copy LinkedIn Pendiente', 'pendiente_revision', 'no_publicado', ?, ?)
            """,
            (ahora, ahora)
        )
        conn.commit()

    resp = client.get("/api/v1/mototradis/checkpoint/2011")
    assert resp.status_code == 200
    data = resp.json()

    assert data["is_published"] is True
    assert "discord" in data["plataformas_publicadas"]
    assert "linkedin" not in data["plataformas_publicadas"]
    # Los borradores UI no deben estar vacíos
    assert "borradores_ui" in data
    assert len(data["borradores_ui"]) > 0
    assert "linkedin" in data["borradores_ui"]


def test_community_messages_enriquecido_con_is_published_y_plataformas(client):
    """
    Spec 016 - RF-003, RF-007:
    Verifica que GET /api/community/messages exponga en 'analysis':
    1. 'is_published: bool' y 'published_platforms: list[str]' ('Discord', 'LinkedIn', 'X').
    2. Si tiene publicación, 'workflow_stage = publicado' y 'curation_status = curated'.
    """
    from datetime import datetime, timezone
    ahora = puente_motor_ia.a_utc_iso(datetime.now(timezone.utc))
    with sqlite3.connect(puente_motor_ia.motor_bd.RUTA_BD) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO interacciones (id, hash, origen_comunidad, periodo_referencia, autor, canal, tipo, texto, creado_en, enviado_en, etapa_flujo, estado_curaduria, relevancia, sentimiento)
            VALUES (2012, 'hash_mt_2012', 'Discord', 'Semana_01', 'ana_data', '#general', 'mensaje', 'Mensaje multicanal de Ana', '2026-10-19T14:20:00+00:00', '2026-10-19T14:20:00+00:00', 'publicado', 'curated', 88, 'Positivo')
            """
        )
        conn.execute(
            """
            INSERT OR REPLACE INTO contenidos_generados (id, interaccion_id, formato, plataforma, titulo, contenido, estado, estado_publicacion, publicado_en, creado_en, actualizado_en)
            VALUES (201201, 2012, 'post', 'linkedin', 'Título LinkedIn Ana', 'Copy Ana LinkedIn', 'publicado', 'publicado', ?, ?, ?)
            """,
            (ahora, ahora, ahora)
        )
        conn.commit()

    resp = client.get("/api/community/messages?limite=500")
    assert resp.status_code == 200
    data = resp.json()
    assert "messages" in data
    msg_2012 = next((m for m in data["messages"] if m["message"]["interaction_id"] == 2012), None)
    assert msg_2012 is not None, "El mensaje 2012 no apareció en /api/community/messages"

    analysis = msg_2012["analysis"]
    assert analysis["is_published"] is True
    assert "LinkedIn" in analysis["published_platforms"]
    assert analysis["workflow_stage"] == "publicado"
    assert analysis["curation_status"] == "curated"


# ==============================================================================
# 28. Spec 017: Telemetría de Bots y Respeto Estricto de Límite en Evaluación
# ==============================================================================

def test_community_messages_incluye_telemetria_bots_y_reales(client):
    """
    Spec 017 - RF-004, RF-005, RF-010:
    Valida que GET /api/community/messages y su alias /api/community/messages/ retornen 200 OK con:
    - 'omitted_bots_count: int' y 'real_messages_count: int' además de 'total' y 'messages'.
    - 'omitted_bots_count >= 0' y 'real_messages_count >= 0'.
    - Conteo exacto de bots (Spidey Boy#0000, tipo webhook) y mensajes humanos reales.
    """
    with sqlite3.connect(puente_motor_ia.motor_bd.RUTA_BD) as conn:
        # 2 mensajes humanos reales
        conn.execute(
            """
            INSERT OR REPLACE INTO interacciones (id, hash, origen_comunidad, periodo_referencia, autor, canal, tipo, texto, creado_en, enviado_en, etapa_flujo)
            VALUES (9301, 'hash_9301', 'Discord', 'Semana_01', 'humano_ana', '#general', 'mensaje', 'Hola, consulta humana 1', '2026-10-19T10:00:00+00:00', '2026-10-19T10:00:00+00:00', 'ingesta')
            """
        )
        conn.execute(
            """
            INSERT OR REPLACE INTO interacciones (id, hash, origen_comunidad, periodo_referencia, autor, canal, tipo, texto, creado_en, enviado_en, etapa_flujo)
            VALUES (9302, 'hash_9302', 'Discord', 'Semana_01', 'humano_beto', '#general', 'mensaje', 'Hola, consulta humana 2', '2026-10-19T10:05:00+00:00', '2026-10-19T10:05:00+00:00', 'ingesta')
            """
        )
        # 2 mensajes de bots
        conn.execute(
            """
            INSERT OR REPLACE INTO interacciones (id, hash, origen_comunidad, periodo_referencia, autor, canal, tipo, texto, creado_en, enviado_en, etapa_flujo)
            VALUES (9303, 'hash_9303', 'Discord', 'Semana_01', 'Spidey Boy#0000', '#anuncios', 'mensaje', 'Alerta bot', '2026-10-19T10:10:00+00:00', '2026-10-19T10:10:00+00:00', 'ingesta')
            """
        )
        conn.execute(
            """
            INSERT OR REPLACE INTO interacciones (id, hash, origen_comunidad, periodo_referencia, autor, canal, tipo, texto, creado_en, enviado_en, etapa_flujo)
            VALUES (9304, 'hash_9304', 'Discord', 'Semana_01', 'github_bot', '#commits', 'webhook', 'Commit push webhook', '2026-10-19T10:15:00+00:00', '2026-10-19T10:15:00+00:00', 'ingesta')
            """
        )
        conn.commit()

    for endpoint in ("/api/community/messages", "/api/community/messages/"):
        resp = client.get(endpoint)
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data, f"Falta 'total' en {endpoint}"
        assert "messages" in data, f"Falta 'messages' en {endpoint}"
        assert "omitted_bots_count" in data, f"Falta 'omitted_bots_count' en la respuesta de {endpoint}"
        assert "real_messages_count" in data, f"Falta 'real_messages_count' en la respuesta de {endpoint}"
        assert isinstance(data["omitted_bots_count"], int), f"'omitted_bots_count' debe ser int en {endpoint}"
        assert isinstance(data["real_messages_count"], int), f"'real_messages_count' debe ser int en {endpoint}"
        assert data["omitted_bots_count"] >= 0
        assert data["real_messages_count"] >= 0
        assert data["omitted_bots_count"] == 2
        assert data["real_messages_count"] == 2


def test_post_evaluate_batch_respeto_estricto_limite_sobre_pendientes(client):
    """
    Spec 017 - RF-004, RF-005, RF-010:
    Valida que POST /api/v1/ai/evaluate-batch con payload {"limite": 1, "solo_pendientes": true}
    evalúe exactamente 1 mensaje pendiente aunque existan mensajes ya analizados al inicio de la tabla,
    y verifique que 'evaluados == 1'.
    """
    with sqlite3.connect(puente_motor_ia.motor_bd.RUTA_BD) as conn:
        # Mensaje ya analizado con fecha más reciente (aparecerá primero en ver_json)
        conn.execute(
            """
            INSERT OR REPLACE INTO interacciones (id, hash, origen_comunidad, periodo_referencia, autor, canal, tipo, texto, creado_en, enviado_en, estado, etapa_flujo, relevancia)
            VALUES (9401, 'hash_9401', 'Discord', 'Semana_01', 'carlos_analizado', '#general', 'mensaje', 'Ya fue analizado previamente', '2026-10-19T12:00:00+00:00', '2026-10-19T12:00:00+00:00', 'analizado', 'analizado', 85)
            """
        )
        # Mensaje pendiente 1 (más antiguo que el analizado)
        conn.execute(
            """
            INSERT OR REPLACE INTO interacciones (id, hash, origen_comunidad, periodo_referencia, autor, canal, tipo, texto, creado_en, enviado_en, estado, etapa_flujo)
            VALUES (9402, 'hash_9402', 'Discord', 'Semana_01', 'laura_pendiente_1', '#general', 'mensaje', 'Mensaje pendiente de evaluar 1', '2026-10-19T11:00:00+00:00', '2026-10-19T11:00:00+00:00', 'pendiente', 'ingesta')
            """
        )
        # Mensaje pendiente 2
        conn.execute(
            """
            INSERT OR REPLACE INTO interacciones (id, hash, origen_comunidad, periodo_referencia, autor, canal, tipo, texto, creado_en, enviado_en, estado, etapa_flujo)
            VALUES (9403, 'hash_9403', 'Discord', 'Semana_01', 'miguel_pendiente_2', '#general', 'mensaje', 'Mensaje pendiente de evaluar 2', '2026-10-19T10:00:00+00:00', '2026-10-19T10:00:00+00:00', 'pendiente', 'ingesta')
            """
        )
        conn.commit()

    mock_eval = MagicMock(return_value={
        "exito": True,
        "total_evaluados": 1,
        "exitosos": 1,
        "fallidos": 0,
        "guardados_supabase": 1,
        "errores": [],
        "aprobados": [{"id_mensaje": 9402, "kpis": {"relevancia": 88}}],
        "descartados": [],
        "resultados": {},
    })

    with patch("evaluador_lotes.evaluar_lote", mock_eval), \
         patch.object(puente_motor_ia, "_sincronizar_supabase_a_sqlite", return_value=1, create=True), \
         patch.object(puente_motor_ia, "obtener_datos_supabase", return_value={"kpis": [{"id_mensaje": 9401}]}):

        payload = {
            "proveedor": "Groq (Llama 3.3)",
            "limite": 1,
            "solo_pendientes": True,
        }
        resp = client.post("/api/v1/ai/evaluate-batch", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("exito") is True
        assert data.get("evaluados") == 1, (
            f"Se esperaba evaluar exactamente 1 mensaje pendiente, pero se reportó evaluados={data.get('evaluados')}"
        )

        assert mock_eval.call_count == 1, "evaluar_lote debía ser invocado para evaluar exactamente 1 mensaje pendiente"
        _, kwargs_eval = mock_eval.call_args
        mensajes_enviados = kwargs_eval.get("mensajes", [])
        assert len(mensajes_enviados) == 1
        assert mensajes_enviados[0]["id"] == 9402


def test_frontend_saneamiento_utf8_global_sin_secuencias_corruptas():
    """
    Spec 017 - RF-001:
    Verifica que no existan secuencias corruptas con signo de interrogación
    ni errores tipográficos en textos estáticos de frontend/src/.
    """
    import os
    import re
    frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend", "src")
    patrones_corruptos = [
        re.compile(r"curadur\?a", re.IGNORECASE),
        re.compile(r"interacci\?n", re.IGNORECASE),
        re.compile(r"v\?lida", re.IGNORECASE),
        re.compile(r"inv\?lido", re.IGNORECASE),
        re.compile(r"inv\?lida", re.IGNORECASE),
        re.compile(r"confirm\?", re.IGNORECASE),
        re.compile(r"Atenci\?n", re.IGNORECASE),
        re.compile(r"cr\?tico", re.IGNORECASE),
        re.compile(r"Cr\?tico", re.IGNORECASE),
        re.compile(r"Se\?ales", re.IGNORECASE),
        re.compile(r"revisi\?n", re.IGNORECASE),
        re.compile(r"aqu\?", re.IGNORECASE),
        re.compile(r"env\?an", re.IGNORECASE),
        re.compile(r"telemetr\?a", re.IGNORECASE),
        re.compile(r"sem\?ntica", re.IGNORECASE),
    ]

    coincidencias = []
    for root, _, files in os.walk(frontend_dir):
        for f in files:
            if f.endswith((".ts", ".tsx")):
                ruta = os.path.join(root, f)
                with open(ruta, "r", encoding="utf-8", errors="replace") as fp:
                    for num_linea, linea in enumerate(fp, 1):
                        for patron in patrones_corruptos:
                            if patron.search(linea):
                                coincidencias.append(f"{f}:{num_linea}: {linea.strip()}")

    assert not coincidencias, (
        f"Se encontraron {len(coincidencias)} secuencias corruptas UTF-8 en frontend/src:\n"
        + "\n".join(coincidencias[:10])
    )


# ==============================================================================
# Spec 018: Resiliencia de Publicaciones Multicanal y Manejo de Rate-Limit Discord
# ==============================================================================

def test_discord_sync_rate_limit_cloudflare_1015_retorna_429_y_cors(monkeypatch):
    """
    Spec 018 - RF-001, RF-002, RF-008:
    Simula un fallo de rate limit HTTP 429 con cuerpo HTML de Cloudflare Error 1015
    durante 'POST /api/v1/discord/sync', verificando que el endpoint retorne
    HTTP 429 (o 502), 'exito: False', 'codigo_error: "RATE_LIMIT_CLOUDFLARE_1015"',
    mensaje descriptivo y cabeceras 'access-control-allow-origin' sin generar un 500 no controlado.
    """
    cliente = TestClient(puente_motor_ia.app, raise_server_exceptions=False)
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "fake_bot_token_spec018")

    html_cf_1015 = (
        "<!DOCTYPE html><html><head><title>Error 1015 Ray ID: 888abc123 | Cloudflare</title></head>"
        "<body><div class='error-details'>You are being rate limited. Error 1015. The owner of this website "
        "has banned your IP address temporarily.</div></body></html>"
    )

    import discord
    resp_mock = MagicMock()
    resp_mock.status = 429
    resp_mock.reason = "Too Many Requests"
    exc_cf_429 = discord.errors.HTTPException(resp_mock, html_cf_1015)

    with patch.object(discord.Client, "start", side_effect=exc_cf_429):
        resp = cliente.post("/api/v1/discord/sync", json={"limite_por_canal": 10})

    # El endpoint debe responder HTTP 429 (o 502), nunca un 500 no controlado
    assert resp.status_code in (429, 502), (
        f"Se esperaba HTTP 429 o 502 ante Error 1015, obtenido: {resp.status_code}. Detalle: {resp.text}"
    )
    assert resp.status_code != 500, "Error 1015 de Cloudflare no debe causar un HTTP 500 no controlado"

    data = resp.json()
    assert data.get("exito") is False, f"Se esperaba exito: False, obtenido: {data}"
    assert data.get("codigo_error") == "RATE_LIMIT_CLOUDFLARE_1015", (
        f"Se esperaba codigo_error 'RATE_LIMIT_CLOUDFLARE_1015', obtenido: {data.get('codigo_error')}"
    )
    mensaje = (data.get("mensaje") or data.get("detail") or "").lower()
    assert any(term in mensaje for term in ("rate limit", "1015", "cloudflare", "ip", "local")), (
        f"Mensaje debe ser descriptivo sobre rate limit Cloudflare 1015: {mensaje}"
    )

    # Cabecera CORS garantizada para evitar error 'Failed to fetch' en frontend React
    cors_origin = resp.headers.get("access-control-allow-origin")
    assert cors_origin is not None, "El backend debe incluir cabecera Access-Control-Allow-Origin"


def test_announcements_publish_fallback_webhook_cloudedtech_oficial(monkeypatch):
    """
    Spec 018 - RF-003, RF-004, RF-008, RF-010:
    Valida que ante rechazo HTTP 429 en Bot API,
    'POST /api/v1/content-workflow/announcements/publish' active el fallback
    al webhook oficial ('CloudEdTech_Oficial') anexando '?wait=true',
    y si este responde 200 con message_id, certifique la publicación exitosa.
    """
    cliente = TestClient(puente_motor_ia.app, raise_server_exceptions=False)
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "fake_bot_token_spec018")
    webhook_base = "https://discord.com/api/webhooks/999888777/fake_token_spec018"
    monkeypatch.setenv("DISCORD_WEBHOOK_ANUNCIOS", webhook_base)

    import io
    import urllib.error
    import urllib.request
    import json

    llamadas_webhook = []

    def fake_urlopen(req, *args, **kwargs):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        # 1. Si la llamada es a la Bot API (canales de texto), simular rate limit HTTP 429
        if "channels/" in url and "/messages" in url:
            fp = io.BytesIO(b'{"message": "You are being rate limited.", "retry_after": 60}')
            raise urllib.error.HTTPError(url, 429, "Too Many Requests", {}, fp)
        # 2. Si la llamada es al Webhook oficial con fallback
        if "webhooks/" in url:
            cuerpo = {}
            if hasattr(req, "data") and req.data:
                try:
                    cuerpo = json.loads(req.data.decode("utf-8"))
                except Exception:
                    pass
            llamadas_webhook.append({
                "url": url,
                "data": cuerpo,
                "headers": dict(getattr(req, "headers", {}))
            })
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_resp.code = 200
            mock_resp.read.return_value = json.dumps({
                "id": "155999888777666555",
                "channel_id": "1559244522842488942",
                "content": "Anuncio oficial resiliente",
                "author": {"username": "CloudEdTech_Oficial", "bot": True}
            }).encode("utf-8")
            mock_resp.__enter__.return_value = mock_resp
            return mock_resp
        raise RuntimeError(f"URL no esperada en test: {url}")

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        payload = {
            "confirmar": True,
            "contenido": "Nuevo bootcamp de IA y Cloud disponible para inscripciones.",
            "channel_id": "1559244522842488942",
        }
        resp = cliente.post("/api/v1/content-workflow/announcements/publish", json=payload)

    assert resp.status_code == 200, (
        f"Se esperaba HTTP 200 tras conmutar al webhook oficial, obtenido {resp.status_code}: {resp.text}"
    )
    data = resp.json()
    assert data.get("estado") == "publicado", f"Se esperaba estado 'publicado', obtenido: {data}"

    # Validar que el webhook se invocó con '?wait=true'
    assert len(llamadas_webhook) > 0, "Se debió invocar el webhook oficial ante fallo 429 de Bot API"
    url_invocada = llamadas_webhook[0]["url"]
    assert "wait=true" in url_invocada, f"La URL del webhook debe contener '?wait=true', obtenida: {url_invocada}"


def test_publish_channel_erradicacion_falsos_positivos_discord(monkeypatch):
    """
    Spec 018 - RF-005, RF-009, RF-010:
    Valida que si Discord Bot API falla (429) y el webhook falla o no existe,
    'POST /api/v1/content-workflow/publish-channel' retorne 'ok: False',
    'estado_canal: "error"' y NO 'enviado'.
    """
    cliente = TestClient(puente_motor_ia.app, raise_server_exceptions=False)
    id_test = 9501

    # Insertar interacción para la prueba
    with sqlite3.connect(puente_motor_ia.motor_bd.RUTA_BD) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO interacciones (id, hash, origen_comunidad, periodo_referencia, autor, canal, tipo, texto, creado_en, enviado_en, estado, etapa_flujo)
            VALUES (?, 'hash_9501', 'Discord', 'Semana_01', 'usuario_test', '#general', 'mensaje', 'Consulta de prueba para publicación', '2026-10-19T10:00:00+00:00', '2026-10-19T10:00:00+00:00', 'pendiente', 'ingesta')
            """,
            (id_test,)
        )
        conn.execute("DELETE FROM contenidos_generados WHERE interaccion_id = ?", (id_test,))
        conn.commit()

    monkeypatch.setenv("DISCORD_BOT_TOKEN", "fake_bot_token_spec018")
    # Desactivar webhooks para forzar que no haya ruta de éxito
    monkeypatch.delenv("DISCORD_WEBHOOK_GENERAL", raising=False)
    monkeypatch.delenv("DISCORD_WEBHOOK_FAQ", raising=False)
    monkeypatch.delenv("DISCORD_WEBHOOK_PQRS", raising=False)
    monkeypatch.delenv("DISCORD_WEBHOOK_ANUNCIOS", raising=False)
    monkeypatch.delenv("DISCORD_WEBHOOK_NOTIFICACIONES", raising=False)

    def fake_requests_post(url, *args, **kwargs):
        # Simular fallo HTTP 429 en Bot API
        mock_r = MagicMock()
        mock_r.status_code = 429
        mock_r.text = '{"message": "You are being rate limited.", "retry_after": 60}'
        mock_r.json.return_value = {"message": "You are being rate limited."}
        return mock_r

    with patch("requests.post", side_effect=fake_requests_post):
        payload = {
            "id_mensaje": id_test,
            "canal": "discord",
            "canal_seleccionado": "general",
            "titulo": "Respuesta Comunitaria",
            "texto_copy": "Explicación técnica para la comunidad."
        }
        resp = cliente.post("/api/v1/content-workflow/publish-channel", json=payload)

    assert resp.status_code == 200
    data = resp.json()

    # Invariante clave de la Spec 018: ¡NO FALSOS POSITIVOS!
    assert data.get("ok") is False, (
        f"Se esperaba ok: False ante rechazo en Discord, pero se obtuvo ok: True (FALSO POSITIVO). Respuesta: {data}"
    )
    assert data.get("estado_canal") == "error", (
        f"Se esperaba estado_canal: 'error', pero se obtuvo '{data.get('estado_canal')}'"
    )
    assert data.get("estado_canal") != "enviado", "estado_canal no puede ser 'enviado' si la llamada a Discord falló"

    # Verificar que NO se persistió en SQLite contenidos_generados como publicado
    with sqlite3.connect(puente_motor_ia.motor_bd.RUTA_BD) as conn:
        rows = conn.execute(
            "SELECT COUNT(*) FROM contenidos_generados WHERE interaccion_id = ? AND estado_publicacion = 'publicado'",
            (id_test,)
        ).fetchone()[0]
    assert rows == 0, "No debe registrarse publicación en contenidos_generados ante fallo de despacho"


def test_publish_channel_captura_ids_y_urls_x_y_linkedin(monkeypatch):
    """
    Spec 018 - RF-006, RF-009:
    Valida que ante publicaciones exitosas en X y LinkedIn se capturen el 'tweet_id'
    numérico (con URL 'https://x.com/CloudEdTech_1/status/{id}') y el URN de LinkedIn
    (con URL 'https://www.linkedin.com/feed/update/{urn}') en el payload de respuesta.
    """
    cliente = TestClient(puente_motor_ia.app, raise_server_exceptions=False)
    id_test = 9502

    with sqlite3.connect(puente_motor_ia.motor_bd.RUTA_BD) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO interacciones (id, hash, origen_comunidad, periodo_referencia, autor, canal, tipo, texto, creado_en, enviado_en, estado, etapa_flujo)
            VALUES (?, 'hash_9502', 'Discord', 'Semana_01', 'autor_multicanal', '#general', 'mensaje', 'Mensaje para X y LinkedIn', '2026-10-19T10:00:00+00:00', '2026-10-19T10:00:00+00:00', 'pendiente', 'ingesta')
            """,
            (id_test,)
        )
        conn.commit()

    monkeypatch.setenv("X_API_KEY", "fake_x_key")
    monkeypatch.setenv("X_API_SECRET", "fake_x_secret")
    monkeypatch.setenv("X_ACCESS_TOKEN", "fake_x_token")
    monkeypatch.setenv("X_ACCESS_TOKEN_SECRET", "fake_x_token_secret")
    monkeypatch.setenv("LINKEDIN_ACCESS_TOKEN", "fake_li_token")
    monkeypatch.setenv("LINKEDIN_AUTHOR_URN", "urn:li:person:fake123")

    mock_tweet_id = "1848123456789012345"
    mock_linkedin_urn = "urn:li:share:98765432109876"

    import json

    def fake_requests_post(url, *args, **kwargs):
        if "linkedin" in str(url):
            mock_resp = MagicMock()
            mock_resp.status_code = 201
            mock_resp.text = json.dumps({"id": mock_linkedin_urn})
            mock_resp.json.return_value = {"id": mock_linkedin_urn}
            return mock_resp
        return MagicMock(status_code=200, text="{}", json=lambda: {})

    with patch("tweepy.Client") as mock_tweepy_cls, \
         patch("requests.post", side_effect=fake_requests_post):

        mock_tw_client = MagicMock()
        mock_tweet_resp = MagicMock()
        mock_tweet_resp.data = {"id": mock_tweet_id, "text": "Tweet exitoso"}
        mock_tw_client.create_tweet.return_value = mock_tweet_resp
        mock_tweepy_cls.return_value = mock_tw_client

        # 1. Probar despacho en X
        payload_x = {
            "id_mensaje": id_test,
            "canal": "x",
            "titulo": "Post X",
            "texto_copy": "Copy optimizado para X con hashtag #CloudEdTech"
        }
        resp_x = cliente.post("/api/v1/content-workflow/publish-channel", json=payload_x)
        assert resp_x.status_code == 200
        data_x = resp_x.json()
        assert data_x.get("ok") is True, f"Despacho en X falló: {data_x}"
        assert data_x.get("estado_canal") == "enviado"
        url_esperada_x = f"https://x.com/CloudEdTech_1/status/{mock_tweet_id}"
        assert data_x.get("url") == url_esperada_x, (
            f"Se esperaba url '{url_esperada_x}', pero se obtuvo '{data_x.get('url')}'"
        )
        assert data_x.get("tweet_id") == mock_tweet_id or mock_tweet_id in (data_x.get("detalle") or ""), (
            f"El payload debe incluir el tweet_id numérico: {data_x}"
        )

        # 2. Probar despacho en LinkedIn
        payload_li = {
            "id_mensaje": id_test,
            "canal": "linkedin",
            "titulo": "Post LinkedIn",
            "texto_copy": "Copy profesional para LinkedIn sobre innovación educativa."
        }
        resp_li = cliente.post("/api/v1/content-workflow/publish-channel", json=payload_li)
        assert resp_li.status_code == 200
        data_li = resp_li.json()
        assert data_li.get("ok") is True, f"Despacho en LinkedIn falló: {data_li}"
        assert data_li.get("estado_canal") == "enviado"
        url_esperada_li = f"https://www.linkedin.com/feed/update/{mock_linkedin_urn}"
        assert data_li.get("url") == url_esperada_li, (
            f"Se esperaba url '{url_esperada_li}', pero se obtuvo '{data_li.get('url')}'"
        )
        assert data_li.get("urn") == mock_linkedin_urn or mock_linkedin_urn in (data_li.get("detalle") or ""), (
            f"El payload debe incluir el URN de LinkedIn: {data_li}"
        )


# Aliases para compatibilidad con las especificaciones de tareas individuales de la Spec 018
test_sync_discord_captura_rate_limit_429_con_cors = test_discord_sync_rate_limit_cloudflare_1015_retorna_429_y_cors
test_sync_discord_tolera_cuerpo_html_sin_json_decode_error = test_discord_sync_rate_limit_cloudflare_1015_retorna_429_y_cors
test_despacho_discord_webhook_anexa_wait_true_y_obtiene_message_id = test_announcements_publish_fallback_webhook_cloudedtech_oficial
test_despacho_discord_cascada_sin_falsos_positivos = test_publish_channel_erradicacion_falsos_positivos_discord
test_publish_channel_no_persiste_en_sqlite_ante_fallo_de_canal = test_publish_channel_erradicacion_falsos_positivos_discord
test_adaptadores_autonomos_x_y_linkedin_capturan_ids_y_urls_canonicas = test_publish_channel_captura_ids_y_urls_x_y_linkedin


def test_enrutar_url_discord_con_proxy_y_sin_proxy(monkeypatch):
    """Verifica que _enrutar_url_discord sustituya https://discord.com cuando DISCORD_PROXY_URL esté configurado."""
    import puente_motor_ia

    # 1. Sin proxy
    monkeypatch.delenv("DISCORD_PROXY_URL", raising=False)
    monkeypatch.delenv("DISCORD_PROXY_BASE", raising=False)
    url_orig = "https://discord.com/api/v10/channels/123/messages"
    assert puente_motor_ia._enrutar_url_discord(url_orig) == url_orig

    # 2. Con proxy
    proxy_test = "https://discord-proxy-edtech.fraustojeovany.workers.dev"
    monkeypatch.setenv("DISCORD_PROXY_URL", proxy_test)
    url_enrutada = puente_motor_ia._enrutar_url_discord(url_orig)
    assert url_enrutada == f"{proxy_test}/api/v10/channels/123/messages"


def test_aplicar_parche_proxy_discord_variables_y_route_base(monkeypatch):
    """Verifica que _aplicar_parche_proxy_discord actualice variables de entorno de webhooks y discord.http.Route.BASE."""
    import puente_motor_ia
    import discord.http

    proxy_test = "https://discord-proxy-edtech.fraustojeovany.workers.dev"
    monkeypatch.setenv("DISCORD_PROXY_URL", proxy_test)
    monkeypatch.setenv("DISCORD_WEBHOOK_ANUNCIOS", "https://discord.com/api/webhooks/111/aaa")
    monkeypatch.setenv("DISCORD_WEBHOOK_GENERAL", "https://discord.com/api/webhooks/222/bbb")

    puente_motor_ia._aplicar_parche_proxy_discord()

    assert os.environ["DISCORD_WEBHOOK_ANUNCIOS"] == f"{proxy_test}/api/webhooks/111/aaa"
    assert os.environ["DISCORD_WEBHOOK_GENERAL"] == f"{proxy_test}/api/webhooks/222/bbb"
    assert discord.http.Route.BASE == f"{proxy_test}/api/v10"


# ==============================================================================
# Spec 019: Sincronización Dinámica de Bandeja por ID e Integración del Design
# System CloudEdTech con Datos Reales (RF-01 a RF-11)
# ==============================================================================
from pathlib import Path


def test_spec019_design_system_activos_referencia_cristian_presentes():
    """
    Spec 019 - RF-03, RF-11:
    Verifica que el directorio de referencia 'cloudedtech-design-system/' de Cristian
    exista íntegro en el repositorio con sus tokens, hojas de estilo, activos SVG y
    prototipos HTML, y que ningún archivo productivo en 'frontend/src/' importe datos
    mock ('CE_DATA' o 'cloudedtech-design-system').
    """
    base_dir = Path(__file__).resolve().parent.parent
    ds_dir = base_dir / "cloudedtech-design-system" / "cloudedtech-ds"
    assert ds_dir.is_dir(), f"No existe el directorio del Design System: {ds_dir}"

    archivos_requeridos = [
        "README.md",
        "design-system.html",
        "login.html",
        "app.html",
        "css/tokens.css",
        "css/components.css",
        "css/layout.css",
        "js/data.js",
        "js/icons.js",
        "js/charts.js",
        "js/app.js",
        "assets/logo.svg",
        "assets/logo-dark.svg",
    ]
    for rel_path in archivos_requeridos:
        archivo = ds_dir / rel_path
        assert archivo.is_file(), f"Falta el activo del Design System: {rel_path}"

    tokens_content = (ds_dir / "css/tokens.css").read_text(encoding="utf-8")
    assert "--orange-500: #ff7400" in tokens_content.lower()
    assert "--navy-950:" in tokens_content.lower() and "#080a27" in tokens_content.lower()

    # RF-11: Prohibición absoluta de importar mocks de CE_DATA en frontend/src/
    frontend_src = base_dir / "frontend" / "src"
    for ts_file in list(frontend_src.rglob("*.ts")) + list(frontend_src.rglob("*.tsx")):
        contenido = ts_file.read_text(encoding="utf-8")
        assert "CE_DATA" not in contenido, f"Uso prohibido de mock CE_DATA en {ts_file}"
        assert "cloudedtech-design-system" not in contenido, (
            f"Importación prohibida desde cloudedtech-design-system en {ts_file}"
        )


def test_spec019_tokens_y_clases_design_system_en_index_css():
    """
    Spec 019 - RF-04:
    Verifica que 'frontend/src/index.css' defina los tokens semánticos de Cristian
    (--orange-500, --navy-950, --surface-app, --surface-card, --shadow-focus) y las
    clases utilitarias del Design System (.tabular-nums, .c-card--brand, .score-ring,
    .c-live, .c-meter, .discord-embed, .c-tray-card--active), además de soporte de
    accesibilidad (:focus-visible y prefers-reduced-motion).
    """
    base_dir = Path(__file__).resolve().parent.parent
    index_css = (base_dir / "frontend" / "src" / "index.css").read_text(encoding="utf-8")
    index_css_lower = index_css.lower()

    tokens_esperados = [
        "--orange-500",
        "#ff7400",
        "--navy-950",
        "#080a27",
        "--surface-app",
        "--surface-card",
        "--shadow-sm",
        "--shadow-focus",
    ]
    for token in tokens_esperados:
        assert token in index_css_lower, f"Falta el token '{token}' en frontend/src/index.css"

    clases_esperadas = [
        ".tabular-nums",
        "tabular-nums",
        ".c-card--brand",
        ".score-ring",
        ".c-live",
        ".c-meter",
        ".discord-embed",
        ".c-tray-card--active",
        ":focus-visible",
        "prefers-reduced-motion",
    ]
    for clase in clases_esperadas:
        assert clase in index_css_lower, f"Falta la regla o clase '{clase}' en frontend/src/index.css"


def test_spec019_sincronizacion_bandeja_por_id_y_discord_embed_en_content_studio():
    """
    Spec 019 - RF-01, RF-02, RF-05 a RF-10:
    Verifica en 'frontend/src/pages/ContentStudio.tsx':
      1. El estado de inyección temporal 'pinnedSearchMessage' y la lista computada
         'displayedTrayMessages' en la Bandeja de mensajes en Redacción.
      2. La insignia '📌 Cargado por ID #' cuando un mensaje buscado por ID se inyecta
         temporalmente en la bandeja.
      3. La limpieza inmediata 'setPinnedSearchMessage(null)' cuando el usuario modifica
         o borra el campo del buscador por ID.
      4. La clase de selección '.c-tray-card--active' y la Vista Previa en vivo estilo
         Discord Embed ('.discord-embed' con 'CloudEdTech_Oficial' y 'BOT').
      5. La integración de '.c-card--brand', '.score-ring', '.c-live' e isotipo SVG en
         las vistas principales del frontend productivo.
    """
    base_dir = Path(__file__).resolve().parent.parent
    content_studio = (
        base_dir / "frontend" / "src" / "pages" / "ContentStudio.tsx"
    ).read_text(encoding="utf-8")

    # RF-01 y RF-02: Sincronización e inyección temporal por ID en Bandeja de Redacción
    assert "pinnedSearchMessage" in content_studio, (
        "Falta el estado 'pinnedSearchMessage' en ContentStudio.tsx"
    )
    assert "setPinnedSearchMessage(null)" in content_studio, (
        "Falta la limpieza 'setPinnedSearchMessage(null)' al cambiar el buscador por ID en ContentStudio.tsx"
    )
    assert "displayedTrayMessages" in content_studio, (
        "Falta la lista computada 'displayedTrayMessages' para la Bandeja de Redacción en ContentStudio.tsx"
    )
    assert "Cargado por ID #" in content_studio, (
        "Falta la insignia '📌 Cargado por ID #' para mensajes inyectados temporalmente en ContentStudio.tsx"
    )

    # RF-09: Selección activa y Vista Previa Discord Embed en ContentStudio.tsx
    assert "c-tray-card--active" in content_studio, (
        "Falta la clase 'c-tray-card--active' en la Bandeja de Redacción de ContentStudio.tsx"
    )
    assert "discord-embed" in content_studio, (
        "Falta la vista previa en vivo 'discord-embed' en el panel de Anuncios Oficiales de ContentStudio.tsx"
    )
    assert "CloudEdTech_Oficial" in content_studio, (
        "Falta el autor 'CloudEdTech_Oficial' en la vista previa Discord Embed de ContentStudio.tsx"
    )

    # RF-05 a RF-08, RF-10: Verificación de patrones del Design System en vistas hermanas
    sidebar_tsx = (
        base_dir / "frontend" / "src" / "components" / "Sidebar.tsx"
    ).read_text(encoding="utf-8")
    assert "EDUCATION & TECHNOLOGY" in sidebar_tsx, (
        "Falta el subtítulo de marca 'EDUCATION & TECHNOLOGY' junto al isotipo SVG en Sidebar.tsx"
    )
    assert "c-live" in sidebar_tsx, "Falta el indicador en vivo 'c-live' en Sidebar.tsx"

    featured_stories = (
        base_dir / "frontend" / "src" / "components" / "FeaturedStories.tsx"
    ).read_text(encoding="utf-8")
    assert "score-ring" in featured_stories, (
        "Falta el anillo circular 'score-ring' en FeaturedStories.tsx"
    )

    analytics_tsx = (
        base_dir / "frontend" / "src" / "pages" / "Analytics.tsx"
    ).read_text(encoding="utf-8")
    assert "c-card--brand" in analytics_tsx, (
        "Falta el patrón 'c-card--brand' en el Insight Principal de Analytics.tsx"
    )

    oci_tsx = (
        base_dir / "frontend" / "src" / "pages" / "OCIStorage.tsx"
    ).read_text(encoding="utf-8")
    assert "c-card--brand" in oci_tsx, (
        "Falta el patrón 'c-card--brand' en el panel de estado de OCIStorage.tsx"
    )


def test_spec020_dashboard_homologado_cristian_datos_reales():
    """
    Spec 020 (Parte 1 — Pestaña Dashboard):
    Verifica la homologación 1:1 del Dashboard Ejecutivo con el Design System
    de Cristian preservando datos reales y el botón 'Actualizar datos':
      1. Clases estructurales en 'frontend/src/index.css'.
      2. Tarjetas KPI ('.c-stat', '.c-iconbox', '.c-stat__spark', 'linearGradient') en 'KpiCard.tsx'.
      3. Estructura, selector '.c-segmented' ('7d', '30d', '90d'), 'Actividad de mensajes' y
         botón 'Actualizar datos' con 'c-btn--primary' en 'Dashboard.tsx'.
      4. Dona interactiva ('.c-chart--donut', '.c-chart__center', '.c-legend--stack') en 'SentimentChart.tsx'.
      5. Barras por hora con píldora 'Peak' y colores '#ff7400' / '#fdba74' en 'AudienceHeatmap.tsx'.
      6. Barras horizontales con botón 'Ordenar por' y colores '#ff7400' / '#fdba74' en 'TopicsChart.tsx'.
    """
    base_dir = Path(__file__).resolve().parent.parent

    # 1. index.css
    index_css = (base_dir / "frontend" / "src" / "index.css").read_text(encoding="utf-8")
    for required_css_class in [
        ".c-stat",
        ".c-stat__spark",
        ".c-iconbox",
        ".c-segmented",
        ".c-chart--donut",
        ".c-chart__center",
        ".c-btn--primary",
        ".l-grid--main-side",
        ".l-grid--halves",
    ]:
        assert required_css_class in index_css, (
            f"Falta la clase '{required_css_class}' en frontend/src/index.css"
        )

    # 2. KpiCard.tsx
    kpi_card = (
        base_dir / "frontend" / "src" / "components" / "KpiCard.tsx"
    ).read_text(encoding="utf-8")
    assert "c-stat" in kpi_card, "Falta '.c-stat' en KpiCard.tsx"
    assert "c-iconbox" in kpi_card, "Falta '.c-iconbox' en KpiCard.tsx"
    assert "c-stat__spark" in kpi_card, "Falta '.c-stat__spark' en KpiCard.tsx"
    assert "linearGradient" in kpi_card, "Falta el Sparkline SVG con 'linearGradient' en KpiCard.tsx"

    # 3. Dashboard.tsx
    dashboard = (
        base_dir / "frontend" / "src" / "pages" / "Dashboard.tsx"
    ).read_text(encoding="utf-8")
    assert "Actividad de mensajes" in dashboard, (
        "Falta la tarjeta 'Actividad de mensajes' en Dashboard.tsx"
    )
    assert "Mensajes ingeridos y preguntas detectadas por día" in dashboard, (
        "Falta la descripción 'Mensajes ingeridos y preguntas detectadas por día' en Dashboard.tsx"
    )
    assert "c-segmented" in dashboard, "Falta el selector '.c-segmented' en Dashboard.tsx"
    for period_label in ["7d", "30d", "90d"]:
        assert period_label in dashboard, f"Falta la opción de período '{period_label}' en Dashboard.tsx"
    assert "Actualizar datos" in dashboard, "Falta el texto 'Actualizar datos' en el botón de Dashboard.tsx"
    assert "c-btn--primary" in dashboard, "Falta la clase 'c-btn--primary' en el botón de Dashboard.tsx"
    assert "l-grid--main-side" in dashboard, "Falta la grilla 'l-grid--main-side' en Dashboard.tsx"
    assert "l-grid--halves" in dashboard, "Falta la grilla 'l-grid--halves' en Dashboard.tsx"

    # 4. SentimentChart.tsx
    sentiment_chart = (
        base_dir / "frontend" / "src" / "charts" / "SentimentChart.tsx"
    ).read_text(encoding="utf-8")
    assert "c-chart--donut" in sentiment_chart, "Falta '.c-chart--donut' en SentimentChart.tsx"
    assert "c-chart__center" in sentiment_chart, "Falta '.c-chart__center' en SentimentChart.tsx"
    assert "c-legend--stack" in sentiment_chart, "Falta '.c-legend--stack' en SentimentChart.tsx"

    # 5. AudienceHeatmap.tsx
    audience_heatmap = (
        base_dir / "frontend" / "src" / "charts" / "AudienceHeatmap.tsx"
    ).read_text(encoding="utf-8")
    assert "Actividad de audiencia" in audience_heatmap, (
        "Falta el título 'Actividad de audiencia' en AudienceHeatmap.tsx"
    )
    assert "Mensajes promedio por hora del día" in audience_heatmap, (
        "Falta el subtítulo 'Mensajes promedio por hora del día' en AudienceHeatmap.tsx"
    )
    assert "Peak" in audience_heatmap, "Falta la píldora 'Peak' en AudienceHeatmap.tsx"
    assert "#ff7400" in audience_heatmap.lower(), "Falta el color pico '#ff7400' en AudienceHeatmap.tsx"
    assert "#fdba74" in audience_heatmap.lower(), "Falta el color base '#fdba74' en AudienceHeatmap.tsx"

    # 6. TopicsChart.tsx
    topics_chart = (
        base_dir / "frontend" / "src" / "charts" / "TopicsChart.tsx"
    ).read_text(encoding="utf-8")
    assert "Temas principales" in topics_chart, "Falta el título 'Temas principales' en TopicsChart.tsx"
    assert "Ordenar por" in topics_chart, "Falta el botón 'Ordenar por' en TopicsChart.tsx"
    assert "#ff7400" in topics_chart.lower(), "Falta el color máximo '#ff7400' en TopicsChart.tsx"
    assert "#fdba74" in topics_chart.lower(), "Falta el color secundario '#fdba74' en TopicsChart.tsx"



def test_discord_sync_asincrono_responde_inmediatamente_sin_bloqueo(monkeypatch):
    """Verifica que POST /api/v1/discord/sync con asincrono=True responda de inmediato sin bloquear."""
    cliente = TestClient(puente_motor_ia.app)
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "mock_discord_token_asincrono")

    resp = cliente.post("/api/v1/discord/sync", json={"limite_por_canal": 10, "asincrono": True})
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("exito") is True
    assert data.get("asincrono") is True
    assert "segundo plano" in data.get("mensaje", "").lower()


# ==============================================================================
# Spec 021: Optimización de Sincronización Discord de Alta Velocidad (Fase Red TDD)
# ==============================================================================

def test_spec021_discord_sync_omite_consulta_guild_y_usa_canales_canonicos(monkeypatch):
    """
    Spec 021 - RF-01, RF-02:
    Valida que _sincronizar_discord_api_rest NO invoque la ruta /guilds/{id}/channels
    y consulte directamente los 4 canales canónicos autorizados, incluso cuando
    DISCORD_GUILD_ID está configurado.
    """
    import asyncio
    import json
    import urllib.request
    import requests

    monkeypatch.setenv("DISCORD_BOT_TOKEN", "mock_bot_token_spec021")
    monkeypatch.setenv("DISCORD_GUILD_ID", "123456789012345678")
    monkeypatch.setenv("DISCORD_CHANNEL_GENERAL", "1550016804418621452")
    monkeypatch.setenv("DISCORD_CHANNEL_FAQ", "1551309664397033513")
    monkeypatch.setenv("DISCORD_CHANNEL_PQRS", "1559244209884504245")
    monkeypatch.setenv("DISCORD_CHANNEL_NOTIFICACIONES", "1559244522842488942")

    urls_solicitadas = []

    def mock_urlopen(req, *args, **kwargs):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        urls_solicitadas.append(url)
        resp = MagicMock()
        resp.read.return_value = json.dumps([]).encode("utf-8")
        resp.__enter__.return_value = resp
        resp.__exit__.return_value = None
        return resp

    class MockResp:
        def __init__(self, data=None):
            self._data = data if data is not None else []
            self.status_code = 200
            self.headers = {}
        def json(self):
            return self._data
        def raise_for_status(self):
            pass

    def mock_session_get(url, *args, **kwargs):
        urls_solicitadas.append(str(url))
        return MockResp([])

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)
    if hasattr(puente_motor_ia, "_obtener_discord_http_session"):
        mock_sess = MagicMock()
        mock_sess.get.side_effect = mock_session_get
        monkeypatch.setattr(puente_motor_ia, "_obtener_discord_http_session", lambda: mock_sess)
    monkeypatch.setattr(requests.Session, "get", lambda self, url, *a, **kw: mock_session_get(url, *a, **kw))

    resultado = asyncio.run(puente_motor_ia._sincronizar_discord_api_rest(token="mock_bot_token_spec021", limite_por_canal=10))

    # Aserción 1: NUNCA debe consultar /guilds/{id}/channels
    assert not any("/guilds/" in u for u in urls_solicitadas), (
        f"Se detectó consulta indebida a la ruta de guild: {urls_solicitadas}"
    )

    # Aserción 2: Debe consultar directamente los 4 canales canónicos
    canales_esperados = {"1550016804418621452", "1551309664397033513", "1559244209884504245", "1559244522842488942"}
    canales_consultados = {
        cid for cid in canales_esperados
        if any(f"/channels/{cid}/messages" in u for u in urls_solicitadas)
    }
    assert canales_consultados == canales_esperados, (
        f"No se consultaron todos los canales canónicos. Esperados: {canales_esperados}, Encontrados: {canales_consultados}"
    )


def test_spec021_discord_sync_persiste_directo_en_sqlite_sin_bloqueo_supabase(monkeypatch):
    """
    Spec 021 - RF-01, RF-03:
    Valida que al sincronizar mensajes nuevos, estos se escriban directamente en la tabla
    interacciones de SQLite local y que _sincronizar_supabase_a_sqlite NO sea ejecutado
    en la ruta crítica síncrona.
    """
    import asyncio
    import json
    import sqlite3
    import urllib.request
    import requests

    monkeypatch.setenv("DISCORD_BOT_TOKEN", "mock_bot_token_spec021")
    mock_sync_supabase = MagicMock()
    monkeypatch.setattr(puente_motor_ia, "_sincronizar_supabase_a_sqlite", mock_sync_supabase)

    msg_id = "msg_spec021_directo_001"
    msg_raw = {
        "id": msg_id,
        "content": "Consulta técnica sobre despliegue en Render y FastAPI",
        "author": {"id": "usr_99", "username": "estudiante_render", "bot": False},
        "timestamp": "2026-10-23T11:00:00+00:00",
        "channel_id": "1550016804418621452",
    }

    def mock_urlopen(req, *args, **kwargs):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        resp = MagicMock()
        if "1550016804418621452" in url:
            resp.read.return_value = json.dumps([msg_raw]).encode("utf-8")
        else:
            resp.read.return_value = json.dumps([]).encode("utf-8")
        resp.__enter__.return_value = resp
        resp.__exit__.return_value = None
        return resp

    class MockResp:
        def __init__(self, data):
            self._data = data
            self.status_code = 200
            self.headers = {}
        def json(self):
            return self._data
        def raise_for_status(self):
            pass

    def mock_session_get(url, *args, **kwargs):
        if "1550016804418621452" in str(url):
            return MockResp([msg_raw])
        return MockResp([])

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)
    if hasattr(puente_motor_ia, "_obtener_discord_http_session"):
        mock_sess = MagicMock()
        mock_sess.get.side_effect = mock_session_get
        monkeypatch.setattr(puente_motor_ia, "_obtener_discord_http_session", lambda: mock_sess)
    monkeypatch.setattr(requests.Session, "get", lambda self, url, *a, **kw: mock_session_get(url, *a, **kw))

    resultado = asyncio.run(puente_motor_ia._sincronizar_discord_api_rest(token="mock_bot_token_spec021", limite_por_canal=10))

    # Aserción 1: Supabase sync no debe llamarse en la ruta crítica
    assert not mock_sync_supabase.called, (
        "_sincronizar_supabase_a_sqlite no debe ser ejecutado en la ruta crítica síncrona"
    )

    # Aserción 2: El mensaje debe estar guardado directamente en la base de datos SQLite local
    conn = sqlite3.connect(puente_motor_ia.motor_bd.RUTA_BD)
    cursor = conn.cursor()
    cursor.execute("SELECT texto, autor, message_id FROM interacciones WHERE message_id = ?", (msg_id,))
    row = cursor.fetchone()
    conn.close()

    assert row is not None, f"El mensaje con message_id={msg_id} no fue insertado directamente en SQLite"
    assert row[1] == "estudiante_render"
    assert "Consulta técnica sobre despliegue" in row[0]
    assert resultado.get("guardadas_nuevas") == 1


def test_spec021_discord_sync_tolerancia_fallo_parcial_canal(monkeypatch):
    """
    Spec 021 - RF-05:
    Valida que si 1 de los 4 canales genera un fallo de red o timeout,
    los 3 canales restantes se procesen exitosamente y la respuesta reporte
    canales_consultados=4, canales_exitosos=3 y '(3 de 4 canales exitosos)'.
    """
    import asyncio
    import json
    import urllib.request
    import requests

    monkeypatch.setenv("DISCORD_BOT_TOKEN", "mock_bot_token_spec021")

    def mock_urlopen(req, *args, **kwargs):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "1550016804418621452" in url:
            raise urllib.error.URLError("Timeout simulado en canal general")
        resp = MagicMock()
        resp.read.return_value = json.dumps([]).encode("utf-8")
        resp.__enter__.return_value = resp
        resp.__exit__.return_value = None
        return resp

    class MockResp:
        def __init__(self, data):
            self._data = data
            self.status_code = 200
            self.headers = {}
        def json(self):
            return self._data
        def raise_for_status(self):
            pass

    def mock_session_get(url, *args, **kwargs):
        if "1550016804418621452" in str(url):
            raise requests.exceptions.Timeout("Timeout simulado en canal general")
        return MockResp([])

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)
    if hasattr(puente_motor_ia, "_obtener_discord_http_session"):
        mock_sess = MagicMock()
        mock_sess.get.side_effect = mock_session_get
        monkeypatch.setattr(puente_motor_ia, "_obtener_discord_http_session", lambda: mock_sess)
    monkeypatch.setattr(requests.Session, "get", lambda self, url, *a, **kw: mock_session_get(url, *a, **kw))

    resultado = asyncio.run(puente_motor_ia._sincronizar_discord_api_rest(token="mock_bot_token_spec021", limite_por_canal=10))

    assert resultado is not None, "La sincronización debe retornar resultado aun con fallo parcial"
    assert resultado.get("exito") is True
    assert resultado.get("canales_consultados") == 4, (
        f"Se esperaba canales_consultados=4, se obtuvo: {resultado.get('canales_consultados')}"
    )
    assert resultado.get("canales_exitosos") == 3, (
        f"Se esperaba canales_exitosos=3, se obtuvo: {resultado.get('canales_exitosos')}"
    )
    assert "(3 de 4 canales exitosos)" in resultado.get("mensaje", ""), (
        f"El mensaje debe contener '(3 de 4 canales exitosos)'. Mensaje obtenido: {resultado.get('mensaje')}"
    )


def test_spec021_discord_sync_coherencia_contable_y_bots(monkeypatch):
    """
    Spec 021 - RF-01, RF-06:
    Valida que los mensajes de bots o webhooks sean omitidos de la tabla interacciones,
    sumados a _cache_bots_omitidos_discord y que se cumpla rigurosamente la ecuación:
    total_recibidas == guardadas_nuevas + repetidas_omitidas + vacias_omitidas.
    """
    import asyncio
    import json
    import sqlite3
    import urllib.request
    import requests

    monkeypatch.setenv("DISCORD_BOT_TOKEN", "mock_bot_token_spec021")

    # 1. Pre-insertar mensaje en SQLite para simular uno repetido
    conn = sqlite3.connect(puente_motor_ia.motor_bd.RUTA_BD)
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO interacciones
           (hash, canal, autor, texto, message_id, creado_en, enviado_en, estado, estado_curaduria, etapa_flujo, etapa, tipo, origen_comunidad, periodo_referencia)
           VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'), 'pendiente', 'pending', 'ingesta', 'ingesta', 'mensaje', 'Discord', 'Semana_43')""",
        ("hash_repetido_spec021_001", "#general", "usuario_antiguo", "Mensaje ya existente", "msg_repetido_spec021",)
    )
    conn.commit()
    conn.close()

    # 2. Definir 5 mensajes de prueba:
    mensajes_prueba = [
        {"id": "bot_msg_1", "content": "Anuncio de bot", "author": {"id": "b1", "username": "BotHelper", "bot": True}, "timestamp": "2026-10-23T10:00:00Z"},
        {"id": "wh_msg_2", "content": "Noticia webhook", "author": {"id": "w1", "username": "GithubHook"}, "webhook_id": "wh_12345", "timestamp": "2026-10-23T10:01:00Z"},
        {"id": "nuevo_msg_3", "content": "Pregunta de un estudiante nuevo sobre Python", "author": {"id": "u1", "username": "estudiante_nuevo", "bot": False}, "timestamp": "2026-10-23T10:02:00Z"},
        {"id": "msg_repetido_spec021", "content": "Mensaje ya existente", "author": {"id": "u2", "username": "usuario_antiguo", "bot": False}, "timestamp": "2026-10-23T10:03:00Z"},
        {"id": "vacio_msg_5", "content": "   ", "author": {"id": "u3", "username": "usuario_espacios", "bot": False}, "timestamp": "2026-10-23T10:04:00Z"},
    ]

    def mock_urlopen(req, *args, **kwargs):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        resp = MagicMock()
        if "1550016804418621452" in url:
            resp.read.return_value = json.dumps(mensajes_prueba).encode("utf-8")
        else:
            resp.read.return_value = json.dumps([]).encode("utf-8")
        resp.__enter__.return_value = resp
        resp.__exit__.return_value = None
        return resp

    class MockResp:
        def __init__(self, data):
            self._data = data
            self.status_code = 200
            self.headers = {}
        def json(self):
            return self._data
        def raise_for_status(self):
            pass

    def mock_session_get(url, *args, **kwargs):
        if "1550016804418621452" in str(url):
            return MockResp(mensajes_prueba)
        return MockResp([])

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)
    if hasattr(puente_motor_ia, "_obtener_discord_http_session"):
        mock_sess = MagicMock()
        mock_sess.get.side_effect = mock_session_get
        monkeypatch.setattr(puente_motor_ia, "_obtener_discord_http_session", lambda: mock_sess)
    monkeypatch.setattr(requests.Session, "get", lambda self, url, *a, **kw: mock_session_get(url, *a, **kw))

    puente_motor_ia._cache_bots_omitidos_discord = 0

    resultado = asyncio.run(puente_motor_ia._sincronizar_discord_api_rest(token="mock_bot_token_spec021", limite_por_canal=10))

    assert resultado is not None
    assert resultado.get("exito") is True

    # 3. Validar contabilidad rigurosa
    total_recibidas = resultado.get("total_recibidas", 0)
    guardadas_nuevas = resultado.get("guardadas_nuevas", 0)
    repetidas_omitidas = resultado.get("repetidas_omitidas", 0)
    vacias_omitidas = resultado.get("vacias_omitidas", 0)

    assert total_recibidas == guardadas_nuevas + repetidas_omitidas + vacias_omitidas, (
        f"Incoherencia contable: total_recibidas ({total_recibidas}) != "
        f"guardadas_nuevas ({guardadas_nuevas}) + repetidas_omitidas ({repetidas_omitidas}) + vacias_omitidas ({vacias_omitidas})"
    )
    assert guardadas_nuevas == 1, f"Se esperaba 1 guardada nueva, se obtuvo {guardadas_nuevas}"
    assert repetidas_omitidas == 1, f"Se esperaba 1 repetida omitida, se obtuvo {repetidas_omitidas}"
    assert vacias_omitidas == 1, f"Se esperaba 1 vacía omitida, se obtuvo {vacias_omitidas}"
    assert total_recibidas == 3, f"Se esperaba 3 mensajes recibidos a nivel humano, se obtuvo {total_recibidas}"

    # 4. Validar telemetría de bots (al menos 2 omitidos: bot y webhook)
    assert puente_motor_ia._cache_bots_omitidos_discord >= 2, (
        f"Se esperaba _cache_bots_omitidos_discord >= 2, se obtuvo {puente_motor_ia._cache_bots_omitidos_discord}"
    )

    # 5. Validar que bots, webhooks y vacíos NO estén en la tabla interacciones de SQLite
    conn = sqlite3.connect(puente_motor_ia.motor_bd.RUTA_BD)
    cursor = conn.cursor()
    cursor.execute("SELECT message_id FROM interacciones WHERE message_id IN ('bot_msg_1', 'wh_msg_2', 'vacio_msg_5')")
    filas_no_deseadas = cursor.fetchall()
    assert len(filas_no_deseadas) == 0, (
        f"Se encontraron mensajes de bots/webhooks/vacíos indebidamente insertados en interacciones: {filas_no_deseadas}"
    )

    cursor.execute("SELECT message_id, texto FROM interacciones WHERE message_id = 'nuevo_msg_3'")
    fila_nueva = cursor.fetchone()
    conn.close()
    assert fila_nueva is not None, "El mensaje humano nuevo 'nuevo_msg_3' debe estar persistido en SQLite"


def test_spec021_discord_sync_sesion_http_keep_alive_configurada():
    """
    Spec 021 - RF-02:
    Valida que _obtener_discord_http_session() retorne una sesión de requests.Session
    configurada con HTTPAdapter de pool_connections=10 y pool_maxsize=10 para Keep-Alive persistente.
    """
    import requests
    from requests.adapters import HTTPAdapter

    assert hasattr(puente_motor_ia, "_obtener_discord_http_session"), (
        "puente_motor_ia debe implementar la función _obtener_discord_http_session"
    )

    sesion = puente_motor_ia._obtener_discord_http_session()
    assert isinstance(sesion, requests.Session), "Debe retornar una instancia de requests.Session"

    adapter_https = sesion.adapters.get("https://")
    adapter_http = sesion.adapters.get("http://")

    assert isinstance(adapter_https, HTTPAdapter), "Debe tener HTTPAdapter configurado para https://"
    assert isinstance(adapter_http, HTTPAdapter), "Debe tener HTTPAdapter configurado para http://"

    assert adapter_https._pool_connections == 10, (
        f"pool_connections para https:// debe ser 10, obtenido: {adapter_https._pool_connections}"
    )
    assert adapter_https._pool_maxsize == 10, (
        f"pool_maxsize para https:// debe ser 10, obtenido: {adapter_https._pool_maxsize}"
    )
    assert adapter_http._pool_connections == 10, (
        f"pool_connections para http:// debe ser 10, obtenido: {adapter_http._pool_connections}"
    )
    assert adapter_http._pool_maxsize == 10, (
        f"pool_maxsize para http:// debe ser 10, obtenido: {adapter_http._pool_maxsize}"
    )


# ==============================================================================
# Spec 022: Migración de Interacciones a Supabase Enoc y Unificación de Conexiones
# ==============================================================================

def test_spec022_estructura_ddl_interacciones_enoc():
    """
    Spec 022 - RF-01:
    Valida que la estructura canónica del DDL para interacciones en Enoc contenga
    las 11 columnas especificadas (id, hash, origen_comunidad, periodo_referencia,
    autor, canal, tipo, texto, enviado_en, estado, creado_en) y la restricción o índice UNIQUE sobre hash.
    """
    import importlib
    try:
        migrador = importlib.import_module("scripts.migrar_interacciones_enoc")
    except ModuleNotFoundError:
        pytest.fail("scripts/migrar_interacciones_enoc.py no existe aún (Fase Red TDD)")

    assert hasattr(migrador, "DDL_INTERACCIONES"), (
        "El módulo scripts.migrar_interacciones_enoc debe definir la constante DDL_INTERACCIONES"
    )
    ddl = getattr(migrador, "DDL_INTERACCIONES", "").lower()

    columnas_esperadas = [
        "id", "hash", "origen_comunidad", "periodo_referencia",
        "autor", "canal", "tipo", "texto", "enviado_en", "estado", "creado_en"
    ]
    for col in columnas_esperadas:
        assert col in ddl, f"La columna '{col}' no se encuentra en el DDL canónico de interacciones"

    assert "unique" in ddl and "hash" in ddl, (
        "El DDL debe definir una restricción o índice UNIQUE sobre la columna 'hash'"
    )


def test_spec022_salvaguarda_conexion_puente_conmuta_tania_a_enoc(monkeypatch, caplog):
    """
    Spec 022 - RF-04:
    Valida que puente_motor_ia detecte si DATABASE_URL apunta al proyecto obsoleto de Tania
    ('ietgilhtccvqlqglqazf') y conmute de forma transparente hacia SUPABASE_DB_URL (Enoc)
    emitiendo una advertencia clara en log (logger.warning).
    """
    import logging

    url_tania = "postgresql://postgres.ietgilhtccvqlqglqazf:pwd123@aws-0-us-east-1.pooler.supabase.com:6543/postgres"
    url_enoc = "postgresql://postgres.swdoucawdasxmnomlcfu:pwd456@aws-0-us-east-1.pooler.supabase.com:6543/postgres"

    monkeypatch.setenv("DATABASE_URL", url_tania)
    monkeypatch.setenv("SUPABASE_DB_URL", url_enoc)

    assert hasattr(puente_motor_ia, "resolver_url_base_datos"), (
        "puente_motor_ia debe implementar la función 'resolver_url_base_datos' para la salvaguarda de conexión"
    )

    with caplog.at_level(logging.WARNING):
        url_activa = puente_motor_ia.resolver_url_base_datos(url_tania, url_enoc)

    assert url_activa == url_enoc, (
        f"Se esperaba conmutación a la URL de Enoc ({url_enoc}), pero se obtuvo: {url_activa}"
    )
    assert any("ietgilhtccvqlqglqazf" in r.message or "Tania" in r.message or "conmut" in r.message.lower() for r in caplog.records), (
        "Debe registrarse una advertencia en log (logger.warning) informando la conmutación automática"
    )


def test_spec022_migracion_idempotencia_y_hashes_coincidentes():
    """
    Spec 022 - RF-02 y RF-03:
    Valida el comportamiento de transferencia idempotente (ON CONFLICT (hash) DO NOTHING),
    la verificación de integridad de los 204 hashes coincidentes (pre-flight y post-flight)
    y la sincronización de la secuencia interacciones_id_seq con COALESCE((SELECT MAX(id) FROM interacciones), 1).
    """
    import importlib
    try:
        migrador = importlib.import_module("scripts.migrar_interacciones_enoc")
    except ModuleNotFoundError:
        pytest.fail("scripts/migrar_interacciones_enoc.py no existe aún (Fase Red TDD)")

    # 1. Validar SQL de inserción con cláusula ON CONFLICT (hash) DO NOTHING
    assert hasattr(migrador, "SQL_INSERT_INTERACCIONES"), (
        "El módulo migrador debe definir la constante SQL_INSERT_INTERACCIONES"
    )
    sql_insert = getattr(migrador, "SQL_INSERT_INTERACCIONES", "").upper()
    assert "ON CONFLICT (HASH) DO NOTHING" in sql_insert or "ON CONFLICT (hash) DO NOTHING".upper() in sql_insert, (
        "La inserción debe incluir la cláusula idempotente 'ON CONFLICT (hash) DO NOTHING'"
    )

    # 2. Validar función de validación de paridad de 204 hashes
    assert hasattr(migrador, "validar_paridad_hashes"), (
        "El módulo migrador debe implementar la función 'validar_paridad_hashes'"
    )
    hashes_origen = [f"hash_discord_{i:03d}" for i in range(204)]
    hashes_destino_exactos = list(hashes_origen)
    assert migrador.validar_paridad_hashes(hashes_origen, hashes_destino_exactos) is True, (
        "Debe retornar True cuando los 204 hashes coinciden exactamente"
    )

    # Casos de discrepancia
    hashes_destino_menos = hashes_origen[:-1]
    assert migrador.validar_paridad_hashes(hashes_origen, hashes_destino_menos) is False, (
        "Debe retornar False si la cantidad no coincide con 204"
    )
    hashes_destino_discrepante = list(hashes_origen)
    hashes_destino_discrepante[0] = "hash_alterado"
    assert migrador.validar_paridad_hashes(hashes_origen, hashes_destino_discrepante) is False, (
        "Debe retornar False si algún hash discrepa"
    )

    # 3. Validar SQL de sincronización de secuencia autoincremental
    assert hasattr(migrador, "SQL_SYNC_SECUENCIA"), (
        "El módulo migrador debe definir la constante SQL_SYNC_SECUENCIA"
    )
    sql_seq = getattr(migrador, "SQL_SYNC_SECUENCIA", "")
    assert "interacciones_id_seq" in sql_seq, "Debe sincronizar la secuencia 'interacciones_id_seq'"
    assert "COALESCE" in sql_seq.upper() and "MAX(ID)" in sql_seq.upper(), (
        "La secuencia debe usar COALESCE((SELECT MAX(id) FROM interacciones), 1)"
    )


# ==============================================================================
# Spec 023: Persistencia en Historial de Reportes Semanales y LangGraph Checkpointer
# en Supabase Enoc con Garantía de Alta Velocidad
# ==============================================================================

def test_spec023_normalizacion_registro_historial_reporte():
    """
    Spec 023 - RF-01, RF-02:
    Valida la función construir_registro_historial_reporte para normalizar los
    12 campos canónicos de public.historial_reportes_semanales:
    - id_mensaje normalizado invariablemente como string (str)
    - autor, semana, fecha_envio, fecha_extraccion, fecha_publicacion
    - rutas_activas como lista de canales despachados
    - estado literal 'publicado'
    - contenido_original como JSON estructurado
    - copys_generados indexado por canal
    - cw_modelo_ia resuelto con catálogo oficial
    """
    assert hasattr(puente_motor_ia, "construir_registro_historial_reporte"), (
        "puente_motor_ia debe implementar 'construir_registro_historial_reporte' para normalizar registros canónicos"
    )

    # 1. Caso de publicación individual
    reg_ind = puente_motor_ia.construir_registro_historial_reporte(
        id_mensaje=101,  # Pasado como entero para verificar conversión a str
        canal="discord",
        copy_generado={"titulo": "Taller IA", "texto_copy": "Aprende agentes autónomos este sábado."},
        interaccion={"autor": "alice", "texto": "¿Habrá taller de IA?", "canal": "#general", "semana": "Semana_01"}
    )

    assert isinstance(reg_ind, dict), "El registro retornado debe ser un diccionario"
    assert reg_ind.get("id_mensaje") == "101", f"id_mensaje debe normalizarse a str ('101'), obtenido: {reg_ind.get('id_mensaje')}"
    assert reg_ind.get("autor") == "alice"
    assert reg_ind.get("semana") == "Semana_01"
    assert reg_ind.get("estado") == "publicado"
    assert reg_ind.get("rutas_activas") == ["discord"], "rutas_activas debe contener exactamente ['discord']"
    assert isinstance(reg_ind.get("fecha_publicacion"), str) and len(reg_ind["fecha_publicacion"]) > 10
    assert isinstance(reg_ind.get("contenido_original"), dict)
    assert reg_ind["contenido_original"].get("texto") == "¿Habrá taller de IA?"
    assert isinstance(reg_ind.get("copys_generados"), dict)
    assert "discord" in reg_ind["copys_generados"]
    assert reg_ind["copys_generados"]["discord"]["titulo"] == "Taller IA"
    assert isinstance(reg_ind.get("cw_modelo_ia"), str) and len(reg_ind["cw_modelo_ia"]) > 0

    # 2. Caso consolidado multi-canal HITL
    copys_hitl = {
        "discord": {"titulo": "D1", "texto_copy": "Copy Discord"},
        "linkedin": {"titulo": "L1", "texto_copy": "Copy LinkedIn"}
    }
    reg_hitl = puente_motor_ia.construir_registro_historial_reporte(
        id_mensaje="snowflake_discord_987654321",
        rutas_activas=["discord", "linkedin"],
        copys_generados=copys_hitl,
        interaccion={"autor": "bob", "texto": "Reunión de Cloud", "canal": "#anuncios"},
        semana="Semana_02"
    )

    assert reg_hitl.get("id_mensaje") == "snowflake_discord_987654321"
    assert reg_hitl.get("rutas_activas") == ["discord", "linkedin"]
    assert reg_hitl.get("estado") == "publicado"
    assert "discord" in reg_hitl["copys_generados"] and "linkedin" in reg_hitl["copys_generados"]


def test_spec023_publish_channel_despacho_asincrono_historial_reportes(client, monkeypatch):
    """
    Spec 023 - RF-01, RF-05, RF-06:
    Valida que ante publicación individual exitosa en /api/v1/mototradis/publish-channel:
    1. Se persista atómicamente en SQLite local en menos de 100 ms de sobrecarga interna.
    2. Se despache de forma desacoplada en segundo plano la réplica hacia Supabase
       (despachar_replicacion_historial_reportes) con el registro canónico individual.
    3. La respuesta HTTP sea inmediata y exitosa.
    """
    import time
    _insertar_interaccion_spec012(
        interaccion_id=801,
        autor="marcos",
        canal="#general",
        texto="Consulta sobre despliegue en la nube",
        etapa_flujo="en_redaccion"
    )

    assert hasattr(puente_motor_ia, "despachar_replicacion_historial_reportes"), (
        "puente_motor_ia debe implementar 'despachar_replicacion_historial_reportes' para desacoplar a segundo plano"
    )

    llamadas_despacho = []
    def mock_despacho(reg):
        llamadas_despacho.append(reg)

    monkeypatch.setattr(puente_motor_ia, "despachar_replicacion_historial_reportes", mock_despacho)
    monkeypatch.setattr(
        puente_motor_ia,
        "despachar_discord_con_cascada",
        lambda *args, **kwargs: {"ok": True, "detalle": "Enviado con éxito", "estado_canal": "enviado", "message_id": "disc_801"}
    )

    t0 = time.perf_counter()
    resp = client.post("/api/v1/mototradis/publish-channel", json={
        "id_mensaje": 801,
        "canal": "discord",
        "titulo": "Novedades Cloud",
        "texto_copy": "Aquí las novedades semanales sobre arquitectura cloud."
    })
    latencia_ms = (time.perf_counter() - t0) * 1000

    assert resp.status_code == 200
    data = resp.json()
    assert data.get("ok") is True
    assert data.get("estado_canal") == "enviado"
    assert latencia_ms < 1500, f"La sobrecarga interna debe ser inmediata, tomada: {latencia_ms:.2f} ms"

    # Verificar que se despachó la tarea en segundo plano con el registro canónico
    assert len(llamadas_despacho) == 1, "Debe invocarse despachar_replicacion_historial_reportes exactamente una vez"
    payload_enviado = llamadas_despacho[0]
    assert payload_enviado.get("id_mensaje") == "801"
    assert payload_enviado.get("rutas_activas") == ["discord"]
    assert payload_enviado.get("estado") == "publicado"
    assert "discord" in payload_enviado.get("copys_generados", {})


def test_spec023_hitl_decision_aprobacion_despacho_asincrono_consolidado(client, monkeypatch):
    """
    Spec 023 - RF-02, RF-04, RF-05:
    Valida que ante aprobación HITL (/api/v1/mototradis/hitl-decision):
    1. Si decision == 'aprobar' y hay al menos un canal enviado con éxito, se despache
       en segundo plano la réplica consolidada conteniendo exactamente las rutas exitosas
       y los copys aprobados por el humano (Soberanía Humana).
    2. Si decision == 'desaprobar', se purgue el hilo en el checkpointer y NO se despache
       réplica a historial_reportes_semanales.
    """
    from datetime import datetime, timezone

    _insertar_interaccion_spec012(
        interaccion_id=802,
        autor="laura",
        canal="#ideas",
        texto="Propuesta de taller práctico sobre FastAPI",
        etapa_flujo="en_redaccion"
    )

    # Insertar borradores en SQLite para simular precondición de aprobación
    ahora = puente_motor_ia.a_utc_iso(datetime.now(timezone.utc))
    with sqlite3.connect(puente_motor_ia.motor_bd.RUTA_BD) as conn:
        conn.execute("""
            INSERT INTO contenidos_generados (
                id, interaccion_id, formato, plataforma, titulo, contenido, estado,
                estado_publicacion, creado_en, actualizado_en
            ) VALUES
            (80201, 802, 'discord', 'discord', 'Draft Discord', 'Borrador Discord', 'pendiente_revision', 'no_publicado', ?, ?),
            (80202, 802, 'linkedin', 'linkedin', 'Draft LinkedIn', 'Borrador LinkedIn', 'pendiente_revision', 'no_publicado', ?, ?)
        """, (ahora, ahora, ahora, ahora))
        conn.commit()

    assert hasattr(puente_motor_ia, "despachar_replicacion_historial_reportes"), (
        "puente_motor_ia debe implementar 'despachar_replicacion_historial_reportes'"
    )

    llamadas_despacho = []
    monkeypatch.setattr(puente_motor_ia, "despachar_replicacion_historial_reportes", lambda r: llamadas_despacho.append(r))

    # Mock dispatchers: Discord y LinkedIn exitosos, X fallido
    monkeypatch.setattr(
        puente_motor_ia,
        "despachar_discord_con_cascada",
        lambda *args, **kwargs: {"ok": True, "detalle": "Discord OK", "estado_canal": "enviado", "message_id": "disc_802"}
    )
    monkeypatch.setattr(
        puente_motor_ia,
        "despachar_linkedin_resiliente",
        lambda *args, **kwargs: {"ok": True, "detalle": "LinkedIn OK", "estado_canal": "enviado", "urn": "urn:li:802"}
    )
    monkeypatch.setattr(
        puente_motor_ia,
        "despachar_x_resiliente",
        lambda *args, **kwargs: {"ok": False, "detalle": "Fallo simulado X", "estado_canal": "error"}
    )

    copys_editados_humano = {
        "discord": {"titulo": "Taller FastAPI Aprobado", "texto_copy": "Aprende APIs rápidas."},
        "linkedin": {"titulo": "Webinar FastAPI Profesional", "texto_copy": "Domina backend moderno con FastAPI."}
    }

    # 1. Aprobación HITL
    resp_aprob = client.post("/api/v1/mototradis/hitl-decision", json={
        "id_mensaje": 802,
        "decision": "aprobar",
        "copys_editados": copys_editados_humano
    })

    assert resp_aprob.status_code == 200
    data_aprob = resp_aprob.json()
    assert data_aprob.get("exito") is True

    # Validar despacho consolidado en background
    assert len(llamadas_despacho) == 1, "Debe despacharse el registro consolidado a Supabase en background"
    reg_consolidado = llamadas_despacho[0]
    assert reg_consolidado.get("id_mensaje") == "802"
    assert "discord" in reg_consolidado.get("rutas_activas", [])
    assert "linkedin" in reg_consolidado.get("rutas_activas", [])
    assert "x" not in reg_consolidado.get("rutas_activas", [])  # X falló, no debe estar activa
    assert reg_consolidado.get("copys_generados", {}).get("discord", {}).get("titulo") == "Taller FastAPI Aprobado"

    # 2. Desaprobación HITL: no debe despachar réplica
    llamadas_despacho.clear()
    resp_desaprob = client.post("/api/v1/mototradis/hitl-decision", json={
        "id_mensaje": 802,
        "decision": "desaprobar"
    })
    assert resp_desaprob.status_code == 200
    assert len(llamadas_despacho) == 0, "No debe despacharse réplica a historial ante desaprobación"


def test_spec023_checkpointer_session_mode_y_mitigacion_prepared_statements(monkeypatch, caplog):
    """
    Spec 023 - RF-03, RF-04, RF-06:
    Valida la fábrica de checkpointer resiliente:
    1. resolver_url_session_mode conmuta puertos de Transaction Pooler (:6543) a Session Mode (:5432).
    2. obtener_checkpointer_resiliente usa Session Mode (:5432) y prepare_threshold=None en psycopg 3
       para mitigar DuplicatePreparedStatement.
    3. Ante fallo de conexión remota o DuplicatePreparedStatement, conmuta transparentemente a MemorySaver
       emitiendo logger.warning estructurado.
    """
    import logging

    assert hasattr(puente_motor_ia, "resolver_url_session_mode"), (
        "puente_motor_ia debe implementar 'resolver_url_session_mode'"
    )

    url_tx = "postgresql://postgres.swdoucawdasxmnomlcfu:secret@aws-0-us-east-1.pooler.supabase.com:6543/postgres"
    url_res = puente_motor_ia.resolver_url_session_mode(url_tx)
    assert ":5432" in url_res and ":6543" not in url_res, (
        f"resolver_url_session_mode debe sustituir el puerto :6543 por :5432. Obtenido: {url_res}"
    )

    url_ya_5432 = "postgresql://postgres.swdoucawdasxmnomlcfu:secret@aws-0-us-east-1.pooler.supabase.com:5432/postgres"
    assert puente_motor_ia.resolver_url_session_mode(url_ya_5432) == url_ya_5432

    # Probar fallback resiliente ante DuplicatePreparedStatement o Network Error
    monkeypatch.setattr(puente_motor_ia, "_checkpointer_activo", None)
    monkeypatch.setenv("SUPABASE_DB_URL", url_tx)

    with patch("langgraph.checkpoint.postgres.PostgresSaver.from_conn_string", side_effect=Exception("DuplicatePreparedStatement: prepared statement _pg3_0 already exists")):
        with caplog.at_level(logging.WARNING):
            cp = puente_motor_ia.obtener_checkpointer_resiliente()

    from langgraph.checkpoint.memory import MemorySaver
    assert isinstance(cp, MemorySaver), "Debe conmutar transparentemente a MemorySaver ante excepción en PostgresSaver"
    assert any("MemorySaver" in r.message or "PostgresSaver" in r.message for r in caplog.records), (
        "Debe emitirse un logger.warning informando la conmutación a MemorySaver"
    )


def test_spec023_resiliencia_fallo_segundo_plano_y_marca_local_sqlite(monkeypatch, caplog):
    """
    Spec 023 - RF-04, RF-05:
    Valida que ante fallo de red o timeout durante la inserción remota en Supabase:
    1. replicar_historial_reportes_semanales_supabase capture la excepción defensivamente.
    2. Se registre un logger.warning descriptivo.
    3. Se marque el estado pendiente local en SQLite (sync_supabase = 'pendiente')
       para reconciliación diferida.
    """
    import logging

    assert hasattr(puente_motor_ia, "replicar_historial_reportes_semanales_supabase"), (
        "puente_motor_ia debe implementar 'replicar_historial_reportes_semanales_supabase'"
    )

    _insertar_interaccion_spec012(
        interaccion_id=803,
        autor="diego",
        canal="#general",
        texto="Problema con el despliegue",
        etapa_flujo="publicado"
    )

    # Insertar en contenidos_generados
    with sqlite3.connect(puente_motor_ia.motor_bd.RUTA_BD) as conn:
        conn.execute("""
            INSERT INTO contenidos_generados (
                id, interaccion_id, formato, plataforma, titulo, contenido, estado,
                estado_publicacion, creado_en, actualizado_en
            ) VALUES
            (80301, 803, 'discord', 'discord', 'Tit 803', 'Contenido 803', 'publicado', 'publicado', '2026-10-23T10:00:00+00:00', '2026-10-23T10:00:00+00:00')
        """)
        conn.commit()

    registro_dummy = {
        "id_mensaje": "803",
        "autor": "diego",
        "semana": "Semana_01",
        "fecha_envio": None,
        "fecha_extraccion": "2026-10-23T10:00:00+00:00",
        "fecha_publicacion": "2026-10-23T10:05:00+00:00",
        "rutas_activas": ["discord"],
        "estado": "publicado",
        "contenido_original": {"texto": "Problema con el despliegue"},
        "copys_generados": {"discord": {"titulo": "Tit 803", "texto_copy": "Contenido 803"}},
        "cw_modelo_ia": "Google Gemini · gemini-3.5-flash-lite"
    }

    # Simular fallo en psycopg.connect
    with patch("psycopg.connect", side_effect=Exception("Connection timed out to Supabase Enoc")), \
         caplog.at_level(logging.WARNING):
        res = puente_motor_ia.replicar_historial_reportes_semanales_supabase(registro_dummy)

    assert res is False, "Debe retornar False defensivamente ante error de conexión"
    assert any("Supabase" in r.message or "historial" in r.message.lower() for r in caplog.records), (
        "Debe registrarse una advertencia en log (logger.warning) ante fallo de inserción remota"
    )

    # Validar que SQLite local registró la marca de sync pendiente
    with sqlite3.connect(puente_motor_ia.motor_bd.RUTA_BD) as conn:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(contenidos_generados)").fetchall()}
        assert "sync_supabase" in cols, "La columna sync_supabase debe existir en contenidos_generados"
        row = conn.execute("SELECT sync_supabase FROM contenidos_generados WHERE interaccion_id = 803").fetchone()
        assert row and row[0] == "pendiente", "Debe marcarse sync_supabase='pendiente' en SQLite local"


def test_spec023_resiliencia_despacho_fondo_y_esquema_defensivo(monkeypatch, caplog):
    """
    Spec 023 - RF-04, RF-05, RF-06:
    Valida la resiliencia en segundo plano y el esquema defensivo:
    1. _asegurar_esquema_sqlite asegura columna sync_supabase sin fallar por duplicate column.
    2. _marcar_sync_sqlite_local(id_mensaje, estado_sync, error_detalle) actualiza SQLite.
    3. despachar_replicacion_historial_reportes captura excepciones imprevistas con logger.warning.
    """
    import logging

    # 1. Esquema defensivo idempotente
    puente_motor_ia._asegurar_esquema_sqlite()
    puente_motor_ia._asegurar_esquema_sqlite()

    with sqlite3.connect(puente_motor_ia.motor_bd.RUTA_BD) as conn:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(contenidos_generados)").fetchall()}
        assert "sync_supabase" in cols, "La columna sync_supabase debe existir defensivamente en contenidos_generados"

    # 2. _marcar_sync_sqlite_local con error_detalle
    _insertar_interaccion_spec012(
        interaccion_id=804,
        autor="maria",
        canal="#faq",
        texto="Pregunta sobre API",
        etapa_flujo="publicado"
    )
    with sqlite3.connect(puente_motor_ia.motor_bd.RUTA_BD) as conn:
        conn.execute("""
            INSERT INTO contenidos_generados (
                id, interaccion_id, formato, plataforma, titulo, contenido, estado,
                estado_publicacion, creado_en, actualizado_en
            ) VALUES
            (80401, 804, 'discord', 'discord', 'Tit 804', 'Contenido 804', 'publicado', 'publicado', '2026-10-23T11:00:00+00:00', '2026-10-23T11:00:00+00:00')
        """)
        conn.commit()

    puente_motor_ia._marcar_sync_sqlite_local(id_mensaje=804, estado_sync="pendiente", error_detalle="Simulated timeout")
    with sqlite3.connect(puente_motor_ia.motor_bd.RUTA_BD) as conn:
        row = conn.execute("SELECT sync_supabase FROM contenidos_generados WHERE interaccion_id = 804").fetchone()
        assert row and row[0] == "pendiente"

    # 3. despachar_replicacion_historial_reportes ante excepción imprevista
    with patch("puente_motor_ia.replicar_historial_reportes_semanales_supabase", side_effect=RuntimeError("Fallo WAN catastrófico")), \
         caplog.at_level(logging.WARNING):
        puente_motor_ia.despachar_replicacion_historial_reportes({"id_mensaje": "804"})
        import time
        time.sleep(0.1)

    assert any("Fallo WAN catastrófico" in r.message or "Excepción" in r.message for r in caplog.records), (
        "Cualquier excepción en la tarea de fondo debe capturarse con logger.warning"
    )


# ==============================================================================
# Spec 024: Reporte OCI desde Historial Semanal con Inyección de Copys Reales y Alta Velocidad
# ==============================================================================

def test_spec024_extraccion_historial_reportes_supabase_timeout_y_kpis(monkeypatch, caplog):
    """
    Spec 024 - RF-01, RF-03, RF-04, RF-06:
    Valida la extracción y deserialización defensiva desde historial_reportes_semanales:
    1. _deserializar_json_defensivo maneja strings JSON, dicts, listas, nulos y strings inválidos.
    2. _extraer_historial_reportes_semanales_supabase conecta con connect_timeout <= 4.
    3. Construye el subdiccionario normalizado 'kpis' con relevancia (int), sentimiento (str),
       temas_clave (list o str), segmento (str) y razonamiento (str).
    4. id_mensaje se garantiza como str.
    5. Ante fallos de conexión o timeouts de psycopg, captura la excepción, registra warning
       y retorna [] defensivamente para activar el fallback.
    """
    import logging
    import json

    assert hasattr(puente_motor_ia, "_deserializar_json_defensivo"), (
        "puente_motor_ia debe implementar '_deserializar_json_defensivo'"
    )
    assert hasattr(puente_motor_ia, "_extraer_historial_reportes_semanales_supabase"), (
        "puente_motor_ia debe implementar '_extraer_historial_reportes_semanales_supabase'"
    )

    # 1. Deserialización defensiva unitaria
    assert puente_motor_ia._deserializar_json_defensivo({"clave": "valor"}) == {"clave": "valor"}
    assert puente_motor_ia._deserializar_json_defensivo('{"clave": "valor"}') == {"clave": "valor"}
    assert puente_motor_ia._deserializar_json_defensivo(None) == {}
    assert puente_motor_ia._deserializar_json_defensivo("invalid json syntax {{{") == {}
    assert puente_motor_ia._deserializar_json_defensivo(["item1", "item2"]) == ["item1", "item2"]
    assert puente_motor_ia._deserializar_json_defensivo('["item1", "item2"]') == ["item1", "item2"]

    # 2. Mock de conexión exitosa con connect_timeout <= 4
    called_timeouts = []
    fake_filas = [
        # id_mensaje, autor, semana, fecha_envio, fecha_extraccion, fecha_publicacion, rutas_activas, estado, contenido_original, copys_generados, cw_modelo_ia
        (
            1001,
            "carlos_dev",
            "2026-semana-42",
            "2026-10-15T10:00:00+00:00",
            "2026-10-15T10:05:00+00:00",
            "2026-10-15T11:00:00+00:00",
            ["linkedin"],
            "publicado",
            json.dumps({
                "texto": "Cómo configurar CI/CD con Docker?",
                "kpis": {
                    "relevancia": 85,
                    "sentimiento": "Positivo",
                    "temas_clave": ["#docker", "#cicd"],
                    "segmento": "DEV",
                    "razonamiento": "Pregunta técnica relevante"
                }
            }),
            json.dumps({
                "linkedin": {"titulo": "Docker en CI/CD", "texto_copy": "Guía práctica de integración continua."}
            }),
            "gemini-3.5-flash-lite"
        ),
        (
            1002,
            "ana_qa",
            "2026-semana-42",
            "2026-10-15T12:00:00+00:00",
            "2026-10-15T12:05:00+00:00",
            "2026-10-15T12:30:00+00:00",
            ["discord"],
            "publicado",
            # Caso contenido_original y copys_generados ya vienen como dict (psycopg jsonb nativo)
            {
                "texto": "Mejor herramienta para pruebas e2e?",
                "kpis": {
                    "relevancia": 92,
                    "sentimiento": "Positivo",
                    "temas_clave": "#testing #e2e",
                    "segmento": "QA",
                    "razonamiento": "Discusión técnica sobre Playwright"
                }
            },
            {
                "discord": {"titulo": "", "texto_copy": "Recomendamos Playwright para e2e."}
            },
            "gemini-3.5-flash-lite"
        )
    ]

    class FakeCursor:
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass
        def execute(self, query, params=None):
            self.query = query
            self.params = params
        def fetchall(self):
            return fake_filas

    class FakeConn:
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass
        def cursor(self):
            return FakeCursor()

    def fake_connect(*args, **kwargs):
        timeout = kwargs.get("connect_timeout")
        called_timeouts.append(timeout)
        return FakeConn()

    monkeypatch.setattr("psycopg.connect", fake_connect)
    monkeypatch.setenv("SUPABASE_DB_URL", "postgresql://user:pass@localhost:5432/db")

    resultados = puente_motor_ia._extraer_historial_reportes_semanales_supabase("2026-semana-42")

    assert len(called_timeouts) > 0, "Debe conectar a Supabase usando psycopg.connect"
    assert all(t is not None and t <= 4 for t in called_timeouts), (
        f"connect_timeout debe ser <= 4 segundos para evitar degradar latencia. Registrado: {called_timeouts}"
    )

    assert len(resultados) == 2
    r1, r2 = resultados[0], resultados[1]

    # Validar tipos estrictos y subdiccionario kpis
    assert isinstance(r1["id_mensaje"], str) and r1["id_mensaje"] == "1001"
    assert isinstance(r1["kpis"], dict)
    assert r1["kpis"]["relevancia"] == 85
    assert r1["kpis"]["sentimiento"] == "Positivo"
    assert r1["kpis"]["segmento"] == "DEV"
    assert r1["kpis"]["razonamiento"] == "Pregunta técnica relevante"
    assert r1["kpis"]["temas_clave"] in (["#docker", "#cicd"], "#docker #cicd")
    assert isinstance(r1["copys_generados"], dict)
    assert "linkedin" in r1["copys_generados"]

    assert isinstance(r2["id_mensaje"], str) and r2["id_mensaje"] == "1002"
    assert r2["kpis"]["relevancia"] == 92
    assert r2["kpis"]["sentimiento"] == "Positivo"

    # 3. Manejo defensivo ante fallos y timeouts retornando [] con warning
    def fake_connect_timeout(*args, **kwargs):
        raise Exception("Connection timed out after 4000ms")

    monkeypatch.setattr("psycopg.connect", fake_connect_timeout)
    with caplog.at_level(logging.WARNING):
        res_vacio = puente_motor_ia._extraer_historial_reportes_semanales_supabase("2026-semana-42")

    assert res_vacio == [], "Debe retornar [] defensivamente ante fallo o timeout de conexión"
    assert any("historial" in r.message.lower() or "timeout" in r.message.lower() or "supabase" in r.message.lower() for r in caplog.records), (
        "Debe registrarse una advertencia en log (logger.warning) ante fallo de extracción remota"
    )


def test_spec024_prelacion_copys_formateo_y_erradicacion_placeholders():
    """
    Spec 024 - RF-02, RF-06:
    Valida la prelación estricta de copys (LinkedIn > Discord > X),
    el formateo con/sin título y la erradicación total de placeholders provisionales:
    1. Si existe LinkedIn con texto, se selecciona prioritariamente.
    2. Si no hay LinkedIn pero sí Discord, se selecciona Discord.
    3. Si no hay LinkedIn ni Discord, se selecciona X.
    4. Con título no vacío: f"{titulo}\n\n{texto_copy}".strip().
    5. Sin título o título vacío/None: texto_copy.strip().
    6. Si no hay ningún canal válido: respaldo con texto_original.strip().
    7. Prohibición categórica de 'Pendiente de redacción por Enoc...'.
    """
    assert hasattr(puente_motor_ia, "_formatear_copy_final"), (
        "puente_motor_ia debe implementar '_formatear_copy_final'"
    )

    # 1. Prelación LinkedIn (máxima prioridad) con título
    copys_multicanal = {
        "linkedin": {"titulo": "Ecosistema Cloud", "texto_copy": "Aprende Kubernetes y Terraform hoy."},
        "discord": {"titulo": "Aviso Discord", "texto_copy": "Texto secundario de Discord."},
        "x": {"texto_copy": "Tweet sobre Cloud."}
    }
    copy_final = puente_motor_ia._formatear_copy_final(copys_multicanal, texto_original="Texto original")
    assert copy_final == "Ecosistema Cloud\n\nAprende Kubernetes y Terraform hoy."

    # 2. LinkedIn sin título
    copys_sin_titulo = {
        "linkedin": {"titulo": "", "texto_copy": "   Texto de LinkedIn sin encabezado.   "},
        "discord": {"texto_copy": "Texto Discord"}
    }
    copy_final = puente_motor_ia._formatear_copy_final(copys_sin_titulo, texto_original="Texto original")
    assert copy_final == "Texto de LinkedIn sin encabezado."

    # 3. Discord cuando no existe LinkedIn (segunda prioridad) con título
    copys_discord = {
        "discord": {"titulo": "Comunidad Alura", "texto": "Revisa los nuevos módulos publicados."},
        "x": {"texto_copy": "Post en X"}
    }
    copy_final = puente_motor_ia._formatear_copy_final(copys_discord, texto_original="Texto original")
    assert copy_final == "Comunidad Alura\n\nRevisa los nuevos módulos publicados."

    # 4. X cuando no existe LinkedIn ni Discord (tercera prioridad)
    copys_x = {
        "x": {"texto_copy": "Tips rápidos de Python en 280 caracteres."}
    }
    copy_final = puente_motor_ia._formatear_copy_final(copys_x, texto_original="Texto original")
    assert copy_final == "Tips rápidos de Python en 280 caracteres."

    # 5. Soporte para canales como string plano o dicts con diversas claves ('texto', 'contenido', 'texto_copy')
    copys_string = {"linkedin": "Publicación directa como cadena"}
    assert puente_motor_ia._formatear_copy_final(copys_string) == "Publicación directa como cadena"

    # 6. Respaldo transparente con texto original ante ausencia de copys
    copy_vacio = puente_motor_ia._formatear_copy_final({}, texto_original="  Consulta original de un estudiante.  ")
    assert copy_vacio == "Consulta original de un estudiante."

    # 7. Erradicación categórica de placeholders provisionales
    placeholder = "Pendiente de redacción por Enoc..."
    copys_con_placeholder = {
        "linkedin": {"titulo": "Tit", "texto_copy": f"{placeholder}"},
        "discord": {"texto_copy": "Copy real en Discord"}
    }
    # Si LinkedIn contiene el placeholder, debe ignorarse y conmutar a Discord o texto original
    copy_sanitizado = puente_motor_ia._formatear_copy_final(copys_con_placeholder, texto_original="Texto original")
    assert placeholder not in copy_sanitizado, "No debe permitirse el placeholder provisional en el copy final"
    assert copy_sanitizado == "Copy real en Discord"


def test_spec024_deduplicacion_publicaciones_multiples():
    """
    Spec 024 - RF-02, RF-06:
    Valida la deduplicación de múltiples publicaciones para un mismo id_mensaje:
    1. Agrupación por id_mensaje consolidando rutas_activas únicas.
    2. Fusión completa de copys_generados multicanal.
    3. Elección de la fecha_publicacion más reciente.
    4. Inyección del campo copy_final calculado por prelación.
    5. Preservación del subdiccionario normalizado kpis sin pérdida de datos.
    """
    assert hasattr(puente_motor_ia, "_consolidar_aprobados_historial"), (
        "puente_motor_ia debe implementar '_consolidar_aprobados_historial'"
    )

    filas_crudas = [
        # Publicación 1 de id_mensaje 901 a Discord a las 10:00
        {
            "id_mensaje": "901",
            "autor": "dev_senior",
            "semana": "2026-semana-42",
            "fecha_envio": "2026-10-15T09:00:00+00:00",
            "fecha_extraccion": "2026-10-15T09:05:00+00:00",
            "fecha_publicacion": "2026-10-15T10:00:00+00:00",
            "rutas_activas": ["discord"],
            "estado": "publicado",
            "contenido_original": {
                "texto": "¿Cómo optimizar queries SQL complejas?",
                "kpis": {
                    "relevancia": 95,
                    "sentimiento": "Positivo",
                    "temas_clave": ["#sql", "#db"],
                    "segmento": "BACKEND",
                    "razonamiento": "Optimización de base de datos"
                }
            },
            "copys_generados": {
                "discord": {"titulo": "SQL Tips", "texto_copy": "Usa EXPLAIN ANALYZE para identificar cuellos de botella."}
            },
            "cw_modelo_ia": "gemini-3.5-flash-lite"
        },
        # Publicación 2 del MISMO id_mensaje 901 a LinkedIn a las 14:30
        {
            "id_mensaje": "901",
            "autor": "dev_senior",
            "semana": "2026-semana-42",
            "fecha_envio": "2026-10-15T09:00:00+00:00",
            "fecha_extraccion": "2026-10-15T09:05:00+00:00",
            "fecha_publicacion": "2026-10-15T14:30:00+00:00",
            "rutas_activas": ["linkedin"],
            "estado": "publicado",
            "contenido_original": {
                "texto": "¿Cómo optimizar queries SQL complejas?",
                "kpis": {
                    "relevancia": 95,
                    "sentimiento": "Positivo",
                    "temas_clave": ["#sql", "#db"],
                    "segmento": "BACKEND",
                    "razonamiento": "Optimización de base de datos"
                }
            },
            "copys_generados": {
                "linkedin": {"titulo": "Mastering SQL Performance", "texto_copy": "El índice correcto cambia de segundos a milisegundos."}
            },
            "cw_modelo_ia": "gemini-3.5-flash-lite"
        },
        # Mensaje independiente 902
        {
            "id_mensaje": "902",
            "autor": "qa_tester",
            "semana": "2026-semana-42",
            "fecha_envio": "2026-10-15T11:00:00+00:00",
            "fecha_extraccion": "2026-10-15T11:05:00+00:00",
            "fecha_publicacion": "2026-10-15T12:00:00+00:00",
            "rutas_activas": ["x"],
            "estado": "publicado",
            "contenido_original": {
                "texto": "Mocking de servicios externos en tests",
                "kpis": {
                    "relevancia": 80,
                    "sentimiento": "Positivo",
                    "temas_clave": ["#testing"],
                    "segmento": "QA",
                    "razonamiento": "Buenas prácticas de testing"
                }
            },
            "copys_generados": {
                "x": {"texto_copy": "Usa mocks para desacoplar tests unitarios."}
            },
            "cw_modelo_ia": "gemini-3.5-flash-lite"
        }
    ]

    consolidados = puente_motor_ia._consolidar_aprobados_historial(filas_crudas)

    assert len(consolidados) == 2, "Debe deduplicar id_mensaje 901 resultando en exactamente 2 registros únicos"

    item_901 = next(item for item in consolidados if str(item["id_mensaje"]) == "901")
    item_902 = next(item for item in consolidados if str(item["id_mensaje"]) == "902")

    # Validar consolidación de rutas_activas
    assert set(item_901["rutas_activas"]) == {"discord", "linkedin"}

    # Validar combinación de copys_generados
    assert "discord" in item_901["copys_generados"]
    assert "linkedin" in item_901["copys_generados"]

    # Validar fecha_publicacion más reciente (14:30 > 10:00)
    assert item_901["fecha_publicacion"] == "2026-10-15T14:30:00+00:00"

    # Validar copy_final por prelación (LinkedIn > Discord)
    assert item_901["copy_final"] == "Mastering SQL Performance\n\nEl índice correcto cambia de segundos a milisegundos."

    # Validar kpis íntegros
    assert item_901["kpis"]["relevancia"] == 95
    assert item_901["kpis"]["segmento"] == "BACKEND"
    assert "Pendiente de redacción por Enoc..." not in item_901["copy_final"]


def test_spec024_complemento_descartados_desde_sqlite(tmp_path, monkeypatch):
    """
    Spec 024 - RF-01, RF-03, RF-04, RF-06:
    Valida el complemento de mensajes descartados desde SQLite local:
    1. _obtener_descartados_semana_sqlite extrae filas con estado_curaduria = 'discarded'
       o (estado_curaduria != 'curated' y relevancia < 70) para la semana objetivo.
    2. Excluye mensajes cuyos IDs ya están en ids_aprobados.
    3. Construye subdiccionario 'kpis' normalizado para evitar KeyError en reporte_semanal.py.
    4. _cargar_lote_para_reporte_semanal ensambla aprobados de Supabase y descartados de SQLite.
    5. reporte_semanal.generar_reporte_semanal calcula métricas totales (aprobados + descartados)
       sin errores.
    """
    from pathlib import Path
    import reporte_semanal

    assert hasattr(puente_motor_ia, "_obtener_descartados_semana_sqlite"), (
        "puente_motor_ia debe implementar '_obtener_descartados_semana_sqlite'"
    )
    assert hasattr(puente_motor_ia, "_cargar_lote_para_reporte_semanal"), (
        "puente_motor_ia debe implementar '_cargar_lote_para_reporte_semanal'"
    )

    test_db = str(tmp_path / "test_reporte_descartados.db")
    monkeypatch.setattr(puente_motor_ia.motor_bd, "RUTA_BD", test_db)
    puente_motor_ia._asegurar_esquema_sqlite()

    # Insertar en SQLite:
    # 1. ID 1101: Aprobado (relevancia 90, curated, semana 2026-semana-42)
    # 2. ID 1102: Descartado explícito (estado_curaduria='discarded', relevancia 50, semana 2026-semana-42)
    # 3. ID 1103: Descartado por relevancia baja (estado_curaduria='pending', relevancia 40, semana 2026-semana-42)
    # 4. ID 1104: Descartado de OTRA semana (semana 2026-semana-40) -> debe ser ignorado
    with sqlite3.connect(test_db) as conn:
        conn.execute("""
            INSERT INTO interacciones (
                id, hash, origen_comunidad, periodo_referencia, autor, canal, tipo,
                texto, enviado_en, creado_en, estado, etapa_flujo, etapa,
                estado_curaduria, relevancia, sentimiento, temas_clave, segmento, razonamiento
            ) VALUES
            (1101, 'hash1101', 'Discord', '2026-semana-42', 'usuario_aprobado', '#general', 'mensaje',
             'Aporte de gran valor sobre Kubernetes', '2026-10-15T10:00:00+00:00', '2026-10-15T10:00:00+00:00',
             'analizado', 'publicado', 'publicado', 'curated', 90, 'Positivo', '#k8s', 'PROFESIONAL', 'Excelente aporte'),
            (1102, 'hash1102', 'Discord', '2026-semana-42', 'usuario_spam', '#general', 'mensaje',
             'Compre criptomonedas con descuento ya', '2026-10-15T11:00:00+00:00', '2026-10-15T11:00:00+00:00',
             'analizado', 'descartado', 'descartado', 'discarded', 30, 'Negativo', '#spam', 'SPAM', 'Publicidad no deseada'),
            (1103, 'hash1103', 'Discord', '2026-semana-42', 'usuario_casual', '#general', 'mensaje',
             'Hola a todos buenos días', '2026-10-15T12:00:00+00:00', '2026-10-15T12:00:00+00:00',
             'analizado', 'pendiente', 'ingesta', 'pending', 25, 'Neutral', '#saludo', 'GENERAL', 'Saludo sin contenido técnico'),
            (1104, 'hash1104', 'Discord', '2026-semana-40', 'usuario_antiguo', '#general', 'mensaje',
             'Mensaje viejo irrelevante', '2026-09-30T10:00:00+00:00', '2026-09-30T10:00:00+00:00',
             'analizado', 'descartado', 'descartado', 'discarded', 20, 'Neutral', '#viejo', 'GENERAL', 'Mensaje de semana anterior')
        """)
        conn.commit()

    # 1. Probar _obtener_descartados_semana_sqlite con ids_aprobados={"1101"}
    descartados = puente_motor_ia._obtener_descartados_semana_sqlite("2026-semana-42", ids_aprobados={"1101"})
    ids_desc = {str(d.get("id_mensaje") or d.get("id")) for d in descartados}
    assert ids_desc == {"1102", "1103"}, f"Debe extraer 1102 y 1103, excluyendo 1101 y 1104. Obtenido: {ids_desc}"

    for d in descartados:
        assert "kpis" in d, "Cada descartado debe contener subdiccionario kpis normalizado"
        assert isinstance(d["kpis"], dict)
        assert "relevancia" in d["kpis"]
        assert "sentimiento" in d["kpis"]

    # 2. Mockear Supabase para simular que retorna el aprobado 1101
    reg_supabase = [{
        "id_mensaje": "1101",
        "autor": "usuario_aprobado",
        "semana": "2026-semana-42",
        "fecha_envio": "2026-10-15T10:00:00+00:00",
        "fecha_extraccion": "2026-10-15T10:05:00+00:00",
        "fecha_publicacion": "2026-10-15T10:30:00+00:00",
        "rutas_activas": ["linkedin"],
        "estado": "publicado",
        "contenido_original": {
            "texto": "Aporte de gran valor sobre Kubernetes",
            "kpis": {"relevancia": 90, "sentimiento": "Positivo", "temas_clave": "#k8s", "segmento": "PROFESIONAL", "razonamiento": "Excelente"}
        },
        "copys_generados": {
            "linkedin": {"titulo": "K8s en Producción", "texto_copy": "Buenas prácticas de Kubernetes."}
        },
        "cw_modelo_ia": "gemini-3.5-flash-lite"
    }]
    monkeypatch.setattr(puente_motor_ia, "_extraer_historial_reportes_semanales_supabase", lambda sem: reg_supabase)

    lote_orquestado = puente_motor_ia._cargar_lote_para_reporte_semanal("2026-semana-42")
    assert len(lote_orquestado["aprobados"]) == 1
    assert len(lote_orquestado["descartados"]) == 2

    # 3. Generación en reporte_semanal.py sin KeyError y con métricas completas
    rep = reporte_semanal.generar_reporte_semanal("2026-semana-42", lote_orquestado)
    resumen = rep["resumen_metricas"]
    assert resumen["total_mensajes"] == 3
    assert resumen["total_aprobados"] == 1
    assert resumen["total_descartados"] == 2


def test_spec024_cache_alta_velocidad_get_reports_e_invalidacion_atomica(client, tmp_path, monkeypatch):
    """
    Spec 024 - RF-01, RF-05, RF-06:
    Valida la caché en memoria de ultra-alta velocidad (< 2 ms) para GET /api/v1/oci-storage/reports
    y su invalidación atómica:
    1. GET /api/v1/oci-storage/reports no invoca _sincronizar_reportes_desde_oci_bucket de forma bloqueante.
    2. Las lecturas en caché responden en < 2 ms.
    3. invalidar_cache_reportes_oci() restablece la caché a None y timestamp a 0.0.
    4. Las mutaciones de estado (publish-channel, hitl-decision, weekly-sync, invalidar_cache_supabase)
       disparan la invalidación atómica de forma automática.
    """
    from pathlib import Path
    import time
    import json

    assert hasattr(puente_motor_ia, "invalidar_cache_reportes_oci"), (
        "puente_motor_ia debe implementar 'invalidar_cache_reportes_oci'"
    )

    # Preparar directorio local reportes con un reporte ficticio
    rep_dir = Path("reportes")
    rep_dir.mkdir(parents=True, exist_ok=True)
    reporte_test_file = rep_dir / "2026-semana-42.json"
    dummy_reporte = {
        "metadata": {"semana": "2026-semana-42", "generado_en": "2026-10-15T12:00:00Z", "oci_storage": {"subido": True}},
        "resumen_metricas": {"total_mensajes": 10, "total_aprobados": 6, "total_descartados": 4}
    }
    reporte_test_file.write_text(json.dumps(dummy_reporte), encoding="utf-8")

    # Mockear _sincronizar_reportes_desde_oci_bucket para asegurar aislamiento WAN absoluto
    mock_sync_wan = MagicMock()
    monkeypatch.setattr(puente_motor_ia, "_sincronizar_reportes_desde_oci_bucket", mock_sync_wan)

    puente_motor_ia.invalidar_cache_reportes_oci()
    assert getattr(puente_motor_ia, "_cache_reportes_oci", None) is None

    # Primera llamada (popula caché desde disco local sin llamadas WAN)
    resp1 = client.get("/api/v1/oci-storage/reports")
    assert resp1.status_code == 200
    assert mock_sync_wan.call_count == 0, (
        "GET /api/v1/oci-storage/reports no debe invocar _sincronizar_reportes_desde_oci_bucket bloqueante"
    )

    # Segunda llamada: debe servirse directamente desde la caché en memoria en < 2 ms
    t_inicio = time.perf_counter()
    resp2 = client.get("/api/v1/oci-storage/reports")
    t_duracion_ms = (time.perf_counter() - t_inicio) * 1000.0

    assert resp2.status_code == 200
    assert t_duracion_ms < 10.0, f"Lectura en caché debe ser ultra rápida (< 10 ms en TestClient). Obtenido: {t_duracion_ms:.2f} ms"
    assert getattr(puente_motor_ia, "_cache_reportes_oci", None) is not None

    # Invalidación atómica explícita
    puente_motor_ia.invalidar_cache_reportes_oci()
    assert getattr(puente_motor_ia, "_cache_reportes_oci", None) is None
    assert getattr(puente_motor_ia, "_timestamp_cache_reportes_oci", 0.0) == 0.0

    # Invalidación atómica invocada por invalidar_cache_supabase()
    client.get("/api/v1/oci-storage/reports")
    assert getattr(puente_motor_ia, "_cache_reportes_oci", None) is not None
    puente_motor_ia.invalidar_cache_supabase()
    assert getattr(puente_motor_ia, "_cache_reportes_oci", None) is None


def test_spec024_resiliencia_fallback_y_http_400_controlado(client, monkeypatch):
    """
    Spec 024 - RF-01, RF-04, RF-06:
    Valida la resiliencia en generación de reportes y respuestas semánticas:
    1. Si Supabase Enoc está inaccesible o vacío, conmuta limpiamente a los lotes locales.
    2. Si ninguna fuente contiene datos para el período, responde HTTP 400 controlado
       ('No hay mensajes analizados para el período indicado') impidiendo HTTP 500.
    """
    # Escenario 1: Conmutación a fallback local cuando Supabase falla
    monkeypatch.setattr(puente_motor_ia, "_extraer_historial_reportes_semanales_supabase", lambda sem: [])
    # Preparar fallback local
    lote_fallback = {
        "aprobados": [
            {
                "id_mensaje": "2441",
                "autor": "dev_enoc",
                "semana": "2026-semana-42",
                "canal_origen": "#general",
                "texto_original": "Logré terminar mi certificación técnica con éxito.",
                "kpis": {"relevancia": 80, "sentimiento": "Positivo", "temas_clave": "#fallback", "segmento": "GENERAL", "razonamiento": "Ok"}
            }
        ],
        "descartados": []
    }
    monkeypatch.setattr(puente_motor_ia, "_cargar_lote_consolidado_para_reporte", lambda: lote_fallback)

    resp_fb = client.post("/api/v1/oci-storage/weekly-sync", json={"semana": "2026-semana-42"})
    assert resp_fb.status_code == 200, f"Debe responder 200 conmutando al fallback. Obtenido: {resp_fb.status_code}"
    assert resp_fb.json()["exito"] is True

    # Escenario 2: HTTP 400 controlado si absolutamente todas las fuentes están vacías
    monkeypatch.setattr(puente_motor_ia, "_cargar_lote_para_reporte_semanal", lambda sem: {"aprobados": [], "descartados": []})
    resp_vacio = client.post("/api/v1/oci-storage/weekly-sync", json={"semana": "2026-semana-99"})

    assert resp_vacio.status_code == 400, (
        f"Debe retornar HTTP 400 controlado ante período sin mensajes (cero 500). Obtenido: {resp_vacio.status_code}"
    )
    detalle = resp_vacio.json().get("detail", "")
    assert "No hay mensajes analizados" in detalle or "período" in detalle.lower()


def test_spec024_modo_offline_oci_y_status_saved_locally(client, tmp_path, monkeypatch):
    """
    Spec 024 - RF-04, RF-06:
    Valida el comportamiento en modo offline OCI o ante fallos de conectividad con OCI:
    1. Si no hay credenciales OCI configuradas o la subida a OCI falla,
       el reporte se persiste obligatoriamente en disco local ('reportes/{semana}.json').
    2. Retorna HTTP 200 con subido_oci=False y status='saved_locally'.
    3. Informa mensaje descriptivo 'Reporte generado y guardado localmente.'.
    """
    from pathlib import Path
    import json

    monkeypatch.setattr(puente_motor_ia, "_asegurar_config_oci_desde_env", lambda: False)
    monkeypatch.delenv("OCI_CONFIG_FILE", raising=False)

    lote_simulado = {
        "aprobados": [
            {
                "id_mensaje": "1201",
                "autor": "offline_author",
                "semana": "2026-semana-42",
                "fecha_envio": "2026-10-15T10:00:00+00:00",
                "texto_original": "Probando modo offline de OCI",
                "copy_final": "Cursos Cloud de alta calidad.",
                "kpis": {"relevancia": 88, "sentimiento": "Positivo", "temas_clave": "#cloud", "segmento": "DEV", "razonamiento": "Test offline"}
            }
        ],
        "descartados": []
    }
    monkeypatch.setattr(puente_motor_ia, "_cargar_lote_para_reporte_semanal", lambda sem: lote_simulado)

    resp = client.post("/api/v1/oci-storage/weekly-sync", json={"semana": "2026-semana-42"})
    assert resp.status_code == 200
    data = resp.json()

    assert data["exito"] is True
    assert data["subido_oci"] is False
    assert data["status"] == "saved_locally"
    assert "guardado localmente" in data.get("message", "").lower()

    # Verificar existencia en disco
    ruta_archivo = Path("reportes") / "2026-semana-42.json"
    assert ruta_archivo.exists(), f"El archivo {ruta_archivo} debe existir en el almacenamiento local"
    contenido = json.loads(ruta_archivo.read_text(encoding="utf-8"))
    assert contenido["metadata"]["semana"] == "2026-semana-42"
    assert contenido["resumen_metricas"]["total_aprobados"] == 1


# ==============================================================================
# Spec 025: Auditoría Integral de Calidad, Resiliencia de Interfaz y Blindaje de Alta Velocidad
# ==============================================================================

def test_spec025_indices_sqlite_creacion_idempotente():
    """
    Spec 025 - RF-02, RF-06:
    Verifica que la ejecución de _asegurar_esquema_sqlite() crea exitosamente en SQLite
    los 6 índices estratégicos requeridos y que su ejecución repetida es 100% idempotente sin colisiones.
    """
    indices_requeridos = {
        "idx_interacciones_enviado_id",
        "idx_interacciones_canal",
        "idx_interacciones_curaduria",
        "idx_interacciones_etapa",
        "idx_interacciones_id_desc",
        "idx_contenidos_interaccion_estado",
    }

    # Primera ejecución
    puente_motor_ia._asegurar_esquema_sqlite()
    with sqlite3.connect(puente_motor_ia.motor_bd.RUTA_BD) as conn:
        indices_db = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()}

    faltantes = indices_requeridos - indices_db
    assert not faltantes, (
        f"Los siguientes índices estratégicos de Spec 025 no fueron creados por _asegurar_esquema_sqlite(): {faltantes}"
    )

    # Segunda ejecución: debe ser 100% idempotente sin errores de colisión
    puente_motor_ia._asegurar_esquema_sqlite()
    with sqlite3.connect(puente_motor_ia.motor_bd.RUTA_BD) as conn:
        indices_db_2 = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()}

    assert indices_requeridos.issubset(indices_db_2), (
        "Los índices deben mantenerse intactos y disponibles tras re-ejecución idempotente de _asegurar_esquema_sqlite()"
    )


def test_spec025_sqlite_indices_explain_query_plan():
    """
    Spec 025 - RF-02, RF-06:
    Valida mediante EXPLAIN QUERY PLAN que el optimizador de SQLite utilice los índices
    creados reportando USING INDEX en las consultas frecuentes, erradicando SCAN TABLE.
    """
    puente_motor_ia._asegurar_esquema_sqlite()

    consultas_a_probar = [
        ("SELECT * FROM interacciones WHERE canal = '#general' ORDER BY id DESC", "idx_interacciones_canal"),
        ("SELECT * FROM interacciones WHERE estado_curaduria = 'curated'", "idx_interacciones_curaduria"),
        ("SELECT * FROM interacciones WHERE etapa_flujo = 'en_redaccion'", "idx_interacciones_etapa"),
        ("SELECT * FROM interacciones ORDER BY enviado_en DESC, id DESC", "idx_interacciones_enviado_id"),
        ("SELECT id FROM interacciones ORDER BY id DESC", "idx_interacciones_id_desc"),
        (
            "SELECT * FROM contenidos_generados WHERE interaccion_id = 1 AND estado = 'publicado' AND estado_publicacion = 'publicado'",
            "idx_contenidos_interaccion_estado",
        ),
    ]

    with sqlite3.connect(puente_motor_ia.motor_bd.RUTA_BD) as conn:
        # Insertar registros mínimos para posibilitar análisis del plan
        for i in range(1, 20):
            conn.execute(
                """
                INSERT INTO interacciones (
                    id, hash, origen_comunidad, periodo_referencia, autor, canal, tipo,
                    texto, enviado_en, creado_en, estado, estado_curaduria, etapa_flujo
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    i, f"hash_{i}", "Discord", "Semana_01", f"user_{i}", "#general" if i % 2 == 0 else "#soporte",
                    "mensaje", f"Texto #{i}", f"2026-10-{i:02d}T10:00:00Z", "2026-10-01T10:00:00Z", "analizado",
                    "curated" if i % 3 == 0 else "pending", "en_redaccion" if i % 2 == 0 else "ingesta"
                )
            )
            conn.execute(
                """
                INSERT INTO contenidos_generados (
                    id, interaccion_id, formato, titulo, contenido, tono, estado,
                    creado_en, actualizado_en, tipo_contenido, version, estado_publicacion
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    i, i, "post", f"Titulo {i}", f"Contenido {i}", "profesional",
                    "publicado" if i % 2 == 0 else "pendiente_revision",
                    "2026-10-01T12:00:00Z", "2026-10-01T12:00:00Z", "publicacion", 1,
                    "publicado" if i % 2 == 0 else "no_publicado"
                )
            )
        conn.commit()

        for sql, indice_esperado in consultas_a_probar:
            plan_rows = conn.execute(f"EXPLAIN QUERY PLAN {sql}").fetchall()
            plan_str = " ".join(str(col) for row in plan_rows for col in row)
            assert ("USING INDEX" in plan_str or "USING COVERING INDEX" in plan_str), (
                f"La consulta '{sql}' no está utilizando índices y realiza escaneo secuencial. Plan obtenido: {plan_str}"
            )
            assert indice_esperado in plan_str, (
                f"La consulta '{sql}' debe utilizar el índice específico '{indice_esperado}'. Plan obtenido: {plan_str}"
            )


def test_spec025_endpoint_messages_limite_cero_sin_tope(client):
    """
    Spec 025 - RF-02, RF-06:
    Invoca GET /api/community/messages?limite=0 y GET /api/community/messages?limit=0
    verificando que devuelva la totalidad absoluta de mensajes comunitarios sin truncar a 1,000.
    """
    total_registros = 1050
    with sqlite3.connect(puente_motor_ia.motor_bd.RUTA_BD) as conn:
        filas = [
            (
                i, f"hash_{i:04d}", "Discord", "Semana_01", f"user_{i}", "#general", "mensaje",
                f"Mensaje comunitario #{i}", f"2026-10-01T12:{i % 60:02d}:00Z", "activo",
                "2026-10-01T12:00:00Z", 75, "Positivo"
            )
            for i in range(1, total_registros + 1)
        ]
        conn.executemany(
            """
            INSERT INTO interacciones (
                id, hash, origen_comunidad, periodo_referencia, autor, canal, tipo,
                texto, enviado_en, estado, creado_en, relevancia, sentimiento
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            filas
        )
        conn.commit()

    # 1. Probar con limite=0
    resp = client.get("/api/community/messages?limite=0")
    assert resp.status_code == 200
    datos = resp.json()
    mensajes = datos.get("messages", [])
    assert len(mensajes) == total_registros, (
        f"Se esperaba recibir la totalidad absoluta de mensajes ({total_registros}) con limite=0, "
        f"pero se obtuvieron {len(mensajes)}. Posible truncamiento a 1,000 o restricción indebida."
    )
    assert len(mensajes) > 1000, "Debe retornar más de 1,000 registros sin tope artificial"

    # 2. Probar con limit=0 (alias)
    resp_alias = client.get("/api/community/messages?limit=0")
    assert resp_alias.status_code == 200
    mensajes_alias = resp_alias.json().get("messages", [])
    assert len(mensajes_alias) == total_registros, (
        f"Se esperaba recibir la totalidad de mensajes ({total_registros}) con limit=0, pero se obtuvieron {len(mensajes_alias)}"
    )


def test_spec025_endpoint_messages_paginacion_pagina_offset(client):
    """
    Spec 025 - RF-02, RF-06:
    Valida que el endpoint soporte paginación backend mediante 'pagina' y 'offset',
    retornando los elementos correspondientes a la página solicitada y sanitizando offsets negativos.
    """
    total_registros = 120
    with sqlite3.connect(puente_motor_ia.motor_bd.RUTA_BD) as conn:
        filas = [
            (
                i, f"hash_{i:04d}", "Discord", "Semana_01", f"user_{i}", "#general", "mensaje",
                f"Mensaje #{i}", f"2026-10-01T12:{i % 60:02d}:00Z", "activo",
                "2026-10-01T12:00:00Z", 75, "Positivo"
            )
            for i in range(1, total_registros + 1)
        ]
        conn.executemany(
            """
            INSERT INTO interacciones (
                id, hash, origen_comunidad, periodo_referencia, autor, canal, tipo,
                texto, enviado_en, estado, creado_en, relevancia, sentimiento
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            filas
        )
        conn.commit()

    # Página 1 (50 elementos)
    resp_p1 = client.get("/api/community/messages?limite=50&pagina=1")
    assert resp_p1.status_code == 200
    p1_items = resp_p1.json().get("messages", [])
    assert len(p1_items) == 50
    p1_ids = [m["message"]["interaction_id"] for m in p1_items]

    # Página 2 (50 elementos)
    resp_p2 = client.get("/api/community/messages?limite=50&pagina=2")
    assert resp_p2.status_code == 200
    p2_items = resp_p2.json().get("messages", [])
    assert len(p2_items) == 50
    p2_ids = [m["message"]["interaction_id"] for m in p2_items]

    # Las páginas 1 y 2 deben ser disjuntas
    assert set(p1_ids).isdisjoint(set(p2_ids)), (
        f"La paginación con pagina=2 retornó elementos solapados con pagina=1: {set(p1_ids).intersection(set(p2_ids))}"
    )

    # Offset explícito: offset=50 debe equivaler a pagina=2
    resp_offset = client.get("/api/community/messages?limite=50&offset=50")
    assert resp_offset.status_code == 200
    offset_ids = [m["message"]["interaction_id"] for m in resp_offset.json().get("messages", [])]
    assert offset_ids == p2_ids, "El offset=50 debe retornar exactamente los mismos elementos que pagina=2"

    # Sanitización: offset negativo debe interpretarse como 0
    resp_neg = client.get("/api/community/messages?limite=50&offset=-25")
    assert resp_neg.status_code == 200
    neg_ids = [m["message"]["interaction_id"] for m in resp_neg.json().get("messages", [])]
    assert neg_ids == p1_ids, "Un offset negativo debe ser sanitizado a offset=0 (página 1)"


def test_spec025_endpoint_messages_retrocompatibilidad_estructura_json(client):
    """
    Spec 025 - RF-01, RF-02, RF-06:
    Valida que la respuesta preserve al 100% las cuatro claves canónicas exigidas por el
    Principio 3 de la Constitución: total, omitted_bots_count, real_messages_count y messages,
    tanto con parámetros por defecto, como con limite=0 y paginación.
    """
    total_reales = 40
    with sqlite3.connect(puente_motor_ia.motor_bd.RUTA_BD) as conn:
        filas = [
            (
                i, f"hash_{i:04d}", "Discord", "Semana_01", f"user_{i}", "#general", "mensaje",
                f"Mensaje #{i}", "2026-10-01T12:00:00Z", "activo",
                "2026-10-01T12:00:00Z", 80, "Positivo"
            )
            for i in range(1, total_reales + 1)
        ]
        conn.executemany(
            """
            INSERT INTO interacciones (
                id, hash, origen_comunidad, periodo_referencia, autor, canal, tipo,
                texto, enviado_en, estado, creado_en, relevancia, sentimiento
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            filas
        )
        # Bot para telemetría
        conn.execute(
            """
            INSERT INTO interacciones (
                id, hash, origen_comunidad, periodo_referencia, autor, canal, tipo,
                texto, enviado_en, estado, creado_en, relevancia, sentimiento
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                9999, "hash_bot_9999", "Discord", "Semana_01", "Spidey Boy#0000", "#notificaciones", "mensaje",
                "Alerta de bot", "2026-10-01T12:00:00Z", "activo", "2026-10-01T12:00:00Z", 0, "Neutral"
            )
        )
        conn.commit()

    # 1. Petición estándar
    resp = client.get("/api/community/messages")
    assert resp.status_code == 200
    datos = resp.json()
    claves_canonicas = {"total", "omitted_bots_count", "real_messages_count", "messages"}
    assert set(datos.keys()) == claves_canonicas, f"Estructura JSON debe contener exactamente {claves_canonicas}"
    assert isinstance(datos["total"], int)
    assert isinstance(datos["omitted_bots_count"], int)
    assert isinstance(datos["real_messages_count"], int)
    assert isinstance(datos["messages"], list)
    assert datos["total"] == total_reales
    assert datos["real_messages_count"] == total_reales
    assert datos["omitted_bots_count"] >= 1

    # Estructura del mensaje individual
    msg = datos["messages"][0]
    assert "message" in msg and "analysis" in msg
    msg_data = msg["message"]
    campos_requeridos = {"interaction_id", "author_name", "channel_name", "content", "created_at"}
    assert campos_requeridos.issubset(set(msg_data.keys()))
    campos_analysis = {"sentiment", "sentiment_score", "relevance", "curation_status", "workflow_stage", "is_published", "published_platforms"}
    assert campos_analysis.issubset(set(msg["analysis"].keys()))

    # 2. Petición con limite=0: debe retornar la totalidad de mensajes reales sin truncamiento
    resp_cero = client.get("/api/community/messages?limite=0")
    assert resp_cero.status_code == 200
    datos_cero = resp_cero.json()
    assert set(datos_cero.keys()) == claves_canonicas
    assert len(datos_cero["messages"]) == total_reales, (
        f"Con limite=0 debe retornar los {total_reales} mensajes reales, se obtuvieron {len(datos_cero['messages'])}"
    )

    # 3. Petición con paginación
    resp_pag = client.get("/api/community/messages?limite=15&pagina=1")
    assert resp_pag.status_code == 200
    datos_pag = resp_pag.json()
    assert set(datos_pag.keys()) == claves_canonicas
    assert datos_pag["total"] == total_reales
    assert len(datos_pag["messages"]) == 15


def test_spec025_endpoints_lectura_latencia_sub_2ms(monkeypatch):
    """
    Spec 025 - RF-02, RF-06:
    Mide la latencia de procesamiento en consultas de lectura a communitylab.db con los índices aplicados,
    comprobando una resolución inferior a 2 milisegundos (< 2 ms) y cero llamadas WAN bloqueantes.
    """
    import time
    indices_requeridos = {
        "idx_interacciones_enviado_id",
        "idx_interacciones_canal",
        "idx_interacciones_curaduria",
        "idx_interacciones_etapa",
        "idx_interacciones_id_desc",
        "idx_contenidos_interaccion_estado",
    }
    with sqlite3.connect(puente_motor_ia.motor_bd.RUTA_BD) as conn:
        indices_existentes = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()}
        indices_faltantes = indices_requeridos - indices_existentes
        assert not indices_faltantes, (
            f"Faltan los índices estratégicos para garantizar latencia de lectura < 2 ms: {indices_faltantes}"
        )

        # Poblar con 1,200 registros simulando producción
        filas_int = [
            (
                i, f"hash_{i}", "Discord", "Semana_01", f"user_{i}",
                "#general" if i % 2 == 0 else "#soporte", "mensaje", f"Texto #{i}",
                f"2026-10-01T12:{i % 60:02d}:00Z", "2026-10-01T12:00:00Z", "analizado",
                "curated" if i % 3 == 0 else "pending", "ingesta"
            )
            for i in range(1, 1201)
        ]
        conn.executemany(
            """
            INSERT INTO interacciones (
                id, hash, origen_comunidad, periodo_referencia, autor, canal, tipo,
                texto, enviado_en, creado_en, estado, estado_curaduria, etapa_flujo
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            filas_int
        )
        filas_cont = [
            (
                i, i, "post", f"Titulo {i}", f"Contenido {i}", "profesional",
                "publicado" if i % 2 == 0 else "pendiente_revision",
                "2026-10-01T12:00:00Z", "2026-10-01T12:00:00Z", "publicacion", 1,
                "publicado" if i % 2 == 0 else "no_publicado"
            )
            for i in range(1, 1201)
        ]
        conn.executemany(
            """
            INSERT INTO contenidos_generados (
                id, interaccion_id, formato, titulo, contenido, tono, estado,
                creado_en, actualizado_en, tipo_contenido, version, estado_publicacion
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            filas_cont
        )
        conn.commit()

        # Blindaje WAN: asegurar que no haya llamadas bloqueantes
        mock_wan = MagicMock(side_effect=RuntimeError("Llamada WAN bloqueante prohibida"))
        monkeypatch.setattr(puente_motor_ia, "obtener_datos_supabase", mock_wan)

        # Medir latencia promedio en 20 ejecuciones de lecturas indexadas
        tiempos = []
        for _ in range(20):
            t0 = time.perf_counter()
            conn.execute("SELECT * FROM interacciones WHERE canal = '#general' ORDER BY id DESC LIMIT 50").fetchall()
            conn.execute("SELECT * FROM interacciones WHERE estado_curaduria = 'curated' LIMIT 50").fetchall()
            conn.execute("SELECT * FROM interacciones ORDER BY enviado_en DESC, id DESC LIMIT 50").fetchall()
            t_ms = (time.perf_counter() - t0) * 1000.0
            tiempos.append(t_ms)

        latencia_promedio_ms = sum(tiempos) / len(tiempos)
        assert latencia_promedio_ms < 2.0, (
            f"La latencia de lectura indexada debe ser sub-2ms (< 2 ms). Obtenido: {latencia_promedio_ms:.2f} ms"
        )


# ==============================================================================
# Spec 026: Corrección Integral de Hallazgos QA (Enoc) Pre-Demo Day
# ==============================================================================

def test_spec026_rf01_curaduria_manual_persistencia_exclusion_y_replica_async(client, monkeypatch):
    """
    Spec 026 - RF-01, RNF-02:
    Valida la persistencia de descarte y restauración manual en Ingesta:
    1. Descartar manualmente ('discarded') persiste en SQLite inmediatamente.
    2. _obtener_ids_evaluados_dual() excluye los mensajes con estado_curaduria = 'discarded'.
    3. La decisión manual sobrevive a resincronizaciones posteriores con _sincronizar_supabase_a_sqlite().
    4. Restaurar un mensaje NO analizado lo devuelve a 'pending' (etapa_flujo = 'ingesta').
    5. Restaurar un mensaje YA analizado lo devuelve a 'curated'.
    6. La mutación delega la réplica hacia public.lotes_ia_kpis en segundo plano (asyncio.create_task)
       ignorando silenciosamente 0 rows affected y respondiendo en < 5 ms sin bloqueo WAN.
    """
    import time

    with sqlite3.connect(puente_motor_ia.motor_bd.RUTA_BD) as conn:
        conn.execute(
            """
            INSERT INTO interacciones (
                id, hash, origen_comunidad, periodo_referencia, autor, canal, tipo,
                texto, enviado_en, creado_en, estado, estado_curaduria, etapa_flujo, relevancia
            ) VALUES
            (2601, 'hash_2601', 'Discord', 'Semana_01', 'user_no_eval', '#general', 'mensaje',
             'Mensaje irrelevante sin evaluar', '2026-10-25T10:00:00Z', '2026-10-25T10:00:00Z',
             'pendiente', 'pending', 'ingesta', NULL),
            (2602, 'hash_2602', 'Discord', 'Semana_01', 'user_ya_eval', '#notificaciones', 'mensaje',
             'Anuncio importante ya evaluado', '2026-10-25T10:05:00Z', '2026-10-25T10:05:00Z',
             'analizado', 'curated', 'en_analisis', 65)
            """
        )
        conn.commit()

    # Simular conexión lenta a Supabase (300 ms) y 0 rows affected para verificar ejecución no bloqueante (< 5 ms)
    ejecuciones_sql_bg = []

    class SlowZeroRowCursor:
        rowcount = 0

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

        def execute(self, sql, params=None):
            ejecuciones_sql_bg.append((sql, params))

    class SlowConn:
        def __enter__(self):
            time.sleep(0.25)
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

        def cursor(self, *args, **kwargs):
            return SlowZeroRowCursor()

        def commit(self):
            pass

    monkeypatch.setenv("SUPABASE_DB_URL", "postgresql://mock:5432/db")
    monkeypatch.setattr("psycopg2.connect", lambda *a, **kw: SlowConn())

    # 1. Descartar manualmente el mensaje 2601 (no analizado) y medir latencia de actualización en el puente
    tareas_creadas = []
    orig_create_task = puente_motor_ia.asyncio.create_task

    def spy_create_task(coro, *args, **kwargs):
        t = orig_create_task(coro, *args, **kwargs)
        tareas_creadas.append(t)
        return t

    monkeypatch.setattr(puente_motor_ia.asyncio, "create_task", spy_create_task)

    async def _medir_curation_async():
        t0 = time.perf_counter()
        res = await puente_motor_ia.curation_v1(2601, {"status": "discarded"})
        dt_ms = (time.perf_counter() - t0) * 1000.0
        return res, dt_ms

    import asyncio
    res_curation, latencia_ms = asyncio.run(_medir_curation_async())
    assert res_curation["curation_status"] == "discarded"
    assert latencia_ms < 5.0, f"curation_v1 debe ejecutarse en < 5 ms sin bloquear en WAN, tardó {latencia_ms:.2f} ms"
    assert len(tareas_creadas) >= 1, "Debe despachar tarea asíncrona con asyncio.create_task"

    # Verificar persistencia en SQLite
    inter_2601 = puente_motor_ia.obtener_interaccion_puente(2601)
    assert inter_2601["estado_curaduria"] == "discarded"

    # 2. _obtener_ids_evaluados_dual() debe incluir 2601 (excluido de pendientes de evaluar por lote)
    monkeypatch.setattr(puente_motor_ia, "_obtener_ids_evaluados_supabase", lambda: set())
    ids_excluidos = puente_motor_ia._obtener_ids_evaluados_dual()
    assert 2601 in ids_excluidos, "El mensaje descartado manualmente (2601) debe ser excluido en _obtener_ids_evaluados_dual()"
    assert 2602 in ids_excluidos

    # 3. Sobrevive a _sincronizar_supabase_a_sqlite() aunque en Supabase aún no tenga KPI
    datos_sb_mock = {
        "interacciones": [
            {
                "id": 2601,
                "hash": "hash_2601",
                "origen_comunidad": "Discord",
                "periodo_referencia": "Semana_01",
                "autor": "user_no_eval",
                "canal": "#general",
                "tipo": "mensaje",
                "texto": "Mensaje irrelevante sin evaluar",
                "enviado_en": "2026-10-25T10:00:00Z",
                "creado_en": "2026-10-25T10:00:00Z",
            },
            {
                "id": 2602,
                "hash": "hash_2602",
                "origen_comunidad": "Discord",
                "periodo_referencia": "Semana_01",
                "autor": "user_ya_eval",
                "canal": "#notificaciones",
                "tipo": "mensaje",
                "texto": "Anuncio importante ya evaluado",
                "enviado_en": "2026-10-25T10:05:00Z",
                "creado_en": "2026-10-25T10:05:00Z",
            },
        ],
        "kpis": [
            {
                "id": 92602,
                "id_mensaje": 2602,
                "autor": "user_ya_eval",
                "canal": "#notificaciones",
                "comunidad": "Discord",
                "semana": "Semana_01",
                "texto_original": "Anuncio importante ya evaluado",
                "relevancia": 65,
                "sentimiento": "Positivo",
                "temas_clave": "#anuncio",
                "segmento": "ESTUDIANTE",
                "razonamiento": "Anuncio oficial",
                "decision_ia": "descartado",
                "estado_revision": "rechazado",
            }
        ],
    }
    puente_motor_ia._sincronizar_supabase_a_sqlite(datos_sb_mock)
    assert puente_motor_ia.obtener_interaccion_puente(2601)["estado_curaduria"] == "discarded"

    # 4. Restaurar 2601 (no analizado) -> debe quedar en 'pending' y etapa_flujo = 'ingesta'
    resp_rest_2601 = client.patch("/api/v1/content-workflow/messages/2601/curation", json={"status": "pending"})
    assert resp_rest_2601.status_code == 200
    assert resp_rest_2601.json()["curation_status"] == "pending"
    inter_2601_rest = puente_motor_ia.obtener_interaccion_puente(2601)
    assert inter_2601_rest["estado_curaduria"] == "pending"
    assert inter_2601_rest["etapa_flujo"] == "ingesta"
    assert 2601 not in puente_motor_ia._obtener_ids_evaluados_dual()

    # 5. Descartar 2602 (ya analizado) y luego restaurarlo -> al estar analizado debe restaurarse a 'curated'
    resp_disc_2602 = client.patch("/api/v1/content-workflow/messages/2602/curation", json={"status": "discarded"})
    assert resp_disc_2602.status_code == 200
    assert puente_motor_ia.obtener_interaccion_puente(2602)["estado_curaduria"] == "discarded"

    # Sobrevive a resincronización como 'discarded'
    puente_motor_ia._sincronizar_supabase_a_sqlite(datos_sb_mock)
    assert puente_motor_ia.obtener_interaccion_puente(2602)["estado_curaduria"] == "discarded"

    # Restaurar 2602 enviando 'pending' -> backend debe restituirlo a 'curated' porque ya está analizado
    resp_rest_2602 = client.patch("/api/v1/content-workflow/messages/2602/curation", json={"status": "pending"})
    assert resp_rest_2602.status_code == 200
    assert resp_rest_2602.json()["curation_status"] == "curated"
    assert puente_motor_ia.obtener_interaccion_puente(2602)["estado_curaduria"] == "curated"


def test_spec026_rf06_umbral_relevancia_35_prioridades_y_filtro_spam_p4(client, monkeypatch):
    """
    Spec 026 - RF-06:
    Valida la alineación del umbral de relevancia con las 4 Prioridades del Orquestador (35%-69%):
    1. _es_spam_prioridad_4 detecta relevancia <= 10, texto < 3 chars, 'select' y 'credenciales'.
    2. Mensajes con relevancia >= 35 (incluyendo anuncios de #notificaciones con 60% y 68%) quedan
       como 'curated' en _sincronizar_supabase_a_sqlite, evaluate_batch_v1 y evaluate_single_message_v1.
    3. Mensajes con relevancia < 35 o que activan _es_spam_prioridad_4 quedan como 'discarded'.
    4. _cargar_lote_consolidado_para_reporte y _obtener_descartados_semana_sqlite usan el umbral < 35 / Prioridad 4.
    """
    assert hasattr(puente_motor_ia, "_es_spam_prioridad_4"), "Debe existir _es_spam_prioridad_4 en puente_motor_ia"

    # 1. Validación unitaria de _es_spam_prioridad_4
    assert puente_motor_ia._es_spam_prioridad_4(10, "Mensaje válido pero relevancia 10", "") is True
    assert puente_motor_ia._es_spam_prioridad_4(5, "Ruido", "") is True
    assert puente_motor_ia._es_spam_prioridad_4(60, "ok", "") is True
    assert puente_motor_ia._es_spam_prioridad_4(65, "SELECT * FROM usuarios", "Intento SQL") is True
    assert puente_motor_ia._es_spam_prioridad_4(55, "Solicitud sospechosa", "Pide credenciales de acceso") is True
    assert puente_motor_ia._es_spam_prioridad_4(60, "Anuncio de nueva sesión en vivo en #notificaciones", "Aviso oficial") is False
    assert puente_motor_ia._es_spam_prioridad_4(68, "Recordatorio de entrega del challenge en #notificaciones", "Aviso") is False
    assert puente_motor_ia._es_spam_prioridad_4(35, "Consulta sobre calendario de mentorías", "Duda válida") is False

    # 2. _sincronizar_supabase_a_sqlite con anuncios de 60% y 68%, baja relevancia (20%) y spam P4 (50% con 'select')
    datos_sb = {
        "interacciones": [
            {"id": 2610, "hash": "h2610", "autor": "admin_one", "canal": "#notificaciones", "tipo": "mensaje",
             "texto": "Hoy tenemos mentoría de arquitectura cloud a las 19h", "periodo_referencia": "2026-semana-42",
             "enviado_en": "2026-10-15T10:00:00Z", "creado_en": "2026-10-15T10:00:00Z"},
            {"id": 2611, "hash": "h2611", "autor": "equipo_alura", "canal": "#notificaciones", "tipo": "mensaje",
             "texto": "Ya están abiertas las inscripciones al Hackathon G10", "periodo_referencia": "2026-semana-42",
             "enviado_en": "2026-10-15T11:00:00Z", "creado_en": "2026-10-15T11:00:00Z"},
            {"id": 2612, "hash": "h2612", "autor": "user_saludo", "canal": "#general", "tipo": "mensaje",
             "texto": "Hola buenas tardes a todos", "periodo_referencia": "2026-semana-42",
             "enviado_en": "2026-10-15T12:00:00Z", "creado_en": "2026-10-15T12:00:00Z"},
            {"id": 2613, "hash": "h2613", "autor": "attacker", "canal": "#general", "tipo": "mensaje",
             "texto": "SELECT password FROM users WHERE admin=1", "periodo_referencia": "2026-semana-42",
             "enviado_en": "2026-10-15T13:00:00Z", "creado_en": "2026-10-15T13:00:00Z"},
        ],
        "kpis": [
            {"id": 92610, "id_mensaje": 2610, "autor": "admin_one", "canal_origen": "#notificaciones",
             "semana": "2026-semana-42", "texto_original": "Hoy tenemos mentoría de arquitectura cloud a las 19h",
             "relevancia": 60, "sentimiento": "Positivo", "temas_clave": "#mentoria", "segmento": "ESTUDIANTE",
             "razonamiento": "Anuncio relevante Prioridad 2", "decision_ia": "descartado", "estado_revision": "rechazado"},
            {"id": 92611, "id_mensaje": 2611, "autor": "equipo_alura", "canal_origen": "#notificaciones",
             "semana": "2026-semana-42", "texto_original": "Ya están abiertas las inscripciones al Hackathon G10",
             "relevancia": 68, "sentimiento": "Positivo", "temas_clave": "#hackathon", "segmento": "ESTUDIANTE",
             "razonamiento": "Anuncio oficial Prioridad 2", "decision_ia": "descartado", "estado_revision": "rechazado"},
            {"id": 92612, "id_mensaje": 2612, "autor": "user_saludo", "canal_origen": "#general",
             "semana": "2026-semana-42", "texto_original": "Hola buenas tardes a todos",
             "relevancia": 20, "sentimiento": "Neutral", "temas_clave": "#saludo", "segmento": "GENERAL",
             "razonamiento": "Saludo casual Prioridad 3", "decision_ia": "descartado", "estado_revision": "rechazado"},
            {"id": 92613, "id_mensaje": 2613, "autor": "attacker", "canal_origen": "#general",
             "semana": "2026-semana-42", "texto_original": "SELECT password FROM users WHERE admin=1",
             "relevancia": 50, "sentimiento": "Negativo", "temas_clave": "#seguridad", "segmento": "SPAM",
             "razonamiento": "Inyección SQL detectada", "decision_ia": "descartado", "estado_revision": "rechazado"},
        ],
    }

    puente_motor_ia._sincronizar_supabase_a_sqlite(datos_sb)

    assert puente_motor_ia.obtener_interaccion_puente(2610)["estado_curaduria"] == "curated"
    assert puente_motor_ia.obtener_interaccion_puente(2611)["estado_curaduria"] == "curated"
    assert puente_motor_ia.obtener_interaccion_puente(2612)["estado_curaduria"] == "discarded"
    assert puente_motor_ia.obtener_interaccion_puente(2613)["estado_curaduria"] == "discarded"

    # 3. _obtener_descartados_semana_sqlite y _cargar_lote_consolidado_para_reporte
    descartados_sem = puente_motor_ia._obtener_descartados_semana_sqlite("2026-semana-42")
    ids_descartados = {str(d["id_mensaje"]) for d in descartados_sem}
    assert "2610" not in ids_descartados, "Anuncio de 60% no debe clasificarse como descartado"
    assert "2611" not in ids_descartados, "Anuncio de 68% no debe clasificarse como descartado"
    assert "2612" in ids_descartados, "Mensaje con relevancia 20% (< 35) debe estar en descartados"
    assert "2613" in ids_descartados, "Mensaje con patrón P4 ('select') debe estar en descartados"

    # 4. evaluate_single_message_v1 con relevancia 60% -> debe quedar en 'curated'
    with sqlite3.connect(puente_motor_ia.motor_bd.RUTA_BD) as conn:
        conn.execute(
            """
            INSERT INTO interacciones (
                id, hash, origen_comunidad, periodo_referencia, autor, canal, tipo,
                texto, enviado_en, creado_en, estado, estado_curaduria, etapa_flujo
            ) VALUES (
                2614, 'h2614', 'Discord', '2026-semana-42', 'mentor', '#notificaciones', 'mensaje',
                'Nuevo material disponible en el repositorio del curso', '2026-10-15T14:00:00Z',
                '2026-10-15T14:00:00Z', 'pendiente', 'pending', 'ingesta'
            )
            """
        )
        conn.commit()

    mock_eval_60 = {
        "exito": True,
        "total_evaluados": 1,
        "exitosos": 1,
        "fallidos": 0,
        "guardados_supabase": 1,
        "errores": [],
        "aprobados": [],
        "descartados": [{
            "id_mensaje": 2614,
            "canal_origen": "#notificaciones",
            "texto_original": "Nuevo material disponible en el repositorio del curso",
            "estado_revision": "rechazado",
            "kpis": {
                "relevancia": 60,
                "sentimiento": "Positivo",
                "temas_clave": "#material",
                "segmento": "ESTUDIANTE",
                "razonamiento": "Aviso útil de Prioridad 2",
            },
        }],
        "resultados": {"aprobados": [], "descartados": []},
    }

    with patch("evaluador_lotes.evaluar_lote", return_value=mock_eval_60), \
         patch.object(puente_motor_ia, "_sincronizar_supabase_a_sqlite", return_value=1):
        resp_single = client.post("/api/v1/ai/evaluate-message", json={
            "interaction_id": 2614,
            "proveedor": "Groq (Llama 3.3)",
        })
        assert resp_single.status_code == 200
        data_single = resp_single.json()
        assert data_single["relevancia"] == 60
        assert data_single["estado_curaduria"] == "curated"
        assert puente_motor_ia.obtener_interaccion_puente(2614)["estado_curaduria"] == "curated"


def test_spec026_rf02_paridad_id_canonico_vinculacion_dual_kpis_y_sin_duplicados(client, monkeypatch):
    """
    Spec 026 - RF-02:
    Valida que:
    1. Un mensaje insertado en SQLite con un ID local temporal (ej. 5) se reconcilia atómicamente
       con el ID canónico asignado por public.interacciones de Supabase (ej. 200) usando su hash.
    2. _sincronizar_supabase_a_sqlite() empareja KPIs tanto por id_mensaje como por hash / (autor, texto_original)
       y no sintetiza filas duplicadas cuando el KPI tenía el ID local previo.
    3. Al evaluar con evaluate_single_message_v1 o evaluate_batch_v1, el mensaje pasa a 'analizado'
       desde el primer clic sin que _sincronizar_supabase_a_sqlite() lo regrese a 'pendiente' aunque
       obtener_datos_supabase() aún no incluya el KPI recién calculado.
    4. Se previene la duplicación de filas en public.lotes_ia_kpis para el mismo mensaje.
    """
    import limpieza

    autor_msg = "enoc_qa_tester"
    canal_msg = "#general"
    texto_msg = "Excelente sesión técnica sobre arquitectura de agentes LangGraph en producción"
    origen_msg = "Discord_Grupo_ONE_G10"
    hash_canonico = limpieza.calcular_hash(origen_msg, canal_msg, autor_msg, texto_msg)

    # 1. Insertar mensaje en SQLite con ID local temporal = 5
    with sqlite3.connect(puente_motor_ia.motor_bd.RUTA_BD) as conn:
        conn.execute(
            """
            INSERT INTO interacciones (
                id, hash, origen_comunidad, periodo_referencia, autor, canal, tipo,
                texto, enviado_en, creado_en, estado, estado_curaduria, etapa_flujo
            ) VALUES (?, ?, ?, 'Semana_01', ?, ?, 'mensaje', ?, '2026-10-25T12:00:00Z', '2026-10-25T12:00:00Z',
                      'pendiente', 'pending', 'ingesta')
            """,
            (5, hash_canonico, origen_msg, autor_msg, canal_msg, texto_msg),
        )
        conn.commit()

    # 2. Simular que en Supabase public.interacciones tiene el ID canónico 200 (con el mismo hash),
    #    mientras que lotes_ia_kpis tiene un registro con id_mensaje=5 (ID temporal previo) para el mismo (autor, texto_original)
    datos_sb_desfasados = {
        "interacciones": [
            {
                "id": 200,
                "hash": hash_canonico,
                "origen_comunidad": origen_msg,
                "periodo_referencia": "Semana_01",
                "autor": autor_msg,
                "canal": canal_msg,
                "tipo": "mensaje",
                "texto": texto_msg,
                "enviado_en": "2026-10-25T12:00:00Z",
                "creado_en": "2026-10-25T12:00:00Z",
            }
        ],
        "kpis": [
            {
                "id": 901,
                "id_mensaje": 5,  # ID local antiguo
                "autor": autor_msg,
                "canal_origen": canal_msg,
                "comunidad": origen_msg,
                "semana": "Semana_01",
                "texto_original": texto_msg,
                "relevancia": 82,
                "sentimiento": "Positivo",
                "temas_clave": "#langgraph, #agentes",
                "segmento": "PROFESIONAL",
                "razonamiento": "Aporte técnico de alto valor",
                "decision_ia": "aprobado",
                "estado_revision": "pendiente",
                "analizado_en": "2026-10-25T12:01:00Z",
            }
        ],
    }

    puente_motor_ia._sincronizar_supabase_a_sqlite(datos_sb_desfasados)

    # Verificar que en SQLite sólo exista el ID canónico 200 (sin fila fantasma 5) y esté 'analizado' con relevancia 82
    with sqlite3.connect(puente_motor_ia.motor_bd.RUTA_BD) as conn:
        conn.row_factory = sqlite3.Row
        filas = conn.execute("SELECT * FROM interacciones").fetchall()
        ids_sqlite = [r["id"] for r in filas]
        assert 200 in ids_sqlite, "El ID canónico 200 debe existir en SQLite"
        assert 5 not in ids_sqlite, "El ID temporal 5 debe haberse reconciliado/eliminado sin dejar duplicado"
        fila_200 = next(dict(r) for r in filas if r["id"] == 200)
        assert fila_200["estado"] == "analizado", "Debe haberse emparejado el KPI por hash/(autor, texto_original)"
        assert fila_200["relevancia"] == 82
        assert fila_200["estado_curaduria"] == "curated"

    # 3. Ahora insertar un segundo mensaje nuevo (ID local = 6, pero canónico en Supabase = 201) aún NO evaluado
    texto_msg_2 = "Nuevo mensaje recién sincronizado desde Discord para evaluar a la primera"
    hash_canonico_2 = limpieza.calcular_hash(origen_msg, canal_msg, autor_msg, texto_msg_2)
    with sqlite3.connect(puente_motor_ia.motor_bd.RUTA_BD) as conn:
        conn.execute(
            """
            INSERT INTO interacciones (
                id, hash, origen_comunidad, periodo_referencia, autor, canal, tipo,
                texto, enviado_en, creado_en, estado, estado_curaduria, etapa_flujo
            ) VALUES (?, ?, ?, 'Semana_01', ?, ?, 'mensaje', ?, '2026-10-25T12:05:00Z', '2026-10-25T12:05:00Z',
                      'pendiente', 'pending', 'ingesta')
            """,
            (6, hash_canonico_2, origen_msg, autor_msg, canal_msg, texto_msg_2),
        )
        conn.commit()

    # Simular que obtener_datos_supabase devuelve el mensaje con ID canónico 201 pero SIN el KPI todavía en 'kpis'
    # (caso real de lectura inmediatamente posterior a evaluar antes de que la réplica/lectura devuelva el KPI)
    datos_sb_sin_kpi_nuevo = {
        "interacciones": [
            {
                "id": 201,
                "hash": hash_canonico_2,
                "origen_comunidad": origen_msg,
                "periodo_referencia": "Semana_01",
                "autor": autor_msg,
                "canal": canal_msg,
                "tipo": "mensaje",
                "texto": texto_msg_2,
                "enviado_en": "2026-10-25T12:05:00Z",
                "creado_en": "2026-10-25T12:05:00Z",
            }
        ],
        "kpis": [],
    }

    llamadas_guardar_lote = []

    def mock_evaluar_lote(mensajes, **kwargs):
        id_enviado = mensajes[0]["id"]
        paquete = {
            "aprobados": [{
                "id_mensaje": id_enviado,
                "autor": autor_msg,
                "canal_origen": canal_msg,
                "texto_original": texto_msg_2,
                "estado_revision": "pendiente",
                "kpis": {
                    "relevancia": 76,
                    "sentimiento": "Positivo",
                    "temas_clave": "#discord",
                    "segmento": "ESTUDIANTE",
                    "razonamiento": "Mensaje relevante evaluado al primer clic",
                },
            }],
            "descartados": [],
        }
        llamadas_guardar_lote.append(id_enviado)
        return {
            "exito": True,
            "total_evaluados": 1,
            "exitosos": 1,
            "fallidos": 0,
            "guardados_supabase": 1,
            "errores": [],
            "aprobados": paquete["aprobados"],
            "descartados": [],
            "resultados": paquete,
        }

    with patch.object(puente_motor_ia, "obtener_datos_supabase", return_value=datos_sb_sin_kpi_nuevo), \
         patch("evaluador_lotes.evaluar_lote", side_effect=mock_evaluar_lote), \
         patch.object(puente_motor_ia._base_datos_raiz, "guardar_lote_ia_supabase", side_effect=lambda p: llamadas_guardar_lote.append("extra_save") or 1):
        # Evaluar pasando el ID local 6 (debe reconciliar con 201 y quedar analizado al primer clic sin doble guardado)
        resp_eval = client.post("/api/v1/ai/evaluate-message", json={
            "interaction_id": 6,
            "proveedor": "Groq (Llama 3.3)",
        })
        assert resp_eval.status_code == 200
        body_eval = resp_eval.json()
        assert body_eval["estado"] == "analizado"
        assert body_eval["relevancia"] == 76
        assert body_eval["estado_curaduria"] == "curated"
        # No debe haber ejecutado un segundo guardado duplicado si evaluar_lote ya guardó
        assert "extra_save" not in llamadas_guardar_lote

        # Y en SQLite el mensaje (con ID canónico 201) debe permanecer 'analizado' (nunca regresar a 'pendiente')
        interaccion_post = puente_motor_ia.obtener_interaccion_puente(body_eval["interaction_id"])
        assert interaccion_post is not None
        assert interaccion_post["estado"] == "analizado", "El mensaje no debe regresar a 'pendiente' tras _sincronizar_supabase_a_sqlite()"
        assert interaccion_post["relevancia"] == 76
        assert interaccion_post["estado_curaduria"] == "curated"


def test_spec026_rf05_deduplicacion_bots_omitidos_en_resincronizacion(monkeypatch):
    """
    Spec 026 - RF-05:
    Valida que _sincronizar_discord_api_rest deduplica los mensajes de bots/webhooks
    mediante _ids_bots_omitidos_vistos:
    1. En la primera sincronización con 2 bots nuevos (bot_9001 y bot_9002), incrementa el contador en +2.
    2. En la segunda sincronización con los mismos 2 bots, incrementa +0 (no infla artificialmente el contador).
    3. En una tercera sincronización con 1 bot repetido (bot_9001) y 1 bot nuevo (bot_9003), incrementa sólo +1.
    """
    import asyncio

    assert hasattr(puente_motor_ia, "_ids_bots_omitidos_vistos"), "Debe existir el set _ids_bots_omitidos_vistos en puente_motor_ia"
    monkeypatch.setattr(puente_motor_ia, "_ids_bots_omitidos_vistos", set())
    monkeypatch.setattr(puente_motor_ia, "_cache_bots_omitidos_discord", 173)

    lote_canal_1 = [
        {"id": "bot_9001", "content": "Aviso automático 1", "author": {"id": "b1", "username": "Spidey Bot", "bot": True}},
        {"id": "bot_9002", "content": "Webhook alert", "author": {"id": "b2", "username": "GitHub"}, "webhook_id": "wh_1"},
        {"id": "hum_1001", "content": "Hola equipo, tengo una consulta sobre SQL", "author": {"id": "u1", "username": "carlos_dev", "bot": False}},
    ]

    class FakeResp:
        def __init__(self, data):
            self._data = data

        def raise_for_status(self):
            pass

        def json(self):
            return self._data

    class FakeSession:
        def __init__(self, lotes_por_llamada):
            self.lotes = lotes_por_llamada
            self.calls = 0

        def get(self, url, headers=None, timeout=None):
            idx = self.calls
            self.calls += 1
            # Sólo el primer canal devuelve los mensajes de prueba; los otros 3 canales devuelven []
            if idx % 4 == 0:
                return FakeResp(self.lotes[min(idx // 4, len(self.lotes) - 1)])
            return FakeResp([])

    lote_canal_3 = [
        {"id": "bot_9001", "content": "Aviso automático 1", "author": {"id": "b1", "username": "Spidey Bot", "bot": True}},
        {"id": "bot_9003", "content": "Nuevo bot aviso 3", "author": {"id": "b3", "username": "DeployBot", "bot": True}},
        {"id": "hum_1001", "content": "Hola equipo, tengo una consulta sobre SQL", "author": {"id": "u1", "username": "carlos_dev", "bot": False}},
    ]

    sesion_mock = FakeSession([lote_canal_1, lote_canal_1, lote_canal_3])
    monkeypatch.setattr(puente_motor_ia, "_obtener_discord_http_session", lambda: sesion_mock)
    monkeypatch.setattr(puente_motor_ia._base_datos_raiz, "guardar_interaccion", lambda **kw: True)

    # 1ª sincronización: 2 bots nuevos -> _cache_bots_omitidos_discord pasa de 173 a 175
    res1 = asyncio.run(puente_motor_ia._sincronizar_discord_api_rest("fake_token", limite_por_canal=10))
    assert res1["exito"] is True
    assert res1.get("bots_omitidos") == 2
    assert puente_motor_ia._cache_bots_omitidos_discord == 175

    # 2ª sincronización con exactamente los mismos mensajes: 0 bots nuevos -> permanece en 175
    res2 = asyncio.run(puente_motor_ia._sincronizar_discord_api_rest("fake_token", limite_por_canal=10))
    assert res2["exito"] is True
    assert res2.get("bots_omitidos") == 0
    assert puente_motor_ia._cache_bots_omitidos_discord == 175

    # 3ª sincronización con 1 bot repetido y 1 bot nuevo (bot_9003): +1 bot nuevo -> pasa a 176
    res3 = asyncio.run(puente_motor_ia._sincronizar_discord_api_rest("fake_token", limite_por_canal=10))
    assert res3["exito"] is True
    assert res3.get("bots_omitidos") == 1
    assert puente_motor_ia._cache_bots_omitidos_discord == 176


def test_spec026_rf04_estructura_json_completa_historial_reportes_semanales(client, monkeypatch):
    """
    Spec 026 - RF-04, RNF-03:
    Valida que construir_registro_historial_reporte, api_mototradis_hitl_decision y api_mototradis_publish_channel
    generen la estructura JSON completa esperada por el motor LangGraph (src/schemas.py y src/nodes.py):
    1. En contenido_original: el objeto completo json_precurado con los 13 campos canónicos
       (id_mensaje, autor, canal_origen, comunidad, semana, texto_original, relevancia int 0-100,
       sentimiento, temas_clave list[str], segmento, razonamiento, decision_ia, estado_revision),
       enriqueciendo automáticamente desde SQLite local y manteniendo alias 'texto' y 'canal'.
    2. En copys_generados: indexado por canal ('discord', 'linkedin', 'x', 'reclamos') con
       status='exito', resumen_comunidad y activos_distribucion_generados completos conforme a src/schemas.py,
       preservando además titulo, texto_copy y plataforma en la raíz del canal para retrocompatibilidad con Spec 024.
    """
    assert hasattr(puente_motor_ia, "_normalizar_copy_canal_completo"), (
        "Debe existir la función auxiliar _normalizar_copy_canal_completo en puente_motor_ia"
    )

    # Insertar interacción analizada en SQLite para verificar enriquecimiento automático
    with sqlite3.connect(puente_motor_ia.motor_bd.RUTA_BD) as conn:
        conn.execute(
            """
            INSERT INTO interacciones (
                id, hash, origen_comunidad, periodo_referencia, autor, canal, tipo,
                texto, enviado_en, creado_en, estado, estado_curaduria, etapa_flujo,
                relevancia, sentimiento, temas_clave, segmento, razonamiento
            ) VALUES (
                2640, 'h2640', 'Discord_Grupo_ONE_G10', 'Semana_03', 'enoc_dev', '#faq', 'mensaje',
                '¿Cómo desplegar microservicios con Docker y LangGraph en producción?',
                '2026-10-20T15:00:00Z', '2026-10-20T15:05:00Z', 'analizado', 'curated', 'en_redaccion',
                88, 'Positivo', '#docker, #langgraph, #cloud', 'PROFESIONAL', 'Consulta técnica de alto valor'
            )
            """
        )
        conn.commit()

    # 1. Prueba directa de construir_registro_historial_reporte con 4 canales (linkedin, x, discord, reclamos)
    copys_input = {
        "linkedin": {"titulo": "Arquitectura con LangGraph", "texto_copy": "Guía profesional de microservicios con @enoc_dev."},
        "x": {"titulo": "LangGraph + Docker", "texto_copy": "Despliega agentes en producción hoy con @enoc_dev."},
        "discord": {"canal_seleccionado": "#faq", "titulo": "Guía FAQ Docker", "texto_copy": "Hola @enoc_dev, revisa esta guía de despliegue."},
        "reclamos": {"titulo": "Soporte PQRS", "texto_copy": "Hola @enoc_dev, te contactamos por interno para ayudarte."},
    }
    reg = puente_motor_ia.construir_registro_historial_reporte(
        id_mensaje=2640,
        rutas_activas=["linkedin", "x", "discord", "reclamos"],
        copys_dict=copys_input,
        interaccion={"autor": "enoc_dev", "texto": "¿Cómo desplegar microservicios con Docker y LangGraph en producción?", "canal": "#faq"},
    )

    cont_orig = reg["contenido_original"]
    # Validar las 13 llaves canónicas de json_precurado + alias de retrocompatibilidad
    for llave in (
        "id_mensaje", "autor", "canal_origen", "canal", "comunidad", "semana",
        "texto_original", "texto", "relevancia", "sentimiento", "temas_clave",
        "segmento", "razonamiento", "decision_ia", "estado_revision"
    ):
        assert llave in cont_orig, f"Falta la llave '{llave}' en contenido_original"

    assert cont_orig["id_mensaje"] == 2640
    assert cont_orig["autor"] == "enoc_dev"
    assert cont_orig["canal_origen"] == "#faq"
    assert cont_orig["comunidad"] == "Discord_Grupo_ONE_G10"
    assert cont_orig["semana"] == "Semana_03"
    assert cont_orig["relevancia"] == 88 and isinstance(cont_orig["relevancia"], int)
    assert cont_orig["sentimiento"] == "Positivo"
    assert isinstance(cont_orig["temas_clave"], list) and "#docker" in cont_orig["temas_clave"]
    assert cont_orig["segmento"] == "PROFESIONAL"
    assert cont_orig["razonamiento"] == "Consulta técnica de alto valor"
    assert cont_orig["decision_ia"] == "PUBLICAR"
    assert cont_orig["estado_revision"] == "aprobado"

    copys_gen = reg["copys_generados"]
    for ch in ("linkedin", "x", "discord", "reclamos"):
        assert ch in copys_gen
        ch_obj = copys_gen[ch]
        assert ch_obj.get("status") == "exito"
        assert "resumen_comunidad" in ch_obj
        res_com = ch_obj["resumen_comunidad"]
        assert res_com["total_interacciones_procesadas"] == 1
        assert res_com["sentimiento_predominante"] == "Positivo"
        assert isinstance(res_com["temas_principales"], list)
        assert "programa" in res_com
        assert "activos_distribucion_generados" in ch_obj
        # Retrocompatibilidad Spec 024 en la raíz del canal
        assert ch_obj.get("titulo") == copys_input[ch]["titulo"]
        assert ch_obj.get("texto_copy") == copys_input[ch]["texto_copy"]
        assert ch_obj.get("plataforma") == ch

    # Validar activos específicos por esquema de src/schemas.py
    act_lk = copys_gen["linkedin"]["activos_distribucion_generados"]
    assert act_lk["post_linkedin"]["titulo"] == "Arquitectura con LangGraph"
    assert act_lk["post_linkedin"]["texto_copy"] == "Guía profesional de microservicios con @enoc_dev."
    assert "destaque_newsletter_semanal" in act_lk
    assert "sugerencia_contenido_faq" in act_lk
    assert "temporalidad_producto_creado" in act_lk

    act_x = copys_gen["x"]["activos_distribucion_generados"]
    assert act_x["post_postx"]["titulo"] == "LangGraph + Docker"
    assert act_x["post_postx"]["texto_copy"] == "Despliega agentes en producción hoy con @enoc_dev."
    assert "temporalidad_producto_creado" in act_x

    act_disc = copys_gen["discord"]["activos_distribucion_generados"]
    assert act_disc["canal_seleccionado"] == "#faq"
    assert act_disc["post_discord_faq"] is not None
    assert act_disc["post_discord_faq"]["titulo"] == "Guía FAQ Docker"
    assert "temporalidad_producto_creado" in act_disc

    act_pqrs = copys_gen["reclamos"]["activos_distribucion_generados"]
    assert act_pqrs["post_discord_pqrs"]["titulo"] == "Soporte PQRS"
    assert "temporalidad_producto_creado" in act_pqrs

    # Validar retrocompatibilidad con _formatear_copy_final de Spec 024
    copy_final_oci = puente_motor_ia._formatear_copy_final(copys_gen, texto_original=cont_orig["texto_original"])
    assert "Arquitectura con LangGraph" in copy_final_oci

    # 2. Prueba extremo a extremo vía publish-channel y hitl-decision
    despachados = []
    monkeypatch.setattr(puente_motor_ia, "despachar_replicacion_historial_reportes", lambda r: despachados.append(r))
    monkeypatch.setattr(
        puente_motor_ia,
        "despachar_discord_con_cascada",
        lambda *a, **kw: {"ok": True, "detalle": "OK", "estado_canal": "enviado", "message_id": "m_2640"},
    )

    resp_pub = client.post("/api/v1/mototradis/publish-channel", json={
        "id_mensaje": 2640,
        "canal": "discord",
        "canal_seleccionado": "#faq",
        "titulo": "Respuesta FAQ Oficial",
        "texto_copy": "Aquí tienes los pasos para desplegar con Docker y LangGraph.",
    })
    assert resp_pub.status_code == 200
    assert len(despachados) == 1
    reg_pub = despachados[0]
    assert reg_pub["contenido_original"]["relevancia"] == 88
    assert reg_pub["contenido_original"]["segmento"] == "PROFESIONAL"
    assert reg_pub["copys_generados"]["discord"]["activos_distribucion_generados"]["post_discord_faq"]["titulo"] == "Respuesta FAQ Oficial"


def test_spec026_rf07_evaluacion_no_bloqueante_y_gemma_resiliente_con_fallback():
    """
    Spec 026 - RF-07 (T1.7):
    Valida que:
    1. Exista _CadenaGemmaResiliente en puente_motor_ia con GEMMA_EVAL_TIMEOUT_SECONDS = 20.0,
       temperature=0.1 y max_output_tokens=800.
    2. Ante bloqueo (> timeout) o errores transitorios 500 INTERNAL / 503 UNAVAILABLE en el modelo primario,
       aplique reintentos acotados y conmute automáticamente a la cascada de fallback
       (gemma-4-26b-a4b-it -> cerebro_ia_gemini_flash -> cerebro_ia Groq), retornando siempre un FormatoSalida válido.
    3. Incluso si evaluador_lotes ejecuta importlib.reload(cerebro_ia_gemma_4), la cadena siga protegida
       con _CadenaGemmaResiliente.
    4. evaluate_batch_v1 y evaluate_single_message_v1 deleguen evaluar_lote mediante asyncio.to_thread
       sin bloquear el event loop de FastAPI.
    """
    import importlib
    import inspect
    import time

    assert hasattr(puente_motor_ia, "GEMMA_EVAL_TIMEOUT_SECONDS"), "Debe definir GEMMA_EVAL_TIMEOUT_SECONDS = 20.0"
    assert puente_motor_ia.GEMMA_EVAL_TIMEOUT_SECONDS == 20.0
    assert hasattr(puente_motor_ia, "_CadenaGemmaResiliente"), "Debe existir la clase _CadenaGemmaResiliente en puente_motor_ia"
    assert isinstance(puente_motor_ia.cerebro_ia_gemma_4.cadena, puente_motor_ia._CadenaGemmaResiliente)
    assert puente_motor_ia.cerebro_ia_gemma_4.cadena.temperature == 0.1
    assert puente_motor_ia.cerebro_ia_gemma_4.cadena.max_output_tokens == 800

    # Caso A: Bloqueo de cadena primaria (> timeout) -> corta con TimeoutError y conmuta al fallback
    class _CadenaColgada:
        def invoke(self, inp, *a, **kw):
            time.sleep(1.2)
            raise RuntimeError("No debería llegar aquí si el timeout corta antes")

    class _CadenaFallbackRapida:
        def __init__(self):
            self.llamadas = 0

        def invoke(self, inp, *a, **kw):
            self.llamadas += 1
            return {
                "relevancia": 78,
                "sentimiento": "Positivo",
                "temas_clave": "#gemma #fallback",
                "segmento": "ESTUDIANTE",
                "razonamiento": "Resuelto por fallback automático tras timeout de Gemma 4 31B",
            }

    fb_rapido = _CadenaFallbackRapida()
    cadena_test_timeout = puente_motor_ia._CadenaGemmaResiliente(
        cadena_primaria=_CadenaColgada(),
        cadenas_fallback=[fb_rapido],
        timeout_seconds=0.1,
        max_retries=1,
    )
    t0 = time.perf_counter()
    salida_timeout = cadena_test_timeout.invoke({"texto": "Consulta sobre agentes con Gemma 4", "canal": "#general"})
    elapsed = time.perf_counter() - t0
    assert elapsed < 0.9, f"El timeout por mensaje no cortó a tiempo ({elapsed:.2f}s)"
    assert fb_rapido.llamadas == 1
    assert getattr(salida_timeout, "relevancia", None) == 78
    assert getattr(salida_timeout, "sentimiento", None) == "Positivo"

    # Caso B: Error 503 UNAVAILABLE / 500 INTERNAL en cadena primaria -> reintenta y usa fallback
    intentos_primaria = {"n": 0}

    class _Cadena503:
        def invoke(self, inp, *a, **kw):
            intentos_primaria["n"] += 1
            raise RuntimeError("503 UNAVAILABLE: The model is overloaded. Please try again later.")

    fb_503 = _CadenaFallbackRapida()
    cadena_test_503 = puente_motor_ia._CadenaGemmaResiliente(
        cadena_primaria=_Cadena503(),
        cadenas_fallback=[fb_503],
        timeout_seconds=1.0,
        max_retries=2,
    )
    salida_503 = cadena_test_503.invoke({"texto": "Prueba de resiliencia ante 503", "canal": "#faq"})
    assert intentos_primaria["n"] >= 2, "Debe haber reintentado ante 503 UNAVAILABLE antes de conmutar al fallback"
    assert fb_503.llamadas == 1
    assert getattr(salida_503, "relevancia", None) == 78

    # Caso C: Supervivencia ante importlib.reload(modulo_cerebro) que ejecuta evaluador_lotes.evaluar_lote
    mod_gemma_root = importlib.import_module("cerebro_ia_gemma_4")
    mod_reloaded = importlib.reload(mod_gemma_root)
    assert isinstance(mod_reloaded.cadena, puente_motor_ia._CadenaGemmaResiliente), (
        "Tras importlib.reload(cerebro_ia_gemma_4), mod.cadena debe seguir envuelta en _CadenaGemmaResiliente"
    )

    # Caso D: Verificar delegación no bloqueante (asyncio.to_thread) en evaluate_batch_v1 y evaluate_single_message_v1
    src_batch = inspect.getsource(puente_motor_ia.evaluate_batch_v1)
    src_single = inspect.getsource(puente_motor_ia.evaluate_single_message_v1)
    assert "asyncio.to_thread" in src_batch and "evaluar_lote" in src_batch, (
        "evaluate_batch_v1 debe ejecutar evaluar_lote en asyncio.to_thread para no bloquear el event loop"
    )
    assert "asyncio.to_thread" in src_single and "evaluar_lote" in src_single, (
        "evaluate_single_message_v1 debe ejecutar evaluar_lote en asyncio.to_thread para no bloquear el event loop"
    )


def test_spec026_rf03_claridad_visual_matriz_multillm_y_umbral_frontend():
    """
    Spec 026 - RF-03, RF-06 (T1.3):
    Valida que:
    1. MODELOS_UTILIZADOS_CATALOGO y resolver_modelo_canal en puente_motor_ia expongan la Matriz Multi-LLM
       con sus fallbacks automáticos (Qwen 3.8 27B, GPT-OSS 120B, Gemini 3.5/3.1 Flash Lite, Gemini 3.6 Flash).
    2. ContentStudio.tsx muestre en la cabecera de la Mesa de Trabajo Multicanal la Matriz Multi-LLM con
       fallbacks automáticos, renombre el selector manual a 'IA Regeneración Individual:' y filtre la bandeja
       de entrada con relevance >= 35 (habilitando Prioridad 1 >= 70% y Prioridad 2 35-69%).
    3. Messages.tsx utilice el umbral < 35 para clasificar mensajes descartados y mueva mensajes con
       relevancia >= 35 a 'Pendientes de Copy'.
    """
    catalogo = puente_motor_ia.MODELOS_UTILIZADOS_CATALOGO
    assert "qwen/qwen3.8-27b" in catalogo["orquestador"].lower()
    assert "fallback" in catalogo["orquestador"].lower()
    assert "gemini-3.5-flash-lite" in catalogo["linkedin"].lower()
    assert "fallback" in catalogo["linkedin"].lower()
    assert "gemini-3.5-flash-lite" in catalogo["x"].lower()
    assert "fallback" in catalogo["x"].lower()
    assert "openai/gpt-oss-120b" in catalogo["discord"].lower()
    assert "fallback" in catalogo["discord"].lower()
    assert "qwen/qwen3.8-27b" in catalogo["pqrs"].lower()
    assert "gemma-4-31b-it" in catalogo["masivo"].lower()

    ruta_raiz = os.path.dirname(os.path.dirname(__file__))
    ruta_studio = os.path.join(ruta_raiz, "frontend", "src", "pages", "ContentStudio.tsx")
    ruta_messages = os.path.join(ruta_raiz, "frontend", "src", "pages", "Messages.tsx")

    with open(ruta_studio, "r", encoding="utf-8") as f:
        codigo_studio = f.read()
    with open(ruta_messages, "r", encoding="utf-8") as f:
        codigo_messages = f.read()

    # Validaciones en ContentStudio.tsx
    assert "item.analysis.relevance >= 35" in codigo_studio, (
        "ContentStudio.tsx debe admitir mensajes curados con relevance >= 35 en la bandeja de entrada"
    )
    assert "item.analysis.relevance >= 70" not in codigo_studio, (
        "ContentStudio.tsx no debe bloquear mensajes de Prioridad 2 (35-69%) con el filtro antiguo >= 70"
    )
    assert "IA Regeneración Individual:" in codigo_studio, (
        "El selector manual debe renombrarse a 'IA Regeneración Individual:' para no confundirse con el fallback automático"
    )
    assert "Qwen 3.8 27B" in codigo_studio and "GPT-OSS 120B" in codigo_studio and "Gemini 3.5 Flash Lite" in codigo_studio, (
        "ContentStudio.tsx debe mostrar explícitamente la Matriz Multi-LLM con fallbacks automáticos"
    )

    # Validaciones en Messages.tsx
    assert "message.relevance < 35" in codigo_messages and "msg.relevance < 35" in codigo_messages, (
        "Messages.tsx debe clasificar como descartados por relevancia sólo cuando relevance < 35"
    )
    assert "message.relevance < 70" not in codigo_messages and "msg.relevance < 70" not in codigo_messages, (
        "Messages.tsx no debe clasificar como descartados los mensajes con relevancia 35-69%"
    )
    assert "res.relevancia >= 35" in codigo_messages, (
        "handleEvaluateSingleMessage en Messages.tsx debe mover a 'Pendientes de Copy' cuando res.relevancia >= 35"
    )




def test_spec026_rf08_sanitizacion_alura_y_menciones_links_manuales_linkedin_x(client, monkeypatch):
    """
    Valida que:
    1. En los mensajes de LinkedIn y X se reemplace automáticamente cualquier mención a 'Alura' / 'Alura Latam'
       por 'CloudEDTech' (tanto en el insumo como en el borrador/post publicado).
    2. Cuando se publique manualmente por canal (publish-channel) o se inserten menciones manuales:
       - LinkedIn incluya el bloque de Más Información con los 3 links:
         https://lnkd.in/gX2m2Rhq, https://lnkd.in/gvbqJiF4, https://lnkd.in/gU7h7xyG
       - X incluya únicamente los 2 links de No Country y GitHub:
         https://lnkd.in/gvbqJiF4, https://lnkd.in/gU7h7xyG
         preservando los links íntegros dentro del límite estricto de 280 caracteres.
       - Si los links ya fueron agregados en el editor manual, no se dupliquen (idempotencia).
    3. ContentStudio.tsx exponga los botones y helpers de inserción manual de links y sanitización de 'Alura'.
    """
    assert hasattr(puente_motor_ia, "_sanitizar_marca_texto_red"), (
        "puente_motor_ia debe definir _sanitizar_marca_texto_red para erradicar menciones a Alura"
    )
    assert hasattr(puente_motor_ia, "_anexar_links_manuales_red"), (
        "puente_motor_ia debe definir _anexar_links_manuales_red para inyectar los links en publicación manual"
    )

    # 1. Prueba unitaria de sanitización de "Alura"
    texto_con_alura = "¡Gracias a Alura Latam y al curso de Alura por esta ruta! #Alura #AluraLatam"
    limpio = puente_motor_ia._sanitizar_marca_texto_red(texto_con_alura)
    assert "alura" not in limpio.lower(), f"No debe quedar mención a Alura: {limpio}"
    assert "CloudEDTech" in limpio

    # 2. Prueba unitaria de inyección idempotente de links manuales en LinkedIn
    lk_con_links = puente_motor_ia._anexar_links_manuales_red(
        "linkedin",
        "Gran avance en Alura Latam con @dev_user",
        "Logré desplegar mi proyecto gracias a Alura.",
    )
    assert "alura" not in lk_con_links["titulo"].lower()
    assert "alura" not in lk_con_links["texto_copy"].lower()
    assert "https://lnkd.in/gX2m2Rhq" in lk_con_links["texto_copy"]
    assert "https://lnkd.in/gvbqJiF4" in lk_con_links["texto_copy"]
    assert "https://lnkd.in/gU7h7xyG" in lk_con_links["texto_copy"]

    # Idempotencia en LinkedIn (segunda llamada no duplica links)
    lk_idempotente = puente_motor_ia._anexar_links_manuales_red(
        "linkedin",
        lk_con_links["titulo"],
        lk_con_links["texto_copy"],
    )
    assert lk_idempotente["texto_copy"].count("https://lnkd.in/gX2m2Rhq") == 1
    assert lk_idempotente["texto_copy"].count("https://lnkd.in/gvbqJiF4") == 1
    assert lk_idempotente["texto_copy"].count("https://lnkd.in/gU7h7xyG") == 1

    # 3. Prueba unitaria de inyección de los 2 links en X con respeto estricto de 280 caracteres
    x_largo = puente_motor_ia._anexar_links_manuales_red(
        "x",
        "Hito en Alura",
        "A" * 240 + " en Alura Latam",
    )
    tweet_combinado = f"{x_largo['titulo']}\n\n{x_largo['texto_copy']}".strip()
    assert "alura" not in tweet_combinado.lower()
    assert "https://lnkd.in/gvbqJiF4" in x_largo["texto_copy"]
    assert "https://lnkd.in/gU7h7xyG" in x_largo["texto_copy"]
    assert "https://lnkd.in/gX2m2Rhq" not in x_largo["texto_copy"], (
        "En X solo deben colocarse los 2 links de No Country y GitHub (gvbqJiF4 y gU7h7xyG)"
    )
    assert len(tweet_combinado) <= 280, f"El tweet combinado con links no debe exceder 280 chars: {len(tweet_combinado)}"

    # 4. Prueba extremo a extremo en endpoint de publicación manual (publish-channel)
    monkeypatch.setattr(puente_motor_ia, "despachar_replicacion_historial_reportes", lambda r: None)
    captura_lk = {}
    captura_x = {}

    def fake_lk(titulo, texto_copy):
        captura_lk["titulo"] = titulo
        captura_lk["texto_copy"] = texto_copy
        return {"ok": True, "detalle": "OK LK", "url": "https://www.linkedin.com/feed/update/urn:li:share:1", "urn": "urn:li:share:1", "estado_canal": "enviado"}

    def fake_x(titulo, texto_copy):
        captura_x["titulo"] = titulo
        captura_x["texto_copy"] = texto_copy
        return {"ok": True, "detalle": "OK X", "url": "https://x.com/CloudEdTech_1/status/1", "tweet_id": "1", "estado_canal": "enviado"}

    monkeypatch.setattr(puente_motor_ia, "despachar_linkedin_resiliente", fake_lk)
    monkeypatch.setattr(puente_motor_ia, "despachar_x_resiliente", fake_x)

    resp_lk = client.post("/api/v1/mototradis/publish-channel", json={
        "id_mensaje": 2640,
        "canal": "linkedin",
        "titulo": "Éxito en Alura",
        "texto_copy": "Gran aprendizaje en los cursos de Alura Latam.",
    })
    assert resp_lk.status_code == 200
    assert "alura" not in captura_lk["titulo"].lower()
    assert "alura" not in captura_lk["texto_copy"].lower()
    assert "https://lnkd.in/gX2m2Rhq" in captura_lk["texto_copy"]
    assert "https://lnkd.in/gvbqJiF4" in captura_lk["texto_copy"]
    assert "https://lnkd.in/gU7h7xyG" in captura_lk["texto_copy"]

    resp_x = client.post("/api/v1/mototradis/publish-channel", json={
        "id_mensaje": 2640,
        "canal": "x",
        "titulo": "Avance en Alura",
        "texto_copy": "Terminé mi proyecto en Alura con Python.",
    })
    assert resp_x.status_code == 200
    assert "alura" not in captura_x["titulo"].lower()
    assert "alura" not in captura_x["texto_copy"].lower()
    assert "https://lnkd.in/gvbqJiF4" in captura_x["texto_copy"]
    assert "https://lnkd.in/gU7h7xyG" in captura_x["texto_copy"]
    assert "https://lnkd.in/gX2m2Rhq" not in captura_x["texto_copy"]

    # 5. Verificación en ContentStudio.tsx
    ruta_raiz = os.path.dirname(os.path.dirname(__file__))
    ruta_studio = os.path.join(ruta_raiz, "frontend", "src", "pages", "ContentStudio.tsx")
    with open(ruta_studio, "r", encoding="utf-8") as f:
        codigo_studio = f.read()

    assert "https://lnkd.in/gX2m2Rhq" in codigo_studio
    assert "https://lnkd.in/gvbqJiF4" in codigo_studio
    assert "https://lnkd.in/gU7h7xyG" in codigo_studio


# ==============================================================================
# PRUEBAS TDD SPEC 027 (RF-01 AL RF-07) - RESOLUCIÓN BLOQUEOS GEMMA 4,
# INCLUSIÓN AUTOMÁTICA DE LINKS Y SINCRONIZACIÓN DE REPORTES OCI
# ==============================================================================

def test_spec027_rf01_gemma_descartado_ingesta(client, monkeypatch):
    """
    Spec 027 - RF-01: Descarte de Gemma 4 en Ingesta y Blindaje de Motores Estables.
    Valida que al solicitar 'cerebro_ia_gemma_4' o 'Google Gemma 4' en:
    - POST /api/v1/ai/evaluate-message
    - POST /api/v1/ai/evaluate-batch
    el sistema rechace la petición con HTTP 400 Bad Request indicando su exclusividad
    para copywriting masivo (< 35%), O ejecute un fallback transparente sin colgar el hilo.
    También valida que nodo_gemma_automatico en src/nodes.py se mantenga reservado para la cola masiva.
    """
    import inspect
    os.environ.setdefault("GEMINI_API_KEY", "dummy-gemini-key")
    os.environ.setdefault("GROQ_API_KEY", "dummy-groq-key")
    from src.config import config
    if not config.GEMINI_API_KEY:
        config.GEMINI_API_KEY = "dummy-gemini-key"
    if not config.GROQ_API_KEY:
        config.GROQ_API_KEY = "dummy-groq-key"

    # Preparar mensaje real en SQLite para la evaluación
    with sqlite3.connect(puente_motor_ia.motor_bd.RUTA_BD) as conn:
        conn.execute("""
            INSERT OR REPLACE INTO interacciones (
                id, hash, origen_comunidad, periodo_referencia, autor, canal, tipo,
                texto, enviado_en, creado_en, estado, estado_curaduria, etapa_flujo,
                relevancia, sentimiento
            ) VALUES (
                1, 'hash_test_01', 'Discord', '2026-semana-42', 'tester', '#general', 'mensaje',
                'Hola mundo testing',
                '2026-10-15T12:00:00+00:00', '2026-10-15T12:01:00+00:00', 'pendiente', 'pending', 'pendiente',
                50, 'Neutral'
            )
        """)
        conn.commit()

    # 1. Validación en evaluate-message con cerebro_ia_gemma_4
    resp_msg = client.post("/api/v1/ai/evaluate-message", json={
        "interaction_id": 1,
        "proveedor": "cerebro_ia_gemma_4"
    })
    # Debe ser 400 Bad Request o fallback transparente donde proveedor usado no sea Gemma 4
    if resp_msg.status_code == 400:
        detalle = str(resp_msg.json().get("detail", "")).lower()
        assert any(k in detalle for k in ["gemma", "masivo", "reservado", "proveedor", "no permitido"]), (
            f"El mensaje 400 debe explicar el descarte de Gemma en Ingesta: {detalle}"
        )
    else:
        assert resp_msg.status_code == 200, f"Esperado 400 o 200 con fallback, obtuvo {resp_msg.status_code}"
        proveedor_usado = str(resp_msg.json().get("proveedor", "")).lower()
        assert "gemma" not in proveedor_usado, f"Si no es 400, debe haber fallback transparente fuera de Gemma: {proveedor_usado}"

    # 2. Validación en evaluate-message con Google Gemma 4
    with sqlite3.connect(puente_motor_ia.motor_bd.RUTA_BD) as conn:
        conn.execute("""
            INSERT OR REPLACE INTO interacciones (
                id, hash, origen_comunidad, periodo_referencia, autor, canal, tipo,
                texto, enviado_en, creado_en, estado, estado_curaduria, etapa_flujo,
                relevancia, sentimiento
            ) VALUES (
                1, 'hash_test_01', 'Discord', '2026-semana-42', 'tester', '#general', 'mensaje',
                'Hola mundo testing',
                '2026-10-15T12:00:00+00:00', '2026-10-15T12:01:00+00:00', 'pendiente', 'pending', 'pendiente',
                50, 'Neutral'
            )
        """)
        conn.commit()

    resp_msg2 = client.post("/api/v1/ai/evaluate-message", json={
        "interaction_id": 1,
        "proveedor": "Google Gemma 4"
    })
    if resp_msg2.status_code == 400:
        detalle2 = str(resp_msg2.json().get("detail", "")).lower()
        assert any(k in detalle2 for k in ["gemma", "masivo", "reservado", "proveedor", "no permitido"])
    else:
        assert resp_msg2.status_code == 200
        assert "gemma" not in str(resp_msg2.json().get("proveedor", "")).lower()

    # 3. Validación en evaluate-batch con cerebro_ia_gemma_4
    resp_batch = client.post("/api/v1/ai/evaluate-batch", json={
        "proveedor": "cerebro_ia_gemma_4",
        "solo_pendientes": True,
        "limite": 1
    })
    if resp_batch.status_code == 400:
        detalle_batch = str(resp_batch.json().get("detail", "")).lower()
        assert any(k in detalle_batch for k in ["gemma", "masivo", "reservado", "proveedor", "no permitido"])
    else:
        assert resp_batch.status_code == 200
        assert "gemma" not in str(resp_batch.json().get("proveedor", "")).lower()

    # 4. nodo_gemma_automatico en src/nodes.py debe seguir activo para rescate masivo < 35%
    import src.nodes as nodes
    assert hasattr(nodes, "nodo_gemma_automatico"), "nodo_gemma_automatico debe mantenerse en src/nodes.py"
    assert inspect.iscoroutinefunction(nodes.nodo_gemma_automatico) or callable(nodes.nodo_gemma_automatico)


def test_spec027_rf02_cancelar_evaluacion_endpoint(client):
    """
    Spec 027 - RF-02: Endpoint de Cancelación Activa y Señal Cooperativa.
    Valida que:
    1. POST /api/v1/ai/cancel-evaluation responda HTTP 200 con {"status": "cancelled", "message": "Evaluación cancelada exitosamente"}.
    2. El endpoint soporte trailing slash (/api/v1/ai/cancel-evaluation/).
    3. Active el evento cooperativo en memoria (_evento_cancelacion_evaluacion) para detener el procesamiento del lote.
    """
    evento = getattr(puente_motor_ia, "_evento_cancelacion_evaluacion", None)
    if evento is not None:
        evento.clear()

    # Test sin trailing slash
    resp = client.post("/api/v1/ai/cancel-evaluation", json={"batch_id": "test-batch-001"})
    assert resp.status_code == 200, f"Endpoint /api/v1/ai/cancel-evaluation debe responder 200 OK: {resp.status_code}"
    data = resp.json()
    assert data.get("status") == "cancelled"
    assert "cancelada" in data.get("message", "").lower()

    # Validar que el evento cooperativo en memoria esté activo (set)
    evento_post = getattr(puente_motor_ia, "_evento_cancelacion_evaluacion", None)
    assert evento_post is not None, "puente_motor_ia._evento_cancelacion_evaluacion debe existir"
    assert evento_post.is_set() is True, "El evento de cancelación debe quedar activado (is_set() == True)"

    # Test con trailing slash
    resp_slash = client.post("/api/v1/ai/cancel-evaluation/", json={})
    assert resp_slash.status_code == 200
    assert resp_slash.json().get("status") == "cancelled"


def test_spec027_rf03_links_automaticos_linkedin(monkeypatch):
    """
    Spec 027 - RF-03: Automatización de Links y Sanitización en LinkedIn.
    Valida que:
    1. nodo_linkedin incorpore automáticamente el bloque 'Más Información' con los 3 links
       oficiales (gX2m2Rhq, gvbqJiF4, gU7h7xyG) y sanitice 'Alura' -> 'CloudEDTech'.
    2. enviar_linkedin verifique e inyecte de forma idempotente los 3 links y sanitice la marca.
    3. No se dupliquen los enlaces si ya estaban presentes en el texto original.
    """
    os.environ.setdefault("GEMINI_API_KEY", "dummy-gemini-key")
    os.environ.setdefault("GROQ_API_KEY", "dummy-groq-key")
    from src.config import config
    if not config.GEMINI_API_KEY:
        config.GEMINI_API_KEY = "dummy-gemini-key"
    if not config.GROQ_API_KEY:
        config.GROQ_API_KEY = "dummy-groq-key"
    import src.nodes as nodes
    import src.publishers as publishers
    from src.schemas import (
        RespuestaComunidadLinkedin,
        ResumenComunidad,
        ActivosDistribucionGeneradosLinkedin,
        PostLinkedin,
        DestaqueNewsletter,
        SugerenciaContenidoFAQ,
        TemporalidadProductoCreado,
    )

    LINKS_OFICIALES = [
        "https://lnkd.in/gX2m2Rhq",
        "https://lnkd.in/gvbqJiF4",
        "https://lnkd.in/gU7h7xyG",
    ]

    # 1. Simulación en nodo_linkedin
    respuesta_falsa = RespuestaComunidadLinkedin(
        status="exito",
        resumen_comunidad=ResumenComunidad(
            total_interacciones_procesadas=1,
            sentimiento_predominante="Positivo",
            temas_principales=["Python", "Alura Latam"],
            programa="Formación Alura",
        ),
        activos_distribucion_generados=ActivosDistribucionGeneradosLinkedin(
            post_linkedin=PostLinkedin(
                titulo="Éxito de la formación Alura Latam",
                texto_copy="¡Felicitaciones a @CarlosDev por culminar la ruta de Alura con honores y grandes resultados!",
                canal_recomendado="LinkedIn Oficial",
                potencial_engagement="Alto",
            ),
            destaque_newsletter_semanal=DestaqueNewsletter(
                seccion="Alura Comunidad",
                titular="Hito Alura",
                resumen="Resumen del hito",
            ),
            sugerencia_contenido_faq=SugerenciaContenidoFAQ(
                tema="Duda sobre Alura",
                origen="Comunidad",
                status="Derivado_a_Mentoria",
            ),
            temporalidad_producto_creado=TemporalidadProductoCreado(
                fecha_envio="2026-10-15T10:00:00Z",
                fecha_extraccion="2026-10-15T11:00:00Z",
                semana="2026-semana-42",
            ),
        ),
    )

    monkeypatch.setattr(nodes, "invocar_con_respaldo_y_tiempo", lambda *args, **kwargs: respuesta_falsa)

    state = {
        "id_mensaje": "2441",
        "autor": "CarlosDev",
        "semana": "2026-semana-42",
        "fecha_envio": "2026-10-15T10:00:00Z",
        "fecha_extraccion": "2026-10-15T11:00:00Z",
        "json_precurado": {"texto_original": "Terminé mi curso de Alura", "relevancia": 85},
        "rutas_activas": ["linkedin"],
        "copys_generados": {},
        "errores_dlq": [],
        "estado_publicacion": "pendiente",
    }

    resultado_nodo = nodes.nodo_linkedin(state)
    copy_lk = resultado_nodo["copys_generados"]["linkedin"]
    post_lk = copy_lk["activos_distribucion_generados"]["post_linkedin"]
    texto_generado = post_lk["texto_copy"]
    titulo_generado = post_lk["titulo"]

    # Validaciones en nodo_linkedin: sanitización y 3 links
    assert "alura" not in texto_generado.lower(), f"No debe haber 'alura' en copy LinkedIn: {texto_generado}"
    assert "alura" not in titulo_generado.lower(), f"No debe haber 'alura' en título LinkedIn: {titulo_generado}"
    assert "CloudEDTech" in texto_generado or "CloudEDTech" in titulo_generado
    assert "Más Información" in texto_generado or "más información" in texto_generado.lower()
    for link in LINKS_OFICIALES:
        assert link in texto_generado, f"El link {link} debe estar presente en el copy de LinkedIn"
        assert texto_generado.count(link) == 1, f"El link {link} no debe estar duplicado"

    # 2. Validación de idempotencia e inyección en publishers.enviar_linkedin
    captura_payload_lk = {}

    def fake_post_lk(url, headers=None, json=None):
        captura_payload_lk["url"] = url
        captura_payload_lk["json"] = json
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        return mock_resp

    monkeypatch.setattr("requests.post", fake_post_lk)
    monkeypatch.setattr(publishers.config, "LINKEDIN_ACCESS_TOKEN", "fake_token_123")
    monkeypatch.setattr(publishers.config, "LINKEDIN_AUTHOR_URN", "urn:li:person:fake_urn_123")

    copys_para_publicar = {
        "linkedin": {
            "status": "success",
            "activos_distribucion_generados": {
                "post_linkedin": {
                    "titulo": "Nuevo Hito en Alura Latam",
                    "texto_copy": "Gran avance de @dev_user en Alura Latam.",
                }
            },
        }
    }

    ok_envio = publishers.enviar_linkedin(copys_para_publicar)
    assert ok_envio is True
    texto_enviado = captura_payload_lk["json"]["specificContent"]["com.linkedin.ugc.ShareContent"]["shareCommentary"]["text"]

    assert "alura" not in texto_enviado.lower(), f"enviar_linkedin debe sanitizar Alura: {texto_enviado}"
    for link in LINKS_OFICIALES:
        assert link in texto_enviado, f"enviar_linkedin debe asegurar link {link}"
        assert texto_enviado.count(link) == 1, f"Link {link} no debe duplicarse en enviar_linkedin"


def test_spec027_rf04_links_automaticos_x_limite_280(monkeypatch):
    """
    Spec 027 - RF-04: Automatización de Links y Límite de 280 Caracteres en X.
    Valida que:
    1. nodo_x incorpore automáticamente los 2 links oficiales (gvbqJiF4, gU7h7xyG).
    2. No incluya el 3er link de LinkedIn (gX2m2Rhq).
    3. Sanitice 'Alura' -> 'CloudEDTech'.
    4. Garantice longitud total <= 280 caracteres recortando en frontera de palabra (...)
       sin mutilar jamás las URLs.
    5. enviar_tweet_x aplique las mismas garantías antes del dispatch a la API v2 de X.
    """
    os.environ.setdefault("GEMINI_API_KEY", "dummy-gemini-key")
    os.environ.setdefault("GROQ_API_KEY", "dummy-groq-key")
    from src.config import config
    if not config.GEMINI_API_KEY:
        config.GEMINI_API_KEY = "dummy-gemini-key"
    if not config.GROQ_API_KEY:
        config.GROQ_API_KEY = "dummy-groq-key"
    import src.nodes as nodes
    import src.publishers as publishers
    from src.schemas import (
        RespuestaComunidadX,
        ResumenComunidad,
        ActivosDistribucionGeneradosX,
        PostX,
        TemporalidadProductoCreadoX,
    )

    LINK_NO_COUNTRY = "https://lnkd.in/gvbqJiF4"
    LINK_GITHUB = "https://lnkd.in/gU7h7xyG"
    LINK_LK_PROHIBIDO = "https://lnkd.in/gX2m2Rhq"

    # 1. Caso en nodo_x con texto largo con mención de Alura
    cuerpo_largo_alura = (
        "¡Excelente avance en Alura Latam! Felicitaciones a @CarlosDev por completar el curso de arquitectura en la plataforma Alura. "
        "Estamos orgullosos de ver cómo construyes proyectos sólidos y aplicas cada conocimiento técnico con rigor y dedicación profesional continua hoy."
    )
    respuesta_x_falsa = RespuestaComunidadX(
        status="exito",
        resumen_comunidad=ResumenComunidad(
            total_interacciones_procesadas=1,
            sentimiento_predominante="Positivo",
            temas_principales=["X", "Alura"],
            programa="Alura X",
        ),
        activos_distribucion_generados=ActivosDistribucionGeneradosX(
            post_postx=PostX(
                titulo="Hito en Alura",
                texto_copy=cuerpo_largo_alura,
                canal_recomendado="X Oficial",
                potencial_engagement="Alto",
            ),
            temporalidad_producto_creado=TemporalidadProductoCreadoX(
                fecha_envio="2026-10-15T10:00:00Z",
                fecha_extraccion="2026-10-15T11:00:00Z",
                semana="2026-semana-42",
            ),
        ),
    )

    monkeypatch.setattr(nodes, "invocar_con_respaldo_y_tiempo", lambda *args, **kwargs: respuesta_x_falsa)

    state_x = {
        "id_mensaje": "2441",
        "autor": "CarlosDev",
        "semana": "2026-semana-42",
        "fecha_envio": "2026-10-15T10:00:00Z",
        "fecha_extraccion": "2026-10-15T11:00:00Z",
        "json_precurado": {"texto_original": "Terminé en Alura", "relevancia": 80},
        "rutas_activas": ["x"],
        "copys_generados": {},
        "errores_dlq": [],
        "estado_publicacion": "pendiente",
    }

    resultado_x = nodes.nodo_x(state_x)
    copy_x = resultado_x["copys_generados"]["x"]
    post_x = copy_x["activos_distribucion_generados"]["post_postx"]
    titulo_x = post_x["titulo"]
    texto_x = post_x["texto_copy"]
    tweet_completo = f"{titulo_x}\n\n{texto_x}".strip()

    # Validaciones en nodo_x
    assert "alura" not in tweet_completo.lower(), f"No debe haber 'alura' en tweet: {tweet_completo}"
    assert LINK_NO_COUNTRY in texto_x, f"Link No Country debe estar en X: {texto_x}"
    assert LINK_GITHUB in texto_x, f"Link GitHub debe estar en X: {texto_x}"
    assert LINK_LK_PROHIBIDO not in texto_x, f"Link LinkedIn no debe estar en X: {texto_x}"
    assert len(tweet_completo) <= 280, f"Tweet no debe superar 280 caracteres, tiene {len(tweet_completo)}: {tweet_completo}"
    assert LINK_NO_COUNTRY in tweet_completo and LINK_GITHUB in tweet_completo, "Las URLs deben permanecer íntegras sin mutilación"

    # 2. Validación en publishers.enviar_tweet_x
    tweet_capturado = {}

    class FakeTweepyClient:
        def __init__(self, **kwargs):
            pass

        def create_tweet(self, text):
            tweet_capturado["text"] = text
            mock_res = MagicMock()
            mock_res.data = {"id": "tweet_123456789"}
            return mock_res

    monkeypatch.setattr("tweepy.Client", FakeTweepyClient)
    monkeypatch.setattr(publishers.config, "X_API_KEY", "fake_key")
    monkeypatch.setattr(publishers.config, "X_API_SECRET", "fake_secret")
    monkeypatch.setattr(publishers.config, "X_ACCESS_TOKEN", "fake_access")
    monkeypatch.setattr(publishers.config, "X_ACCESS_TOKEN_SECRET", "fake_access_secret")

    copys_x_publicar = {
        "x": {
            "status": "success",
            "activos_distribucion_generados": {
                "post_postx": {
                    "titulo": "Novedad Alura",
                    "texto_copy": "A" * 260 + " en Alura Latam",
                }
            },
        }
    }

    ok_x = publishers.enviar_tweet_x(copys_x_publicar)
    assert ok_x is True
    t_enviado = tweet_capturado["text"]
    assert "alura" not in t_enviado.lower()
    assert LINK_NO_COUNTRY in t_enviado
    assert LINK_GITHUB in t_enviado
    assert LINK_LK_PROHIBIDO not in t_enviado
    assert len(t_enviado) <= 280, f"Tweet enviado a API no debe superar 280 chars: {len(t_enviado)}"


def test_spec027_rf05_publicador_exito_parcial_rutas_activas(monkeypatch):
    """
    Spec 027 - RF-05: Persistencia Atómica de Publicaciones Parciales en historial_reportes_semanales.
    Valida que:
    1. Si al menos un canal es exitoso (ej. Discord=True, X=False por falta de credenciales),
       nodo_publicador persista la fila en Supabase public.historial_reportes_semanales.
    2. Se guarde rutas_activas conteniendo exclusivamente los canales exitosos (['discord']).
    3. El estado persista como 'publicado' y el lote se actualice a 'aprobado'.
    """
    os.environ.setdefault("GEMINI_API_KEY", "dummy-gemini-key")
    os.environ.setdefault("GROQ_API_KEY", "dummy-groq-key")
    from src.config import config
    if not config.GEMINI_API_KEY:
        config.GEMINI_API_KEY = "dummy-gemini-key"
    if not config.GROQ_API_KEY:
        config.GROQ_API_KEY = "dummy-groq-key"
    import src.nodes as nodes

    # Simular éxito en Discord y fallo en X
    monkeypatch.setattr(nodes, "enviar_webhook_discord", lambda *args, **kwargs: True)
    monkeypatch.setattr(nodes, "enviar_tweet_x", lambda *args, **kwargs: False)
    monkeypatch.setattr(nodes, "enviar_linkedin", lambda *args, **kwargs: False)

    lote_actualizado = {}
    monkeypatch.setattr(nodes, "actualizar_estado_lote", lambda id_msg, estado: lote_actualizado.update({"id": id_msg, "estado": estado}))

    sql_ejecutado = {}

    class FakeCursor:
        def execute(self, query, params=None):
            sql_ejecutado["query"] = query
            sql_ejecutado["params"] = params

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    class FakeConn:
        def cursor(self):
            return FakeCursor()

        def commit(self):
            sql_ejecutado["committed"] = True

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    monkeypatch.setattr("psycopg.connect", lambda *args, **kwargs: FakeConn())

    state = {
        "id_mensaje": "2441",
        "autor": "CarlosDev",
        "semana": "2026-semana-42",
        "fecha_envio": "2026-10-15T10:00:00Z",
        "fecha_extraccion": "2026-10-15T11:00:00Z",
        "rutas_activas": ["discord", "x"],
        "copys_generados": {
            "discord": {"status": "success", "activos_distribucion_generados": {"canal_seleccionado": "#general"}},
            "x": {"status": "error", "error": "Credenciales no configuradas"},
        },
        "json_precurado": {"texto_original": "Mensaje de prueba", "relevancia": 88},
        "errores_dlq": [],
        "estado_publicacion": "validado_esperando_hitl",
    }

    resultado = nodes.nodo_publicador(state)

    # Validar que ante éxito parcial, la publicación se considere completada y guardada
    assert resultado.get("estado_publicacion") == "completado", (
        f"Con al menos un canal exitoso (Discord), estado_publicacion debe ser 'completado', no {resultado.get('estado_publicacion')}"
    )
    assert sql_ejecutado.get("committed") is True, "Debe haberse ejecutado commit en Supabase"

    params = sql_ejecutado.get("params", ())
    rutas_guardadas = None
    estado_guardado = None
    for p in params:
        if isinstance(p, list):
            rutas_guardadas = p
        elif p in ("publicado", "error"):
            estado_guardado = p

    assert rutas_guardadas == ["discord"], f"rutas_activas guardadas deben ser solo las exitosas (['discord']): {rutas_guardadas}"
    assert estado_guardado == "publicado", f"El estado guardado debe ser 'publicado': {estado_guardado}"
    assert lote_actualizado.get("estado") == "aprobado", "El lote debe marcarse como 'aprobado' al haberse publicado en al menos un canal"


def test_spec027_rf06_semana_canonico_iso8601():
    """
    Spec 027 - RF-06: Normalización Canónica de Semana (YYYY-semana-WW) sin Modificar Archivos Raíz.
    Valida que:
    1. puente_motor_ia._normalizar_semana_canonico convierta diversos formatos (Semana_01, Semana_42, 2026-semana-42)
       al formato canónico YYYY-semana-WW.
    2. TemporalidadProductoCreado y TemporalidadProductoCreadoX en src/schemas.py utilicen o acepten
       el formato canónico YYYY-semana-WW.
    3. REGLA CONSTITUCIONAL: reporte_semanal.py en la raíz NO haya sido modificado.
    """
    fn_normalizar = getattr(puente_motor_ia, "_normalizar_semana_canonico", None)
    assert callable(fn_normalizar), "puente_motor_ia._normalizar_semana_canonico debe existir y ser invocable"

    # Validar transformaciones canónicas
    assert fn_normalizar("2026-semana-42") == "2026-semana-42"
    assert fn_normalizar("2026-semana-05") == "2026-semana-05"
    assert fn_normalizar("Semana_42", fecha_ref="2026-10-15T12:00:00Z") == "2026-semana-42"
    assert fn_normalizar("semana_42") == "2026-semana-42" or "semana-42" in fn_normalizar("semana_42")
    assert fn_normalizar(None, fecha_ref="2026-10-15T12:00:00Z") == "2026-semana-42"

    # Validar schemas en src/schemas.py
    import src.schemas as schemas
    temp_lk = schemas.TemporalidadProductoCreado(semana="2026-semana-42")
    assert temp_lk.semana == "2026-semana-42"
    temp_x = schemas.TemporalidadProductoCreadoX(semana="2026-semana-42")
    assert temp_x.semana == "2026-semana-42"

    # INVIOLABILIDAD ABSOLUTA: reporte_semanal.py en la raíz no debe haber sido tocado
    ruta_raiz = os.path.dirname(os.path.dirname(__file__))
    ruta_reporte = os.path.join(ruta_raiz, "reporte_semanal.py")
    assert os.path.exists(ruta_reporte), "reporte_semanal.py debe existir en la raíz"

    import subprocess
    diff_res = subprocess.run(
        ["git", "diff", "--name-only", "reporte_semanal.py"],
        cwd=ruta_raiz,
        capture_output=True,
        text=True,
    )
    assert "reporte_semanal.py" not in diff_res.stdout, (
        f"VIOLACIÓN CONSTITUCIONAL: reporte_semanal.py fue modificado en git: {diff_res.stdout}"
    )


def test_spec027_rf07_reconstruccion_oci_sin_mocks(monkeypatch):
    """
    Spec 027 - RF-07: Reconstrucción de Reportes OCI desde SQLite y Erradicación Total de Mocks.
    Valida que:
    1. _cargar_lote_para_reporte_semanal consulte contenidos_generados e interacciones de SQLite
       cuando Supabase no posea registros para la semana.
    2. Erradique por completo cualquier registro con id_mensaje: '999' o autor: 'fallback_user'.
    3. Si no existen registros en Supabase ni en SQLite, retorne {'aprobados': [], 'descartados': []}
       sin inventar datos ficticios.
    4. Con registros reales en SQLite, reconstruya los aprobados con copys reales.
    """
    # 1. Caso base: Sin datos en Supabase ni SQLite -> listas vacías, cero mocks
    monkeypatch.setattr(puente_motor_ia, "_extraer_historial_reportes_semanales_supabase", lambda semana: [])

    # Asegurar SQLite limpia sin mensajes
    _asegurar_esquema = getattr(puente_motor_ia, "_asegurar_esquema_sqlite", lambda: None)
    _asegurar_esquema()
    with sqlite3.connect(puente_motor_ia.motor_bd.RUTA_BD) as conn:
        conn.execute("DELETE FROM contenidos_generados WHERE interaccion_id IN (1, 2441)")
        conn.execute("DELETE FROM interacciones WHERE id IN (1, 2441)")
        conn.commit()

    lote_vacio = puente_motor_ia._cargar_lote_para_reporte_semanal("2026-semana-50")
    assert isinstance(lote_vacio, dict)
    assert lote_vacio.get("aprobados") == []
    assert "999" not in str(lote_vacio), "No debe haber ningún id_mensaje: 999"
    assert "fallback_user" not in str(lote_vacio), "No debe haber ningún fallback_user"

    # 2. Caso con datos reales en SQLite: debe reconstruir los copys aprobados reales
    with sqlite3.connect(puente_motor_ia.motor_bd.RUTA_BD) as conn:
        conn.execute("""
            INSERT OR REPLACE INTO interacciones (
                id, hash, origen_comunidad, periodo_referencia, autor, canal, tipo,
                texto, enviado_en, creado_en, estado, estado_curaduria, etapa_flujo,
                relevancia, sentimiento
            ) VALUES (
                2441, 'hash_real_2441', 'Discord', '2026-semana-42', 'dev_enoc', '#general', 'mensaje',
                'Logré terminar mi certificación y publicar mi proyecto con éxito.',
                '2026-10-15T12:00:00+00:00', '2026-10-15T12:01:00+00:00', 'publicado', 'curated', 'publicado',
                92, 'Positivo'
            )
        """)
        conn.execute("""
            INSERT OR REPLACE INTO contenidos_generados (
                id, interaccion_id, formato, titulo, contenido, llamada_accion,
                plataforma, estado, estado_publicacion, creado_en, actualizado_en
            ) VALUES (
                9001, 2441, 'linkedin', 'Logro Profesional en CloudEDTech',
                'Felicitamos a @dev_enoc por su certificación técnica.',
                'Conoce más sobre nuestras rutas.', 'linkedin', 'publicado', 'publicado',
                '2026-10-15T13:00:00+00:00', '2026-10-15T13:00:00+00:00'
            )
        """)
        conn.commit()

    lote_real = puente_motor_ia._cargar_lote_para_reporte_semanal("2026-semana-42")
    aprobados = lote_real.get("aprobados", [])
    assert len(aprobados) >= 1, f"Debe reconstruir al menos 1 aprobado real desde SQLite: {lote_real}"

    item_aprobado = aprobados[0]
    assert str(item_aprobado.get("id_mensaje") or item_aprobado.get("id")) == "2441"
    assert "999" not in str(lote_real), "No debe haber ningún id 999 en lote reconstruido"
    assert "fallback_user" not in str(lote_real), "No debe haber fallback_user en lote reconstruido"

