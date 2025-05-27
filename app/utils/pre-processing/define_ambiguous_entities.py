import sys
import os

# Calculate the project root directory based on the current script's location
# This script is in app/utils/pre-processing, so we need to go up three levels
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.utils.queries import standard_api_request, endpoints, query_sketch_profiles_contains
from app.utils.parsing import feature_parser, extract_feature_summaries, enrich_feature_summaries

from app.utils.queries import define_ambiguous_entities

def define_ambiguous_entities_wrapper(url: str, enriched_feature_summary: list, ambiguous_entity_ids: list) -> list:
    """
    Wrapper function to call the define_ambiguous_entities function from queries.py.
    
    Args:
        url (str): The URL of the Onshape document.
        enriched_feature_summary (list): The enriched feature summary containing entity information.
        ambiguous_entity_ids (list): List of entity IDs that need definitions (output from identify_ambiguous_entities).
    
    Returns:
        list: The enriched_feature_summary with definitions added for all matched entities.
    """
    return define_ambiguous_entities(url, ambiguous_entity_ids, enriched_feature_summary)

if __name__ == "__main__":
    # Example usage for testing
   
    test_onshape_url = "https://cad.onshape.com/documents/34194a7792ea9db6d10188d3/w/2603dadfb9d5ccf8117390d0/e/140112c65afa2d3dddb074ba"
    test_onshape_url_2 = "https://cad.onshape.com/documents/34194a7792ea9db6d10188d3/w/2603dadfb9d5ccf8117390d0/e/ed0327add99ecf3427274439"
    test_onshape_url_3 = "https://cad.onshape.com/documents/34194a7792ea9db6d10188d3/w/2603dadfb9d5ccf8117390d0/e/8e8fe9de5851db99112d3500"
    
    params = {'rollbackBarIndex': -1, 'noSketchGeometry': 'false'}

    # # Step 1: Get and parse features
    response = standard_api_request(
            test_onshape_url,
            endpoints['features'],
            method='GET',
            params=params
        )
    new_parsed_features_data = feature_parser(response)
    new_feature_summaries = extract_feature_summaries(new_parsed_features_data)
    new_enriched_summaries_data = enrich_feature_summaries(new_feature_summaries, test_onshape_url)

    print("Here is the new_enriched_summaries_data: ", new_enriched_summaries_data)
    
    
    # Example ambiguous entity IDs (this would normally come from identify_ambiguous_entities)
    ambiguous_entity_ids = ['IB', 'JDC', 'JGO', 'JHK', 'KIlC']
    
    result = define_ambiguous_entities_wrapper(test_onshape_url, new_enriched_summaries_data, ambiguous_entity_ids)
    print("Ambiguous entities definition result:")
    import json
    print(json.dumps(result, indent=2))
