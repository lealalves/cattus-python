from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

mongo_uri = os.getenv('MONGO_URI')
client = MongoClient(mongo_uri)
db = os.getenv('DB_NAME')  # Nome do banco de dados
collection = os.getenv('COLLECTION_NAME')  # Nome da coleção

def get_collection():
    return collection