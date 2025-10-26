"""
Adjudication Agent Package

Provides standalone adjudication of exceptions using learned playbook rules.
"""

from .exception_parser import ExceptionParser
from .playbook_loader import PlaybookLoader

__all__ = ['ExceptionParser', 'PlaybookLoader']

# Lazy import of AdjudicationAgent to avoid requiring google package at import time
def get_runner():
    """Lazy import of AdjudicationAgent."""
    from .adjudication_runner import AdjudicationAgent
    return AdjudicationAgent

__all__.append('get_runner')

