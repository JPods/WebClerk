from typing import Callable, Dict, List, Optional

_SEEDERS: Dict[str, Callable[[int, dict], List[int]]] = {}

def register_seeder(model_label: str):
    """
    Usage:
      @register_seeder("communications.Domain")
      def seed_domain(per: int, ctx: dict) -> List[int]: ...
    """
    def _wrap(fn: Callable[[int, dict], List[int]]):
        _SEEDERS[model_label] = fn
        return fn
    return _wrap

def get_seeders() -> Dict[str, Callable[[int, dict], List[int]]]:
    return dict(_SEEDERS)