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

# Load environment variables (assuming .env is in project_root)
load_dotenv(os.path.join(project_root, '.env'))

# Make these top-level imports for the whole script if they are needed outside __main__ too
# If not, they can stay in the try-except block within __main__
from app.utils.onshape_tools import _onshape_url_to_enriched_feature_summary_logic
# Use absolute import because sys.path is modified to include project root
from .identify_ambigous_entities import identify_ambigous_entities

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
    ambiguous_entities_output: str
) -> str:
    """
    Generates test points for sketch profiles using an LLM.

    The function takes parsed feature data from Onshape and the output of an
    ambiguity analysis (which provides context on entities). It then uses an
    OpenAI model to identify enclosed profiles within each sketch and suggest
    a test point (in meters) for each profile, returning a human-readable
    text description.

    Args:
        parsed_features (Dict[str, Any]): The parsed feature data, typically
                                          from `feature_parser` (e.g.,
                                          `tool_output.get("feature_parser_output")`).
        ambiguous_entities_output (str): The string output from the
                                         `identify_ambigous_entities` function.

    Returns:
        str: A human-readable string describing the identified enclosed profiles
             and their test points for each sketch, or an error message string
             if the process fails (e.g., API key issue, API call error).
             The error message will typically start with "Error:".
    """

    if not OPENAI_API_KEY:
        return "Error: OPENAI_API_KEY is not configured."

    system_prompt = (
        "You are an expert assistant specializing in Onshape CAD geometry. "
        "Your task is to identify enclosed profiles within Onshape sketches and provide a test point for each profile. "
        "You will be given 'Parsed Features Data' which includes details of sketches and their geometric entities, "
        "and 'Ambiguous Entities Output' for additional context.\n\n"
        "Instructions:\n"
        "1. Analyze features of type 'Sketch' from the 'Parsed Features Data'. The sketch ID is the 'id' field of the sketch feature.\n"
        "2. For each sketch:\n"
        "   a. Identify all unique enclosed profiles. An enclosed profile is a closed loop of sketch entities.\n"
        "      - Consider inner loops (e.g., the area between a circle inside a rectangle).\n"
        "      - Consider segmented profiles (e.g., a rectangle divided by a line, creating two smaller rectangular profiles).\n"
        "   b. If a sketch contains identifiable enclosed profiles, begin your description for that sketch with:\n"
        "      \"Within Sketch [Sketch_ID_from_data], the following enclosed profiles can be identified:\"\n"
        "      Then, for each profile within that sketch:\n"
        "        - Provide a brief, descriptive name for the profile (e.g., \"Main outer boundary\", \"Circular cutout\", \"Left segment of divided rectangle\"). If relevant, you can mention entity IDs that form or are related to the profile.\n"
        "        - Clearly state one test point (x, y) that lies strictly within that profile. The coordinates must be in meters. Use the format: \"A point within this profile is (x.xxx, y.yyy) meters.\"\n"
        "   c. If a sketch has no identifiable enclosed profiles, state:\n"
        "      \"Sketch [Sketch_ID_from_data] has no identifiable enclosed profiles.\"\n"
        "3. Your entire response should be a single block of human-readable text, describing the profiles and test points for all relevant sketches.\n"
        "4. Do not use JSON or any other structured data format for your primary output. The output should be narrative.\n"
        "5. Ensure coordinates are in meters and formatted as (x_value, y_value), for example, (0.05, -0.123)."
    )

    try:
        user_prompt_content = (
            f"Parsed Features Data:\n{json.dumps(parsed_features, indent=2)}\n\n"
            f"Ambiguous Entities Output (for context):\n{ambiguous_entities_output}\n\n"
            "Please generate the sketch test points as a descriptive text according to the system prompt instructions."
        )
    except Exception as e: 
        error_message = f"Error serializing data for OpenAI prompt: {type(e).__name__} - {e}"
        print(error_message)
        return error_message

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
            # No response_format needed as we expect plain text
        )
        
        response_content_str = completion.choices[0].message.content
        if response_content_str is None:
            return "Error: OpenAI API returned null content."
        
        # The response is expected to be a string, so we return it directly.
        return response_content_str

    except NameError as ne:
        error_message = f"Configuration or Import Error: {ne}. Ensure AsyncOpenAI is imported and API keys/models are set."
        print(error_message)
        return error_message
    except Exception as e:
        error_message = f"Error during OpenAI API call or processing: {type(e).__name__} - {e}. Raw response if available: {response_content_str}"
        print(error_message)
        # import traceback # For more detailed debugging if needed
        # traceback.print_exc()
        return error_message

