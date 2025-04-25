import requests
import json
import os
from dotenv import load_dotenv
from agents import function_tool # Assuming this is the correct import

# Load environment variables from .env file
load_dotenv()

ONSHAPE_API_BASE_URL = "https://cad.onshape.com/api"

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
