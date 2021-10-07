import flask
import json

from src import app, db
from src.models.user_model import UserModel


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
        return json.dumps({"message": "User does not Exist"}), 400
    else:
        return json.dumps(user_data.user_json_serializer())
