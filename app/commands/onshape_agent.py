import requests
import json
import os
from dotenv import load_dotenv
from agents import Agent, ModelSettings, function_tool, Runner, RunConfig
import asyncio
import re # Import regex for URL parsing
from typing import Union # Import Union
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

    def __init__(self, user_query: str):
        self.user_query = user_query
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
        name="Onshape Assistant Agent V5",  # Renamed agent again
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
            "**General Rules:**"
            "\n- Always use the **most specific tool** available."
            "\n- Get the `sourceMicroversion` using `get_onshape_document_details` before attempting `create_onshape_feature`."
            "\n- If a tool call fails, **report the specific error message from the tool's output string** back to the user."
            "\n- Ask for clarification if the request is ambiguous or missing required information."
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

        # test_part_studio_url = "https://cad.onshape.com/documents/34194a7792ea9db6d10188d3/w/2603dadfb9d5ccf8117390d0/e/ff8bd4f1cd0882be07172a4d" # Example URL
        # user_query = f"Show me the featurescript representation for the part studio {test_part_studio_url}"


        print(f"\nUser Query: {self.user_query}")

        config = RunConfig(tracing_disabled=True)

        try:
            result = await Runner.run(
                starting_agent=onshape_agent,
                input=self.user_query,
                run_config=config
            )

            print("\n--- Agent Run Result ---")
            output_message = "Agent did not produce a standard output." # Default message

            if hasattr(result, 'output'):
                if isinstance(result.output, str):
                    output_message = result.output
                    print(f"Final Output:\n{output_message}")
                else:
                    # If output is structured, convert to string or handle as needed
                    # For now, let's represent it as a string
                    output_message = str(result.output)
                    print(f"Final Output (Structured):\n{output_message}")
                return {"message": output_message} # Return the output message in a dict
            else:
                print("Could not find '.output' attribute on the result. Printing the full result object:")
                print(result)
                # Attempt to return the result object itself if serializable, or an error
                try:
                    # Check if the result object itself can be returned (might be a dict or serializable)
                    # This depends heavily on the structure of the 'result' object from Runner.run
                    # If result is often a dict-like object, this might work.
                    if isinstance(result, dict):
                         return {"message": "Agent result structure unclear, returning full result.", "data": result}
                    else:
                         # Fallback if result is not a dict
                         return {"error": output_message, "details": str(result)}
                except Exception:
                     return {"error": output_message, "details": "Result object not serializable."}


            print("------------------------")


        except Exception as e:
            print(f"\nAn error occurred while running the agent: {e}")
            import traceback
            traceback.print_exc() # Print traceback for debugging
            # Return an error dictionary
            return {"error": f"An error occurred during agent execution: {e}"}


