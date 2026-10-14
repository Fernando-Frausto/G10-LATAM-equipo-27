"""Puente seguro entre la identidad SQLite y la identidad Supabase."""

from base_datos import obtener_identidad_interaccion
from adaptador_supabase import buscar_id_supabase


def resolver_identidad_supabase(id_local: int) -> dict:
    """Resuelve una identidad sin habilitar conexiones externas."""
    identidad = obtener_identidad_interaccion(id_local)

    if identidad is None:
        return {
            "id_local": id_local,
            "id_supabase": None,
            "estado": "interaccion_local_no_encontrada",
        }

    resultado = buscar_id_supabase(
        identidad["hash"],
        permitir_conexion=False,
    )

    return {
        "id_local": identidad["id"],
        "id_supabase": resultado.get("id_supabase"),
        "estado": resultado.get("motivo"),
    }