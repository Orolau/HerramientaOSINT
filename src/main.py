from modules.domains_module import get_domains_WHOISXMLAPI, get_crtsh_and_classify, get_subdomains, mark_excluded_domains_for_subdomain_search
from modules.mongodb_management import connect_database
from modules.asn_module import get_asn_info
from modules.ia_module import get_related_company_names
from modules.whois_module import get_whois_all_domains
from modules.reports_module import generar_informe_pdf
from modules.locations_module import get_company_locations_serpapi
from modules.employees_module import get_company_employees_serpapi
from modules.shodan_module import shodan_get_assets
from modules.leaks_module import search_all_domains_leaks
from modules.graph_module import create_graph
def show_menu():

    print("\n========= MÓDULOS DISPONIBLES =========")
    print("1  - Buscar nombres de empresa relacionados (IA)")
    print("2  - Obtener dominios desde crt.sh")
    print("3  - Obtener dominios desde WHOISXMLAPI")
    print("4  - Buscar subdominios")
    print("5  - Obtener WHOIS de dominios")
    print("6  - Buscar filtraciones de dominios")
    print("7  - Obtener información de ASN")
    print("8  - Buscar activos expuestos (Shodan)")
    print("9  - Buscar localizaciones de la empresa")
    print("10 - Buscar empleados de la empresa")
    print("11 - Generar informe PDF")
    print("12 - Generar grafo de infraestructura")
    print("0  - Ejecutar todo")
    print("========================================")


def main():

    db = connect_database()

    company = input("Introduce el nombre de la empresa: ")

    show_menu()

    selected = input(
        "\nIntroduce los números de los módulos separados por coma (ej: 1,2,5,11): "
    )

    if selected.strip() == "0":

        get_related_company_names(company, db)
        get_crtsh_and_classify(company, db)
        get_domains_WHOISXMLAPI(company, db)
        mark_excluded_domains_for_subdomain_search(company, db)
        get_subdomains(company, db)
        get_whois_all_domains(company, db)
        search_all_domains_leaks(company, db)
        get_asn_info(company, db)
        shodan_get_assets(company, db)
        get_company_locations_serpapi(company, db)
        get_company_employees_serpapi(company, db)
        generar_informe_pdf(company, db)
        create_graph(company, db)

        return

    modules = [m.strip() for m in selected.split(",")]

    for m in modules:

        if m == "1":
            get_related_company_names(company, db)

        elif m == "2":
            get_crtsh_and_classify(company, db)

        elif m == "3":
            get_domains_WHOISXMLAPI(company, db)

        elif m == "4":
            mark_excluded_domains_for_subdomain_search(company, db)
            get_subdomains(company, db)

        elif m == "5":
            get_whois_all_domains(company, db)

        elif m == "6":
            search_all_domains_leaks(company, db)

        elif m == "7":
            get_asn_info(company, db)

        elif m == "8":
            shodan_get_assets(company, db)

        elif m == "9":
            get_company_locations_serpapi(company, db)

        elif m == "10":
            get_company_employees_serpapi(company, db)

        elif m == "11":
            generar_informe_pdf(company, db)

        elif m == "12":
            create_graph(company, db)

        else:
            print(f"[!] Módulo desconocido: {m}")


if __name__ == "__main__":
    main()