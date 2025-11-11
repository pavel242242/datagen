"""Datacruncher: Multi-persona data quality analysis with DuckDB."""

from .analyzer import DataCruncher, AnalysisConfig
from .report import CrunchReport, Issue, Metrics
from .personas import (
    Persona,
    AnalysisQuery,
    get_persona,
    list_personas,
    PERSONA_REGISTRY,
    VP_GROWTH,
    DATA_ENGINEER,
    FINANCE_VP,
    CUSTOMER_SUCCESS_VP,
)

__all__ = [
    "DataCruncher",
    "AnalysisConfig",
    "CrunchReport",
    "Issue",
    "Metrics",
    "Persona",
    "AnalysisQuery",
    "get_persona",
    "list_personas",
    "PERSONA_REGISTRY",
    "VP_GROWTH",
    "DATA_ENGINEER",
    "FINANCE_VP",
    "CUSTOMER_SUCCESS_VP",
]
