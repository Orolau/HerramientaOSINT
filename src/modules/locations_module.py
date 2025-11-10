import requests
from serpapi import GoogleSearch
from datetime import datetime
import time
from dotenv import load_dotenv
import os
from modules.mongodb_management import save_in_database

load_dotenv()
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")


def get_company_locations_serpapi(company_name, db):
    """
    Busca sedes físicas de una empresa en Google Maps mediante SerpAPI.
    Añade automáticamente variaciones en la búsqueda (oficinas, centros, etc.)
    y guarda los resultados en la base de datos.
    """
    print(f"[=] Iniciando búsqueda de sedes para '{company_name}' con SerpAPI...")

    # Variaciones de búsqueda
    search_variations = [
        company_name,
        f"{company_name} oficina",
        f"{company_name} sede",
        f"{company_name} centro logístico",
        f"{company_name} centro de distribución",
        #f"{company_name} almacén",
        #f"{company_name} headquarters",
    ]

    results_list = []

    for query in search_variations:
        print(f"Buscando: {query}")
        params = {
            "engine": "google_maps",
            "q": query,
            "api_key": SERPAPI_API_KEY,
            "hl": "es"
        }

        try:
            search = GoogleSearch(params)
            results = search.get_dict()

            local_results = results.get("local_results", [])
            for r in local_results:
                location_data = {
                    "source": "serpapi",
                    "name": r.get("title"),
                    "address": r.get("address"),
                    "type": r.get("type"),
                    "rating": r.get("rating"),
                    "gps_coordinates": r.get("gps_coordinates", {}),
                    "phone": r.get("phone"),
                }

                # Evitar duplicados (por dirección)
                if location_data["address"] and location_data["address"] not in [l.get("address") for l in results_list]:
                    results_list.append(location_data)

            
            time.sleep(1.5)

        except Exception as e:
            print(f"[!] Error en búsqueda '{query}': {e}")

    if not results_list:
        print(f"[!] No se encontraron sedes para {company_name}.")
        return

    # Guardar resultados en MongoDB
    date_str = datetime.now().strftime("%Y%m%d")
    save_in_database(db, {"locations": results_list}, company_name)
    
    print(f"[+] {len(results_list)} sedes guardadas para {company_name}")

