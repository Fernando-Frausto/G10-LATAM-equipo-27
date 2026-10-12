import json
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="CommunityLab API", version="1.0")

# Configurar CORS para permitir que el Frontend de Netlify se conecte
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, aquí iría la URL de Netlify
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ARCHIVO_RESULTADOS = "resultados_kpis.json"

@app.get("/api/kpis", summary="Obtiene los mensajes analizados con el texto dummy de copy")
def obtener_kpis():
    if not os.path.exists(ARCHIVO_RESULTADOS):
        return []
    
    try:
        with open(ARCHIVO_RESULTADOS, "r", encoding="utf-8") as f:
            datos = json.load(f)
            
        # Inyectar el campo 'copy_final' para la Integración Iterativa con Frontend
        if "aprobados" in datos:
            for mensaje in datos["aprobados"]:
                if "copy_final" not in mensaje:
                    mensaje["copy_final"] = "Pendiente de redacción por Enoc..."
            
        return datos
    except Exception as e:
        return {"error": f"Error al procesar el archivo: {str(e)}"}

@app.get("/api/reporte-semanal", summary="Obtiene el reporte semanal consolidado con métricas globales")
def obtener_reporte_semanal():
    if os.path.exists("reportes"):
        archivos = sorted(
            [f for f in os.listdir("reportes") if f.endswith(".json")],
            reverse=True,
        )
        if archivos:
            ruta = os.path.join("reportes", archivos[0])
            with open(ruta, "r", encoding="utf-8") as f:
                return json.load(f)
    return {"mensaje": "Aún no se ha generado ningún reporte semanal."}

@app.get("/", summary="Estado del servidor")
def health_check():
    return {"status": "ok", "message": "Backend Administrativo funcionando correctamente."}
