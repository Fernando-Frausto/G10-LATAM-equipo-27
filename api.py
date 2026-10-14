import os
import json
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import base_datos

app = FastAPI(title="CommunityLab API", version="1.0")

# Configurar CORS configurable desde variables de entorno
origenes_cors = [origen.strip() for origen in os.getenv("ALLOWED_ORIGINS", "*").split(",") if origen.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origenes_cors or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ARCHIVO_RESULTADOS = "resultados_kpis.json"


def _formatear_lote_kpis(datos) -> dict:
    """Normaliza y asegura la estructura canónica {"aprobados": [...], "descartados": [...]} con copy_final."""
    if not datos:
        return {"aprobados": [], "descartados": []}

    # Si viene como lista directa (ej. filas planas de base de datos)
    if isinstance(datos, list):
        aprobados = []
        descartados = []
        for f in datos:
            fila = dict(f)
            kpis = fila.get("kpis")
            if not isinstance(kpis, dict):
                kpis = {
                    "relevancia": fila.get("relevancia", 0),
                    "sentimiento": fila.get("sentimiento", "Neutral"),
                    "temas_clave": fila.get("temas_clave", "N/A"),
                    "segmento": fila.get("segmento", "N/A"),
                    "razonamiento": fila.get("razonamiento", ""),
                }
            item = {
                "id_mensaje": fila.get("id_mensaje"),
                "autor": fila.get("autor"),
                "canal_origen": fila.get("canal_origen"),
                "comunidad": fila.get("comunidad"),
                "semana": fila.get("semana"),
                "fecha_envio": fila.get("fecha_envio"),
                "fecha_extraccion": fila.get("fecha_extraccion"),
                "modelo_ia": fila.get("modelo_ia"),
                "texto_original": fila.get("texto_original", ""),
                "kpis": kpis,
            }
            if "decision_ia" in fila:
                item["decision_ia"] = fila.get("decision_ia")
            if "estado_revision" in fila:
                item["estado_revision"] = fila.get("estado_revision")

            estado = str(fila.get("estado_revision") or "").strip().lower()
            decision_ia = str(fila.get("decision_ia") or fila.get("decision") or "").strip().lower()

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
                item["copy_final"] = fila.get("copy_final") or "Pendiente de redacción por Enoc..."
                aprobados.append(item)
            else:
                descartados.append(item)
        return {"aprobados": aprobados, "descartados": descartados}

    # Si ya viene como diccionario
    if isinstance(datos, dict):
        items_todos = []
        for lista_clave in ("aprobados", "descartados"):
            for elemento in datos.get(lista_clave, []):
                if isinstance(elemento, dict):
                    elem = dict(elemento)
                    if "decision_ia" not in elem:
                        elem["decision_ia"] = "aprobado" if lista_clave == "aprobados" else "descartado"
                    items_todos.append(elem)

        if items_todos or "aprobados" in datos or "descartados" in datos:
            aprobados = []
            descartados = []
            for item in items_todos:
                estado = str(item.get("estado_revision") or "").strip().lower()
                decision_ia = str(item.get("decision_ia") or item.get("decision") or "").strip().lower()

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
                    if "copy_final" not in item:
                        item["copy_final"] = item.get("copy_final") or "Pendiente de redacción por Enoc..."
                    aprobados.append(item)
                else:
                    descartados.append(item)
            return {"aprobados": aprobados, "descartados": descartados}

    return {"aprobados": [], "descartados": []}


@app.get("/api/kpis", summary="Obtiene los mensajes analizados con el texto dummy de copy")
def obtener_kpis():
    # 1. Intentar consultar Supabase prioritariamente
    try:
        datos_supabase = base_datos.obtener_lote_kpis_supabase()
        if datos_supabase is not None:
            return _formatear_lote_kpis(datos_supabase)
    except Exception:
        pass

    # 2. Fallback a archivo local resultados_kpis.json
    if os.path.exists(ARCHIVO_RESULTADOS):
        try:
            with open(ARCHIVO_RESULTADOS, "r", encoding="utf-8") as f:
                datos_archivo = json.load(f)
            return _formatear_lote_kpis(datos_archivo)
        except Exception:
            pass

    # 3. Base y archivo vacíos o inexistentes: contrato canónico inmutable (HTTP 200)
    return {"aprobados": [], "descartados": []}


@app.get("/api/reporte-semanal", summary="Obtiene el reporte semanal consolidado con métricas globales")
def obtener_reporte_semanal():
    # 1. Intentar consultar Supabase prioritariamente
    try:
        reporte_supabase = base_datos.obtener_ultimo_reporte_semanal_supabase()
        if reporte_supabase is not None:
            return reporte_supabase
    except Exception:
        pass

    # 2. Fallback al archivo más reciente en reportes/
    if os.path.exists("reportes"):
        archivos = sorted(
            [f for f in os.listdir("reportes") if f.endswith(".json")],
            reverse=True,
        )
        if archivos:
            ruta = os.path.join("reportes", archivos[0])
            try:
                with open(ruta, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

    # 3. Sin ningún reporte existente: HTTP 404 estructurado
    return JSONResponse(
        status_code=404,
        content={
            "error": "No se encontró ningún reporte semanal generado",
            "detail": "No se encontró ningún reporte semanal generado",
        },
    )


@app.get("/", summary="Estado del servidor")
def health_check():
    return {"status": "ok", "message": "Backend Administrativo funcionando correctamente."}

