import os
import json
import re
import requests
from typing import Union, List, Dict, Any, Optional
from typing_extensions import TypedDict
from dotenv import load_dotenv
from agents import function_tool
from .api_requests import standard_api_request, endpoints
from .filter import apply_filters, FILTER_CONFIG
from .queries import query_get_created_entities, query_get_sketch_plane
from .geometry_extractors import extract_plane_vectors
from datetime import datetime
from onshape_client.onshape_url import OnshapeElement


# Load environment variables for API keys
load_dotenv()
ONSHAPE_API_BASE_URL = "https://cad.onshape.com/api/v10"
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



def _fetch_onshape_document_details_logic(document_id: str) -> str:
    """Internal logic to fetch Onshape document details."""
    api_url = f"{ONSHAPE_API_BASE_URL}/documents/{document_id}"
    access_key = os.getenv("ACCESS_KEY")
    secret_key = os.getenv("SECRET_KEY")
    if not access_key or not secret_key:
        return "Error: Onshape ACCESS_KEY or SECRET_KEY not found in environment variables. Cannot use tool."
    headers = {
        'Accept': 'application/vnd.onshape.v1+json;charset=UTF-8;qs=0.1',
        'Content-Type': 'application/json'
    }
    try:
        response = requests.get(api_url, auth=(access_key, secret_key), headers=headers, timeout=20)
        if response.ok:
            try:
                return json.dumps(response.json(), indent=2)
            except json.JSONDecodeError:
                return f"Error: Successfully fetched from {api_url} but failed to decode JSON response. Raw response preview: {response.text[:200]}"
        else:
            return f"Error: Failed to fetch from {api_url}. Status Code: {response.status_code}. Response Text: {response.text[:200]}"
    except requests.exceptions.Timeout:
        return f"Error: Request timed out after 20 seconds while trying to reach {api_url}."
    except requests.exceptions.RequestException as e:
        return f"Error: A network communication error occurred while requesting {api_url}: {e}"
    except Exception as e:
        return f"Error: An unexpected error occurred: {e}"


@function_tool
def get_onshape_document_details(document_id: str) -> str:
    """
    Fetches details for a specific Onshape document using its ID from the Onshape API.
    """
    return _fetch_onshape_document_details_logic(document_id)


def _parse_onshape_url(url: str) -> Union[dict, None]:
    """Parses a standard Onshape Part Studio URL to extract document, workspace, and element IDs."""
    match = re.search(r"/documents/([a-zA-Z0-9]+)/([wvm])/([a-zA-Z0-9]+)/e/([a-zA-Z0-9]+)", url)
    if not match:
        return None
    did, wv_type, wv_id, eid = match.groups()
    if wv_type != 'w':
        return None
    return {"did": did, "wid": wv_id, "eid": eid}


def _get_onshape_feature_list_logic(part_studio_url: str) -> str:
    """Internal logic to fetch the feature list for an Onshape Part Studio."""
    parsed = _parse_onshape_url(part_studio_url)
    if not parsed:
        return f"Error: Could not parse IDs from URL: {part_studio_url}"
    api_url = f"{ONSHAPE_API_BASE_URL}/partstudios/d/{parsed['did']}/w/{parsed['wid']}/e/{parsed['eid']}/features"
    access_key = os.getenv("ACCESS_KEY")
    secret_key = os.getenv("SECRET_KEY")
    if not access_key or not secret_key:
        return "Error: Onshape ACCESS_KEY or SECRET_KEY not found."
    headers = {
        'Accept': 'application/json;charset=UTF-8; qs=0.09',
        'Content-Type': 'application/json'
    }
    try:
        response = requests.get(api_url, auth=(access_key, secret_key), headers=headers, timeout=20)
        if response.ok:
            try:
                return json.dumps(response.json(), indent=2)
            except json.JSONDecodeError as e:
                return f"Error: Failed to decode JSON response: {e}. Raw: {response.text[:200]}"
        else:
            return f"Error: Failed to get feature list. Status Code: {response.status_code}. Response: {response.text[:200]}"
    except requests.exceptions.RequestException as e:
        return f"Error: A network communication error occurred: {e}"


