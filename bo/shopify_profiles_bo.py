from src.connectors.shopify.shopify_api import ShopifyApi
from src.connectors.shopify.repository.shopify_profiles_repository import ShopifyProfileRepository
from src.connectors.shopify.repository.shopify_orders_repository import ShopifyOrdersRepository

import datetime
import json


class ShopifyProfilesBO:
    def __init__(self):
        self.repository = ShopifyProfileRepository()
        self.shopify_api = ShopifyApi()
        self.orders_repository = ShopifyOrdersRepository()

    def create_user_profile(self, id, shop, access_token, shop_details):
        document = {
            'user_id': id,
            'shop': shop,
            'access_token': access_token,
            'user_name': shop_details['first_name'] + ' ' + shop_details['last_name'],
            'email': shop_details['email'],
            'currency': shop_details['currency']
        }
        self.repository.create(document)

    def get_all_active_shopify_profiles(self):
        return list(self.repository.read_all())

    def delete_user_profile(self, shop):
        self.repository.delete(shop)

    def get_shop_profile(self, shop):
        return self.repository.get_shop(shop)

    def get_by_user(self, user_id):
        return self.repository.read(user_id)

    def update_orders_database(self):
        users = self.repository.read_all()
        for user in users:
            self.update_user_orders(user['user_id'])

        print('orders database updated successfully')

    def update_user_orders(self, user_id, updated_at_min=None):
        try:
            user = self.repository.read(user_id)
            if user is not None:
                data = self._fetch_orders(user['shop'], user['access_token'], updated_at_min)
                orders = data['orders']
                for order in orders:
                    document = {
                        'user_id': user_id,
                        'order_id': order['id'],
                        'created_at': datetime.datetime.fromisoformat(order['created_at']).replace(tzinfo=datetime.timezone.utc),
                        'shop': user['shop'],
                        'order': order,
                    }
                    self.orders_repository.create(document)
        except Exception as e:
            print(e)
            return None

    def _fetch_orders(self, shop, access_token, updated_at_min=None, status='any', limit=250):
        date = '&update_at_min='+str(updated_at_min) if updated_at_min is not None else ''
        endpoint = f"orders.json?status={status}&limit={limit}" + date
        data = self.shopify_api.authenticated_shopify_call(shop, access_token, endpoint, 'GET')
        return data

    def fetch_marketing_details(self, shop, access_token):
        endpoint = f"graphql.json"
        payload = {
            "query": "{ marketingActivities(first: 10) { edges { node { adSpend { amount currencyCode } activityListUrl createdAt formData } } } }"
        }
        data = self.shopify_api.authenticated_shopify_call(shop, access_token, endpoint, 'POST', payload=payload)
        print(data)
        return data

    def fetch_shop_logo(self, shop, access_token):
        data = self.shopify_api.authenticated_shopify_call(shop, access_token, 'themes.json', 'GET')
        print(data)
        for theme in data['themes']:
            print(theme)
            if theme['role'] == 'main':
                asset_data = self.shopify_api.authenticated_shopify_call(shop, access_token, f"themes/{theme['id']}/assets.json?asset[key]=config/settings_data.json", 'GET')
                value = json.loads(asset_data['asset']['value'])['current']['sections']['header']['settings']
                # print(value)
                print(json.dumps(value, indent=4))
                logo_img = value['logo']
                print(logo_img)

    def test(self, shop, access_token):
        endpoint = f"inventory_items.json?ids=41933739524185"
        data = self.shopify_api.authenticated_shopify_call(shop, access_token, endpoint, 'GET')
        print(json.dumps(data, indent=4))
        return data

    def get_customer_data(self, customer_id):
        return self.orders_repository.get_orders_by_customer(customer_id)

    def delete_shop_data(self, shop):
        self.orders_repository.delete_orders_by_shop(shop)

    def delete_customer_data(self, customer_id):
        self.orders_repository.delete_orders_by_customer(customer_id)

    def get_shop_details(self, shop, access_token):
        endpoint = f"shop.json"
        data = self.shopify_api.authenticated_shopify_call(shop, access_token, endpoint, 'GET')
        if data is None:
            return data
        data = data['shop']
        name = data['shop_owner'].split(' ')
        return {
            'email': data['email'],
            'first_name': name[0],
            'last_name': name[-1] if len(name) > 0 else '',
            'currency': data['currency'],
        }


if __name__ == '__main__':
    spb = ShopifyProfilesBO()
    # spb.update_user_orders('111112222')
    spb.update_orders_database()
    # date = datetime.datetime.utcnow()
    # print(spb.last_month_sales('628492174ae2717dcef72746', date))
    # spb.test('ylytic-app-dev.myshopify.com', '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')
    # print(data)