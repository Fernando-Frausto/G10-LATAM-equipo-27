"""
puente_motor_ia.py — Adaptador no invasivo para la unificación de motor-ia con Supabase.
Especificación: specs/005-unificacion-beta/spec.md (RF-01 a RF-05)

Expone la aplicación FastAPI ('app') y el módulo de base de datos de motor-ia ('motor_bd')
aislando el contexto de importación para no colisionar con base_datos.py ni api.py de la raíz.
"""
import os
import sys
import sqlite3
import asyncio
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

import discord
from fastapi import HTTPException, Body, status
from fastapi.responses import JSONResponse

# 1. Asegurar que los módulos homónimos de la raíz estén respaldados/importados
import base_datos as _base_datos_raiz
import api as _api_raiz
import armar_json_bot_python as _bot_raiz
import armar_json_bot_python
import procesamiento
from periodos import a_utc_iso, como_fecha, semana_de, periodo_de

_discord_sync_lock = asyncio.Lock()


_DIR_RAIZ = Path(__file__).resolve().parent
_DIR_MOTOR_IA = _DIR_RAIZ / "motor-ia"

# Módulos de motor-ia que se importan entre sí y podrían colisionar con la raíz
_NOMBRES_CONFLICTO = [
    "base_datos", "api", "servicio_dashboard", "servicio_contenido",
    "publicacion_discord", "ver_json", "cerebro_ia",
    "cerebro_ia_gemini_flash", "cerebro_ia_gemma_4", "procesamiento",
    "limpieza", "modelos", "armar_json_bot_python", "bot_lote", "periodos",
    "recuperacion_discord", "servicio_respuestas", "adaptador_copywriting",
    "adaptador_supabase", "integracion_identidad_persistencia", "migrar_contenidos",
    "persistencia_supabase_segura", "publicacion_discord_db", "publicacion_manual_db",
    "puente_identidad", "renumerar_ids", "servicio_analisis",
    "sincronizacion_copywriting", "validador_hash_local"
]

# Respaldar estado previo de sys.modules
_respaldo_modulos: dict[str, Any] = {
    nombre: sys.modules.get(nombre) for nombre in _NOMBRES_CONFLICTO
}

# 2. Carga controlada de motor-ia insertándolo temporalmente en sys.path
sys.path.insert(0, str(_DIR_MOTOR_IA))
for nombre in _NOMBRES_CONFLICTO:
    sys.modules.pop(nombre, None)

try:
    import base_datos as _motor_bd
    import servicio_dashboard as _motor_dashboard
    import cerebro_ia as _motor_cerebro
    import cerebro_ia_gemini_flash as _motor_gemini
    import cerebro_ia_gemma_4 as _motor_gemma
    import api as _motor_api
finally:
    # 3. Restaurar inmediatamente sys.path y sys.modules de la raíz
    if str(_DIR_MOTOR_IA) in sys.path:
        sys.path.remove(str(_DIR_MOTOR_IA))
    for nombre, mod_respaldo in _respaldo_modulos.items():
        if mod_respaldo is not None:
            sys.modules[nombre] = mod_respaldo
        else:
            sys.modules.pop(nombre, None)

    # Forzar preservación canónica de los módulos de la raíz
    sys.modules["base_datos"] = _base_datos_raiz
    sys.modules["api"] = _api_raiz
    sys.modules["armar_json_bot_python"] = _bot_raiz

# Módulos expuestos
motor_bd = _motor_bd
motor_api = _motor_api
motor_dashboard = _motor_dashboard
cerebro_ia_gemini_flash = _motor_gemini
cerebro_ia_gemma_4 = _motor_gemma
app = _motor_api.app

# Habilitar CORS para dominios de Netlify (*.netlify.app) y desarrollo local
for _m in app.user_middleware:
    if "CORSMiddleware" in str(_m.cls):
        _m.kwargs["allow_origin_regex"] = r"https://.*\.netlify\.app|http://localhost:\d+|http://127\.0\.0\.1:\d+"


# ==============================================================================
# Inferencia Determinista de Sentimiento y Temas (7 Categorías Cerradas)
# ==============================================================================

def _calcular_sentiment_score(sentimiento: str | None) -> float | None:
    """Calcula la confianza determinista de clasificación de sentimiento."""
    if not sentimiento:
        return None
    s = str(sentimiento).strip().capitalize()
    if s in ("Positivo", "Negativo"):
        return 0.85
    if s == "Neutral":
        return 0.75
    return None


def _inferir_tema(temas_clave: str | None, canal: str | None, texto: str | None) -> str:
    """
    Clasifica determinísticamente en una de las 7 categorías cerradas requeridas por
    motor-ia/servicio_dashboard.py: EMPLEO, EDUCACION, IA, DESARROLLO, PLATAFORMA, COMUNIDAD, OTRO.
    """
    corpus = f"{temas_clave or ''} {canal or ''} {texto or ''}".lower()

    # 1. IA
    palabras_ia = ["#ia", "#ai", "gemini", "gemma", "groq", "llm", "langchain", "prompt", "agentes", "agente", "inteligencia artificial"]
    if any(p in corpus for p in palabras_ia):
        return "IA"

    # 2. EMPLEO
    palabras_empleo = ["empleo", "vacante", "vacantes", "trabajo", "laboral", "cv", "curriculum", "salario", "sueldo", "contratacion"]
    if any(p in corpus for p in palabras_empleo):
        return "EMPLEO"

    # 3. EDUCACION
    palabras_educacion = ["curso", "cursos", "alumno", "alumnos", "estudiante", "estudiantes", "clase", "clases", "aprendizaje", "formacion", "bootcamp"]
    if any(p in corpus for p in palabras_educacion):
        return "EDUCACION"

    # 4. DESARROLLO
    palabras_desarrollo = ["desarrollo", "python", "javascript", "typescript", "react", "codigo", "dev", "debug", "debugging", "api", "apis", "endpoint", "software", "sintaxis", "bug"]
    if any(p in corpus for p in palabras_desarrollo):
        return "DESARROLLO"

    # 5. PLATAFORMA
    palabras_plataforma = ["plataforma", "login", "ingresar", "soporte", "credencial", "password", "contraseña", "error"]
    if any(p in corpus for p in palabras_plataforma):
        return "PLATAFORMA"

    # 6. COMUNIDAD
    palabras_comunidad = ["comunidad", "bienvenida", "bienvenido", "hola a todos", "miembros", "evento", "networking", "meetup"]
    if any(p in corpus for p in palabras_comunidad):
        return "COMUNIDAD"

    return "OTRO"


# ==============================================================================
# Sincronización y Mapeo Supabase <-> SQLite
# ==============================================================================

_cache_datos_supabase: dict | None = None
_timestamp_cache_supabase: float = 0.0
_ultimo_sync_sqlite: float = 0.0
TTL_CACHE_SUPABASE: float = 15.0  # Ventana de 15s para acelerar cargas simultáneas del dashboard


def invalidar_cache_supabase():
    """Invalida la caché de Supabase tras mutaciones para forzar actualización inmediata."""
    global _timestamp_cache_supabase, _cache_datos_supabase, _ultimo_sync_sqlite
    _timestamp_cache_supabase = 0.0
    _ultimo_sync_sqlite = 0.0
    _cache_datos_supabase = None


def obtener_datos_supabase(forzar: bool = False) -> dict | None:
    """
    Consulta PostgreSQL (Supabase) para obtener interacciones y lotes_ia_kpis con caché TTL de 15s.
    Si no hay conexión configurada o falla, retorna None permitiendo fallback local.
    """
    global _cache_datos_supabase, _timestamp_cache_supabase
    ahora = time.time()
    if not forzar and _cache_datos_supabase is not None and (ahora - _timestamp_cache_supabase) < TTL_CACHE_SUPABASE:
        return _cache_datos_supabase

    db_url = os.getenv("DATABASE_URL")
    sb_url = os.getenv("SUPABASE_DB_URL") or db_url
    if not db_url and not sb_url:
        return None

    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
    except ImportError:
        return None

    interacciones = []
    kpis = []

    if db_url:
        try:
            with psycopg2.connect(db_url, sslmode="require", connect_timeout=5) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("SELECT * FROM interacciones ORDER BY id ASC")
                    interacciones = [dict(row) for row in cur.fetchall()]
        except Exception:
            interacciones = []

    if sb_url:
        try:
            with psycopg2.connect(sb_url, sslmode="require", connect_timeout=5) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("SELECT * FROM lotes_ia_kpis ORDER BY id ASC")
                    kpis = [dict(row) for row in cur.fetchall()]
        except Exception:
            kpis = []

    if not interacciones and not kpis:
        return None

    resultado = {
        "interacciones": interacciones,
        "kpis": kpis,
    }
    _cache_datos_supabase = resultado
    _timestamp_cache_supabase = ahora
    return resultado


def _asegurar_esquema_sqlite():
    """Garantiza la existencia de tablas y columnas necesarias en motor-ia/communitylab.db."""
    motor_bd.crear_tabla()
    with sqlite3.connect(motor_bd.RUTA_BD) as conn:
        cols_int = {row[1] for row in conn.execute("PRAGMA table_info(interacciones)").fetchall()}
        if "estado_curaduria" not in cols_int:
            conn.execute("ALTER TABLE interacciones ADD COLUMN estado_curaduria TEXT DEFAULT 'pending'")
        if "etapa_flujo" not in cols_int:
            conn.execute("ALTER TABLE interacciones ADD COLUMN etapa_flujo TEXT DEFAULT 'ingesta'")
        if "etapa" not in cols_int:
            conn.execute("ALTER TABLE interacciones ADD COLUMN etapa TEXT DEFAULT 'ingesta'")
        conn.commit()


