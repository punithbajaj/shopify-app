import datetime

from flask import jsonify, Blueprint, request, Response, redirect
import json

from src.connectors.shopify.shopify_api import ShopifyApi, verify_web_call, verify_webhook_call
from src.constants import SHOPIFY_BASE_URL, BASE_URL

from src.auth_bo import auth, verify_token
from src.users.users_bo import UsersBO
from src.connectors.shopify.bo.shopify_profiles_bo import ShopifyProfilesBO
from src.connectors.shopify.bo.nonce_bo import NonceBO
from src.connectors.shopify.bo.shopify_payment import ShopifyPayment
import logging
from src.commons.discord.discord_service import DiscordService

shopify_blueprint = Blueprint('shopify', __name__, url_prefix='/connectors/shopify/api/v1/')

nonce_bo = NonceBO()
users_bo = UsersBO()
shopify_profiles_bo = ShopifyProfilesBO()
shopify_api = ShopifyApi()
logger = logging.getLogger("shopify-app")
discord_service = DiscordService()
shopify_payment = ShopifyPayment()

@shopify_blueprint.route('/ping')
def index():
    return jsonify({'status': 'Welcome to Ylytic shopify Connector!'})


@shopify_blueprint.route('/install', methods=['GET'])
@auth.login_required()
def app_install():
    try:
        if request.args.get('shop'):
            shop = request.args.get('shop')
            if shopify_profiles_bo.get_shop_profile(shop):
                return Response(response=f"{shop} already registered", status=403)
        else:
            return Response(response="Error:parameter shop not found", status=500)

        NONCE = nonce_bo.create(shop)

        auth_url = shopify_api.generate_install_redirect_url(shop, NONCE)
        return jsonify({'redirectURL': auth_url})
    except Exception as ex:
        logger.error(ex)
        return Response(response=str(ex), status=500)


@shopify_blueprint.route('/app', methods=['GET'])
@verify_web_call
def app_display():
    try:
        if request.args.get('shop'):
            shop = request.args.get('shop')
            shop_profile = shopify_profiles_bo.get_shop_profile(shop)
            if shop_profile is None:

                NONCE = nonce_bo.create(shop)
                auth_url = shopify_api.generate_install_redirect_url(shop, NONCE)
                response = redirect(auth_url)
                header = "frame-ancestors %s admin.shopify.com" % shop
                logger.info(header)
                response.headers['Content-Security-Policy'] = header
                response.headers['Access-Control-Allow-Origin'] = '*'
                return response
            else:
                user = users_bo.get_complete_user(shop_profile['user_id'])
                token = users_bo.get_token(user)
                return redirect(BASE_URL + f'/login?token={token}&initialConnector=shopify')
        return Response(response="Error: Parameter shop not found", status=400)

    except Exception as ex:
        logger.error(ex)
        discord_service.alert(category='shopify_app', message='error in while connecting from store (/app)',
                              value=str(ex))
        return redirect(BASE_URL + '/login?error=something went wrong, please try again after sometime.')


@shopify_blueprint.route('/connect', methods=['GET'])
@verify_web_call
def app_connect():
    try:
        state = request.args.get('state')
        shop = request.args.get("shop")
        code = request.args.get("code")

        data = nonce_bo.get_by_data(shop, state)
        if data is None:
            return "Invalid `state` received", 400

        nonce_bo.delete(state)

        if shopify_profiles_bo.get_shop_profile(shop):
            return redirect(BASE_URL + '/dashboard')

        access_token = shopify_api.authenticate(shop=shop, code=code)

        uninstall_url = SHOPIFY_BASE_URL + '/uninstall'
        shopify_api.create_webhook(shop, access_token, uninstall_url, "app/uninstalled")

        # url = SHOPIFY_BASE_URL + '/update_onetime_subscription'
        # shopify_api.create_webhook(shop, access_token, url, "app_purchases_one_time/update")

        url = SHOPIFY_BASE_URL + '/update_onetime_subscription'
        shopify_api.create_webhook(shop, access_token, url, "app_subscriptions/update")

        redirect_url = BASE_URL + f'/shopifyReconnect?shop={shop}&access_token={access_token}'
        return redirect(redirect_url)
    except Exception as ex:
        logger.error(ex)
        discord_service.alert(category='shopify_app', message='error in while installing from store (/connect)',
                              value=str(ex))
        return redirect(BASE_URL + '/login?error=something went wrong, please try again after sometime.')


