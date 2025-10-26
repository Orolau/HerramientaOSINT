from pymongo import MongoClient
from dotenv import load_dotenv
import os
from datetime import datetime

def connect_database():
    # Cargar variables del entorno
    load_dotenv()
    # Conexión con MongoDB
    client = MongoClient(os.getenv("MONGO_URI"))
    db = client[os.getenv("MONGO_DB")]
    return db


def save_in_database(db, data, company_name):
    date_str = datetime.now().strftime("%Y%m%d")
    db[date_str].update_one({"company": company_name}, {"$set": data}, upsert = True)

def add_to_database_field(db, company_name, field_name, new_data):
    """
    Añade (fusiona) nuevos pares clave-valor a un campo tipo diccionario.
    - db: objeto de la base de datos
    - company_name: nombre de la empresa
    - field_name: nombre del campo (por ejemplo 'domains')
    - new_data: diccionario con los nuevos valores (por ejemplo {'dominio3': {}, 'dominio4': {}})
    """
    if not isinstance(new_data, dict):
        raise ValueError("'new_data' debe ser un diccionario.")

    date_str = datetime.now().strftime("%Y%m%d")

    # Intentamos obtener el documento actual
    existing = db[date_str].find_one({"company": company_name}, {field_name: 1})
    existing_data = existing.get(field_name, {}) if existing else {}

    # Fusionar los diccionarios (sin eliminar claves existentes)
    merged = {**existing_data, **new_data}

    # Guardar el resultado fusionado
    db[date_str].update_one(
        {"company": company_name},
        {"$set": {field_name: merged}},
        upsert=True
    )