@function_tool
def get_onshape_feature_list(part_studio_url: str) -> str:
    """
    Fetches the list of features for a specified Onshape Part Studio.
    """
    return _get_onshape_feature_list_logic(part_studio_url)


def _get_onshape_featurescript_representation_logic(part_studio_url: str) -> str:
    """Internal logic to fetch the FeatureScript representation for an Onshape Part Studio."""
    parsed = _parse_onshape_url(part_studio_url)
    if not parsed:
        return f"Error: Could not parse IDs from URL: {part_studio_url}"
    api_url = f"{ONSHAPE_API_BASE_URL}/partstudios/d/{parsed['did']}/w/{parsed['wid']}/e/{parsed['eid']}/featurescriptrepresentation"
    access_key = os.getenv("ACCESS_KEY")
    secret_key = os.getenv("SECRET_KEY")
    if not access_key or not secret_key:
        return "Error: Onshape ACCESS_KEY or SECRET_KEY not found."
    headers = {
        'Accept': 'application/vnd.onshape.v1+json; charset=UTF-8;qs=0.1',
        'Content-Type': 'application/json'
    }
    try:
        response = requests.get(api_url, auth=(access_key, secret_key), headers=headers, timeout=20)
        if response.ok:
            text = response.text
            try:
                return json.dumps(json.loads(text), indent=2)
            except json.JSONDecodeError:
                return text
        else:
            return f"Error: Failed to get FeatureScript representation. Status Code: {response.status_code}. Response: {response.text[:200]}"
    except requests.exceptions.Timeout:
        return f"Error: Request timed out while trying to reach {api_url}."
    except requests.exceptions.RequestException as e:
        return f"Error: A network communication error occurred: {e}"


@function_tool
def get_onshape_featurescript_representation(part_studio_url: str) -> str:
    """
    Fetches the FeatureScript representation for a specified Onshape Part Studio.
    """
    return _get_onshape_featurescript_representation_logic(part_studio_url)


def _create_onshape_cube_logic(part_studio_url: str, name: str, side_length_expression: str) -> str:
    """Internal logic to create a simple cube feature using the dedicated 'cube' featureType."""
    parsed = _parse_onshape_url(part_studio_url)
    if not parsed:
        return f"Error: Could not parse IDs from URL: {part_studio_url}"
    api_url = f"{ONSHAPE_API_BASE_URL}/partstudios/d/{parsed['did']}/w/{parsed['wid']}/e/{parsed['eid']}/features"
    feature_payload = {
        "btType": "BTFeatureDefinitionCall-1406",
        "feature": {
            "btType": "BTMFeature-134",
            "featureType": "cube",
            "name": name,
            "parameters": [
                {"btType": "BTMParameterQuantity-147", "isInteger": False, "expression": side_length_expression, "parameterId": "sideLength"}
            ],
            "returnAfterSubfeatures": False,
            "suppressed": False
        }
    }
    access_key = os.getenv("ACCESS_KEY")
    secret_key = os.getenv("SECRET_KEY")
    if not access_key or not secret_key:
        return "Error: Onshape ACCESS_KEY or SECRET_KEY not found."
    headers = {
        'Accept': 'application/json;charset=UTF-8; qs=0.09',
        'Content-Type': 'application/json;charset=UTF-8; qs=0.09'
    }
    try:
        response = requests.post(api_url, auth=(access_key, secret_key), headers=headers, json=feature_payload, timeout=30)
        if response.ok:
            try:
                resp = response.json()
                return f"Successfully created cube feature '{name}'. Response: {json.dumps(resp, indent=2)}"
            except json.JSONDecodeError:
                return f"Cube created (status {response.status_code}), but response not valid JSON."
        else:
            return f"Error: Failed to create cube. Status Code: {response.status_code}. Response: {response.text[:200]}"
    except requests.exceptions.RequestException as e:
        return f"Error: A network communication error occurred: {e}"
    except Exception as e:
        return f"Error: An unexpected error occurred: {e}"


