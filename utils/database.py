import os

import pymongo
from dotenv import load_dotenv

load_dotenv('.env')
client = pymongo.MongoClient(
    f"{os.getenv('DATABASE_LINK')}")

db = client['cluster0']

collection = db["cluster0"]
modmail_collection = db["mod-mail"]