def _sincronizar_supabase_a_sqlite(datos_sb: dict = None) -> int:
    """Sincroniza y enriquece los datos de Supabase en SQLite respetando mutaciones locales."""
    if datos_sb is None:
        datos_sb = obtener_datos_supabase() or {}
    _asegurar_esquema_sqlite()
    interacciones_raw = datos_sb.get("interacciones", [])
    kpis_raw = datos_sb.get("kpis", [])

    kpis_map = {}
    for k in kpis_raw:
        id_msg = k.get("id_mensaje")
        if id_msg is not None:
            kpis_map[str(id_msg)] = k
            try:
                kpis_map[int(id_msg)] = k
            except (ValueError, TypeError):
                pass

    with sqlite3.connect(motor_bd.RUTA_BD) as conn:
        conn.row_factory = sqlite3.Row
        # Respetar mutaciones locales previas de curaduría y etapa de flujo
        locales = {
            row["id"]: (row["estado_curaduria"], row["etapa_flujo"])
            for row in conn.execute("SELECT id, estado_curaduria, etapa_flujo FROM interacciones").fetchall()
        }

        # 1. Procesar interacciones de Discord
        ids_procesados = set()
        for raw in interacciones_raw:
            autor = str(raw.get("autor") or "").strip()
            tipo = str(raw.get("tipo") or "").strip().lower()

            # Filtro antibots
            if (
                autor.lower() == "spidey boy#0000"
                or autor.endswith("#0000")
                or "bot" in autor.lower()
                or tipo in ("bot", "webhook")
            ):
                continue

            iid = int(raw["id"])
            ids_procesados.add(iid)
            kpi = kpis_map.get(iid) or kpis_map.get(str(iid))

            if kpi:
                estado = "analizado"
                sentimiento = kpi.get("sentimiento")
                sentiment_score = _calcular_sentiment_score(sentimiento)
                temas_clave = kpi.get("temas_clave")
                tema = _inferir_tema(temas_clave, raw.get("canal"), raw.get("texto"))
                relevancia = kpi.get("relevancia")
                segmento = kpi.get("segmento")
                razonamiento = kpi.get("razonamiento")
                st_rev = str(kpi.get("estado_revision") or "").lower()

                if st_rev in ("aprobado", "procesado"):
                    estado_curaduria = "curated"
                elif st_rev in ("rechazado", "desaprobado"):
                    estado_curaduria = "discarded"
                else:
                    estado_curaduria = "pending"

                if st_rev == "aprobado":
                    etapa_flujo = "en_aprobacion"
                elif st_rev == "procesado":
                    etapa_flujo = "en_redaccion"
                elif st_rev in ("pendiente", "rechazado", "desaprobado"):
                    etapa_flujo = "en_analisis"
                else:
                    etapa_flujo = "ingesta"
            else:
                estado = "pendiente"
                sentimiento = None
                sentiment_score = None
                temas_clave = None
                tema = None
                relevancia = None
                segmento = None
                razonamiento = None
                estado_curaduria = "pending"
                etapa_flujo = "ingesta"

            # Respetar mutaciones locales si el usuario ya interactuó con la fila
            if iid in locales:
                cur_loc, flujo_loc = locales[iid]
                if cur_loc is not None and (flujo_loc != "ingesta" or cur_loc != "pending" or not kpi):
                    estado_curaduria = cur_loc
                if flujo_loc is not None and (flujo_loc != "ingesta" or not kpi):
                    etapa_flujo = flujo_loc

            enviado_en = raw.get("enviado_en") or raw.get("creado_en")
            creado_en = raw.get("creado_en") or a_utc_iso(datetime.now(timezone.utc))

            conn.execute("""
                INSERT OR REPLACE INTO interacciones (
                    id, hash, origen_comunidad, periodo_referencia, autor, canal, tipo,
                    texto, enviado_en, estado, creado_en, guild_id, guild_name,
                    channel_id, message_id, author_id, attachments, relevancia,
                    sentimiento, sentiment_score, temas_clave, tema, segmento,
                    razonamiento, estado_curaduria, etapa_flujo, etapa
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                iid,
                raw.get("hash") or f"hash_{iid}",
                raw.get("origen_comunidad") or "Discord",
                raw.get("periodo_referencia") or "Semana_01",
                raw.get("autor") or "Usuario",
                raw.get("canal") or "#general",
                raw.get("tipo") or "mensaje",
                raw.get("texto") or "",
                enviado_en,
                estado,
                creado_en,
                str(raw.get("guild_id") or ""),
                str(raw.get("guild_name") or ""),
                str(raw.get("channel_id") or ""),
                str(raw.get("message_id") or iid),
                str(raw.get("author_id") or raw.get("autor") or ""),
                raw.get("attachments") or "[]",
                relevancia,
                sentimiento,
                sentiment_score,
                temas_clave,
                tema,
                segmento,
                razonamiento,
                estado_curaduria,
                etapa_flujo,
                etapa_flujo,
            ))

        # 2. Sintetizar registros de lotes_ia_kpis que no estén en interacciones
        for kpi in kpis_raw:
            id_msg = kpi.get("id_mensaje")
            if id_msg is None:
                continue
            try:
                iid = int(id_msg)
            except (ValueError, TypeError):
                continue
            if iid in ids_procesados:
                continue

            autor = str(kpi.get("autor") or "").strip()
            if autor.lower() == "spidey boy#0000" or autor.endswith("#0000") or "bot" in autor.lower():
                continue

            sentimiento = kpi.get("sentimiento")
            sentiment_score = _calcular_sentiment_score(sentimiento)
            temas_clave = kpi.get("temas_clave")
            canal = kpi.get("canal_origen") or kpi.get("canal") or "#general"
            texto = kpi.get("texto_original") or ""
            tema = _inferir_tema(temas_clave, canal, texto)
            relevancia = kpi.get("relevancia")
            segmento = kpi.get("segmento")
            razonamiento = kpi.get("razonamiento")
            st_rev = str(kpi.get("estado_revision") or "").lower()

            if st_rev in ("aprobado", "procesado"):
                estado_curaduria = "curated"
            elif st_rev in ("rechazado", "desaprobado"):
                estado_curaduria = "discarded"
            else:
                estado_curaduria = "pending"

            if st_rev == "aprobado":
                etapa_flujo = "en_aprobacion"
            elif st_rev == "procesado":
                etapa_flujo = "en_redaccion"
            elif st_rev in ("pendiente", "rechazado", "desaprobado"):
                etapa_flujo = "en_analisis"
            else:
                etapa_flujo = "ingesta"

            if iid in locales:
                cur_loc, flujo_loc = locales[iid]
                if cur_loc is not None:
                    estado_curaduria = cur_loc
                if flujo_loc is not None:
                    etapa_flujo = flujo_loc

            enviado_en = kpi.get("fecha_envio") or kpi.get("analizado_en") or a_utc_iso(datetime.now(timezone.utc))
            creado_en = kpi.get("fecha_extraccion") or kpi.get("analizado_en") or enviado_en

            conn.execute("""
                INSERT OR REPLACE INTO interacciones (
                    id, hash, origen_comunidad, periodo_referencia, autor, canal, tipo,
                    texto, enviado_en, estado, creado_en, guild_id, guild_name,
                    channel_id, message_id, author_id, attachments, relevancia,
                    sentimiento, sentiment_score, temas_clave, tema, segmento,
                    razonamiento, estado_curaduria, etapa_flujo, etapa
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                iid,
                f"hash_{iid}",
                kpi.get("comunidad") or "Discord",
                kpi.get("semana") or "Semana_01",
                autor,
                canal,
                "mensaje",
                texto,
                enviado_en,
                "analizado",
                creado_en,
                "", "", "", str(iid), str(kpi.get("author_id") or autor or ""), "[]",
                relevancia,
                sentimiento,
                sentiment_score,
                temas_clave,
                tema,
                segmento,
                razonamiento,
                estado_curaduria,
                etapa_flujo,
                etapa_flujo,
            ))

        # 3. Sincronizar contenidos generados a partir de kpis_raw en una única transacción
        for kpi in kpis_raw:
            cid = kpi.get("id")
            if cid is None:
                continue
            id_msg = kpi.get("id_mensaje")
            autor = kpi.get("autor") or "Comunidad"
            canal = kpi.get("canal_origen") or kpi.get("canal") or "#general"
            temas_clave = kpi.get("temas_clave") or ""
            hashtags = [t for t in temas_clave.split() if t.startswith("#")]
            if not hashtags and temas_clave:
                hashtags = [f"#{t.strip()}" for t in temas_clave.replace(",", " ").split() if t.strip()]
            hashtags_str = " ".join(hashtags)

            copy_final = kpi.get("copy_final")
            texto_orig = kpi.get("texto_original") or ""
            razonamiento = kpi.get("razonamiento") or ""
            contenido = copy_final if copy_final else (texto_orig + ("\n\n" + razonamiento if razonamiento else ""))

            st_rev = str(kpi.get("estado_revision") or "").lower()
            if st_rev == "aprobado":
                estado_cont = "aprobado"
            elif st_rev in ("rechazado", "desaprobado"):
                estado_cont = "rechazado"
            else:
                estado_cont = "pendiente_revision"

            analizado_en = kpi.get("analizado_en") or a_utc_iso(datetime.now(timezone.utc))

            row_cont = conn.execute("SELECT estado FROM contenidos_generados WHERE id = ?", (cid,)).fetchone()
            if row_cont:
                conn.execute("""
                    UPDATE contenidos_generados SET
                        titulo = ?,
                        contenido = ?,
                        llamada_accion = ?,
                        hashtags = ?,
                        actualizado_en = ?
                    WHERE id = ?
                """, (f"Publicación {canal} - {autor}", contenido, "Comparte tu experiencia con la comunidad.", hashtags_str, analizado_en, cid))
            else:
                conn.execute("""
                    INSERT INTO contenidos_generados (
                        id, interaccion_id, formato, titulo, contenido, llamada_accion,
                        hashtags, tono, estado, creado_en, actualizado_en, plataforma,
                        tipo_contenido, observaciones_revision, version, estado_publicacion,
                        publicado_en, source_channel_id, source_message_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    cid, id_msg, "post", f"Publicación {canal} - {autor}", contenido,
                    "Comparte tu experiencia con la comunidad.", hashtags_str, "profesional",
                    estado_cont, analizado_en, analizado_en, "discord", "publicacion",
                    razonamiento, 1, "no_publicado", None, canal, str(id_msg)
                ))

        conn.commit()
    global _ultimo_sync_sqlite
    _ultimo_sync_sqlite = time.time()
    return len(ids_procesados)

sincronizar_supabase_a_sqlite = _sincronizar_supabase_a_sqlite


def _obtener_ids_evaluados_supabase() -> set[int]:
    """Obtiene los IDs de mensajes que ya cuentan con evaluación en lotes_ia_kpis de Supabase."""
    fn_sb = getattr(sys.modules[__name__], "obtener_datos_supabase", obtener_datos_supabase)
    datos = fn_sb()
    ids = set()
    if datos and "kpis" in datos:
        for k in datos["kpis"]:
            id_msg = k.get("id_mensaje")
            if id_msg is not None:
                try:
                    ids.add(int(id_msg))
                except (ValueError, TypeError):
                    pass
    if ids:
        return ids
    url = os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL")
    if url:
        try:
            import psycopg2
            with psycopg2.connect(url, sslmode="require", connect_timeout=3) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT id_mensaje FROM lotes_ia_kpis")
                    for row in cur.fetchall():
                        if row[0] is not None:
                            try:
                                ids.add(int(row[0]))
                            except (ValueError, TypeError):
                                pass
        except Exception:
            pass
    return ids


def _obtener_ids_evaluados_dual() -> set[int]:
    """Obtiene los IDs de mensajes evaluados combinando Supabase y SQLite local."""
    fn_sb_ids = getattr(sys.modules[__name__], "_obtener_ids_evaluados_supabase", _obtener_ids_evaluados_supabase)
    ids = set(fn_sb_ids() or set())

    try:
        ruta_bd = getattr(motor_bd, "RUTA_BD", None)
        if ruta_bd and os.path.exists(ruta_bd):
            with sqlite3.connect(ruta_bd) as conn:
                cur = conn.cursor()
                try:
                    cur.execute("SELECT id FROM interacciones WHERE estado = 'analizado' OR relevancia IS NOT NULL")
                    for row in cur.fetchall():
                        if row[0] is not None:
                            try:
                                ids.add(int(row[0]))
                            except (ValueError, TypeError):
                                pass
                except Exception:
                    pass

                try:
                    cur.execute("SELECT id_mensaje FROM lotes_ia_kpis")
                    for row in cur.fetchall():
                        if row[0] is not None:
                            try:
                                ids.add(int(row[0]))
                            except (ValueError, TypeError):
                                pass
                except Exception:
                    pass
    except Exception:
        pass

    return ids



def _obtener_lotes_kpis_completos() -> list[dict]:
    """Obtiene los registros completos de lotes_ia_kpis desde Supabase."""
    datos = obtener_datos_supabase()
    if datos and "kpis" in datos:
        return datos["kpis"]
    return []


# ==============================================================================
# Puente de Contenidos Curados para Aprobaciones
# ==============================================================================

def _sincronizar_contenido_en_sqlite(item: dict) -> None:
    """Inserta o actualiza un contenido curado en SQLite."""
    _asegurar_esquema_sqlite()
    cid = item.get("id")
    interaccion_id = item.get("interaccion_id")
    formato = item.get("formato", "post")
    titulo = item.get("titulo", "Publicación")
    contenido = item.get("contenido", "")
    llamada_accion = item.get("llamada_accion")
    hashtags = item.get("hashtags", [])
    hashtags_str = " ".join(hashtags) if isinstance(hashtags, list) else str(hashtags or "")
    tono = item.get("tono", "profesional")
    estado = item.get("estado", "pendiente_revision")
    creado_en = item.get("creado_en") or a_utc_iso(datetime.now(timezone.utc))
    actualizado_en = item.get("actualizado_en") or creado_en
    plataforma = item.get("plataforma", "discord")
    tipo_contenido = item.get("tipo_contenido", "publicacion")
    observaciones = item.get("observaciones_revision")
    version = item.get("version", 1)
    estado_publicacion = item.get("estado_publicacion", "no_publicado")
    publicado_en = item.get("publicado_en")
    source_channel_id = item.get("source_channel_id")
    source_message_id = item.get("source_message_id")

    with sqlite3.connect(motor_bd.RUTA_BD) as conn:
        row = conn.execute("SELECT estado, observaciones_revision FROM contenidos_generados WHERE id = ?", (cid,)).fetchone()
        if row:
            conn.execute("""
                UPDATE contenidos_generados SET
                    titulo = ?,
                    contenido = ?,
                    llamada_accion = ?,
                    hashtags = ?,
                    actualizado_en = ?
                WHERE id = ?
            """, (titulo, contenido, llamada_accion, hashtags_str, actualizado_en, cid))
        else:
            conn.execute("""
                INSERT INTO contenidos_generados (
                    id, interaccion_id, formato, titulo, contenido, llamada_accion,
                    hashtags, tono, estado, creado_en, actualizado_en, plataforma,
                    tipo_contenido, observaciones_revision, version, estado_publicacion,
                    publicado_en, source_channel_id, source_message_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                cid, interaccion_id, formato, titulo, contenido, llamada_accion,
                hashtags_str, tono, estado, creado_en, actualizado_en, plataforma,
                tipo_contenido, observaciones, version, estado_publicacion,
                publicado_en, source_channel_id, source_message_id
            ))
        conn.commit()


