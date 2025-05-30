import os
import json
from dotenv import load_dotenv
from datetime import datetime
from app.core.commands import WriteCommand
from app.utils.onshape_tools import _onshape_url_to_enriched_feature_summary_logic
from openai import AsyncOpenAI
import asyncio
import traceback
from app.utils.queries import standard_api_request, endpoints
from app.utils.parsing import feature_parser, extract_feature_summaries, enrich_feature_summaries
import json
from openai import AsyncOpenAI
from dotenv import load_dotenv
import asyncio # Ensure asyncio is imported
import re
from app.utils.pre_processing.identify_ambigous_entities import identify_ambigous_entities
from app.utils.pre_processing.test_points import generate_sketch_test_points
from app.utils.pre_processing.define_sketch_entities import define_sketch_entities
from app.utils.pre_processing.define_ambiguous_entities import define_ambiguous_entities_wrapper
from app.utils.pre_processing.visualize_geometery import visualize_workspace_geometry

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4.1-nano"

class PreProcessing(WriteCommand):
    """
    Command to answer user questions about an Onshape Part Studio using the enriched feature summary
    as context, via the OpenAI Chat Completions endpoint.
    """

    def __init__(self, part_studio_url: str, history=None):
        """
        Args:
            user_query (str): The user's question about the part studio.
            part_studio_url (str): The Onshape Part Studio URL.
            history (list, optional): List of previous messages (dicts with 'role' and 'content').
        """
        self.part_studio_url = part_studio_url
        self.history = history or []
        self.model = OPENAI_MODEL

    async def execute(self) -> dict:

        params = {'rollbackBarIndex': -1, 'noSketchGeometry': 'false'}

        
        response = standard_api_request(
            self.part_studio_url,
            endpoints['features'],
            method='GET',
            params=params
        )
        new_parsed_features_data = feature_parser(response)
        new_feature_summaries = extract_feature_summaries(new_parsed_features_data)
        new_enriched_summaries_data = enrich_feature_summaries(new_feature_summaries, self.part_studio_url)

        ambiguous_entity_ids = await identify_ambigous_entities(new_parsed_features_data, new_enriched_summaries_data)

        test_points_result = await generate_sketch_test_points(new_parsed_features_data, ambiguous_entity_ids)

        # Convert single dict to list format expected by define_sketch_entities
        test_points_list = [test_points_result] if test_points_result and not isinstance(test_points_result, list) else test_points_result

        defined_sketch_entities = define_sketch_entities(self.part_studio_url, test_points_list, new_enriched_summaries_data)

        enriched_summary_with_definitions = define_ambiguous_entities_wrapper(self.part_studio_url, new_enriched_summaries_data, ambiguous_entity_ids)

        visualized_geometry = await visualize_workspace_geometry(enriched_summary_with_definitions, new_parsed_features_data)


        return {"visualized_summary": visualized_geometry, "enriched_summary": enriched_summary_with_definitions, "defined_sketch_entities": defined_sketch_entities, "parsed_features": new_parsed_features_data}