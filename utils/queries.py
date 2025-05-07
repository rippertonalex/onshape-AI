from utils.api_requests import standard_api_request, endpoints
from utils.geometry_extractors import extract_plane_vectors, extract_face_geometry, extract_edge_geometry
from utils.geom import convert_2d_to_3d

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

def query_sketch_profile_contains(url: str, sketch_id: str, profile_id: str, test_point: str) -> bool:
    """
    Check if a test point is contained within a sketch profile.

    Args:
        sketch_id (str): The featureID of the sketch profile.
        profile_id (str): The 3 letter transient ID of the profile to check.
        test_point (str): The test point to check in the format "x.xxx,y.yyy,z.zzz", units are meters.

    Returns:
        bool: True if the test point is contained within the profile, False otherwise.
    """
    payload = {
    "script": f"""
    function(context is Context, queries) {{ 
      return transientQueriesToStrings(evaluateQuery(context, qContainsPoint(qSketchRegion(makeId('{sketch_id}')), vector([{test_point}])*meter))); 
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
        matches.append(result['message']['value'])
    
    if len(matches) == 1 and matches[0] == profile_id:
        return True
    else:
        return False

def query_define_face_or_edge(url: str, entity_id: str, rollback_index: int) -> dict:
    """
    Query to define a face or edge from a given entity ID and rollback index.

    Args:
        url (str): The base URL of the API.
        entity_id (str): The transint ID of the entity to define. 3 letters for a face, 4 letters for an edge.
        rollback_index (int): The rollback index of the entity to define.

    Returns:
        dict: The minimal definition of the face or edge.
    """
    if len(entity_id) == 3:
        entity_type = 'face'
    elif len(entity_id) == 4:
        entity_type = 'edge'
    else:
        raise ValueError(f"Invalid entity ID: {entity_id}")
    
    if entity_type == 'face':
        payload = {
            "script": f"""
            function(context is Context, queries) {{ 
                const transientID = qTransient('{entity_id}');
                println(transientID);
                return transientQueriesToStrings(evSurfaceDefinition(context, {{'face': transientID}}));
            }}"""
        }
    elif entity_type == 'edge':
        payload = {
            "script": f"""
            function(context is Context, queries) {{ 
                const transientID = qTransient('{entity_id}');
                println(transientID);
                return transientQueriesToStrings(evCurveDefinition(context, {{'edge': transientID}}));
            }}"""
        }
    else:
        raise ValueError(f"Invalid entity ID: {entity_id}")
    
    response = standard_api_request(url,
                                    endpoints['featurescript'],
                                    method='POST',
                                    payload=payload,
                                    params={'rollbackBarIndex': rollback_index})
    
    if entity_type == 'face':
        return extract_face_geometry(response)
    elif entity_type == 'edge':
        return extract_edge_geometry(response)

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

    print(query_sketch_profile_contains(url, sketch_id, 'JGO', test_point))

    x_2d = 0.25
    y_2d = 3
    test_point = convert_2d_to_3d(x_2d, y_2d, sketch_plane['normal'], sketch_plane['x_direction'], sketch_plane['origin'], units='in')
    print(test_point)

    print(query_sketch_profile_contains(url, sketch_id, 'JGO', test_point))

    face_id = 'JHK'
    face_definition = query_define_face_or_edge(url, face_id, 2)
    print(face_definition)

    edge_id = 'KIlC'
    edge_definition = query_define_face_or_edge(url, edge_id, 3)
    print(edge_definition)
