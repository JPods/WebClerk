"""secret_guard: must block what users actually type, and leave ordinary talk about passwords alone.

Positive cases are drawn from 2026-09-16, when a WiFi password, a database password and a
new router password each ended up somewhere shared. Values here are fake.
"""
import pytest

from apps.core.utils.secret_guard import correction, redact, scan, scan_obj

BLOCK = [
    # typed into a chat, value before the word
    "zephyr482ridge  where do I change the password in Asus RT-AC86U?",
    # env-style lines copied into a readme
    "LOCAL_DATABASE_PASS=quartz7Lantern",
    "DB_PASSWORD: 'mapleRiver_2024'",  # gitleaks:allow — invented fixture
    # natural language
    "the new wifi password is Summer2026!",
    "My password is hunter2hunter2",
    "wifi key: correcthorse99",
    "set the PSK to Blue-Heron-44",
    # vendor key shapes
    "use sk-ant-api03-" + "A" * 40,
    "AKIA" + "ABCDEFGHIJKLMNOP",
    "ghp_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8",
    "postgres://webclerk:s3cretPass@localhost:5432/commerce_expert",
    "Authorization: Bearer " + "abcDEF123456ghiJKL789012mno",
    "-----BEGIN OPENSSH PRIVATE KEY-----",
    "pbkdf2_sha256$870000$abcdefghijklmnop$qrstuvwxyz0123456789",
]

ALLOW = [
    "Password reset required for all portal users",
    "Keep it in your password manager",
    "LOCAL_DATABASE_PASS=<set on Andi — never in docs>",
    "LOCAL_DATABASE_PASS=${DB_PASS}",
    "token_url: /wcapi/token/",
    "Run changepassword for bill.james@jpods.com",
    "The router is an Asus RT-AC86U on firmware 386.5_2",
    "commit 8fb88f7e1c04cf1d is on origin/main; password rotation pending",
    "Go to Wireless → General → WPA Pre-Shared Key and click Apply",
    "api_key_setting: wchq_api_key",
    "The password field is hidden",
    "Login page: https://webclerk.com/admin/login/",
    "SECRET_KEY=generate-a-random-key-here",
    "PIN 1234",
]


@pytest.mark.parametrize("text", BLOCK)
def test_blocks(text):
    assert scan(text), f"missed: {text!r}"


@pytest.mark.parametrize("text", ALLOW)
def test_allows(text):
    assert not scan(text), f"false positive: {text!r} -> {[f.describe() for f in scan(text)]}"


def test_findings_never_carry_the_secret():
    secret = "quartz7Lantern"
    f = scan(f"LOCAL_DATABASE_PASS={secret}")[0]
    assert secret not in f.describe()
    assert secret not in correction([f], where="this note")
    assert f.hint == "qu" and f.length == len(secret)


def test_redact_keeps_context():
    out = redact("the new wifi password is Summer2026! thanks")
    assert "Summer2026" not in out and out.startswith("the new wifi password is ‹redacted:")


def test_json_envelopes():
    hits = scan_obj({"config": {"password": "hunter2hunter2", "host": "andi"}, "notes": ["ok"]})
    assert [p for p, _ in hits] == ["config.password"]
    assert not scan_obj({"config": {"token_url": "/wcapi/token/", "api_key_setting": "claude_api"}})


# Calibrated 2026-09-16 against 1,840 Allie readmes/handoffs/sessions: these were false positives.
CALIBRATED_ALLOW = [
    "TOKEN=$(python3 ~/Allie/scripts/allie_wc_token.py)",
    "harvest.py correlation pass: sameday lessons",
    "rules in Setting, read in useDataBrowser, pass to DataGrid",
    "WEBHOOK_SECRET = os.environ['WEBHOOK_SECRET']",
    'SECRET_KEY = os.getenv("SECRET_KEY")',
    '"token_scope": "carryon:read"',
    "export all credentials to AthenaVault",
    "wifis:\n    wlp132s0f0:\n      access-points:",
    "reconnected on wifi: wlp132s0f0 192.168.1.122",
]


@pytest.mark.parametrize("text", CALIBRATED_ALLOW)
def test_calibrated_allows(text):
    assert not scan(text), f"false positive: {text!r} -> {[f.describe() for f in scan(text)]}"


def test_real_doc_leaks_still_blocked():
    assert scan('network={\n    ssid="JPods"\n    psk="Pinecone2020ab"\n}')
    assert scan("| WiFi Password | `Pinecone2020ab` |")
    assert scan("DATABASE_URL=postgresql://webclerk:Tr0ub4dor@localhost:5432/commerce_expert")


def test_placeholders_and_ambiguous_words():
    assert not scan('network={\n    ssid="NETWORK_NAME"\n    psk="NETWORK_PASSWORD"\n}')
    assert not scan('psk="YourWiFiPassword"')
    assert not scan("Username/password: **see password manager**")
    assert not scan("Signs: Nothing yet (session token is Athena's)")
    assert scan("ssh pi@raspberrypi.local  # password: 1234abcd")


def test_known_leaked_passwords_blocked_without_being_in_source():
    import hashlib, pathlib
    import apps.core.utils.secret_guard as sg
    leaked = [w for w in ("pass" + "1111", "1111" + "pass")]
    for w in leaked:
        assert hashlib.sha256(w.encode()).hexdigest() in sg._KNOWN_LEAKED_SHA256
        assert scan(f"login with `{w}`")
    src = pathlib.Path(sg.__file__).read_text()
    assert not any(w in src for w in leaked)


def test_prose_and_tool_names_pass():
    assert not scan("one reused password was simultaneously a readme example and the WiFi key")
    assert not scan("call the leftshoe MCP first; log_session after each action")
    assert scan("DB_PASSWORD=simultaneously")  # explicit assignment still blocks


def test_names_and_hashes_pass():
    assert not scan("deployed on branch andi-secret-guard (8fb88f7 + 4 guard commits)")
    assert not scan("secret: 8fb88f7e1c04")  # hex id after a label


def test_digit_only_passwords_after_explicit_labels():
    assert scan("Pi password: `482913`")
    assert scan("the new password is 90817263")
    assert not scan("PIN 1234")
    assert not scan("password reset for 482913 users")  # no = : or 'is'


def test_code_assignments_pass():
    assert not scan("digits_pw = bool(strong) and re.fullmatch(r'x', v)")
    assert not scan("token = request.headers.get('Authorization')")
    assert not scan("password = None")
