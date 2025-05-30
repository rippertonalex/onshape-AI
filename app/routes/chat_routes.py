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
        total_time_seconds = agent_response_data.get("total_time_seconds")
        tools_called_summary = agent_response_data.get("tools_called_summary")
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
        "history": updated_history,
        "total_time_seconds": total_time_seconds,
        "tools_called_summary": tools_called_summary
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

@chat_routes.post("/onshape", endpoint="onshape_chat")
@handle_exceptions
def onshape_chat():
    logger.info("--- Entered /v1/chat/onshape route ---")
    json_data = request.get_json()
    if not json_data:
        return Response.make({"error": "Request must be JSON"}, Response.HTTP_BAD_REQUEST)

    try:
        validated_request_body = chat_schema.load(json_data)
    except ValidationError as err:
        logger.error(f"Schema validation failed: {err.messages}")
        return Response.make({"error": "Schema validation failed", "details": err.messages}, Response.HTTP_BAD_REQUEST)

    user_query = validated_request_body["message"]
    part_studio_url = validated_request_body["part_studio_url"]
    history = validated_request_body.get("history", [])

    logger.info(f"Received message with history length: {len(history)}")

    try:
        agent_response_data = asyncio.run(chat_controller.onshape_chat(
            user_query=user_query,
            part_studio_url=part_studio_url,
            history=history
        ))
        # Extract all relevant data from the agent response dictionary
        agent_message = agent_response_data.get("response", "Agent did not return a user-friendly message.")
        enriched_feature_summary = agent_response_data.get("enriched_feature_summary")
        parsed_features = agent_response_data.get("parsed_features")
        total_time_seconds = agent_response_data.get("total_time_seconds")
    except Exception as e:
        logger.exception("Error running onshape_chat")  
        agent_message = f"An internal error occurred: {e}"
        response_payload = {
            "error": agent_message,
            "response": None,
            "enriched_feature_summary": None,
            "history": history + [{"role": "user", "content": user_query}, {"role": "assistant", "content": agent_message}]
        }
        return Response.make(response_payload, Response.HTTP_ERROR)
    
    # Prepare response payload including the *updated* history and the new fields
    # Construct the updated history first
    updated_history = history + [{"role": "user", "content": user_query}, {"role": "assistant", "content": agent_message}]
    response_payload = {
        "response": agent_message,
        "enriched_feature_summary": enriched_feature_summary,
        # Use the pre-calculated updated_history list here
        "history": updated_history, 
        "total_time_seconds": total_time_seconds,
        "parsed_features": parsed_features
    }

    # Log the length of the pre-calculated list
    logger.info(f"Responding with updated history length: {len(updated_history)}") 
    return Response.make(response_payload, Response.HTTP_SUCCESS)


@chat_routes.post("/pre_processing", endpoint="pre_processing")
@handle_exceptions
def pre_processing():
    logger.info("--- Entered /v1/chat/pre_processing route ---")
    json_data = request.get_json()
    if not json_data:
        return Response.make({"error": "Request must be JSON"}, Response.HTTP_BAD_REQUEST)
    
    part_studio_url = json_data.get("part_studio_url")

    try:
        pre_processing_data = asyncio.run(chat_controller.pre_processing(part_studio_url))
    except Exception as e:
        logger.exception("Error running pre_processing")
        return Response.make({"error": "An internal error occurred"}, Response.HTTP_ERROR)
    
    response_payload = {
        "visualized_summary": pre_processing_data.get("visualized_summary"),
        "enriched_summary": pre_processing_data.get("enriched_summary"),
        "defined_sketch_entities": pre_processing_data.get("defined_sketch_entities"),
        "parsed_features": pre_processing_data.get("parsed_features")
    }

    logger.info("--- Pre-processing completed successfully ---")
    return Response.make(response_payload, Response.HTTP_SUCCESS)

    
    
    





