import json
import importlib
from typing import Callable, Optional, List, Dict, Any
import base_datos


def evaluar_lote(
    mensajes: List[Dict[str, Any]],
    nombre_modulo_cerebro: str,
    nombre_cerebro_legible: str,
    limite: Optional[int] = None,
    callback_progreso: Optional[Callable[[int, int], None]] = None,
    ruta_salida_json: str = "resultados_kpis.json",
) -> Dict[str, Any]:
    """Evalúa un lote de mensajes de Discord utilizando un motor de inferencia de IA.

    Clasifica los mensajes según su relevancia (>= 70 aprobados, < 70 descartados),
    proporciona tolerancia y resiliencia ante excepciones por mensaje individual,
    protege el archivo persistente ante fallo total (100% de errores), y sincroniza
    los resultados exitosos con Supabase.
    """
    if not mensajes:
        return {
            "exito": True,
            "total_evaluados": 0,
            "exitosos": 0,
            "fallidos": 0,
            "guardados_supabase": 0,
            "errores": [],
            "aprobados": [],
            "descartados": [],
            "resultados": {"aprobados": [], "descartados": []},
        }

    # 1. Recortar según límite
    mensajes_a_procesar = mensajes[:limite] if limite is not None else mensajes
    total = len(mensajes_a_procesar)

    # 2. Cargar dinámicamente el módulo de IA
    modulo_cerebro = importlib.import_module(nombre_modulo_cerebro)
    try:
        importlib.reload(modulo_cerebro)
    except Exception:
        # Si reload falla por cualquier motivo, mantener la instancia importada
        pass

    aprobados = []
    descartados = []
    exitosos = []
    fallidos = []
    errores = []

    # 3. Bucle de inferencia con try/except individual
    for idx, msg in enumerate(mensajes_a_procesar):
        try:
            respuesta = modulo_cerebro.cadena.invoke(
                {"texto": msg.get("texto", ""), "canal": msg.get("canal", "")}
            )

            if hasattr(respuesta, "model_dump"):
                kpis = respuesta.model_dump()
            elif hasattr(respuesta, "dict"):
                kpis = respuesta.dict()
            else:
                kpis = dict(respuesta)

            dato = {
                "id_mensaje": msg.get("id"),
                "autor": msg.get("autor"),
                "canal_origen": msg.get("canal"),
                "comunidad": msg.get("origen_comunidad"),
                "fecha_envio": msg.get("enviado_en"),
                "fecha_extraccion": msg.get("creado_en"),
                "semana": msg.get("periodo_referencia"),
                "modelo_ia": nombre_cerebro_legible,
                "texto_original": msg.get("texto"),
                "kpis": kpis,
            }

            if int(kpis.get("relevancia", 0)) >= 70:
                dato["estado_revision"] = "pendiente"
                aprobados.append(dato)
            else:
                dato["estado_revision"] = "rechazado"
                descartados.append(dato)

            exitosos.append(dato)

        except Exception as e:
            error_str = str(e)
            fallidos.append({"id": msg.get("id"), "error": error_str})
            errores.append(error_str)

        finally:
            if callback_progreso is not None:
                callback_progreso(idx + 1, total)

    # 4. Resiliencia y persistencia
    guardados_supabase = 0
    paquete_maestro = None

    if len(exitosos) > 0:
        paquete_maestro = {
            "aprobados": aprobados,
            "descartados": descartados,
        }

        # Guardar en JSON local
        with open(ruta_salida_json, "w", encoding="utf-8") as archivo:
            json.dump(paquete_maestro, archivo, indent=2, ensure_ascii=False)

        # Sincronizar en Supabase
        try:
            guardados_supabase = base_datos.guardar_lote_ia_supabase(paquete_maestro)
        except Exception as e:
            errores.append(f"Error sincronizando con Supabase: {e}")

        exito = True
    else:
        # Fallo del 100%: no se toca el archivo local preexistente
        exito = False

    return {
        "exito": exito,
        "total_evaluados": total,
        "exitosos": len(exitosos),
        "fallidos": len(fallidos),
        "guardados_supabase": guardados_supabase,
        "errores": errores,
        "aprobados": aprobados,
        "descartados": descartados,
        "resultados": paquete_maestro,
    }
