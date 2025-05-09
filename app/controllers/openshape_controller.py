from typing import List, Dict
from app.controllers.controller import Controller
from app.commands import (
    OnShapeAgent,
    OnshapeChat
    )
import logging

logger = logging.getLogger(__name__)

class OpenShapeController(Controller):   
    async def onshape_agent(self, user_query: str, history: List[Dict[str, str]] = None) -> OnShapeAgent:
        logger.info(f"Executing onshape_agent command for query: {user_query}")
        return await self.executor.execute_write(OnShapeAgent(user_query, history))
    
    async def onshape_chat(self, user_query: str, part_studio_url: str, history: List[Dict[str, str]] = None) -> OnshapeChat:
        logger.info(f"Executing onshape_chat command for URL: {part_studio_url} Query: {user_query}")
        try:
            command_instance = OnshapeChat(user_query, part_studio_url, history)
            logger.info("OnshapeChat command instance created successfully.")
            result = await self.executor.execute_write(command_instance)
            logger.info("executor.execute_write called successfully for OnshapeChat.")
            return result
        except Exception as e:
            logger.exception(f"Error during onshape_chat controller execution or command init: {e}")
            raise
    
    
    
    
    
    
    