from src import db, func
from src.models.user_model import UserModel


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
