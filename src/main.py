from dotenv import load_dotenv
import os
from modules.domains_module import get_domains
from modules.mongodb_management import connect_database

def main():
    db = connect_database()

    company = input("Introduce el nombre de la empresa: ")
    get_domains(company, db)

if __name__ == "__main__":
    main()