@function_tool
def create_onshape_cube(part_studio_url: str, name: str, side_length_expression: str) -> str:
    """
    Creates a simple cube feature in a specified Onshape Part Studio using the dedicated 'cube' featureType.
    """
    return _create_onshape_cube_logic(part_studio_url, name, side_length_expression)


def _create_onshape_feature_logic(part_studio_url: str, feature_payload_str: str) -> str:
    """Internal logic to create a feature using a provided Feature JSON payload."""
    parsed = _parse_onshape_url(part_studio_url)
    if not parsed:
        return f"Error: Could not parse IDs from URL: {part_studio_url}"
    api_url = f"{ONSHAPE_API_BASE_URL}/partstudios/d/{parsed['did']}/w/{parsed['wid']}/e/{parsed['eid']}/features"
    try:
        feature_payload = json.loads(feature_payload_str)
    except json.JSONDecodeError as e:
        return f"Error: Failed to parse feature payload JSON: {e}."
    access_key = os.getenv("ACCESS_KEY")
    secret_key = os.getenv("SECRET_KEY")
    if not access_key or not secret_key:
        return "Error: Onshape ACCESS_KEY or SECRET_KEY not found."
    headers = {
        'Accept': 'application/vnd.onshape.v1+json;charset=UTF-8;qs=0.1',
        'Content-Type': 'application/json'
    }
    try:
        response = requests.post(api_url, auth=(access_key, secret_key), headers=headers, json=feature_payload, timeout=30)
        if response.ok:
            try:
                resp = response.json()
                return f"Successfully created feature. Response: {json.dumps(resp, indent=2)}"
            except json.JSONDecodeError:
                return f"Feature created (status {response.status_code}), but response not valid JSON."
        else:
            return f"Error: Failed to create feature. Status Code: {response.status_code}. Response: {response.text[:200]}"
    except requests.exceptions.RequestException as e:
        return f"Error: A network communication error occurred: {e}"
    except Exception as e:
        return f"Error: An unexpected error occurred: {e}"


@function_tool
def create_onshape_feature(part_studio_url: str, feature_payload_json: str) -> str:
    """
    Creates a new feature in a specified Onshape Part Studio based on a provided JSON payload.
    """
    return _create_onshape_feature_logic(part_studio_url, feature_payload_json)


# --- TypedDict definitions for parsing functions ---
class FeatureInternalMessage(TypedDict):
    featureType: Optional[str]
    featureId: Optional[str]
    name: Optional[str]
    # This can be expanded if other fields from the message are consistently needed for typing

class ParsedFeature(TypedDict):
    typeName: Optional[str] # From the top-level of the original feature object
    message: FeatureInternalMessage # The parsed message part
    # Other original feature keys could be here if consistently present and typed

class ParsedFeaturesData(TypedDict): # Output of feature_parser
    features: List[ParsedFeature]

class SketchPlaneInfo(TypedDict): # Structure returned by extract_plane_vectors
    normal: Optional[List[float]]
    origin: Optional[List[float]]
    x_direction: Optional[List[float]]

class FeatureSummary(TypedDict): # Output of extract_feature_summaries, input/output of enrich_feature_summaries
    featureType: Optional[str]
    featureId: Optional[str]
    name: Optional[str]
    createdEntities: Optional[List[str]] # Changed to List of strings (entity IDs)
    sketchPlane: Optional[SketchPlaneInfo] # Changed to SketchPlaneInfo TypedDict


