import os
import json
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from prompts_ia import FormatoSalida, prompt_filtro

load_dotenv()

# 2. Leemos las variables nuevas de Google
_modelo = os.getenv("GEMINI_MODEL", "").strip() or os.getenv("GOOGLE_MODEL", "").strip() or "gemini-3.5-flash-lite"

# 3. Inicializamos el LLM con la clase correcta
llm = ChatGoogleGenerativeAI(
    model=_modelo, 
    temperature=0.1,
    google_api_key=os.environ.get("GOOGLE_API_KEY")
)

llm_estructurado = llm.with_structured_output(FormatoSalida)
cadena = prompt_filtro | llm_estructurado

