import sys
import os
import re
import json

# Calculate the project root directory based on the current script's location
# This script is in app/utils, so we need to go up two levels
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Now we can safely import our modules
if __name__ == '__main__':
    from app.utils.api_requests import standard_api_request, endpoints
    from app.utils.geometry_extractors import extract_plane_vectors, extract_face_geometry, extract_edge_geometry
    from app.utils.geom import convert_2d_to_3d
    from app.utils.parsing import feature_parser, extract_feature_summaries, enrich_feature_summaries
else:
    from .api_requests import standard_api_request, endpoints
    from .geometry_extractors import extract_plane_vectors, extract_face_geometry, extract_edge_geometry
    from .geom import convert_2d_to_3d

def parse_console_map_output(console_output: str) -> dict:
    # Remove curly braces at the ends
    s = console_output.strip()
    if s.startswith("{") and s.endswith("}"):
        s = s[1:-1]
    result = {}
    # Split by top-level commas (not inside brackets)
    parts = re.split(r',\s*(?=[a-zA-Z_][a-zA-Z0-9_]*\s*:)', s)
    for part in parts:
        key, value = part.split(":", 1)
        key = key.strip()
        # Extract items inside brackets
        items_match = re.search(r'\[(.*)\]', value)
        if items_match:
            items_str = items_match.group(1)
            # Split by comma, strip whitespace, ignore empty
            items = [item.strip() for item in items_str.split(",") if item.strip()]
        else:
            items = []
        result[key] = items
    return result

def query_get_all_entities(url: str, extra_arguments: dict = None) -> dict:
    """
    Query to get all entities of all types.
    Args:
        url (str): The URL of the Onshape document.
        extra_arguments (dict): Extra arguments to pass to the query. Typically of the form {'rollbackBarIndex': i}
    Returns:
        dict: All entities separated by type: BODY, FACE, EDGE, VERTEX.
    """
    result = {}
    keys = ['bodies', 'faces', 'edges', 'vertices']
    entity_types = ['BODY', 'FACE', 'EDGE', 'VERTEX']
    
    for key, entity_type in zip(keys, entity_types):
        feature_payload = {
            "script": f"""
            function(context is Context, queries) {{
              return transientQueriesToStrings(evaluateQuery(context, qEverything(EntityType.{entity_type})));
              }}"""
        }
        response = standard_api_request(url,
                                    endpoints['featurescript'],
                                    method='POST',
                                    payload=feature_payload,
                                    params=extra_arguments)
        
        entities = []
        for item in response['result']['message']['value']:
            entities.append(item['message']['value'])
        result[key] = entities
    
    return result

def query_get_created_entities(url: str, feature_id: str, extra_arguments: dict = None) -> dict:
    """
    Query to get the created entities of a given feature ID.
    Args:
        url (str): The URL of the part studio.
        feature_id (str): The featureID of the feature to get the created entities of.
        extra_arguments (dict): Extra arguments to pass to the query. Typically of the form {'rollbackBarIndex': i}
    Returns:
        dict: The created entities of the given feature ID, separated by type: BODY, FACE, EDGE, VERTEX.
    """
    payload = {
    "script": f"""
    function(context is Context, queries) {{
      var entityMap = {{}};
      var entityQuery = qCreatedBy(makeId('{feature_id}'));
      var bodyQuery = qEntityFilter(entityQuery, EntityType.BODY);
      entityMap['bodies'] = transientQueriesToStrings(evaluateQuery(context, bodyQuery));
      var faceQuery = qEntityFilter(entityQuery, EntityType.FACE);
      entityMap['faces'] = transientQueriesToStrings(evaluateQuery(context, faceQuery));
      var edgeQuery = qEntityFilter(entityQuery, EntityType.EDGE);
      entityMap['edges'] = transientQueriesToStrings(evaluateQuery(context, edgeQuery));
      var vertexQuery = qEntityFilter(entityQuery, EntityType.VERTEX);
      entityMap['vertices'] = transientQueriesToStrings(evaluateQuery(context, vertexQuery));
      println(entityMap);
      }}"""
}
    response = standard_api_request(url,
                                endpoints['featurescript'],
                                method='POST',
                                payload=payload,
                                params=extra_arguments)
    # print(response['console'])
    response = parse_console_map_output(response['console'])
    return response

