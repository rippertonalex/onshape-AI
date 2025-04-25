from app.controllers.controller import Controller
from app.commands import (
    OnShapeAgent
    )


class OpenShapeController(Controller):   
    def onshape_agent(self, user_query: str) -> OnShapeAgent:
        return self.executor.execute_write(OnShapeAgent(user_query))
    
    
    
    
    
    
    
    