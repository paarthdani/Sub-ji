import flask
import json

from src import app, db, logger
from src.models.user_model import UserModel


@app.route('/user/<username>', methods=['PUT'])
def add_user(username):
    try:
        obj = UserModel(user_name=username)
        db.session.add(obj)
        db.session.commit()
        logger.info("User successfully added - " + username)
        return flask.Response(status=200)

    except Exception as e:
        logger.error("Failed to add user - " + username + " " + str(e))
        return json.dumps({"message": "Failed To Add User", "err": str(e)}), 409


@app.route("/user/<username>", methods=["GET"])
def get_by_username(username):
    user_data = db.session.query(UserModel).filter(UserModel.user_name == username).first()
    if user_data is None:
        logger.error("User does not Exist - " + username)
        return json.dumps({"message": "User does not Exist"}), 404
    else:
        logger.info("User data found for - " + username)
        return json.dumps(user_data.user_json_serializer())
