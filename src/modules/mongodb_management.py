from pymongo import MongoClient
from dotenv import load_dotenv
import os
from datetime import datetime
import certifi

def connect_database():
    # Cargar variables del entorno
    load_dotenv()
    # Conexión con MongoDB
    client = MongoClient(os.getenv("MONGO_URI"), tls=True,tlsCAFile=certifi.where())
    db = client[os.getenv("MONGO_DB")]
    return db


def save_in_database(db, data, company_name, date=None):
    if not date:
        date_str = datetime.now().strftime("%Y%m%d")
    else:
        date_str = date
    db[date_str].update_one({"company": company_name}, {"$set": data}, upsert = True)

def add_to_database_field(db, company_name, field_name, new_data):
    if not isinstance(new_data, list):
        raise ValueError("'new_data' debe ser una lista.")

    date_str = datetime.now().strftime("%Y%m%d")

    db[date_str].update_one(
        {"company": company_name},
        {"$push": {field_name: {"$each": new_data}}},
        upsert=True
    )

def update_domain_entry(db, company_name, field_name, domain_name, new_data):
    if not isinstance(new_data, dict):
        raise ValueError("'new_data' debe ser un diccionario.")

    date_str = datetime.now().strftime("%Y%m%d")

    # Buscar el documento y el índice del dominio dentro de la lista
    record = db[date_str].find_one(
        {"company": company_name, field_name: {"$elemMatch": {"name": domain_name}}},
        {f"{field_name}.$": 1}
    )

    if not record or field_name not in record:
        print(f"[!] El dominio '{domain_name}' no existe en '{field_name}', no se actualizará.")
        return

    # Obtener el elemento existente (el que coincide con name)
    existing_entry = record[field_name][0]

    # Fusionar los datos nuevos con los existentes
    updated_entry = {**existing_entry, **new_data}

    # Reemplazar el elemento correspondiente dentro del array
    result = db[date_str].update_one(
        {"company": company_name, f"{field_name}.name": domain_name},
        {"$set": {f"{field_name}.$": updated_entry}}
    )

    if not result.modified_count > 0:
        print(f"[!] No se modificó '{domain_name}' en '{field_name}'.")