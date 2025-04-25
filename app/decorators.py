import functools
import traceback

from marshmallow import ValidationError

from app import logger
from app.errors import ProcessingException, ValidationException
from app.utils.messages import Error
from app.utils.response import Response
from functools import wraps
from flask import request, jsonify
from flask import current_app


def handle_exceptions(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValidationException as ve:
            logger.info(str(ve.messages))
            return Response.make(ve.messages, Response.HTTP_BAD_REQUEST)
        except ProcessingException as pe:
            logger.info(str(pe.messages))
            return Response.make(pe.messages, Response.HTTP_BAD_REQUEST)
        except ValidationError as err:
            logger.info(err)
            return Response.make(err.messages, Response.HTTP_BAD_REQUEST)
        except Exception as e:
            traceback.print_exc()
            logger.error(f"general exception {e}")
            return Response.make(Error.REQUEST_FAILED, Response.HTTP_ERROR)

    return wrapper


def token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        # Check if the token is in the request headers
        if "Authorization" in request.headers:
            token = request.headers["Authorization"].split(" ")[
                1
            ]  # Extract the token part

        if not token:
            return jsonify({"message": "Token is missing!"}), 401

        # Check if the token matches the predefined token
        if token != current_app.config["BEARER_TOKEN"]:
            return jsonify({"message": "Token is invalid!"}), 401

        return f(*args, **kwargs)

    return decorated_function