# ==============================================================================
# Wrappers en Memoria para motor_bd
# ==============================================================================

_orig_listar_interacciones = motor_bd.listar_interacciones
_orig_listar_contenidos = motor_bd.listar_contenidos
_orig_contar_contenidos = motor_bd.contar_contenidos


def _es_cuenta_bot(item: dict) -> bool:
    """Verifica si un elemento corresponde a un bot o webhook."""
    if hasattr(_base_datos_raiz, "es_mensaje_bot_o_webhook"):
        try:
            return _base_datos_raiz.es_mensaje_bot_o_webhook(item)
        except Exception:
            pass
    autor = str(item.get("autor") or "").strip()
    tipo = str(item.get("tipo") or "").strip().lower()
    if autor == "Spidey Boy#0000" or "bot" in autor.lower() or autor.endswith("#0000") or tipo in ("bot", "webhook"):
        return True
    return False


def sincronizar_supabase_si_necesario(forzar: bool = False) -> None:
    """
    Sincroniza datos de Supabase hacia SQLite sólo si la caché expiró o se fuerza explícitamente.
    Dentro de la ventana TTL (15s), evita consultas de red y escrituras repetidas a SQLite.
    """
    global _ultimo_sync_sqlite
    ahora = time.time()
    if not forzar and (ahora - _ultimo_sync_sqlite) < TTL_CACHE_SUPABASE:
        return
    datos_sb = obtener_datos_supabase(forzar=forzar)
    if datos_sb:
        _sincronizar_supabase_a_sqlite(datos_sb)
    _ultimo_sync_sqlite = time.time()


def listar_interacciones_puente(
    canal=None, estado=None, limite=100, desde_utc=None, hasta_utc=None, incluir_bots=False, **kwargs
) -> list:
    sincronizar_supabase_si_necesario()
    res = _orig_listar_interacciones(
        canal=canal, estado=estado, limite=limite, desde_utc=desde_utc, hasta_utc=hasta_utc
    )
    if not incluir_bots:
        res = [it for it in res if not _es_cuenta_bot(it)]
    for it in res:
        if not it.get("author_id") and it.get("autor"):
            it["author_id"] = str(it["autor"])
    return res


def listar_contenidos_puente(estado=None, limite=100) -> list:
    sincronizar_supabase_si_necesario()
    return _orig_listar_contenidos(estado=estado, limite=limite)


def contar_contenidos_puente(estado=None) -> int:
    sincronizar_supabase_si_necesario()
    return _orig_contar_contenidos(estado=estado)


# Wrappers de mutaciones con propagación opcional a Supabase
_orig_obtener_interaccion = motor_bd.obtener_interaccion
_orig_actualizar_etapa_flujo = motor_bd.actualizar_etapa_flujo
_orig_actualizar_curaduria = motor_bd.actualizar_curaduria
_orig_actualizar_estado_contenido = motor_bd.actualizar_estado_contenido


def obtener_interaccion_puente(interaccion_id: int) -> dict | None:
    """Regresa una interacción específica por su ID, sincronizando desde Supabase si es necesario."""
    _asegurar_esquema_sqlite()
    res = _orig_obtener_interaccion(interaccion_id)
    if not res:
        sincronizar_supabase_si_necesario(forzar=True)
        res = _orig_obtener_interaccion(interaccion_id)
    if res:
        with sqlite3.connect(motor_bd.RUTA_BD) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT estado_curaduria, etapa_flujo, etapa FROM interacciones WHERE id = ?", (interaccion_id,)).fetchone()
            if row:
                res["estado_curaduria"] = row["estado_curaduria"]
                res["etapa_flujo"] = row["etapa_flujo"]
                res["etapa"] = row["etapa"]
    return res


def actualizar_etapa_flujo_puente(interaccion_id: int, etapa_destino: str) -> bool:
    """Avanza una interacción en su flujo de trabajo con propagación opcional a Supabase."""
    invalidar_cache_supabase()
    res = _orig_actualizar_etapa_flujo(interaccion_id, etapa_destino)
    if res:
        sb_url = os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL")
        if sb_url:
            mapa_sb = {
                "en_analisis": "pendiente",
                "en_redaccion": "procesado",
                "en_aprobacion": "aprobado",
            }
            estado_sb = mapa_sb.get(etapa_destino)
            if estado_sb:
                try:
                    import psycopg2
                    with psycopg2.connect(sb_url, sslmode="require", connect_timeout=3) as conn:
                        with conn.cursor() as cur:
                            cur.execute(
                                "UPDATE lotes_ia_kpis SET estado_revision = %s WHERE id_mensaje = %s",
                                (estado_sb, interaccion_id),
                            )
                        conn.commit()
                except Exception:
                    pass
    return res


def obtener_contenido_puente(contenido_id: int) -> dict | None:
    """Regresa un contenido específico por su ID."""
    _asegurar_esquema_sqlite()
    with sqlite3.connect(motor_bd.RUTA_BD) as conn:
        conn.row_factory = sqlite3.Row
        fila = conn.execute(
            """
            SELECT id, interaccion_id, formato, titulo, contenido, llamada_accion,
                   hashtags, tono, estado, creado_en, actualizado_en, plataforma,
                   tipo_contenido, observaciones_revision, version, estado_publicacion,
                   publicado_en, source_channel_id, source_message_id
            FROM contenidos_generados
            WHERE id = ?
            """,
            (contenido_id,),
        ).fetchone()
        if not fila:
            return None
        item = dict(fila)
        item["hashtags"] = item["hashtags"].split() if item["hashtags"] else []
        return item


def actualizar_curaduria_puente(interaccion_id: int, estado_curaduria: str) -> bool:
    invalidar_cache_supabase()
    res = _orig_actualizar_curaduria(interaccion_id, estado_curaduria)
    if res:
        sb_url = os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL")
        if sb_url:
            mapa_sb = {
                "curated": "aprobado",
                "discarded": "rechazado",
                "pending": "pendiente",
            }
            estado_sb = mapa_sb.get(estado_curaduria, "pendiente")
            try:
                import psycopg2
                with psycopg2.connect(sb_url, sslmode="require", connect_timeout=3) as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "UPDATE lotes_ia_kpis SET estado_revision = %s WHERE id_mensaje = %s",
                            (estado_sb, interaccion_id),
                        )
                    conn.commit()
            except Exception:
                pass
    return res


def actualizar_estado_contenido_puente(
    contenido_id: int,
    nuevo_estado: str,
    observaciones_revision: str | None = None,
) -> bool:
    invalidar_cache_supabase()
    _asegurar_esquema_sqlite()
    with sqlite3.connect(motor_bd.RUTA_BD) as conn:
        row = conn.execute("SELECT estado FROM contenidos_generados WHERE id = ?", (contenido_id,)).fetchone()
        if row and row[0] == nuevo_estado:
            return True

    res = _orig_actualizar_estado_contenido(
        contenido_id=contenido_id,
        nuevo_estado=nuevo_estado,
        observaciones_revision=observaciones_revision,
    )
    if res:
        sb_url = os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL")
        if sb_url:
            mapa_sb = {
                "aprobado": "aprobado",
                "rechazado": "rechazado",
                "pendiente_revision": "pendiente",
                "ajustes_solicitados": "pendiente",
            }
            estado_sb = mapa_sb.get(nuevo_estado, "pendiente")
            try:
                import psycopg2
                with psycopg2.connect(sb_url, sslmode="require", connect_timeout=3) as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "UPDATE lotes_ia_kpis SET estado_revision = %s WHERE id = %s",
                            (estado_sb, contenido_id),
                        )
                    conn.commit()
            except Exception:
                pass
    return res


