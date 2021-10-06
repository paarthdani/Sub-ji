from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
import json

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///subji.db"
db = SQLAlchemy(app)

plans = {"FREE", "TRIAL", "LITE_1M", "PRO_1M", "LITE_6M", "PRO_6M"}
plan_cost = {"FREE": 0.0, "TRIAL": 0.0, "LITE_1M": 100.0, "PRO_1M": 200.0, "LITE_6M": 500.0, "PRO_6M": 900.0}
plan_validity = {"FREE": "Infinite", "TRIAL": 7, "LITE_1M": 30, "PRO_1M": 30, "LITE_6M": 180, "PRO_6M": 180}


## Models


class UserModel(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String, unique=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def user_json_serializer(self):
        return {"id": self.id, "user_name": self.user_name, "created_at": str(self.created_at),
                "updated_at": str(self.updated_at)}


@app.route('/user/<username>', methods=['PUT'])
def add_user(username):
    try:
        obj = UserModel(user_name=username)
        db.session.add(obj)
        db.session.commit()
        print(obj)
        return json.dumps({"message": "Added User"}), 200

    except Exception as e:
        return json.dumps({"message": "Failed To Add User", "err": str(e)}), 400


@app.route("/user/<username>", methods=["GET"])
def get_by_username(username):
    user_data = db.session.query(UserModel).filter(UserModel.user_name == username).first()
    if user_data is None:
        return json.dumps({"message": "user does not exist"}), 400
    else:
        return json.dumps(user_data.user_json_serializer())


db.create_all()

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=19094)
