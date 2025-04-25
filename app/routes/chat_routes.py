from flask import Blueprint, request, jsonify, Response as FlaskResponse
from collections import OrderedDict
import requests
import time
import json
import asyncio

from app.controllers import OpenShapeController
from app.decorators import handle_exceptions, token_required
from app.routes import get_pagination_args
from app.schemas.chat_schema import chat_schema
from app.utils.response import Response
from app.errors.validation import ValidationException
import logging

from flask import current_app


logger = logging.getLogger(__name__)
chat_routes = Blueprint("chat_routes", __name__)
chat_controller = OpenShapeController()


@chat_routes.post("/", endpoint="chat")
#@token_required
@handle_exceptions
def chat():
    validated_request_body = chat_schema.load(request.get_json())
    user_query = validated_request_body["message"]
    chat_response = asyncio.run(chat_controller.onshape_agent(
        user_query=user_query
    ))
    return Response.make(chat_response, Response.HTTP_SUCCESS)

