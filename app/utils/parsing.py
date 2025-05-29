import sys
import os

# Calculate the project root directory based on the current script's location
# This script is in app/utils, so we need to go up two levels
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Now we can safely import our modules
if __name__ == '__main__':
    from app.utils.api_requests import standard_api_request, endpoints
else:
    from .api_requests import standard_api_request, endpoints

import json
from typing import Any, Dict, List, Union, Optional
from agents import function_tool
from app.utils.filter import apply_filters, FILTER_CONFIG
from app.utils.queries import query_get_created_entities, query_get_sketch_plane, query_get_default_features
from app.utils.geometry_extractors import extract_plane_vectors
from datetime import datetime


def feature_parser(response_data: dict):
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
            # if feature_type and feature_type in FILTER_CONFIG:
            #     param_list = apply_filters(param_list, FILTER_CONFIG[feature_type])
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

def extract_feature_summaries(parsed_features: dict) -> list:
    """
    Takes the output of feature_parser and returns a list of dicts, each containing only:
      {
        'featureType': ...,
        'featureId': ...,
        'name': ...
      }
    for each feature in order.
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


def enrich_feature_summaries(feature_summaries: list, url: str) -> list:
    """
    Enriches a list of feature summary dictionaries with additional information from the Onshape API.

    For each feature in the input summary list, this function:
      - Calls `query_get_created_entities` to retrieve the entities created by the feature, passing
        `extra_arguments={'rollbackBarIndex': i+1}` where `i` is the feature's index in the list. The
        returned entities are added to the feature summary under the key 'createdEntities' as a list of
        dictionaries, each mapping the entity name to an empty dictionary.
      - If the feature's type is 'newSketch', it also calls `query_get_sketch_plane` to retrieve the
        sketch plane information, which is processed by `extract_plane_vectors` and added to the summary
        under the key 'sketchPlane'.

    Parameters:
        feature_summaries (list):
            A list of dictionaries, each representing a feature summary. Each dictionary should contain
            at least the keys 'featureId' and 'featureType'.
        url (str):
            The Onshape document URL used to query for additional feature information.

    Returns:
        list: The input list of feature summaries, with each dictionary enriched with the following keys:
            - 'createdEntities': a list of dicts representing entities created by the feature.
            - 'sketchPlane': (only for sketches) a dict of sketch plane vectors, if applicable.

    Side Effects:
        - Makes network requests to the Onshape API for each feature in the list.
        - Modifies the input feature summary dictionaries in-place by adding new keys.

    Notes:
        - If an error occurs while retrieving created entities, the 'createdEntities' key will be set to an empty list.
        - If an error occurs while retrieving the sketch plane, the 'sketchPlane' key may be omitted.
        - The function assumes that the order of features in the input list matches the order in the Onshape feature tree.
    """
    enriched = []
    default_features = query_get_default_features(url)
    enriched.append({'defaultFeatures': default_features})
    for i, feature in enumerate(feature_summaries):
        feature_id = feature.get('featureId')
        feature_type = feature.get('featureType')
        # Get created entities with rollbackBarIndex
        entities_response = query_get_created_entities(url, feature_id, extra_arguments={'rollbackBarIndex': i+1})
        created_entities = {}
        try:
            # entities_response is now a dict with keys: bodies, edges, faces, vertices
            for entity_type in ['bodies', 'edges', 'faces', 'vertices']:
                items = entities_response.get(entity_type, [])
                created_entities[entity_type] = [{item: {}} for item in items]
        except Exception:
            # If error, set all to empty lists
            for entity_type in ['bodies', 'edges', 'faces', 'vertices']:
                created_entities[entity_type] = []
        feature['createdEntities'] = created_entities
        ## TODO : add rollbackBarIndex to the feature_summaries
        # If sketch, get sketch plane
        if feature_type and feature_type == 'newSketch':
            sketch_plane_response = query_get_sketch_plane(url, feature_id)
            feature['sketchPlane'] = extract_plane_vectors(sketch_plane_response)
        enriched.append(feature)
    return enriched

if __name__ == '__main__':
    url = r'https://cad.onshape.com/documents/34194a7792ea9db6d10188d3/w/2603dadfb9d5ccf8117390d0/e/7c61ed6a6bdd4b97c28505a6'
    params = {'rollbackBarIndex': -1, 'noSketchGeometry': 'false'}  # Example param usage
    response = standard_api_request(
        url,
        endpoints['features'],
        method='GET',
        params=params
    )
    parsed = feature_parser(response)
    # print(parsed)
    os.makedirs('test_data', exist_ok=True)
    with open('test_data/parsed_output.json', 'w', encoding='utf-8') as f:
        json.dump(parsed, f, indent=2)

    feature_summaries = extract_feature_summaries(parsed)
    enriched = enrich_feature_summaries(feature_summaries, url)
    with open('test_data/summary_output.json', 'w', encoding='utf-8') as f:
        json.dump(enriched, f, indent=2)
