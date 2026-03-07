from datetime import datetime
from modules.mongodb_management import add_to_database_field
from modules.make_requests import make_GET_request
import json

def search_domain_leaks(domain, company_name, db, date_str):
    url = f"https://haveibeenpwned.com/api/v3/breaches?Domain={domain}"
    make_GET_request(
        lambda data: show_domain_leak_results(data, domain, company_name, db, date_str),
        show_error,
        url
    )

def show_domain_leak_results(data, domain, company_name, db, date_str):
    leaks = parse_domain_response(data)
    
    if leaks:
        add_to_database_field(db, company_name, "domain_leaks", leaks)
        print(f"[+] {domain} ha sufrido {len(leaks)} filtraciones.")

def parse_domain_response(data):
    

    if isinstance(data, bytes):
        data = json.loads(data.decode())

    if not isinstance(data, list):
        return []

    parsed_leaks = []
    for breach in data:
        parsed_leaks.append({
            "domain":breach.get("Domain"),
            "name": breach.get("Name"),
            "title": breach.get("Title"),
            "breach_date": breach.get("BreachDate"),
            "added_date": breach.get("AddedDate"),
            "pwn_count": breach.get("PwnCount"),
            "description": breach.get("Description"),
            "data_classes": breach.get("DataClasses"),
            "is_verified": breach.get("IsVerified"),
            "is_sensitive": breach.get("IsSensitive"),
            "is_spam_list": breach.get("IsSpamList"),
            "is_malware": breach.get("IsMalware"),
            "is_stealer_log": breach.get("IsStealerLog"),
        })

    return parsed_leaks
    
def show_error(e):
    print("[-] Error en la búsqueda de filtraciones de domnios: ", e)

def search_all_domains_leaks(company_name, db, date_str=None):
    print(f"[=] Iniciando búsqueda de filtraciones para los dominios identificados")
    if not date_str:
        date_str = datetime.now().strftime("%Y%m%d")

    record = db[date_str].find_one({"company": company_name})
    if not record:
        print(f"[!] No se encontraron datos para {company_name} en {date_str}")
        return
    
    domains = record.get("domains", [])
    if len(domains) == 0:
        print(f"[!] No se han encontrado dominios para {company_name} en {date_str}")
        return
    for domain in domains:
        search_domain_leaks(domain.get("name"), company_name, db, date_str)