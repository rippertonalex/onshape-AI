import requests
import json
import os
from dotenv import load_dotenv
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
)
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
        onshape_agent = Agent(
            name="Onshape Assistant Agent V6", # Incremented version for clarity
            instructions=(
                "You are a helpful assistant knowledgeable about Onshape documents and capable of viewing and creating features using the Onshape REST API v10. "
                "You have five tools: 'get_onshape_document_details', 'get_onshape_feature_list', 'get_onshape_featurescript_representation', 'create_onshape_cube', and 'create_onshape_feature'."
                "\n\n"
                "1.  **Get Document Details:** Use for overall document info (like 'microversionId'). Requires document ID."
                "\n\n"
                "2.  **Get Feature List:** Use when asked to **list the features** in a Part Studio. Requires the full Part Studio URL. Returns a JSON list of features."
                "\n\n"
                "3.  **Get FeatureScript Representation:** Use when asked for the **FeatureScript representation** or underlying code of a Part Studio. Requires the full Part Studio URL. Returns the FeatureScript data (often JSON or plain text)."
                "\n\n"
                "4.  **Create Cube:** Use ONLY when asked to create a **simple 'cube'**. Requires `part_studio_url`, `name`, and `side_length_expression`."
                "\n   **Example:** 'Create a 2 inch cube named TestCube at URL ...' -> call `create_onshape_cube(part_studio_url='...', name='TestCube', side_length_expression='2 * inch')`."
                "\n\n"
                "5.  **Create Feature (General):** Use for creating **any other feature type** (sketch, extrude, fillet, etc.). Requires `part_studio_url` and a generated `feature_payload_json` string conforming to the Onshape API v10 'addPartStudioFeature' structure."
                "\n   **WARNING:** Generating the payload is difficult. Prefer specific tools like `create_onshape_cube` when available."
                "\n\n"
                "**Conversation Context:**"
                "\n- The user's input may include previous conversation history formatted before the current query. Use this history for context."
                "\n\n"
                "**General Rules:**"
                "\n- Always use the **most specific tool** available."
                "\n- Get the `sourceMicroversion` using `get_onshape_document_details` before attempting `create_onshape_feature`."
                "\n- If a tool call fails, **report the specific error message from the tool's output string** back to the user."
                "\n- Ask for clarification if the request is ambiguous or missing required information based on the conversation history and current query."
            ),
            model="gpt-4o-mini",
            tools=[
                get_onshape_document_details,
                get_onshape_feature_list,
                get_onshape_featurescript_representation,
                create_onshape_cube,
                create_onshape_feature,
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
            # Pass the combined string (history + query) as input
            # The result object should conform to RunResultBase (likely RunResult)
            result = await Runner.run(
                starting_agent=onshape_agent,
                input=full_input, # Pass the combined string
                run_config=config
            )

            print("\n--- Agent Run Result ---")
            final_output_data = None
            output_message = "Agent did not produce a standard output." # Default message
            chain_of_thought = [] # Default empty list for chain of thought (new_items)
            raw_responses_data = [] # Default empty list for raw responses

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


            # Extract the chain of thought (new items) using result.new_items
            if hasattr(result, 'new_items') and isinstance(result.new_items, list):
                print("\n--- Chain of Thought (New Items) ---")
                try:
                    # Convert RunItem objects (or whatever they are) to serializable dictionaries
                    chain_of_thought = [item.model_dump() if hasattr(item, 'model_dump') else str(item) for item in result.new_items]
                    print(json.dumps(chain_of_thought, indent=2)) # Print formatted JSON
                except Exception as serial_err:
                    print(f"Error serializing chain of thought (new_items): {serial_err}")
                    chain_of_thought = [{"error": "Could not serialize chain of thought", "details": str(serial_err)}]
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

            # Return the structured response including new fields
            return {
                "response": output_message, # User-friendly final message
                "final_output": final_output_data, # Raw final output from agent
                "chain_of_thought": chain_of_thought, # Serialized new_items
                "raw_responses": raw_responses_data, # Serialized raw LLM responses
                "history": updated_history
            }


        except Exception as e:
            print(f"\nAn error occurred while running the agent: {e}")
            import traceback
            traceback.print_exc() # Print traceback for debugging

            # Return an error dictionary including new fields as None
            return {
                "error": f"An error occurred during agent execution: {e}",
                "response": None,
                "final_output": None,
                "chain_of_thought": None,
                "raw_responses": None,
                "history": self.history # Return the history *before* this failed turn
            }
