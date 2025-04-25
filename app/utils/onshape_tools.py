import os
import json
import re
import requests
from typing import Union
from dotenv import load_dotenv
from agents import function_tool

# Load environment variables for API keys
load_dotenv()
ONSHAPE_API_BASE_URL = "https://cad.onshape.com/api/v10"


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
