from flask import request, abort
import requests
import logging
import json

# for verification
from functools import wraps
import base64
import hmac
import hashlib
import re

from src.constants import SHOPIFY_API_VERSION, SHOPIFY_API_KEY, SHOPIFY_SECRET, SHOPIFY_SCOPES, SHOPIFY_BASE_URL, \
    SHOPIFY_APP_NAME

NONCE = None
REQUEST_METHODS = {
    "GET": requests.get,
    "POST": requests.post,
    "PUT": requests.put,
    "DEL": requests.delete
}


class ShopifyApi:

    @staticmethod
    def authenticate(shop, code):
        url = f"https://{shop}/admin/oauth/access_token"
        payload = {
            "client_id": SHOPIFY_API_KEY,
            "client_secret": SHOPIFY_SECRET,
            "code": code
        }
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            return response.json()['access_token']
        except Exception as e:
            logging.exception(e)
            return None

    def authenticated_shopify_call(self, shop, access_token, call_path, method, params=None, payload=None, headers={}):
        url = f"https://{shop}/admin/api/{SHOPIFY_API_VERSION}/{call_path}"
        request_func = REQUEST_METHODS[method]
        headers['X-Shopify-Access-Token'] = access_token
        try:
            response = request_func(url, params=params, json=payload, headers=headers)
            response.raise_for_status()
            # print(f"authenticated_shopify_call response:\n{json.dumps(response.json(), indent=4)}")
            return response.json()
        except Exception as ex:
            logging.exception(ex)
            return None

    def create_webhook(self, shop, access_token, address: str, topic: str) -> dict:
        call_path = f'webhooks.json'
        method = 'POST'
        payload = {
            "webhook": {
                "topic": topic,
                "address": address,
                "format": "json"
            }
        }
        webhook_response = self.authenticated_shopify_call(shop, access_token, call_path=call_path, method=method,
                                                           payload=payload)
        if not webhook_response:
            return None
        return webhook_response['webhook']

    def generate_install_redirect_url(self, shop, nonce):
        redirect_url = f"https://{shop}/admin/oauth/authorize?client_id={SHOPIFY_API_KEY}&scope={SHOPIFY_SCOPES}&redirect_uri={SHOPIFY_BASE_URL + '/connect'}&state={nonce}"
        return redirect_url

    def generate_post_install_redirect_url(self, shop):
        redirect_url = f"https://{shop}/admin/apps/{SHOPIFY_APP_NAME}"
        return redirect_url


def verify_web_call(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        get_args = request.args
        hmac = get_args.get('hmac')
        sorted(get_args)
        data = '&'.join([f"{key}={value}" for key, value in get_args.items() if key != 'hmac']).encode('utf-8')
        if not verify_hmac(data, hmac):
            logging.error(f"HMAC could not be verified: \n\thmac {hmac}\n\tdata {data}")
            abort(401)

        shop = get_args.get('shop')
        if shop and not is_valid_shop(shop):
            logging.error(f"Shop name received is invalid: \n\tshop {shop}")
            abort(401)
        return f(*args, **kwargs)

    return wrapper


def verify_webhook_call(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            encoded_hmac = request.headers.get('X-Shopify-Hmac-Sha256')
            hmac = base64.b64decode(encoded_hmac).hex()

            data = request.get_data()
            if not verify_hmac(data, hmac):
                logging.error(f"HMAC could not be verified: \n\thmac {hmac}\n\tdata {data}")
                abort(401)
            return f(*args, **kwargs)
        except Exception as ex:
            logging.error(ex)
            abort(401)

    return wrapper


def verify_hmac(data, original_hmac):
    new_hmac = hmac.new(SHOPIFY_SECRET.encode('utf-8'), data, hashlib.sha256)
    return new_hmac.hexdigest() == original_hmac


def is_valid_shop(shop):
    shopname_regex = r'[a-zA-Z0-9][a-zA-Z0-9\-]*\.myshopify\.com[\/]?'
    return re.match(shopname_regex, shop)


if __name__ == '__main__':
    print(base64.b64decode('').hex())