def query_get_default_features(url: str) -> dict:
    """
    Query to get the default features of a given part studio.
    Args:
        url (str): The URL of the part studio.
    Returns:
        dict: The default features of the given part studio. Example:
        {
            'Origin': 'IB',
            'Front': 'JCC',
            'Right': 'JDC',
            'Top': 'JEC'
        }
    """
    output = {}
    entity_names = ['Origin', 'Front', 'Right', 'Top']
    entity_types = ['VERTEX', 'FACE', 'FACE', 'FACE']
    for entity_name, entity_type in zip(entity_names, entity_types):
      feature_payload = {
        "script": f"""
        function(context is Context, queries) {{
          return transientQueriesToStrings(evaluateQuery(context, qCreatedBy(makeId(\"{entity_name}\"), EntityType.{entity_type})));
          }}"""
      }
      response = standard_api_request(url,
                                      endpoints['featurescript'],
                                      method='POST',
                                      payload=feature_payload)
      id = response['result']['message']['value'][0]['message']['value']
      output[entity_name] = id
    return output

def query_get_sketch_plane(url: str, sketch_id: str) -> dict:
    """
    Query to get the sketch plane of a given sketch ID.
    Args:
        url (str): The URL of the part studio.
        sketch_id (str): The featureID of the sketch to get the plane of.
    Returns:
        dict: The sketch plane of the given sketch ID.
    """
    payload = {
    "script": f"""
    function(context is Context, queries) {{ 
      return evOwnerSketchPlane(context, {{'entity': qCreatedBy(makeId('{sketch_id}'), EntityType.BODY)}}); 
      }}"""
}
    response = standard_api_request(url,
                                    endpoints['featurescript'],
                                    method='POST',
                                    payload=payload)
    return response

def query_get_sketch_n_regions(url: str, sketch_id: str) -> dict:
    """
    Query to get the sketch and its regions.
    Args:
        url (str): The URL of the Onshape document.
        sketch_id (str): The featureID of the sketch to get the regions of.
    Returns:
        int: The number of regions in the sketch.
    """
    payload = {
    "script": f"""
    function(context is Context, queries) {{
    return transientQueriesToStrings(evaluateQuery(context, qSketchRegion(makeId('{sketch_id}'), false)));
    }}"""
    }
    response = standard_api_request(url,
                                    endpoints['featurescript'],
                                    method='POST',
                                    payload=payload)
    return len(response['result']['message']['value'])

def query_sketch_profiles_contains(url: str, enriched_feature_summary: list, test_points: list) -> list:
    """
    For each sketch and its test points, check which region(s) each point is contained in.
    Args:
        url (str): The URL of the Onshape document.
        enriched_feature_summary (list): 
            A list of feature summary dictionaries, where each dictionary contains the original feature summary keys
            (such as 'featureType', 'featureId', and 'name'), and is enriched with:
                - 'createdEntities': a list of dictionaries representing entities created by the feature.
                - 'sketchPlane': (for sketch features only) a dictionary of sketch plane vectors, if applicable.
            This list is typically produced by the enrich_feature_summaries function and includes additional
            information retrieved from the Onshape API for each feature.
        test_points (list): A list where each item is a dict with:
            - 'sketch_id' (str): The sketch id
            - 'test_points' (list): Each item is a string "x.xxx,y.yyy" (meters). The coordinates are 2D and relative to the sketch plane.
            test_points = [
                {'sketch_id': 'FT1DvSE7Alu8Ovc_0', 'test_points': [[0.0, 0.75], [0.0, -5.0]]},
            ]
    Returns:
        list: Each item is a dict with:
            - 'id' (str): The sketch id
            - 'points_to_region_ids' (list): Each item is a dict with:
                - 'pt_xyz' (str): The test point
                - 'geo_id' (list): List of region ids matched (after disambiguation)
            points_to_region_ids = [
                {'pt_xyz': '0,0', 'geo_id': ['JHK']},
                {'pt_xyz': '0,0.75', 'geo_id': ['JGO']},
                {'pt_xyz': '0,-5', 'geo_id': ['JGC']},
            ]
    """
    results = []
    enriched_by_id = {f['featureId']: f for f in enriched_feature_summary if f.get('featureId')}
    for sketch in test_points:
        sketch_id = sketch['sketch_id']
        sketch_plane = enriched_by_id[sketch_id]['sketchPlane']
        pts = sketch['test_points']
        print([pt for pt in pts])
        pts_3d = [convert_2d_to_3d(pt, sketch_plane['normal'], sketch_plane['x_direction'], sketch_plane['origin']) for pt in pts]
        points_to_matches = []
        geo_id_to_points = {}
        # First pass: collect all matches
        for pt in pts_3d:
            payload = {
                "script": f"""
                function(context is Context, queries) {{ 
                  return transientQueriesToStrings(evaluateQuery(context, qContainsPoint(qSketchRegion(makeId('{sketch_id}')), vector([{pt}])*meter))); 
                  }}"""
            }
            response = standard_api_request(
                url,
                endpoints['featurescript'],
                method='POST',
                payload=payload
            )
            matches = []
            for result in response['result']['message']['value']:
                geo_id = result['message']['value']
                matches.append(geo_id)
                if geo_id not in geo_id_to_points:
                    geo_id_to_points[geo_id] = set()
                geo_id_to_points[geo_id].add(pt)
            points_to_matches.append({'pt_xyz': pt, 'geo_id': matches})
        # Second pass: disambiguate geo_ids
        # Build a set of geo_ids that are matched by more than one point
        ambiguous_geo_ids = {gid for gid, pts_set in geo_id_to_points.items() if len(pts_set) > 1}
        # For each point, remove ambiguous geo_ids unless it is the only match for that point
        for pt_match in points_to_matches:
            pt_geo_ids = pt_match['geo_id']
            # If more than one geo_id, remove ambiguous ones
            if len(pt_geo_ids) > 1:
                pt_match['geo_id'] = [gid for gid in pt_geo_ids if gid not in ambiguous_geo_ids]
            # If after removal, empty, restore ambiguous geo_ids (if that's all there was)
            if not pt_match['geo_id']:
                pt_match['geo_id'] = [gid for gid in pt_geo_ids if gid in ambiguous_geo_ids]
        results.append({'id': sketch_id, 'points_to_region_ids': points_to_matches})
    return results

