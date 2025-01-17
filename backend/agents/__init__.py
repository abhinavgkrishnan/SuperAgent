"""
Agents package initializer.
Exposes all agent classes for easy import and provides version information.
"""

from .base_agent import BaseAgent
from .thesis_agent import ThesisAgent
from .twitter_agent import TwitterAgent
from .super_agent import SuperAgent
from .serper_agent import SerperAgent
from .financial_agent import FinancialReportAgent
from .data_analysis_agent import DataAnalysisAgent
from .product_description_agent import ProductDescriptionAgent

__version__ = "1.0.0"
__author__ = "AI Content Generator Team"

# Export all agent classes for easier imports
__all__ = [
    "BaseAgent",
    "ThesisAgent",
    "TwitterAgent", 
    "SuperAgent",
    "SerperAgent",
    "FinancialReportAgent",
    "DataAnalysisAgent",
    "ProductDescriptionAgent"
]