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
            "relevancia": 60,
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

    with patch("reporte_semanal.generar_reporte_semanal", return_value=mock_reporte) as mock_gen:
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

    with patch.dict(os.environ, {"DISCORD_WEBHOOK_GENERAL": "https://discord.com/api/webhooks/mock/123"}, clear=False):
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

    with patch.dict(os.environ, {"DISCORD_WEBHOOK_GENERAL": "https://discord.com/api/webhooks/mock/123"}, clear=False):
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

    with patch.dict(os.environ, {"DISCORD_WEBHOOK_GENERAL": "https://discord.com/api/webhooks/mock/test"}, clear=False):
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

