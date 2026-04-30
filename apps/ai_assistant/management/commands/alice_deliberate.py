"""
alice_deliberate — Alice's multi-LLM deliberative loop

Three-stage hallucination probe inside WebClerk:
  Stage 1 — Reasoner  (deepseek-r1:8b)  : makes the claim
  Stage 2 — Adversary (athena-reason)   : probes for hallucinations and overreach
  Stage 3 — Judge     (llama3.2)        : adjudicates, produces final verdict

Alice writes the result as:
  - A WC3 Setting record (document pointer) in the allie project
  - A WC3 Action record if the verdict implies follow-up
  - A corpus entry in ~/Allie/training/corpus.jsonl

Usage:
  python manage.py alice_deliberate --prompt "Should Alice index product codes by supplier prefix?"
  python manage.py alice_deliberate --alice-pending   # deliberate on open alice_pending items
  python manage.py alice_deliberate --prompt "..." --rounds 2
  python manage.py alice_deliberate --dry-run --prompt "..."

The deliberation output is saved to ~/Allie/thoughts/ and a pointer is
created in WC3. The verdict is printed to stdout.
"""

import json
import sys
import datetime
import pathlib
import urllib.request
import urllib.error
import time

from django.core.management.base import BaseCommand

ALLIE      = pathlib.Path("/Users/williamjames/Allie")
OLLAMA_URL = "http://localhost:11434/api/generate"
SCRIPTS    = ALLIE / "scripts"

DEFAULT_REASONER  = "deepseek-r1:8b"
DEFAULT_ADVERSARY = "athena-reason:latest"
DEFAULT_JUDGE     = "llama3.2:latest"

# WC3 project IDs
PROJECT_ALLIE       = 25   # allie — active operating work
PROJECT_ALLIE_WHATIF = 24  # allie-whatif — hypotheses


# ── Ollama ────────────────────────────────────────────────────────────────────

def call_ollama(prompt: str, model: str, timeout: int) -> tuple:
    start = time.time()
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.3, "num_predict": 2048},
    }).encode()
    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read())
            return body.get("response", "").strip(), time.time() - start, None
    except urllib.error.URLError as e:
        return "", time.time() - start, str(e)
    except Exception as e:
        return "", time.time() - start, str(e)


# ── Role prompts (Alice-specific context) ─────────────────────────────────────

def prompt_reasoner(question: str) -> str:
    return f"""\
You are Alice — the database and pattern-recognition agent inside WebClerk3.
You are not a general assistant. You govern search indexing, keyword denormalization,
pattern detection across user behavior, and alice_pending coordination notes.

Your task: produce the best synthesis or answer to the question below.
Be specific. Name models, fields, endpoints, and patterns by name.
State your assumptions. Do not hedge without reason.
This output will be scrutinized by an adversarial model.

Question:
{question}
"""


def prompt_adversary(question: str, claim: str) -> str:
    return f"""\
You are the adversarial observer in a three-stage deliberation inside WebClerk3.
Your job: probe the claim below for hallucinations, contradictions, and overreach.

WebClerk3 invariants you know:
- Alice governs search, keywords, and alice_pending notes. Allie governs the person.
- Allie does not write WebClerk schema or queue config — that is Alice's domain.
- Every durable follow-up (actions, WhatIf, unresolved diagnostics) belongs in WC3, not in prose.
- The sovereignty rule: sovereign data stays local (CarryOn), collaborative data lives in WebClerk.
- Nothing is deleted — compensating transaction pattern (dt_completed: 0 = open).

How to probe:
- Quote the exact phrase you are challenging.
- State what is wrong and why.
- If the claim is sound, say so — false alarms waste time.

Original question:
{question}

Claim:
{claim}
"""


def prompt_judge(question: str, claim: str, critique: str) -> str:
    return f"""\
You are the adjudicator in a three-stage deliberation inside WebClerk3.

For each critique point: rule whether it stands or fails (one sentence).
Then produce a revised synthesis incorporating valid critique points.
State your final verdict: SUBSTANTIALLY CORRECT | PARTIALLY CORRECT | SUBSTANTIALLY WRONG.
Be specific. Evidence and logic only.

Original question:
{question}

Reasoner's claim:
{claim}

Adversary's critique:
{critique}
"""


# ── WC3 writes via Alice's token ──────────────────────────────────────────────

def wc_write(endpoint: str, payload: dict, token: str) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"http://localhost:8000{endpoint}",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}


