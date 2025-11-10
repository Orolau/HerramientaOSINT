import whois
import socket
from datetime import datetime
from modules.mongodb_management import update_domain_entry

def get_ip(domain, db, company_name):
    try:
        ip = socket.gethostbyname(domain)
    except:
        ip = None
    update_domain_entry(db, company_name, "domains", domain, {"ip": ip})



def get_whois_info(domain, db, company_name):

    try:
        info = whois.whois(domain)
        data = dict(info)

        valores_invalidos = ["", None, "Not Disclosed", " not published", "Redacted for Privacy", "REDACTED", "N/A", "None"]
        clean_data = {}

        for k, v in data.items():
            if isinstance(v, (list, set)):
                v = list(v)
                if len(v) == 1:
                    v = v[0]
            if v and not any(str(v).strip().lower() == str(inval).lower() for inval in valores_invalidos):
                clean_data[k] = v

        update_domain_entry(db, company_name, "domains", domain, {"whois": clean_data})

    except Exception as e:
        update_domain_entry(db, company_name, "domains", domain, {"whois": {"error": str(e)}})



def get_whois_all_domains(company_name, db):
    date_str = datetime.now().strftime("%Y%m%d")
    try:
        record = db[date_str].find_one({"company": company_name})
        if not record or "domains" not in record:
            print(f"[!] Error: no se encontraron dominios para {company_name}")
            return

        domains = record["domains"]

        for domain in domains:
            domain_name = domain.get("name")
            get_ip(domain_name, db, company_name)
            get_whois_info(domain_name, db, company_name)
        print("[+] Completada la búsqueda de información de whois y direcciones IP para los dominios")
        
    except Exception as e:
        print(f"[!] Error obteniendo la lista de dominios: {e}")
