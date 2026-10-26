import os
import re
import requests
import tweepy
from src.config import config
from typing import Dict, Any
import time
import random
from functools import wraps

LINKS_OFICIALES_LINKEDIN = [
    "https://lnkd.in/gX2m2Rhq",
    "https://lnkd.in/gvbqJiF4",
    "https://lnkd.in/gU7h7xyG",
]

BLOQUE_LINKS_LINKEDIN = (
    "Más Información:\n"
    "https://lnkd.in/gX2m2Rhq\n"
    "https://lnkd.in/gvbqJiF4\n"
    "https://lnkd.in/gU7h7xyG"
)

LINKS_OFICIALES_X = [
    "https://lnkd.in/gvbqJiF4",
    "https://lnkd.in/gU7h7xyG",
]

BLOQUE_LINKS_X = (
    "https://lnkd.in/gvbqJiF4\n"
    "https://lnkd.in/gU7h7xyG"
)


def _sanitizar_marca(texto: str | None) -> str:
    """Sanitiza menciones residuales a 'Alura' transformándolas a 'CloudEDTech'."""
    if not texto or not isinstance(texto, str):
        return ""
    limpio = texto
    limpio = re.sub(r"#AluraLatam\b", "#CloudEDTech", limpio, flags=re.IGNORECASE)
    limpio = re.sub(r"#Alura\b", "#CloudEDTech", limpio, flags=re.IGNORECASE)
    limpio = re.sub(r"\bAlura\s+Latam\b", "CloudEDTech", limpio, flags=re.IGNORECASE)
    limpio = re.sub(r"\bAlura\b", "CloudEDTech", limpio, flags=re.IGNORECASE)
    return limpio


def _procesar_copy_linkedin(titulo: str | None, texto_copy: str | None) -> tuple[str, str]:
    """Inyecta de forma idempotente el bloque 'Más Información' con los 3 links oficiales y sanitiza marca."""
    tit = _sanitizar_marca(titulo or "").strip()
    txt = _sanitizar_marca(texto_copy or "").strip()
    if not txt:
        return tit, txt

    tiene_mas_info = "más información" in txt.lower() or "mas informacion" in txt.lower()
    faltantes = [lnk for lnk in LINKS_OFICIALES_LINKEDIN if lnk not in txt and lnk not in tit]

    if not faltantes and tiene_mas_info:
        return tit, txt

    if len(faltantes) == len(LINKS_OFICIALES_LINKEDIN):
        txt = f"{txt}\n\n{BLOQUE_LINKS_LINKEDIN}".strip()
    elif faltantes:
        txt = f"{txt}\n" + "\n".join(faltantes)
        if not tiene_mas_info:
            txt = f"{txt}\n\nMás Información:\n" + "\n".join(LINKS_OFICIALES_LINKEDIN)
    elif not tiene_mas_info:
        primer_link = LINKS_OFICIALES_LINKEDIN[0]
        if primer_link in txt:
            txt = txt.replace(primer_link, f"Más Información:\n{primer_link}", 1)
        else:
            txt = f"{txt}\n\n{BLOQUE_LINKS_LINKEDIN}".strip()

    return tit, txt.strip()


