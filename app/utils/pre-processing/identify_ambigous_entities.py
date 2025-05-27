import sys
import os

# Calculate the project root directory based on the current script's location
# This script is in app/utils/pre-processing, so we need to go up three levels
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Now your imports should work
from app.utils.onshape_tools import _onshape_url_to_enriched_feature_summary_logic
import json
from openai import AsyncOpenAI
from dotenv import load_dotenv
import asyncio # Ensure asyncio is imported
import re

# Load environment variables (assuming .env is in project_root)
load_dotenv(os.path.join(project_root, '.env')) 

# Assumed globals (to be defined at module level by colleague after imports):
# OPENAI_API_KEY: str (loaded from .env or environment)
# OPENAI_MODEL_FOR_AMBIGUITY: str (e.g., "gpt-4.1-nano", loaded from .env or environment)
#
#Assumed imports (to be added at the top of the file by colleague):
# import json # Moved up
# from openai import AsyncOpenAI # Moved up
# For loading OPENAI_API_KEY and OPENAI_MODEL_FOR_AMBIGUITY:
# import os # Moved up
# from dotenv import load_dotenv # Moved up

# # Example setup for globals (colleague to adapt and place at module level):
# # load_dotenv() # Moved up and made more specific
# # OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# # OPENAI_MODEL_FOR_AMBIGUITY = os.getenv("OPENAI_MODEL_FOR_AMBIGUITY", "gpt-4.1-nano")
# # if not OPENAI_API_KEY:
# #     print("CRITICAL: OPENAI_API_KEY is not set. identify_ambiguous_entities will fail.")
# # if not OPENAI_MODEL_FOR_AMBIGUITY:
# #     print("CRITICAL: OPENAI_MODEL_FOR_AMBIGUITY is not set. identify_ambiguous_entities will fail.")


async def identify_ambigous_entities(
    parsed_features: dict, 
    enriched_feature_summaries: list
) -> list:
    """
    Identifies entities within Onshape feature data that require more detailed descriptions 
    to fully define the geometry, using an OpenAI Chat Completions call.

    This function assumes that `OPENAI_API_KEY` and `OPENAI_MODEL_FOR_AMBIGUITY` are available
    in the global scope of this module, and that necessary modules (`json`, `openai.AsyncOpenAI`)
    have been imported at the top of the file.

    Args:
        parsed_features (dict): The parsed feature data from the Onshape API,
                                typically the output of `feature_parser`.
        enriched_feature_summaries (list): The enriched feature summaries,
                                          typically the output of `enrich_feature_summaries`.

    Returns:
        list: A list of entity IDs (strings) that need more detail, e.g., ['IB', 'JDC', 'JGO', 'JHK', 'KIlC'],
              or an empty list if the process fails or no ambiguous entities are found.
    """

    # --- Prompt Definition ---
    # System prompt incorporates the detailed instructions provided by the user.
    system_prompt = (
        "Attached are files describing an onshape part studio. Your ultimate goal is to form a precise mental image of the represented geometry.\n\n"
        "The features will be listed in order, and can be a sketch or a 3D type feature like and extrude or fillet.\n\n"
        "There will be certain entities (3 or 4 letter IDs) which you don't know the exact details of.\n\n"
        "For a sketch, you will be able to define the exact geometry of the sketch, but not the sketch plane exactly. You will know it's ID however.\n\n"
        "Similarly for a 3D feature like an extrude or fillet, you will know it's exact behavior and the IDs of the entities which the feature acts on, "
        "but not the exact definition of these entities.\n\n"
        "Please identify the entities for which you require a more detailed description to EXACTLY define the geometry. "
        "Your response must be ONLY a JSON array of entity IDs, for example: [\"IB\", \"JDC\", \"JGO\", \"JHK\", \"KIlC\"]\n"
        "Do not include any other text, explanations, or formatting. Only return the JSON array.\n\n"
        "Here is a suggested order of operations:\n"
        "• Look through the parsed output file.\n"
        "• For a sketch, define precisely the 2D geometry created. Consider any unit conversions necessary. Consider constraints.\n"
        "• For a 3D feature like an extrude or fillet, define precisely its action (e.g. it extrudes 3mm in direction z+ or it fillets 0.25in) and which entities it acts on (usually a 3 or 4 letter ID).\n"
        "• Look through the summary_output.\n"
        "• Identify any relationships between entities acted on by 3D features or by a sketch (perhaps the sketch plane). Your goal here is to link all entities so that we can fully resolve the geometry."
    )

    try:
        # `json` module is assumed to be imported at the top of the file.
        # If `json` is not imported, this line will raise a NameError.
        user_prompt_content = (
            f"Parsed Features Data:\n{json.dumps(parsed_features, indent=2)}\n\n"
            f"Enriched Feature Summary:\n{json.dumps(enriched_feature_summaries, indent=2)}\n\n"
            "Based on your instructions (form a precise mental image and identify entities needing more detail), "
            "please provide your analysis as a JSON array of entity IDs only."
        )
    except NameError:
        # This occurs if `json` is not imported.
        error_message = "Critical Error: `json` module not imported. Cannot serialize data for OpenAI prompt."
        print(error_message)
        return []
    except Exception as e: # Catch potential json.dumps errors
        error_message = f"Error serializing data for OpenAI prompt: {type(e).__name__} - {e}"
        # Consider logging this error properly in a real application.
        print(error_message) 
        return []

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt_content}
    ]

    # --- OpenAI API Call ---
    try:
        # `AsyncOpenAI` is assumed to be imported from `openai` at the top of the file.
        # `OPENAI_API_KEY` and `OPENAI_MODEL_FOR_AMBIGUITY` are assumed to be global constants.
        # If these are not defined in the global scope, a NameError will be raised here.
        
        client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        completion = await client.chat.completions.create(
            model="gpt-4.1", # Assuming OPENAI_MODEL_FOR_AMBIGUITY would be used here if defined and intended
            messages=messages
        )
        
        response_content = completion.choices[0].message.content
        if response_content is None:
            print("Error: OpenAI API returned a null response content.")
            return []
        
        # Parse the JSON response
        try:
            # Clean the response to extract just the JSON array
            response_content = response_content.strip()
            # Try to parse as JSON
            entity_ids = json.loads(response_content)
            
            # Validate that it's a list
            if not isinstance(entity_ids, list):
                print(f"Error: Expected JSON array, got {type(entity_ids)}")
                return []
            
            # Validate that all items are strings (entity IDs)
            for item in entity_ids:
                if not isinstance(item, str):
                    print(f"Error: Expected string entity ID, got {type(item)}: {item}")
                    return []
            
            return entity_ids
            
        except json.JSONDecodeError as je:
            print(f"Error parsing JSON response: {je}")
            print(f"Raw response: {response_content}")
            # Try to extract entity IDs using regex as fallback
            try:
                # Look for patterns like 3-4 letter IDs in the response
                entity_pattern = r'\b[A-Za-z]{3,4}\b'
                found_entities = re.findall(entity_pattern, response_content)
                # Filter to likely entity IDs (3-4 characters, alphanumeric)
                filtered_entities = [e for e in found_entities if len(e) in [3, 4] and e.isalnum()]
                return list(set(filtered_entities))  # Remove duplicates
            except Exception as fallback_error:
                print(f"Fallback parsing also failed: {fallback_error}")
                return []

    except NameError as ne:
        # This catches if `AsyncOpenAI`, `OPENAI_API_KEY`, or `OPENAI_MODEL_FOR_AMBIGUITY` are not defined.
        error_message = f"Configuration or Import Error: A required name is not defined: {ne}. Ensure imports and global API variables are set."
        print(error_message)
        return []
    except Exception as e:
        # In a real application, import traceback and use traceback.print_exc() for detailed debugging.
        error_message = f"Error during OpenAI API call: {type(e).__name__} - {e}"
        print(error_message) 
        return []