def get_alice_token() -> str | None:
    try:
        sys.path.insert(0, str(SCRIPTS))
        from allie_wc_token import get_token
        return get_token("alice")
    except Exception as e:
        return None


def save_to_wc3(title: str, path: str, summary: str, token: str,
                project_id: int = PROJECT_ALLIE) -> int | None:
    result = wc_write("/wcapi/save/", {
        "model_name": "document",
        "name":        title,
        "body":        summary,
        "description": summary[:255],
        "path":        {"local": path},
        "status":      "active",
        "data": {
            "agent":      "alice",
            "project_id": project_id,
            "dt_created": datetime.datetime.now().isoformat(),
        },
    }, token)
    return result.get("data", {}).get("id") or result.get("id")


def create_followup_action(title: str, description: str, token: str,
                           project_id: int = PROJECT_ALLIE) -> int | None:
    result = wc_write("/wcapi/save/", {
        "model_name": "action",
        "action_en": title,
        "description_en": description,
        "project_id": project_id,
        "kanban_column": "Backlog",
        "priority": 2,
    }, token)
    return result.get("data", {}).get("id") or result.get("id")


def log_to_corpus(prompt: str, verdict: str, verified: bool = False):
    try:
        sys.path.insert(0, str(SCRIPTS))
        from allie_corpus_log import CorpusLog
        CorpusLog().add(
            agent="alice",
            domain="webclerk",
            prompt=prompt,
            response=verdict,
            verified=verified,
            tags=["deliberation", "alice"],
        )
    except Exception:
        pass


