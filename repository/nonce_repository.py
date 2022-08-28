import datetime

from src.constants import MONGO_CLIENT
from src.ylytic_schema_constants import SHOPIFY_DB, NONCE_DB


class NonceRepository:
    def __init__(self):
        self.schema = MONGO_CLIENT[SHOPIFY_DB][NONCE_DB]

    def create(self, document):
        document['created_at'] = datetime.datetime.utcnow()
        self.schema.insert_one(document=document)

    def get(self, data, state):
        return self.schema.find_one(filter={'data': data, 'nonce': state})

    def delete(self, nonce):
        self.schema.delete_one({'nonce': nonce})
