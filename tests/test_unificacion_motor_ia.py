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