def _procesar_copy_x(titulo: str | None, texto_copy: str | None) -> tuple[str, str]:
    """Inyecta de forma idempotente los 2 links de X garantizando longitud total <= 280 caracteres recortando en frontera de palabra."""
    tit = _sanitizar_marca(titulo or "").strip()
    txt = _sanitizar_marca(texto_copy or "").strip()
    if not txt and not tit:
        return tit, txt

    txt = txt.replace("https://lnkd.in/gX2m2Rhq", "")
    tit = tit.replace("https://lnkd.in/gX2m2Rhq", "")

    cuerpo_base = txt
    for lnk in LINKS_OFICIALES_X:
        cuerpo_base = cuerpo_base.replace(lnk, "")
    cuerpo_base = re.sub(r"\n{3,}", "\n\n", cuerpo_base).strip()

    sufijo_links = f"\n\n{BLOQUE_LINKS_X}" if (cuerpo_base or tit) else BLOQUE_LINKS_X
    prefijo_tit = f"{tit}\n\n" if tit else ""
    max_cuerpo = 280 - len(prefijo_tit) - len(sufijo_links)

    if max_cuerpo < 0:
        max_tit = max(0, 280 - len(sufijo_links) - 5)
        tit = (tit[:max_tit].rstrip() + "...") if max_tit > 3 and len(tit) > max_tit else tit[:max(0, max_tit)]
        prefijo_tit = f"{tit}\n\n" if tit else ""
        max_cuerpo = max(0, 280 - len(prefijo_tit) - len(sufijo_links))

    if len(cuerpo_base) > max_cuerpo:
        if max_cuerpo > 3:
            corte = cuerpo_base[: max_cuerpo - 3]
            ultimo_esp = corte.rfind(" ")
            if ultimo_esp > max(10, (max_cuerpo - 3) // 2):
                cuerpo_base = corte[:ultimo_esp].rstrip(",;.: ") + "..."
            else:
                cuerpo_base = corte.rstrip(",;.: ") + "..."
        else:
            cuerpo_base = cuerpo_base[:max_cuerpo]

    txt_final = f"{cuerpo_base}\n\n{BLOQUE_LINKS_X}".strip() if cuerpo_base else BLOQUE_LINKS_X
    return tit, txt_final

def retry_with_backoff(max_intentos=3, base_delay=1.0):
    """Reintento simple con backoff exponencial para rate-limits."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            ultimo_error = None
            for intento in range(1, max_intentos + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    ultimo_error = e
                    msg = str(e).lower()
                    if any(x in msg for x in ["rate", "429", "limit", "throttle", "timeout", "503", "502"]):
                        espera = (base_delay * (2 ** (intento - 1))) + random.uniform(0.1, 0.5)
                        print(f"⏳ Rate-limit/Error transitorio en {func.__name__} (intento {intento}/{max_intentos}). Esperando {espera:.1f}s...")
                        time.sleep(espera)
                    else:
                        break
            print(f"❌ {func.__name__} falló después de {max_intentos} intentos: {ultimo_error}")
            return False
        return wrapper
    return decorator

def enviar_webhook_discord(copys_generados: Dict[str, Any], autor: str = "Comunidad CloudEDTech", texto_original: str = "") -> bool:
    """
    Envía el copy a Discord (o canal de Reclamos) incluyendo una citación formal
    en bloque del mensaje original del usuario para dar contexto.
    Retorna True si el envío es exitoso o no hay ruta activa, False si falla.
    """
    canal_datos = copys_generados.get("discord") or copys_generados.get("reclamos")

    if not canal_datos:
        return True # Si no hay ruta de discord/reclamos activa, no bloquea

    # 🛠️ Corrección: Incluir "procesado" y manejar estados vacíos o de éxito
    status_copy = str(canal_datos.get("status", "")).lower()
    if status_copy == "error":
        return False
    if status_copy and status_copy not in ["success", "exito", "procesado"]:
        return True

    activos = canal_datos.get("activos_distribucion_generados", {})
    canal = activos.get("canal_seleccionado", "").lower()

    post_a_enviar = None
    webhook_url = None

    # Mapeo estricto de webhooks por canal
    if canal == "#general" or "general" in canal:
        post_a_enviar = activos.get("post_discord")
        webhook_url = config.DISCORD_WEBHOOK_GENERAL or config.get("DISCORD_WEBHOOK_GENERAL")
    elif canal == "#faq" or "faq" in canal:
        post_a_enviar = activos.get("post_discord_faq")
        webhook_url = config.DISCORD_WEBHOOK_FAQ or config.get("DISCORD_WEBHOOK_FAQ")
    elif canal == "#notificaciones" or "notificaciones" in canal:
        post_a_enviar = activos.get("post_discord_notificaciones")
        webhook_url = config.DISCORD_WEBHOOK_NOTIFICACIONES or config.get("DISCORD_WEBHOOK_NOTIFICACIONES")
    elif "pqrs" in canal or "reclamos" in copys_generados:
        post_a_enviar = activos.get("post_discord_pqrs")
        webhook_url = config.DISCORD_WEBHOOK_PQRS or config.get("DISCORD_WEBHOOK_PQRS")

    if not post_a_enviar and "post_discord_pqrs" in activos:
        post_a_enviar = activos.get("post_discord_pqrs")
        webhook_url = config.DISCORD_WEBHOOK_PQRS or config.get("DISCORD_WEBHOOK_PQRS")

    if not webhook_url:
        print(f"⚠️ Discord: Webhook no configurado para el canal '{canal}'. Revisa variables DISCORD_WEBHOOK_* en .env")
        return False

    if not post_a_enviar or not webhook_url:
        print("⚠️ Discord: Falta contenido estructurado o URL de Webhook en las variables de entorno.")
        return False

    titulo = post_a_enviar.get("titulo", "Actualización CloudEDTech")
    texto = post_a_enviar.get("texto_copy", "")

    # 💬 Cita resumida e inteligente (máximo 110 caracteres para dar contexto sin saturar)
    if texto_original:
        texto_snippet = (texto_original[:110] + "...") if len(texto_original) > 110 else texto_original
        citacion = f"> 💬 **Contexto de @{autor}:** *\"{texto_snippet}\"*\n\n"
    else:
        citacion = ""

    mensaje_completo = f"{citacion}**{titulo}**\n\n{texto}"
    payload = {"content": mensaje_completo}

    try:
        print(f"🌐 Enviando petición POST al Webhook de Discord con citación de contexto...")
        response = requests.post(webhook_url, json=payload)
        if response.status_code in [200, 204]:
            print("✅ ¡Publicado con éxito en Discord con contexto!")
            return True
        else:
            print(f"❌ Error en Discord | Código: {response.status_code} | Respuesta: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Excepción crítica en Discord: {e}")
        return False

@retry_with_backoff(max_intentos=3)
def enviar_tweet_x(copys_generados: Dict[str, Any]) -> bool:
    """
    Publica un tweet utilizando la API v2 de X (Twitter) vía tweepy.
    Retorna True si es exitoso, False si falla.
    """
    x_datos = copys_generados.get("x")
    if not x_datos:
        return True

    status_copy = str(x_datos.get("status", "")).lower()
    if status_copy not in ["success", "exito", "exitoso"]:
        print(f"⚠️ X omitido por estado no exitoso: {status_copy}")
        return True

    activos = x_datos.get("activos_distribucion_generados", {})
    post_x = activos.get("post_postx", {})

    if not post_x:
        print("⚠️ X (Twitter): No se encontró contenido estructurado en post_postx.")
        return False

    titulo = post_x.get("titulo", "")
    texto = post_x.get("texto_copy", "")
    titulo_limpio, texto_limpio = _procesar_copy_x(titulo, texto)
    tweet_mensaje = f"{titulo_limpio}\n\n{texto_limpio}".strip() if titulo_limpio else texto_limpio.strip()

    api_key = config.X_API_KEY or config.get("X_API_KEY")
    api_secret = config.X_API_SECRET or config.get("X_API_SECRET")
    access_token = config.X_ACCESS_TOKEN or config.get("X_ACCESS_TOKEN")
    access_token_secret = config.X_ACCESS_TOKEN_SECRET or config.get("X_ACCESS_TOKEN_SECRET")

    if not all([api_key, api_secret, access_token, access_token_secret]):
        print("⚠️ X (Twitter): Faltan credenciales en variables de entorno.")
        return False

    try:
        print("🐦 Conectando con la API de X (Twitter v2)...")
        client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        response = client.create_tweet(text=tweet_mensaje)
        print(f"✅ ¡Publicado con éxito en X! ID: {response.data['id']}")
        return True
    except Exception as e:
        print(f"❌ Error al publicar en X: {e}")
        return False

@retry_with_backoff(max_intentos=3)
def enviar_linkedin(copys_generados: Dict[str, Any]) -> bool:
    """
    Envía el copy a LinkedIn usando la API corporativa y retorna True si es exitoso, False si falla.
    """
    lk_datos = copys_generados.get("linkedin")

    if not lk_datos:
        return True

    status_copy = str(lk_datos.get("status", "")).lower()
    if status_copy not in ["success", "exito"]:
        return True

    activos = lk_datos.get("activos_distribucion_generados", {})
    post_lk = activos.get("post_linkedin", {})

    if not post_lk:
        print("⚠️ LinkedIn: No se encontró contenido estructurado en post_linkedin.")
        return False

    titulo = post_lk.get("titulo", "")
    texto = post_lk.get("texto_copy", "")
    titulo_limpio, texto_limpio = _procesar_copy_linkedin(titulo, texto)
    mensaje_completo = f"{titulo_limpio}\n\n{texto_limpio}".strip() if titulo_limpio else texto_limpio.strip()

    access_token = (config.LINKEDIN_ACCESS_TOKEN or config.get("LINKEDIN_ACCESS_TOKEN", "")).strip().replace('\"', '')
    author_urn = (config.LINKEDIN_AUTHOR_URN or config.get("LINKEDIN_AUTHOR_URN", "")).strip().replace('\"', '')

    if not access_token or not author_urn:
        print("⚠️ LinkedIn: Faltan credenciales (LINKEDIN_ACCESS_TOKEN o LINKEDIN_AUTHOR_URN).")
        return False

    if not author_urn.startswith("urn:li:"):
        author_urn = f"urn:li:person:{author_urn}"

    try:
        print(f"💼 Conectando con la API de LinkedIn para URN: {author_urn}...")
        url = "https://api.linkedin.com/v2/ugcPosts"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0"
        }
        payload = {
            "author": author_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": mensaje_completo},
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
        }

        response = requests.post(url, headers=headers, json=payload)
        if response.status_code in [200, 201]:
            print("✅ ¡Publicado con éxito en LinkedIn!")
            return True
        else:
            print(f"❌ Error en LinkedIn | Código: {response.status_code} | Respuesta: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Excepción crítica en LinkedIn: {e}")
        return False