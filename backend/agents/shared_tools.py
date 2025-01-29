from typing import Dict, Any, Callable, Optional
from dataclasses import dataclass

@dataclass
class SharedTool:
    name: str
    description: str
    method: Callable[..., Any]
    parameters: Dict[str, str]
    agent_type: str

class ToolRegistry:
    """Centralized registry for all agent tools"""
    _instance = None
    _tools: Dict[str, SharedTool] = {}  # Class variable to store tools
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # Initialize instance attributes
            cls._instance._tools = {}
        return cls._instance
    
    @property
    def tools(self) -> Dict[str, SharedTool]:
        """Get the tools dictionary"""
        return self._tools
    
    @tools.setter
    def tools(self, value: Dict[str, SharedTool]):
        """Set the tools dictionary"""
        self._tools = value

    def register_tool(self, 
                     name: str, 
                     description: str, 
                     method: Callable[..., Any], 
                     parameters: Dict[str, str],
                     agent_type: str) -> None:
        """Register a tool in the global registry"""
        tool_id = f"{agent_type}_{name}"
        self._tools[tool_id] = SharedTool(
            name=name,
            description=description,
            method=method,
            parameters=parameters,
            agent_type=agent_type
        )
    
    def get_tool(self, tool_id: str) -> Optional[SharedTool]:
        """Get a tool from the registry. Returns None if tool not found."""
        return self._tools.get(tool_id)
    
    def get_tools_by_agent(self, agent_type: str) -> Dict[str, SharedTool]:
        """Get all tools registered by a specific agent type"""
        return {
            k: v for k, v in self._tools.items() 
            if v.agent_type == agent_type
        }
    
    def get_all_tools(self) -> Dict[str, SharedTool]:
        """Get all registered tools"""
        return self._tools