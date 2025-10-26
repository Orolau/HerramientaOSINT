import whois
import socket
from modules.mongodb_management import save_in_database
from datetime import datetime

def get_ip(domain, db, company_name):
    try:
        ip = socket.gethostbyname(domain)
    except:
        ip = None
    
    save_in_database(db, {f"domains.{domain}.ip": ip}, company_name)

def get_whois_info(domain, db, company_name):
    try:
        info = whois.whois(domain)
        data = dict(info)
        print(data)
        # Palabras o valores que queremos ignorar
        valores_invalidos = ["", None, "Not Disclosed", "Redacted for Privacy", "REDACTED", "N/A", "None"]

        clean_data = {}
        # Convertir listas o sets en strings legibles
        for k, v in data.items():
            if isinstance(v, (list, set)):
                v = list(v)
                if len(v) == 1:
                    v = v[0]

            # Filtrar valores no deseados
            if v and not any(str(v).strip().lower() == inval.lower() for inval in valores_invalidos):
                clean_data[k] = v

        save_in_database(db, {f"domains.{domain}.whois": clean_data}, company_name)

    except Exception as e:
        save_in_database(db, {f"domains.{domain}.whois": "Error getting data"}, company_name)


def get_whois_all_domains(company_name, db):
    date_str = datetime.now().strftime("%Y%m%d")
    try:
        domains = db[date_str].find_one({"company": company_name})["domains"]

        for domain in domains:
            get_ip(domain, db, company_name)
            get_whois_info(domain, db, company_name)
        
    except:
        print("Error obteniendo la lista de dominios de la base de datos")