# ── Command ───────────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = "Alice three-stage LLM deliberative loop — hallucination probe"

    def add_arguments(self, parser):
        src = parser.add_mutually_exclusive_group(required=True)
        src.add_argument("--prompt",        help="Question or claim to deliberate on")
        src.add_argument("--alice-pending", action="store_true",
                         help="Deliberate on open alice_pending items from WC3")

        parser.add_argument("--reasoner",  default=DEFAULT_REASONER)
        parser.add_argument("--adversary", default=DEFAULT_ADVERSARY)
        parser.add_argument("--judge",     default=DEFAULT_JUDGE)
        parser.add_argument("--rounds",    type=int, default=1, choices=[1, 2])
        parser.add_argument("--timeout",   type=int, default=300)
        parser.add_argument("--project-id", type=int, default=PROJECT_ALLIE)
        parser.add_argument("--dry-run",   action="store_true")
        parser.add_argument("--no-wc3",    action="store_true",
                            help="Skip WC3 writes (useful when WC3 is unreachable)")

    def handle(self, *args, **options):
        dry_run   = options["dry_run"]
        no_wc3    = options["no_wc3"]
        reasoner  = options["reasoner"]
        adversary = options["adversary"]
        judge     = options["judge"]
        timeout   = options["timeout"]
        project_id = options["project_id"]

        # Resolve question
        if options["alice_pending"]:
            question = self._gather_pending_question()
        else:
            question = options["prompt"]

        self.stdout.write(f"[alice_deliberate] {datetime.date.today().isoformat()}")
        self.stdout.write(f"  reasoner={reasoner}  adversary={adversary}  judge={judge}")
        self.stdout.write(f"  Prompt: {question[:100]}{'...' if len(question) > 100 else ''}\n")

        if dry_run:
            self.stdout.write("── DRY RUN — prompts only ──────────────────────────────────")
            self.stdout.write(prompt_reasoner(question))
            return

        # Stage 1 — Reasoner
        self.stdout.write(f"  [Stage 1 — Reasoner] {reasoner}...", ending=" ")
        self.stdout.flush()
        claim, elapsed, error = call_ollama(prompt_reasoner(question), reasoner, timeout)
        if error:
            self.stderr.write(f"ERROR: {error}")
            sys.exit(1)
        self.stdout.write(f"{elapsed:.0f}s | {len(claim)} chars")

        # Stage 2 — Adversary
        self.stdout.write(f"  [Stage 2 — Adversary] {adversary}...", ending=" ")
        self.stdout.flush()
        critique, elapsed, error = call_ollama(prompt_adversary(question, claim), adversary, timeout)
        if error:
            self.stderr.write(f"ERROR: {error}")
            sys.exit(1)
        self.stdout.write(f"{elapsed:.0f}s | {len(critique)} chars")

        # Stage 3 — Judge
        self.stdout.write(f"  [Stage 3 — Judge] {judge}...", ending=" ")
        self.stdout.flush()
        verdict, elapsed, error = call_ollama(prompt_judge(question, claim, critique), judge, timeout)
        if error:
            self.stderr.write(f"ERROR: {error}")
            sys.exit(1)
        self.stdout.write(f"{elapsed:.0f}s | {len(verdict)} chars")

        # Optional round 2
        if options["rounds"] == 2:
            self.stdout.write(f"  [Round 2 — Adversary] {adversary}...", ending=" ")
            self.stdout.flush()
            adv2_prompt = f"Judge's verdict:\n{verdict}\n\nOriginal question:\n{question}\n\nDoes the verdict introduce new problems or miss something you flagged? Be specific or confirm it's sound."
            critique2, elapsed, error = call_ollama(adv2_prompt, adversary, timeout)
            if not error:
                self.stdout.write(f"{elapsed:.0f}s")
                self.stdout.write(f"  [Round 2 — Judge] {judge}...", ending=" ")
                self.stdout.flush()
                verdict2, elapsed, error = call_ollama(
                    prompt_judge(question, verdict, critique2), judge, timeout)
                if not error:
                    verdict = verdict2
                    self.stdout.write(f"{elapsed:.0f}s")

        # Write output file
        date_str = datetime.date.today().isoformat()
        ts_str   = datetime.datetime.now().strftime("%H%M%S")
        thoughts_dir = ALLIE / "thoughts"
        thoughts_dir.mkdir(parents=True, exist_ok=True)
        out_path = thoughts_dir / f"{date_str}-alice-deliberate-{ts_str}.md"

        lines = [
            f"# Alice Deliberation — {date_str} {ts_str[:2]}:{ts_str[2:4]}:{ts_str[4:]}",
            f"*Reasoner: {reasoner} | Adversary: {adversary} | Judge: {judge}*",
            "", "---", "",
            "## Question", "", question, "",
            "---", "", f"## Stage 1 — Reasoner ({reasoner})", "", claim, "",
            "---", "", f"## Stage 2 — Adversary ({adversary})", "", critique, "",
            "---", "", f"## Stage 3 — Judge ({judge}) — Final Verdict", "", verdict, "",
        ]
        out_path.write_text("\n".join(lines))
        self.stdout.write(f"\n  Written: {out_path}")

        # WC3 writes
        if not no_wc3:
            token = get_alice_token()
            if token:
                # Document pointer
                setting_id = save_to_wc3(
                    title=f"Alice deliberation {date_str}: {question[:60]}",
                    path=str(out_path),
                    summary=verdict[:500],
                    token=token,
                    project_id=project_id,
                )
                self.stdout.write(f"  WC3 document pointer: setting id={setting_id}")

                # If verdict suggests follow-up, create an action
                verdict_lower = verdict.lower()
                if any(w in verdict_lower for w in ["should", "needs", "must", "follow", "action", "next step"]):
                    action_id = create_followup_action(
                        title=f"Follow-up: {question[:80]}",
                        description=f"Alice deliberation verdict:\n\n{verdict[:800]}",
                        token=token,
                        project_id=project_id,
                    )
                    self.stdout.write(f"  WC3 action created: id={action_id}")
            else:
                self.stdout.write("  WC3: token unavailable — skipping writes")

        # Corpus
        log_to_corpus(question, verdict, verified=False)
        self.stdout.write("  Corpus entry logged.")

        # Print verdict
        self.stdout.write(f"\n{'─'*60}")
        self.stdout.write("FINAL VERDICT")
        self.stdout.write('─'*60)
        self.stdout.write(verdict)

    def _gather_pending_question(self) -> str:
        """Pull open alice_pending items and form a deliberation question."""
        try:
            from apps.ai_assistant.models import Message
            # Read recent pending notes from WC3 via internal query
            token = get_alice_token()
            if not token:
                return "What are the highest-priority open alice_pending items and what should be done about them?"
            req = urllib.request.Request(
                "http://localhost:8000/wcapi/ai/report/?category=pending&days=14",
                headers={"Authorization": f"Bearer {token}"},
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
            items = data.get("data", []) if isinstance(data, dict) else data
            if not items:
                return "No open alice_pending items found. Is the pattern recognition system producing observations?"
            lines = ["Open alice_pending items (last 14 days):"]
            for item in items[:10]:
                body = item.get("body", "")[:100]
                role = item.get("role", "")
                lines.append(f"- [{role}] {body}")
            lines.append("\nFor each item: should it be promoted to a Setting feature, added as a WhatIf, or resolved? What is the correct action?")
            return "\n".join(lines)
        except Exception as e:
            return f"Analyze open alice_pending items in WebClerk3. Error fetching them: {e}"
