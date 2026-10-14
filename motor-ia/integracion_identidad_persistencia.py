"""Integracion controlada de identidad y preparacion de resultados."""

from base_datos import obtener_interaccion, obtener_identidad_interaccion
from validador_hash_local import validar_integridad_hash
from puente_identidad import resolver_identidad_supabase
from persistencia_supabase_segura import preparar_registro_supabase


def preparar_desde_identidad_local(
    id_local: int,
    datos_ia: dict,
    decision: str,
) -> dict:
    """Prepara datos solo si el puente confirma una identidad."""
    if type(id_local) is not int or id_local <= 0:
        raise ValueError("El ID local debe ser positivo.")

    if not isinstance(datos_ia, dict):
        raise TypeError("Los datos de IA deben ser un diccionario.")

    identidad = resolver_identidad_supabase(id_local)

    if identidad.get("id_local") != id_local:
        raise ValueError("La identidad local no coincide.")

    if identidad.get("estado") != "correspondencia_encontrada":
        raise ValueError("No existe identidad Supabase confirmada.")

    id_supabase = identidad.get("id_supabase")

    if type(id_supabase) is not int or id_supabase <= 0:
        raise ValueError("El ID Supabase confirmado no es valido.")

    if "id_mensaje" in datos_ia:
        raise ValueError("No se acepta id_mensaje externo.")

    if "id_supabase" in datos_ia:
        raise ValueError("No se acepta id_supabase externo.")

    if "identidad_validada" in datos_ia:
        raise ValueError("No se acepta identidad_validada externa.")

    interaccion = obtener_interaccion(id_local)

    if interaccion is None:
        raise ValueError("No se encontro la interaccion local.")

    identidad_local = obtener_identidad_interaccion(id_local)

    if identidad_local is None:
        raise ValueError("No se encontro la identidad local.")

    if not validar_integridad_hash(interaccion, identidad_local):
        raise ValueError("La integridad SHA-256 del mensaje no coincide.")

    texto_local = interaccion.get("texto")
    texto_recibido = datos_ia.get("texto_original")

    if not isinstance(texto_local, str):
        raise ValueError("El texto local no es valido.")

    if not isinstance(texto_recibido, str):
        raise ValueError("Se requiere texto_original.")

    if texto_recibido != texto_local:
        raise ValueError("El texto no coincide con SQLite.")

    autor_local = interaccion.get("autor")
    canal_local = interaccion.get("canal")

    if not isinstance(autor_local, str) or not autor_local:
        raise ValueError("El autor local no es valido.")

    if not isinstance(canal_local, str) or not canal_local:
        raise ValueError("El canal local no es valido.")

    if datos_ia.get("autor") != autor_local:
        raise ValueError("El autor no coincide con SQLite.")

    if datos_ia.get("canal_origen") != canal_local:
        raise ValueError("El canal no coincide con SQLite.")

    registro = dict(datos_ia)
    registro["id_supabase"] = id_supabase
    registro["identidad_validada"] = True

    return preparar_registro_supabase(registro, decision)