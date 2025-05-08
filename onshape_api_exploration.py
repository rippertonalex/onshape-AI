import requests
import json
import os
from dotenv import load_dotenv
from agents import function_tool # Assuming this is the correct import
from datetime import datetime
from typing import Union, List
from app.utils.onshape_tools import (
    get_onshape_feature_list, 
    feature_parser, 
    extract_feature_summaries, 
    enrich_feature_summaries, 
    ParsedFeaturesData,
    FeatureSummary
)
from onshape_client.onshape_url import OnshapeElement



# Load environment variables from .env file
load_dotenv()

ONSHAPE_API_BASE_URL = "https://cad.onshape.com/api"
base_urls = {
    'features': '/api/partstudios/d/did/w/wid/e/eid/features', #TODO figure out query for specific feature ID
    'documents': '/api/documents',
    'elements': '/api/documents/d/did/w/wid/elements',
    'featurescriptrep': '/api/partstudios/d/did/w/wid/e/eid/featurescriptrepresentation', #TODO: fix this
    'featurescript': '/api/partstudios/d/did/w/wid/e/eid/featurescript',
    'featurespecs': '/api/partstudios/d/did/w/wid/e/eid/featurespecs',
    'edges': '/api/partstudios/d/did/w/wid/e/eid/tessellatededges',
    'faces': '/api/partstudios/d/did/w/wid/e/eid/tessellatedfaces',
    'sketches': '/api/partstudios/d/did/w/wid/e/eid/sketches',
    'sketchtesselated': '/api/partstudios/d/did/w/wid/e/eid/sketches/sid/tessellatedentities', #TODO test with sketch id
    'parts': '/api/parts/d/did/w/wid/e/eid',
    'bodydetails': '/api/parts/d/did/w/wid/e/eid/partid/pid/bodydetails', #TODO test with part id
    'partedges': '/api/parts/d/did/w/wid/e/eid/partid/pid/tessellatededges',
    'partfaces': '/api/parts/d/did/w/wid/e/eid/partid/pid/tessellatedfaces',
    'assemblies': '/api/assemblies/d/did/w/wid/e/eid',
    'assemblyfeatures': '/api/assemblies/d/did/w/wid/e/eid/features',
    'assemblyfeaturespecs': '/api/assemblies/d/did/w/wid/e/eid/featurespecs',
}
base='https://cad.onshape.com'

@function_tool
def get_onshape_document_details(document_id: str) -> str:
    """
    Fetches details for a specific Onshape document using its ID.

    Args:
        document_id: The unique identifier of the Onshape document.

    Returns:
        A string containing the JSON details of the document if successful,
        or an error message if the request fails or keys are missing.
    """
    api_url = f"{ONSHAPE_API_BASE_URL}/documents/{document_id}"

    access_key = os.getenv("ACCESS_KEY")
    secret_key = os.getenv("SECRET_KEY")

    if not access_key or not secret_key:
        return "Error: Onshape ACCESS_KEY or SECRET_KEY not found in environment variables."

    headers = {
        'Accept': 'application/vnd.onshape.v1+json;charset=UTF-8;qs=0.1',
        'Content-Type': 'application/json'
    }

    try:
        response = requests.get(
            api_url,
            auth=(access_key, secret_key),
            headers=headers,
            timeout=15 # Slightly longer timeout
        )

        if response.ok:
            try:
                response_json = response.json()
                # Return formatted JSON string for the agent to use
                return json.dumps(response_json, indent=2)
            except json.JSONDecodeError:
                return f"Error: Successfully fetched from {api_url} but failed to decode JSON response. Status: {response.status_code}. Response text: {response.text}"
        else:
            return f"Error: Failed to fetch from {api_url}. Status: {response.status_code}. Response text: {response.text}"

    except requests.exceptions.Timeout:
        return f"Error: Request timed out while trying to reach {api_url}."
    except requests.exceptions.RequestException as e:
        return f"Error: An network error occurred while requesting {api_url}: {e}"
    except Exception as e:
        return f"Error: An unexpected error occurred: {e}"

