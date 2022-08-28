import datetime

from src.constants import MONGO_CLIENT
from src.ylytic_schema_constants import SHOPIFY_DB, SHOPIFY_PROFILES


class ShopifyProfileRepository:
    def __init__(self):
        self.schema = MONGO_CLIENT[SHOPIFY_DB][SHOPIFY_PROFILES]

    def create(self, document):
        document['created_at'] = datetime.datetime.utcnow()
        document['updated_at'] = datetime.datetime.utcnow()
        self.schema.insert_one(document=document)

    def read(self, user_id):
        return self.schema.find_one(filter={'user_id': user_id, 'deleted': {'$ne': True}})

    def read_all(self):
        docs = []
        cursor = self.schema.find(filter={'deleted': {'$ne': True}})
        for doc in cursor:
            docs.append(doc)
        return docs

    def delete(self, shop):
        self.schema.update_one(filter={'shop': shop, 'deleted': {'$ne': True}},
                               update={'$set': {'updated_at': datetime.datetime.utcnow(),
                                                'deleted': True, 'deleted_at': datetime.datetime.utcnow()}})

    def get_shop(self, shop):
        return self.schema.find_one(filter={'shop': shop, 'deleted': {'$ne': True}})

if __name__ == '__main__':
    shopify_profiles = ShopifyProfileRepository()
    # print(shopify_profiles.read_all())
