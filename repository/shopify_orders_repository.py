import datetime

from src.constants import MONGO_CLIENT
from src.ylytic_schema_constants import SHOPIFY_DB, SHOPIFY_ORDERS


class ShopifyOrdersRepository:
    def __init__(self):
        self.schema = MONGO_CLIENT[SHOPIFY_DB][SHOPIFY_ORDERS]

    def create(self, document):
        db_document = self.schema.find_one(filter={'user_id': document['user_id'], 'order_id': document['order_id'], 'deleted': {'$ne': True}})
        if db_document is None:
            document['created_at'] = datetime.datetime.utcnow()
            document['updated_at'] = datetime.datetime.utcnow()
            self.schema.insert_one(document=document)
        else:
            self.schema.update_one(filter={'user_id': document['user_id'], 'order_id': document['order_id'], 'deleted': {'$ne': True}},
                                   update={
                                       '$set': {'updated_at': datetime.datetime.utcnow(), 'order': document['order']}})

    def get_all_orders(self, user_id):
        docs = []
        cursor = self.schema.find(filter={'user_id': user_id, 'deleted': {'$ne': True}})
        for doc in cursor:
            docs.append(doc)
        return docs

    def delete_orders_by_customer(self, customer_id):
        self.schema.update(filter={'order.customer.id': customer_id},
                            update={
                                '$set': {'updated_at': datetime.datetime.utcnow(), 'deleted': True}})

    def delete_orders_by_shop(self, shop):
        self.schema.update(filter={'shop': shop},
                           update={
                               '$set': {'updated_at': datetime.datetime.utcnow(), 'deleted': True}})

    def get_orders_by_customer(self, customer_id):
        docs = []
        cursor = self.schema.find(filter={'order.customer.id': customer_id, 'deleted': {'$ne': True}})
        for doc in cursor:
            docs.append(doc)
        return docs

    def get_orders(self, user_id, start_date, end_date):
        return list(self.schema.find(filter={
                'user_id': user_id,
                'created_at': {'$gte': start_date, '$lt': end_date},
            }))

if __name__ == '__main__':
    p = ShopifyOrdersRepository()
    p.schema.delete_many(filter={'shop': 'dwyerhomecollection.myshopify.com'})
    # x = p.get_all_orders('62867d506c33cb13cf05dd30')
    # for ord in x:
    #     print(ord['order']['created_at'], ord['order']['current_total_price'])
