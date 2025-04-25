import requests
import json
import os
from dotenv import load_dotenv
from agents import Agent, ModelSettings, function_tool, Runner, RunConfig
import asyncio
import re # Import regex for URL parsing
from typing import Union # Import Union

# --- Onshape Tool Definitions ---

# Load environment variables from .env file
# Ensure your .env file with ACCESS_KEY and SECRET_KEY is in the same directory
# or accessible in your environment when running this.
load_dotenv()

ONSHAPE_API_BASE_URL = "https://cad.onshape.com/api" # Use the /api endpoint


# --- Tool 1: Get Document Details ---

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


# --- Tool 2: Create Onshape Feature ---

def _parse_onshape_url(url: str) -> Union[dict, None]:
    """Parses a standard Onshape document URL to extract IDs."""
    # Regex to capture did, wvmid (w, v, or m), and eid
    match = re.search(r"/documents/([a-zA-Z0-9]+)/([wvm])/([a-zA-Z0-9]+)/e/([a-zA-Z0-9]+)", url)
    if match:
        did, wv_type, wv_id, eid = match.groups()
        # Combine wv_type and wv_id into wvmid for API consistency if needed, or keep separate
        # For the features endpoint, w/wid seems standard. Let's check if we got 'w'.
        if wv_type == 'w':
             return {"did": did, "wid": wv_id, "eid": eid}
        else:
             # Handle cases where the URL is for a version or microversion if needed
             # For this specific tool, we might require a workspace URL
             print(f"[URL Parse] URL type '{wv_type}' not directly usable for feature creation endpoint requiring workspace 'w'.")
             return None # Indicate parsing failure or incompatibility
    else:
        print("[URL Parse] Failed to parse URL with regex.")
        return None

# Helper function containing the core logic (undecorated)
def _create_onshape_feature_logic(part_studio_url: str, feature_payload_str: str) -> str:
    """Internal logic to create a feature in an Onshape Part Studio using a provided JSON payload."""
    print(f"[Tool Logic] Attempting to create feature for URL: {part_studio_url}")
    print(f"[Tool Logic] Received Payload String:\n{feature_payload_str}") # Log the raw payload string

    # --- 1. Parse URL ---
    parsed_ids = _parse_onshape_url(part_studio_url)
    if not parsed_ids:
        return f"Error: Could not parse Document ID, Workspace ID, and Element ID from the provided URL: {part_studio_url}. Ensure it's a valid Onshape Part Studio URL with a workspace (e.g., /w/).'"

    did = parsed_ids["did"]
    wid = parsed_ids["wid"]
    eid = parsed_ids["eid"]

    api_url = f"{ONSHAPE_API_BASE_URL}/partstudios/d/{did}/w/{wid}/e/{eid}/features"
    print(f"[Tool Logic] Constructed API URL: {api_url}")

    # --- 2. Parse Payload JSON ---
    try:
        feature_payload = json.loads(feature_payload_str)
        print(f"[Tool Logic] Successfully Parsed Payload JSON.")
    except json.JSONDecodeError as e:
        error_msg = f"Error: Failed to parse the provided feature_payload string as JSON: {e}. Payload received:\n{feature_payload_str}"
        print(f"[Tool Logic] {error_msg}")
        return error_msg

    # --- 3. Authentication ---
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

    # --- 4. Make API Call ---
    print(f"[Tool Logic] Attempting POST request to {api_url} with parsed payload.")
    try:
        response = requests.post(
            api_url,
            auth=(access_key, secret_key),
            headers=headers,
            json=feature_payload, # Send the parsed dictionary as JSON
            timeout=30
        )

        print(f"[Tool Logic] Response Status Code: {response.status_code}")

        # Process response (same logic as before)
        if response.ok:
            try:
                response_json = response.json()
                print("[Tool Logic] Successfully created feature.")
                return f"Successfully created feature. Response: {json.dumps(response_json, indent=2)}"
            except json.JSONDecodeError:
                return f"Successfully sent request to {api_url} (Status: {response.status_code}), but the response was not valid JSON."
        else:
            error_msg = f"Error: Failed to create feature via {api_url}. Status Code: {response.status_code}."
            print(f"[Tool Logic] {error_msg}")
            return error_msg + f" Response Text: {response.text[:500]}"

    except requests.exceptions.Timeout:
        error_msg = f"Error: Request timed out after 30 seconds while trying to reach {api_url}."
        print(f"[Tool Logic] {error_msg}")
        return error_msg
    except requests.exceptions.RequestException as e:
        error_msg = f"Error: A network communication error occurred while requesting {api_url}: {e}"
        print(f"[Tool Logic] {error_msg}")
        return error_msg
    except Exception as e:
        error_msg = f"Error: An unexpected error occurred within the create feature tool logic: {e}"
        print(f"[Tool Logic] {error_msg}")
        return error_msg