def _define_face(url: str, entity_id: str, rollback_index: int):
    payload = {
        "script": f"""
        function(context is Context, queries) {{ 
            const transientID = qTransient('{entity_id}');
            println(transientID);
            return transientQueriesToStrings(evSurfaceDefinition(context, {{'face': transientID}}));
        }}"""
    }
    response = standard_api_request(url,
                                    endpoints['featurescript'],
                                    method='POST',
                                    payload=payload,
                                    params={'rollbackBarIndex': rollback_index})
    return extract_face_geometry(response)

def _define_edge(url: str, entity_id: str, rollback_index: int):
    payload = {
        "script": f"""
        function(context is Context, queries) {{ 
            const transientID = qTransient('{entity_id}');
            println(transientID);
            return transientQueriesToStrings(evCurveDefinition(context, {{'edge': transientID}}));
        }}"""
    }
    response = standard_api_request(url,
                                    endpoints['featurescript'],
                                    method='POST',
                                    payload=payload,
                                    params={'rollbackBarIndex': rollback_index})
    return extract_edge_geometry(response)

def _define_body(url: str, entity_id: str, rollback_index: int):
    """
    Placeholder function to define a body entity.
    In a real implementation, this would query the Onshape API for body geometry or metadata.
    Args:
        url (str): The base URL of the API.
        entity_id (str): The ID of the body entity to define.
        rollback_index (int): The rollback index for the feature tree state.
    Returns:
        dict: A dictionary containing the definition of the body entity.
    """
    return {'definition': f'Definition for body {entity_id} at rollback {rollback_index}'}

def _define_vertex(url: str, entity_id: str, rollback_index: int):
    """
    Placeholder function to define a vertex entity.
    In a real implementation, this would query the Onshape API for vertex geometry or metadata.
    Args:
        url (str): The base URL of the API.
        entity_id (str): The ID of the vertex entity to define.
        rollback_index (int): The rollback index for the feature tree state.
    Returns:
        dict: A dictionary containing the definition of the vertex entity.
    """
    return {'definition': f'Definition for vertex {entity_id} at rollback {rollback_index}'}

