import os
from dotenv import load_dotenv
import json
from modules.mongodb_management import save_in_database, add_to_database_field
from modules.make_requests import make_POST_request, make_GET_request
from datetime import datetime
import requests

load_dotenv()
API_KEY = os.getenv("API_KEY_DOMAINS")

def is_domain_valid(domain):
    url = f"http://{domain}"
    try:
        r = requests.get(url, timeout=3)
        if r.status_code<400:
            return True
        else:
            return False
    except requests.RequestException:
        return False
    
def saveDomainData(data, company_name, db):
    try:
        jsonData = json.loads(data)
        domains_list = jsonData.get("domainsList", [])

        # Filtrar dominios válidos
        valid_domains = [d for d in domains_list if is_domain_valid(d)]

        # Convertir la lista a diccionario: {"dominio": {}}
        domains_dict = {domain: {} for domain in valid_domains}

        # Guardar o añadir al campo "domains"
        add_to_database_field(db, company_name, "domains", domains_dict)

        print(f"{len(valid_domains)} dominios válidos guardados para {company_name}")

    except json.JSONDecodeError:
        print("Error: la respuesta no es JSON válido.")
    except KeyError:
        print("Error: formato inesperado en los datos recibidos.")
    except Exception as e:
        print(f"Error al guardar datos: {e}")

def onError(error_code):
    print(f"Error: {error_code}")

def get_domains_WHOISXMLAPI(company_name, db):
    """
    Busca dominios y subdominios asociados a una empresa,
    incluyendo nombres alternativos. Hace una petición por cada nombre.
    """
    urlWHOISXMLAPI = "https://domains-subdomains-discovery.whoisxmlapi.com/api/v1"

    # Recuperar nombres alternativos desde la base de datos
    date_str = datetime.now().strftime("%Y%m%d")
    record = db[date_str].find_one({"company": company_name})
    
    names_to_search = [company_name]

    if record and "alternativeNames" in record:
        alt = record["alternativeNames"]
        if isinstance(alt, dict):
            for key, val in alt.items():
                if isinstance(val, list):
                    names_to_search.extend(val)
        elif isinstance(alt, list):
            names_to_search.extend(alt)

    # Limpiar y normalizar nombres
    import re
    def clean_name(name):
        return re.sub(r"[^a-zA-Z0-9\-]", "", name).lower()

    names_to_search = list({clean_name(n) for n in names_to_search if clean_name(n)})

    print(f"Buscando dominios para: {', '.join(names_to_search)}")

    headers = {"Content-Type": "application/json"}

    for name in names_to_search:
        payload = {
            "apiKey": API_KEY,
            "domains": {
                "include": [f"{name}.*"]
            }
        }

        make_POST_request(
            lambda data: saveDomainData(data, company_name, db),
            onError,
            urlWHOISXMLAPI,
            payload,
            headers
        )

#------------------------------------------crt.sh--------------------------------------------------
def get_crtsh_and_classify(company_name, db):
    """
    Consulta crt.sh, clasifica los resultados en dominios o subdominios
    según su estructura, y los guarda en la base de datos en los campos
    'domains' y 'subdomains'.
    """

    base_query = f"%.{company_name}.%"
    url = f"https://crt.sh/json?q={company_name}"

    print(f"Consultando crt.sh para {company_name}...")

    def on_success(response_text):
        try:
            data = json.loads(response_text)
            all_names = set()

            for entry in data:
                names = entry.get("name_value", "").split("\n")
                for n in names:
                    n = n.strip().lower()
                    if n and "*" not in n:
                        all_names.add(n)

            if not all_names:
                print(f"No se encontraron resultados en crt.sh para {company_name}")
                return

            domains_dict = {}
            subdomains_dict = {}

            for name in all_names:
                name = name.replace("https://", "").replace("http://", "").strip("/")
                parts = name.split(".")

                # --- Clasificación ---
                # Si el nombre base está contenido y solo tiene 2 o 3 partes (e.g., mercadona.es o www.mercadona.es)
                # y no tiene subniveles adicionales, lo clasificamos como dominio
                if len(parts) < 3:
                    domains_dict[name] = {}
                elif len(parts) == 3 and parts[0] == "www":
                    domains_dict['.'.join(parts[1:])] = {}
                else:
                    subdomains_dict[name] = {}

            # --- Guardar en la base de datos ---
            if domains_dict:
                add_to_database_field(db, company_name, "domains", domains_dict)
                print(f"{len(domains_dict)} dominios añadidos.")
            if subdomains_dict:
                add_to_database_field(db, company_name, "subdomains", subdomains_dict)
                print(f"{len(subdomains_dict)} subdominios añadidos.")
        except Exception as e:
            print(f"Error procesando respuesta de crt.sh: {e}")

    def on_error(status_code):
        print(f"Error {status_code} al consultar crt.sh para {company_name}")

    make_GET_request(on_success, on_error, url)



#-----------------------------------------Subdominios-----------------------------------------------------------------
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
def subdomain_categorizer(subdomain):
    subdomain = subdomain.lower()
    for category, words in CATEGORIES.items():
        if any(word in subdomain for word in words):
            return category
    return "Desconocido"

def saveSubDomainData(data, company_name, db):
    jsonData = json.loads(data)
    subdomains_list = {}
    for i in jsonData["result"]["records"]: 
        category = subdomain_categorizer(i["domain"])
        subdomains_list[i["domain"]] = {"category": category}
    
    date_str = datetime.now().strftime("%Y%m%d")
    try:
        subdomains_saved = db[date_str].find_one({"company": company_name})["subdomains"]
        actualized_subdomains = dict(set(subdomains_list + subdomains_saved))
        save_in_database(db, {"subdomains": actualized_subdomains}, company_name)
    except:
        save_in_database(db, {"subdomains": subdomains_list}, company_name)

def get_subdomains(company_name, db):
    date_str = datetime.now().strftime("%Y%m%d")
    domains_list = db[date_str].find_one({"company": company_name})["domains"]
    for i in domains_list:
        url = f"https://subdomains.whoisxmlapi.com/api/v1?apiKey={API_KEY}&domainName={i}" 

        make_GET_request(lambda data: saveSubDomainData(data, company_name, db), onError, url)

def delete_not_included_domains(company_name, db):
    date_str = datetime.now().strftime("%Y%m%d")
    # Obtener los dominios almacenados (como lista)
    record = db[date_str].find_one({"company": company_name})
    if not record or "domains" not in record:
        print(f"No se encontraron dominios para {company_name}.")
        return

    domains_list = record["domains"]

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
    
    # Crear diccionario con dominios seleccionados
    domains_dict = {domain: {} for domain in filtered_domains}


    save_in_database(db, {"domains":domains_dict}, company_name)