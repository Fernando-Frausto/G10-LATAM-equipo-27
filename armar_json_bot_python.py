"""
Armo aquí el mismo paquete JSON que antes armaba el nodo Code de n8n, para que el
bot en Python lo mande directo a procesar_actividad (ya no hay endpoint al que
mandarlo por POST). La limpieza del texto y la detección de repetidos siguen siendo
trabajo de procesamiento.py y base_datos.py; el bot solo arma el paquete.
"""
from periodos import a_utc_iso, semana_de

CANALES = {}

ORIGEN_COMUNIDAD = "Discord_Grupo_ONE_G10"

# la fecha de inicio del proyecto (y cómo se cuentan las semanas) ya no vive aquí:
# está en periodos.py, para que solo haya un lugar donde cambiarla


def nombre_canal(canal) -> str:
    """Formatea el canal con prefijo '#' sin generar duplicados '##'."""
    nombre = getattr(canal, "name", None)
    if nombre:
        return f"#{nombre.lstrip('#')}"
    return f"#{getattr(canal, 'id', 'desconocido')}"


def detectar_canales(servidores, id_servidor=None) -> list:
    """Retorna los canales de texto legibles por el bot."""
    id_servidor_str = str(id_servidor).strip() if id_servidor else None
    if not id_servidor_str:
        id_servidor_str = None

    # Si se especificó un ID y no está en los servidores conectados, retorna vacío
    if id_servidor_str and not any(str(getattr(s, "id", "")) == id_servidor_str for s in servidores):
        return []

    canales = []
    for servidor in servidores:
        if id_servidor_str and str(getattr(servidor, "id", "")) != id_servidor_str:
            continue
        for canal in getattr(servidor, "text_channels", []):
            permisos = canal.permissions_for(servidor.me)
            if getattr(permisos, "view_channel", False) and getattr(permisos, "read_message_history", False):
                canales.append(canal)
    return canales


def construir_paquete(mensajes: list) -> dict | None:
    # channel.history() entrega cada canal del más nuevo al más viejo, y el bot los recorre
    # canal por canal, así que la lista llega desordenada. Como el id de la base se asigna
    # en el orden en que se guarda, la ordeno aquí de más viejo a más nuevo (por la fecha
    # real en que se mandó cada mensaje en Discord) para que el id 1 sea el primero enviado
    mensajes = sorted(mensajes, key=lambda m: m.created_at)

    interacciones = []
    for m in mensajes:
        # Ignorar mensajes automáticos de bots o webhooks (ej. Spidey Boy o anuncios)
        if getattr(m.author, "bot", False) or getattr(m, "webhook_id", None):
            continue

        texto = m.content.strip()
        if not texto:
            continue
        interacciones.append({
            "autor": str(m.author),
            "canal": nombre_canal(m.channel),
            "texto": texto,
            # fecha real en que se mandó el mensaje en Discord (no cuándo lo guardé yo),
            # es lo que después permite filtrar los mensajes por periodo
            "enviado_en": a_utc_iso(m.created_at),
        })

    if not interacciones:
        return None

    # periodo_referencia sigue siendo por lote: la semana del mensaje más reciente de esta corrida
    fecha_reciente = max(m.created_at for m in mensajes)

    return {
        "origen_comunidad": ORIGEN_COMUNIDAD,
        "periodo_referencia": f"Semana_{semana_de(fecha_reciente):02d}",
        "interacciones": interacciones,
    }
