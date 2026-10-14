import os
from datetime import datetime, timezone
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

from periodos import a_utc_iso

load_dotenv()

def obtener_conexion():
    """Retorna una conexión segura a PostgreSQL (Supabase) usando variables de entorno."""
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return psycopg2.connect(database_url, sslmode="require")

    host = os.getenv("DB_HOST")
    password = os.getenv("DB_PASSWORD")
    if not host or not password:
        raise ValueError(
            "Faltan las credenciales de PostgreSQL/Supabase en el archivo .env "
            "(se requiere DATABASE_URL o la combinación de DB_HOST y DB_PASSWORD)."
        )

    # Si no existe DATABASE_URL, usa las variables separadas (ninguna con contraseñas quemadas)
    return psycopg2.connect(
        host=host,
        database=os.getenv("DB_NAME", "postgres"),
        user=os.getenv("DB_USER"),
        password=password,
        port=os.getenv("DB_PORT", "6543"),
        sslmode="require",
    )

def crear_tabla() -> None:
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            # el campo hash es UNIQUE: si intento guardar un mensaje repetido, la base lo ignora.
            # "estado" es el que van a usar después las demás etapas (pendiente, analizado, etc.)
            # En Postgres usamos SERIAL en vez de AUTOINCREMENT
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS interacciones (
                    id SERIAL PRIMARY KEY,
                    hash VARCHAR(128) UNIQUE NOT NULL,
                    origen_comunidad VARCHAR(100) NOT NULL,
                    periodo_referencia VARCHAR(100) NOT NULL,
                    autor VARCHAR(100) NOT NULL,
                    canal VARCHAR(100) NOT NULL,
                    tipo VARCHAR(50),
                    texto TEXT NOT NULL,
                    enviado_en VARCHAR(100),
                    estado VARCHAR(50) NOT NULL DEFAULT 'pendiente',
                    creado_en VARCHAR(100) NOT NULL
                );
                """
            )
        conexion.commit()
    finally:
        conexion.close()


def guardar_interaccion(
    origen, periodo, autor, canal, tipo, texto, hash_mensaje, enviado_en=None
) -> bool:
    """Guarda un mensaje. Regresa True si era nuevo y False si ya existía (repetido)."""
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            # antes usaba INSERT directo/ignorar, pero eso gasta un id
            # incluso cuando el mensaje ya existía (el contador avanza aunque el
            # insert se descarte). Por eso primero pregunto si el hash ya existe, y solo
            # si no existe hago el INSERT: así el id solo sube con mensajes de verdad nuevos
            cursor.execute(
                "SELECT 1 FROM interacciones WHERE hash = %s;", (hash_mensaje,)
            )
            if cursor.fetchone():
                return False

            cursor.execute(
                """
                INSERT INTO interacciones
                (hash, origen_comunidad, periodo_referencia, autor, canal, tipo, texto, enviado_en, creado_en)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
                """,
                (
                    hash_mensaje,
                    origen,
                    periodo,
                    autor,
                    canal,
                    tipo,
                    texto,
                    enviado_en,
                    # cuándo lo guardó el bot (la "llamada"). En UTC y con el mismo formato que
                    # enviado_en, para que no dependa del reloj de la máquina donde corra (PC o Colab)
                    a_utc_iso(datetime.now(timezone.utc)),
                ),
            )
        conexion.commit()
        return True
    finally:
        conexion.close()


def _corte_utc(corte) -> str:
    """Convierte un corte de fecha (texto ISO o datetime) al formato exacto en que se guarda

    enviado_en. Es necesario porque el filtro compara las fechas como texto: si el corte
    llegara en otro formato (por ejemplo con otra zona horaria), compararía mal y sin avisar.
    Una fecha sin zona horaria se toma como UTC. Si el texto no es una fecha, lanza ValueError.
    """
    if isinstance(corte, str):
        corte = datetime.fromisoformat(corte)
    return a_utc_iso(corte)


def es_mensaje_bot_o_webhook(item: dict) -> bool:
    """Determina si un registro corresponde a un bot o webhook de Discord."""
    autor = (item.get("autor") or "").strip()
    tipo = (item.get("tipo") or "").strip().lower()
    if autor == "Spidey Boy#0000":
        return True
    if "bot" in autor.lower():
        return True
    if autor.endswith("#0000"):
        return True
    if tipo in ("bot", "webhook"):
        return True
    return False


def listar_interacciones(
    canal=None, estado=None, limite=100, desde_utc=None, hasta_utc=None, incluir_bots=False
) -> list:
    """Regresa las interacciones guardadas como lista de diccionarios (las más recientes primero).

    desde_utc y hasta_utc filtran por enviado_en, la fecha real de envío en Discord:
    desde_utc SÍ incluye ese instante y hasta_utc NO lo incluye, así dos periodos seguidos
    no repiten ni se saltan mensajes. Con limite=None no hay tope de mensajes. Los mensajes
    sin fecha (paquetes armados a mano) no aparecen cuando se filtra por fechas.
    incluir_bots=False excluye por defecto mensajes de bots y webhooks.
    """
    conexion = obtener_conexion()
    try:
        # RealDictCursor devuelve cada fila directamente como un diccionario con sus nombres de columna
        with conexion.cursor(cursor_factory=RealDictCursor) as cursor:
            # no incluyo el hash porque es un dato interno que a mis compañeros no les sirve
            consulta = (
                "SELECT id, origen_comunidad, periodo_referencia, autor, canal,"
                " tipo, texto, enviado_en, estado, creado_en FROM"
                " interacciones"
            )
            condiciones = []
            parametros = []
            if canal:
                condiciones.append("canal = %s")
                parametros.append(canal)
            if estado:
                condiciones.append("estado = %s")
                parametros.append(estado)
            if desde_utc:
                condiciones.append("enviado_en >= %s")
                parametros.append(_corte_utc(desde_utc))
            if hasta_utc:
                condiciones.append("enviado_en < %s")
                parametros.append(_corte_utc(hasta_utc))

            if not incluir_bots:
                condiciones.append("autor != 'Spidey Boy#0000'")
                condiciones.append("autor NOT ILIKE '%%bot%%'")
                condiciones.append("autor NOT LIKE '%%#0000'")
                condiciones.append("(tipo IS NULL OR tipo NOT IN ('bot', 'webhook'))")

            if condiciones:
                consulta += " WHERE " + " AND ".join(condiciones)
            consulta += " ORDER BY id DESC"
            if limite is not None:
                consulta += " LIMIT %s"
                parametros.append(limite)

            cursor.execute(consulta, parametros)
            filas = cursor.fetchall()
            interacciones = [dict(fila) for fila in filas]
            if not incluir_bots:
                interacciones = [f for f in interacciones if not es_mensaje_bot_o_webhook(f)]
            return interacciones
    finally:
        conexion.close()


def obtener_conexion_copywriting():
    """Retorna una conexión segura al PostgreSQL (Supabase) de Copywriting usando SUPABASE_DB_URL."""
    url_copy = os.getenv("SUPABASE_DB_URL")
    if not url_copy:
        raise ValueError(
            "Falta la variable SUPABASE_DB_URL en el archivo .env para conectar con el Supabase de Copywriting."
        )
    return psycopg2.connect(url_copy, sslmode="require")


def crear_tabla_lotes_ia() -> None:
    """Crea la tabla lotes_ia_kpis en el Supabase de Copywriting si no existe."""
    conexion = obtener_conexion_copywriting()
    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS lotes_ia_kpis (
                    id SERIAL PRIMARY KEY,
                    id_mensaje INTEGER UNIQUE NOT NULL,
                    autor TEXT NOT NULL,
                    canal_origen VARCHAR(100),
                    comunidad VARCHAR(100),
                    semana VARCHAR(100),
                    fecha_envio VARCHAR(100),
                    fecha_extraccion VARCHAR(100),
                    modelo_ia VARCHAR(100),
                    texto_original TEXT NOT NULL,
                    relevancia INTEGER NOT NULL,
                    sentimiento VARCHAR(50),
                    temas_clave TEXT,
                    segmento TEXT,
                    razonamiento TEXT,
                    decision_ia VARCHAR(50) NOT NULL,
                    estado_revision VARCHAR(50) NOT NULL DEFAULT 'pendiente',
                    analizado_en VARCHAR(100) NOT NULL
                );
                ALTER TABLE lotes_ia_kpis ADD COLUMN IF NOT EXISTS modelo_ia VARCHAR(100);
                """
            )
        conexion.commit()
    finally:
        conexion.close()