def standard_api_request(url: str,
                        base_url: str,
                        method: str= 'GET',
                        extra_arguments: dict = None,
                        params: dict = None,
                        payload: dict = None,
                        pid: str = None,
                        sid: str = None,
                        download: bool = False,
                        tag: str = None):
    element = OnshapeElement(url)
    base_url = base_url.replace('did', element.did)
    base_url = base_url.replace('wid', element.wvmid)
    base_url = base_url.replace('eid', element.eid)
    if pid:
      base_url = base_url.replace('pid', pid)
    if sid:
      base_url = base_url.replace('sid', sid)

    if params is None:
      params = {}
    if payload is None:
      payload = {}
    headers = {'Accept': 'application/vnd.onshape.v1+json; charset=UTF-8;qs=0.1',
              'Content-Type': 'application/json'}
    if extra_arguments is not None:
      base_url += '?'
      for key in extra_arguments.keys():
        base_url += f"{key}={extra_arguments[key]}&"
      base_url = base_url[:-1]

    api_url = base+base_url
    # print(api_url)

    if method == 'GET':
      response = requests.get(
            api_url,
            auth=(os.getenv("ACCESS_KEY"), os.getenv("SECRET_KEY")),
            headers=headers,
            timeout=20
        )
    elif method == 'POST':
      response = requests.post(
            api_url,
            auth=(os.getenv("ACCESS_KEY"), os.getenv("SECRET_KEY")),
            headers=headers,
            json=payload,
            timeout=20
        )
    response = response.json()
    return response

def get_onshape_features(url: str):
    """
    Helper function to fetch features from an Onshape Part Studio URL using standard_api_request.
    Prints and returns the response.
    """
    # Example usage for local dev and prod:
    # url = r'https://cad.onshape.com/documents/34194a7792ea9db6d10188d3/w/2603dadfb9d5ccf8117390d0/e/ed0327add99ecf3427274439'
    # response = standard_api_request(url, base_urls['features'], method='GET')
    # print(response)
    try:
        response = standard_api_request(url, base_urls['features'], method='GET')
        print(response)
        return response
    except Exception as e:
        print(f"Error in get_onshape_features: {e}")
        return f"Error: {e}"

