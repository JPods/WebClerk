"""
secret_guard — one detector for passwords, keys and tokens typed into shared places.

Every agent calls this before text becomes readable by anyone else:
Alice (WebClerk saves, chat), Allie (teach/observe/remember), Andi (nightly sweep
of stored text), Athena (git pre-commit and the daily canary check).

Rules this module keeps:
  - It never returns, logs or raises with the secret itself. Findings carry a
    kind, the label that introduced it, a two-character hint and the length.
  - It has no dependencies (stdlib only) so Allie's scripts and Andi's cron
    import the same file WebClerk does. One detector, not four.
  - It prefers blocking over guessing: a false positive costs the user one
    rephrase; a false negative puts a live credential in a shared store.

Usage:
    from apps.core.utils.secret_guard import scan, correction, redact
    findings = scan(text)
    if findings:
        return error(correction(findings, where="this note"))
"""
from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass

# ── High-confidence shapes: the value alone is enough ────────────────────────

_SHAPES = [
    ("anthropic_key", r"sk-ant-[A-Za-z0-9_\-]{20,}"),
    ("openai_key", r"sk-(?:proj-)?[A-Za-z0-9_\-]{32,}"),
    ("stripe_key", r"(?:sk|rk)_(?:live|test)_[A-Za-z0-9]{16,}"),
    ("aws_access_key", r"(?:AKIA|ASIA)[0-9A-Z]{16}"),
    ("github_token", r"(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}"),
    ("gitlab_token", r"glpat-[A-Za-z0-9_\-]{20,}"),
    ("slack_token", r"xox[baprs]-[A-Za-z0-9\-]{10,}"),
    ("google_api_key", r"AIza[0-9A-Za-z_\-]{35}"),
    ("private_key", r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----"),
    ("jwt", r"eyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"),
    ("url_credentials", r"[a-z][a-z0-9+.\-]*://[^/\s:@]{1,64}:[^/\s@]{3,128}@[^\s/]+"),
    ("bearer_token", r"(?i:bearer)\s+[A-Za-z0-9_\-.=+/]{24,}"),
    ("django_hash", r"(?:pbkdf2_sha256|argon2|bcrypt_sha256)\$[^\s\"']{20,}"),
]
_SHAPE_RE = [(k, re.compile(p)) for k, p in _SHAPES]

# ── Label → value: "password is X", "wifi key: X", "PASS=X" ─────────────────

_LABELS = (
    r"pass(?:word|wd|code|phrase)?|pwd|pw|pin|passkey"
    r"|wi-?fi\s+(?:password|key|pass)|wpa2?\s*(?:key|password|psk)?|pre-?shared\s+key|psk"
    r"|secret(?:\s+key)?|api[\s_\-]?key|access[\s_\-]?key|auth[\s_\-]?token|token"
    r"|client[\s_\-]?secret|credentials?|login"
)
_LABEL_RE = re.compile(
    r"(?P<label>\b(?:[A-Za-z]+[_\-])*(?:" + _LABELS + r")(?:[_\-][A-Za-z]+)*\b)"
    r"[\"']?(?P<sep>\s*(?:is|was|=|:|->|→|to|of)\s*|\s+)(?:set\s+to\s+|now\s+)?"
    r"[\"'`]?(?P<value>[^\s\"'`<>,;]{6,128})",
    re.IGNORECASE,
)

# Values that follow a label but are not secrets.
_PLACEHOLDER_RE = re.compile(
    r"^(?:\$\(|`|os\.|getenv|config\(|settings\.|env\[|process\.env|\$\{?[A-Z_][A-Z0-9_]*\}?|\{\{.*\}\}|%\(.*\)s|env:|vault:|keychain:|op://"
    r"|x{3,}|\*{2,}|•{3,}|\.{3,}|your|(?-i:[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+$)|<|\[|redacted|changeme$|example|placeholder|none$|null$)",
    re.IGNORECASE,
)
# A value built from these words is an instruction, not a secret: "generate-a-random-key-here".
_PLACEHOLDER_WORDS = {"generate", "random", "your", "here", "replace", "insert", "change", "changeme",
                      "example", "sample", "dummy", "fake", "placeholder", "todo", "fixme", "secret", "key"}
# Labels with these suffixes name a place or a setting, not a credential: token_url, api_key_setting.
_NON_SECRET_LABEL_SUFFIX = re.compile(
    r"(?i)[_\-](?:url|uri|endpoint|path|setting|settings|name|id|ids|field|fields|type|length|header|"
    r"expiry|expires|ttl|policy|hint|label|prompt|format|method|mode|required|reset|manager|count|scope|scopes|"
    r"type|kind|file|dir|backup|endpoint|view|views|serializer|model|table|column|class|fn|func|"
    r"guard|gate|sweep|scan|scanner|canary|check|rule|rules|store|vault|rotation|leak|leaks)$")
# Short, everyday words ("pass to X", "credentials to Athena", "login page") only count
# as a label when followed by = : or "is" — never by "to", "of" or a bare space.
_AMBIGUOUS_LABELS = {"pass", "pw", "pin", "login", "token", "credential", "credentials", "secret"}
_STRICT_SEP = re.compile(r"^\s*(?:=|:|is|was)\s*$", re.IGNORECASE)
# Network interface names sit next to "wifi" constantly: wlp132s0f0, enp131s0, wlan0.
_IFACE_RE = re.compile(r"^(?:wlp|enp|eno|ens|eth|wlan|wlx|br|veth|docker|tailscale|utun|en|wl)\d[a-z0-9]*$")

_STOPWORDS = {
    "required", "reset", "resets", "field", "fields", "protected", "manager", "managers",
    "change", "changed", "changes", "changing", "below", "above", "here", "hidden",
    "blank", "empty", "expired", "policy", "policies", "strength", "length", "rules",
    "rotation", "rotated", "please", "should", "must", "never", "always", "because",
    "authentication", "authenticated", "settings", "setting", "config", "configured",
    "missing", "invalid", "incorrect", "correct", "prompt", "prompts", "enter", "entered",
    "users", "account", "accounts", "access", "different", "somewhere", "instead",
    "updated", "update", "twice", "again", "whatever", "something", "provided",
    "stored", "encrypted", "hashed", "unusable", "disabled", "enabled", "validation",
    "management", "command", "commands", "matches", "mismatch", "request", "requests",
    "section", "without", "through", "between", "before", "after", "during", "within",
    "authorization", "authorized", "expires", "refresh", "rotate", "revoke", "revoked",
}


# Passwords known to have been published. Stored as SHA-256 so this public file does not
# publish them again. Any word-like token whose hash matches is blocked on sight.
# A leaked password that is also project vocabulary (a tool or host name) cannot be
# matched as a bare word without blocking ordinary talk; rotate it instead of listing it.
_KNOWN_LEAKED_SHA256 = {
    "7c1771271a1e3953d7b9073e44fc5817434175597fe96d5455d9db8f7272651c",
    "89d6f2878f320b612a335dd0ff8eec11d340460256b581023bc587964d08d8c5",
}
_WORDISH_RE = re.compile(r"(?<![\w@.])[A-Za-z0-9!#%&*+\-_]{6,64}(?![\w@])")


@dataclass(frozen=True)
class Finding:
    kind: str       # e.g. "password", "anthropic_key"
    label: str      # the word that introduced it ("" for shape matches)
    hint: str       # first two characters only
    length: int
    start: int
    end: int

    def describe(self) -> str:
        name = self.label or self.kind.replace("_", " ")
        return f"{name} ({self.hint}…, {self.length} chars)"


def _entropy(s: str) -> float:
    if not s:
        return 0.0
    counts = {c: s.count(c) for c in set(s)}
    return -sum(n / len(s) * math.log2(n / len(s)) for n in counts.values())


def _looks_like_secret_value(v: str) -> bool:
    v = v.rstrip(".!?)]}")
    if v[:1] in "([{" or len(v) < 6 or _PLACEHOLDER_RE.search(v):
        return False
    if re.search(r"\w\(|\)$|^(?:self|cls|request|settings|os|kwargs|args)\.|^(?:True|False|None)$", v):
        return False  # code: pw = bool(strong), token = request.headers...
    if v.startswith("/") or re.fullmatch(r"[\w.\-]+/[\w./\-]*", v):
        return False  # a path: token_url: /wcapi/token/
    parts = [p for p in re.split(r"[\-_.]", v.lower()) if p]
    if len(parts) > 1 and all(p.isalpha() for p in parts) and _PLACEHOLDER_WORDS & set(parts):
        return False
    if v.lower() in _STOPWORDS:
        return False
    if re.fullmatch(r"https?://\S+", v) and "@" not in v:
        return False  # a URL after "login:" is a location, not a secret
    has_digit = any(c.isdigit() for c in v)
    has_alpha = any(c.isalpha() for c in v)
    has_symbol = any(not c.isalnum() for c in v)
    mixed_case = any(c.isupper() for c in v) and any(c.islower() for c in v)
    # Plain lowercase dictionary-looking words ("manager", "protected") are not secrets;
    # anything with a digit, symbol, mixed case, or high entropy is treated as one.
    if has_digit and has_alpha:
        return True
    if has_symbol or mixed_case:
        return _entropy(v) >= 2.5
    return len(v) >= 12 and _entropy(v) >= 3.2


def scan(text: str | None) -> list[Finding]:
    """Return findings for anything in text that looks like a credential. Never the value."""
    if not text or not isinstance(text, str):
        return []
    found: list[Finding] = []
    taken: list[tuple[int, int]] = []

    def overlaps(a: int, b: int) -> bool:
        return any(a < e and b > s for s, e in taken)

    for m in _WORDISH_RE.finditer(text):
        v = m.group(0)
        if hashlib.sha256(v.encode()).hexdigest() in _KNOWN_LEAKED_SHA256:
            found.append(Finding("known_leaked_password", "", v[:2], len(v), m.start(), m.end()))
            taken.append((m.start(), m.end()))

    for kind, rx in _SHAPE_RE:
        for m in rx.finditer(text):
            if overlaps(m.start(), m.end()):
                continue
            v = m.group(0)
            found.append(Finding(kind, "", v[:2], len(v), m.start(), m.end()))
            taken.append((m.start(), m.end()))

    for m in _LABEL_RE.finditer(text):
        v = m.group("value").rstrip(".!?)]}")
        s, e = m.start("value"), m.start("value") + len(v)
        strong = re.search(r"(?i)pass(?:word|wd|code|phrase)?\b|pwd|psk|wpa", m.group("label"))
        digits_pw = bool(strong) and re.fullmatch(r"\d{6,}", v) and re.search(r"[=:]|\bis\b", m.group("sep"))
        if overlaps(s, e) or not (digits_pw or _looks_like_secret_value(v)):
            continue
        if _NON_SECRET_LABEL_SUFFIX.search(m.group("label")):
            continue
        if re.fullmatch(r"[0-9a-f]{7,40}", v) and not re.search(r"(?i)pass|pwd|pw\b|pin|wi-?fi|psk|wpa", m.group("label")):
            continue  # "secret: 8fb88f7e" is a commit hash; a hex value after "password" still blocks
        if m.group("label").strip().lower() in _AMBIGUOUS_LABELS and not (
                _STRICT_SEP.match(m.group("sep")) and any(c.isdigit() for c in v) and any(c.isalpha() for c in v)):
            continue
        if re.fullmatch(r"[a-z]+", v) and not re.search(r"[=:]", m.group("sep")):
            continue  # prose: "the password was simultaneously ..." — a bare lowercase word after is/was/to
        if not m.group("sep").strip() and not (any(c.isdigit() for c in v) and any(c.isalpha() for c in v)):
            continue  # "Pre-Shared Key and click" — bare whitespace needs a letters+digits value
        label = re.sub(r"\s+", " ", m.group("label").strip().lower())
        found.append(Finding("password", label, v[:2], len(v), s, e))
        taken.append((s, e))

    # Proximity: "keytone423volt  where do I change the password" — the value comes
    # before the word, or is separated from it. A letters+digits token of 10+ chars
    # within 100 chars of a password word is treated as the password.
    for kw in _NEARBY_KEYWORD_RE.finditer(text):
        lo, hi = max(0, kw.start() - 100), min(len(text), kw.end() + 100)
        for m in _NEARBY_TOKEN_RE.finditer(text, lo, hi):
            v = m.group(0)
            if overlaps(m.start(), m.end()) or re.fullmatch(r"[0-9a-fA-F]+", v):
                continue  # hex = commit hashes, ids
            if sum(c.isalpha() for c in v) < 3 or sum(c.isdigit() for c in v) < 1:
                continue
            if re.fullmatch(r"[A-Z0-9]+", v) or _IFACE_RE.match(v):
                continue  # model numbers, SKUs (RTAC86U), interface names (wlp132s0f0)
            found.append(Finding("password", kw.group(0).lower(), v[:2], len(v), m.start(), m.end()))
            taken.append((m.start(), m.end()))

    return sorted(found, key=lambda f: f.start)


_NEARBY_KEYWORD_RE = re.compile(r"(?i)\b(?:pass(?:word|wd|code|phrase)?|wi-?fi|psk|wpa2?|credentials?)\b")
_NEARBY_TOKEN_RE = re.compile(r"(?<![\w\-./@])[A-Za-z0-9]{10,64}(?![\w\-./@])")


def scan_obj(obj, _path: str = "") -> list[tuple[str, Finding]]:
    """Scan every string leaf of a dict/list (JSON envelopes). Returns (path, finding)."""
    out: list[tuple[str, Finding]] = []
    if isinstance(obj, str):
        out += [(_path, f) for f in scan(obj)]
    elif isinstance(obj, dict):
        for k, v in obj.items():
            key_path = f"{_path}.{k}" if _path else str(k)
            # A bare credential under a credential-named key: {"password": "hunter22"}
            if (isinstance(v, str) and not _NON_SECRET_LABEL_SUFFIX.search(str(k))
                    and re.fullmatch(r"(?i)(?:\w*[_\-])?(?:" + _LABELS + r")(?:[_\-]\w*)?", str(k))):
                if _looks_like_secret_value(v) and not scan(v):
                    out.append((key_path, Finding("password", str(k).lower(), v[:2], len(v), 0, len(v))))
                    continue
            out += scan_obj(v, key_path)
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            out += scan_obj(v, f"{_path}[{i}]")
    return out


def redact(text: str) -> str:
    """Replace each finding with ‹redacted:kind›. For logs that must keep the surrounding text."""
    if not text:
        return text
    for f in reversed(scan(text)):
        text = text[: f.start] + f"‹redacted:{f.kind}›" + text[f.end :]
    return text


def correction(findings, where: str = "here") -> str:
    """The one message every agent gives. Plain, specific, and says what to do next."""
    items = [f[1] if isinstance(f, tuple) else f for f in findings]
    what = ", ".join(sorted({f.describe() for f in items}))
    return (
        f"Not saved: that looks like a password or key — {what}. "
        f"Passwords never go in {where} or anywhere other people or agents can read: "
        "anyone who can see it can use it. Keep it in your password manager and refer to it "
        "by name instead (\"the JPods WiFi password\"). If it was a real password, change it "
        "now — it has already been typed somewhere it could be copied."
    )