def guardar_lote_ia_supabase(paquete_maestro: dict) -> int:
    """Guarda los mensajes analizados por la IA (aprobados y descartados) en la tabla lotes_ia_kpis del Supabase de Enoc."""
    if not os.getenv("SUPABASE_DB_URL"):
        return 0

    crear_tabla_lotes_ia()
    conexion = obtener_conexion_copywriting()
    ahora_utc = a_utc_iso(datetime.now(timezone.utc))
    total_guardados = 0

    try:
        with conexion.cursor() as cursor:
            for decision, llave in [("aprobado", "aprobados"), ("descartado", "descartados")]:
                for item in paquete_maestro.get(llave, []):
                    kpis = item.get("kpis", {})
                    if decision == "aprobado" or item.get("estado_revision") == "pendiente":
                        estado_revision = "pendiente"
                    else:
                        estado_revision = "rechazado"

                    cursor.execute(
                        """
                        INSERT INTO lotes_ia_kpis (
                            id_mensaje, autor, canal_origen, comunidad, semana,
                            fecha_envio, fecha_extraccion, modelo_ia, texto_original,
                            relevancia, sentimiento, temas_clave, segmento,
                            razonamiento, decision_ia, estado_revision, analizado_en
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id_mensaje) DO UPDATE SET
                            comunidad = COALESCE(EXCLUDED.comunidad, lotes_ia_kpis.comunidad),
                            semana = COALESCE(EXCLUDED.semana, lotes_ia_kpis.semana),
                            fecha_envio = COALESCE(EXCLUDED.fecha_envio, lotes_ia_kpis.fecha_envio),
                            fecha_extraccion = COALESCE(EXCLUDED.fecha_extraccion, lotes_ia_kpis.fecha_extraccion),
                            modelo_ia = COALESCE(EXCLUDED.modelo_ia, lotes_ia_kpis.modelo_ia),
                            relevancia = EXCLUDED.relevancia,
                            sentimiento = EXCLUDED.sentimiento,
                            temas_clave = EXCLUDED.temas_clave,
                            segmento = EXCLUDED.segmento,
                            razonamiento = EXCLUDED.razonamiento,
                            decision_ia = EXCLUDED.decision_ia,
                            estado_revision = EXCLUDED.estado_revision,
                            analizado_en = EXCLUDED.analizado_en
                        WHERE lotes_ia_kpis.estado_revision IN ('pendiente', 'rechazado');
                        """,
                        (
                            item.get("id_mensaje"),
                            item.get("autor", "Desconocido"),
                            item.get("canal_origen"),
                            item.get("comunidad"),
                            item.get("semana"),
                            item.get("fecha_envio"),
                            item.get("fecha_extraccion"),
                            item.get("modelo_ia"),
                            item.get("texto_original", ""),
                            int(kpis.get("relevancia", 0)),
                            kpis.get("sentimiento"),
                            kpis.get("temas_clave"),
                            kpis.get("segmento"),
                            kpis.get("razonamiento"),
                            decision,
                            estado_revision,
                            ahora_utc,
                        ),
                    )
                    total_guardados += 1
        conexion.commit()
        return total_guardados
    finally:
        conexion.close()