def onshape_url_to_enriched_feature_summary(url: str) -> Union[dict, str]:
    """
    Takes an Onshape Part Studio URL, fetches its features, parses them,
    extracts summaries, and enriches them. This is a high-level function
    that chains several tools together to perform the standard geometry
    interpretation workflow.

    Parameters:
    - url (str): The full URL of the Onshape Part Studio.

    Returns:
    - dict: A dictionary containing the outputs of each step, including
      the outputs from feature_parser and extract_feature_summaries, as well as the final enriched summaries.
      If any step fails, returns an error message string.
      Also includes character counts for each output.
    """
    function_chain_errors = [] # To collect errors if we want to return all

    # Step 1: Get feature list using the new helper
    print(f"[{datetime.now()}] ChainedOp: Calling get_onshape_features for {url}")
    feature_list_result = get_onshape_features(url) # Result is dict or error string
    
    # Check if the output of get_onshape_features is an error string
    if isinstance(feature_list_result, str) and feature_list_result.startswith("Error:"):
        error_message = f"Step 1 (get_onshape_features) failed: {feature_list_result}"
        print(f"[{datetime.now()}] ChainedOp: {error_message}")
        return error_message # Fail fast
    
    # Check if it's a dictionary (expected success case)
    if not isinstance(feature_list_result, dict):
        error_message = f"Step 1 (get_onshape_features) failed: Expected dict result, but got {type(feature_list_result).__name__}. Preview: {str(feature_list_result)[:250]}"
        print(f"[{datetime.now()}] ChainedOp: {error_message}")
        return error_message

    feature_list_dict = feature_list_result # Rename for clarity
    print(f"[{datetime.now()}] ChainedOp: get_onshape_features completed. Received dictionary.")
    # Optionally print length/keys for debugging large dicts
    # print(f"[{datetime.now()}] ChainedOp: Feature list dict keys: {list(feature_list_dict.keys())}") 

    # Step 2: Parse features
    parsed_features: ParsedFeaturesData
    try:
        print(f"[{datetime.now()}] ChainedOp: Calling feature_parser with dictionary.")
        # Pass the dictionary directly to the modified feature_parser
        parsed_features_result = feature_parser(response_data=feature_list_dict) 
        
        # Print the output of feature_parser
        print("\n--- Feature Parser Output ---")
        try:
            print(json.dumps(parsed_features_result, indent=2))
        except TypeError as e:
            print(f"Could not JSON serialize feature_parser output: {e}")
            print(str(parsed_features_result))
        print("--- End Feature Parser Output ---\n")

        if isinstance(parsed_features_result, dict) and parsed_features_result.get("error"):
            error_message = f"Step 2 (feature_parser) failed: {parsed_features_result.get('error')}"
            print(f"[{datetime.now()}] ChainedOp: {error_message}")
            return error_message
        
        if not (isinstance(parsed_features_result, dict) and 'features' in parsed_features_result):
             error_message = f"Step 2 (feature_parser) failed: Output is not ParsedFeaturesData. Got: {str(parsed_features_result)[:250]}"
             print(f"[{datetime.now()}] ChainedOp: {error_message}")
             return error_message
        parsed_features = parsed_features_result

    except json.JSONDecodeError as e:
        error_message = f"Step 2 (feature_parser) failed: JSONDecodeError - {e}. Input preview: {feature_list_dict[:250]}"
        print(f"[{datetime.now()}] ChainedOp: {error_message}")
        return error_message
    except Exception as e:
        error_message = f"Step 2 (feature_parser) failed with unexpected error: {type(e).__name__} - {e}"
        print(f"[{datetime.now()}] ChainedOp: {error_message}")
        import traceback
        traceback.print_exc()
        return error_message
    
    print(f"[{datetime.now()}] ChainedOp: feature_parser completed. Number of parsed features: {len(parsed_features.get('features', []))}")

    # Step 3: Extract feature summaries
    summaries: List[FeatureSummary]
    try:
        print(f"[{datetime.now()}] ChainedOp: Calling extract_feature_summaries.")
        summaries = extract_feature_summaries(parsed_features=parsed_features)
        
        # Print the output of extract_feature_summaries
        print("\n--- Extract Feature Summaries Output ---")
        try:
             print(json.dumps(summaries, indent=2))
        except TypeError as e:
             print(f"Could not JSON serialize extract_feature_summaries output: {e}")
             print(str(summaries))
        print("--- End Extract Feature Summaries Output ---\n")

        if not isinstance(summaries, list):
            error_message = f"Step 3 (extract_feature_summaries) failed: Did not return a list. Got: {type(summaries)}"
            print(f"[{datetime.now()}] ChainedOp: {error_message}")
            if isinstance(summaries, str):
                return f"{error_message} Content: {summaries[:250]}"
            return error_message
    except Exception as e:
        error_message = f"Step 3 (extract_feature_summaries) failed with unexpected error: {type(e).__name__} - {e}"
        print(f"[{datetime.now()}] ChainedOp: {error_message}")
        import traceback
        traceback.print_exc()
        return error_message

    print(f"[{datetime.now()}] ChainedOp: extract_feature_summaries completed. Number of summaries: {len(summaries)}")

    # Step 4: Enrich feature summaries
    enriched_summaries: List[FeatureSummary]
    try:
        print(f"[{datetime.now()}] ChainedOp: Calling enrich_feature_summaries.")
        enriched_summaries = enrich_feature_summaries(feature_summaries=summaries, url=url)
        if not isinstance(enriched_summaries, list):
            error_message = f"Step 4 (enrich_feature_summaries) failed: Did not return a list. Got: {type(enriched_summaries)}"
            print(f"[{datetime.now()}] ChainedOp: {error_message}")
            if isinstance(enriched_summaries, str):
                 return f"{error_message} Content: {enriched_summaries[:250]}"
            return error_message
            
    except Exception as e:
        error_message = f"Step 4 (enrich_feature_summaries) failed with unexpected error: {type(e).__name__} - {e}"
        print(f"[{datetime.now()}] ChainedOp: {error_message}")
        import traceback
        traceback.print_exc()
        return error_message

    print(f"[{datetime.now()}] ChainedOp: enrich_feature_summaries completed. Number of enriched summaries: {len(enriched_summaries)}")
    print(f"[{datetime.now()}] ChainedOp: Successfully completed onshape_url_to_enriched_feature_summary for {url}")

    # Compute character counts for each output
    def get_char_count(obj):
        try:
            return len(json.dumps(obj))
        except Exception:
            try:
                return len(str(obj))
            except Exception:
                return None

    feature_list_dict_count = len(json.dumps(feature_list_dict))
    feature_parser_output_count = get_char_count(parsed_features)
    extract_feature_summaries_output_count = get_char_count(summaries)
    enriched_feature_summaries_count = get_char_count(enriched_summaries)

    # Return all outputs in a dictionary for inspection, including char counts

    return {
        "feature_list_dict": feature_list_dict,
        "feature_parser_output": parsed_features,
        "extract_feature_summaries_output": summaries,
        "enriched_feature_summaries": enriched_summaries,
        "enriched_feature_summaries_char_count": enriched_feature_summaries_count,
        "feature_list_dict_char_count": feature_list_dict_count,
        "feature_parser_output_char_count": feature_parser_output_count,
        "extract_feature_summaries_output_char_count": extract_feature_summaries_output_count,
    }

# Call the function and print its output as formatted JSON
result = onshape_url_to_enriched_feature_summary("https://cad.onshape.com/documents/34194a7792ea9db6d10188d3/w/2603dadfb9d5ccf8117390d0/e/ed0327add99ecf3427274439")
print("\n--- onshape_url_to_enriched_feature_summary Outputs ---")
if isinstance(result, str): # Handle error strings
    print(result)
else: # Print all outputs as JSON
    print(json.dumps(result, indent=2))

