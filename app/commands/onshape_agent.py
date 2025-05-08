import requests
import json
import os
from dotenv import load_dotenv
from datetime import datetime # Added import for datetime
# Import necessary components from the agents library
from agents import Agent, Runner, RunConfig
# Import specific types if needed for serialization or type checking, e.g., ModelResponse, RunItem
# from agents.result import ModelResponse, RunItem # Example if direct import is needed
import asyncio
import re # Import regex for URL parsing
from typing import Union, List, Dict, Any # Import Union, List, Dict, Any
from app.core.commands import WriteCommand
from app.utils.onshape_tools import (
    get_onshape_document_details,
    get_onshape_feature_list,
    get_onshape_featurescript_representation,
    create_onshape_cube,
    create_onshape_feature,
    feature_parser,
    extract_feature_summaries,
    enrich_feature_summaries,
)
import logging

# Set higher logging levels for verbose libraries
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

# --- Onshape Tool Definitions ---

# Load environment variables from .env file
# Ensure your .env file with ACCESS_KEY and SECRET_KEY is in the same directory
# or accessible in your environment when running this.
load_dotenv()

ONSHAPE_API_BASE_URL = "https://cad.onshape.com/api/v10" # Use the /api endpoint


# --- Tool 1: Get Document Details ---

class OnShapeAgent(WriteCommand):

    def __init__(self, user_query: str, history: List[Dict[str, str]] = None):
        """
        Initializes the OnShapeAgent command.

        Args:
            user_query (str): The latest query from the user.
            history (List[Dict[str, str]], optional): A list of previous messages
                in the conversation, where each message is a dict with 'role'
                ('user' or 'assistant') and 'content'. Defaults to None.
                This history will be formatted and included in the prompt.
        """
        self.user_query = user_query
        self.history = history or [] # Store the history, default to empty list
        self.access_key = os.getenv("ACCESS_KEY")
        self.secret_key = os.getenv("SECRET_KEY")
        self.base_api_url = ONSHAPE_API_BASE_URL
        self.openai_api_key = os.getenv("OPENAI_API_KEY")

    def validate_auth(self) -> bool:
        if not self.access_key or not self.secret_key:
            print("Error: Onshape ACCESS_KEY or SECRET_KEY not found in environment variables. Cannot use tool.")
            return False
        return True


    # --- Agent Definition ---

    # Define the Onshape Agent
    async def execute(self) -> dict:
        print("***** OnShapeAgent.execute() ENTERED *****") # ADDED FOR DIAGNOSTICS
        overall_start_time = datetime.now() # Record start time for the whole execution

        onshape_agent = Agent(
            name="Onshape Assistant Agent V8", # Incremented version
            instructions=(
                "You are a helpful assistant knowledgeable about Onshape documents. You can view features, create simple features, and provide detailed interpretations of Part Studio geometry using the Onshape REST API v10 and specialized processing tools."
                "\n\n"
                "You have eight tools: 'get_onshape_document_details', 'get_onshape_feature_list', 'get_onshape_featurescript_representation', 'create_onshape_cube', 'create_onshape_feature', 'feature_parser', 'extract_feature_summaries', and 'enrich_feature_summaries'."
                "\n\n"
                "**Standardized Workflow for Geometry Interpretation:**"
                "\nWhen asked to describe, analyze, or interpret the geometry of a Part Studio, and you haven't already processed its features in the current conversational context, you MUST follow this sequence:"
                "\n  1. Use `get_onshape_feature_list` to retrieve the raw feature data JSON string for the relevant Part Studio URL."
                "\n  2. Use `feature_parser` on the JSON string output from step 1."
                "\n  3. Use `extract_feature_summaries` on the dictionary output from step 2."
                "\n  4. Use `enrich_feature_summaries` on the list output from step 3 and the document URL."
                "\n  5. After this sequence, you will have an enriched summary of features. Your primary task is to interpret THIS enriched data to answer the user's geometry question based on the guidelines below."
                "\n\n"
                "**Interpreting Geometric Data from Enriched Summaries:**"
                "\nYour goal is to create an EXACT verbal representation of the geometry based on the processed feature data you obtain through the workflow above."
                "\n- **General Data:** The enriched data will include feature types (e.g., 'newSketch', 'extrude'), feature names, specific parameters, and entity IDs (often 3 or 4 letter transient IDs like 'JHK', 'KIlC'). The `createdEntities` field will list IDs of entities B-Rep elements (faces, edges, vertices) created by each feature. The `sketchPlane` field will describe the plane for sketch features."
                "\n- **Sketches (e.g., featureType 'newSketch'):**"
                "\n  - The processed data (especially after `enrich_feature_summaries` provides `sketchPlane` details) allows you to define the 2D geometry (lines, arcs, circles, their dimensions, and constraints). Note units."
                "\n  - You will know the sketch plane's geometric definition (normal, origin, x-direction) from the `sketchPlane` field in the enriched summary."
                "\n- **3D Features (e.g., 'extrude', 'fillet', 'revolve'):**"
                "\n  - The data will describe the feature's precise action (e.g., 'extrude by 3mm in the positive Z direction', 'fillet with a 0.25 inch radius')."
                "\n  - It will specify the entity IDs that the feature acts upon (input geometry). You won't initially know the full geometric definition of these input entities from the summary alone, only their IDs and types if provided."
                "\n- **Resolving Unknowns & Entity Definitions:**"
                "\n  - Recognize that the enriched summary provides definitions for *created* entities and *sketch planes*. Input entities for 3D features are referenced by ID."
                "\n  - Your interpretation should clearly state what is known (e.g., 'Sketch1 creates a 10mm diameter circle centered at origin on a plane defined by...') and what entities (by their IDs) are referenced as inputs but not fully defined by the summary itself (e.g., 'Extrude1 acts on face JHK')."
                "\n  - If the user's query requires a complete geometric definition of an entity that is an *input* to a feature and its definition isn't apparent from the `createdEntities` of a *previous* feature or the `sketchPlane` data, you should state: 'To EXACTLY define the complete geometry, particularly [specific aspect, e.g., the shape of face JHK], I would need its detailed geometric definition. The current summary describes how it's used, but not its intrinsic geometry if it wasn't created by an earlier feature in this summary.' (You currently do not have a general tool to get arbitrary B-Rep entity definitions by ID beyond what `enrich_feature_summaries` provides.)"
                "\n- **Linking Entities & Feature Dependencies:** When analyzing the enriched summary, identify relationships. For example, if an extrude acts on entities created by a specific sketch, note this link. This helps understand how the part is constructed."
                "\n\n"
                "**Core Onshape Interaction Tools:**"
                "\n1.  **Get Document Details (`get_onshape_document_details`):** Use for overall document info (like 'microversionId'). Requires `document_id`."
                "\n2.  **Get Feature List (`get_onshape_feature_list`):** Use when asked to list/analyze features. Requires `part_studio_url`. Returns a raw JSON string of features. **This is the first step in the Standardized Workflow for Geometry Interpretation.**"
                "\n3.  **Get FeatureScript Representation (`get_onshape_featurescript_representation`):** Use when asked for the **FeatureScript representation** (code) of a Part Studio. Requires `part_studio_url`."
                "\n4.  **Create Cube (`create_onshape_cube`):** Use ONLY when asked to create a **simple 'cube'**. Requires `part_studio_url`, `name`, `side_length_expression`."
                "\n5.  **Create Feature (General) (`create_onshape_feature`):** Use for creating **any other feature type**. Requires `part_studio_url` and `feature_payload_json`."
                "\n\n"
                "**Feature Data Processing Tools (used in the Standardized Workflow):**"
                "\n6.  **Parse Features (`feature_parser`):** Input: `response_json_str` (JSON string from `get_onshape_feature_list`). Output: Parsed, filtered feature data (dictionary)."
                "\n7.  **Extract Feature Summaries (`extract_feature_summaries`):** Input: `parsed_features` (output of `feature_parser`). Output: List of simple feature summaries (featureType, featureId, name)."
                "\n8.  **Enrich Feature Summaries (`enrich_feature_summaries`):** Input: `feature_summaries` (list from `extract_feature_summaries`), `url` (document URL). Output: Enriched list of summaries with `createdEntities` and `sketchPlane` data."
                "\n\n"
                "**Example Workflow for Answering a Geometry Question (e.g., 'Describe the part at URL...'):**"
                "\n  1. **Agent Receives Query:** User asks to describe geometry at a given Part Studio URL."
                "\n  2. **Agent Executes Standardized Workflow (if features for this URL not yet processed):**"
                "\n     a. Call `get_onshape_feature_list` with the URL (gets raw feature JSON string)."
                "\n     b. Call `feature_parser` with the JSON string from (a) (gets structured, filtered features dict)."
                "\n     c. Call `extract_feature_summaries` with the dict from (b) (gets list of feature summaries: ID, type, name)."
                "\n     d. Call `enrich_feature_summaries` with the list from (c) and the document URL (adds `createdEntities` and `sketchPlane` info)."
                "\n  3. **Agent Interprets Data:** The agent now has the enriched feature summaries. It uses this data to provide a detailed textual description of the geometry, following the 'Interpreting Geometric Data from Enriched Summaries' guidelines."
                "\n\n"
                "**Conversation Context:**"
                "\n- The user's input may include previous conversation history. Use this for context."
                "\n\n"
                "**General Rules:**"
                "\n- Always use the **most specific tool** available for the task, following the Standardized Workflow for geometry questions."
                "\n- Get `sourceMicroversion` using `get_onshape_document_details` before `create_onshape_feature`."
                "\n- If a tool call fails, report the error message from the tool's output string."
                "\n- Ask for clarification if ambiguous or missing info."
            ),
            model="gpt-4o-mini",
            tools=[
                get_onshape_document_details,
                get_onshape_feature_list,
                get_onshape_featurescript_representation,
                create_onshape_cube,
                create_onshape_feature,
                feature_parser,
                extract_feature_summaries,
                enrich_feature_summaries,
            ],
        )

        # Format the history into a string to prepend to the user query
        history_string = ""
        if self.history:
            history_string += "Conversation History:\n"
            for msg in self.history:
                role = msg.get("role", "unknown").capitalize()
                content = msg.get("content", "")
                history_string += f"{role}: {content}\n"
            history_string += "---\n" # Separator

        # Combine history string with the current user query
        full_input = f"{history_string}Current User Query: {self.user_query}"

        print(f"\nAgent Input (including history):\n{full_input}")

        # Enable tracing to capture the chain of thought
        config = RunConfig(tracing_disabled=False)

        try:
            print(f"[{datetime.now()}] --- Calling Runner.run ---") # Added log
            # Pass the combined string (history + query) as input
            # The result object should conform to RunResultBase (likely RunResult)
            result = await Runner.run(
                starting_agent=onshape_agent,
                input=full_input, # Pass the combined string
                run_config=config
            )
            print(f"[{datetime.now()}] --- Runner.run finished ---") # Added log

            print("\n--- Agent Run Result ---")
            final_output_data = None
            output_message = "Agent did not produce a standard output." # Default message
            chain_of_thought = [] # Default empty list for chain of thought (new_items)
            raw_responses_data = [] # Default empty list for raw responses
            tools_called_summary = [] # Initialize list for tools called summary
            pending_tool_calls = {}   # Initialize dict to link tool calls with their outputs
            call_id_to_tokens = {}    # Initialize dict to map call_id to token usage

            # Extract the final output using result.final_output
            if hasattr(result, 'final_output'):
                final_output_data = result.final_output
                # Attempt to get a string representation for the 'response' field
                if isinstance(final_output_data, str):
                    output_message = final_output_data
                    print(f"Final Output (str):\n{output_message}")
                # Add checks for other potential types if needed, e.g., Pydantic models
                # elif hasattr(final_output_data, 'content') and isinstance(final_output_data.content, str):
                #     output_message = final_output_data.content
                #     print(f"Final Output (object with content):\n{output_message}")
                else:
                    # Fallback to string conversion
                    try:
                        output_message = str(final_output_data)
                        print(f"Final Output (Converted to str):\n{output_message}")
                    except Exception as str_err:
                        print(f"Could not convert final_output to string: {str_err}")
                        output_message = "[Could not represent final output as string]"

                # Serialize the raw final_output for inclusion in the response
                try:
                    # If it's a Pydantic model or dataclass, dump it
                    if hasattr(final_output_data, 'model_dump'):
                        final_output_data = final_output_data.model_dump()
                    elif hasattr(final_output_data, '__dict__'): # Basic object check
                         final_output_data = final_output_data.__dict__
                    # Keep basic types as is (str, int, list, dict etc.)
                except Exception as dump_err:
                    print(f"Error serializing final_output: {dump_err}")
                    final_output_data = {"error": "Could not serialize final_output", "details": str(dump_err)}

            else:
                 print("Could not find '.final_output' attribute on the result.")
                 final_output_data = {"info": "final_output attribute not found."}


            # Phase 1: Pre-process result.raw_responses to map call_id to tokens
            if hasattr(result, 'raw_responses') and isinstance(result.raw_responses, list):
                for model_resp_obj in result.raw_responses:
                    resp_output_list = getattr(model_resp_obj, 'output', [])
                    # Ensure resp_output_list is a list, even if a single item is returned
                    if not isinstance(resp_output_list, list):
                        resp_output_list = [resp_output_list]
                    
                    resp_usage = getattr(model_resp_obj, 'usage', None)

                    if resp_output_list and resp_usage:
                        for out_item in resp_output_list:
                            current_call_id = None
                            # Check if out_item is a Pydantic model with call_id and type='function_call' or 'tool_call'
                            if hasattr(out_item, 'call_id') and hasattr(out_item, 'type') and str(getattr(out_item, 'type', '')).lower() in ['function_call', 'tool_call']:
                                current_call_id = getattr(out_item, 'call_id', None)
                            # Check if out_item is a dict with call_id and type='function_call' or 'tool_call'
                            elif isinstance(out_item, dict) and 'call_id' in out_item and str(out_item.get('type', '')).lower() in ['function_call', 'tool_call']:
                                current_call_id = out_item.get('call_id')
                            
                            if current_call_id:
                                current_call_id_str = str(current_call_id)
                                if hasattr(resp_usage, 'total_tokens'): # Pydantic model-like usage
                                    call_id_to_tokens[current_call_id_str] = {
                                        'total_tokens': getattr(resp_usage, 'total_tokens', 0),
                                        'input_tokens': getattr(resp_usage, 'input_tokens', 0),
                                        'output_tokens': getattr(resp_usage, 'output_tokens', 0)
                                    }
                                elif isinstance(resp_usage, dict): # Dict-like usage
                                    call_id_to_tokens[current_call_id_str] = resp_usage
                                else:
                                    call_id_to_tokens[current_call_id_str] = str(resp_usage) # Fallback

            # Extract the chain of thought (new items) using result.new_items
            if hasattr(result, 'new_items') and isinstance(result.new_items, list):
                print("\n--- Chain of Thought (New Items) ---")
                chain_of_thought = [] # Initialize here
                try:
                    for item in result.new_items:
                        serialized_item = {}
                        if hasattr(item, 'model_dump'):
                            serialized_item = item.model_dump()
                        else:
                            # Fallback for items that don't have model_dump
                            serialized_item = {"item_type": type(item).__name__, "content_str": str(item)}

                        # Attempt to calculate duration from original item object
                        start_time_val = getattr(item, 'start_time', None)
                        end_time_val = getattr(item, 'end_time', None)

                        if start_time_val is not None and end_time_val is not None:
                            try:
                                # Case 1: datetime objects
                                if isinstance(start_time_val, datetime) and isinstance(end_time_val, datetime):
                                    duration = (end_time_val - start_time_val).total_seconds()
                                    serialized_item['duration_seconds'] = duration
                                # Case 2: Numeric timestamps (e.g., float/int seconds since epoch)
                                elif isinstance(start_time_val, (float, int)) and isinstance(end_time_val, (float, int)):
                                    duration = end_time_val - start_time_val
                                    serialized_item['duration_seconds'] = duration
                                # Case 3: Serialized ISO strings (check in serialized_item from model_dump)
                                # This case is less likely if we check attributes on 'item' first, but good as a fallback.
                                elif 'start_time' in serialized_item and 'end_time' in serialized_item and \
                                     isinstance(serialized_item['start_time'], str) and isinstance(serialized_item['end_time'], str):
                                    dt_start = datetime.fromisoformat(str(serialized_item['start_time']).replace('Z', '+00:00'))
                                    dt_end = datetime.fromisoformat(str(serialized_item['end_time']).replace('Z', '+00:00'))
                                    duration = (dt_end - dt_start).total_seconds()
                                    serialized_item['duration_seconds'] = duration
                                else:
                                    serialized_item['duration_calculation_info'] = "Timestamps present but not recognized types for direct calculation."
                            except Exception as e:
                                serialized_item['duration_calculation_error'] = str(e)
                        elif start_time_val is None and end_time_val is None:
                            pass # No timing info, do nothing
                        else:
                            serialized_item['duration_calculation_info'] = "Incomplete timing information (start or end time missing)."

                        chain_of_thought.append(serialized_item)

                        # --- Populate tools_called_summary --- 
                        try:
                            item_obj = item 
                            item_class_name_lower = type(item_obj).__name__.lower()

                            tool_name_attr = None
                            call_id_attr = None

                            if hasattr(item_obj, 'name'): tool_name_attr = item_obj.name
                            if hasattr(item_obj, 'call_id'): call_id_attr = item_obj.call_id

                            raw_item = getattr(item_obj, 'raw_item', None)
                            if raw_item:
                                if tool_name_attr is None and hasattr(raw_item, 'name'): tool_name_attr = raw_item.name
                                if call_id_attr is None and hasattr(raw_item, 'call_id'): call_id_attr = raw_item.call_id
                                if isinstance(raw_item, dict):
                                    if tool_name_attr is None: tool_name_attr = raw_item.get('name')
                                    if call_id_attr is None: call_id_attr = raw_item.get('call_id')
                            
                            call_id_str = str(call_id_attr) if call_id_attr is not None else None
                            tool_name_str = str(tool_name_attr) if tool_name_attr is not None else "Unknown Tool"

                            if call_id_str:
                                # If it's a ToolCallItem (LLM's decision to call a tool)
                                if tool_name_str != "Unknown Tool" and ('toolcallitem' in item_class_name_lower or 'tool_call_item' in item_class_name_lower):
                                    pending_tool_calls[call_id_str] = tool_name_str
                                
                                # If it's a ToolCallOutputItem (actual tool execution's output)
                                elif 'toolcalloutputitem' in item_class_name_lower or 'tool_call_output_item' in item_class_name_lower:
                                    if call_id_str in pending_tool_calls:
                                        retrieved_tool_name = pending_tool_calls.pop(call_id_str)
                                        tokens = call_id_to_tokens.get(call_id_str, "Token info N/A for this call_id")
                                        
                                        # Get duration from the serialized_item already calculated for this item
                                        duration = serialized_item.get('duration_seconds') # This item is the ToolCallOutputItem
                                        
                                        tools_called_summary.append({
                                            'tool_name': retrieved_tool_name,
                                            'duration_seconds': duration, 
                                            'tokens': tokens
                                        })
                                    # else: This output item didn't have a preceding call item in pending_tool_calls
                        
                        except Exception as e_tool_summary:
                            print(f"Error processing item for tools_called_summary: {e_tool_summary}")

                    print(json.dumps(chain_of_thought, indent=2)) # Print formatted JSON
                except Exception as serial_err:
                    print(f"Error serializing chain of thought (new_items): {serial_err}")
                    # Ensure chain_of_thought is a list even on error, for consistent return type
                    chain_of_thought = chain_of_thought or [] # Keep partially processed items if any
                    chain_of_thought.append({"error": "Could not fully serialize chain of thought", "details": str(serial_err)})
            else:
                print("Could not find '.new_items' attribute or it's not a list on the result.")
                chain_of_thought = [{"info": "Chain of thought data (new_items) not available in expected format."}]

            # Extract the raw LLM responses using result.raw_responses
            if hasattr(result, 'raw_responses') and isinstance(result.raw_responses, list):
                print("\n--- Raw LLM Responses ---")
                try:
                    # Convert ModelResponse objects to serializable dictionaries
                    raw_responses_data = [resp.model_dump() if hasattr(resp, 'model_dump') else str(resp) for resp in result.raw_responses]
                    print(json.dumps(raw_responses_data, indent=2)) # Print formatted JSON
                except Exception as serial_err:
                    print(f"Error serializing raw_responses: {serial_err}")
                    raw_responses_data = [{"error": "Could not serialize raw_responses", "details": str(serial_err)}]
            else:
                print("Could not find '.raw_responses' attribute or it's not a list on the result.")
                raw_responses_data = [{"info": "Raw responses data not available in expected format."}]


            # Construct the updated history
            updated_history = self.history + [
                {"role": "user", "content": self.user_query},
                {"role": "assistant", "content": output_message} # Use the extracted/formatted message
            ]

            print("------------------------")

            overall_end_time_success = datetime.now() # Record end time for successful execution
            total_duration_seconds_success = (overall_end_time_success - overall_start_time).total_seconds()

            # Return the structured response including new fields
            response_dict_success = {
                "response": output_message, # User-friendly final message
                "final_output": final_output_data, # Raw final output from agent
                "chain_of_thought": chain_of_thought, # Serialized new_items
                "raw_responses": raw_responses_data, # Serialized raw LLM responses
                "history": updated_history,
                "total_time_seconds": total_duration_seconds_success, # Added total time
                "tools_called_summary": tools_called_summary # Added tools called summary
            }
            print(f"[{datetime.now()}] --- Returning successful response --- ") # Added log
            return response_dict_success


        except Exception as e:
            print(f"\nAn error occurred while running the agent: {e}")
            import traceback
            traceback.print_exc() # Print traceback for debugging

            overall_end_time_error = datetime.now() # Record end time for error case
            total_duration_seconds_error = (overall_end_time_error - overall_start_time).total_seconds()

            # Return an error dictionary including new fields as None
            response_dict_error = {
                "error": f"An error occurred during agent execution: {e}",
                "response": None,
                "final_output": None,
                "chain_of_thought": None,
                "raw_responses": None,
                "history": self.history, # Return the history *before* this failed turn
                "total_time_seconds": total_duration_seconds_error, # Added total time
                "tools_called_summary": [] # Empty list in case of error before processing
            }
            print(f"[{datetime.now()}] --- Returning error response --- ") # Added log
            return response_dict_error