def define_ambiguous_entities(url: str, entity_id_list: list, enriched_feature_summary: list) -> list:
    """
    Enriches the provided feature summary with geometry definitions for specified ambiguous entities.
    For each feature in the enriched_feature_summary (except sketches), this function iterates through all entity categories
    (bodies, faces, edges, vertices). If an entity's ID matches one in the entity_id_list, it calls the appropriate definition
    function (_define_edge, _define_face, _define_body, or _define_vertex) and inserts the resulting definition into the entity's
    dictionary within the enriched_feature_summary.
    Args:
        url (str): The base URL of the API.
        entity_id_list (list): List of entity IDs (strings) to define (e.g., ['JGO', 'JHK']).
        enriched_feature_summary (list): List of feature summary dictionaries, each containing createdEntities and other metadata.
    Returns:
        list: The enriched_feature_summary with definitions added for all matched entities.
    """
    for rollback_index, feature in enumerate(enriched_feature_summary, start=1):
        feature_id = feature.get('featureId')
        feature_type = feature.get('featureType')
        if feature_type == 'newSketch':
            # Get the number of regions in the sketch
            n_regions = query_get_sketch_n_regions(url, feature_id)
            print(f"Sketch {feature_id} has {n_regions} regions")
            feature['n_regions'] = n_regions
        created_entities = feature.get('createdEntities', {})
        ## TODO: Invert the searching hierarchy, so that we search for the entity_id_list in the createdEntities,
        ## and then call the appropriate definition function.
        for category in ['bodies', 'faces', 'edges', 'vertices']:
            entities = created_entities.get(category, [])
            for entity_dict in entities:
                for entity_id in entity_dict.keys():
                    if entity_id in entity_id_list:
                        print(f"Defining {entity_id} for {feature_id} at rollback {rollback_index}")
                        # Call the appropriate definition function
                        if category == 'edges':
                            definition = _define_edge(url, entity_id, rollback_index)
                        elif category == 'faces':
                            definition = _define_face(url, entity_id, rollback_index)
                        elif category == 'bodies':
                            definition = _define_body(url, entity_id, rollback_index)
                        elif category == 'vertices':
                            definition = _define_vertex(url, entity_id, rollback_index)
                        else:
                            definition = None
                        # Insert the definition into the entity's dict
                        entity_dict[entity_id]['definition'] = definition
                    else:
                        # print(f"Attempting to define {entity_id} at rollback {rollback_index} but it is not in the createdEntities list")
                        pass
    return enriched_feature_summary

if __name__ == '__main__':
    def save_debug_json(data: dict, filename: str = 'output_debug.json'):
        """
        Save a dictionary to a JSON file in the test_data folder.
        
        Args:
            data (dict): The dictionary to save
            filename (str): The name of the file to save to (default: 'output_debug.json')
        """
        # Ensure test_data directory exists
        test_data_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'test_data')
        os.makedirs(test_data_dir, exist_ok=True)
        
        # Create full file path
        file_path = os.path.join(test_data_dir, filename)
        
        # Save the data with pretty printing
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Debug data saved to {file_path}")

    url = r'https://cad.onshape.com/documents/34194a7792ea9db6d10188d3/w/2603dadfb9d5ccf8117390d0/e/140112c65afa2d3dddb074ba'
    params = {'rollbackBarIndex': -1, 'noSketchGeometry': 'false'}

    # Step 1: Get and parse features
    response = standard_api_request(
        url,
        endpoints['features'],
        method='GET',
        params=params
    )
    parsed = feature_parser(response)
    # Save the parsed data for debugging
    save_debug_json(parsed, 'parsed_features.json')
    
    feature_summaries = extract_feature_summaries(parsed)
    save_debug_json(feature_summaries, 'feature_summaries.json')
    
    enriched = enrich_feature_summaries(feature_summaries, url)
    save_debug_json(enriched, 'enriched_feature_summaries.json')

    # Step 2: Build a mapping for easy lookup
    # enriched_by_id = {f['featureId']: f for f in enriched if f.get('featureId')}
    # save_debug_json(enriched_by_id, 'enriched_by_id.json')

    # Step 3: Find a sketch feature to test
    sketch_features = [f for f in enriched if f.get('featureType') == 'newSketch']
    if not sketch_features:
        print("No sketch features found.")
    else:
        sketch_id = sketch_features[0]['featureId']
        print(f"Testing sketch_id: {sketch_id}")

        # Step 4: Define test points (2D, in inches)
        test_points = [
            {'sketch_id': sketch_id, 'test_points': [
                [0.0, 0.02], 
                [-0.03175, 0.01905],
                [0.03175, 0.01905],
                [0.0, 0.07619]]},
        ]

        # Step 5: Run the test
        result = query_sketch_profiles_contains(url, enriched, test_points)
        # print("Result of query_sketch_profiles_contains:")
        # print(result)
        save_debug_json(result, 'sketch_profiles_result.json')

    # --- Test for define_ambiguous_entities ---
    print("\n--- Testing define_ambiguous_entities ---")
    entity_id_list = ['JDC', 'JGO', 'JHF', 'JHG', 'JHK', 'KIlC']
    # Deep copy to avoid mutating the original enriched summary if needed
    import copy
    enriched_copy = copy.deepcopy(enriched)
    enriched_with_defs = define_ambiguous_entities(url, entity_id_list, enriched_copy)
    save_debug_json(enriched_with_defs, 'enriched_with_defs.json')
    # print(json.dumps(enriched_with_defs, indent=2))