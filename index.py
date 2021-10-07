import datetime
import json

import flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import desc
from sqlalchemy.sql import func
from payment_gateway import payment_gateway
from sqlalchemy import create_engine

app = flask.Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///subji.db"
db = SQLAlchemy(app)

# engine = create_engine('sqlite:///subji.db', echo=False)

plans_all = {"FREE", "TRIAL", "LITE_1M", "PRO_1M", "LITE_6M", "PRO_6M"}
plan_cost_all = {"FREE": 0.0, "TRIAL": 0.0, "LITE_1M": 100.0, "PRO_1M": 200.0, "LITE_6M": 500.0, "PRO_6M": 900.0}
plan_validity_all = {"FREE": "Infinite", "TRIAL": 7, "LITE_1M": 30, "PRO_1M": 30, "LITE_6M": 180, "PRO_6M": 180}


## Models

class UserModel(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String, unique=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())

    def user_json_serializer(self):
        return {"user_name": self.user_name, "created_at": str(self.created_at)}

    def user_json_serialize_all(self):
        return {"id": self.id, "user_name": self.user_name, "created_at": str(self.created_at)}


class SubscriptionModel(db.Model):
    __tablename__ = "subscriptions"

    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.Boolean, nullable=False, default=True)
    start_date = db.Column(db.DateTime(timezone=True), nullable=False)
    valid_till = db.Column(db.DateTime(timezone=True), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    plan = db.Column(db.String, nullable=False)
    user_id = db.Column(db.ForeignKey(UserModel.id))

    def subscription_json_serialize_all(self):
        return {"id": self.id, "user_id": str(self.user_id), "created_at": str(self.created_at), "status": self.status,
                "start_date": str(self.start_date), "valid_till": str(self.valid_till), "plan": self.plan}

    def subscription_json_serializer(self):
        return {"plan": self.plan, "start_date": str(self.start_date), "valid_till": str(self.valid_till)}


class PurchaseOrder(db.Model):
    __tablename__ = "purchase_orders"

    id = db.Column(db.Integer, primary_key=True)
    plan = db.Column(db.String, nullable=False)
    status = db.Column(db.String, nullable=False)
    payment_id = db.Column(db.String, nullable=True)
    user_id = db.Column(db.ForeignKey(UserModel.id))

    def purchase_order_json_serialize_all(self):
        return {"id": self.id, "user_id": str(self.user_id), "status": self.status,
                "payment_id": self.payment_id, "plan": self.plan}


@app.route('/user/<username>', methods=['PUT'])
def add_user(username):
    try:
        obj = UserModel(user_name=username)
        db.session.add(obj)
        db.session.commit()
        return flask.Response(status=200)

    except Exception as e:
        return json.dumps({"message": "Failed To Add User", "err": str(e)}), 400


@app.route("/user/<username>", methods=["GET"])
def get_by_username(username):
    user_data = db.session.query(UserModel).filter(UserModel.user_name == username).first()
    if user_data is None:
        return json.dumps({"message": "user does not exist"}), 400
    else:
        return json.dumps(user_data.user_json_serializer())


@app.route('/view/subscription', methods=['GET'])
def view_subscription():
    d = [i.subscription_json_serialize_all() for i in db.session.query(SubscriptionModel).all()]
    return json.dumps(d)


@app.route('/view/po', methods=['GET'])
def view_po():
    d = [i.purchase_order_json_serialize_all() for i in db.session.query(PurchaseOrder).all()]
    return json.dumps(d)


@app.route('/subscription', methods=['POST'])
def new_subscription():
    request = flask.request.get_json()
    user_name = request.get("user_name")
    plan = request.get("plan_id")
    start_date = request.get("start_date")

    print(user_name, plan, start_date)

    user_data = db.session.query(UserModel).filter(UserModel.user_name == user_name).first()

    print(user_data)

    if user_data is None:
        return json.dumps({"message": "user does not exist"})
    user_data = json.dumps(user_data.user_json_serialize_all())

    print(user_data)

    plan_cost = plan_cost_all.get(plan)
    plan_validity = plan_validity_all.get(plan)
    if plan_cost is None or plan_validity is None:
        return json.dumps({"message": "plan does not exist"})

    print(plan_cost, plan_validity)

    start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    if plan == 'FREE':
        valid_till = start_date + datetime.timedelta(days=999999)
    else:
        valid_till = start_date + datetime.timedelta(days=plan_validity)

    print(start_date, valid_till)

    user_id = json.loads(user_data).get("id")

    print(user_id)

    current_active_sub = db.session.query(SubscriptionModel) \
        .filter(SubscriptionModel.status == True, SubscriptionModel.user_id == user_id) \
        .order_by(desc(SubscriptionModel.created_at)) \
        .first()

    # print(current_active_sub.subscription_json_serialize_all())

    if current_active_sub is not None and current_active_sub.subscription_json_serialize_all()['plan'] == plan:
        return json.dumps({"message": "plan is already active"})
    else:
        if current_active_sub is None:
            active_plan = "FREE"
        else:
            active_plan = current_active_sub.subscription_json_serialize_all()['plan']
        new_plan_cost = plan_cost_all[plan]
        active_plan_cost = plan_cost_all[active_plan]

        print(active_plan_cost, new_plan_cost)

        if active_plan_cost < new_plan_cost:
            payment_type = 'DEBIT'
            amount = new_plan_cost - active_plan_cost
        else:
            payment_type = 'CREDIT'
            amount = active_plan_cost - new_plan_cost

        print(payment_type, amount)

        payment_request = {"user_name": user_name, "payment_type": payment_type, "amount": amount}
        response, status_code = payment_gateway(payment_request)

        print(response, status_code)

        if status_code != 200 or response.get("status") == "FAILURE":
            return json.dumps({"message": "Not able to complete the payment"})
        else:
            payment_id = response.get("payment_id")
            amount = amount if payment_type == "CREDIT" else -amount

        print(payment_id, amount)

    subscription_model = SubscriptionModel(status=True, start_date=start_date, valid_till=valid_till,
                                           plan=plan, user_id=json.loads(user_data).get("id"))
    db.session.add(subscription_model)
    if current_active_sub is not None:
        print("in here")
        SubscriptionModel.query.filter_by(id=current_active_sub.subscription_json_serialize_all()['id']).update(
            {SubscriptionModel.status: False})

    purchase_order = PurchaseOrder(plan=plan, status="SUCCESS", payment_id=payment_id,
                                   user_id=json.loads(user_data).get("id"))
    db.session.add(purchase_order)
    db.session.commit()

    return json.dumps({"status": "SUCCESS", "amount": amount})


@app.route("/subscription/<user_name>", methods=['GET'])
def get_subscription_by_username(user_name):
    user_data = db.session.query(UserModel).filter(UserModel.user_name == user_name).first()

    print(user_data)

    if user_data is None:
        return json.dumps({"message": "user does not exist"})
    user_data = json.dumps(user_data.user_json_serialize_all())

    print(user_data)

    subscription_list = db.session.query(SubscriptionModel) \
        .filter(SubscriptionModel.user_id == json.loads(user_data).get("id")).all()

    result = []
    for i in subscription_list:
        result.append(i.subscription_json_serializer())
    print(result)
    return json.dumps(result)


@app.route("/subscription/<user_name>/<current_date>", methods=['GET'])
def get_subscription_by_username_by_currentdate(user_name, current_date):
    user_data = db.session.query(UserModel).filter(UserModel.user_name == user_name).first()
    if user_data is None:
        return json.dumps({"message": "user does not exist"})
    user_data = json.dumps(user_data.user_json_serialize_all())
    print(user_data)
    current_date = datetime.datetime.strptime(current_date, '%Y-%m-%d')
    subscription = db.session.query(SubscriptionModel) \
        .filter(SubscriptionModel.user_id == json.loads(user_data).get("id"),
                SubscriptionModel.status == True, SubscriptionModel.start_date < str(current_date),
                SubscriptionModel.valid_till > str(current_date)).first()

    if subscription is None:
        return json.dumps({"message": "No active plan for the user"})

    print(current_date)

    subscription_object = json.loads(json.dumps(subscription.subscription_json_serializer()))

    valid_till = subscription_object.get("valid_till")
    print(valid_till)
    valid_till = datetime.datetime.strptime(valid_till, '%Y-%m-%d %H:%M:%S')

    days_left = valid_till - current_date
    print(days_left)
    if days_left.days < 0:
        return json.dumps({"message": "Plan is already ended"})
    else:
        return json.dumps({"plan_id": subscription_object['plan'], "days_left": days_left.days})


db.create_all()
# SubscriptionModel.__table__.drop(engine)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=19095)