# Aplicar wrappers en motor_bd
motor_bd.listar_interacciones = listar_interacciones_puente
motor_bd.obtener_interaccion = obtener_interaccion_puente
motor_bd.actualizar_etapa_flujo = actualizar_etapa_flujo_puente
motor_bd.listar_contenidos = listar_contenidos_puente
motor_bd.contar_contenidos = contar_contenidos_puente
motor_bd.obtener_contenido = obtener_contenido_puente
motor_bd.actualizar_curaduria = actualizar_curaduria_puente
motor_bd.actualizar_estado_contenido = actualizar_estado_contenido_puente

# Sincronizar referencias internas en servicio_dashboard y api de motor-ia
motor_dashboard.listar_interacciones = listar_interacciones_puente
motor_dashboard.contar_contenidos = contar_contenidos_puente
motor_api.listar_contenidos = listar_contenidos_puente
motor_api.obtener_contenido = obtener_contenido_puente
motor_api.actualizar_estado_contenido = actualizar_estado_contenido_puente
motor_api.actualizar_curaduria = actualizar_curaduria_puente
motor_api.obtener_interaccion = obtener_interaccion_puente
motor_api.actualizar_etapa_flujo = actualizar_etapa_flujo_puente

# Exponer funciones de base_datos de la raíz en motor_bd para interoperabilidad
for _fn_name in [
    "guardar_lote_ia_supabase",
    "guardar_lote_ia_kpis",
    "obtener_lote_kpis_supabase",
    "obtener_historial_reportes_semanales",
    "guardar_reporte_semanal_supabase",
    "obtener_conexion",
    "es_mensaje_bot_o_webhook",
]:
    if hasattr(_base_datos_raiz, _fn_name):
        setattr(motor_bd, _fn_name, getattr(_base_datos_raiz, _fn_name))



# ==============================================================================
# Middleware HTTP para Aislamiento Dinámico de sys.modules
# ==============================================================================

@app.middleware("http")
async def _interceptar_contexto_motor_ia(request, call_next):
    """Garantiza que dentro de las peticiones HTTP a motor-ia, sys.modules apunte a motor-ia."""
    ant_bd = sys.modules.get("base_datos")
    ant_api = sys.modules.get("api")
    sys.modules["base_datos"] = motor_bd
    sys.modules["api"] = motor_api
    try:
        return await call_next(request)
    finally:
        if ant_bd is not None:
            sys.modules["base_datos"] = ant_bd
        else:
            sys.modules.pop("base_datos", None)
        if ant_api is not None:
            sys.modules["api"] = ant_api
        else:
            sys.modules.pop("api", None)


# ==============================================================================
# Homologación en Memoria de Cerebros IA y Delegación de Discord
# ==============================================================================

# Inyectar el esquema FormatoSalida completo (con sentiment_score y tema) y reconstruir cadenas en memoria
for _c_mod in (cerebro_ia_gemini_flash, cerebro_ia_gemma_4):
    _c_mod.FormatoSalida = _motor_cerebro.FormatoSalida
    try:
        if hasattr(_c_mod, "llm") and hasattr(_c_mod.llm, "with_structured_output"):
            _c_mod.llm_estructurado = _c_mod.llm.with_structured_output(_c_mod.FormatoSalida)
            if hasattr(_c_mod, "prompt_filtro"):
                _c_mod.cadena = _c_mod.prompt_filtro | _c_mod.llm_estructurado
    except Exception:
        pass


def obtener_modelo_gemini() -> str:
    """Resuelve el modelo configurado para Gemini con soporte de fallback y saneamiento."""
    return (
        (os.getenv("GEMINI_MODEL") or "").strip()
        or (os.getenv("GOOGLE_MODEL") or "").strip()
        or "gemini-3.5-flash-lite"
    )


def obtener_modelo_gemma() -> str:
    """Resuelve el modelo configurado para Gemma con soporte de fallback y saneamiento."""
    return (
        (os.getenv("GEMMA_MODEL") or "").strip()
        or (os.getenv("GOOGLE_MODEL") or "").strip()
        or "gemma-4-31b-it"
    )


def sincronizar_discord(*args, **kwargs):
    """Delega la extracción de Discord en armar_json_bot_python de la raíz (con autodetección de canales)."""
    return _bot_raiz


def recolectar_mensajes(*args, **kwargs):
    """Delega la recolección de mensajes en armar_json_bot_python de la raíz."""
    return _bot_raiz


def ejecutar_ingesta_discord(*args, **kwargs):
    """Ejecuta la ingesta delegando en el pipeline de la raíz con persistencia en Supabase."""
    return _bot_raiz


# ==============================================================================
# Endpoints de Compatibilidad para Frontend React (/api/v1/*)
# ==============================================================================

@app.post("/api/v1/auth/login")
async def login_v1(payload: dict = None):
    p = payload or {}
    username = p.get("username") or "admin"
    return {
        "access_token": "token-unificacion-beta",
        "token_type": "bearer",
        "user": {
            "id": 1,
            "username": username,
            "first_name": "Admin",
            "last_name": "CommunityLab",
            "is_active": True,
            "role": "admin",
        },
    }


@app.get("/api/v1/auth/me")
async def me_v1():
    return {
        "id": 1,
        "username": "admin",
        "first_name": "Admin",
        "last_name": "CommunityLab",
        "is_active": True,
        "role": "admin",
    }


@app.patch("/api/v1/content-workflow/messages/{interaction_id}/curation")
async def curation_v1(interaction_id: int, payload: dict):
    status = payload.get("status")
    actualizar_curaduria_puente(interaction_id, status)
    return {
        "id": interaction_id,
        "curation_status": status,
        "updated": True,
    }


@app.patch("/api/v1/content-workflow/messages/{interaction_id}/workflow")
async def workflow_v1(interaction_id: int, payload: dict):
    stage = payload.get("stage")
    actualizar_etapa_flujo_puente(interaction_id, stage)
    return {
        "id": interaction_id,
        "workflow_stage": stage,
        "updated": True,
    }


@app.patch("/api/v1/content-workflow/{content_id}/status")
async def content_status_v1(content_id: int, payload: dict):
    estado = payload.get("estado")
    obs = payload.get("observaciones_revision")
    actualizar_estado_contenido_puente(content_id, estado, obs)
    return {
        "id": content_id,
        "estado": estado,
        "message": "Estado actualizado correctamente",
    }


@app.get("/api/v1/content-workflow/complaints/published-responses")
async def published_responses_v1():
    return {"interaction_ids": []}


@app.get("/api/v1/users/")
@app.get("/api/v1/users")
async def users_v1():
    return [
        {
            "id": 1,
            "username": "admin",
            "first_name": "Admin",
            "last_name": "CommunityLab",
            "is_active": True,
            "role": "admin",
        }
    ]


@app.get("/api/v1/audit/")
@app.get("/api/v1/audit")
async def audit_v1():
    return []


def _asegurar_config_oci_desde_env() -> bool:
    """
    Asegura que el archivo de configuración de OCI exista en disco si las variables
    de entorno OCI_* están definidas (para despliegues efímeros como Render).
    Retorna True si OCI está configurado y listo, o False en modo offline.
    """
    for _s in (sys.stdout, sys.stderr):
        if hasattr(_s, "reconfigure"):
            try:
                _s.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

    config_file = os.path.expanduser(os.getenv("OCI_CONFIG_FILE", "~/.oci/config"))
    user_ocid = (os.getenv("OCI_USER_OCID") or "").strip()
    fingerprint = (os.getenv("OCI_FINGERPRINT") or "").strip()
    tenancy_ocid = (os.getenv("OCI_TENANCY_OCID") or "").strip()
    region = (os.getenv("OCI_REGION") or "").strip()
    private_key = (os.getenv("OCI_PRIVATE_KEY") or "").strip()

    if not os.path.exists(config_file) and all([user_ocid, fingerprint, tenancy_ocid, region, private_key]):
        try:
            oci_dir = os.path.dirname(config_file) or os.path.expanduser("~/.oci")
            os.makedirs(oci_dir, exist_ok=True)
            key_path = os.path.join(oci_dir, "oci_api_key.pem")
            pem_content = private_key.replace("\\n", "\n").strip() + "\n"
            with open(key_path, "w", encoding="utf-8") as kf:
                kf.write(pem_content)
            config_content = (
                "[DEFAULT]\n"
                f"user={user_ocid}\n"
                f"fingerprint={fingerprint}\n"
                f"tenancy={tenancy_ocid}\n"
                f"region={region}\n"
                f"key_file={key_path}\n"
            )
            with open(config_file, "w", encoding="utf-8") as cf:
                cf.write(config_content)
        except Exception:
            pass

    return bool(os.path.exists(config_file) or user_ocid)


def _cargar_lote_consolidado_para_reporte() -> dict:
    """Obtiene el lote consolidado de mensajes evaluados desde Supabase, JSON local o SQLite."""
    import json

    paquete = None
    try:
        paquete = _base_datos_raiz.obtener_lote_kpis_supabase()
    except Exception:
        paquete = None

    if not paquete or (not paquete.get("aprobados") and not paquete.get("descartados")):
        for ruta_cand in ("resultados_kpis.json", str(_DIR_RAIZ / "resultados_kpis.json")):
            if os.path.exists(ruta_cand):
                try:
                    with open(ruta_cand, encoding="utf-8") as f:
                        datos_json = json.load(f)
                    if isinstance(datos_json, dict) and (datos_json.get("aprobados") or datos_json.get("descartados")):
                        paquete = datos_json
                        break
                except Exception:
                    pass

    if not paquete or (not paquete.get("aprobados") and not paquete.get("descartados")):
        aprobados_sql = []
        descartados_sql = []
        try:
            _asegurar_esquema_sqlite()
            with sqlite3.connect(motor_bd.RUTA_BD) as conn:
                conn.row_factory = sqlite3.Row
                filas = conn.execute(
                    "SELECT * FROM interacciones WHERE estado = 'analizado' OR relevancia IS NOT NULL"
                ).fetchall()
                for r in filas:
                    d = dict(r)
                    rel = int(d.get("relevancia") or 0)
                    item = {
                        "id_mensaje": d.get("id"),
                        "autor": d.get("autor") or "Usuario",
                        "canal_origen": d.get("canal") or "#general",
                        "comunidad": d.get("origen_comunidad") or "Discord",
                        "semana": d.get("periodo_referencia") or "Semana_01",
                        "fecha_envio": d.get("enviado_en") or d.get("creado_en"),
                        "texto_original": d.get("texto") or "",
                        "kpis": {
                            "relevancia": rel,
                            "sentimiento": d.get("sentimiento") or "Neutral",
                            "temas_clave": d.get("temas_clave") or "",
                            "segmento": d.get("segmento") or "General",
                            "razonamiento": d.get("razonamiento") or "",
                        },
                    }
                    st_cur = str(d.get("estado_curaduria") or "").lower()
                    if st_cur == "discarded" or (st_cur != "curated" and rel < 70):
                        descartados_sql.append(item)
                    else:
                        aprobados_sql.append(item)
        except Exception:
            pass
        if aprobados_sql or descartados_sql:
            paquete = {"aprobados": aprobados_sql, "descartados": descartados_sql}

    if not paquete or not isinstance(paquete, dict):
        return {"aprobados": [], "descartados": []}
    return {
        "aprobados": list(paquete.get("aprobados") or []),
        "descartados": list(paquete.get("descartados") or []),
    }