@shopify_blueprint.route('/redirect', methods=['PUT'])
@auth.login_required()
def app_redirect():
    try:
        user = auth.current_user()
        id = user['id']

        data = json.loads(request.data)
        shop = data['shop']
        access_token = data['access_token']

        shop_details = shopify_profiles_bo.get_shop_details(shop, access_token)
        if shop_details is None:
            logger.info(data)
            print(f'Wrong shop: {shop} and access_token: {access_token}')
            return Response(response=f"Shop and access_token are invalid")

        shopify_profiles_bo.create_user_profile(id, shop, access_token, shop_details)
        users_bo.update_user(user_id=id, document={'shopify_connected': True})
        users_bo.new_update_profile(user_id=id, data=data)

        return jsonify({'status': 200})

    except Exception as ex:
        print(ex)
        logger.error(ex)
        discord_service.alert(category='shopify_app', message='error in redirect (/redirect)',
                              value=str(ex))
        return redirect(BASE_URL + '/login?error=something went wrong, please try again after sometime.')


@shopify_blueprint.route('/storesignup', methods=['PUT'])
def app_store_singup():
    try:
        data = json.loads(request.data)
        shop = data['shop']
        access_token = data['access_token']

        shop_details = shopify_profiles_bo.get_shop_details(shop, access_token)
        if shop_details is None:
            logger.info(data)
            print(f'Wrong shop: {shop} and access_token: {access_token}')
            return Response(response=f"Shop and access_token are invalid")

        email = shop_details['email']

        user = users_bo.find_user_doc({'email': email})
        if user is not None:
            if user['shopify_connected']:
                # TODO here we are not connecting shop to any user (multiple store scenario)
                return Response(response=f"{email} is already connected to another store")
            token = users_bo.get_token(user)
            id = str(user['_id'])
        else:
            password = users_bo.generate_random_password()
            token = users_bo.register(email=email,
                                      password=password,
                                      first_name=shop_details['first_name'],
                                      last_name=shop_details['last_name'],
                                      agent=str(request.headers.get('User-Agent')),
                                      source_ip=str(request.remote_addr),
                                      user_source='shopify app store',
                                      initial_connector='shopify',
                                      shopify_connected=True,
                                      )
            user_info = verify_token(token)
            id = user_info['id']
            print(shop_details['email'], password)

        shopify_profiles_bo.create_user_profile(id, shop, access_token, shop_details)
        users_bo.new_update_profile(user_id=id, data=data)
        return jsonify({'status': 200, 'token': token, 'initial_connector': 'shopify',
                        'info': f'You logged in as {shop_details["email"]}.',
                        'user_id': id})

    except Exception as ex:
        logger.error(ex)
        print('error:', ex)
        discord_service.alert(category='shopify_app', message='error in redirect (/storessignup)',
                              value=str(ex))
        return redirect(BASE_URL + '/login?error=something went wrong, please try again after sometime.')


@shopify_blueprint.route('/uninstall', methods=['POST'])
@verify_webhook_call
def app_uninstalled():
    try:
        webhook_payload = request.get_json()
        logger.info(webhook_payload)
        shop = webhook_payload['myshopify_domain']
        shop_profile = shopify_profiles_bo.get_shop_profile(shop)
        if shop_profile is not None:
            users_bo.update_user(user_id=shop_profile['user_id'],
                                 document={
                                    'stage': 'nudgeSelection',
                                    'shopify_connected': False,
                                })
            shopify_profiles_bo.delete_user_profile(shop)

        print(f"uninstalled {shop}")
        discord_service.alert(category='shopify_app', message=f'shop ({shop}) uninstalled',
                              value=str(webhook_payload))
        return jsonify({'status': 200})
    except Exception as ex:
        print('uninstall er:', ex)
        logger.error(ex)
        discord_service.alert(category='shopify_app', message=f'error in shop ({shop}) uninstallation',
                              value=str(webhook_payload))
        return jsonify({'status': 200}), 500


