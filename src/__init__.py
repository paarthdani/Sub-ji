import flask
from flask_sqlalchemy import SQLAlchemy
import logging
from sqlalchemy import desc
from sqlalchemy.sql import func

app = flask.Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///subji.db"
db = SQLAlchemy(app)

logger = logging.getLogger()
logging.basicConfig(filename="system.log",
                    format='%(asctime)s %(levelname)s %(message)s',
                    filemode='a',
                    level=logging.DEBUG)

from src.controllers import subscription_controller, user_controller

db.create_all()
