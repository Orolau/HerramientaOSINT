from pymongo import MongoClient
from dotenv import load_dotenv
import os

def connect_database():
    # Cargar variables del entorno
    load_dotenv()
    # Conexión con MongoDB
    client = MongoClient(os.getenv("MONGO_URI"))
    db = client[os.getenv("MONGO_DB")]
    return db


def save_in_database(db, data, company_name):
    db[company_name].insert_one(data)