# Decorated function for the agent framework
@function_tool
def create_onshape_feature(part_studio_url: str, feature_payload_json: str) -> str:
    """
    Creates a new feature in a specified Onshape Part Studio based on a provided JSON payload.
    The agent MUST generate the correct JSON payload defining the feature according to the
    Onshape API specification before calling this tool.

    Args:
        part_studio_url: The full URL of the Onshape Part Studio element where the
                         feature should be created. Must contain document ID (did),
                         workspace ID (wid), and element ID (eid).
                         Example: 'https://cad.onshape.com/documents/DID/w/WID/e/EID'
        feature_payload_json: A valid JSON string defining the feature to be created.
                              This JSON must conform to the Onshape 'Add Feature' API endpoint structure.
                              The agent is responsible for generating this based on the user's request.

    Returns:
        A string indicating success (including details from the API response)
        or a descriptive error message if the operation fails (e.g., invalid URL,
        invalid JSON payload, API error).
    """
    # Call the internal logic function, passing the JSON string directly
    return _create_onshape_feature_logic(part_studio_url, feature_payload_json)


# --- Agent Definition ---

# Define the Onshape Agent
onshape_agent = Agent(
    name="Onshape Assistant Agent V2", # Renamed agent
    instructions=(
        "You are a helpful assistant knowledgeable about Onshape documents and capable of creating features using the Onshape REST API v9. "
        "You have two tools: 'get_onshape_document_details' and 'create_onshape_feature'."
        "\n\n"
        "1.  **Get Details:** If the user asks for details about a specific Onshape document and provides its ID, "
        "use the 'get_onshape_document_details' tool. This tool returns document details, including the current 'microversionId', "
        "which is crucial for creating features reliably. Present the key information clearly."
        "\n\n"
        "2.  **Create Feature:** If the user asks to create a new feature (like a cube, extrude, sketch, fillet, etc.) "
        "in a specific Part Studio and provides its **full URL**, you MUST use the 'create_onshape_feature' tool."
        "\n   To use this tool, you need TWO arguments:"
        "\n   - `part_studio_url`: The full URL provided by the user (e.g., 'https://cad.onshape.com/documents/DID/w/WID/e/EID')."
        "\n   - `feature_payload_json`: A JSON **string** that YOU MUST GENERATE, defining the feature. "
        "\n\n   **Generating the `feature_payload_json`:**"
        "\n   - **STEP 1 (Recommended):** Before generating the payload, consider calling `get_onshape_document_details` for the document ID "
        "     (extracted from the `part_studio_url`) to get the latest `sourceMicroversion`. This is important!"
        "\n   - **STEP 2:** Construct a valid JSON string based precisely on the user's request (e.g., dimensions, feature type, name, location)."
        "\n   - The JSON structure MUST follow this **exact** template for the `addPartStudioFeature` endpoint:"
        "\n     ```json\n"
        "     {\n"
        '       "btType": "BTFeatureDefinitionCall-1406",\n'  # <<< Use this exact outer btType
        '       "feature": {\n'
        '         "btType": "BTMFeature-134",\n'             # <<< Use this btType for standard features (or BTMSketch-151 for sketches)
        '         "featureType": "string",\n'                  # <<< Determine from user (e.g., "extrude", "sketch", "cube", "fillet")
        '         "name": "string",\n'                         # <<< Generate descriptive name from user request
        '         "parameters": [ \n'                          # <<< *** GENERATE THIS ARRAY CAREFULLY ***
        "           // Add parameter objects here based on featureType and user request.\n"
        "           // Use the correct parameter btType from the documentation!\n"
        "           // Example Parameter Types:\n"
        '           //   Quantity:  { "btType": "BTMParameterQuantity-147", "parameterId": "id_like_depth_or_radius", "expression": "value_with_units" }\n'
        '           //   QueryList: { "btType": "BTMParameterQueryList-148", "parameterId": "id_like_entities_or_sketchPlane", "queries": [ { query_object } ] }\n'
        '           //   Enum:      { "btType": "BTMParameterEnum-145", "parameterId": "id_like_operationType_or_bodyType", "value": "ENUM_VALUE", "enumName": "OnshapeEnumName" }\n'
        '           //   Boolean:   { "btType": "BTMParameterBoolean-144", "parameterId": "id_like_booleanOption", "value": true_or_false }\n'
        "           // See documentation examples for specific parameters needed for 'extrude', 'sketch', 'cube', 'fillet' etc.\n"
        "         ],\n"
        '         "suppressed": false,\n'                       # <<< Usually false unless requested
        '         "returnAfterSubfeatures": false\n'           # <<< Usually false
        '         // "namespace": "" // Often optional\n'
        "       },\n"
        '       // "serializationVersion": "...", // Optional, API typically uses latest\n'
        '       "sourceMicroversion": "string" \n'              # <<< *** Fill this with microversionId obtained from get_onshape_document_details! *** If unavailable, the API call might fail. Acknowledge this risk.\n'
        '       // "rejectMicroversionSkew": false // Optional\n'
        "     }\n"
        "     ```\n"
        "   - **Populating Parameters:** This is the most complex part. Carefully identify the required `parameterId`s for the requested `featureType` (e.g., an 'extrude' needs 'depth' and 'entities'). Use the correct parameter `btType` and structure based on the documentation examples (Quantity uses 'expression', QueryList uses 'queries' with `deterministicIds` or `queryString`, Enum uses 'value' and 'enumName'). Infer values (like `25 * mm`, `NEW`, sketch IDs) from the user query."
        "\n   - Ensure the final output for `feature_payload_json` is a valid, single-line or multi-line JSON string."
        "\n\n"
        "**Example Workflow for 'Create Cylinder (Extrude Sketch)':**"
        "\n1. User provides URL and asks to extrude a specific sketch ('Sketch 1') by 1 inch."
        "\n2. Call `get_onshape_document_details` to get the `sourceMicroversion`."
        "\n3. Generate the `feature_payload_json`:"
        "\n   - Outer `btType`: 'BTFeatureDefinitionCall-1406'"
        "\n   - `feature.btType`: 'BTMFeature-134'"
        "\n   - `feature.featureType`: 'extrude'"
        "\n   - `feature.name`: 'Extrude Sketch 1'"
        "\n   - `feature.parameters`: MUST include parameters for:"
        "\n     - `bodyType` (Enum: 'SOLID', 'ExtendedToolBodyType')"
        "\n     - `operationType` (Enum: 'NEW', 'NewBodyOperationType')"
        "\n     - `entities` (QueryList: referencing the sketch's featureId - e.g., `[{ 'btType': 'BTMIndividualSketchRegionQuery-140', 'featureId': '{sketch_feature_id}' }]`)"
        "\n     - `endBound` (Enum: 'BLIND', 'BoundingType')"
        "\n     - `depth` (Quantity: '1 * inch')"
        "\n   - `sourceMicroversion`: Use the value obtained in step 2."
        "\n4. Call `create_onshape_feature` with the URL and the generated JSON string."
        "\n\n"
        "**General Rules:**"
        "\n- Always use the tools when appropriate. Do not guess results."
        "\n- If a tool call fails (e.g., `create_onshape_feature` returns a 400 error), **report the specific error message provided in the tool's output string** back to the user. This helps diagnose the problem (often an invalid payload)."
        "\n- Ask for clarification if the user's request is ambiguous or missing required information (URL, dimensions, feature specifics)."
    ),
    model="gpt-4o-mini",
    tools=[
        get_onshape_document_details,
        create_onshape_feature
    ],
)


