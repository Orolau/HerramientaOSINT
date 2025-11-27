import shodan
from dotenv import load_dotenv
import os
from modules.mongodb_management import save_in_database

load_dotenv()
SHODAN_API_KEY = os.getenv("SHODAN_API_KEY")

def clasificar_activo_shodan(asset):
    port = asset.get("port")
    product = (asset.get("product") or "").lower()
    banner = (asset.get("banner") or "").lower()
    hostnames = " ".join(asset.get("hostnames", [])).lower()

    # --- Categoría WEB ---
    if port in [80, 443, 8080, 8443] or "http" in banner:
        return "web"

    # --- Categoría ADMIN ---
    admin_keywords = [
        "admin", "login", "dashboard", "control panel",
        "webmin", "pfsense", "sonicwall", "jenkins", "grafana",
        "phpmyadmin", "ubiquiti", "router", "fortigate"
    ]
    if any(k in banner for k in admin_keywords) or any(k in hostnames for k in admin_keywords):
        return "administracion"

    # --- Categoría CORREO ---
    if port in [25, 465, 587, 993, 995] or "smtp" in banner or "mail" in product:
        return "correo"

    # --- Categoría TÉCNICO / INFRA ---
    infra_ports = [22, 3389, 445, 161, 389, 3306, 5432, 6379, 27017]
    if port in infra_ports:
        return "infraestructura"

    # --- Categoría IoT ---
    iot_keywords = ["camera", "webcam", "printer", "nas", "dvr", "hikvision"]
    if any(k in banner for k in iot_keywords) or any(k in product for k in iot_keywords):
        return "iot"

    # --- Por defecto ---
    return "otros"


def shodan_get_assets(company_name, db):
    """
    Obtiene activos expuestos en Internet usando la librería oficial de Shodan.
    Busca por nombre de organización (org:"Company Name") y guarda resultados.
    """

    api = shodan.Shodan(SHODAN_API_KEY)

    query = f'org:"{company_name}"'

    try:
        results = api.search(query)
    except Exception as e:
        print(f"[!] Error con Shodan: {e}")
        return

    assets = []

    for match in results.get("matches", []):
        asset = {
            "ip": match.get("ip_str"),
            "port": match.get("port"),
            "protocol": match.get("transport"),
            "product": match.get("product"),
            "devicetype": match.get("devicetype"),
            "version": match.get("version"),
            "os": match.get("os"),
            "isp": match.get("isp"),
            "asn": match.get("asn"),
            "org": match.get("org"),
            "hostnames": match.get("hostnames", []),
            "location": match.get("location", {}),
            "vulnerabilities": match.get("vulns", {}),
            "cpe": match.get("cpe", []),
            "banner": match.get("data"),
            "timestamp": match.get("timestamp"),
            "source": "shodan"
        }
        asset["category"] = clasificar_activo_shodan(asset)
        assets.append(asset)

    save_in_database(db, {"shodan_assets": assets}, company_name)

    print(f"[+] Guardados {len(assets)} activos de Shodan.")