# Helper functions (not directly tools, but used by tools below)
def feature_3d_parse(feature) -> dict:
    message = feature['message']
    feature_type = message.get('featureType')
    result = {}
    for messagekey in message.keys():
        if messagekey == 'parameters':
            param_list = []
            for parameter in message['parameters']:
                feature_param_dict = {}
                if 'enumName' in parameter['message']:
                    feature_param_dict['parameterId'] = parameter['message']['parameterId']
                    feature_param_dict['enumName'] = parameter['message']['enumName']
                    feature_param_dict['value'] = parameter['message']['value']
                elif 'queries' in parameter['message']:
                    feature_param_dict['parameterId'] = parameter['message']['parameterId']
                    feature_param_dict['queries'] = [query['message'] for query in parameter['message']['queries']]
                elif 'value' in parameter['message'] and 'units' in parameter['message']:
                    feature_param_dict['parameterId'] = parameter['message']['parameterId']
                    feature_param_dict['expression'] = parameter['message']['expression']
                elif 'items' in parameter['message']:
                    feature_param_dict['parameterId'] = parameter['message']['parameterId']
                    feature_param_dict['items'] = parameter['message']['items']
                else:
                    feature_param_dict['parameterId'] = parameter['message']['parameterId']
                    feature_param_dict['value'] = parameter['message'].get('value')
                param_list.append(feature_param_dict)
            # Apply type-specific parameter-level filters for 3D features to the whole list
            if feature_type and feature_type in FILTER_CONFIG:
                param_list = apply_filters(param_list, FILTER_CONFIG[feature_type])
            result['parameters'] = param_list
        else:
            result[messagekey] = message[messagekey]
    # Apply general feature_3d-level filters
    result = apply_filters(result, FILTER_CONFIG['feature_3d'])
    return result


def feature_2d_parse(feature) -> dict:
    message = feature['message']
    result = {}
    for key in message.keys():
        if key == 'entities':
            result['entities'] = entity_parser(message['entities'])
        elif key == 'constraints':
            result['constraints'] = constraint_parser(message['constraints'])
        elif key == 'parameters':
            result['parameters'] = parameter_parser(message['parameters'])
        else:
            result[key] = message[key]
    # Apply feature_2d-level filters
    result = apply_filters(result, FILTER_CONFIG['feature_2d'])
    return result


def entity_parser(entities) -> list:
    result = []
    for entity in entities:
        entity_dict = {'typeName': entity['typeName']}
        for key in entity['message'].keys():
            if key == 'geometry':
                entity_dict['geometry'] = entity['message']['geometry']
            else:
                entity_dict[key] = entity['message'][key]
        # Apply entity-level filters
        entity_dict = apply_filters(entity_dict, FILTER_CONFIG['entity'])
        result.append(entity_dict)
    return result


def constraint_parser(constraints) -> list:
    result = []
    for constraint in constraints:
        constraint_dict = {'typeName': constraint['typeName']}
        for key in constraint['message'].keys():
            if key == 'parameters':
                constraint_dict['parameters'] = []
                for param in constraint['message']['parameters']:
                    param_dict = {}
                    for paramitem in param['message'].keys():
                        param_dict[paramitem] = param['message'][paramitem]
                    # Apply parameter-level filters inside constraint
                    param_dict = apply_filters(param_dict, FILTER_CONFIG['constraint_parameter'])
                    constraint_dict['parameters'].append(param_dict)
            else:
                constraint_dict[key] = constraint['message'][key]
        # Apply constraint-level filters
        constraint_dict = apply_filters(constraint_dict, FILTER_CONFIG['constraint'])
        result.append(constraint_dict)
    return result


def parameter_parser(parameters) -> list:
    result = []
    for parameter in parameters:
        param_dict = {'typeName': parameter['typeName']}
        for key in parameter['message'].keys():
            if key == 'queries':
                param_dict['queries'] = []
                for query in parameter['message']['queries']:
                    query_dict = {}
                    for querykey in query.keys():
                        if querykey == 'message':
                            query_dict['message'] = query['message']
                        else:
                            query_dict[querykey] = query[querykey]
                    param_dict['queries'].append(query_dict)
            else:
                param_dict[key] = parameter['message'][key]
        # Apply parameter-level filters
        param_dict = apply_filters(param_dict, FILTER_CONFIG['parameter'])
        result.append(param_dict)
    return result


