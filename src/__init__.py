import flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import desc
from sqlalchemy.sql import func

app = flask.Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///subji.db"
db = SQLAlchemy(app)

from src.controllers import subscription_controller, user_controller

db.create_all()