@shopify_blueprint.route('/payment_redirect', methods=['GET'])
def payment_redirect():
    try:
        if request.args.get('charge_id'):
            charge_id = request.args.get('charge_id')
            print(charge_id)

            user = users_bo.find_user_doc({
                'pricing.shopify.charge_id': 'gid://shopify/AppSubscription/' + str(charge_id)
            })

            if user is None:
                return redirect(BASE_URL + '/login?error=Something went wrong')

            shop_details = shopify_profiles_bo.get_by_user(str(user['_id']))
            subscription_info = shopify_payment.get_subscription(shop_details['shop'], shop_details['access_token'], charge_id)

            if subscription_info is not None:
                discord_service.alert(category='shopify_app', message=f"New subscription by {user['email']}", value=str(subscription_info))
                users_bo.update_user(user_id=str(user['_id']), document={
                    'pricing.current_plan': subscription_info['name'],
                    'pricing.shopify.current_plan': subscription_info['name'],
                    'pricing.shopify.status': 'active',
                    'pricing.shopify.trial_ends_on': datetime.datetime.fromisoformat(subscription_info['trial_ends_on']),
                    'pricing.plan_expiry_date': datetime.datetime.fromisoformat(subscription_info['billing_on']),
                })

                return redirect(BASE_URL + '/dashboard?success=Payment was successful')

        return redirect(BASE_URL + '/login?error=something went wrong, contact the team for details')

    except Exception as ex:
        logger.error(ex)
        discord_service.alert(category='shopify_app', message='error in shopify payment redirect (/payment_redirect)',
                              value=str(ex))
        print(ex)
        return redirect(BASE_URL + '/login?error=something went wrong, please try again after sometime.')



@shopify_blueprint.route('/update_onetime_subscription', methods=['POST'])
@verify_webhook_call
def subscription_updated():
    print('called /update_onetime')
    try:
        webhook_payload = request.get_json()
        logger.info(webhook_payload)
        shop = webhook_payload['domain']  # domain or myshopify_domain
        shop_profile = shopify_profiles_bo.get_shop_profile(shop)
        print(webhook_payload)
        if shop_profile is not None:
            pass

        print(f"sub updated {shop}")
        discord_service.alert(category='shopify_app', message=f'shop ({shop}) uninstalled',
                              value=str(webhook_payload))
        return jsonify({'status': 200})
    except Exception as ex:
        print('subscription update er:', ex)
        logger.error(ex)
        return jsonify({'status': 200})


@shopify_blueprint.route('/customer_data_request', methods=['GET', 'POST'])
@verify_webhook_call
def customer_data_request():
    try:
        webhook_payload = request.get_json()
        data = shopify_profiles_bo.get_customer_data(webhook_payload['customer']['id'])
        return jsonify({'status': 200, 'data': data})
    except Exception as ex:
        print('in exception', ex)
        logger.error(ex)
        discord_service.alert(category='shopify_app', message='error in customer_data_request', value=str(webhook_payload))
        return jsonify({'status': 200, 'data': []})


@shopify_blueprint.route('/customer_redact', methods=['GET', 'POST'])
@verify_webhook_call
def customer_redact():
    try:
        webhook_payload = request.get_json()
        shopify_profiles_bo.delete_customer_data(webhook_payload['customer']['id'])
        return jsonify({'status': 200, 'data': []})
    except Exception as ex:
        print('in exception', ex)
        logger.error(ex)
        discord_service.alert(category='shopify_app', message='error in customer_redact', value=str(webhook_payload))
        return jsonify({'status': 200, 'data': []})


@shopify_blueprint.route('/shop_redact', methods=['GET', 'POST'])
@verify_webhook_call
def shop_redact():
    try:
        webhook_payload = request.get_json()
        shopify_profiles_bo.delete_shop_data(webhook_payload['shop_domain'])
        return jsonify({'status': 200, 'data': []})
    except Exception as ex:
        print('in exception', ex)
        logger.error(ex)
        discord_service.alert(category='shopify_app', message='error in shop_redact', value=str(webhook_payload))
        return jsonify({'status': 200, 'data': []})


@shopify_blueprint.route('/profile', methods=['GET'])
@auth.login_required()
def get_profile():
    try:
        user = auth.current_user()
        id = user['id']
        shop_details = shopify_profiles_bo.get_by_user(id)

        return jsonify({
            'user_name':  shop_details['user_name'],
            'shop': shop_details['shop'],
            'created_at': shop_details['created_at']
        })

    except Exception as ex:
        print(ex)
        logger.error(ex)
        return jsonify({'status': 500})

