import datetime

from src.constants import MONGO_CLIENT
from src.ylytic_schema_constants import SHOPIFY_DB, SHOPIFY_REPORTS


class ShopifyReportsRepository:
    def __init__(self):
        self.schema = MONGO_CLIENT[SHOPIFY_DB][SHOPIFY_REPORTS]

    def create(self, document):
        db_document = self.schema.find_one(filter={'user_id': document['user_id'],
                                                   'start_date': document['start_date'],
                                                   'end_date': document['end_date']})
        if db_document is None:
            document['created_at'] = datetime.datetime.utcnow()
            document['updated_at'] = datetime.datetime.utcnow()
            self.schema.insert_one(document=document)
        else:
            self.schema.update_one(filter={'user_id': document['user_id'], 'start_date': document['start_date']},
                                   update={
                                       '$set': {'updated_at': datetime.datetime.utcnow(), 'report': document['report']}})

    def get(self, user_id, start_date, end_date):
        return self.schema.find_one(filter={'user_id': user_id, 'start_date': start_date, 'end_date': end_date})

    def sales_this_month(self, user_id, month, year):
        start_date = datetime.datetime(year, month, 1, 0, 0, 0)
        next_end_date = start_date + datetime.timedelta(days=32)
        end_date = datetime.datetime(next_end_date.year, next_end_date.month, 1, 0, 0, 0)
        query = [
            {'$match': {'user_id': user_id, 'frequency': 'daily', 'start_date': {'$gte': start_date, '$lt': end_date}}},
            {'$group': {'_id': "subs", 'sales': {'$sum': '$report.sales'}}}
        ]
        for response in self.schema.aggregate(pipeline=query):
            return response['sales']
        return 0