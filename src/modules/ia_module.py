import os
import json
import re
from dotenv import load_dotenv
from modules.make_requests import make_POST_request
from modules.mongodb_management import save_in_database

# Cargar clave de API desde .env
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

def get_related_company_names(company_name, db):
    """
    Llama directamente a la API REST de Gemini para obtener nombres asociados a una empresa.
    Devuelve una lista de nombres relacionados, antiguos o subsidiarios.
    """
    if not API_KEY:
        raise ValueError("No se encontró la variable GEMINI_API_KEY en el entorno")

    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": API_KEY
    }

    prompt = (
        f'Actúa como un asistente de análisis corporativo. Dada la empresa "{company_name}", '
        f'genera un objeto JSON con los siguientes campos:\n'
        f'{{\n'
        f'  "nombres_alternativos": [],  # nombres antiguos o abreviados\n'
        f'  "filiales": [],              # empresas subsidiarias o relacionadas\n'
        f'  "internacionales": [],       # nombres o denominaciones en otros países\n'
        f'  "marcas": []                 # marcas comerciales propiedad de la empresa\n'
        f'}}\n'
        f'Retorna exclusivamente el JSON, sin texto adicional, sin explicaciones, sin formato Markdown ni comillas triples.'
    )
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }
    make_POST_request(lambda x: parse_ai_data(x, company_name, db), on_ai_error, url, payload, headers)

    
def on_ai_error(status_code=None):
    print(f"[!] Error al realizar la petición a la API (status {status_code})")


def parse_ai_data(response, company_name, db):
    """
    Procesa la respuesta JSON devuelta por la API de Gemini.
    Si el contenido parece un JSON, lo convierte a un diccionario.
    Si no, lo guarda como texto plano.
    """
    try:
        data = json.loads(response)
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
        # Intentar interpretar el texto como JSON real
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            # Si no es JSON válido, lo guardamos como texto
            print("[!] Error: el modelo no devolvió JSON válido. Se guardará como texto plano.")
            parsed = {"raw_text": text}

        # Guardar en la base de datos
        save_in_database(db, {"alternativeNames": parsed}, company_name)
        print("[+] Información de nombres alternativos guardada correctamente.")

    except (KeyError, IndexError, json.JSONDecodeError) as e:
        print("[!] Error al procesar la respuesta del modelo:", e)
