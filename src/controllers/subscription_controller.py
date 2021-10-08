import flask
import json
import datetime

from src import db, app, desc, logger
from src.models.user_model import UserModel
from src.models.subscription_model import SubscriptionModel
from src.models.purchase_order_model import PurchaseOrder
from src.helpers.payment_gateway import payment_gateway

plans_all = {"FREE", "TRIAL", "LITE_1M", "PRO_1M", "LITE_6M", "PRO_6M"}
plan_cost_all = {"FREE": 0.0, "TRIAL": 0.0, "LITE_1M": 100.0, "PRO_1M": 200.0, "LITE_6M": 500.0, "PRO_6M": 900.0}
plan_validity_all = {"FREE": "Infinite", "TRIAL": 7, "LITE_1M": 30, "PRO_1M": 30, "LITE_6M": 180, "PRO_6M": 180}


def get_user_id_from_username(user_name):
    user_data = db.session.query(UserModel).filter(UserModel.user_name == user_name).first()

    if user_data is None:
        return None
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
    if user_id is None:
        logger.error("User does not Exist - " + user_name)
        return json.dumps({"message": "User does not exist"}), 404

    plan_cost = plan_cost_all.get(plan)
    plan_validity = plan_validity_all.get(plan)
    if plan_cost is None or plan_validity is None:
        logger.error("Plan does not exist - " + plan)
        return json.dumps({"message": "Plan does not exist"}), 404

    start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    valid_till = get_plan_validity(plan, start_date, plan_validity)

    current_active_sub = db.session.query(SubscriptionModel) \
        .filter(SubscriptionModel.status == True, SubscriptionModel.user_id == user_id) \
        .order_by(desc(SubscriptionModel.created_at)) \
        .first()

    if current_active_sub is not None and current_active_sub.subscription_json_serialize_all()['plan'] == plan:
        logger.error("Plan " + plan + " is already active for - " + user_name)
        return json.dumps({"message": "Plan is already active"}), 404
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
                    logger.error("Not able to complete the payment for - " + user_name)
                    return json.dumps({"message": "Not able to complete the payment"}), 502
                else:
                    payment_id = response.get("payment_id")
                    amount = amount if payment_type == "CREDIT" else -amount
                purchase_order = PurchaseOrder(plan=plan, status="SUCCESS", payment_id=payment_id, user_id=user_id)
                db.session.add(purchase_order)

            subscription_model = SubscriptionModel(status=True, start_date=start_date, valid_till=valid_till, plan=plan,
                                                   user_id=user_id)
            db.session.add(subscription_model)
            if current_active_sub is not None:
                SubscriptionModel.query \
                    .filter_by(id=current_active_sub.subscription_json_serialize_all()['id']) \
                    .update({SubscriptionModel.status: False})

            db.session.commit()
            logger.info("successfully added subscription for user - " + user_name + " and amount - " + str(amount))
            return json.dumps({"status": "SUCCESS", "amount": amount}), 200

        except Exception as e:
            logger.error("Failed To Add New Subscription for - " + user_name + " " + str(e))
            return json.dumps({"message": "Failed To Add New Subscription", "err": str(e)}), 409


@app.route("/subscription/<user_name>", methods=['GET'])
def get_subscription_by_username(user_name):
    user_id = get_user_id_from_username(user_name)
    if user_id is None:
        logger.error("User does not Exist - " + user_name)
        return json.dumps({"message": "User does not exist"}), 404

    subscription_list = db.session.query(SubscriptionModel).filter(SubscriptionModel.user_id == user_id).all()
    if not subscription_list:
        logger.error("No subscription found for the user - " + user_name)
        return json.dumps({"message": "No subscription found for the user"}), 404

    result = []
    for i in subscription_list:
        result.append(i.subscription_json_serializer())

    logger.info("subscription list for user - " + user_name + " is - " + str(json.dumps(result)))
    return json.dumps(result), 200


@app.route("/subscription/<user_name>/<current_date>", methods=['GET'])
def get_subscription_by_username_by_currentdate(user_name, current_date):
    user_id = get_user_id_from_username(user_name)
    if user_id is None:
        logger.error("User does not Exist - " + user_name)
        return json.dumps({"message": "User does not exist"}), 404

    current_date = datetime.datetime.strptime(current_date, '%Y-%m-%d')
    subscription = db.session.query(SubscriptionModel) \
        .filter(SubscriptionModel.user_id == user_id,
                SubscriptionModel.status == True, SubscriptionModel.start_date <= str(current_date),
                SubscriptionModel.valid_till >= str(current_date)).first()

    if subscription is None:
        logger.error("No active plan found for the user - " + user_name)
        return json.dumps({"message": "No active plan found for the user"}), 404

    subscription_object = json.loads(json.dumps(subscription.subscription_json_serializer()))
    valid_till = datetime.datetime.strptime(subscription_object.get("valid_till"), '%Y-%m-%d %H:%M:%S')

    days_left = valid_till - current_date
    logger.info("Plan id - " + subscription_object['plan_id'] + " and days left - " + str(days_left) + " for user - " + user_name + " and current date " + str(current_date))
    return json.dumps({"plan_id": subscription_object['plan_id'], "days_left": days_left.days}), 200
