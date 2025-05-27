import sys
import os

# Calculate the project root directory based on the current script's location
# This script is in app/utils/pre-processing, so we need to go up three levels
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.utils.queries import query_sketch_profiles_contains

def define_sketch_entities(url: str, test_points_output: list, enriched_feature_summary: list) -> list:
    """
    Define sketch entities by checking which regions contain the test points.
    
    Args:
        url (str): The URL of the Onshape document.
        test_points_output (list): Output from test_points.py function, where each item is a dict with:
            - 'sketch_id' (str): The sketch id
            - 'test_points' (list): Each item is [x, y] coordinates in meters
        enriched_feature_summary (list): The enriched feature summary containing sketch plane information
    
    Returns:
        list: Each item is a dict with:
            - 'sketch_id' (str): The sketch id
            - 'points_to_region_ids' (list): Each item is a dict with:
                - 'pt_xyz' (str): The test point
                - 'geo_id' (list): List of region ids matched (after disambiguation)
    """
    return query_sketch_profiles_contains(url, enriched_feature_summary, test_points_output)

if __name__ == "__main__":
    # Example usage for testing
    url = "https://cad.onshape.com/documents/34194a7792ea9db6d10188d3/w/2603dadfb9d5ccf8117390d0/e/140112c65afa2d3dddb074ba"
    
    # First we need to get the enriched feature summary
    from app.utils.onshape_tools import _onshape_url_to_enriched_feature_summary_logic
    tool_output = _onshape_url_to_enriched_feature_summary_logic(url)
    
    if isinstance(tool_output, str):
        print(f"Error getting enriched feature summary: {tool_output}")
        exit(1)
    
    enriched_feature_summary = tool_output.get("enriched_feature_summaries", [])
    
    # Example test points output (this would normally come from test_points.py)
    test_points_output = [
        {
            "sketch_id": "FT1DvSE7Alu8Ovc_0",
            "test_points": [[0.0, 0.12], [0.0, 0.0762], [-0.03175, 0.01905], [0.03175, 0.01905]]
        }
    ]
    
    result = define_sketch_entities(url, test_points_output, enriched_feature_summary)
    print("Sketch entities definition result:")
    print(result)
