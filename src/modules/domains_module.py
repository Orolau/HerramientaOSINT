import os
from dotenv import load_dotenv
import json
from modules.mongodb_management import save_in_database
from modules.make_requests import make_POST_request, make_GET_request
from datetime import datetime

load_dotenv()
API_KEY = os.getenv("API_KEY_DOMAINS")

CATEGORIES = {
    "Administración": ["admin", "panel", "dashboard", "cpanel"],
    "Desarrollo": ["dev", "test", "staging", "qa", "sandbox"],
    "Correo": ["mail", "smtp", "imap", "mx"],
    "Autenticación": ["login", "auth", "signin", "sso"],
    "API / Servicio": ["api", "graphql", "backend", "ftp"],
    "CDN / Contenido estático": ["cdn", "static", "assets"],
    "Aplicación / Producto": ["shop", "store", "app", "blog", "support"],
    "Infraestructura": ["ns", "vpn", "proxy", "monitor", "infra"],
    "Regional": ["es", "us", "eu", "latam"]
}

def saveDomainData(data, company_name, db):
    try:
        jsonData = json.loads(data)
        save_in_database(db, {"company": company_name,"domains": jsonData["domainsList"]}, company_name)
        print("Datos guardados")
    except:
        print(data['message'])

def subdomain_categorizer(subdomain):
    subdomain = subdomain.lower()
    for category, words in CATEGORIES.items():
        if any(word in subdomain for word in words):
            return category
    return "Desconocido"

def saveSubDomainData(data, company_name, db):
    jsonData = json.loads(data)
    subdomains_list = {}
    domain = jsonData["search"]
    for i in jsonData["result"]["records"]: 
        category = subdomain_categorizer(i["domain"])
        subdomains_list[i["domain"]] = category
    save_in_database(db, {domain: subdomains_list}, company_name)
    

def onError(error_code):
    print(f"Error: {error_code}")

def get_domains(company_name, db):
    url = "https://domains-subdomains-discovery.whoisxmlapi.com/api/v1" 
    payload = {
        "apiKey": API_KEY,
        "domains": {
            "include": [
                f"*{company_name}.*"
            ]
        }
    }
    headers = {
        "Content-Type": "application/json"
    }   
 
    make_POST_request(lambda data: saveDomainData(data, company_name, db), onError, url, payload, headers)

def get_subdomains(company_name, db):
    date_str = datetime.now().strftime("%Y%m%d")
    domains_list = db[date_str].find_one({"company": company_name})["domains"]
    for i in domains_list:
        url = f"https://subdomains.whoisxmlapi.com/api/v1?apiKey={API_KEY}&domainName={i}" 

        make_GET_request(lambda data: saveSubDomainData(data, company_name, db), onError, url)

def delete_not_included_domains(company_name, db):
    date_str = datetime.now().strftime("%Y%m%d")
    domains_list = db[date_str].find_one({"company": company_name})["domains"]

    print(f"\nDominios encontrados para {company_name}:")
    for i, domain in enumerate(domains_list, start=1):
        print(f"{i}. {domain}")

    print("\nIndica los números de los dominios que deseas incluir en la búsqueda de subdominios, separados por comas.")
    include = input("Dominios a incluir: ").strip()
    if include:
        try:
            indices = [int(i) - 1 for i in include.split(",") if i.strip().isdigit()]
            filtered_domains = [d for i, d in enumerate(domains_list) if i in indices]
        except ValueError:
            print("Entrada no válida. No se eliminará ningún dominio.")
            filtered_domains = domains_list
    else:
        filtered_domains = domains_list
    
    save_in_database(db, {"domains":filtered_domains}, company_name)