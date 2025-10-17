from modules.domains_module import get_domains, get_subdomains, delete_not_included_domains
from modules.mongodb_management import connect_database

def main():
    db = connect_database()

    company = input("Introduce el nombre de la empresa: ")
    get_domains(company, db)
    delete_not_included_domains(company, db)
    #get_subdomains(company, db)

if __name__ == "__main__":
    main()