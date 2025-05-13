from .api_requests import standard_api_request, endpoints
from .geometry_extractors import extract_plane_vectors, extract_face_geometry, extract_edge_geometry
from .geom import convert_2d_to_3d

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

def query_get_created_entities(url: str, feature_id: str, extra_arguments: dict = None) -> dict:
    """
    Query to get the created entities of a given feature ID.

    Args:
        url (str): The URL of the part studio.
        feature_id (str): The featureID of the feature to get the created entities of.
        extra_arguments (dict): Extra arguments to pass to the query. Typically of the form {'rollbackBarIndex': i}

    Returns:
        dict: The created entities of the given feature ID.
    """
    payload = {
    "script": f"""
    function(context is Context, queries) {{ 
      return transientQueriesToStrings(evaluateQuery(context, qCreatedBy(makeId('{feature_id}')))); 
      }}"""
}
    response = standard_api_request(url,
                                endpoints['featurescript'],
                                method='POST',
                                payload=payload,
                                params=extra_arguments)
    # for result in response['result']['message']['value']:
    #     print(result['message']['value'])
    return response

def query_sketch_profiles_contains(url: str, test_points: list) -> list:
    """
    For each sketch and its test points, check which region(s) each point is contained in.

    Args:
        url (str): The URL of the Onshape document.
        test_points (list): A list where each item is a dict with:
            - 'id' (str): The sketch id
            - 'test_points' (list): Each item is a string "x.xxx,y.yyy,z.zzz" (meters)

    Returns:
        list: Each item is a dict with:
            - 'id' (str): The sketch id
            - 'points_to_region_ids' (list): Each item is a dict with:
                - 'pt_xyz' (str): The test point
                - 'geo_id' (list): List of region ids matched (after disambiguation)
    """
    results = []
    for sketch in test_points:
        sketch_id = sketch['id']
        pts = sketch['test_points']
        points_to_matches = []
        geo_id_to_points = {}
        # First pass: collect all matches
        for pt in pts:
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

def batch_define_faces_and_edges(url: str, entity_id_list: list) -> list:
    """
    Batch query to define faces and edges from a list of entity IDs and rollback indices.

    Args:
        url (str): The base URL of the API.
        entity_id_list (list): Each item is a dict with 'entity_id' (3-letter face or 4-letter edge ID) and 'rollback_index' (int).

    Returns:
        list: Each item is a dict with 'entity_id', 'type' ('face' or 'edge'), and 'definition' (geometry data).
    """
    results = []
    for item in entity_id_list:
        entity_id = item['entity_id']
        rollback_index = item['rollback_index']
        if len(entity_id) == 3:
            definition = _define_face(url, entity_id, rollback_index)
            results.append({'entity_id': entity_id, 'type': 'face', 'definition': definition})
        elif len(entity_id) == 4:
            definition = _define_edge(url, entity_id, rollback_index)
            results.append({'entity_id': entity_id, 'type': 'edge', 'definition': definition})
        else:
            # Optionally, skip or raise error for invalid entity_id
            continue
    return results

if __name__ == '__main__':
    url = r'https://cad.onshape.com/documents/34194a7792ea9db6d10188d3/w/2603dadfb9d5ccf8117390d0/e/140112c65afa2d3dddb074ba'
    
    sketch_id = 'FT1DvSE7Alu8Ovc_0'
    sketch_plane = query_get_sketch_plane(url, sketch_id)
    sketch_plane = extract_plane_vectors(sketch_plane)
    print(sketch_plane)

    x_2d = 0
    y_2d = 1
    test_point = convert_2d_to_3d(x_2d, y_2d, sketch_plane['normal'], sketch_plane['x_direction'], sketch_plane['origin'], units='in')
    print(test_point)

    print(query_sketch_profiles_contains(url, [{'id': sketch_id, 'test_points': [test_point]}]))

    x_2d = 0.25
    y_2d = 3
    test_point = convert_2d_to_3d(x_2d, y_2d, sketch_plane['normal'], sketch_plane['x_direction'], sketch_plane['origin'], units='in')
    print(test_point)

    print(query_sketch_profiles_contains(url, [{'id': sketch_id, 'test_points': [test_point]}]))

    face_id = 'JHK'
    face_definition = query_define_face_or_edge(url, face_id, 2)
    print(face_definition)

    edge_id = 'KIlC'
    edge_definition = query_define_face_or_edge(url, edge_id, 3)
    print(edge_definition)