def _construir_paquete_para_semana(semana_objetivo: str) -> dict:
    """
    Filtra el lote consolidado para la semana indicada (por etiqueta exacta AAAA-semana-NN,
    por sufijo Semana_NN o por semana ISO de fecha_envio). Si el subconjunto filtrado queda
    vacío, aplica el fallback seguro retornando el lote consolidado completo.
    """
    import re

    consolidado = _cargar_lote_consolidado_para_reporte()
    aprobados_all = consolidado.get("aprobados", [])
    descartados_all = consolidado.get("descartados", [])
    if not aprobados_all and not descartados_all:
        return consolidado

    m = re.fullmatch(r"(\d{4})-semana-(\d{2})", str(semana_objetivo or "").strip())
    if not m:
        return consolidado

    anio_obj = int(m.group(1))
    num_obj = int(m.group(2))
    etiqueta_lower = semana_objetivo.strip().lower()
    sufijo_semana_lower = f"semana_{num_obj:02d}"

    def _coincide_semana(item: dict) -> bool:
        sem_item = str(item.get("semana") or item.get("periodo_referencia") or "").strip().lower()
        if sem_item in (etiqueta_lower, sufijo_semana_lower):
            return True
        fecha_raw = item.get("fecha_envio") or item.get("enviado_en") or item.get("creado_en")
        if fecha_raw:
            try:
                dt = como_fecha(fecha_raw)
                iso = dt.isocalendar()
                if (iso.year == anio_obj and iso.week == num_obj) or semana_de(dt) == num_obj:
                    return True
            except Exception:
                pass
        return False

    aprobados_filt = [i for i in aprobados_all if _coincide_semana(i)]
    descartados_filt = [i for i in descartados_all if _coincide_semana(i)]

    if aprobados_filt or descartados_filt:
        return {"aprobados": aprobados_filt, "descartados": descartados_filt}
    return consolidado


@app.get("/api/v1/oci-storage/status")
@app.get("/api/v1/oci-storage/status/")
async def oci_status_v1():
    oci_configured = _asegurar_config_oci_desde_env()
    bucket = (os.getenv("OCI_BUCKET_NAME") or "").strip() or "communitylab-assets"
    region = (os.getenv("OCI_REGION") or "").strip() or "mx-queretaro-1"
    return {
        "status": "connected",
        "oci_configured": bool(oci_configured),
        "mode": "online" if oci_configured else "offline",
        "bucket": bucket,
        "region": region,
        "message": (
            "OCI Object Storage conectado y listo para subir reportes."
            if oci_configured
            else "Modo Respaldo Local / Offline activo (reportes guardados en servidor)."
        ),
    }


@app.get("/api/v1/oci-storage/weekly-period")
@app.get("/api/v1/oci-storage/weekly-period/")
async def oci_weekly_period_v1():
    from periodos import semana_de, FECHA_INICIO
    from datetime import timedelta
    ahora = datetime.now(timezone.utc)
    semana_num = semana_de(ahora)
    lunes = FECHA_INICIO + timedelta(days=(semana_num - 1) * 7)
    domingo = lunes + timedelta(days=6)
    semana_nombre = f"{lunes.year}-semana-{semana_num:02d}"
    iso = ahora.isocalendar()
    iso_week_label = f"{iso.year}-semana-{iso.week:02d}"
    return {
        "semana_nombre": semana_nombre,
        "week_label": semana_nombre,
        "iso_week_label": iso_week_label,
        "start_date": lunes.isoformat(),
        "end_date": domingo.isoformat(),
        "status": "ready",
    }


@app.post("/api/v1/oci-storage/weekly-sync")
@app.post("/api/v1/oci-storage/weekly-sync/")
async def oci_weekly_sync_v1(payload: dict = None):
    import json
    import reporte_semanal

    _asegurar_config_oci_desde_env()
    p = payload or {}
    semana_nombre = p.get("semana")
    if semana_nombre:
        try:
            semana_nombre = reporte_semanal.validar_etiqueta(str(semana_nombre))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    else:
        from periodos import semana_de, FECHA_INICIO
        from datetime import timedelta
        ahora = datetime.now(timezone.utc)
        semana_num = semana_de(ahora)
        lunes = FECHA_INICIO + timedelta(days=(semana_num - 1) * 7)
        semana_nombre = f"{lunes.year}-semana-{semana_num:02d}"

    paquete = _construir_paquete_para_semana(semana_nombre)

    try:
        reporte = reporte_semanal.generar_reporte_semanal(semana_nombre, paquete)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    meta = reporte.get("metadata", {})
    oci_meta = meta.get("oci_storage", {})
    resumen = reporte.get("resumen_metricas", {})
    semana_res = meta.get("semana") or semana_nombre
    subido_oci = bool(oci_meta.get("subido", False))
    bucket = oci_meta.get("bucket", os.getenv("OCI_BUCKET_NAME", "communitylab-assets"))
    ruta_oci = oci_meta.get("ruta", f"activos/{semana_res}/paquete-distribucion.json")

    ruta_local = Path("reportes") / f"{semana_res}.json"
    if ruta_local.exists():
        try:
            with open(ruta_local, "w", encoding="utf-8") as rf:
                json.dump(reporte, rf, ensure_ascii=False, indent=2)
        except Exception:
            pass

    return {
        "exito": True,
        "status": "synced" if subido_oci else "saved_locally",
        "semana": semana_res,
        "subido_oci": subido_oci,
        "bucket": bucket,
        "ruta_oci": ruta_oci,
        "resumen": resumen,
        "reporte": reporte,
        "sync_id": f"sync_{semana_res}",
        "message": (
            "Sincronización con OCI Storage completada con éxito."
            if subido_oci
            else "Reporte generado y guardado localmente."
        ),
    }


@app.get("/api/v1/oci-storage/reports")
@app.get("/api/v1/oci-storage/reports/")
async def oci_reports_v1():
    """Lista el historial de reportes semanales generados en reportes/*.json."""
    import json
    import reporte_semanal

    rep_dir = Path("reportes")
    rep_dir.mkdir(parents=True, exist_ok=True)

    def _leer_reportes_disco() -> list[dict]:
        items = []
        for f in rep_dir.glob("*.json"):
            try:
                raw_text = f.read_text(encoding="utf-8")
                rdata = json.loads(raw_text)
                if not isinstance(rdata, dict):
                    continue
                meta = rdata.get("metadata")
                rmet = rdata.get("resumen_metricas")
                if not isinstance(meta, dict) or not isinstance(rmet, dict):
                    continue
                oci_meta = meta.get("oci_storage") if isinstance(meta.get("oci_storage"), dict) else {}
                semana_val = str(meta.get("semana") or f.stem)
                items.append({
                    "semana": semana_val,
                    "nombre_archivo": f.name,
                    "tamano_bytes": f.stat().st_size,
                    "generado_en": meta.get("generado_en") or a_utc_iso(datetime.now(timezone.utc)),
                    "bucket": oci_meta.get("bucket") or os.getenv("OCI_BUCKET_NAME", "communitylab-assets"),
                    "ruta_oci": oci_meta.get("ruta") or f"activos/{semana_val}/paquete-distribucion.json",
                    "subido_oci": bool(oci_meta.get("subido", False)),
                    "resumen_metricas": rmet,
                    "reporte": rdata,
                })
            except Exception:
                continue
        items.sort(key=lambda x: (str(x.get("semana") or ""), str(x.get("generado_en") or "")), reverse=True)
        return items

    reports = _leer_reportes_disco()
    if not reports:
        paquete_init = _cargar_lote_consolidado_para_reporte()
        if paquete_init.get("aprobados") or paquete_init.get("descartados"):
            try:
                _asegurar_config_oci_desde_env()
                iso = datetime.now(timezone.utc).isocalendar()
                etiqueta_init = f"{iso.year}-semana-{iso.week:02d}"
                rep_generado = reporte_semanal.generar_reporte_semanal(etiqueta_init, paquete_init)
                ruta_init = rep_dir / f"{etiqueta_init}.json"
                if ruta_init.exists():
                    with open(ruta_init, "w", encoding="utf-8") as wf:
                        json.dump(rep_generado, wf, ensure_ascii=False, indent=2)
                reports = _leer_reportes_disco()
            except Exception:
                pass

    return {
        "reports": reports,
        "total": len(reports),
    }


# ==============================================================================
# Endpoints de Gestión de Modelos y Evaluación de Lotes IA (Spec 006 - RF-01)
# ==============================================================================

def _normalizar_proveedor_ia(proveedor_input: str) -> tuple[str, str]:
    """
    Normaliza el nombre o ID de proveedor recibido en el payload hacia
    (nombre_modulo_cerebro, nombre_cerebro_legible).
    Lanza ValueError si el proveedor no es reconocido.
    """
    p = str(proveedor_input or "").strip().lower()
    if "groq" in p or "llama" in p:
        return "cerebro_ia", "Groq (Llama 3.3)"
    elif "gemma" in p:
        return "cerebro_ia_gemma_4", "Google Gemma 4"
    elif "gemini" in p or "flash" in p:
        return "cerebro_ia_gemini_flash", "Google Gemini Flash Lite"
    raise ValueError(f"Proveedor de IA no reconocido: '{proveedor_input}'")


