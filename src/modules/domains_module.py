import requests
import os
from dotenv import load_dotenv
import json

from modules.mongodb_management import save_in_database
from modules.make_requests import make_POST_request


# URL del endpoint de la API - dominios y subdominios
url = "https://domains-subdomains-discovery.whoisxmlapi.com/api/v1" 

# Cargar api key
load_dotenv()
API_KEY = os.getenv("API_KEY_DOMAINS")

def saveDomainData(data, company_name, db):
    jsonData = json.loads(data)
    save_in_database(db, {"domains": jsonData["domainsList"]}, company_name)
    print("Datos guardados")

def onError(error_code):
    print(f"Error: {error_code}")

def get_domains(company_name, db):
    payload = {
        "apiKey": API_KEY,
        "domains": {
            "include": [
                f"{company_name}.*"
            ]
        }
    }
    headers = {
        "Content-Type": "application/json"
    }   

    make_POST_request(lambda data: saveDomainData(data, company_name, db), onError, url, payload, headers)
