
from typing import Dict, List
from collections import OrderedDict
import re
from modules.make_requests import make_GET_request
from modules.mongodb_management import save_in_database


def parse_asns_and_routes(company_name, db,html_bytes: bytes) -> Dict[str, List[str]]:
    """
    Parsea el contenido HTML (en bytes) y extrae:
      - ASNs (ej: AS201976)
      - Rutas/prefijos IP (ej: 195.53.43.0/24)
    
    """
    # Decodificar el HTML
    try:
        html = html_bytes.decode("utf-8")
    except UnicodeDecodeError:
        html = html_bytes.decode("utf-8", errors="ignore")

    # --- Buscar todos los ASNs ---
    asns = re.findall(r"\bAS\s*?(\d{1,10})\b", html, flags=re.IGNORECASE)
    asns = [f"AS{a}" for a in asns]

    # --- Buscar todas las rutas IPv4 con máscara ---
    routes = re.findall(r"\b(\d{1,3}(?:\.\d{1,3}){3}/\d{1,2})\b", html)

    # --- Eliminar duplicados manteniendo el orden ---
    def dedup(seq):
        return list(OrderedDict.fromkeys(seq))

    asns = dedup(asns)
    routes = dedup(routes)

    save_in_database(db, {"asn": asns, "routes": routes}, company_name)


def onError_getting_asn(db, company_name):
    save_in_database(db, {"asn": [], "routes": []}, company_name)

def get_asn_info(company_name,db):
    url = f"https://bgp.he.net/search?search%5Bsearch%5D={company_name}&commit=Search"

    make_GET_request(lambda data: parse_asns_and_routes(company_name, db, data), lambda data: onError_getting_asn(db, company_name), url)
