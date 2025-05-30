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

# Import from the same directory
from define_ambiguous_entities import define_ambiguous_entities_wrapper

from app.utils.queries import standard_api_request, endpoints, query_sketch_profiles_contains
from app.utils.parsing import feature_parser, extract_feature_summaries, enrich_feature_summaries

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# Define a model for this specific task.
# Users can set OPENAI_MODEL_FOR_VISUALIZATION in their .env file.
OPENAI_MODEL_FOR_VISUALIZATION = os.getenv("OPENAI_MODEL_FOR_VISUALIZATION", "gpt-4o")  # Default to a capable model

if not OPENAI_API_KEY:
    print("CRITICAL: OPENAI_API_KEY is not set in environment variables. Geometry visualization will fail.")
if not OPENAI_MODEL_FOR_VISUALIZATION: 
    print("CRITICAL: OPENAI_MODEL_FOR_VISUALIZATION is not set. Geometry visualization will fail.")


async def visualize_workspace_geometry(
    enriched_feature_summary: List[Dict[str, Any]],
    parsed_feature_output: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generates a detailed description of the workspace geometry using an LLM.

    The function takes enriched feature summary data (including ambiguous entity definitions)
    and parsed feature output from Onshape, then uses an OpenAI model to provide a step-by-step
    description of the resulting geometry in the workspace.

    Args:
        enriched_feature_summary (List[Dict[str, Any]]): The enriched feature summary containing
            entity information and definitions from the define_ambiguous_entities step.
        parsed_feature_output (Dict[str, Any]): The parsed feature output from the
            _onshape_url_to_enriched_feature_summary_logic function.

    Returns:
        Dict[str, Any]: A dictionary containing:
            - 'geometry_description' (str): Detailed step-by-step description of the workspace geometry
            - 'success' (bool): Whether the visualization was successful
            - 'error' (str, optional): Error message if visualization failed
    """
    try:
        # Initialize OpenAI client
        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        
        # Prepare the data for the prompt
        data_summary = {
            "enriched_feature_summary": enriched_feature_summary,
            "parsed_feature_output": parsed_feature_output
        }
        
        # Create the prompt
        prompt = f"""
You are an expert CAD analyst. I will provide you with detailed feature data from an Onshape workspace.

Data Inputs:
1. Enriched Feature Summary: Contains feature information including entity definitions and geometry data
2. Parsed Feature Output: Contains the raw parsed feature data from the workspace

Your task is to describe step by step in precise details what the resulting geometry in the workspace is. For each feature, describe the result in the end, taking note of how it references previous features. Keep a detailed description of the geometry in mind.

Please provide:
1. A sequential walkthrough of each feature and its geometric result
2. How each feature builds upon or references previous features
3. The final overall geometry of the workspace
4. Any notable geometric relationships or constraints

Here is the data:

{json.dumps(data_summary, indent=2)}

Please provide a comprehensive, step-by-step analysis of the workspace geometry.
"""

        # Make the API call
        response = await client.chat.completions.create(
            model=OPENAI_MODEL_FOR_VISUALIZATION,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert CAD analyst specializing in geometric analysis and feature interpretation. Provide detailed, technical descriptions of CAD geometry."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.1,  # Low temperature for consistent, factual output
            max_tokens=4000   # Allow for detailed descriptions
        )
        
        geometry_description = response.choices[0].message.content
        
        return {
            "geometry_description": geometry_description,
            "success": True
        }
        
    except Exception as e:
        error_message = f"Error in visualize_workspace_geometry: {str(e)}"
        print(error_message)
        return {
            "geometry_description": "",
            "success": False,
            "error": error_message
        }


def visualize_workspace_geometry_sync(
    enriched_feature_summary: List[Dict[str, Any]],
    parsed_feature_output: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Synchronous wrapper for the async visualize_workspace_geometry function.
    
    Args:
        enriched_feature_summary (List[Dict[str, Any]]): The enriched feature summary
        parsed_feature_output (Dict[str, Any]): The parsed feature output
    
    Returns:
        Dict[str, Any]: Result from visualize_workspace_geometry
    """
    return asyncio.run(visualize_workspace_geometry(enriched_feature_summary, parsed_feature_output))


if __name__ == "__main__":
    # Example usage for testing
    # For local dev:
    # url = "https://cad.onshape.com/documents/34194a7792ea9db6d10188d3/w/2603dadfb9d5ccf8117390d0/e/ed0327add99ecf3427274439"
    # For prod:
    # url = "https://cad.onshape.com/documents/your_doc_id/w/your_workspace_id/e/your_element_id"
    
    test_onshape_url = "https://cad.onshape.com/documents/34194a7792ea9db6d10188d3/w/2603dadfb9d5ccf8117390d0/e/140112c65afa2d3dddb074ba"
    test_onshape_url_2 = "https://cad.onshape.com/documents/34194a7792ea9db6d10188d3/w/2603dadfb9d5ccf8117390d0/e/ed0327add99ecf3427274439"
    test_onshape_url_3 = "https://cad.onshape.com/documents/34194a7792ea9db6d10188d3/w/2603dadfb9d5ccf8117390d0/e/8e8fe9de5851db99112d3500"
    
    params = {'rollbackBarIndex': -1, 'noSketchGeometry': 'false'}

    # # Step 1: Get and parse features
    response = standard_api_request(
            test_onshape_url,
            endpoints['features'],
            method='GET',
            params=params
        )
    new_parsed_features_data = feature_parser(response)
    new_feature_summaries = extract_feature_summaries(new_parsed_features_data)
    new_enriched_summaries_data = enrich_feature_summaries(new_feature_summaries, test_onshape_url)
    
    

    # Example ambiguous entity IDs (this would normally come from identify_ambiguous_entities)
    ambiguous_entity_ids = ['IB', 'JDC', 'JGO', 'JHK', 'KIlC']
    
    # Define ambiguous entities
    enriched_with_definitions = define_ambiguous_entities_wrapper(test_onshape_url, new_enriched_summaries_data, ambiguous_entity_ids)
    
    # Visualize the geometry
    print("Generating geometry visualization...")
    result = visualize_workspace_geometry_sync(enriched_with_definitions, new_parsed_features_data)
    
    if result["success"]:
        print("Geometry Visualization Result:")
        print("=" * 80)
        print(result["geometry_description"])
        print("=" * 80)
    else:
        print(f"Visualization failed: {result.get('error', 'Unknown error')}")
