import flask
import json
import datetime

from src import db, app, desc
from src.models.user_model import UserModel
from src.models.subscription_model import SubscriptionModel
from src.models.purchase_order_model import PurchaseOrder
from src.helpers.payment_gateway import payment_gateway


plans_all = {"FREE", "TRIAL", "LITE_1M", "PRO_1M", "LITE_6M", "PRO_6M"}
plan_cost_all = {"FREE": 0.0, "TRIAL": 0.0, "LITE_1M": 100.0, "PRO_1M": 200.0, "LITE_6M": 500.0, "PRO_6M": 900.0}
plan_validity_all = {"FREE": "Infinite", "TRIAL": 7, "LITE_1M": 30, "PRO_1M": 30, "LITE_6M": 180, "PRO_6M": 180}


# @app.route('/view/subscription', methods=['GET'])
# def view_subscription():
#     d = [i.subscription_json_serialize_all() for i in db.session.query(SubscriptionModel).all()]
#     return json.dumps(d)
#
#
# @app.route('/view/po', methods=['GET'])
# def view_po():
#     d = [i.purchase_order_json_serialize_all() for i in db.session.query(PurchaseOrder).all()]
#     return json.dumps(d)


def get_user_id_from_username(user_name):
    user_data = db.session.query(UserModel).filter(UserModel.user_name == user_name).first()

    if user_data is None:
        return json.dumps({"message": "User does not exist"}), 400
    user_data = json.dumps(user_data.user_json_serialize_all())
    user_id = json.loads(user_data).get("id")
    return user_id


def get_plan_validity(plan, start_date, plan_validity):
    if plan == 'FREE':
        valid_till = start_date + datetime.timedelta(days=999999)
    else:
        valid_till = start_date + datetime.timedelta(days=plan_validity)
    return valid_till


def get_payment_type_and_amount(active_plan_cost, new_plan_cost):
    if active_plan_cost < new_plan_cost:
        payment_type = 'DEBIT'
        amount = new_plan_cost - active_plan_cost
    else:
        payment_type = 'CREDIT'
        amount = active_plan_cost - new_plan_cost
    return payment_type, amount


@app.route('/subscription', methods=['POST'])
def new_subscription():
    request = flask.request.get_json()
    user_name = request.get("user_name")
    plan = request.get("plan_id")
    start_date = request.get("start_date")
    user_id = get_user_id_from_username(user_name)

    plan_cost = plan_cost_all.get(plan)
    plan_validity = plan_validity_all.get(plan)
    if plan_cost is None or plan_validity is None:
        return json.dumps({"message": "Plan does not exist"}), 400

    start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    valid_till = get_plan_validity(plan, start_date, plan_validity)

    current_active_sub = db.session.query(SubscriptionModel) \
        .filter(SubscriptionModel.status == True, SubscriptionModel.user_id == user_id) \
        .order_by(desc(SubscriptionModel.created_at)) \
        .first()

    if current_active_sub is not None and current_active_sub.subscription_json_serialize_all()['plan'] == plan:
        return json.dumps({"message": "Plan is already active"}), 400
    else:
        try:
            if current_active_sub is None:
                active_plan = "FREE"
            else:
                active_plan = current_active_sub.subscription_json_serialize_all()['plan']
            new_plan_cost = plan_cost_all[plan]
            active_plan_cost = plan_cost_all[active_plan]
            payment_type, amount = get_payment_type_and_amount(active_plan_cost, new_plan_cost)

            if amount != 0.0:
                response, status_code = payment_gateway(user_name, payment_type, amount)

                if status_code != 200 or response.get("status") != "SUCCESS":
                    return json.dumps({"message": "Not able to complete the payment"}), 400
                else:
                    payment_id = response.get("payment_id")
                    amount = amount if payment_type == "CREDIT" else -amount
                purchase_order = PurchaseOrder(plan=plan, status="SUCCESS", payment_id=payment_id, user_id=user_id)
                db.session.add(purchase_order)

            subscription_model = SubscriptionModel(status=True, start_date=start_date, valid_till=valid_till, plan=plan, user_id=user_id)
            db.session.add(subscription_model)
            if current_active_sub is not None:
                SubscriptionModel.query\
                    .filter_by(id=current_active_sub.subscription_json_serialize_all()['id'])\
                    .update({SubscriptionModel.status: False})

            db.session.commit()
            return json.dumps({"status": "SUCCESS", "amount": amount}), 200

        except Exception as e:
            return json.dumps({"message": "Failed To Add New Subscription", "err": str(e)}), 400


@app.route("/subscription/<user_name>", methods=['GET'])
def get_subscription_by_username(user_name):
    user_id = get_user_id_from_username(user_name)
    subscription_list = db.session.query(SubscriptionModel).filter(SubscriptionModel.user_id == user_id).all()

    if not subscription_list:
        return json.dumps({"message": "No subscription found for the user"}), 400

    result = []
    for i in subscription_list:
        result.append(i.subscription_json_serializer())
    return json.dumps(result), 200


@app.route("/subscription/<user_name>/<current_date>", methods=['GET'])
def get_subscription_by_username_by_currentdate(user_name, current_date):
    user_id = get_user_id_from_username(user_name)
    current_date = datetime.datetime.strptime(current_date, '%Y-%m-%d')
    subscription = db.session.query(SubscriptionModel) \
        .filter(SubscriptionModel.user_id == user_id,
                SubscriptionModel.status == True, SubscriptionModel.start_date <= str(current_date),
                SubscriptionModel.valid_till >= str(current_date)).first()

    if subscription is None:
        return json.dumps({"message": "No active plan for the user"}), 400

    subscription_object = json.loads(json.dumps(subscription.subscription_json_serializer()))
    valid_till = datetime.datetime.strptime(subscription_object.get("valid_till"), '%Y-%m-%d %H:%M:%S')

    days_left = valid_till - current_date
    if days_left.days < 0:
        return json.dumps({"message": "Plan has already ended"}), 400
    else:
        return json.dumps({"plan_id": subscription_object['plan'], "days_left": days_left.days}), 200
