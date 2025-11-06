import os
from dotenv import load_dotenv
import json
import re
from modules.mongodb_management import save_in_database, add_to_database_field
from modules.make_requests import make_POST_request, make_GET_request
from datetime import datetime
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()
API_KEY = os.getenv("API_KEY_DOMAINS")

def is_domain_valid(domain):
    """
    Comprueba si un dominio está activo y no pertenece a un placeholder
    de registradores o páginas de aparcamiento.
    """
    placeholder_patterns = [
        r"buy\s*this\s*domain",
        r"this\s*domain\s*is\s*for\s*sale",
        r"register\s*this\s*domain",
        r"get\sthis\sdomain",
        f"the domain {domain} is for sale",
        r"busca\stu\sdominio",
        r"domain\smay\sbe\savailable",
        r"domain\s*parking",
        r"go\s*daddy",
        r"namecheap",
        r"sedo",
        r"acredited\sregistrar",
        r"hostinger",
        r"ovh",
        r"plesk",
        r"entorno\sdigital"
        r"Heberjahiz",
        r"página\s*de\s*inicio\s*por\s*defecto",
        r"web\s*en\s*construcción",
        r"coming\s*soon",
        r"this\s*site\s*is\s*parked",
        r"dns\s*error",
        r"no\s*such\s*host",
    ]

    for protocol in ["https", "http"]:
        url = f"{protocol}://{domain}"
        try:
            r = requests.get(url, timeout=4, headers={"User-Agent": "Mozilla/5.0"})
            content = r.text.lower()

            # Si no responde correctamente, descartamos
            if r.status_code >= 400:
                continue

            # Si la respuesta es demasiado corta, probablemente sea falsa
            if len(content) < 300:
                continue

            # Buscar patrones de placeholder
            if any(re.search(p, content) for p in placeholder_patterns):
                continue

            # Si pasa todos los filtros, es un dominio válido
            return True

        except requests.RequestException:
            continue

    return False
    
def saveDomainData(data, company_name, db):
    try:
        jsonData = json.loads(data)
        domains_list = jsonData.get("domainsList", [])

        # Filtrar dominios válidos
        valid_domains = check_domains_parallel(domains_list)

        if not valid_domains:
            print(f"[-] No se encontraron dominios válidos para {company_name}")
            return
        # Crear lista de documentos
        domain_docs = [{"name": d, "source": "whoisxmlapi"} for d in valid_domains]

        # Guardar o añadir al campo "domains"
        add_to_database_field(db, company_name, "domains", domain_docs)

        print(f"[+] {len(valid_domains)} dominios válidos guardados para {company_name}")

    except json.JSONDecodeError:
        print("[!] Error: la respuesta no es JSON válido.")
    except KeyError:
        print("[!] Error: formato inesperado en los datos recibidos.")
    except Exception as e:
        print(f"[!] Error al guardar datos: {e}")

def onError(error_code):
    print(f"[!] Error: {error_code}")

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
            for val in alt.items():
                if isinstance(val, list):
                    names_to_search.extend(val)
        elif isinstance(alt, list):
            names_to_search.extend(alt)

    # Limpiar y normalizar nombres
    import re
    def clean_name(name):
        return re.sub(r"[^a-zA-Z0-9\-]", "", name).lower()

    names_to_search = list({clean_name(n) for n in names_to_search if clean_name(n)})

    print(f"[-] Buscando dominios para: {', '.join(names_to_search)}")

    headers = {"Content-Type": "application/json"}

    for name in names_to_search:
        if name == company_name:
            payload_name = f"*{name}.*"
        else:
            payload_name = f"{name}.*"
        payload = {
            "apiKey": API_KEY,
            "domains": {
                "include": [payload_name]
            }
        }

        make_POST_request(
            lambda data: saveDomainData(data, company_name, db),
            onError,
            urlWHOISXMLAPI,
            payload,
            headers
        )

def check_domains_parallel(domains, max_workers=20):
    """
    Comprueba en paralelo si los dominios existen.
    Retorna SOLO la lista de dominios válidos.
    """
    if isinstance(domains, dict):
        domain_list = list(domains.keys())
    else:
        domain_list = list(domains)

    print(f"[-] Comprobando {len(domain_list)} dominios en paralelo...")

    valid_domains = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_domain = {executor.submit(is_domain_valid, d): d for d in domain_list}

        for future in as_completed(future_to_domain):
            domain = future_to_domain[future]
            try:
                if future.result():  # Solo añadir los válidos
                    valid_domains.append(domain)
            except Exception:
                pass

    print(f"[+] {len(valid_domains)} dominios válidos / {len(domain_list)} totales.")
    return valid_domains

#------------------------------------------crt.sh--------------------------------------------------
def get_crtsh_and_classify(company_name, db):
    """
    Consulta crt.sh, clasifica los resultados en dominios o subdominios
    según su estructura, y los guarda en la base de datos en los campos
    'domains' y 'subdomains'.
    """

    url = f"https://crt.sh/json?q={company_name}"

    print(f"[-] Consultando crt.sh para {company_name}...")

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
                print(f"[-] No se encontraron resultados en crt.sh para {company_name}")
                return

            domains = []
            subdomains = []

            for name in all_names:
                name = name.replace("https://", "").replace("http://", "").strip("/")
                parts = name.split(".")

                # --- Clasificación ---
                # Si el nombre base está contenido y solo tiene 2 o 3 partes (e.g., mercadona.es o www.mercadona.es)
                # y no tiene subniveles adicionales, lo clasificamos como dominio
                if len(parts) < 3 or (len(parts) == 3 and parts[0] == "www"):
                    domains.append(name)
                else:
                    subdomains.append(name)

            # --- Guardar en la base de datos ---
            # Validar dominios antes de guardar
            valid_domains = check_domains_parallel(domains)
            domain_docs = [{"name": d, "source": "crt.sh"} for d in valid_domains]
            subdomain_docs = [{"name": s, "source": "crt.sh"} for s in subdomains]

            if domain_docs:
                add_to_database_field(db, company_name, "domains", domain_docs)
                print(f"[+] {len(domain_docs)} dominios añadidos.")
            if subdomain_docs:
                add_to_database_field(db, company_name, "subdomains", subdomain_docs)
                print(f"[+] {len(subdomain_docs)} subdominios añadidos.")
        except Exception as e:
            print(f"[!] Error procesando respuesta de crt.sh: {e}")

    def on_error(status_code):
        print(f"[!] Error {status_code} al consultar crt.sh para {company_name}")

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