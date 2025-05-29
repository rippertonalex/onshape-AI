def extract_plane_vectors(response: dict) -> dict:
    """
    Extracts normal, origin, and x-direction vectors from a FeatureScript evOwnerSketchPlane response.
    
    Args:
        response (dict): The response from the FeatureScript evOwnerSketchPlane query.

    Returns:
        dict: A dictionary containing the normal, origin, and x-direction vectors.
    """
    
    # Initialize output
    normal = origin = x_dir = None

    # Check if the response has the expected structure
    if "result" not in response:
        print(f"ERROR: 'result' key not found in sketch plane response. Available keys: {list(response.keys())}")
        return {"normal": None, "origin": None, "x_direction": None}
    
    if "message" not in response["result"]:
        print(f"ERROR: 'message' key not found in response['result']. Available keys: {list(response['result'].keys())}")
        return {"normal": None, "origin": None, "x_direction": None}
    
    if "value" not in response["result"]["message"]:
        print(f"ERROR: 'value' key not found in response['result']['message']. Available keys: {list(response['result']['message'].keys())}")
        return {"normal": None, "origin": None, "x_direction": None}

    # Navigate to the list of value map entries
    entries = response["result"]["message"]["value"]
    
    # Handle empty entries (when API returns error or no data)
    if not entries:
        print("WARNING: No sketch plane data returned from API.")
        return {"normal": None, "origin": None, "x_direction": None}

    for entry in entries:
        key = entry["message"]["key"]["message"]["value"]
        value_data = entry["message"]["value"]["message"]["value"]
        
        if key == "normal":
            normal = [v["message"]["value"] for v in value_data]
        
        elif key == "origin":
            # These values have units; we just extract the numeric values
            origin = [v["message"]["value"] for v in value_data]
        
        elif key == "x":
            x_dir = [v["message"]["value"] for v in value_data]

    return {
        "normal": normal,
        "origin": origin,
        "x_direction": x_dir
    }

def extract_face_geometry(face_json: dict) -> dict:
    """
    Extracts face geometry information from a Featurescript face JSON response.

    Parameters:
        face_json (dict): JSON response from Onshape transient face query.

    Returns:
        dict: {
            "normal": list of float,   # The normal vector of the face (if present)
            "x": list of float,        # The x-direction vector of the face (if present)
            "origin": list of float,   # The origin point of the face (if present)
            "surfaceType": str,        # The type of surface (e.g., 'plane', 'cylinder', etc.)
            "typeTag": str             # The overall typeTag for the geometry object
        }
    """
    result = {}
    # print(face_json)
    entries = face_json["result"]["message"]["value"]

    for entry in entries:
        key = entry["message"]["key"]["message"]["value"]
        value_data = entry["message"]["value"]["message"]

        if key in {"normal", "x"}:
            # Plain vector with 3 components
            result[key] = [v["message"]["value"] for v in value_data["value"]]

        elif key == "origin":
            # Vector with units
            result["origin"] = [v["message"]["value"] for v in value_data["value"]]

        elif key == "surfaceType":
            result["surfaceType"] = value_data["value"]

    # Add the overall typeTag for the geometry object
    result["typeTag"] = face_json["result"]["message"]["typeTag"]

    return result

def extract_edge_geometry(edge_json: dict) -> dict:
    """
    Extracts the curve type, direction, and origin from a Featurescript edge JSON response.
    
    Parameters:
        edge_json (dict): JSON response from Onshape transient edge query.
        
    Returns:
        dict: {
            "type": str,
            "direction": list of float,
            "origin": list of float
        }
    """
    result = {"type": None, "direction": None, "origin": None}

    if "result" not in edge_json or "message" not in edge_json["result"]:
        raise ValueError("Invalid JSON structure: missing result/message")

    for entry in edge_json["result"]["message"]["value"]:
        key = entry["message"]["key"]["message"]["value"]
        value_entry = entry["message"]["value"]

        if key == "curveType":
            result["type"] = value_entry["message"]["value"]
        elif key == "direction":
            result["direction"] = [
                val["message"]["value"] for val in value_entry["message"]["value"]
            ]
        elif key == "origin":
            result["origin"] = [
                val["message"]["value"] for val in value_entry["message"]["value"]
            ]

    return result
