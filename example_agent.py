import requests
import json
import os
from dotenv import load_dotenv
from agents import Agent, ModelSettings, function_tool, Runner, RunConfig # Add Runner and RunConfig
import asyncio # Import asyncio

# --- Onshape Tool Definition ---

# Load environment variables from .env file
# Ensure your .env file with ACCESS_KEY and SECRET_KEY is in the same directory
# or accessible in your environment when running this.
load_dotenv()

ONSHAPE_API_BASE_URL = "https://cad.onshape.com/api" # Use the /api endpoint


# Helper function containing the core logic (undecorated)
def _fetch_onshape_document_details_logic(document_id: str) -> str:
    """Internal logic to fetch Onshape document details."""
    api_url = f"{ONSHAPE_API_BASE_URL}/documents/{document_id}"
    print(f"[Tool Logic] Attempting to fetch: {api_url}")

    access_key = os.getenv("ACCESS_KEY")
    secret_key = os.getenv("SECRET_KEY")

    if not access_key or not secret_key:
        error_msg = "Error: Onshape ACCESS_KEY or SECRET_KEY not found in environment variables. Cannot use tool."
        print(f"[Tool Logic] {error_msg}")
        return error_msg

    masked_access_key = f"{access_key[:5]}..." if access_key else "None"
    print(f"[Tool Logic] Using Access Key: {masked_access_key}")

    headers = {
        'Accept': 'application/vnd.onshape.v1+json;charset=UTF-8;qs=0.1',
        'Content-Type': 'application/json'
    }

    try:
        response = requests.get(
            api_url,
            auth=(access_key, secret_key),
            headers=headers,
            timeout=20
        )

        print(f"[Tool Logic] Response Status Code: {response.status_code}")

        if response.ok:
            try:
                response_json = response.json()
                print("[Tool Logic] Successfully fetched and decoded JSON.")
                return json.dumps(response_json, indent=2)
            except json.JSONDecodeError:
                error_msg = f"Error: Successfully fetched from {api_url} but failed to decode JSON response. Status: {response.status_code}."
                print(f"[Tool Logic] {error_msg}")
                return error_msg + f" Raw response preview: {response.text[:200]}"
        else:
            error_msg = f"Error: Failed to fetch from {api_url}. Status Code: {response.status_code}."
            print(f"[Tool Logic] {error_msg}")
            return error_msg + f" Response Text: {response.text[:200]}"

    except requests.exceptions.Timeout:
        error_msg = f"Error: Request timed out after 20 seconds while trying to reach {api_url}."
        print(f"[Tool Logic] {error_msg}")
        return error_msg
    except requests.exceptions.RequestException as e:
        error_msg = f"Error: A network communication error occurred while requesting {api_url}: {e}"
        print(f"[Tool Logic] {error_msg}")
        return error_msg
    except Exception as e:
        error_msg = f"Error: An unexpected error occurred within the tool logic: {e}"
        print(f"[Tool Logic] {error_msg}")
        return error_msg


# Decorated function for the agent framework
@function_tool
def get_onshape_document_details(document_id: str) -> str:
    """
    Fetches details for a specific Onshape document using its ID from the Onshape API.

    Args:
        document_id: The unique identifier (alphanumeric string) of the Onshape document.
                     Example: '7820391e3a9b37485d78da07'

    Returns:
        A string containing the JSON details of the document if successful,
        or a descriptive error message if the request fails, keys are missing,
        or the response is not valid JSON.
    """
    # Call the internal logic function
    return _fetch_onshape_document_details_logic(document_id)


# --- Agent Definition ---

# Define the Onshape Agent
onshape_agent = Agent(
    name="Onshape Document Agent",
    instructions=(
        "You are a helpful assistant knowledgeable about Onshape documents. "
        "If the user asks for details about a specific Onshape document and provides its ID, "
        "use the 'get_onshape_document_details' tool to fetch the information. "
        "Present the key information from the fetched data to the user in a clear way. "
        "If the tool returns an error, inform the user about the error."
        "Do not guess document details; only use the tool."
    ),
    # Replace 'o3-mini' with the actual model you intend to use (e.g., 'gpt-4', 'gpt-3.5-turbo')
    # Check the 'agents' library documentation for supported model identifiers
    model="gpt-4o-mini",
    # model_settings=ModelSettings(temperature=0.7), # Optional: configure model params
    tools=[get_onshape_document_details], # Still pass the decorated function here
)


# --- Example Usage (How you might run this agent) ---

async def run_agent_example():
    """Runs the Onshape agent with a sample query."""
    print("Running Onshape Agent example...")

    # Define the user query
    user_query = "Could you please provide details for the Onshape document here is the url with docid: https://cad.onshape.com/documents/34194a7792ea9db6d10188d3/w/2603dadfb9d5ccf8117390d0/e/ff8bd4f1cd0882be07172a4d"
    print(f"\nUser Query: {user_query}")

    # Define RunConfig (optional, disabling tracing as per example)
    config = RunConfig(tracing_disabled=True)

    # Run the agent using Runner.run
    try:
        # Assuming no specific context is needed for this simple case (context=None)
        result = await Runner.run(
            starting_agent=onshape_agent,
            input=user_query,
            run_config=config
            # context=None, # Explicitly setting context to None if not needed
            # max_turns=5 # Optional: Limit the number of turns
        )

        # Process the result
        # The exact structure of RunResult needs verification from the library's
        # actual usage or more detailed docs. Common attributes might be .output, .final_output, .result
        # We'll try accessing .output first.
        print("\n--- Agent Run Result ---")
        # print(f"Raw Result Object: {result}") # Uncomment to inspect the full result object

        if hasattr(result, 'output'):
             # Check if the output is a simple string or might need further processing
            if isinstance(result.output, str):
                print(f"Final Output:\n{result.output}")
            else:
                 # If output is structured (like a Pydantic model if you used output_type)
                print(f"Final Output (Structured):\n{result.output}")
        else:
            print("Could not find '.output' attribute on the result. Printing the full result object:")
            print(result)

        print("------------------------")

    except Exception as e:
        print(f"\nAn error occurred while running the agent: {e}")
        import traceback
        traceback.print_exc() # Print full traceback for debugging


if __name__ == "__main__":
    # Use asyncio.run() to execute the async function
    asyncio.run(run_agent_example())

    # --- Keep direct tool test commented out if needed for debugging ---
    # print("\n--- Direct Tool Logic Test ---")
    # test_doc_id = "7820391e3a9b37485d78da07"
    # tool_result = _fetch_onshape_document_details_logic(test_doc_id)
    # print(f"Direct call to _fetch_onshape_document_details_logic('{test_doc_id}') returned:")
    # try:
    #     parsed_json = json.loads(tool_result)
    #     print(json.dumps(parsed_json, indent=4))
    # except json.JSONDecodeError:
    #     print(tool_result)
    # print("------------------------")

