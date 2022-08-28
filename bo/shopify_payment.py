from flask import jsonify
import logging
from src.connectors.shopify.shopify_api import ShopifyApi
from src.constants import BASE_URL

logger = logging.getLogger("shopify-payment")
shopify_api = ShopifyApi()


class ShopifyPayment:
    def __init__(self):
        pass

    def make_subscription_payment(self, shop, access_token, plan, redirect_url, test=False):
        try:
            endpoint = f"graphql.json"
            payload = {
                "query": "mutation AppSubscriptionCreate($name: String!, $lineItems: [AppSubscriptionLineItemInput!]!, $returnUrl: URL!, $trialDays: Int, $test: Boolean){ appSubscriptionCreate(name: $name, returnUrl: $returnUrl, lineItems: $lineItems, trialDays: $trialDays, test: $test) { userErrors { field message } appSubscription { id } confirmationUrl } }",
                "variables": {
                    "name": plan['name'],
                    "returnUrl": redirect_url,
                    "trialDays": plan['trial_days'],
                    "test": test,
                    "lineItems": [
                        {
                            "plan": {
                                "appRecurringPricingDetails": {
                                    "price": {
                                        "amount": plan['amount'],
                                        "currencyCode": "USD"
                                    },
                                    "interval": plan['interval']
                                },
                            }
                        }
                    ]
                }
            }
            data = shopify_api.authenticated_shopify_call(shop, access_token, endpoint, 'POST', payload=payload)
            print(data)
            return data['data']['appSubscriptionCreate']
        except Exception as ex:
            print(ex)
            logger.error(ex)
            return {'status': 500}


    def make_onetime_payment(self, shop, access_token, plan, redirect_url, test=False):
        try:
            endpoint = f"graphql.json"
            payload = {
                "query": "mutation appPurchaseOneTimeCreate($name: String!, $price: MoneyInput!, $returnUrl: URL!, $test: Boolean) {appPurchaseOneTimeCreate(name: $name, price: $price, returnUrl: $returnUrl, test: $test) {userErrors { field message } appPurchaseOneTime { id } confirmationUrl }}",
                "variables": {
                    "name": plan['name'],
                    "returnUrl": redirect_url,
                    "test": test,
                    "price": {
                        "amount": plan['amount'],
                        "currencyCode": "USD"
                    },
                }
            }
            data = shopify_api.authenticated_shopify_call(shop, access_token, endpoint, 'POST', payload=payload)
            print(data)
            return data['data']['appPurchaseOneTimeCreate']
        except Exception as ex:
            print(ex)
            logger.error(ex)
            return jsonify({'status': 500})


    def cancel_payment(self, shop, access_token, subscription_id):
        try:
            endpoint = f"graphql.json"
            payload = {
                "query": "mutation AppSubscriptionCancel($id: ID!){appSubscriptionCancel(id: $id) {userErrors {field message} appSubscription {id status}}}",
                "variables": {
                    "id": subscription_id
                }
            }
            data = shopify_api.authenticated_shopify_call(shop, access_token, endpoint, 'POST', payload=payload)
            print(data)
            return data
        except Exception as ex:
            print(ex)
            logger.error(ex)
            return jsonify({'status': 500})

    def get_subscriptions(self, shop, access_token):
        try:
            endpoint = f"recurring_application_charges.json"
            data = shopify_api.authenticated_shopify_call(shop, access_token, endpoint, 'GET')
            print(data)
            return data
        except Exception as ex:
            print(ex)
            logger.error(ex)
            return jsonify({'status': 500})

    def get_subscription(self, shop, access_token, subsrciption_id):
        try:
            endpoint = f"recurring_application_charges/{subsrciption_id}.json"
            data = shopify_api.authenticated_shopify_call(shop, access_token, endpoint, 'GET')

            print(data)
            if data is not None:
                return data['recurring_application_charge']

            return None
        except Exception as ex:
            print(ex)
            logger.error(ex)
            return jsonify({'status': 500})

if __name__ == '__main__':
    plan = {
        'name': "Super Duper Recurring Plan with a Trial",
        'trial_days': 30,
        'amount': 4.99,
    }
    shopify_payment = ShopifyPayment()
    # make_onetime_payment('testylyticapp2.myshopify.com', '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', test=True)
    # data = make_subscription_payment('ylytic-app-dev.myshopify.com', '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', plan, test=True)
    # cancel_payment('ylytic-app-dev.myshopify.com', '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', "gid://shopify/AppSubscription/22761472089")
    # get_subscriptions('ylytic-app-dev.myshopify.com', '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')
    data = shopify_payment.get_subscription('ylytic-app-dev.myshopify.com', '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', '22764814425')
    print(data)
