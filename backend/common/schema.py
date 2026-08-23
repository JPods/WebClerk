import re
from drf_spectacular.openapi import AutoSchema
from common.schema_whitelist import WHITELIST


class WhitelistAutoSchema(AutoSchema):
    """AutoSchema that only includes endpoints whose path matches WHITELIST patterns.

    If WHITELIST is empty, falls back to default behavior (include all).
    """

    def _should_include(self, path: str) -> bool:
        if not WHITELIST:
            return True
        return any(re.match(pat, path) for pat in WHITELIST)

    # Hook into path processing
    def _get_paths_dict(self):
        paths = super()._get_paths_dict()
        if not WHITELIST:
            return paths
        return {p: v for p, v in paths.items() if self._should_include(p)}
