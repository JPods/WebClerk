from functools import wraps


def allow_write(view):
    """Mark a view as allowed to perform write operations.

    This sets a flag inspected by WriteGateMiddleware so POST/PUT/PATCH/DELETE
    can pass for this view even if not on the default allowlist.

    Usage:
        @allow_write
        def my_view(request): ...

        @allow_write
        class MyApiView(APIView): ...
    """
    if isinstance(view, type):  # class-based view decorator
        setattr(view, '_allow_write', True)
        return view

    @wraps(view)
    def _wrapped(*args, **kwargs):
        # Also set request flag to be extra-safe in nested dispatch flows
        request = args[1] if args and len(args) > 1 else None
        if request is not None:
            setattr(request, '_write_gate_bypass', True)
        return view(*args, **kwargs)

    setattr(_wrapped, '_allow_write', True)
    return _wrapped
