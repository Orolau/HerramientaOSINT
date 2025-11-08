import os
from dotenv import load_dotenv
import json
import re
from modules.mongodb_management import save_in_database, add_to_database_field
from modules.make_requests import make_POST_request, make_GET_request
from datetime import datetime
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from colorama import Fore

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
        domain_docs = [{"name": d, "source": "whoisxmlapi", "included_subdomains_search": True} for d in valid_domains]

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

def select_alternative_names(company_name, db):
    """
    Permite al usuario seleccionar qué nombres alternativos utilizar
    para la búsqueda de dominios en WHOISXMLAPI.
    """
    date_str = datetime.now().strftime("%Y%m%d")
    record = db[date_str].find_one({"company": company_name})
    
    if not record or "alternativeNames" not in record:
        print("[-] No se encontraron nombres alternativos.")
        return [company_name]

    alt = record["alternativeNames"]

    # Aplanar todos los nombres alternativos en una lista simple
    if isinstance(alt, dict):
        alt_list = []
        for k, v in alt.items():
            if isinstance(v, list):
                alt_list.extend(v)
            elif isinstance(v, str):
                alt_list.append(v)
    elif isinstance(alt, list):
        alt_list = alt
    else:
        alt_list = []

    # Mostrar opciones al usuario
    print(f"\n[+] Nombres alternativos encontrados para {company_name}:")
    for i, name in enumerate(alt_list, start=1):
        print(f"{i}. {name}")

    print("\n[=] Indica los números de los nombres alternativos que deseas incluir, separados por comas o rangos (ej: 1,3,5-7).")
    selected = input("[=] Nombres a incluir: ").strip()

    # Si el usuario no selecciona nada → usar todos
    if not selected:
        print("[-] No se seleccionó ningún nombre. Se incluirán todos los alternativos.")
        return [company_name] + alt_list

    # Parsear los índices (soporta rangos)
    indices = set()
    for part in selected.split(","):
        part = part.strip()
        if "-" in part:
            try:
                start, end = map(int, part.split("-"))
                indices.update(range(start, end + 1))
            except ValueError:
                continue
        elif part.isdigit():
            indices.add(int(part))

    chosen = [alt_list[i - 1] for i in indices if 0 < i <= len(alt_list)]
    chosen.insert(0, company_name)  # incluir el nombre principal siempre

    print(f"[+] Se buscarán dominios para: {', '.join(chosen)}")
    return chosen


def get_domains_WHOISXMLAPI(company_name, db):
    """
    Busca dominios asociados a una empresa,
    incluyendo solo los nombres alternativos seleccionados por el usuario.
    """
    urlWHOISXMLAPI = "https://domains-subdomains-discovery.whoisxmlapi.com/api/v1"
    headers = {"Content-Type": "application/json"}

    names_to_search = select_alternative_names(company_name, db)

    import re
    def clean_name(name):
        return re.sub(r"[^a-zA-Z0-9\-]", "", name).lower()

    names_to_search = list({clean_name(n) for n in names_to_search if clean_name(n)})

    print(f"\n[=] Iniciando búsqueda de dominios para: {', '.join(names_to_search)}")

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

    print(f"[=] Comprobando {len(domain_list)} dominios en paralelo...")

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

    print(f"[=] Consultando crt.sh para {company_name}...")

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
            domain_docs = [{"name": d, "source": "crt.sh", "included_subdomains_search": True} for d in valid_domains]
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
    "Desarrollo": ["dev", "test", "staging", "qa", "sandbox","prueba"],
    "Correo": ["mail","correo", "smtp", "imap", "mx", "spf"],
    "Autenticación": ["login", "auth", "signin", "sso"],
    "API / Servicio": ["api", "graphql", "backend", "ftp"],
    "CDN / Contenido estático": ["cdn", "static", "assets"],
    "Aplicación / Producto": ["shop", "tienda", "store", "app", "blog", "support", "news", "noticias"],
    "Infraestructura": ["ns", "vpn", "proxy", "monitor", "infra"],
    "Regional": ["es", "us", "eu", "latam","pt", "fr", "nl"]
}
def subdomain_categorizer(subdomain):
    subdomain = subdomain.lower()
    for category, words in CATEGORIES.items():
        if any(word in subdomain for word in words):
            return category
    return "Sin categoría"