def feature_parser(response_data: dict) -> ParsedFeaturesData:
    """
    Parses the feature data dictionary obtained directly from an Onshape API JSON response.
    It processes both 3D features and 2D sketch features, applying configured filters.
    Expects a dictionary containing a 'features' list.
    Returns a dictionary with a 'features' key containing a list of parsed feature dictionaries.
    """
    # response_data = json.loads(response_json_str) # No longer needed, input is already a dict
    print(f"[{datetime.now()}] feature_parser: Received dictionary data.")
    features = []
    raw_features_list = response_data.get('features', []) # Use the input dict directly
    if not isinstance(raw_features_list, list):
         print(f"[{datetime.now()}] feature_parser: Warning - 'features' key not found or not a list in input data.")
         raw_features_list = [] # Process empty list to avoid errors

    print(f"[{datetime.now()}] feature_parser: Processing {len(raw_features_list)} raw features.")
    for feature in raw_features_list:
        feature_dict = {}
        featureType = None
        for key in feature.keys():
            if key == 'typeName': # Still assuming typeName exists
                if feature['typeName'] == 'BTMFeature':
                    featureType = '3D'
                elif feature['typeName'] == 'BTMSketch':
                    featureType = '2D'
                feature_dict['typeName'] = feature['typeName']
            if key == 'message':
                if featureType == '3D':
                    feature_dict['message'] = feature_3d_parse(feature)
                elif featureType == '2D':
                    feature_dict['message'] = feature_2d_parse(feature)
                else:
                    feature_dict['message'] = feature['message']
            else:
                feature_dict[key] = feature[key]
            
            # Apply filters (this part might need review depending on desired filter application point)
            # The original code applied filters inside the key loop, which seems odd.
            # It might be better applied once per feature_dict after the loop?
            # Let's keep original logic for now:
            if key == 'message': 
                if featureType == '3D':
                    pass # Handled in feature_3d_parse
                elif featureType == '2D':
                    pass # Handled in feature_2d_parse

        features.append(feature_dict)
    print(f"[{datetime.now()}] feature_parser: Finished processing. Parsed features count: {len(features)}.")
    return {'features': features}


def extract_feature_summaries(parsed_features: ParsedFeaturesData) -> List[FeatureSummary]:
    """
    Takes the output of feature_parser (a dictionary containing a 'features' list)
    and returns a list of simpler dictionaries, each containing:
      {'featureType': ..., 'featureId': ..., 'name': ...}
    for each feature in order. Useful for getting a quick overview of features.
    """
    summaries = []
    for feature in parsed_features.get('features', []):
        message = feature.get('message', {})
        summary = {
            'featureType': message.get('featureType'),
            'featureId': message.get('featureId'),
            'name': message.get('name')
        }
        summaries.append(summary)
    return summaries


