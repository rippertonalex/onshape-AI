from app import ma
from marshmallow import fields


class ChatSchema(ma.Schema):
    HMW_user_id = ma.Integer()
    message = ma.String()


chat_schema = ChatSchema()
