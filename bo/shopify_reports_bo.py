from src.connectors.shopify.bo.shopify_profiles_bo import ShopifyProfilesBO
from src.connectors.shopify.repository.shopify_reports_repository import ShopifyReportsRepository
from src.connectors.shopify.repository.shopify_orders_repository import ShopifyOrdersRepository
from src.user_targets.user_targets_bo import UserTargetsBO
from datetime import datetime, timedelta, timezone
from dateutil.relativedelta import relativedelta


class ShopifyReportsBO:
    def __init__(self):
        self.shopify_profiles_bo = ShopifyProfilesBO()
        self.reports_repository = ShopifyReportsRepository()
        self.orders_repository = ShopifyOrdersRepository()
        self.user_target = UserTargetsBO()

    # create single report
    def generate_report_data(self, user_id, start_date, end_date):
        shop_details = self.shopify_profiles_bo.get_by_user(user_id)

        self.user_target.create_new_target(user_id, 'shopify', 'monthly', start_date, end_date)

        report = {
            'shop': shop_details['shop'],
            'user_name': shop_details['user_name'],
            'store_currency': shop_details['currency'] if 'currency' in shop_details else 'USD',
            'orders': 0,
            'sales': 0,
            'products': {},
            'locations': {},
        }

        items = self.orders_repository.get_orders(user_id, start_date=start_date, end_date=end_date)
        for item in items:
            order = item['order']

            report['orders'] += 1
            report['sales'] += float(order['total_price'])

            for item in order['line_items']:
                item_id = item['title']
                if item_id not in report['products']:
                    report['products'][item_id] = {
                        'name': item['title'],
                        'sales': 0,
                        'orders': 0,
                    }
                report['products'][item_id]['sales'] += float(item['price']) * float(item['quantity'])
                report['products'][item_id]['orders'] += 1

            try:
                location = order['customer']['default_address']['city']
            except Exception as e:
                location = 'Anonymous'

            if location not in report['locations']:
                report['locations'][location] = {
                    'name': location,
                    'sales': 0,
                    'orders': 0,
                }
            report['locations'][location]['sales'] += float(order['total_price'])
            report['locations'][location]['orders'] += 1

            # if start_date.month == created_at.month and start_date.year == created_at.year and created_at <= end_date:
            #     report['sales'] += float(order['total_price'])

        def get_sales(x):
            return x['sales']

        product_arr = [report['products'][key] for key in report['products']]
        product_arr.sort(key=get_sales, reverse=True)
        total_sales = sum([product['sales'] for product in product_arr])
        for i, item in enumerate(product_arr):
            product_arr[i]['per'] = round(item['sales']*100/total_sales)
        report['products'] = product_arr[:3] # TODO all or 3

        location_arr = [report['locations'][key] for key in report['locations']]
        location_arr.sort(key=get_sales, reverse=True)
        total_sales = report['sales']
        for i, item in enumerate(location_arr):
            location_arr[i]['per'] = round(item['sales']*100/total_sales)
        report['locations'] = location_arr[:3] # TODO all or 3

        report['aov'] = round(report['orders'] and (report['sales'] / report['orders']), 2)

        return report

    # generates all reports
    def generate_daily_reports(self):
        try:
            now = datetime.utcnow()
            date = datetime(now.year, now.month, now.day, 0, 0, 0, tzinfo=timezone.utc)
            users = self.shopify_profiles_bo.get_all_active_shopify_profiles()
            for user in users:
                for i in range(1, 9):
                    start_date = date - timedelta(days=i)
                    end_date = start_date + timedelta(days=1)

                    if self.reports_repository.get(user['user_id'], start_date, end_date) is None:
                        report = self.generate_report_data(user['user_id'], start_date, end_date)
                        document = {
                            'user_id': user['user_id'],
                            'frequency': 'daily',
                            'start_date': start_date,
                            'end_date': end_date,
                            'report': report,
                        }

                        self.reports_repository.create(document)
        except Exception as ex:
            print(ex)

    def generate_weekly_reports(self):
        try:
            now = datetime.utcnow()
            date = datetime(now.year, now.month, now.day, 0, 0, 0, tzinfo=timezone.utc)
            users = self.shopify_profiles_bo.get_all_active_shopify_profiles()
            for user in users:
                for i in range(1, 3):
                    start_date = date - timedelta(days=date.weekday()) - timedelta(days=7) * i
                    end_date = start_date + timedelta(days=6)

                    if self.reports_repository.get(user['user_id'], start_date, end_date) is None:
                        report = self.generate_report_data(user['user_id'], start_date, end_date)
                        document = {
                            'user_id': user['user_id'],
                            'frequency': 'weekly',
                            'start_date': start_date,
                            'end_date': end_date,
                            'report': report,
                        }

                        self.reports_repository.create(document)
        except Exception as ex:
            print(ex)

    def generate_monthly_reports(self):
        try:
            now = datetime.utcnow()
            date = datetime(now.year, now.month, 1, 0, 0, 0, tzinfo=timezone.utc)
            users = self.shopify_profiles_bo.get_all_active_shopify_profiles()
            for user in users:
                for i in range(1, 3):
                    start_date = date - relativedelta(months=i)
                    end_date = start_date + relativedelta(months=1)

                    if self.reports_repository.get(user['user_id'], start_date, end_date) is None:
                        report = self.generate_report_data(user['user_id'], start_date, end_date)
                        document = {
                            'user_id': user['user_id'],
                            'frequency': 'monthly',
                            'start_date': start_date,
                            'end_date': end_date,
                            'report': report,
                        }

                        self.reports_repository.create(document)
        except Exception as ex:
            print(ex)

    def get_user_report(self, user_id, start_date, end_date):
        return self.reports_repository.get(user_id, start_date, end_date)

    # retriving reports
    def get_daily_differential_report(self, user_id, nudge_template_name=None):
        now = datetime.utcnow()
        today = datetime(now.year, now.month, now.day, 0, 0, 0)

        prev_start_date = today - timedelta(days=2)
        prev_end_date = prev_start_date + timedelta(days=1)
        cur_start_date = today - timedelta(days=1)
        cur_end_date = cur_start_date + timedelta(days=1)

        previous = self.reports_repository.get(user_id, prev_start_date, prev_end_date)
        current = self.reports_repository.get(user_id, cur_start_date, cur_end_date)

        if previous is not None and current is not None and 'report' in previous and 'report' in current:
            return cur_start_date, cur_end_date, previous['report'], current['report']
        return None, None, None, None

    def get_weekly_differential_report(self, user_id, nudge_template_name=None):
        now = datetime.utcnow()
        today = datetime(now.year, now.month, now.day, 0, 0, 0)

        prev_start_date = today - timedelta(days=today.weekday()) - timedelta(days=14)
        prev_end_date = prev_start_date + timedelta(days=6)
        cur_start_date = today - timedelta(days=today.weekday()) - timedelta(days=7)
        cur_end_date = cur_start_date + timedelta(days=6)

        previous = self.reports_repository.get(user_id, prev_start_date, prev_end_date)
        current = self.reports_repository.get(user_id, cur_start_date, cur_end_date)

        if previous is not None and current is not None and 'report' in previous and 'report' in current:
            return cur_start_date, cur_end_date, previous['report'], current['report']
        return None, None, None, None

    def get_monthly_differential_report(self, user_id, nudge_template_name=None):
        now = datetime.utcnow()
        today = datetime(now.year, now.month, 1, 0, 0, 0)

        prev_start_date = today - relativedelta(months=2)
        prev_end_date = prev_start_date + relativedelta(months=1)
        cur_start_date = today - relativedelta(months=1)
        cur_end_date = cur_start_date + relativedelta(months=1)

        previous = self.reports_repository.get(user_id, prev_start_date, prev_end_date)
        current = self.reports_repository.get(user_id, cur_start_date, cur_end_date)

        if previous is not None and current is not None and 'report' in previous and 'report' in current:
            return cur_start_date, cur_end_date, previous['report'], current['report']
        return None, None, None, None

    def sales_this_month(self, user_id, month, year):
        return self.reports_repository.sales_this_month(user_id, month, year)

    def update_orders(self):
        self.shopify_profiles_bo.update_orders_database()

if __name__ == '__main__':
    reports_bo = ShopifyReportsBO()
    reports_bo.update_orders()
    # reports_bo.generate_reports()
    reports_bo.generate_daily_reports()
    # reports_bo.generate_weekly_reports()
    # reports_bo.generate_monthly_reports()
    # reports_bo.shopify_profiles_bo.update_orders_database()
    # report = reports_bo.user_report('111112222')
    # print(report)