def enrich_feature_summaries(feature_summaries: List[FeatureSummary], url: str) -> List[FeatureSummary]:
    """
    Enriches a list of feature summaries (from extract_feature_summaries) with additional details.
    For each feature:
      - Runs query_get_created_entities to find entities created by this feature (using rollbackBarIndex).
      - If the feature is a 'newSketch', runs query_get_sketch_plane to get its plane information.
    Parameters:
      - feature_summaries: A list of feature summary dictionaries.
      - url: The Onshape document URL (e.g., https://cad.onshape.com/documents/...).
    Returns the list of enriched feature summary dictionaries.
    """
    enriched = []
    for i, feature_summary in enumerate(feature_summaries): # Renamed to avoid conflict
        feature_id = feature_summary.get('featureId')
        feature_type = feature_summary.get('featureType')
        
        # Get created entities with rollbackBarIndex
        # The 'standard_api_request' used by 'query_get_created_entities' constructs the full URL.
        # 'query_get_created_entities' itself needs the base element URL.
        entities_response = query_get_created_entities(url, feature_id, extra_arguments={'rollbackBarIndex': i + 1})
        created_entities_values = []
        try:
            # Assuming entities_response['result']['message']['value'] is a list of entity messages
            if entities_response and entities_response.get('result', {}).get('message', {}).get('value'):
                for entity_value_msg in entities_response['result']['message']['value']:
                     # The actual entity might be nested further, e.g. entity_value_msg['message']['value']
                     # This part needs to align with the actual structure of 'query_get_created_entities' response
                    created_entities_values.append(entity_value_msg.get('message',{}).get('value', {})) # Simplified, adjust based on actual structure
            else: # Handle cases where response structure is not as expected or value is missing
                 pass # Or log a warning, or append a placeholder
        except Exception: # Broad except, consider more specific handling
            pass # Or log error
        feature_summary['createdEntities'] = created_entities_values
        
        # If sketch, get sketch plane
        if feature_type and feature_type == 'newSketch':
            # 'query_get_sketch_plane' also needs the base element URL.
            sketch_plane_response = query_get_sketch_plane(url, feature_id)
            # 'extract_plane_vectors' processes the response from 'query_get_sketch_plane'
            feature_summary['sketchPlane'] = extract_plane_vectors(sketch_plane_response)
            
        enriched.append(feature_summary)
    return enriched

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


# Undecorated logic function
def _onshape_url_to_enriched_feature_summary_logic(url: str) -> Union[dict, str]:
    """
    Core logic for taking an Onshape Part Studio URL, fetching its features, parsing them,
    extracts summaries, and enriches them.
    """
    function_chain_errors = [] # To collect errors if we want to return all

    # Step 1: Get feature list using the new helper
    print(f"[{datetime.now()}] ChainedOp: Calling get_onshape_features for {url}")
    feature_list_result = get_onshape_features(url) # Result is dict or error string
    
    if isinstance(feature_list_result, str) and feature_list_result.startswith("Error:"):
        error_message = f"Step 1 (get_onshape_features) failed: {feature_list_result}"
        print(f"[{datetime.now()}] ChainedOp: {error_message}")
        return error_message
    
    if not isinstance(feature_list_result, dict):
        error_message = f"Step 1 (get_onshape_features) failed: Expected dict result, but got {type(feature_list_result).__name__}. Preview: {str(feature_list_result)[:250]}"
        print(f"[{datetime.now()}] ChainedOp: {error_message}")
        return error_message

    feature_list_dict = feature_list_result
    print(f"[{datetime.now()}] ChainedOp: get_onshape_features completed. Received dictionary.")

    # Step 2: Parse features
    parsed_features: ParsedFeaturesData
    try:
        print(f"[{datetime.now()}] ChainedOp: Calling feature_parser with dictionary.")
        parsed_features_result = feature_parser(response_data=feature_list_dict)
        
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
        error_message = f"Step 2 (feature_parser) failed: JSONDecodeError - {e}. Input preview: {str(feature_list_dict)[:250]}"
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
    print(f"[{datetime.now()}] ChainedOp: Successfully completed _onshape_url_to_enriched_feature_summary_logic for {url}")

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

    return {
        "feature_parser_output": parsed_features,
        "enriched_feature_summaries": enriched_summaries,
        "enriched_feature_summaries_char_count": enriched_feature_summaries_count,
        "feature_list_dict_char_count": feature_list_dict_count,
        "feature_parser_output_char_count": feature_parser_output_count,
        "extract_feature_summaries_output_char_count": extract_feature_summaries_output_count,
    }

@function_tool
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
    return _onshape_url_to_enriched_feature_summary_logic(url)
