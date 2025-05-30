import sys
import os
import json
from openai import AsyncOpenAI
from dotenv import load_dotenv
import asyncio
from typing import Union, List, Dict, Any

# Calculate the project root directory based on the current script's location
# This script is in app/utils/pre-processing, so we need to go up three levels
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Also add the current directory to sys.path for local imports
current_dir = os.path.dirname(__file__)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Load environment variables (assuming .env is in project_root)
load_dotenv(os.path.join(project_root, '.env'))

# Now import from app modules after sys.path is set up
from app.utils.queries import standard_api_request, endpoints
from app.utils.parsing import feature_parser, extract_feature_summaries, enrich_feature_summaries

# Make these top-level imports for the whole script if they are needed outside __main__ too
from app.utils.onshape_tools import _onshape_url_to_enriched_feature_summary_logic
# Import from the same directory
from identify_ambigous_entities import identify_ambigous_entities

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# Define a model for this specific task.
# Users can set OPENAI_MODEL_FOR_TEST_POINTS in their .env file.
OPENAI_MODEL_FOR_TEST_POINTS = os.getenv("OPENAI_MODEL_FOR_TEST_POINTS", "o3") # Default to a capable and cost-effective model

if not OPENAI_API_KEY:
    print("CRITICAL: OPENAI_API_KEY is not set in environment variables. Test point generation will fail.")
if not OPENAI_MODEL_FOR_TEST_POINTS: 
    print("CRITICAL: OPENAI_MODEL_FOR_TEST_POINTS is not set. Test point generation will fail.")


async def generate_sketch_test_points(
    parsed_features: Dict[str, Any],
    ambiguous_entities: List[str]
) -> Dict[str, Any]:
    """
    Generates test points for sketch profiles using an LLM.

    The function takes parsed feature data from Onshape and a list of ambiguous
    entities. It then uses an OpenAI model to identify enclosed profiles within
    each sketch and suggest test points (in meters) for each profile, returning
    a structured dictionary.

    Args:
        parsed_features (Dict[str, Any]): The parsed feature data, typically
                                          from `feature_parser` (e.g.,
                                          `tool_output.get("feature_parser_output")`).
        ambiguous_entities (List[str]): A list of ambiguous entity IDs from the
                                       `identify_ambigous_entities` function.

    Returns:
        Dict[str, Any]: A dictionary with 'sketch_id' and 'test_points' keys.
                       The 'sketch_id' is a string and 'test_points' is a list
                       of [x, y] coordinate pairs in meters. Returns an error
                       dictionary with 'error' key if the process fails.
    """

    if not OPENAI_API_KEY:
        return {"error": "OPENAI_API_KEY is not configured."}

    system_prompt = (
        "You are an expert assistant specializing in Onshape CAD geometry. "
        "Your task is to identify enclosed profiles within Onshape sketches and provide test points for each profile. "
        "You will be given 'Parsed Features Data' which includes details of sketches and their geometric entities, "
        "and 'Ambiguous Entities' for additional context.\n\n"
        "Instructions:\n"
        "1. Analyze features of type 'Sketch' from the 'Parsed Features Data'. The sketch ID is the 'id' field of the sketch feature.\n"
        "2. For each sketch:\n"
        "   a. Identify all unique enclosed profiles. An enclosed profile is a closed loop of sketch entities.\n"
        "      - Consider inner loops (e.g., the area between a circle inside a rectangle).\n"
        "      - Consider segmented profiles (e.g., a rectangle divided by a line, creating two smaller rectangular profiles).\n"
        "   b. For each profile, determine a test point (x, y) that lies strictly within that profile. The coordinates must be in meters.\n"
        "3. Your response must be ONLY a JSON object in the following format:\n"
        "   {\n"
        "     \"sketch_id\": \"[sketch_id_from_data]\",\n"
        "     \"test_points\": [[x1, y1], [x2, y2], [x3, y3], ...]\n"
        "   }\n"
        "4. If multiple sketches are found, return the result for the first sketch only.\n"
        "5. If no enclosed profiles are found, return an empty test_points array.\n"
        "6. Ensure coordinates are in meters as floating point numbers.\n"
        "7. Do not include any other text, explanations, or formatting. Only return the JSON object."
    )

    try:
        user_prompt_content = (
            f"Parsed Features Data:\n{json.dumps(parsed_features, indent=2)}\n\n"
            f"Ambiguous Entities: {json.dumps(ambiguous_entities)}\n\n"
            "Please generate the sketch test points as a JSON object according to the system prompt instructions."
        )
    except Exception as e: 
        error_message = f"Error serializing data for OpenAI prompt: {type(e).__name__} - {e}"
        print(error_message)
        return {"error": error_message}

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt_content}
    ]

    response_content_str = "" # Initialize to ensure it's defined for error reporting
    try:
        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        completion = await client.chat.completions.create(
            model=OPENAI_MODEL_FOR_TEST_POINTS,
            messages=messages
        )
        
        response_content_str = completion.choices[0].message.content
        if response_content_str is None:
            return {"error": "OpenAI API returned null content."}
        
        # Parse the JSON response
        try:
            # Clean the response to extract just the JSON object
            response_content_str = response_content_str.strip()
            result = json.loads(response_content_str)
            
            # Validate the structure
            if not isinstance(result, dict):
                return {"error": f"Expected JSON object, got {type(result)}"}
            
            if "sketch_id" not in result or "test_points" not in result:
                return {"error": "Missing required keys 'sketch_id' or 'test_points' in response"}
            
            if not isinstance(result["sketch_id"], str):
                return {"error": f"Expected string for sketch_id, got {type(result['sketch_id'])}"}
            
            if not isinstance(result["test_points"], list):
                return {"error": f"Expected list for test_points, got {type(result['test_points'])}"}
            
            # Validate test points format
            for i, point in enumerate(result["test_points"]):
                if not isinstance(point, list) or len(point) != 2:
                    return {"error": f"Test point {i} should be a list of 2 coordinates, got {point}"}
                if not all(isinstance(coord, (int, float)) for coord in point):
                    return {"error": f"Test point {i} coordinates should be numbers, got {point}"}
            
            return result
            
        except json.JSONDecodeError as je:
            return {"error": f"Error parsing JSON response: {je}. Raw response: {response_content_str}"}

    except NameError as ne:
        error_message = f"Configuration or Import Error: {ne}. Ensure AsyncOpenAI is imported and API keys/models are set."
        print(error_message)
        return {"error": error_message}
    except Exception as e:
        error_message = f"Error during OpenAI API call or processing: {type(e).__name__} - {e}. Raw response if available: {response_content_str}"
        print(error_message)
        return {"error": error_message}

