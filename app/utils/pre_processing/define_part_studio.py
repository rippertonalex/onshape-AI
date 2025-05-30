import sys
import os
import json

# Calculate the project root directory based on the current script's location
# This script is in app/utils/pre-processing, so we need to go up three levels
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.utils.queries import standard_api_request, endpoints

if __name__ == "__main__":
    url = r"https://cad.onshape.com/documents/34194a7792ea9db6d10188d3/w/2603dadfb9d5ccf8117390d0/e/ed0327add99ecf3427274439"

    element_info = {}
    response = standard_api_request(url, endpoints['metadata'], method='GET')
    element_info['element_type'] = response['mimeType']
    element_info['Name'] = response['properties'][0]['value']
    element_info['Description'] = response['properties'][1]['value']

    # print(element_info)

    if element_info['element_type'] == 'onshape/partstudio':
        element_info['parts'] = []
        response = standard_api_request(url, endpoints['parts'], method='GET')
        for part in response:
            part_info = {}
            part_info['name'] = part['name']
            part_info['description'] = part['description']
            part_info['partId'] = part['partId']
            # print(part_info)
            element_info['parts'].append(part_info)

    print(json.dumps(element_info, indent=4))