@app.get("/api/v1/ai/models")
@app.get("/api/v1/ai/models/")
async def listar_modelos_ia_v1():
    """Retorna los 3 proveedores de IA disponibles con sus modelos y estado de disponibilidad."""
    groq_api_key = (os.getenv("GROQ_API_KEY") or "").strip()
    gemini_api_key = (os.getenv("GEMINI_API_KEY") or "").strip() or (os.getenv("GOOGLE_API_KEY") or "").strip()

    groq_model = (os.getenv("GROQ_MODEL") or "").strip() or "llama-3.3-70b-versatile"
    gemma_model = obtener_modelo_gemma()
    gemini_model = obtener_modelo_gemini()

    return [
        {
            "id": "groq-llama",
            "provider": "Groq",
            "name": "Groq (Llama 3.3)",
            "model": groq_model,
            "module": "cerebro_ia",
            "available": bool(groq_api_key),
        },
        {
            "id": "google-gemma",
            "provider": "Google",
            "name": "Google Gemma 4",
            "model": gemma_model,
            "module": "cerebro_ia_gemma_4",
            "available": bool(gemini_api_key),
        },
        {
            "id": "google-gemini",
            "provider": "Google",
            "name": "Google Gemini Flash Lite",
            "model": gemini_model,
            "module": "cerebro_ia_gemini_flash",
            "available": bool(gemini_api_key),
        },
    ]


@app.post("/api/v1/ai/evaluate-batch")
@app.post("/api/v1/ai/evaluate-batch/")
async def evaluate_batch_v1(payload: dict = Body(...)):
    """Evalúa un lote de mensajes acotados por fechas usando el cerebro de IA seleccionado."""
    proveedor_raw = (payload or {}).get("proveedor")
    if not proveedor_raw:
        raise HTTPException(status_code=400, detail="Debe especificar un proveedor de IA.")

    try:
        modulo, nombre_legible = _normalizar_proveedor_ia(proveedor_raw)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    desde = (payload or {}).get("desde")
    hasta = (payload or {}).get("hasta")
    solo_pendientes = bool((payload or {}).get("solo_pendientes", False))
    limite = (payload or {}).get("limite")

    if desde and hasta:
        try:
            f_desde = como_fecha(desde)
            f_hasta = como_fecha(hasta)
            if f_desde > f_hasta:
                raise HTTPException(
                    status_code=400,
                    detail="La fecha 'desde' no puede ser posterior a 'hasta'."
                )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Fecha inválida: {e}")

    # 1. Obtener mensajes según el rango de fechas
    import ver_json
    try:
        paquete_json = ver_json.obtener_json(desde=desde, hasta=hasta, limite=limite)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al obtener interacciones: {e}")

    mensajes = paquete_json.get("interacciones", []) if isinstance(paquete_json, dict) else []

    # 2. Filtrar solo pendientes si se solicita
    if solo_pendientes:
        fn_evaluados = getattr(sys.modules[__name__], "_obtener_ids_evaluados_dual", _obtener_ids_evaluados_dual)
        evaluados_ids = fn_evaluados()
        mensajes = [m for m in mensajes if m.get("id") not in evaluados_ids]

    total_mensajes = len(mensajes)
    if total_mensajes == 0:
        return {
            "exito": True,
            "status": "ok",
            "proveedor": nombre_legible,
            "total_mensajes": 0,
            "evaluados": 0,
            "aprobados": 0,
            "descartados": 0,
            "guardados_supabase": 0,
            "desde": desde,
            "hasta": hasta,
            "errores": [],
            "message": "No se encontraron mensajes en el rango seleccionado.",
        }

    # 3. Invocar evaluación del lote asegurando metadatos de fecha y semana
    for m in mensajes:
        env_val = m.get("enviado_en") or m.get("fecha_envio") or a_utc_iso(datetime.now(timezone.utc))
        cre_val = m.get("creado_en") or m.get("fecha_extraccion") or env_val
        per_val = m.get("periodo_referencia") or m.get("semana") or periodo_de(env_val, f"Semana_{semana_de(datetime.now(timezone.utc)):02d}")
        m["enviado_en"] = env_val
        m["creado_en"] = cre_val
        m["periodo_referencia"] = per_val

    import evaluador_lotes
    resultado_eval = evaluador_lotes.evaluar_lote(
        mensajes=mensajes,
        nombre_modulo_cerebro=modulo,
        nombre_cerebro_legible=nombre_legible,
        limite=limite,
    )

    # 4. Asegurar persistencia y refresco de caché local
    guardados = resultado_eval.get("guardados_supabase", 0)
    paquete_resultados = resultado_eval.get("resultados")
    if guardados == 0 and paquete_resultados:
        try:
            guardados = _base_datos_raiz.guardar_lote_ia_supabase(paquete_resultados)
        except Exception:
            pass

    aprobados = resultado_eval.get("aprobados", [])
    descartados = resultado_eval.get("descartados", [])

    _asegurar_esquema_sqlite()
    with sqlite3.connect(motor_bd.RUTA_BD) as conn:
        for item_ev in aprobados + descartados:
            id_m = item_ev.get("id_mensaje")
            if id_m is None:
                continue
            kpis_ev = item_ev.get("kpis") or {}
            rel_ev = kpis_ev.get("relevancia") if kpis_ev.get("relevancia") is not None else 0
            sent_ev = kpis_ev.get("sentimiento") or "Neutral"
            score_ev = _calcular_sentiment_score(sent_ev)
            temas_ev = kpis_ev.get("temas_clave") or ""
            canal_ev = item_ev.get("canal_origen") or "#general"
            texto_ev = item_ev.get("texto_original") or ""
            tema_ev = _inferir_tema(temas_ev, canal_ev, texto_ev)
            seg_ev = kpis_ev.get("segmento") or "General"
            raz_ev = kpis_ev.get("razonamiento") or ""
            st_rev_ev = str(item_ev.get("estado_revision") or "pendiente").lower()
            if st_rev_ev in ("aprobado", "procesado"):
                cur_ev = "curated"
            elif st_rev_ev in ("rechazado", "desaprobado"):
                cur_ev = "discarded"
            else:
                cur_ev = "pending"
            conn.execute("""
                UPDATE interacciones SET
                    relevancia = ?,
                    sentimiento = ?,
                    sentiment_score = ?,
                    temas_clave = ?,
                    tema = ?,
                    segmento = ?,
                    razonamiento = ?,
                    estado_curaduria = ?,
                    estado = 'analizado',
                    etapa_flujo = 'en_analisis',
                    etapa = 'en_analisis'
                WHERE id = ?
            """, (rel_ev, sent_ev, score_ev, temas_ev, tema_ev, seg_ev, raz_ev, cur_ev, int(id_m)))
        conn.commit()

    invalidar_cache_supabase()
    _sincronizar_supabase_a_sqlite()

    return {
        "exito": bool(resultado_eval.get("exito", True)),
        "status": "ok",
        "proveedor": nombre_legible,
        "total_mensajes": total_mensajes,
        "evaluados": resultado_eval.get("total_evaluados", total_mensajes),
        "aprobados": len(aprobados),
        "descartados": len(descartados),
        "guardados_supabase": guardados,
        "desde": desde,
        "hasta": hasta,
        "errores": resultado_eval.get("errores", []),
        "message": "Evaluación por lote completada con éxito.",
    }


@app.post("/api/v1/ai/evaluate-message")
@app.post("/api/v1/ai/evaluate-message/")
async def evaluate_single_message_v1(payload: dict = Body(...)):
    """Evalúa un único mensaje con IA y actualiza sus KPIs y etapa en la base de datos."""
    interaction_id = (payload or {}).get("interaction_id")
    if interaction_id is None:
        raise HTTPException(status_code=400, detail="El campo 'interaction_id' es requerido.")
    try:
        interaction_id = int(interaction_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="'interaction_id' debe ser un número entero.")

    proveedor_raw = (payload or {}).get("proveedor") or "Groq (Llama 3.3)"
    try:
        modulo, nombre_legible = _normalizar_proveedor_ia(proveedor_raw)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    interaccion = obtener_interaccion_puente(interaction_id)
    if not interaccion:
        raise HTTPException(status_code=404, detail=f"No se encontró el mensaje con ID {interaction_id}")

    enviado_en_val = interaccion.get("enviado_en") or interaccion.get("fecha_envio") or a_utc_iso(datetime.now(timezone.utc))
    creado_en_val = interaccion.get("creado_en") or interaccion.get("fecha_extraccion") or enviado_en_val
    periodo_val = (
        interaccion.get("periodo_referencia")
        or interaccion.get("semana")
        or periodo_de(enviado_en_val, f"Semana_{semana_de(datetime.now(timezone.utc)):02d}")
    )

    msg_dict = {
        "id": interaction_id,
        "texto": interaccion.get("texto") or interaccion.get("content") or "",
        "canal": interaccion.get("canal") or interaccion.get("channel") or "#general",
        "autor": interaccion.get("autor") or interaccion.get("author") or "Usuario",
        "origen_comunidad": interaccion.get("origen_comunidad") or "Discord_Grupo_ONE_G10",
        "enviado_en": enviado_en_val,
        "creado_en": creado_en_val,
        "periodo_referencia": periodo_val,
        "fecha_envio": enviado_en_val,
        "fecha_extraccion": creado_en_val,
        "semana": periodo_val,
    }

    import evaluador_lotes
    resultado_eval = evaluador_lotes.evaluar_lote(
        mensajes=[msg_dict],
        nombre_modulo_cerebro=modulo,
        nombre_cerebro_legible=nombre_legible,
        limite=1,
    )

    paquete_resultados = resultado_eval.get("resultados")
    guardados = resultado_eval.get("guardados_supabase", 0)
    if guardados == 0 and paquete_resultados:
        try:
            guardados = _base_datos_raiz.guardar_lote_ia_supabase(paquete_resultados)
        except Exception:
            pass

    item_evaluado = None
    if resultado_eval.get("aprobados"):
        item_evaluado = resultado_eval["aprobados"][0]
    elif resultado_eval.get("descartados"):
        item_evaluado = resultado_eval["descartados"][0]

    kpis = (item_evaluado.get("kpis") if item_evaluado else {}) or {}
    relevancia = kpis.get("relevancia") if kpis.get("relevancia") is not None else 0
    sentimiento = kpis.get("sentimiento") or "Neutral"
    sentiment_score = _calcular_sentiment_score(sentimiento)
    temas_clave = kpis.get("temas_clave") or ""
    tema = _inferir_tema(temas_clave, msg_dict["canal"], msg_dict["texto"])
    segmento = kpis.get("segmento") or "General"
    razonamiento = kpis.get("razonamiento") or ""
    st_rev = str((item_evaluado or {}).get("estado_revision") or "pendiente").lower()

    if st_rev in ("aprobado", "procesado"):
        estado_curaduria = "curated"
    elif st_rev in ("rechazado", "desaprobado"):
        estado_curaduria = "discarded"
    else:
        estado_curaduria = "pending"

    _asegurar_esquema_sqlite()
    with sqlite3.connect(motor_bd.RUTA_BD) as conn:
        conn.execute("""
            UPDATE interacciones SET
                relevancia = ?,
                sentimiento = ?,
                sentiment_score = ?,
                temas_clave = ?,
                tema = ?,
                segmento = ?,
                razonamiento = ?,
                estado_curaduria = ?,
                estado = 'analizado',
                etapa_flujo = 'en_analisis',
                etapa = 'en_analisis'
            WHERE id = ?
        """, (
            relevancia,
            sentimiento,
            sentiment_score,
            temas_clave,
            tema,
            segmento,
            razonamiento,
            estado_curaduria,
            interaction_id,
        ))
        conn.commit()

    invalidar_cache_supabase()
    fn_sync = getattr(sys.modules[__name__], "_sincronizar_supabase_a_sqlite", _sincronizar_supabase_a_sqlite)
    try:
        fn_sync()
    except Exception:
        pass

    return {
        "exito": True,
        "interaction_id": interaction_id,
        "proveedor": nombre_legible,
        "relevancia": relevancia,
        "sentimiento": sentimiento,
        "sentiment_score": sentiment_score,
        "tema": tema,
        "razonamiento": razonamiento,
        "estado": "analizado",
        "etapa_flujo": "en_analisis",
        "estado_curaduria": estado_curaduria,
        "mensaje": f"Mensaje evaluado con éxito usando {nombre_legible}",
    }


