"""Dynamic registry for layout optimization algorithms."""

import logging
from typing import Any, Callable, Dict, List, Optional, Type
from app.algorithms.base import BaseLayoutAlgorithm

logger = logging.getLogger(__name__)


class AlgorithmRegistry:
    """Central registry for layout optimization algorithms.
    
    Allows plug-and-play registration of new algorithms (CORELAP, CRAFT, GA, etc.)
    without modifying the core dispatcher.
    """

    _registry: Dict[str, Type[BaseLayoutAlgorithm]] = {}

    @classmethod
    def register(cls, name_or_class: Optional[Any] = None) -> Any:
        """Decorator or direct method to register an algorithm class in the global registry.
        
        Usage:
            @AlgorithmRegistry.register
            class MyAlgorithm(BaseLayoutAlgorithm): ...
            
            # Or with explicit name:
            @AlgorithmRegistry.register("my_algorithm")
            class MyAlgorithm(BaseLayoutAlgorithm): ...
        """

        def decorator(subclass: Type[BaseLayoutAlgorithm]) -> Type[BaseLayoutAlgorithm]:
            if not issubclass(subclass, BaseLayoutAlgorithm):
                raise TypeError(f"Class '{subclass.__name__}' must inherit from BaseLayoutAlgorithm.")
            
            # Determine registration key
            key = (name_or_class if isinstance(name_or_class, str) else getattr(subclass, "_name_override", None))
            if not key:
                try:
                    # Instantiate temporarily or use dummy inspection if name is property
                    temp = subclass.__new__(subclass)
                    key = getattr(temp, "name", subclass.__name__.lower())
                except Exception:
                    key = subclass.__name__.lower()
            
            cls._registry[key.lower()] = subclass
            logger.info("Registered layout algorithm: %s -> %s", key, subclass.__name__)
            return subclass

        if isinstance(name_or_class, type) and issubclass(name_or_class, BaseLayoutAlgorithm):
            return decorator(name_or_class)

        return decorator

    @classmethod
    def get(cls, name: str, parameters: Optional[Dict[str, Any]] = None) -> BaseLayoutAlgorithm:
        """Instantiate an algorithm instance by its registered name."""
        key = name.lower()
        if key not in cls._registry:
            raise KeyError(
                f"Algorithm '{name}' is not registered. Available: {list(cls._registry.keys())}"
            )
        algorithm_cls = cls._registry[key]
        return algorithm_cls(parameters=parameters)

    @classmethod
    def list_available(cls) -> List[Dict[str, Any]]:
        """List summary metadata for all registered algorithms."""
        result: List[Dict[str, Any]] = []
        seen_classes = set()
        for key, alg_cls in cls._registry.items():
            if alg_cls in seen_classes:
                continue
            seen_classes.add(alg_cls)
            try:
                instance = alg_cls()
                result.append(instance.metadata)
            except Exception:
                result.append({"name": key, "class": alg_cls.__name__})
        return result

    @classmethod
    def clear(cls) -> None:
        """Clear the registry (useful for test isolation)."""
        cls._registry.clear()


register_algorithm = AlgorithmRegistry.register