if __name__ == "__main__":
    # The _onshape_url_to_enriched_feature_summary_logic call returns a dictionary or an error string.
    # We need to capture its output to pass to identify_ambigous_entities.
    print("Running _onshape_url_to_enriched_feature_summary_logic...")
    # Example URL, replace with actual test URL if needed
    test_onshape_url = "https://cad.onshape.com/documents/34194a7792ea9db6d10188d3/w/2603dadfb9d5ccf8117390d0/e/140112c65afa2d3dddb074ba"
    tool_output = _onshape_url_to_enriched_feature_summary_logic(test_onshape_url)
    
    if isinstance(tool_output, str): # If the tool returned an error string
        print(f"Error from _onshape_url_to_enriched_feature_summary_logic: {tool_output}")
        parsed_features_data = {}
        enriched_summaries_data = []
    elif isinstance(tool_output, dict):
        parsed_features_data = tool_output.get("feature_parser_output", {})
        enriched_summaries_data = tool_output.get("enriched_feature_summaries", [])
        if not parsed_features_data:
            print("Warning: 'feature_parser_output' missing or empty in tool output.")
        if not enriched_summaries_data:
            print("Warning: 'enriched_feature_summaries' missing or empty in tool output.")
    else:
        print(f"Unexpected output type from _onshape_url_to_enriched_feature_summary_logic: {type(tool_output)}")
        parsed_features_data = {}
        enriched_summaries_data = []

    print("\nRunning identify_ambigous_entities...")
    # Ensure identify_ambigous_entities is awaited as it's an async function
    result = asyncio.run(identify_ambigous_entities(parsed_features_data, enriched_summaries_data))
    print("\n--- Ambiguity Analysis Result ---")
    print(result)
    print(f"Type: {type(result)}")
    print(f"Length: {len(result) if isinstance(result, list) else 'N/A'}")