if __name__ == "__main__":
    # Imports are now at the top level, so no try-except needed here for them
    # However, we should still check if they were successfully imported in case of issues
    # For simplicity in this step, we assume they import correctly if sys.path is set up.
    # The previous more robust check for None can be reinstated if needed.

    async def main_test():
        # Check if functions are available (they should be due to top-level imports)
        if not callable(_onshape_url_to_enriched_feature_summary_logic) or not callable(identify_ambigous_entities):
            print("Skipping __main__ test due to missing function definitions.")
            return

        test_onshape_url = "https://cad.onshape.com/documents/34194a7792ea9db6d10188d3/w/2603dadfb9d5ccf8117390d0/e/140112c65afa2d3dddb074ba"
        if not test_onshape_url:
            print("Skipping __main__ test: TEST_ONSHAPE_URL environment variable not set.")
            print("Please set TEST_ONSHAPE_URL to a valid Onshape document URL with sketches for testing.")
            return

        current_time = lambda: asyncio.get_event_loop().time()
        print(f"[{current_time():.2f}] Running test with Onshape URL: {test_onshape_url}")
        
        print(f"[{current_time():.2f}] Calling _onshape_url_to_enriched_feature_summary_logic...")
        try:
            tool_output = await asyncio.to_thread(_onshape_url_to_enriched_feature_summary_logic, test_onshape_url)
        except Exception as e:
            print(f"Error calling _onshape_url_to_enriched_feature_summary_logic: {type(e).__name__} - {e}")
            return

        if isinstance(tool_output, str):
            print(f"Error from _onshape_url_to_enriched_feature_summary_logic: {tool_output}")
            return
        
        parsed_features_data = tool_output.get("feature_parser_output")
        enriched_summaries_data = tool_output.get("enriched_feature_summaries", []) # Default to empty list

        if not parsed_features_data:
            print("Error: 'feature_parser_output' missing from tool_output. Cannot proceed.")
            return
        
        if not tool_output.get("enriched_feature_summaries"): # Check original before defaulting
            print("Warning: 'enriched_feature_summaries' missing or empty in tool_output. Ambiguity analysis might be affected.")

        print(f"[{current_time():.2f}] Calling identify_ambigous_entities...")
        ambiguous_output_str = await identify_ambigous_entities(parsed_features_data, enriched_summaries_data)
        
        print(f"\n--- Ambiguity Analysis Result (first 500 chars of {len(str(ambiguous_output_str))} total) ---")
        print(str(ambiguous_output_str)[:500])
        if isinstance(ambiguous_output_str, str) and "Error:" in ambiguous_output_str[:20]:
            print(f"Warning: identify_ambigous_entities may have returned an error/warning: {ambiguous_output_str[:100]}...")

        print(f"\n[{current_time():.2f}] Calling generate_sketch_test_points...")
        test_points_result = await generate_sketch_test_points(parsed_features_data, str(ambiguous_output_str))

        print("\n--- Sketch Test Points Generation Result ---")
        if isinstance(test_points_result, str):
            # Check if it's an error message (which typically starts with "Error:")
            if test_points_result.startswith("Error:"):
                print(f"Error generating test points: {test_points_result}")
            else:
                # Successful descriptive text output
                print("Successfully generated test points description:")
                print(test_points_result)
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
