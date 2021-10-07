from src import db, func


class UserModel(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String, unique=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())

    def user_json_serializer(self):
        return {"user_name": self.user_name, "created_at": str(self.created_at)}

    def user_json_serialize_all(self):
        return {"id": self.id, "user_name": self.user_name, "created_at": str(self.created_at)}
