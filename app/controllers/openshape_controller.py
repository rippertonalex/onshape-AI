from typing import List, Dict
from app.controllers.controller import Controller
from app.commands import (
    OnShapeAgent
    )


class OpenShapeController(Controller):   
    def onshape_agent(self, user_query: str, history: List[Dict[str, str]] = None) -> OnShapeAgent:
        return self.executor.execute_write(OnShapeAgent(user_query, history))
    
    
    
    
    
    
    
    