import os
import json
from dotenv import load_dotenv
from datetime import datetime
from app.core.commands import WriteCommand
from app.utils.onshape_tools import _onshape_url_to_enriched_feature_summary_logic
from openai import AsyncOpenAI
import asyncio
import traceback

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4.1-mini"

class OnshapeChat(WriteCommand):
    """
    Command to answer user questions about an Onshape Part Studio using the enriched feature summary
    as context, via the OpenAI Chat Completions endpoint.
    """

    def __init__(self, user_query: str, part_studio_url: str, history=None):
        """
        Args:
            user_query (str): The user's question about the part studio.
            part_studio_url (str): The Onshape Part Studio URL.
            history (list, optional): List of previous messages (dicts with 'role' and 'content').
        """
        self.user_query = user_query
        self.part_studio_url = part_studio_url
        self.history = history or []
        self.model = OPENAI_MODEL

    async def execute(self) -> dict:
        print(f"[{datetime.now()}] ***** OnshapeChat.execute() ENTERED *****")
        start_time = datetime.now()
        actual_enriched_summary_for_llm = None
        parsed_features_for_llm = None # For parsed features
        enriched_summary_tool_output = None
        char_counts = {}

        try:
            print(f"[{datetime.now()}] Attempting to call _onshape_url_to_enriched_feature_summary_logic via asyncio.to_thread")
            enriched_summary_tool_output = await asyncio.to_thread(
                _onshape_url_to_enriched_feature_summary_logic, self.part_studio_url
            )
            print(f"[{datetime.now()}] _onshape_url_to_enriched_feature_summary_logic completed.")

            if isinstance(enriched_summary_tool_output, str):
                print(f"[{datetime.now()}] Tool returned an error string: {enriched_summary_tool_output}")
                return {
                    "error": f"Failed to get enriched feature summary (tool error): {enriched_summary_tool_output}",
                    "response": None,
                    "enriched_feature_summary": None,
                    "history": self.history,
                    "total_time_seconds": (datetime.now() - start_time).total_seconds(),
                    "char_counts": char_counts
                }
            
            actual_enriched_summary_for_llm = enriched_summary_tool_output.get("enriched_feature_summaries")
            parsed_features_for_llm = enriched_summary_tool_output.get("feature_parser_output") # Extract parsed features
            
            char_counts = {
                "enriched_feature_summaries_char_count": enriched_summary_tool_output.get("enriched_feature_summaries_char_count"),
                "feature_list_dict_char_count": enriched_summary_tool_output.get("feature_list_dict_char_count"),
                "feature_parser_output_char_count": enriched_summary_tool_output.get("feature_parser_output_char_count"),
                "extract_feature_summaries_output_char_count": enriched_summary_tool_output.get("extract_feature_summaries_output_char_count"),
            }
            print(f"[{datetime.now()}] Populated char_counts: {char_counts}")

            if actual_enriched_summary_for_llm is None or parsed_features_for_llm is None:
                 missing_keys = []
                 if actual_enriched_summary_for_llm is None: missing_keys.append("'enriched_feature_summaries'")
                 if parsed_features_for_llm is None: missing_keys.append("'feature_parser_output'")
                 error_msg = f"{', '.join(missing_keys)} key(s) not found in tool output or is None."
                 print(f"[{datetime.now()}] {error_msg}")
                 return {
                    "error": error_msg,
                    "response": None,
                    "enriched_feature_summary": None, 
                    "history": self.history,
                    "total_time_seconds": (datetime.now() - start_time).total_seconds(),
                    "char_counts": char_counts
                }

        except Exception as e:
            print(f"\n!!!! EXCEPTION in OnshapeChat.execute() during/after asyncio.to_thread for summary logic: {type(e).__name__}: {e} !!!!")
            print("Full traceback:")
            traceback.print_exc()
            return {
                "error": f"Failed during feature summary processing: {type(e).__name__} - {e}",
                "response": None,
                "enriched_feature_summary": None,
                "history": self.history,
                "total_time_seconds": (datetime.now() - start_time).total_seconds(),
                "char_counts": char_counts
            }

        system_prompt = (
            "You are a helpful assistant knowledgeable about Onshape Part Studios. "
            "You are provided with detailed parsed feature data and an enriched feature summary of a Part Studio. "
            "Use this information to answer the user's question as precisely as possible, "
            "explaining the geometry, features, and relationships in detail. "
            "If the information does not contain enough detail to answer a specific aspect, "
            "state what is missing and what is known."
        )

        messages = [{"role": "system", "content": system_prompt}]
        # Construct the context message string
        context_content = (
            f"Here is the data for the Part Studio at {self.part_studio_url}:\n\n"
            f"Parsed Features Data:\n{json.dumps(parsed_features_for_llm, indent=2)}\n\n"
            f"Enriched Feature Summary:\n{json.dumps(actual_enriched_summary_for_llm, indent=2)}"
        )
        messages.append({"role": "user", "content": context_content})
        
        for msg in self.history:
            if "role" in msg and "content" in msg:
                messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": self.user_query})

        answer = None
        try:
            client = AsyncOpenAI()
            print(f"[{datetime.now()}] Attempting to call OpenAI ChatCompletion with new API...")
            # Log the message length before sending to OpenAI
            prompt_char_count = sum(len(json.dumps(m)) for m in messages)
            print(f"[{datetime.now()}] Approximate characters in prompt to OpenAI: {prompt_char_count}")

            response_openai = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.2,
                max_tokens=1024,
            )
            answer = response_openai.choices[0].message.content
            print(f"[{datetime.now()}] OpenAI call successful. Answer received.")
        except Exception as e:
            print(f"\n!!!! EXCEPTION during OpenAI API call: {type(e).__name__}: {e} !!!!")
            print("Full traceback for OpenAI API call exception:")
            traceback.print_exc()
            return {
                "error": f"OpenAI API call failed: {type(e).__name__} - {e}",
                "response": None,
                "enriched_feature_summary": actual_enriched_summary_for_llm,
                "history": self.history,
                "total_time_seconds": (datetime.now() - start_time).total_seconds(),
                "char_counts": char_counts
            }

        updated_history = self.history + [
            {"role": "user", "content": self.user_query},
            {"role": "assistant", "content": answer}
        ]
        total_time = (datetime.now() - start_time).total_seconds()
        print(f"[{datetime.now()}] OnshapeChat.execute() completed successfully. Total time: {total_time:.2f}s")
        print(f"[{datetime.now()}] Returning char_counts: {char_counts}")
        return {
            "response": answer,
            "enriched_feature_summary": actual_enriched_summary_for_llm,
            "parsed_features": parsed_features_for_llm,
            "history": updated_history,
            "total_time_seconds": total_time,
            "char_counts": char_counts
        }