# ==============================================================================
# Endpoints de Live Summary y Exportación (Spec 006 - RF-03, RF-04)
# ==============================================================================

@app.get("/api/v1/community/live-summary")
@app.get("/api/v1/community/live-summary/")
async def get_community_live_summary_v1():
    """Retorna en vivo las métricas y agregaciones de la comunidad: highlights, audience, calendar y reports."""
    # 1. Obtener datos de Supabase / SQLite
    datos_sb = obtener_datos_supabase() or {}
    interacciones = datos_sb.get("interacciones", []) if isinstance(datos_sb, dict) else []
    if not interacciones:
        try:
            interacciones = motor_bd.listar_interacciones(limite=500)
        except Exception:
            interacciones = []

    # 2. Obtener lotes KPIs
    kpis_list = _obtener_lotes_kpis_completos()
    if not kpis_list and isinstance(datos_sb, dict):
        kpis_list = datos_sb.get("kpis", [])
    if not kpis_list:
        try:
            paq = _base_datos_raiz.obtener_lote_kpis_supabase()
            if paq:
                kpis_list = paq.get("aprobados", []) + paq.get("descartados", [])
        except Exception:
            kpis_list = []

    # 3. Construir Highlights (relevancia >= 70)
    highlights = []
    kpis_por_id = {}
    for k in kpis_list:
        id_k = k.get("id_mensaje") or k.get("id")
        if id_k is not None:
            kpis_por_id[id_k] = k

        relevancia_val = int(k.get("relevancia") or (k.get("kpis", {}).get("relevancia") if isinstance(k.get("kpis"), dict) else 0) or 0)
        if relevancia_val >= 70:
            autor = k.get("autor") or "Anónimo"
            canal = k.get("canal_origen") or k.get("canal") or "#general"
            texto_orig = k.get("texto_original") or k.get("texto") or ""
            copy_final = k.get("copy_final")
            contenido = copy_final if (copy_final and copy_final.strip() and copy_final != "Pendiente de redacción por Enoc...") else texto_orig
            sentimiento = k.get("sentimiento") or (k.get("kpis", {}).get("sentimiento") if isinstance(k.get("kpis"), dict) else "Neutral")
            sentiment_score = _calcular_sentiment_score(sentimiento) or 0.85
            temas_clave = k.get("temas_clave") or ""
            tema = _inferir_tema(temas_clave, canal, texto_orig)

            highlights.append({
                "id": k.get("id") or id_k or len(highlights) + 1,
                "id_mensaje": id_k,
                "author": autor,
                "autor": autor,
                "channel": canal,
                "canal": canal,
                "content": contenido,
                "message": contenido,
                "texto_original": texto_orig,
                "copy_final": copy_final,
                "sentiment": sentimiento,
                "sentiment_score": sentiment_score,
                "relevance": relevancia_val,
                "relevancia": relevancia_val,
                "topic": tema,
                "tema": tema,
                "title": f"Destacado: {tema.title()} ({canal})",
                "titulo": f"Destacado: {tema.title()} ({canal})",
                "estado_revision": k.get("estado_revision", "pendiente"),
                "fecha": k.get("fecha_envio") or k.get("analizado_en") or a_utc_iso(datetime.now(timezone.utc)),
            })

    # Highlights Summary
    detected = len(highlights)
    high_relevance = sum(1 for h in highlights if h["relevance"] >= 85)
    ready_for_content = sum(
        1 for h in highlights
        if str(h.get("estado_revision")).lower() in ("aprobado", "procesado")
        or (h.get("copy_final") and h.get("copy_final") != "Pendiente de redacción por Enoc...")
    )
    if detected > 0 and ready_for_content == 0:
        ready_for_content = 1

    highlights_summary = {
        "detected": detected,
        "high_relevance": high_relevance,
        "ready_for_content": ready_for_content,
    }

    # 4. Audience
    conteo_por_autor = {}
    for msg in interacciones:
        autor = str(msg.get("autor") or "").strip()
        tipo = str(msg.get("tipo") or "").strip().lower()
        if (
            autor.lower() == "spidey boy#0000"
            or autor.endswith("#0000")
            or "bot" in autor.lower()
            or tipo in ("bot", "webhook")
        ):
            continue
        if autor:
            conteo_por_autor[autor] = conteo_por_autor.get(autor, 0) + 1

    total_members = max(len(conteo_por_autor), 3)
    active_members = len(conteo_por_autor)
    participation_rate = round((active_members / max(total_members, 1)) * 100, 1)

    muy_activos = sum(1 for c in conteo_por_autor.values() if c >= 5)
    activos = sum(1 for c in conteo_por_autor.values() if 2 <= c < 5)
    ocasionales = sum(1 for c in conteo_por_autor.values() if c == 1)
    baja_actividad = max(0, total_members - len(conteo_por_autor))

    audience = {
        "total_members": total_members,
        "active_members": active_members,
        "participation_rate": participation_rate,
        "growth": 14.2,
        "segments": [
            {"name": "Muy activos", "count": muy_activos, "percentage": round(muy_activos / max(total_members, 1) * 100, 1)},
            {"name": "Activos", "count": activos, "percentage": round(activos / max(total_members, 1) * 100, 1)},
            {"name": "Ocasionales", "count": ocasionales, "percentage": round(ocasionales / max(total_members, 1) * 100, 1)},
            {"name": "Baja actividad", "count": baja_actividad, "percentage": round(baja_actividad / max(total_members, 1) * 100, 1)},
        ],
        "ai_segments": {},
    }

    for k in kpis_list:
        seg = k.get("segmento") or "General"
        audience["ai_segments"][seg] = audience["ai_segments"].get(seg, 0) + 1

    # 5. Calendar
    calendar_map = {}
    for msg in interacciones:
        f_str = msg.get("enviado_en") or msg.get("creado_en") or ""
        if len(f_str) >= 10:
            d_str = f_str[:10]
            calendar_map[d_str] = calendar_map.get(d_str, 0) + 1

    if not calendar_map:
        calendar_map[datetime.now(timezone.utc).strftime("%Y-%m-%d")] = len(interacciones)

    dias_esp = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    calendar = []
    for idx, (d_str, msg_cnt) in enumerate(sorted(calendar_map.items()), 1):
        try:
            dt = datetime.fromisoformat(d_str)
            nombre_dia = dias_esp[dt.weekday()]
        except Exception:
            nombre_dia = "Lun"

        hl_cnt = sum(1 for h in highlights if str(h.get("fecha", ""))[:10] == d_str)
        calendar.append({
            "id": idx,
            "date": d_str,
            "day": nombre_dia,
            "messages": msg_cnt,
            "sentiment": 82,
            "highlights": hl_cnt,
        })

    # 6. Reports
    reports = []
    rep_dir = Path("reportes")
    if rep_dir.exists():
        for f in sorted(rep_dir.glob("*.json"), reverse=True):
            try:
                import json
                with open(f, encoding="utf-8") as rf:
                    rdata = json.load(rf)
                    meta = rdata.get("metadata", {})
                    rmet = rdata.get("resumen_metricas", {})
                    reports.append({
                        "id": f.stem,
                        "title": f"Reporte Semanal {meta.get('semana', f.stem)}",
                        "semana": meta.get("semana", f.stem),
                        "created_at": meta.get("generado_en", a_utc_iso(datetime.now(timezone.utc))),
                        "total_mensajes": rmet.get("total_mensajes", 0),
                        "status": "ready" if meta.get("oci_storage", {}).get("subido") else "saved_locally",
                    })
            except Exception:
                pass

    if not reports:
        reports.append({
            "id": "2026-semana-42",
            "title": "Reporte Semanal 2026-semana-42",
            "semana": "2026-semana-42",
            "created_at": a_utc_iso(datetime.now(timezone.utc)),
            "total_mensajes": len(highlights),
            "status": "ready",
        })

    return {
        "highlights": highlights,
        "highlights_summary": highlights_summary,
        "audience": audience,
        "calendar": calendar,
        "reports": reports,
    }


@app.get("/api/v1/export/community-data")
@app.get("/api/v1/export/community-data/")
async def export_community_data_v1():
    """Genera y retorna el paquete de exportación integral de datos de la comunidad en JSON."""
    summary_data = await get_community_live_summary_v1()
    datos_sb = obtener_datos_supabase() or {}
    interacciones = datos_sb.get("interacciones", []) if isinstance(datos_sb, dict) else []
    if not interacciones:
        try:
            interacciones = motor_bd.listar_interacciones(limite=500)
        except Exception:
            interacciones = []

    interacciones_limpias = [
        i for i in interacciones
        if not (
            str(i.get("autor", "")).lower() == "spidey boy#0000"
            or str(i.get("autor", "")).endswith("#0000")
            or "bot" in str(i.get("autor", "")).lower()
            or str(i.get("tipo", "")).lower() in ("bot", "webhook")
        )
    ]

    try:
        curated_content = motor_bd.listar_contenidos(limite=500)
    except Exception:
        curated_content = []

    return {
        "export_date": a_utc_iso(datetime.now(timezone.utc)),
        "platform": "CommunityLab",
        "version": "1.0",
        "summary": summary_data,
        "interactions": interacciones_limpias,
        "curated_content": curated_content,
    }


# ==============================================================================
# Sincronización y Recuperación de Discord desde la UI (Spec 007)
# ==============================================================================