# --- Example Usage (How you might run this agent) ---

async def run_agent_example():
    """Runs the Onshape agent with a sample query."""
    print("Running Onshape Agent example...")

    # --- Query for Get Details ---
    # user_query = "Could you please provide details for the Onshape document with ID 34194a7792ea9db6d10188d3"

    # --- Query for Create Feature ---
    # Replace with a valid Part Studio URL you have write access to
    test_part_studio_url = "https://cad.onshape.com/documents/34194a7792ea9db6d10188d3/w/2603dadfb9d5ccf8117390d0/e/ff8bd4f1cd0882be07172a4d" # Example URL
    # Example request that requires the agent to generate the payload
    user_query = f"Please create a simple extrusion, call it 'My Test Extrude', make it 25 mm deep, in the Part Studio at this URL: {test_part_studio_url}. Assume you can use the default front plane or an existing sketch if available for the profile."
    # A more complex request: user_query = f"Create a 1.5 inch cube named 'UserCube' centered at the origin on the Top plane in the Part Studio: {test_part_studio_url}"


    print(f"\nUser Query: {user_query}")

    config = RunConfig(tracing_disabled=True)

    try:
        result = await Runner.run(
            starting_agent=onshape_agent,
            input=user_query,
            run_config=config
        )

        print("\n--- Agent Run Result ---")
        if hasattr(result, 'output'):
            if isinstance(result.output, str):
                print(f"Final Output:\n{result.output}")
            else:
                print(f"Final Output (Structured):\n{result.output}")
        else:
            print("Could not find '.output' attribute on the result. Printing the full result object:")
            print(result)
        print("------------------------")

    except Exception as e:
        print(f"\nAn error occurred while running the agent: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
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

