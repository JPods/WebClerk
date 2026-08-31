import importlib

__all__ = ["transaction_flow"]


def __getattr__(name: str):
    if name == "transaction_flow":
        return importlib.import_module("apps.transactions.services.transaction_flow")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")