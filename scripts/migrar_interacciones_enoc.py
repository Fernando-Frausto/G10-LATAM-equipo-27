"""
Script de Migración Idempotente y Ejecución Segura — Spec 022
Migra la tabla public.interacciones de la cuenta de Tania a la de Enoc en Supabase.

Cumple con:
- RF-01: Estructura canónica DDL de 11 columnas e índice UNIQUE sobre hash.
- RF-02: Transferencia idempotente (ON CONFLICT (hash) DO NOTHING), Pre-Flight y Post-Flight checks de 204 registros.
- RF-03: Cero secretos en código duro (Regla Constitucional 4), carga exclusiva de variables de entorno.
- RF-05: Inviolabilidad de archivos protegidos y no afectación de velocidad.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Sequence

from dotenv import load_dotenv
import psycopg2
import psycopg2.extras

# Configurar logging legible y estructurado
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("migrador_enoc")

# ==============================================================================
# Constantes Canónicas DDL y SQL (Spec 022 - RF-01, RF-02, RF-03)
# ==============================================================================

DDL_INTERACCIONES = """
CREATE TABLE IF NOT EXISTS public.interacciones (
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
CREATE UNIQUE INDEX IF NOT EXISTS idx_interacciones_hash ON public.interacciones(hash);
"""

SQL_INSERT_INTERACCIONES = """
INSERT INTO public.interacciones (
    id, hash, origen_comunidad, periodo_referencia, autor, canal, tipo, texto, enviado_en, estado, creado_en
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
) ON CONFLICT (hash) DO NOTHING;
"""

SQL_SYNC_SECUENCIA = """
SELECT setval('interacciones_id_seq', COALESCE((SELECT MAX(id) FROM interacciones), 1), (SELECT COUNT(*) > 0 FROM interacciones));
"""


# ==============================================================================
# Funciones Auxiliares Exportadas (Spec 022)
# ==============================================================================

def obtener_ddl_interacciones() -> str:
    """Retorna la sentencia canónica DDL para la tabla public.interacciones e índice UNIQUE."""
    return DDL_INTERACCIONES


def crear_tabla_interacciones_enoc(conexion_enoc) -> None:
    """
    Crea la tabla public.interacciones y su índice UNIQUE sobre hash en Enoc si no existen.
    Acepta una conexión psycopg2 o una cadena de conexión.
    """
    if isinstance(conexion_enoc, str):
        with psycopg2.connect(conexion_enoc, connect_timeout=15) as conn:
            with conn.cursor() as cur:
                cur.execute(DDL_INTERACCIONES)
            conn.commit()
    else:
        with conexion_enoc.cursor() as cur:
            cur.execute(DDL_INTERACCIONES)
        conexion_enoc.commit()


def validar_paridad_hashes(
    hashes_origen: Sequence[str] | set[str],
    hashes_destino: Sequence[str] | set[str],
    retornar_diferencia: bool = False,
) -> bool | tuple[bool, set[str]]:
    """
    Valida la paridad de integridad estricta entre el conjunto de hashes de origen y destino.
    Verifica que:
    1. Ambos conjuntos tengan exactamente 204 elementos.
    2. La diferencia simétrica de conjuntos sea estrictamente vacía.

    Retorna un booleano (o una tupla (coinciden, diferencia) si retornar_diferencia=True).
    """
    set_orig = set(hashes_origen)
    set_dest = set(hashes_destino)

    cantidad_origen_ok = len(hashes_origen) == 204 and len(set_orig) == 204
    cantidad_destino_ok = len(hashes_destino) == 204 and len(set_dest) == 204
    conjuntos_identicos = (set_orig == set_dest)

    coinciden = bool(cantidad_origen_ok and cantidad_destino_ok and conjuntos_identicos)
    diferencia = set_orig ^ set_dest

    if retornar_diferencia:
        return coinciden, diferencia
    return coinciden


def obtener_url_origen() -> str:
    """
    Obtiene la URL de conexión a la base de datos de origen (Tania).
    Prioriza TANIA_DATABASE_URL y recurre a DATABASE_URL si contiene 'ietgilhtccvqlqglqazf'.
    """
    load_dotenv()
    url = os.environ.get("TANIA_DATABASE_URL")
    if not url:
        db_url = os.environ.get("DATABASE_URL", "")
        if "ietgilhtccvqlqglqazf" in db_url:
            url = db_url
    if not url:
        raise ValueError(
            "No se encontró la URL de la base de datos de origen de Tania en variables de entorno (TANIA_DATABASE_URL o DATABASE_URL)."
        )
    return url


def obtener_url_destino() -> str:
    """
    Obtiene la URL de conexión a la base de datos de destino (Enoc).
    Prioriza SUPABASE_DB_URL o DATABASE_URL si contiene 'swdoucawdasxmnomlcfu'.
    """
    load_dotenv()
    url = os.environ.get("SUPABASE_DB_URL")
    if not url or "swdoucawdasxmnomlcfu" not in url:
        db_url = os.environ.get("DATABASE_URL", "")
        if "swdoucawdasxmnomlcfu" in db_url:
            url = db_url
    if not url:
        raise ValueError(
            "No se encontró la URL de la base de datos de destino de Enoc en variables de entorno (SUPABASE_DB_URL o DATABASE_URL)."
        )
    return url


def ejecutar_migracion_completa(
    url_origen: str | None = None,
    url_destino: str | None = None,
) -> dict:
    """
    Orquesta la migración completa e idempotente de los 204 registros históricos de interacciones:
    1. Pre-flight check: valida 204 registros en Tania y extrae el conjunto de hashes.
    2. Creación canónica de tabla e índice UNIQUE en Supabase Enoc.
    3. Transferencia por lotes con ON CONFLICT (hash) DO NOTHING preservando IDs originales.
    4. Post-flight check: valida 204 registros en Enoc y paridad del 100% de hashes.
    5. Sincronización defensiva de la secuencia interacciones_id_seq.
    """
    origen = url_origen or obtener_url_origen()
    destino = url_destino or obtener_url_destino()

    logger.info("=== INICIO DE PROTOCOLO DE MIGRACIÓN SUPABASE (Spec 022) ===")

    # 1. Pre-Flight Check en Tania
    logger.info("1/5. Ejecutando Pre-Flight Check en origen (Tania)...")
    with psycopg2.connect(origen, connect_timeout=15) as conn_tania:
        with conn_tania.cursor() as cur_tania:
            cur_tania.execute("SELECT COUNT(*) FROM public.interacciones;")
            total_tania = cur_tania.fetchone()[0]

            if total_tania != 204:
                raise RuntimeError(
                    f"Pre-flight fallido: Tania contiene {total_tania} registros (se requerían exactamente 204). Migración abortada."
                )

            cur_tania.execute("""
                SELECT id, hash, origen_comunidad, periodo_referencia, autor, canal, tipo, texto, enviado_en, estado, creado_en
                FROM public.interacciones
                ORDER BY id ASC;
            """)
            filas_tania = cur_tania.fetchall()
            hashes_tania = [f[1] for f in filas_tania]

    logger.info(f"     Pre-Flight exitoso: {len(filas_tania)} registros y {len(set(hashes_tania))} hashes únicos verificados.")

    # 2. Conectar a Enoc y crear tabla
    logger.info("2/5. Creando estructura DDL canónica en destino (Enoc)...")
    with psycopg2.connect(destino, connect_timeout=15) as conn_enoc:
        crear_tabla_interacciones_enoc(conn_enoc)
        logger.info("     Tabla public.interacciones e índice idx_interacciones_hash verificados en Enoc.")

        # 3. Transferencia por lotes idempotente
        logger.info(f"3/5. Transfiriendo {len(filas_tania)} registros por lotes a Enoc...")
        with conn_enoc.cursor() as cur_enoc:
            psycopg2.extras.execute_batch(
                cur_enoc,
                SQL_INSERT_INTERACCIONES,
                filas_tania,
                page_size=100,
            )
        conn_enoc.commit()
        logger.info("     Transferencia por lotes finalizada.")

        # 4. Post-Flight Check en Enoc
        logger.info("4/5. Ejecutando Post-Flight Check en Enoc...")
        with conn_enoc.cursor() as cur_enoc:
            cur_enoc.execute("SELECT COUNT(*) FROM public.interacciones;")
            total_enoc = cur_enoc.fetchone()[0]

            cur_enoc.execute("SELECT hash FROM public.interacciones ORDER BY id ASC;")
            hashes_enoc = [r[0] for r in cur_enoc.fetchall()]

            coinciden, diferencia = validar_paridad_hashes(hashes_tania, hashes_enoc, retornar_diferencia=True)

            if total_enoc != 204 or not coinciden:
                raise RuntimeError(
                    f"Post-flight fallido: Enoc contiene {total_enoc} registros (se requerían 204). Diferencia de hashes: {diferencia}. Migración abortada."
                )

            # 5. Sincronización de secuencia autoincremental
            logger.info("5/5. Sincronizando secuencia autoincremental 'interacciones_id_seq'...")
            cur_enoc.execute(SQL_SYNC_SECUENCIA)
            res_seq = cur_enoc.fetchone()
            val_seq = res_seq[0] if res_seq else None

        conn_enoc.commit()
        logger.info(f"     Secuencia interacciones_id_seq ajustada a valor: {val_seq}")

    logger.info("=== MIGRACIÓN COMPLETADA EXITOSAMENTE AL 100% ===")
    return {
        "exito": True,
        "pre_flight_count": total_tania,
        "post_flight_count": total_enoc,
        "total_migrados": len(filas_tania),
        "paridad_hashes": coinciden,
        "secuencia_sincronizada": val_seq,
    }


if __name__ == "__main__":
    try:
        reporte = ejecutar_migracion_completa()
        print("\n" + "=" * 60)
        print("REPORTE DE MIGRACIÓN SUPABASE ENOC (Spec 022)")
        print("=" * 60)
        print(f"Estado general:           {'EXITOSO' if reporte['exito'] else 'FALLIDO'}")
        print(f"Registros en Origen (Tania): {reporte['pre_flight_count']}")
        print(f"Registros en Destino (Enoc): {reporte['post_flight_count']}")
        print(f"Total filas transferidas:    {reporte['total_migrados']}")
        print(f"Paridad de hashes al 100%:   {'SÍ' if reporte['paridad_hashes'] else 'NO'}")
        print(f"Secuencia ID sincronizada:   {reporte['secuencia_sincronizada']}")
        print("=" * 60 + "\n")
    except Exception as exc:
        logger.error(f"Error fatal durante la migración: {exc}", exc_info=True)
        sys.exit(1)