def obtener_lote_kpis_supabase() -> dict | None:
    """Consulta los registros de lotes_ia_kpis en Supabase y reconstruye el diccionario canónico.

    Retorna {"aprobados": [...], "descartados": [...]} o None si no hay conexión o registros.
    """
    url_copy = os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL")
    if not url_copy:
        return None

    try:
        try:
            conexion = obtener_conexion_copywriting()
        except Exception:
            conexion = obtener_conexion()

        try:
            with conexion.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT id, id_mensaje, autor, canal_origen, comunidad, semana,
                           fecha_envio, fecha_extraccion, modelo_ia, texto_original,
                           relevancia, sentimiento, temas_clave, segmento,
                           razonamiento, decision_ia, estado_revision, analizado_en
                    FROM lotes_ia_kpis
                    ORDER BY id_mensaje ASC;
                    """
                )
                filas = cursor.fetchall()
                if not filas:
                    return {"aprobados": [], "descartados": []}

                aprobados = []
                descartados = []
                for f in filas:
                    fila_dict = dict(f)
                    item = {
                        "id_mensaje": fila_dict.get("id_mensaje"),
                        "autor": fila_dict.get("autor"),
                        "canal_origen": fila_dict.get("canal_origen"),
                        "comunidad": fila_dict.get("comunidad"),
                        "semana": fila_dict.get("semana"),
                        "fecha_envio": fila_dict.get("fecha_envio"),
                        "fecha_extraccion": fila_dict.get("fecha_extraccion"),
                        "modelo_ia": fila_dict.get("modelo_ia"),
                        "texto_original": fila_dict.get("texto_original", ""),
                        "decision_ia": fila_dict.get("decision_ia"),
                        "estado_revision": fila_dict.get("estado_revision"),
                        "kpis": {
                            "relevancia": fila_dict.get("relevancia", 0),
                            "sentimiento": fila_dict.get("sentimiento", "Neutral"),
                            "temas_clave": fila_dict.get("temas_clave", "N/A"),
                            "segmento": fila_dict.get("segmento", "N/A"),
                            "razonamiento": fila_dict.get("razonamiento", ""),
                        },
                    }
                    estado = str(fila_dict.get("estado_revision") or "").strip().lower()
                    decision_ia = str(fila_dict.get("decision_ia") or "").strip().lower()

                    if estado in ("aprobado", "procesado"):
                        es_aprobado = True
                    elif estado in ("desaprobado", "rechazado"):
                        es_aprobado = False
                    elif estado == "pendiente":
                        es_aprobado = True
                    else:
                        # Fallback retrocompatible para registros antiguos
                        es_aprobado = (decision_ia == "aprobado")

                    if es_aprobado:
                        item["copy_final"] = fila_dict.get("copy_final") or "Pendiente de redacción por Enoc..."
                        aprobados.append(item)
                    else:
                        descartados.append(item)

                return {"aprobados": aprobados, "descartados": descartados}
        finally:
            conexion.close()
    except Exception:
        return None


def obtener_ultimo_reporte_semanal_supabase() -> dict | None:
    """Consulta la tabla historial_reportes_semanales en Supabase y retorna el reporte más reciente.

    Retorna el diccionario del reporte o None si no existe o ante error.
    """
    url_copy = os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL")
    if not url_copy:
        return None

    try:
        try:
            conexion = obtener_conexion_copywriting()
        except Exception:
            conexion = obtener_conexion()

        try:
            with conexion.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT reporte_completo, etiqueta
                    FROM historial_reportes_semanales
                    ORDER BY id DESC
                    LIMIT 1;
                    """
                )
                fila = cursor.fetchone()
                if not fila:
                    return None

                reporte = fila.get("reporte_completo")
                if isinstance(reporte, str):
                    import json
                    return json.loads(reporte)
                elif isinstance(reporte, dict):
                    return reporte
                return dict(fila)
        finally:
            conexion.close()
    except Exception:
        return None
