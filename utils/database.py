import os

import pymongo
from dotenv import load_dotenv

load_dotenv('.env')
client = pymongo.MongoClient(
    f"mongodb+srv://{os.getenv('DATABASE_NAME')}:{os.getenv('DATABASE_PASS')}@cluster0.3pkiv.mongodb.net/cluster0?retryWrites=true&w=majority")

db = client['cluster0']

collection = db["cluster0"]
modmail_collection = db["mod-mail"]
prefix_collection = db["prefix"]