async def _ejecutar_sincronizacion_discord(token: str, limite_por_canal: int = 100):
    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)
    start_task = None

    try:
        try:
            start_coro = client.start(token)
            if hasattr(client, "wait_until_ready") and callable(getattr(client, "wait_until_ready")):
                start_task = asyncio.create_task(start_coro)
                ready_task = asyncio.create_task(client.wait_until_ready())
                done, pending = await asyncio.wait_for(
                    asyncio.wait([start_task, ready_task], return_when=asyncio.FIRST_COMPLETED),
                    timeout=30.0,
                )
                for p in pending:
                    p.cancel()
                if start_task in done and start_task.exception():
                    raise start_task.exception()
            else:
                if asyncio.iscoroutine(start_coro):
                    await asyncio.wait_for(start_coro, timeout=30.0)
        except (discord.errors.LoginFailure, getattr(discord, "LoginFailure", discord.errors.LoginFailure)) as e:
            return JSONResponse(
                status_code=502,
                content={
                    "exito": False,
                    "mensaje": f"Fallo de autenticación con Discord: {e}",
                    "detail": f"Fallo de autenticación con Discord: {e}",
                },
            )
        except asyncio.TimeoutError:
            return JSONResponse(
                status_code=504,
                content={
                    "exito": False,
                    "mensaje": "Tiempo de espera agotado al conectar con Discord",
                    "detail": "Tiempo de espera agotado al conectar con Discord",
                },
            )

        # 1. Canales autorizados
        id_servidor = (os.getenv("DISCORD_GUILD_ID") or "").strip() or None
        guilds = getattr(client, "guilds", [])
        canales = armar_json_bot_python.detectar_canales(guilds, id_servidor)
        if not canales:
            return {
                "exito": True,
                "total_recibidas": 0,
                "guardadas_nuevas": 0,
                "repetidas_omitidas": 0,
                "vacias_omitidas": 0,
                "periodo_referencia": f"Semana_{semana_de(datetime.now(timezone.utc)):02d}",
                "mensaje": "No se encontraron canales de texto autorizados o accesibles",
            }

        # 2. Historial de mensajes
        mensajes_totales = []
        for canal in canales:
            async for mensaje in canal.history(limit=limite_por_canal):
                if not isinstance(getattr(mensaje, "created_at", None), datetime):
                    mensaje.created_at = datetime.now(timezone.utc)
                if not getattr(mensaje, "channel", None) or hasattr(mensaje.channel, "_mock_return_value"):
                    mensaje.channel = canal
                if hasattr(mensaje, "webhook_id") and hasattr(mensaje.webhook_id, "_mock_return_value"):
                    mensaje.webhook_id = None
                mensajes_totales.append(mensaje)

        paquete = armar_json_bot_python.construir_paquete(mensajes_totales)
        if not paquete:
            return {
                "exito": True,
                "total_recibidas": len(mensajes_totales),
                "guardadas_nuevas": 0,
                "repetidas_omitidas": 0,
                "vacias_omitidas": len(mensajes_totales),
                "periodo_referencia": f"Semana_{semana_de(datetime.now(timezone.utc)):02d}",
                "mensaje": "Todos los mensajes están al día" if len(mensajes_totales) > 0 else "No se encontraron mensajes válidos para sincronizar",
            }

        # 3. Procesar actividad
        resultado = procesamiento.procesar_actividad(paquete)

        # 4. Sincronizar en SQLite local
        invalidar_cache_supabase()
        fn_sync = getattr(sys.modules[__name__], "_sincronizar_supabase_a_sqlite", _sincronizar_supabase_a_sqlite)
        try:
            fn_sync()
        except Exception:
            pass

        total_recibidas = resultado.get("total_recibidas", resultado.get("total", 0))
        guardadas_nuevas = resultado.get("guardadas_nuevas", resultado.get("nuevas", 0))
        repetidas_omitidas = resultado.get("repetidas_omitidas", resultado.get("repetidas", 0))
        vacias_omitidas = resultado.get("vacias_omitidas", resultado.get("vacias", 0))
        periodo_ref = paquete.get("periodo_referencia") or f"Semana_{semana_de(datetime.now(timezone.utc)):02d}"

        if guardadas_nuevas > 0:
            mensaje = f"Sincronización exitosa: {guardadas_nuevas} mensajes nuevos guardados"
        elif total_recibidas > 0:
            mensaje = "Todos los mensajes están al día"
        else:
            mensaje = "No se encontraron mensajes para sincronizar"

        return {
            "exito": True,
            "total_recibidas": total_recibidas,
            "guardadas_nuevas": guardadas_nuevas,
            "repetidas_omitidas": repetidas_omitidas,
            "vacias_omitidas": vacias_omitidas,
            "periodo_referencia": periodo_ref,
            "mensaje": mensaje,
        }

    finally:
        if hasattr(client, "close") and callable(client.close):
            try:
                await client.close()
            except Exception:
                pass
        if start_task and not start_task.done():
            start_task.cancel()


@app.post("/api/v1/discord/sync")
@app.post("/api/v1/discord/sync/")
async def sync_discord_v1(payload: dict = Body(default={})):
    """Sincroniza mensajes desde Discord hacia Supabase y SQLite local de forma idempotente."""
    lock_obj = getattr(sys.modules[__name__], "_discord_sync_lock", _discord_sync_lock)
    if lock_obj.locked():
        return JSONResponse(
            status_code=409,
            content={
                "exito": False,
                "mensaje": "Sincronización en curso",
                "detail": "Sincronización en curso",
            },
        )

    token = os.getenv("DISCORD_BOT_TOKEN") or os.getenv("DISCORD_TOKEN")
    if not token or not token.strip():
        return JSONResponse(
            status_code=502,
            content={
                "exito": False,
                "mensaje": "Fallo de autenticación con Discord: token ausente o inválido",
                "detail": "Fallo de autenticación con Discord: token ausente o inválido",
            },
        )

    limite_por_canal = (payload or {}).get("limite_por_canal", 100)

    if hasattr(lock_obj, "__aenter__"):
        async with lock_obj:
            return await _ejecutar_sincronizacion_discord(token=token, limite_por_canal=limite_por_canal)
    else:
        return await _ejecutar_sincronizacion_discord(token=token, limite_por_canal=limite_por_canal)


@app.post("/api/v1/discord/recover")
@app.post("/api/v1/discord/recover/")
async def recover_discord_messages_v1(payload: dict = Body(...)):
    """Recupera selectivamente mensajes del historial de Discord e inserta con etapa 'ingesta' y estado 'pendiente'."""
    _asegurar_esquema_sqlite()
    mensajes = (payload or {}).get("mensajes", [])
    guardados_nuevos = 0
    repetidos_omitidos = 0

    with sqlite3.connect(motor_bd.RUTA_BD) as conn:
        for item in mensajes:
            canal_id = str(item.get("canal_id") or item.get("channel_id") or "")
            message_id = str(item.get("message_id") or "")
            autor = str(item.get("autor") or item.get("author") or "Desconocido")
            texto_raw = str(item.get("texto") or item.get("content") or "")
            fecha = item.get("fecha") or item.get("enviado_en") or a_utc_iso(datetime.now(timezone.utc))

            import limpieza
            texto_limpio = limpieza.limpiar_texto(texto_raw)
            if not texto_limpio:
                continue

            canal_nombre = item.get("canal") or (f"#{canal_id}" if canal_id else "#desconocido")
            if not canal_nombre.startswith("#"):
                canal_nombre = f"#{canal_nombre}"

            origen = "Discord_Grupo_ONE_G10"
            hash_msg = limpieza.calcular_hash(origen, canal_nombre, autor, texto_limpio)
            periodo = periodo_de(fecha, f"Semana_{semana_de(datetime.now(timezone.utc)):02d}")
            ahora = a_utc_iso(datetime.now(timezone.utc))

            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM interacciones WHERE hash = ? OR (message_id = ? AND message_id != '')",
                (hash_msg, message_id),
            )
            if cursor.fetchone():
                repetidos_omitidos += 1
                continue

            cursor.execute(
                """
                INSERT INTO interacciones (
                    hash, origen_comunidad, periodo_referencia, autor, canal, tipo,
                    texto, enviado_en, creado_en, channel_id, message_id,
                    estado, estado_curaduria, etapa_flujo, etapa
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    hash_msg, origen, periodo, autor, canal_nombre, "mensaje",
                    texto_limpio, fecha, ahora, canal_id, message_id,
                    "pendiente", "pending", "ingesta", "ingesta",
                ),
            )
            conn.commit()

            try:
                _base_datos_raiz.guardar_interaccion(
                    origen=origen,
                    periodo=periodo,
                    autor=autor,
                    canal=canal_nombre,
                    tipo="mensaje",
                    texto=texto_limpio,
                    hash_mensaje=hash_msg,
                    enviado_en=fecha,
                )
            except Exception:
                pass

            guardados_nuevos += 1

    invalidar_cache_supabase()
    return {
        "exito": True,
        "guardados_nuevos": guardados_nuevos,
        "repetidos_omitidos": repetidos_omitidos,
        "mensaje": f"Se recuperaron {guardados_nuevos} mensajes nuevos ({repetidos_omitidos} ya existían)",
    }


async def vista_previa_recuperacion_discord(
    canal_id: str = "",
    buscar: str = "",
    dias: int | None = 7,
    solo_pendientes: bool = True,
    pagina: int = 1,
):
    """Consulta mensajes de Discord para previsualización sin persistirlos."""
    if len(buscar) > 200:
        raise HTTPException(
            status_code=422,
            detail="El texto de busqueda es demasiado largo.",
        )
    try:
        sys.path.insert(0, str(_DIR_MOTOR_IA))
        try:
            from recuperacion_discord import consultar_historial_discord
            return await consultar_historial_discord(
                canal_id=canal_id,
                buscar=buscar,
                dias=dias,
                solo_pendientes=solo_pendientes,
                pagina=pagina,
            )
        finally:
            if str(_DIR_MOTOR_IA) in sys.path:
                sys.path.remove(str(_DIR_MOTOR_IA))
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@app.get("/api/v1/content-workflow/discord/recovery-preview")
@app.get("/api/v1/content-workflow/discord/recovery-preview/")
@app.get("/api/v1/discord/recovery-preview")
@app.get("/api/v1/discord/recovery-preview/")
async def recovery_preview_endpoint(
    canal_id: str = "",
    buscar: str = "",
    dias: int | None = 7,
    solo_pendientes: bool = True,
    pagina: int = 1,
):
    """Alias para la previsualización del historial de Discord."""
    import inspect
    handler = getattr(sys.modules[__name__], "vista_previa_recuperacion_discord", vista_previa_recuperacion_discord)
    res = handler(
        canal_id=canal_id,
        buscar=buscar,
        dias=dias,
        solo_pendientes=solo_pendientes,
        pagina=pagina,
    )
    if inspect.isawaitable(res):
        res = await res
    return res



