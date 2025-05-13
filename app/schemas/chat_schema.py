from app import ma
from marshmallow import fields


class ChatSchema(ma.Schema):
    HMW_user_id = ma.Integer()
    message = ma.String(required=True)
    part_studio_url = fields.String()
    history = ma.List(ma.Dict())


chat_schema = ChatSchema()
