import json
import requests
from onshape_client.onshape_url import OnshapeElement
from os import getenv
import os

ACCESS_KEY = getenv('ACCESS_KEY')
SECRET_KEY = getenv('SECRET_KEY')

base_url = 'https://cad.onshape.com'

endpoints = {
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

def standard_api_request(url: str,
                        endpoint_url: str,
                        method: str = 'GET',
                        params: dict = None,
                        payload: dict = None,
                        pid: str = None,
                        sid: str = None,
                        download: bool = False,
                        tag: str = None):
    """
    Make an authenticated API request to the Onshape API.

    Parameters:
    - url (str): The full Onshape document URL.
    - endpoint_url (str): The endpoint template string (from endpoints).
    - method (str): HTTP method ('GET' or 'POST').
    - params (dict): Dictionary of query parameters to append to the URL. Example: {'rollbackBarIndex': -1, 'noSketchGeometry': 'true'}
    - payload (dict): Dictionary of data to send in the body (for POST requests).
    - pid (str): Optional part ID for endpoints that require it.
    - sid (str): Optional sketch ID for endpoints that require it.
    - download (bool): If True, saves the response as a JSON file in test_data.
    - tag (str): Optional string to tag the output file name (output_{tag}.json).

    Returns:
    - dict: The JSON response from the API.

    If download is True, the response is also saved to test_data/output.json or test_data/output_{tag}.json.
    """
    
    element = OnshapeElement(url)
    endpoint_url = endpoint_url.replace('did', element.did)
    endpoint_url = endpoint_url.replace('wid', element.wvmid)
    endpoint_url = endpoint_url.replace('eid', element.eid)
    if pid:
        endpoint_url = endpoint_url.replace('pid', pid)
    if sid:
        endpoint_url = endpoint_url.replace('sid', sid)

    if payload is None:
        payload = {}

    headers = {'Accept': 'application/vnd.onshape.v1+json; charset=UTF-8;qs=0.1',
               'Content-Type': 'application/json'}
    if params is not None:
        endpoint_url += '?'
        for key in params.keys():
            endpoint_url += f"{key}={params[key]}&"
        endpoint_url = endpoint_url[:-1]

    api_url = base_url + endpoint_url

    if method == 'GET':
        response = requests.get(
            api_url,
            auth=(ACCESS_KEY, SECRET_KEY),
            headers=headers,
            timeout=20
        ).json()
    elif method == 'POST':
        response = requests.post(
            api_url,
            auth=(ACCESS_KEY, SECRET_KEY),
            headers=headers,
            json=payload,
            timeout=20
        ).json()
    else:
        raise ValueError(f"Unsupported method {method!r}")

    if download:
        if not os.path.exists('test_data'):
            os.makedirs('test_data')
        if tag:
            out_path = f"test_data/output_{tag}.json"
        else:
            out_path = "test_data/output.json"
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(response, f, indent=2)
    return response

if __name__ == "__main__":
    url = r'https://cad.onshape.com/documents/34194a7792ea9db6d10188d3/w/2603dadfb9d5ccf8117390d0/e/140112c65afa2d3dddb074ba'
    params = {'rollbackBarIndex': -1, 'noSketchGeometry': 'true'}  # Example param usage
    response = standard_api_request(
        url,
        endpoints['features'],
        method='GET',
        params=params
    )
    print(response)
