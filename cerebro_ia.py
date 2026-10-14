import os
import json
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from prompts_ia import FormatoSalida, prompt_filtro

load_dotenv()
_modelo = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
llm = ChatGroq(model=_modelo, temperature=0.1)

llm_estructurado = llm.with_structured_output(FormatoSalida)
cadena = prompt_filtro | llm_estructurado