def saveSubDomainData(data, company_name, db, parent_domain):
    """
    Guarda subdominios obtenidos desde WHOISXMLAPI en la base de datos.
    Estructura: subdomains = [ {name, category, domain}, ... ]
    """
    date_str = datetime.now().strftime("%Y%m%d")
    try:
        jsonData = json.loads(data)
        records = jsonData.get("result", {}).get("records", [])

        if not records:
            print(f"[-] No se encontraron subdominios para {parent_domain}.")
            return

        # Crear lista con la estructura deseada
        new_subdomains = []
        for record in records:
            sub_name = record.get("domain")
            if not sub_name:
                continue
            category = subdomain_categorizer(sub_name)
            new_subdomains.append({
                "name": sub_name,
                "category": category,
                "domain": parent_domain
            })

        collection = db[date_str]
        company_doc = collection.find_one({"company": company_name})
        existing_subdomains = company_doc.get("subdomains", []) if company_doc else []

        # Evitar duplicados
        existing_names = {sd["name"] for sd in existing_subdomains}
        merged_subdomains = existing_subdomains + [sd for sd in new_subdomains if sd["name"] not in existing_names]

        # Guardar actualizando solo el campo subdomains
        collection.update_one(
            {"company": company_name},
            {"$set": {"subdomains": merged_subdomains}},
            upsert=True
        )

        print(f"[+] {len(new_subdomains)} subdominios añadidos para {parent_domain}")

    except json.JSONDecodeError:
        print(f"[!] Respuesta no válida al guardar subdominios de {parent_domain}")
    except Exception as e:
        print(f"[!] Error al guardar subdominios de {parent_domain}: {e}")


def get_subdomains(company_name, db):
    """
    Recorre los dominios con included_subdomains_search=True
    y obtiene sus subdominios usando WHOISXMLAPI.
    """
    date_str = datetime.now().strftime("%Y%m%d")
    record = db[date_str].find_one({"company": company_name})
    if not record or "domains" not in record:
        print(f"[-] No se encontraron dominios para {company_name}.")
        return

    domains_list = record["domains"]

    # Filtrar dominios marcados como incluidos
    domains_to_search = [d for d in domains_list if d.get("included_subdomains_search", True)]

    print(f"\n[=] Buscando subdominios para {len(domains_to_search)} dominios...")

    for domain_entry in domains_to_search:
        domain_name = domain_entry.get("name")
        if not domain_name:
            continue

        url = f"https://subdomains.whoisxmlapi.com/api/v1?apiKey={API_KEY}&domainName={domain_name}"

        make_GET_request(
            lambda data, dname=domain_name: saveSubDomainData(data, company_name, db, dname),
            onError,
            url
        )


def mark_excluded_domains_for_subdomain_search(company_name, db):
    date_str = datetime.now().strftime("%Y%m%d")
    # Obtener los dominios almacenados (como lista)
    record = db[date_str].find_one({"company": company_name})
    if not record or "domains" not in record:
        print(f"[!] No se encontraron dominios para {company_name}.")
        return

    domains_list = record["domains"]

    print(f"\n[=] Dominios encontrados para {company_name}:")
    for i, domain in enumerate(domains_list, start=1):
        name = domain.get("name", "<sin nombre>")
        include_flag = domain.get("included_subdomains_search", True)
        status = "incluido" if include_flag else "excluido"
        print(f"{i}. {name} ({status})")

    print("\n[=] Indica los números de los dominios que **NO** deseas incluir en la búsqueda de subdominios (separados por comas).")
    print("    Ejemplo: 1,3,5-10,15")
    exclude_input = input("[=] Dominios a excluir: ").strip()

    def parse_indices(input_str, total):
        """Convierte una cadena como '1,3,5-10' en una lista de índices [0,2,4,5,6,7,8,9]."""
        indices = set()
        parts = [p.strip() for p in input_str.split(",") if p.strip()]
        for part in parts:
            if "-" in part:
                try:
                    start, end = part.split("-")
                    start, end = int(start), int(end)
                    indices.update(range(start - 1, min(end, total)))  # convertir a base 0
                except ValueError:
                    print(f"[!] Rango inválido: {part}")
            else:
                if part.isdigit():
                    idx = int(part) - 1
                    if 0 <= idx < total:
                        indices.add(idx)
        return sorted(indices)

    # Parsear la entrada del usuario
    exclude_indices = parse_indices(exclude_input, len(domains_list)) if exclude_input else []


    # Actualizar los flags en la lista de dominios
    updated_domains = []
    for i, domain in enumerate(domains_list):
        updated_domain = domain.copy()
        updated_domain["included_subdomains_search"] = False if i in exclude_indices else True
        updated_domains.append(updated_domain)

    # Guardar los cambios en la base de datos
    db[date_str].update_one(
        {"company": company_name},
        {"$set": {"domains": updated_domains}}
    )

    print(f"\n[+] Se han actualizado los dominios correctamente.")
    for d in updated_domains:
        print(f"  - {d.get('name')}: {'incluido' if d.get('included_subdomains_search', True) else 'excluido'}")