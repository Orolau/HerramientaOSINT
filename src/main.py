from modules.domains_module import get_domains_WHOISXMLAPI, get_crtsh_and_classify, get_subdomains, delete_not_included_domains
from modules.mongodb_management import connect_database
from modules.asn_module import get_asn_info
from modules.ia_module import get_related_company_names
from modules.whois_module import get_whois_all_domains

def main():
    db = connect_database()

    company = input("Introduce el nombre de la empresa: ")
    get_related_company_names(company, db)
    get_crtsh_and_classify(company, db)
    #get_domains_WHOISXMLAPI(company, db)
    get_whois_all_domains(company, db)
    #delete_not_included_domains(company, db)
    get_asn_info(company, db)
    #get_subdomains(company, db)

if __name__ == "__main__":
    main()