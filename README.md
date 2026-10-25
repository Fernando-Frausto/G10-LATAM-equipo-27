<p align="center">
  <img src="https://github.com/user-attachments/assets/a83ad067-c6ae-4b78-b382-c9f71262b352" alt="Logo de CloudEDTech: Education & Technology" width="420">
</p>

# ☁️ CloudPulse — Motor Inteligente de Transformación y Distribución para Comunidades Digitales

> **Ningún mensaje sin respuesta. Ningún logro sin celebrar.**

**CloudPulse** es una solución de **CloudEDTech** que escucha la actividad orgánica de una comunidad en Discord, la analiza con IA (relevancia, sentimiento y temas) y la convierte en activos de marketing listos para publicar en **LinkedIn, X y Discord**, siempre con **revisión humana** (*Human-in-the-Loop*) antes de publicar. También atiende quejas y genera reportes semanales que se almacenan en **OCI Object Storage (Always Free)**.

Proyecto desarrollado por el **Equipo 27** para el **Hackathon ONE G10 — Oracle Next Education & Alura** (simulación No Country, Proyecto 3: *CommunityLab*).

---

## 📑 Contenido

- [El problema](#-el-problema)
- [La solución](#-la-solución)
- [Funcionalidades](#-funcionalidades)
- [Arquitectura](#️-arquitectura)
- [Stack tecnológico](#-stack-tecnológico)
- [Estructura del repositorio](#-estructura-del-repositorio)
- [Instalación y ejecución local](#-instalación-y-ejecución-local)
- [Pruebas](#-pruebas)
- [Despliegue en la nube](#️-despliegue-en-la-nube)
- [Documentación adicional](#-documentación-adicional)
- [Equipo](#-equipo)
- [Licencia](#-licencia)

---

## 🎯 El problema

Matías es *community manager* de una comunidad de estudiantes. Cada día llegan cientos de mensajes a varios canales de Discord: dudas, logros, quejas y spam. Leerlos uno por uno, decidir cuáles importan, redactar publicaciones para cada red, responder quejas y armar reportes le toma **10 pasos manuales**, y los mensajes más valiosos (un alumno atascado hace tres días, una contratación lograda gracias a un curso) se pierden en el historial.

## 💡 La solución

CloudPulse reduce el proceso a **3 pasos**: conectar la comunidad, dejar que la IA lea y clasifique, y que el community manager **apruebe** lo que se publica.

| Etapa | Qué hace |
|---|---|
| **1. Ingesta** | Sincroniza los mensajes de los canales de Discord, omite bots, los limpia, los ordena por fecha y los guarda. |
| **2. Análisis con IA** | Calcula relevancia (0–100), sentimiento, temas (hashtags) y segmento de cada mensaje, de forma individual o por lotes. |
| **3. Orquestación y redacción** | Un grafo de **LangGraph** decide a qué canales enviar cada mensaje y redacta el copy de cada red con la voz del Manual de Marca. |
| **4. Revisión humana (HITL)** | El community manager edita, aprueba o descarta antes de publicar. |
| **5. Publicación** | Envío real a LinkedIn, X y Discord (canales `#general`, `#faq`, `#notificaciones` y `#pqrs`). |
| **6. Informes** | Paquete semanal en JSON con métricas y activos, subido a **OCI Object Storage**. |

---

## ✨ Funcionalidades

<p align="center">
  <img src="https://github.com/user-attachments/assets/9023e6c7-dbb4-4a26-9d3f-a263f2bd360e" alt="Dashboard de CloudPulse con KPIs de la comunidad, sentimiento, temas principales e historias destacadas" width="900">
</p>

La interfaz web se organiza en cinco pestañas:

| Pestaña | Ruta | Qué hace |
|---|---|---|
| **Dashboard** | `/dashboard` | KPIs de la comunidad, gráficas de sentimiento y temas, historias destacadas y participación por canal. |
| **Ingesta de mensajes** | `/messages` | Sincronización con Discord, evaluación con IA (individual o por lotes) y filtros por estado: pendientes de evaluar, pendientes de publicar, proceso completo y descartados. |
| **Análisis** | `/analytics` | Métricas de sentimiento, emojis, hashtags, alineación de marca e *insights* sobre quejas. |
| **Redacción de contenidos** | `/content` | Mesa de trabajo multicanal: genera o regenera *copys* para LinkedIn, X y Discord, aprobación HITL, procesamiento masivo, anuncios oficiales y panel de quejas y soporte. |
| **Informes y almacenamiento** | `/oci-storage` | Generación del reporte semanal, carga al bucket de OCI Object Storage e historial de reportes (reintento y descarga). |

Se puede elegir entre tres modelos de IA: **Groq (Llama 3.3)**, **Google Gemma 4** y **Google Gemini Flash Lite**. Cada nodo del pipeline cuenta con un **modelo de respaldo** (*fallback*) por si el principal falla o se satura.

---

## 🏗️ Arquitectura

### Flujo de datos

```mermaid
%%{init: {"theme": "base", "flowchart": {"wrappingWidth": 260, "nodeSpacing": 25, "rankSpacing": 25, "padding": 6}, "themeVariables": {"primaryColor": "#080A27", "primaryTextColor": "#080A27", "primaryBorderColor": "#FF7400", "lineColor": "#FF7400", "clusterBkg": "transparent", "clusterBorder": "#FF7400", "titleColor": "#FF7400", "edgeLabelBackground": "#FFE3CC", "textColor": "#080A27", "fontFamily": "Inter, Arial, sans-serif", "fontSize": "12px"}}}%%
flowchart TD
    A["Comunidad en Discord"] --> B["Ingesta: sincronización, limpieza y filtrado"]
    B --> C["Supabase (PostgreSQL)"]
    C --> D["Motor de IA: relevancia, sentimiento y temas"]
    D --> E{"Orquestador<br/>LangGraph"}
    E --> F["Redacción por canal: LinkedIn, X, Discord y Quejas"]
    F --> G["Validador del Manual de Marca"]
    G --> H["Revisión humana (HITL)"]
    H --> I["Publicación en LinkedIn, X y Discord"]
    I --> J["Reporte semanal JSON"]
    J --> K["OCI Object Storage (Always Free)"]
    classDef default fill:#080A27,stroke:#FF7400,stroke-width:1.5px,color:#FFFFFF
    classDef decision fill:#FF7400,stroke:#080A27,stroke-width:2px,color:#080A27,font-weight:bold
    classDef terminal fill:#FFFFFF,stroke:#FF7400,stroke-width:2px,color:#080A27
    class E decision
```

### Grafo de orquestación (LangGraph)

El orquestador decide las rutas según la **relevancia** y el **tipo de mensaje** (bifurcación condicional):

```mermaid
%%{init: {"theme": "base", "flowchart": {"wrappingWidth": 420}, "themeVariables": {"primaryColor": "#080A27", "primaryTextColor": "#080A27", "primaryBorderColor": "#FF7400", "lineColor": "#FF7400", "clusterBkg": "transparent", "clusterBorder": "#FF7400", "titleColor": "#FF7400", "edgeLabelBackground": "#FFE3CC", "textColor": "#080A27", "fontFamily": "Inter, Arial, sans-serif"}}}%%
flowchart TD
    S((Inicio)) --> O{"Orquestador"}
    O -- "Relevancia ≤ 10 (spam)" --> FIN((Fin sin ruta))
    O -- "11–34 (baja)" --> GA["Gemma automático<br/>respuesta directa en Discord"]
    O -- "Logro / caso de éxito" --> LI["Nodo LinkedIn<br/>post + destacado newsletter + FAQ"]
    O -- "Logro / anuncio" --> X["Nodo X<br/>post conciso ≤ 210 caracteres"]
    O -- "Duda / aviso" --> DC["Nodo Discord<br/>#general · #faq · #notificaciones"]
    O -- "Queja" --> RQ["Nodo Reclamos<br/>#pqrs"]
    LI --> V["Validador de marca"]
    X --> V
    DC --> V
    RQ --> V
    V --> HITL["⏸️ Pausa HITL<br/>aprobación humana"]
    HITL --> P["Publicador"]
    P --> F2((Fin))
    GA --> F2
    classDef default fill:#080A27,stroke:#FF7400,stroke-width:1.5px,color:#FFFFFF
    classDef decision fill:#FF7400,stroke:#080A27,stroke-width:2px,color:#080A27,font-weight:bold
    classDef terminal fill:#FFFFFF,stroke:#FF7400,stroke-width:2px,color:#080A27
    class O decision
    class F2,FIN,S terminal
```

### Flujos detallados por etapa

<details>
<summary><b>🔍 Ver flujo detallado de Ingesta</b></summary>

```mermaid
%%{init: {"theme": "base", "flowchart": {"wrappingWidth": 420}, "themeVariables": {"primaryColor": "#080A27", "primaryTextColor": "#080A27", "primaryBorderColor": "#FF7400", "lineColor": "#FF7400", "clusterBkg": "transparent", "clusterBorder": "#FF7400", "titleColor": "#FF7400", "edgeLabelBackground": "#FFE3CC", "textColor": "#080A27", "fontFamily": "Inter, Arial, sans-serif"}}}%%
flowchart TD
    A["Comunidad en Discord"] --> I1
    I1["1. Captura de mensajes (bot_lote.py)<br/>Lee el historial de cada canal<br/>Detecta canales legibles y manda el paquete a procesar"]
    I1 --> Q1{"¿Hay canales<br/>que leer?"}
    Q1 -- "No" --> N1["Aviso: no hay canales<br/>Termina el proceso"]
    Q1 -- "Sí" --> I2["2. Armado del paquete (armar_json_bot_python.py)<br/>Pone los mensajes en formato JSON<br/>Ordena por fecha, descarta vacíos y arma las llaves del JSON"]
    I2 --> Q2{"¿Hay mensajes<br/>con texto?"}
    Q2 -- "No" --> N2["Nada que procesar<br/>Termina sin guardar"]
    Q2 -- "Sí" --> I3["3. Revisión del formato (modelos.py)<br/>Confirma que el paquete esté bien armado<br/>Autor, canal y texto obligatorios; tipo y enviado_en opcionales"]
    I3 --> Q3{"¿Formato<br/>correcto?"}
    Q3 -- "No" --> N3["Devuelve status error<br/>No procesa el lote"]
    Q3 -- "Sí" --> I4["4. Limpieza del texto (limpieza.py)<br/>Quita espacios de más y calcula el hash<br/>Quita espacios y saltos de línea; si queda vacío, se omite"]
    I4 --> I5["5. Semana del proyecto (periodos.py)<br/>Según la fecha en que se envió<br/>Fecha de inicio, zona horaria y cálculo de semanas"]
    I5 --> I6["6. Repetidos (limpieza.py, base_datos.py)<br/>Compara el hash de cada mensaje<br/>procesar_actividad descarta repetidos y vacíos antes de guardar"]
    I6 --> Q4{"¿Hash ya<br/>existe?"}
    Q4 -- "Sí" --> N4["Se omite<br/>Cuenta como repetido"]
    Q4 -- "No" --> I7["7. Guardado (base_datos.py)<br/>Se guardan en communitylab.db<br/>Crea la base SQLite y guarda cada mensaje nuevo"]
    I7 --> I8["8. Consulta de datos (ver_json.py)<br/>Filtra por semana o por fechas<br/>obtener_json entrega los datos; también corre en la terminal"]
    I8 --> Q5{"¿Se pidió<br/>un periodo?"}
    Q5 -- "Sí" --> R1["Solo ese periodo<br/>Usa semanas o fechas"]
    Q5 -- "No" --> R2["Devuelve los 100 más recientes"]
    classDef default fill:#080A27,stroke:#FF7400,stroke-width:1.5px,color:#FFFFFF
    classDef decision fill:#FF7400,stroke:#080A27,stroke-width:2px,color:#080A27,font-weight:bold
    classDef terminal fill:#FFFFFF,stroke:#FF7400,stroke-width:2px,color:#080A27
    class Q1,Q2,Q3,Q4,Q5 decision
```

</details>

<details>
<summary><b>🔍 Ver flujo detallado de Análisis con IA</b></summary>

```mermaid
%%{init: {"theme": "base", "flowchart": {"wrappingWidth": 420}, "themeVariables": {"primaryColor": "#080A27", "primaryTextColor": "#080A27", "primaryBorderColor": "#FF7400", "lineColor": "#FF7400", "clusterBkg": "transparent", "clusterBorder": "#FF7400", "titleColor": "#FF7400", "edgeLabelBackground": "#FFE3CC", "textColor": "#080A27", "fontFamily": "Inter, Arial, sans-serif"}}}%%
flowchart TD
    subgraph PRI["Workflow principal: evaluación inteligente y extracción de 5 KPIs con 3 cerebros IA"]
        M["Mensajes a evaluar<br/>Cola Discord cruda<br/>(id, autor, canal, texto)"]
        M --> L["Configurar lote<br/>Filtro de pendientes y límite<br/>(evaluador_lotes.py)"]
        L --> INV["Invocador dinámico<br/>Carga e inferencia<br/>(importlib / cadena)"]
        INV --> SW{"Switch<br/>(cerebro IA)"}
        SW -- "Groq Cloud" --> C1["Cerebro 1: Groq Cloud<br/>ChatGroq (Llama 3.3 / OSS)<br/>(cerebro_ia.py)"]
        SW -- "Gemma 4" --> C2["Cerebro 2: Google Gemma<br/>ChatGoogle (gemma-4-31b-it)<br/>(cerebro_ia_gemma_4.py)"]
        SW -- "Gemini Flash" --> C3["Cerebro 3: Gemini Flash<br/>ChatGoogle (flash-lite)<br/>(cerebro_ia_gemini_flash.py)"]
        C1 --> MG["Merge<br/>(cadena.invoke)<br/>(texto, canal)"]
        C2 --> MG
        C3 --> MG
        MG --> AG["AI Agent evaluador<br/>Extracción de 5 KPIs<br/>cadena = prompt | llm"]
        PR(["Prompt filtro EdTech<br/>Reglas y guía de 5 KPIs<br/>(prompts_ia.py)"]) -.-> AG
        SP(["Structured Output Parser<br/>Pydantic: FormatoSalida<br/>(JSON validado)"]) -.-> AG
        AG --> K5["Extracción de 5 KPIs<br/>Relevancia, sentimiento, temas<br/>Segmento y razonamiento"]
        AG --> FR["Filtro relevancia >= 70<br/>Aprobados vs descartados<br/>(clasificación de valor)"]
        FR --> PE["Persistencia de KPIs<br/>SQLite (communitylab.db)<br/>y Supabase (lotes_ia_kpis)"]
        PE --> PM["Paquete maestro JSON<br/>Exportar resultados_kpis.json<br/>(resumen y métricas)"]
        PM --> HO["Handoff a redacción<br/>Disponible en Dashboard y Studio<br/>(listo para publicar)"]
    end

    L -. "Captura cualquier fallo / rate limit (429)" .-> ET

    subgraph SEC["Workflow secundario: manejo global de errores, tolerancia por mensaje y resiliencia"]
        ET["Error trigger<br/>Excepción IA / HTTP 429<br/>(rate limit o timeout)"]
        ET --> AI["Aislamiento individual<br/>try / except por mensaje<br/>(no interrumpe el lote)"]
        AI --> PP["Protección de persistencia<br/>Blindar resultados_kpis.json<br/>(evita sobrescribir si falla)"]
        PP --> RD["Registro y diagnóstico<br/>Notificación clara en la UI<br/>(ID fallido y causa exacta)"]
    end
    classDef default fill:#080A27,stroke:#FF7400,stroke-width:1.5px,color:#FFFFFF
    classDef decision fill:#FF7400,stroke:#080A27,stroke-width:2px,color:#080A27,font-weight:bold
    classDef terminal fill:#FFFFFF,stroke:#FF7400,stroke-width:2px,color:#080A27
    class SW decision
```

</details>

<details>
<summary><b>🔍 Ver flujo detallado de Informes y OCI Object Storage</b></summary>

```mermaid
%%{init: {"theme": "base", "flowchart": {"wrappingWidth": 260, "nodeSpacing": 25, "rankSpacing": 25, "padding": 6}, "themeVariables": {"primaryColor": "#080A27", "primaryTextColor": "#080A27", "primaryBorderColor": "#FF7400", "lineColor": "#FF7400", "clusterBkg": "transparent", "clusterBorder": "#FF7400", "titleColor": "#FF7400", "edgeLabelBackground": "#FFE3CC", "textColor": "#080A27", "fontFamily": "Inter, Arial, sans-serif", "fontSize": "12px"}}}%%
flowchart TD
    T["Botón Generar informe<br/>(OCIStorage.tsx)"] --> SEM["Definir semana<br/>(indicada o actual)"]
    SEM --> QV{"¿Semana<br/>válida?"}
    QV -- "No" --> E1["Error 400"]
    QV -- "Sí" --> CL["Cargar mensajes de la semana<br/>Supabase o respaldo SQLite"]
    CL --> QM{"¿Hay<br/>mensajes?"}
    QM -- "No" --> E2["Error 400"]
    QM -- "Sí" --> RP["Generar reporte JSON<br/>métricas y activos"]
    RP --> QO{"¿Credenciales<br/>OCI?"}
    QO -- "No" --> LO["Guardado local"]
    QO -- "Sí" --> UP["Subir al bucket<br/>(put_object)"]
    UP --> QU{"¿Subida<br/>exitosa?"}
    QU -- "No" --> LO
    QU -- "Sí" --> OB["Sincronizado en OCI"]
    LO --> PN["Panel de Informes<br/>historial, descarga y reintento"]
    OB --> PN
    classDef default fill:#080A27,stroke:#FF7400,stroke-width:1.5px,color:#FFFFFF
    classDef decision fill:#FF7400,stroke:#080A27,stroke-width:2px,color:#080A27,font-weight:bold
    classDef terminal fill:#FFFFFF,stroke:#FF7400,stroke-width:2px,color:#080A27
    class QV,QM,QO,QU decision
    class E1,E2 terminal
```

---

## 🧰 Stack tecnológico

| Capa | Tecnologías |
|---|---|
| Frontend | React 19, TypeScript, Vite, Tailwind CSS 4, React Router, Recharts, Lucide |
| Backend / API | Python 3.10+, FastAPI, Uvicorn, Pydantic, SQLAlchemy, Alembic |
| IA y orquestación | LangChain, LangGraph, Groq, Google GenAI (Gemini / Gemma 4), LangSmith (trazabilidad, opcional) |
| Datos | Supabase (PostgreSQL), SQLite (respaldo local), psycopg |
| Integraciones | discord.py, Tweepy (X), API de LinkedIn, SDK de OCI |
| Almacenamiento | OCI Object Storage (capa Always Free) |
| Despliegue | Netlify (frontend), Render (API), Cloudflare Worker (proxy de Discord) |
| Calidad | pytest, oxlint |

---

## 📁 Estructura del repositorio

```
├── puente_motor_ia.py   # Servidor principal (FastAPI)
├── src/                 # Pipeline LangGraph: orquestador, nodos, validador y publicador
├── motor-ia/            # Evaluación con IA
├── frontend/            # Panel web (React + Vite)
├── backend/             # API administrativa (usuarios, roles y auditoría)
├── tests/               # Pruebas automatizadas
└── docs/                # Documentación técnica
```

---

## 🚀 Instalación y ejecución local

### Requisitos previos

- Python **3.10 o superior** y Node.js **24** (la versión que usa Netlify)
- Un proyecto de **Supabase** (PostgreSQL)
- Claves de API de **Groq** y **Google AI Studio (Gemini)**
- Bot y webhooks de **Discord**
- *(Opcional)* Credenciales de **X** y **LinkedIn** para publicar en esas redes
- *(Opcional)* Un bucket de **OCI Object Storage** (capa Always Free) para subir los reportes

### 1. Clonar el repositorio

```bash
git clone https://github.com/No-Country-simulation/G10-LATAM-equipo-27.git
cd G10-LATAM-equipo-27
```

### 2. Servidor principal (API + motor de IA)

```bash
python -m venv .venv
source .venv/bin/activate          # Windows (Git Bash): source .venv/Scripts/activate

pip install -r requirements.txt

cp .env.example .env               # Completa las claves reales
uvicorn puente_motor_ia:app --port 8002 --reload
```

La documentación interactiva de la API queda en `http://127.0.0.1:8002/docs`.

### 3. Frontend (panel web)

En otra terminal:

```bash
cd frontend
npm install
cp .env.example .env
```

Edita `frontend/.env` para que apunte al servidor principal:

```env
VITE_API_URL=http://127.0.0.1:8002
```

Levanta el servidor de desarrollo:

```bash
npm run dev                        # http://localhost:5173
```

---

## 🧪 Pruebas

```bash
pytest                                   # Backend (más de 100 pruebas)
cd frontend && npm run build && npm run lint   # Frontend
```

---

## ☁️ Despliegue en la nube

| Componente | Servicio | Notas |
|---|---|---|
| Frontend | **Netlify** | Configurado en [`netlify.toml`](netlify.toml): compila `frontend/` con `npm run build` y publica `dist/`. Todas las rutas redirigen a `index.html` (SPA). |
| API | **Render** | Comando de inicio: `uvicorn puente_motor_ia:app --host 0.0.0.0 --port $PORT`. Variables cargadas como *secrets*. Un servicio externo la consulta cada 10 minutos para que no entre en reposo. |
| Proxy de Discord | **Cloudflare Worker** | Evita el bloqueo de IP que Discord aplica a Render (error 1015). Se activa con `DISCORD_PROXY_URL`. |
| Base de datos | **Supabase** | PostgreSQL administrado. |
| Almacenamiento | **OCI Object Storage** | Bucket en la capa *Always Free*. |

**Pasos:**
1. **OCI:** crear el bucket en la capa Always Free y generar la API key del usuario (OCID de usuario y tenancy, fingerprint y llave privada).
2. **Supabase:** crear el proyecto y copiar la cadena de conexión.
3. **Render:** crear un *Web Service* desde este repositorio con el comando de inicio indicado y cargar todas las variables de entorno.
4. **Netlify:** crear el sitio desde este repositorio (toma `netlify.toml` automáticamente) y definir `VITE_API_URL` con la URL de Render.
5. *(Si Discord bloquea la IP de Render)* Desplegar el Cloudflare Worker y definir `DISCORD_PROXY_URL` en Render.

🔗 **Demo en línea:** *[agregar URL de Netlify]*

---

## 📚 Documentación adicional

- [`docs/leeme.md`](docs/leeme.md): detalle del pipeline LangGraph, ejecución por consola y demo en Streamlit.
- [`docs/contrato-pipeline.md`](docs/contrato-pipeline.md): contrato técnico del pipeline de copywriting.
- [`docs/informe_archivos.md`](docs/informe_archivos.md): descripción de cada archivo del pipeline.
- [`docs/constitution.md`](docs/constitution.md): principios de trabajo y arquitectura.
- [`specs/`](specs/): especificación, plan y tareas de cada funcionalidad (metodología SDD).
- [`CAMBIOS_INTEGRACION.md`](CAMBIOS_INTEGRACION.md): bitácora de integración del backend.
- [`MEJORAS_PENDIENTES.md`](MEJORAS_PENDIENTES.md): mejoras identificadas pendientes.

---

## 👥 Equipo

Equipo 27 — 12 integrantes de 5 países.

- Enoc Ramírez
- Patricia Madrid
- Fernando Frausto
- Eduardo Alonso
- Andrés Martínez
- Tania Orantes
- Cristian Astudillo
- Samuel Ramírez
- Eduardo García
- Miguel Sierra
- Francisco Valleverde

---

## 📄 Licencia

Distribuido bajo la licencia **MIT**. Consulta [`LICENSE`](LICENSE) para más detalles.

---

<p align="center"><b>CloudPulse</b> · una solución de <b>CloudEDTech</b> · Hackathon ONE G10 — Oracle Next Education & Alura</p>
