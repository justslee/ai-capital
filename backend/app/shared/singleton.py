"""Utility for creating singleton instances."""
from typing import TypeVar, Type, Dict, Any

T = TypeVar('T')

_instances: Dict[Type, Any] = {}

def get_singleton(cls: Type[T], *args, **kwargs) -> T:
    """Get or create a singleton instance of the given class."""
    if cls not in _instances:
        _instances[cls] = cls(*args, **kwargs)
    return _instances[cls]