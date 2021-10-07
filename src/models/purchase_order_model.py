from src import db
from src.models.user_model import UserModel


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