if __name__ == "__main__":
    # Imports are now at the top level, so no try-except needed here for them
    # However, we should still check if they were successfully imported in case of issues
    # For simplicity in this step, we assume they import correctly if sys.path is set up.
    # The previous more robust check for None can be reinstated if needed.

    async def main_test():
        # Check if functions are available (they should be due to top-level imports)
      

        test_onshape_url = "https://cad.onshape.com/documents/34194a7792ea9db6d10188d3/w/2603dadfb9d5ccf8117390d0/e/140112c65afa2d3dddb074ba"
        if not test_onshape_url:
            print("Skipping __main__ test: TEST_ONSHAPE_URL environment variable not set.")
            print("Please set TEST_ONSHAPE_URL to a valid Onshape document URL with sketches for testing.")
            return

        current_time = lambda: asyncio.get_event_loop().time()
        print(f"[{current_time():.2f}] Running test with Onshape URL: {test_onshape_url}")
        
      
        test_onshape_url = "https://cad.onshape.com/documents/34194a7792ea9db6d10188d3/w/2603dadfb9d5ccf8117390d0/e/140112c65afa2d3dddb074ba"
        test_onshape_url_2 = "https://cad.onshape.com/documents/34194a7792ea9db6d10188d3/w/2603dadfb9d5ccf8117390d0/e/ed0327add99ecf3427274439"
        test_onshape_url_3 = "https://cad.onshape.com/documents/34194a7792ea9db6d10188d3/w/2603dadfb9d5ccf8117390d0/e/8e8fe9de5851db99112d3500"
    
        params = {'rollbackBarIndex': -1, 'noSketchGeometry': 'false'}

    # # Step 1: Get and parse features
        response = standard_api_request(
            test_onshape_url_2,
            endpoints['features'],
            method='GET',
            params=params
        )
        new_parsed_features_data = feature_parser(response)

        #tool_output = _onshape_url_to_enriched_feature_summary_logic(test_onshape_url)

        #old_parsed_features_data = tool_output.get("feature_parser_output", [])
        
        print(f"[{current_time():.2f}] Calling identify_ambigous_entities...")
        ambiguous_entities_list_1 = ["IB", "JDC", "JGO", "JHK", "KIlC"]

        print(f"\n[{current_time():.2f}] Calling generate_sketch_test_points...")
        test_points_result = await generate_sketch_test_points(new_parsed_features_data, ambiguous_entities_list_1)

        print("\n--- Sketch Test Points Generation Result ---")
        if isinstance(test_points_result, dict):
            if "error" in test_points_result:
                print(f"Error generating test points: {test_points_result['error']}")
            else:
                # Successful structured output
                print("Successfully generated test points:")
                print(f"Sketch ID: {test_points_result.get('sketch_id')}")
                print(f"Test Points: {test_points_result.get('test_points')}")
                print(f"Number of test points: {len(test_points_result.get('test_points', []))}")
        else:
            # This case should ideally not be reached if the function behaves as expected
            print(f"Unexpected result type from generate_sketch_test_points: {type(test_points_result)}")
            print("Result content:")
            print(test_points_result)
        
        print(f"[{current_time():.2f}] Test finished.")

    if OPENAI_API_KEY:
        asyncio.run(main_test())
    else:
        print("Skipping __main__ test execution: OPENAI_API_KEY is not set.")
