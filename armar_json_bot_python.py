"""
Armo aquí el mismo paquete JSON que antes armaba el nodo Code de n8n, para que el
bot en Python lo mande directo a procesar_actividad (ya no hay endpoint al que
mandarlo por POST). La limpieza del texto y la detección de repetidos siguen siendo
trabajo de procesamiento.py y base_datos.py; el bot solo arma el paquete.
"""
from periodos import a_utc_iso, semana_de

# Ya no hay que declarar los canales a mano: el bot los detecta solos al conectarse
# (detectar_canales). El nombre del canal sale de Discord, con "#" al inicio, igual que
# antes ("#general", "#preguntas"...), así los hashes de los mensajes ya guardados no cambian.


def nombre_canal(canal) -> str:
    """Nombre del canal como se guarda en la base: '#' + el nombre que tiene en Discord."""
    nombre = getattr(canal, "name", None)
    return f"#{nombre}" if nombre else f"#{canal.id}"


def detectar_canales(servidores, id_servidor=None) -> list:
    """Regresa los canales de texto que el bot puede leer, en todos los servidores donde está.

    - id_servidor (opcional): si se pasa, solo se revisa ese servidor. Es recomendable cuando
      el bot está en más de uno, para no leer canales de comunidades que no son esta.
    - Solo entran canales donde el bot puede ver el canal y leer el historial; los demás se
      omiten (se avisan desde bot_lote.py) en vez de fallar a la mitad de la lectura.
    """
    canales = []
    for servidor in servidores:
        if id_servidor and str(servidor.id) != str(id_servidor):
            continue
        for canal in servidor.text_channels:
            permisos = canal.permissions_for(servidor.me)
            if permisos.view_channel and permisos.read_message_history:
                canales.append(canal)
    return canales


ORIGEN_COMUNIDAD = "Discord_Grupo_ONE_G10"

# la fecha de inicio del proyecto (y cómo se cuentan las semanas) ya no vive aquí:
# está en periodos.py, para que solo haya un lugar donde cambiarla


def construir_paquete(mensajes: list) -> dict | None:
    # channel.history() entrega cada canal del más nuevo al más viejo, y el bot los recorre
    # canal por canal, así que la lista llega desordenada. Como el id de la base se asigna
    # en el orden en que se guarda, la ordeno aquí de más viejo a más nuevo (por la fecha
    # real en que se mandó cada mensaje en Discord) para que el id 1 sea el primero enviado
    mensajes = sorted(mensajes, key=lambda m: m.created_at)

    interacciones = []
    for m in mensajes:
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
