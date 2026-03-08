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

def main():
    db = connect_database()
    
    company = input("Introduce el nombre de la empresa: ")
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
    

if __name__ == "__main__":
    main()