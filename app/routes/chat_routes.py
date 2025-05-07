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
from marshmallow import ValidationError
import logging

from flask import current_app


logger = logging.getLogger(__name__)
chat_routes = Blueprint("chat_routes", __name__)
chat_controller = OpenShapeController()

# --- Remove Conversation Store ---
# conversation_store = {}
# ---------------------------------

@chat_routes.post("/", endpoint="chat")
#@token_required
@handle_exceptions
def chat():
    logger.info("--- Entered /v1/chat/ route --- (Using client-side history)")
    json_data = request.get_json()
    if not json_data:
        return Response.make({"error": "Request must be JSON"}, Response.HTTP_BAD_REQUEST)

    # Validate request body
    try:
        # History is now part of the schema validation
        validated_request_body = chat_schema.load(json_data)
    except ValidationError as err: # Catch Marshmallow validation errors directly
         logger.error(f"Schema validation failed: {err.messages}")
         return Response.make({"error": "Schema validation failed", "details": err.messages}, Response.HTTP_BAD_REQUEST)

    user_query = validated_request_body["message"]
    # Get history from the validated request body, defaulting to empty list if not present
    history = validated_request_body.get("history", []) 

    logger.info(f"Received message with history length: {len(history)}")

    # --- Call the Agent --- 
    # Pass the incoming history directly to the agent
    try:
        # The controller method already accepts history
        agent_response_data = asyncio.run(chat_controller.onshape_agent(
            user_query=user_query,
            history=history # Pass the history received from the client
        ))
        # Extract all relevant data from the agent response dictionary
        agent_message = agent_response_data.get("response", "Agent did not return a user-friendly message.")
        final_output = agent_response_data.get("final_output")
        chain_of_thought = agent_response_data.get("chain_of_thought")
        raw_responses = agent_response_data.get("raw_responses")

    except Exception as e:
         logger.exception("Error running onshape_agent")
         agent_message = f"An internal error occurred: {e}"
         # Prepare response payload even on error
         # Include the new fields as None on error
         response_payload = {
            "error": agent_message,
            "response": None,
            "final_output": None,
            "chain_of_thought": None,
            "raw_responses": None,
            "history": history + [{"role": "user", "content": user_query}, {"role": "assistant", "content": agent_message}] # Return updated history
         }
         return Response.make(response_payload, Response.HTTP_ERROR)
    # ----------------------

    # --- Prepare Response History ---
    # Append current user query and agent response to the history *before* sending back
    updated_history = history + [
        {"role": "user", "content": user_query},
        {"role": "assistant", "content": agent_message}
    ]
    # -------------------------------

    # Prepare response payload including the *updated* history and the new fields
    response_payload = {
        "response": agent_message,
        "final_output": final_output,
        "chain_of_thought": chain_of_thought,
        "raw_responses": raw_responses,
        "history": updated_history
    }

    logger.info(f"Responding with updated history length: {len(updated_history)}")
    return Response.make(response_payload, Response.HTTP_SUCCESS)

# Clean up the old simplified version if it exists
# (Ensure the new chat function replaces any previous simple 'chat' definition)
# Remove the following if it was part of the previous code:
# @chat_routes.post("/", endpoint="chat")
# def simple_chat():
#    print("--- Entered /v1/chat/ route (RADICAL SIMPLIFICATION) ---", flush=True)
#    logger.info("--- Entered /v1/chat/ route ---")
#    return jsonify({"message": "Route reached successfully"}), 200
    
