import json
import os
from typing import Any, Dict
from utils.api_requests import standard_api_request, endpoints
from utils.filter import apply_filters, FILTER_CONFIG
from utils.queries import query_get_created_entities, query_get_sketch_plane
from utils.geometry_extractors import extract_plane_vectors

def feature_parser(response) -> dict:
    features = []
    for feature in response['features']:
        feature_dict = {}
        featureType = None
        for key in feature.keys():
            if key == 'typeName':
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
            
            if featureType == '3D':
                feature_dict = apply_filters(feature_dict, FILTER_CONFIG['feature_3d'])
            elif featureType == '2D':
                feature_dict = apply_filters(feature_dict, FILTER_CONFIG['feature_2d'])
        features.append(feature_dict)
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
    For each feature in the summary, run get_created_entities and add the returned 'value' list to the summary.
    If the feature is a sketch, also run get_sketch_plane and add the result to the summary.
    Passes extra_arguments={'rollbackBarIndex': i+1} to get_created_entities for each feature.
    Returns the enriched summary list.
    """
    enriched = []
    for i, feature in enumerate(feature_summaries):
        feature_id = feature.get('featureId')
        feature_type = feature.get('featureType')
        # Get created entities with rollbackBarIndex
        entities_response = query_get_created_entities(url, feature_id, extra_arguments={'rollbackBarIndex': i+1})
        values = []
        try:
            # Each entity is a dict with the entity name as key and an empty dict as value
            values = [{v['message']['value']: {}} for v in entities_response['result']['message']['value']]
        except Exception:
            pass
        feature['createdEntities'] = values
        ## TODO : add rollbackBarIndex to the feature_summaries
        # If sketch, get sketch plane
        if feature_type and feature_type == 'newSketch':
            sketch_plane_response = query_get_sketch_plane(url, feature_id)
            feature['sketchPlane'] = extract_plane_vectors(sketch_plane_response)
        enriched.append(feature)
    return enriched

if __name__ == '__main__':
    url = r'https://cad.onshape.com/documents/34194a7792ea9db6d10188d3/w/2603dadfb9d5ccf8117390d0/e/140112c65afa2d3dddb074ba'
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
