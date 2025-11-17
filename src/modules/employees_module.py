from serpapi import GoogleSearch
from dotenv import load_dotenv
import os
import requests
from modules.mongodb_management import save_in_database

load_dotenv()
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")
ENRICH_API_KEY = os.getenv("ENRICH_API_KEY")

def get_company_employees_serpapi(company_name, db, max_pages=5):
    employees = []
    print(f"[+] Buscando empleados en LinkedIn...")
    for page in range(max_pages):
        query = f"site:linkedin.com/in \"{company_name}\""
        
        params = {
            "engine": "google",
            "q": query,
            "start": page * 10,
            "num": 10,
            "api_key": SERPAPI_API_KEY
        }

        search = GoogleSearch(params)
        results = search.get_dict()

        organic = results.get("organic_results", [])
        if not organic:
            break

        for item in organic:
            employees.append({
                "name": item.get("title"),
                "profile_link": item.get("link"),
                "additional_data": item.get("snippet"),
                "source": item.get("source")
            })

        print(f"[+] Página {page+1}: {len(organic)} resultados")

    save_in_database(db, {"employees": employees}, company_name)
    print(f"[+] Total guardados: {len(employees)} empleados")


#------------------enrich---------------------------


ENRICH_BASE_URL = "https://api.enrich.so"

def enrich_get_company_summary(company_name, domain):
    """
    Devuelve únicamente company_id y description desde enrich.so.
    """
    url = f"{ENRICH_BASE_URL}/v1/api/company"

    params = {"name": company_name, "domain": domain}

    headers = {
        "Authorization": f"Bearer {ENRICH_API_KEY}",
        "Content-Type": "application/json"
    }

    r = requests.get(url, headers=headers, params=params)

    if r.status_code != 200:
        print(f"[!] Error solicitando company_id: {r.text}")
        return None

    data = r.json()

    if "company_id" not in data:
        print("[!] No se encontró company_id en la respuesta.")
        return None

    return {
        "company_id": data["company_id"],
        "description": data.get("description", "")
    }


def enrich_get_company_employees(company_id, max_pages=50, page_size=50):
    """
    Devuelve una lista completa de empleados
    """

    url = f"{ENRICH_BASE_URL}/v1/api/search-company-employees"
    headers = {
        "Authorization": f"Bearer {ENRICH_API_KEY}",
        "Content-Type": "application/json"
    }

    all_profiles = []

    for page in range(1, max_pages + 1):
        payload = {
            "page": page,
            "page_size": page_size,
            "companyIds": [company_id]
        }

        r = requests.post(url, headers=headers, json=payload)

        if r.status_code != 200:
            print(f"[!] Error en página {page}: {r.text}")
            break

        data = r.json()
        profiles = data.get("data", {}).get("profiles", [])

        if not profiles:
            break

        for p in profiles:

            # Construir nombre combinado
            given = p.get("given_name", "")
            family = p.get("family_name", "")

            full_name = (given + " " + family).strip()

            formatted = {
                "name": full_name if full_name else None,
                "current_position": p.get("current_position"),
                "linkedin_url": p.get("external_profile_url"),
                "residence": p.get("residence"),
                "expert_skills": p.get("expert_skills", []),
                "source": "enrich"
            }

            all_profiles.append(formatted)

        # Fin de paginación
        current = data["data"]["current_page"]
        total = data["data"]["total_page"]
        if current >= total:
            break

    return all_profiles




def enrich_save_employees(company_name, domain, db, date_str):
    """
    Guarda únicamente:
      - descripción de la empresa
      - lista completa de empleados
    """

    # 1. Obtener resumen de empresa
    company_info = enrich_get_company_summary(company_name, domain)
    if not company_info:
        print("[!] No se pudo obtener información de la empresa.")
        return None

    company_id = company_info["company_id"]

    # 2. Obtener empleados
    employees = enrich_get_company_employees(company_id)

    # 3. Guardar en la base de datos
    save_in_database(db, {
                "company_description": company_info.get("description", ""),
                "employees": employees
            }
            ,company_name, date_str)

    print(f"[+] Guardados {len(employees)} empleados y descripción de la empresa '{company_name}'.")




