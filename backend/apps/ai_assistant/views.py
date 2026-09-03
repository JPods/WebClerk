"""
AI Assistant API views.

Endpoints:
    POST /wcapi/ai/ask/       — ask a question (RAG-powered, mode-aware)
    POST /wcapi/ai/debug/     — analyze an error/traceback
    POST /wcapi/ai/review/    — review code for convention compliance
    POST /wcapi/ai/generate/  — generate code or tests
    POST /wcapi/ai/feedback/  — submit feedback on an answer
    GET  /wcapi/ai/health/    — system health check
    GET  /wcapi/ai/history/   — conversation history for current user
    GET  /wcapi/ai/modes/     — list available AI modes
    POST /wcapi/ai/reindex/   — trigger reindexing (staff only)

    Upstream (any WC3 can serve these for downstream instances):
    POST /wcapi/alice/ask/         — downstream escalation to this instance's Alice
    POST /wcapi/alice/ask-claude/  — downstream escalation with Claude (professional tier)
"""
import json
import logging

from django.core.management import call_command
from django.http import StreamingHttpResponse, JsonResponse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.views import APIView

from common.api_responses import api_response
from .models import Conversation, Message
from .services.rag import RAGService
from .services.notes import (
    create_note,
    resolve_pending,
    get_report,
    log_search_feedback,
    CATEGORY_PURPOSE_MAP,
    VALID_ROLES,
)

logger = logging.getLogger(__name__)


class AskView(APIView):
    """
    POST /wcapi/ai/ask/
    Body: {
        "question": "...",
        "conversation_id": null,
        "context_page": "",
        "mode": "general",           # general|developer|debugger|user_support|code_review|test_writer
        "extra_context": "",          # optional: paste traceback, code, etc.
        "stream": false
    }
    """
    permission_classes = [IsAuthenticated]

    VALID_MODES = {"general", "developer", "debugger", "user_support", "code_review", "test_writer"}

    def post(self, request):
        question = request.data.get("question", "").strip()
        if not question:
            return api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Question is required",
                error_code="missing_question",
            )

        conversation_id = request.data.get("conversation_id")
        context_page = request.data.get("context_page", "")
        mode = request.data.get("mode", "general")
        extra_context = request.data.get("extra_context", "")
        do_stream = request.data.get("stream", False)

        # Validate mode
        if mode not in self.VALID_MODES:
            mode = "general"

        # Get or create conversation
        if conversation_id:
            try:
                conversation = Conversation.objects.get(
                    pk=conversation_id, user=request.user
                )
            except Conversation.DoesNotExist:
                conversation = None

        if not conversation_id or conversation is None:
            conversation = Conversation.objects.create(
                user=request.user,
                context_page=context_page,
            )

        # Build history from conversation
        history = []
        for msg in conversation.messages.all()[:20]:  # last 20 messages
            history.append({"role": msg.role, "content": msg.content})

        # Save user message
        Message.objects.create(
            conversation=conversation,
            role="user",
            content=question,
        )

        rag = RAGService()

        if do_stream:
            return self._stream_response(rag, question, history, conversation, mode, extra_context)

        # Non-streaming response
        try:
            result = rag.ask(question, history=history, mode=mode, extra_context=extra_context)
        except ConnectionError as e:
            return api_response(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=str(e),
                error_code="ollama_unavailable",
            )
        except Exception as e:
            logger.exception("AI ask failed")
            return api_response(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="AI generation failed",
                error_code="generation_error",
            )

        # Save assistant message
        msg = Message.objects.create(
            conversation=conversation,
            role="assistant",
            content=result["answer"],
            sources=result["sources"],
        )

        return api_response(data={
            "answer": result["answer"],
            "sources": result["sources"],
            "model": result["model"],
            "mode": result.get("mode", mode),
            "conversation_id": conversation.pk,
            "message_id": msg.pk,
            "confidence": result.get("confidence"),
            "tier_used": result.get("tier_used", "alice_local"),
            "escalation_log": result.get("escalation_log", []),
        })

    def _stream_response(self, rag, question, history, conversation, mode="general", extra_context=""):
        """Return a streaming response for real-time output."""

        def event_stream():
            try:
                stream, sources = rag.ask_stream(
                    question, history=history, mode=mode, extra_context=extra_context
                )
                full_answer = []

                for chunk in stream:
                    full_answer.append(chunk)
                    yield f"data: {json.dumps({'chunk': chunk})}\n\n"

                # Save the complete answer
                answer_text = "".join(full_answer)
                Message.objects.create(
                    conversation=conversation,
                    role="assistant",
                    content=answer_text,
                    sources=sources,
                )

                yield f"data: {json.dumps({'done': True, 'sources': sources, 'conversation_id': conversation.pk})}\n\n"

            except ConnectionError as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
            except Exception as e:
                logger.exception("Streaming AI ask failed")
                yield f"data: {json.dumps({'error': 'Generation failed'})}\n\n"

        response = StreamingHttpResponse(
            event_stream(),
            content_type="text/event-stream",
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


class FeedbackView(APIView):
    """
    POST /wcapi/ai/feedback/
    Body: {"message_id": 123, "feedback": 1}   # 1=helpful, -1=not helpful
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        message_id = request.data.get("message_id")
        feedback = request.data.get("feedback")

        if not message_id or feedback not in (1, -1):
            return api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="message_id and feedback (1 or -1) required",
                error_code="invalid_feedback",
            )

        try:
            msg = Message.objects.get(
                pk=message_id,
                conversation__user=request.user,
                role="assistant",
            )
        except Message.DoesNotExist:
            return api_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Message not found",
                error_code="not_found",
            )

        msg.feedback = feedback
        msg.save(update_fields=["feedback"])

        return api_response(data={"message_id": msg.pk, "feedback": feedback})


class HealthView(APIView):
    """
    GET /wcapi/ai/health/
    Public health check for the AI subsystem.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        rag = RAGService()
        health = rag.health_check()
        return api_response(data=health)


class DiagnoseView(APIView):
    """
    GET  /wcapi/ai/diagnose/  — Full Alice diagnostic for Andi device manager.
    POST /wcapi/ai/diagnose/  — Run a specific remediation action.

    GET returns a structured report of every Alice subsystem with ok/fail
    and a remediation hint for each failure. Andi reads this to decide
    what to fix instead of blindly restarting everything.

    POST body: {"action": "migrate" | "restart_celery" | "pull_model" | "reindex"}
    Runs the specified remediation and returns the result.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        checks = {}
        actions = []

        # 1. Ollama model
        checks['ollama'] = self._check_ollama()
        if not checks['ollama']['ok']:
            actions.append('pull_model')

        # 2. Chroma vector store
        checks['chroma'] = self._check_chroma()
        if not checks['chroma']['ok']:
            actions.append('reindex')

        # 3. Celery tasks registered
        checks['celery_tasks'] = self._check_celery_tasks()
        if not checks['celery_tasks']['ok']:
            actions.append('restart_celery')

        # 4. Beat schedule
        checks['beat_schedule'] = self._check_beat_schedule()

        # 5. Alice DB tables
        checks['alice_db'] = self._check_alice_db()
        if not checks['alice_db']['ok']:
            actions.append('migrate')

        # 6. Alice observations (is she producing output?)
        checks['alice_activity'] = self._check_alice_activity()

        all_ok = all(c['ok'] for c in checks.values())

        return api_response(data={
            'status': 'ok' if all_ok else 'degraded',
            'checks': checks,
            'recommended_actions': actions,
        })

    def post(self, request):
        action = request.data.get('action', '')

        if action == 'migrate':
            return self._do_migrate()
        elif action == 'restart_celery':
            return self._do_restart_celery()
        elif action == 'reindex':
            return self._do_reindex()
        elif action == 'pull_model':
            return api_response(
                data={'message': 'Model pull must be done via ollama CLI'},
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        else:
            return api_response(
                data={'message': f'Unknown action: {action}. Valid: migrate, restart_celery, reindex'},
                status_code=status.HTTP_400_BAD_REQUEST,
            )

    # ── Check methods ─────────────────────────────────────────────

    def _check_ollama(self):
        try:
            from django.conf import settings
            import urllib.request
            configured = getattr(settings, 'OLLAMA_MODEL', 'unknown')
            base_url = getattr(settings, 'OLLAMA_BASE_URL', 'http://localhost:11434')
            resp = urllib.request.urlopen(f'{base_url}/api/tags', timeout=5)
            import json as _json
            data = _json.loads(resp.read())
            installed = [m['name'] for m in data.get('models', [])]
            if configured in installed:
                return {'ok': True, 'model': configured, 'installed': installed}
            return {
                'ok': False, 'model': configured, 'installed': installed,
                'hint': f'Model {configured} not installed. Run: ollama pull {configured}',
            }
        except Exception as e:
            return {'ok': False, 'error': str(e), 'hint': 'Ollama not responding'}

    def _check_chroma(self):
        try:
            rag = RAGService()
            stats = rag.vector_store.stats()
            if stats.get('count', 0) > 0:
                return {'ok': True, 'chunks': stats['count']}
            return {'ok': False, 'chunks': 0, 'hint': 'Vector store empty — run reindex'}
        except Exception as e:
            return {'ok': False, 'error': str(e), 'hint': 'Chroma not responding'}

    def _check_celery_tasks(self):
        expected = [
            'apps.ai_assistant.tasks.alice_schema_watch_task',
            'apps.ai_assistant.tasks.apply_pending_layouts_task',
            'apps.ai_assistant.tasks.data_cleanup_task',
            'apps.ai_assistant.tasks.health_scoring_task',
            'apps.ai_assistant.tasks.json_optimize_task',
            'apps.ai_assistant.tasks.layout_drift_task',
            'apps.ai_assistant.tasks.margin_tracking_task',
            'apps.ai_assistant.tasks.relationship_scan_task',
            'apps.ai_assistant.tasks.schema_drift_task',
            'apps.ai_assistant.tasks.velocity_task',
            'apps.ai_assistant.tasks.full_intelligence_run',
        ]
        try:
            from celery import current_app
            registered = current_app.control.inspect().registered()
            if not registered:
                return {'ok': False, 'hint': 'No Celery workers responding'}
            all_tasks = set()
            for worker_tasks in registered.values():
                all_tasks.update(worker_tasks)
            missing = [t for t in expected if t not in all_tasks]
            if missing:
                return {
                    'ok': False, 'missing': missing,
                    'hint': 'Tasks missing @shared_task decorator or Celery needs restart',
                }
            return {'ok': True, 'registered': len(all_tasks)}
        except Exception as e:
            return {'ok': False, 'error': str(e), 'hint': 'Cannot inspect Celery'}

    def _check_beat_schedule(self):
        from django.conf import settings as django_settings
        schedule = getattr(django_settings, 'CELERY_BEAT_SCHEDULE', {})
        alice_entries = {
            k: v['task'] for k, v in schedule.items()
            if 'ai_assistant' in v.get('task', '')
        }
        if len(alice_entries) < 3:
            return {
                'ok': False, 'count': len(alice_entries),
                'hint': 'Alice tasks not wired in CELERY_BEAT_SCHEDULE',
            }
        return {'ok': True, 'count': len(alice_entries), 'entries': alice_entries}

    def _check_alice_db(self):
        try:
            from .models.alice import AliceObservation, AliceCoachingLog, AliceInsight
            counts = {
                'observations': AliceObservation.objects.count(),
                'coaching_logs': AliceCoachingLog.objects.count(),
                'insights': AliceInsight.objects.count(),
            }
            return {'ok': True, **counts}
        except Exception as e:
            return {'ok': False, 'error': str(e), 'hint': 'Run: manage.py migrate'}

    def _check_alice_activity(self):
        """Check if Alice has produced any output in the last 24 hours."""
        try:
            import time
            from .models.alice import AliceObservation
            cutoff = int((time.time() - 86400) * 1000)  # epoch millis, 24h ago
            recent = AliceObservation.objects.filter(dt_created__gte=cutoff).count()
            if recent > 0:
                return {'ok': True, 'recent_24h': recent}
            total = AliceObservation.objects.count()
            return {
                'ok': False, 'recent_24h': 0, 'total': total,
                'hint': 'No observations in 24h — Alice may not be running her tasks',
            }
        except Exception as e:
            return {'ok': False, 'error': str(e)}

    # ── Remediation methods ───────────────────────────────────────

    def _do_migrate(self):
        try:
            call_command('migrate', '--run-syncdb', verbosity=0)
            return api_response(data={'action': 'migrate', 'result': 'ok'})
        except Exception as e:
            return api_response(
                data={'action': 'migrate', 'result': 'failed', 'error': str(e)},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _do_restart_celery(self):
        import subprocess
        try:
            result = subprocess.run(
                ['sudo', 'systemctl', 'restart', 'webclerk3-celery'],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                return api_response(data={'action': 'restart_celery', 'result': 'ok'})
            return api_response(
                data={'action': 'restart_celery', 'result': 'failed', 'error': result.stderr},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except Exception as e:
            return api_response(
                data={'action': 'restart_celery', 'result': 'failed', 'error': str(e)},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _do_reindex(self):
        try:
            call_command('reindex_vectors', verbosity=0)
            return api_response(data={'action': 'reindex', 'result': 'ok'})
        except Exception as e:
            return api_response(
                data={'action': 'reindex', 'result': 'failed', 'error': str(e)},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class DeviceStatusView(APIView):
    """
    GET  /wcapi/ai/device-status/  — Read current device health for dashboard.
    POST /wcapi/ai/device-status/  — Andi/Mac pushes device telemetry.

    Stored in Setting(purpose='device_status', parent_model='system').
    Dashboard reads GET; Andi/Mac scripts POST every 5 minutes.

    The stress_rating (1-5) is computed from the telemetry:
      1 = cool and quiet, 5 = critical.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        from apps.core.models import Setting
        setting = Setting.objects.filter(
            purpose='device_status',
        ).first()
        if not setting or not setting.config:
            return api_response(data={'status': 'no_data'})
        return api_response(data=setting.config)

    def post(self, request):
        from apps.core.models import Setting
        data = request.data
        if not data:
            return api_response(
                data={'error': 'No data provided'},
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Compute stress rating from telemetry
        data['stress_rating'] = self._compute_stress(data)
        data['dt_updated'] = _utc_now_iso()

        setting, created = Setting.objects.update_or_create(
            purpose='device_status',
            parent_model='system',
            defaults={
                'name': 'device_status:system',
                'config': data,
            },
        )

        return api_response(data={
            'stored': True,
            'stress_rating': data['stress_rating'],
            'created': created,
        })

    @staticmethod
    def _compute_stress(data):
        """Compute physical stress rating 1-5 from device telemetry.

        Factors: CPU temp, memory usage, disk usage, load average.
        Each factor scores 0-1, weighted sum maps to 1-5.
        """
        score = 0.0

        # CPU temp: 40°C=0, 90°C=1
        cpu_max = data.get('cpu_temp_max_c', 0)
        if cpu_max:
            score += max(0, min(1, (cpu_max - 40) / 50)) * 0.35

        # Memory: 20%=0, 95%=1
        mem_pct = data.get('memory_used_pct', 0)
        if mem_pct:
            score += max(0, min(1, (mem_pct - 20) / 75)) * 0.25

        # Disk: 50%=0, 95%=1
        disk_pct = data.get('disk_used_pct', 0)
        if disk_pct:
            score += max(0, min(1, (disk_pct - 50) / 45)) * 0.20

        # Load avg (per core): 0.5=0, 2.0=1
        load_1 = data.get('load_avg_1min', 0)
        cores = data.get('cpu_cores', 1)
        if load_1 and cores:
            per_core = load_1 / cores
            score += max(0, min(1, (per_core - 0.5) / 1.5)) * 0.20

        # Map 0-1 to 1-5
        rating = 1 + (score * 4)
        return round(rating, 1)


def _utc_now_iso():
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


class HistoryView(APIView):
    """
    GET /wcapi/ai/history/
    Returns the user's conversation list with recent messages.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        conversations = Conversation.objects.filter(
            user=request.user
        ).prefetch_related("messages")[:20]

        data = []
        for conv in conversations:
            msgs = conv.messages.all()[:5]
            data.append({
                "id": conv.pk,
                "context_page": conv.context_page,
                "dt_created": conv.dt_created.isoformat(),
                "messages": [
                    {
                        "id": m.pk,
                        "role": m.role,
                        "content": m.content[:200],
                        "feedback": m.feedback,
                        "dt_created": m.dt_created.isoformat(),
                    }
                    for m in msgs
                ],
            })

        return api_response(data={"conversations": data})


# ── Specialized endpoints ──────────────────────────────────────────


class DebugView(APIView):
    """
    POST /wcapi/ai/debug/
    Body: {"error": "traceback or error message", "file_context": "", "question": ""}

    Shortcut for ask with mode=debugger.
    Accepts a traceback/error directly and returns diagnosis + fix.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        error = request.data.get("error", "").strip()
        file_context = request.data.get("file_context", "")
        question = request.data.get("question", "").strip()

        if not error and not question:
            return api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Provide 'error' (a traceback) or 'question'",
                error_code="missing_input",
            )

        # Build the question for the debugger
        if error and not question:
            question = f"Analyze this error and suggest a fix:\n\n{error}"
        elif error:
            question = f"{question}\n\nError/traceback:\n{error}"

        rag = RAGService()
        try:
            result = rag.ask(
                question,
                mode="debugger",
                extra_context=file_context,
            )
        except ConnectionError as e:
            return api_response(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=str(e),
                error_code="ollama_unavailable",
            )

        return api_response(data={
            "diagnosis": result["answer"],
            "sources": result["sources"],
            "model": result["model"],
            "mode": "debugger",
        })


class ReviewView(APIView):
    """
    POST /wcapi/ai/review/
    Body: {"code": "...", "file_path": "relative/path.py", "question": ""}

    Reviews code against CommerceExpert conventions.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        code = request.data.get("code", "").strip()
        file_path = request.data.get("file_path", "")
        question = request.data.get("question", "").strip()

        if not code and not question:
            return api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Provide 'code' to review or a 'question'",
                error_code="missing_input",
            )

        review_prompt = question or "Review this code for CommerceExpert convention compliance."
        extra = ""
        if code:
            extra = f"File: {file_path}\n```\n{code}\n```"

        rag = RAGService()
        try:
            result = rag.ask(review_prompt, mode="code_review", extra_context=extra)
        except ConnectionError as e:
            return api_response(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=str(e),
                error_code="ollama_unavailable",
            )

        return api_response(data={
            "review": result["answer"],
            "sources": result["sources"],
            "model": result["model"],
            "mode": "code_review",
        })


class GenerateView(APIView):
    """
    POST /wcapi/ai/generate/
    Body: {
        "task": "test|code|migration",
        "description": "what to generate",
        "file_context": "",
        "target_file": ""
    }

    Generates code, tests, or migration plans following project conventions.
    """
    permission_classes = [IsAuthenticated]

    TASK_MODE_MAP = {
        "test": "test_writer",
        "code": "developer",
        "migration": "developer",
    }

    def post(self, request):
        task = request.data.get("task", "code")
        description = request.data.get("description", "").strip()
        file_context = request.data.get("file_context", "")
        target_file = request.data.get("target_file", "")

        if not description:
            return api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Provide a 'description' of what to generate",
                error_code="missing_description",
            )

        mode = self.TASK_MODE_MAP.get(task, "developer")
        extra = ""
        if file_context:
            extra = f"Target file: {target_file}\nExisting code context:\n{file_context}"

        rag = RAGService()
        try:
            result = rag.ask(description, mode=mode, extra_context=extra)
        except ConnectionError as e:
            return api_response(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=str(e),
                error_code="ollama_unavailable",
            )

        return api_response(data={
            "generated": result["answer"],
            "sources": result["sources"],
            "model": result["model"],
            "mode": mode,
            "task": task,
        })


class ModesView(APIView):
    """
    GET /wcapi/ai/modes/
    Returns the list of available AI assistant modes.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        return api_response(data={"modes": RAGService.available_modes()})


class ReindexView(APIView):
    """
    POST /wcapi/ai/reindex/
    Body: {"source": "all"}  # optional: readmes, models, services, views, etc.

    Triggers re-indexing of the knowledge base. Staff only.
    """
    permission_classes = [IsAdminUser]

    def post(self, request):
        source = request.data.get("source", "all")
        reset = request.data.get("reset", False)

        try:
            call_command("index_docs", source=source, reset=reset)
        except Exception as e:
            logger.exception("Reindex failed")
            return api_response(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Reindex failed: {e}",
                error_code="reindex_error",
            )

        # Return updated stats
        rag = RAGService()
        stats = rag.vector_store.stats()
        return api_response(data={
            "message": "Reindex complete",
            "source": source,
            "total_chunks": stats["count"],
        })


# ── Alice Notes ─────────────────────────────────────────────────────

class NoteView(APIView):
    """
    POST /wcapi/ai/note/
    Body: {
        "category": "pending" | "log",
        "role": "keyword_gap" | "search" | ...,
        "name": "Missing keyword field: phone",
        "parent_model": "customer",          // optional
        "details": { ... }                   // optional JSON payload
    }

    PATCH /wcapi/ai/note/
    Body: { "id": 123 }
    Resolves an alice_pending record (sets is_active=False).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        category = request.data.get("category", "").strip()
        role = request.data.get("role", "").strip()
        name = request.data.get("name", "").strip()

        if not category or not role or not name:
            return api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="category, role, and name are required",
                error_code="missing_fields",
            )

        try:
            setting = create_note(
                category,
                role=role,
                name=name,
                parent_model=request.data.get("parent_model"),
                details=request.data.get("details"),
            )
        except ValueError as exc:
            return api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=str(exc),
                error_code="invalid_note",
            )

        return api_response(
            status_code=status.HTTP_201_CREATED,
            data={
                "id": setting.pk,
                "name": setting.name,
                "purpose": setting.purpose,
                "role": setting.role,
                "parent_model": setting.parent_model,
            },
        )

    def patch(self, request):
        note_id = request.data.get("id")
        if not note_id:
            return api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="id is required",
                error_code="missing_id",
            )
        try:
            setting = resolve_pending(int(note_id))
        except Exception as exc:
            return api_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message=str(exc),
                error_code="not_found",
            )

        return api_response(data={
            "id": setting.pk,
            "is_active": setting.is_active,
            "resolved_at": setting.config.get("resolved_at"),
        })


class ReportView(APIView):
    """
    GET /wcapi/ai/report/
    Query params:
        category      — "pending" | "log" | omit for both
        days          — lookback window (default 30)
        parent_model  — filter to one model
        role          — filter to one role
        resolved      — "true" to include resolved pending items
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        category = request.query_params.get("category") or None
        days = int(request.query_params.get("days", "30"))
        parent_model = request.query_params.get("parent_model") or None
        role = request.query_params.get("role") or None
        include_resolved = request.query_params.get("resolved", "").lower() == "true"

        try:
            report = get_report(
                category,
                days=days,
                parent_model=parent_model,
                role=role,
                include_resolved=include_resolved,
            )
        except ValueError as exc:
            return api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=str(exc),
                error_code="invalid_params",
            )

        return api_response(data=report)


class SearchFeedbackView(APIView):
    """
    POST /wcapi/ai/search-feedback/
    Body: {
        "rating": 1 | -1,
        "query": "acm, @west",
        "parent_model": "customer",
        "result_count": 12,            // optional
        "coaching": "I was looking for Acme West division"  // optional
    }

    Always creates an alice_log (search_feedback).
    If rating is negative, also creates an alice_pending (keyword_gap).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        rating = request.data.get("rating")
        query = request.data.get("query", "").strip()
        parent_model = request.data.get("parent_model", "").strip()

        if rating not in (1, -1):
            return api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="rating must be 1 or -1",
                error_code="invalid_rating",
            )
        if not query or not parent_model:
            return api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="query and parent_model are required",
                error_code="missing_fields",
            )

        result = log_search_feedback(
            rating=rating,
            query=query,
            parent_model=parent_model,
            result_count=request.data.get("result_count", 0),
            coaching=request.data.get("coaching", ""),
            user_id=request.user.pk,
        )

        return api_response(
            status_code=status.HTTP_201_CREATED,
            data=result,
        )


# ── Upstream Alice endpoints ─────────────────────────────────────────
# Any WC3 instance can serve these for downstream installations.
# WCHQ is just a WC3 instance that happens to be upstream of others.


def _validate_athena_token(request):
    """Validate Authorization: Athena <token> against Connection records."""
    from apps.sync.models.connection import Connection

    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth_header.startswith('Athena '):
        return None, api_response(
            status_code=status.HTTP_401_UNAUTHORIZED,
            message="Missing or invalid Authorization header. Expected: Athena <token>",
            error_code="invalid_auth",
        )

    token = auth_header[7:].strip()
    if not token:
        return None, api_response(
            status_code=status.HTTP_401_UNAUTHORIZED,
            message="Empty Athena token",
            error_code="empty_token",
        )

    connections = Connection.objects.filter(status='active', is_active=True)
    for conn in connections:
        config = conn.config if isinstance(conn.config, dict) else {}
        if config.get('athena_token') == token:
            return conn, None

    return None, api_response(
        status_code=status.HTTP_403_FORBIDDEN,
        message="Athena token not recognized",
        error_code="invalid_token",
    )


def _log_upstream_exchange(connection, question, answer, tier_used, pii_count):
    """Log the exchange as an AliceObservation for audit."""
    try:
        from .models.alice import AliceObservation
        AliceObservation.objects.create(
            category='escalation',
            source='wchq',
            message=f"Upstream ask from {connection.name} — tier: {tier_used}",
            detail=(
                f"question: {question[:500]}\n"
                f"pii_scrubbed: {pii_count}\n"
                f"tier_used: {tier_used}"
            ),
            model_name='Connection',
            record_id=connection.pk,
        )
    except Exception as e:
        logger.warning("Failed to log upstream exchange: %s", e)


class AliceAskUpstreamView(APIView):
    """
    POST /wcapi/alice/ask/

    Upstream endpoint — downstream WC3 installations call this when
    escalating a low-confidence question. Any WC3 can be upstream.

    Auth: Authorization: Athena <token>
    """
    permission_classes = [AllowAny]

    def post(self, request):
        from .services.pii_scrub import scrub_pii

        connection, error_resp = _validate_athena_token(request)
        if error_resp:
            return error_resp

        question = request.data.get('question', '').strip()
        if not question:
            return api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Question is required",
                error_code="missing_question",
            )

        context_summary = request.data.get('context_summary', '')
        mode = request.data.get('mode', 'general')

        question, pii_count = scrub_pii(question)
        if context_summary:
            context_summary, ctx_pii = scrub_pii(context_summary)
            pii_count += ctx_pii

        try:
            rag = RAGService()
            result = rag.ask(
                question=question,
                mode=mode,
                extra_context=context_summary,
                escalate=False,
            )
        except Exception as e:
            logger.exception("Upstream Alice failed for %s", connection.name)
            return api_response(
                status_code=status.HTTP_502_BAD_GATEWAY,
                message=f"Alice processing error: {e}",
                error_code="alice_error",
            )

        answer = result.get('answer', '')
        _log_upstream_exchange(connection, question, answer, 'wchq_alice', pii_count)

        return api_response(data={
            'answer': answer,
            'model': result.get('model', ''),
            'tier_used': 'wchq_alice',
            'confidence': result.get('confidence', {}),
            'usage': {},
        })


class AliceAskClaudeUpstreamView(APIView):
    """
    POST /wcapi/alice/ask-claude/

    Upstream endpoint with Claude escalation. WCHQ (or any upstream WC3)
    holds the Claude API key centrally. Professional tier only.

    Auth: Authorization: Athena <token>
    """
    permission_classes = [AllowAny]

    CLAUDE_CONFIDENCE_THRESHOLD = 0.50

    def post(self, request):
        from .services.pii_scrub import scrub_pii

        connection, error_resp = _validate_athena_token(request)
        if error_resp:
            return error_resp

        config = connection.config if isinstance(connection.config, dict) else {}
        tier = config.get('subscription_tier', 'community')
        if tier != 'professional':
            return api_response(
                status_code=status.HTTP_403_FORBIDDEN,
                message="Claude escalation requires professional-tier subscription",
                error_code="tier_insufficient",
            )

        question = request.data.get('question', '').strip()
        if not question:
            return api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Question is required",
                error_code="missing_question",
            )

        local_answer = request.data.get('local_answer', '')
        context_summary = request.data.get('context_summary', '')
        mode = request.data.get('mode', 'general')

        question, pii_count = scrub_pii(question)
        if local_answer:
            local_answer, la_pii = scrub_pii(local_answer)
            pii_count += la_pii
        if context_summary:
            context_summary, ctx_pii = scrub_pii(context_summary)
            pii_count += ctx_pii

        # Tier 2: Try local Alice first
        try:
            rag = RAGService()
            result = rag.ask(
                question=question, mode=mode,
                extra_context=context_summary, escalate=False,
            )
        except Exception as e:
            logger.exception("Upstream Alice failed for %s", connection.name)
            return api_response(
                status_code=status.HTTP_502_BAD_GATEWAY,
                message=f"Alice processing error: {e}",
                error_code="alice_error",
            )

        alice_answer = result.get('answer', '')
        alice_score = result.get('confidence', {}).get('score', 0.0)
        tier_used = 'wchq_alice'
        answer = alice_answer
        model_used = result.get('model', '')
        usage = {}

        # Tier 3: Escalate to Claude if Alice is low-confidence
        if alice_score < self.CLAUDE_CONFIDENCE_THRESHOLD:
            try:
                answer, usage, model_used = self._ask_claude(
                    question, local_answer, alice_answer, context_summary, mode,
                )
                tier_used = 'wchq_claude'
            except Exception as e:
                logger.warning("Claude escalation failed for %s: %s", connection.name, e)

        _log_upstream_exchange(connection, question, answer, tier_used, pii_count)

        return api_response(data={
            'answer': answer,
            'model': model_used,
            'tier_used': tier_used,
            'usage': usage,
        })

    def _ask_claude(self, question, local_answer, alice_answer, context_summary, mode):
        """Call Claude API — key held centrally in Setting(purpose='wchq_claude_key')."""
        import anthropic
        from apps.core.models import Setting

        key_setting = Setting.objects.filter(
            purpose='wchq_claude_key', is_active=True,
        ).first()
        if not key_setting:
            raise ValueError("No wchq_claude_key Setting configured")

        config = key_setting.config if isinstance(key_setting.config, dict) else {}
        api_key = config.get('api_key', '')
        if not api_key:
            raise ValueError("wchq_claude_key has no api_key")

        model = config.get('model', 'claude-sonnet-4-5-20250514')

        system_prompt = (
            "You are Alice, a commerce assistant for WebClerk installations. "
            "A downstream installation asked a question that their local AI "
            "could not answer confidently. Provide a clear, accurate answer."
        )

        user_parts = [f"Question: {question}"]
        if local_answer:
            user_parts.append(f"\nDownstream local answer (low confidence):\n{local_answer}")
        if alice_answer:
            user_parts.append(f"\nUpstream Alice answer (also low confidence):\n{alice_answer}")
        if context_summary:
            user_parts.append(f"\nContext:\n{context_summary}")

        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model, max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": "\n".join(user_parts)}],
        )

        answer = response.content[0].text if response.content else ""
        usage = {
            'input_tokens': response.usage.input_tokens,
            'output_tokens': response.usage.output_tokens,
        }
        return answer, usage, model


# ── PII Parse & Correct ─────────────────────────────────────────────

class PiiParseView(APIView):
    """POST /wcapi/ai/pii/parse/ — parse text for PII candidates.

    Request:  {"text": "Call Bill James at 612-555-1234"}
    Response: {"candidates": [...], "scrubbed": "Call <name> at <phone>"}
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        text = (request.data.get('text') or '').strip()
        if not text:
            return api_response(error='text is required', status_code=400)

        from .services.pii_scrub import parse_pii, scrub_pii
        candidates = parse_pii(text)
        scrubbed, count = scrub_pii(text)

        return api_response(data={
            'candidates': candidates,
            'scrubbed': scrubbed,
            'pii_count': count,
            'original': text,
        })


class ContactParseView(APIView):
    """POST /wcapi/ai/contact/parse/ — parse pasted text into a contact grid.

    Request:  {"text": "Bill James, CEO, JPods Inc, 612-555-1234\\nJane Smith..."}
    Response: {"columns": [...], "rows": [...]}
    """
    permission_classes = [AllowAny]  # Tool served from same origin; CSRF protects

    def post(self, request):
        text = (request.data.get('text') or '').strip()
        source_label = (request.data.get('source_label') or '').strip()
        if not text:
            return api_response(error='text is required', status_code=400)

        from .services.contact_parser import parse_contact_text, log_import_episode
        result = parse_contact_text(text)

        # Log episode for Alice's learning
        if result.get('rows'):
            log_import_episode(result, source_label=source_label)

        return api_response(data=result)


class ContactDetectView(APIView):
    """POST /wcapi/ai/contact/detect/ — detect structure and propose column mapping.

    Step 1 of structured import. Returns header detection + mapping proposal.
    User confirms/adjusts, then calls /contact/parse-confirmed/.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        text = (request.data.get('text') or '').strip()
        if not text:
            return api_response(error='text is required', status_code=400)

        from .services.contact_parser import detect_structure, recall_import_pattern
        result = detect_structure(text)
        if not result:
            return api_response(data={'structured': False})

        # Check if Alice recognizes this column pattern from a previous import
        header_fp = '|'.join(c.get('header', '') for c in result.get('columns', []))
        headers = [c.get('header', '') for c in result.get('columns', [])]
        prior = recall_import_pattern(
            header_fingerprint=header_fp,
            column_headers=headers,
        )
        if prior:
            result['prior_import'] = {
                'recognized': True,
                'source_label': prior.get('source_label', ''),
                'total_rows_last_time': prior.get('total_rows', 0),
                'principle': prior.get('principle', ''),
            }

        return api_response(data=result)


class ContactParseConfirmedView(APIView):
    """POST /wcapi/ai/contact/parse-confirmed/ — parse with user-confirmed column map.

    Step 2 of structured import. Uses the confirmed mapping to build JSON rows.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        text = (request.data.get('text') or '').strip()
        delimiter = request.data.get('delimiter', '\t')
        column_map = request.data.get('column_map', [])
        header_row = request.data.get('header_row', 0)
        source_label = (request.data.get('source_label') or '').strip()

        if not text or not column_map:
            return api_response(error='text and column_map required', status_code=400)

        from .services.contact_parser import parse_structured_confirmed, log_import_episode
        result = parse_structured_confirmed(text, delimiter, column_map, header_row)

        if result.get('rows'):
            log_import_episode(result, source_label=source_label)

        return api_response(data=result)


class ContactSearchView(APIView):
    """GET /wcapi/ai/contact/search/?q=Wyoming — load existing contacts for cleanup.

    Returns same grid format as parse, plus cross-row duplicate scores.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        query = request.query_params.get('q', '').strip()
        limit = min(int(request.query_params.get('limit', 20)), 50)
        if not query:
            return api_response(error='q parameter required', status_code=400)

        from .services.contact_parser import load_contacts
        result = load_contacts(query, limit=limit)
        return api_response(data=result)


class ContactParseCorrectView(APIView):
    """POST /wcapi/ai/contact/correct/ — record a chip drag (Small-Sting).

    Request: {"text": "CEO", "original_field": "unassigned", "corrected_field": "title"}
    """
    permission_classes = [AllowAny]

    def post(self, request):
        text = request.data.get('text', '')
        original = request.data.get('original_field', '')
        corrected = request.data.get('corrected_field', '')

        if not text or not corrected:
            return api_response(error='text and corrected_field required', status_code=400)

        from .services.contact_parser import record_field_correction
        user_id = getattr(request.user, 'id', None)
        record_field_correction(text, original, corrected, user_id)

        return api_response(data={'recorded': True, 'text': text, 'field': corrected})


class PiiCorrectView(APIView):
    """POST /wcapi/ai/pii/correct/ — record a user correction on a PII candidate.

    Request:
        {
            "original_text": "the full text that was parsed",
            "candidate": {<candidate dict from parse>},
            "action": "confirmed" | "rejected" | "corrected",
            "corrected_type": "company"  // only if action=corrected
        }

    Each correction is a Small-Sting — Alice learns from it.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        original_text = request.data.get('original_text', '')
        candidate = request.data.get('candidate')
        action = request.data.get('action', '')
        corrected_type = request.data.get('corrected_type')

        if not candidate or action not in ('confirmed', 'rejected', 'corrected'):
            return api_response(
                error='candidate and action (confirmed/rejected/corrected) required',
                status_code=400,
            )

        from .services.pii_scrub import record_pii_correction
        user_id = getattr(request.user, 'id', None)
        record_pii_correction(
            original_text=original_text,
            candidate=candidate,
            action=action,
            corrected_type=corrected_type,
            user_id=user_id,
        )

        return api_response(data={
            'recorded': True,
            'action': action,
            'text': candidate.get('text', ''),
        })


# ═════════════════════════════════════════════════════════════════════════
# Episode Feed & Review — telemetry-style episode exchange
# ═════════════════════════════════════════════════════════════════════════

class EpisodeFeedView(APIView):
    """
    GET /wcapi/episodes/feed/

    Serve this instance's episodes. Like telemetry pings — published
    and generally available to any authenticated connection.

    WCHQ serves only approved episodes (reviewed by Athena + Allie).
    Other instances serve all their local episodes for WCHQ to harvest.

    Auth: Authorization: Athena <token>
    Params:
        since_ms: Only episodes after this timestamp (default: 0 = all)
        approved_only: If "true", only serve reviewed+approved (default: false)
        limit: Max episodes (default: 200)
    """
    permission_classes = [AllowAny]

    def get(self, request):
        connection, error_resp = _validate_athena_token(request)
        if error_resp:
            return error_resp

        from apps.sync.services.episode_bundle import build_episode_feed

        since_ms = int(request.query_params.get('since_ms', 0))
        approved_only = request.query_params.get('approved_only', '').lower() == 'true'
        limit = min(int(request.query_params.get('limit', 200)), 1000)

        feed = build_episode_feed(
            since_ms=since_ms,
            only_approved=approved_only,
            limit=limit,
        )

        return Response(feed)


class EpisodeReviewView(APIView):
    """
    POST /wcapi/episodes/review/

    Review an episode — approve, reject, or archive. Used by Athena
    and Allie after WCHQ harvests episodes from connected instances.

    Auth: Staff or superuser (admin review).
    Body: {
        "episode_id": "EP-xxxx",
        "review_status": "approved" | "rejected" | "archived",
        "reviewed_by": "athena" | "allie" | "admin_username",
        "quality_score": 0.8,   (optional, -1.0 to 1.0)
        "review_note": "..."    (optional)
    }
    """
    permission_classes = [IsAdminUser]

    VALID_STATUSES = {'approved', 'rejected', 'archived', 'pending'}

    def post(self, request):
        from .models import Episode

        episode_id = request.data.get('episode_id', '').strip()
        new_status = request.data.get('review_status', '').strip()
        reviewed_by = request.data.get('reviewed_by', '').strip()

        if not episode_id or not new_status:
            return api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="episode_id and review_status required",
                error_code="missing_fields",
            )

        if new_status not in self.VALID_STATUSES:
            return api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=f"Invalid review_status. Valid: {', '.join(self.VALID_STATUSES)}",
                error_code="invalid_status",
            )

        ep = Episode.objects.filter(episode_id=episode_id).first()
        if not ep:
            return api_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"Episode {episode_id} not found",
                error_code="not_found",
            )

        import time
        ep.review_status = new_status
        ep.reviewed_by = reviewed_by or str(request.user)
        ep.dt_reviewed = int(time.time() * 1000)
        ep.review_note = request.data.get('review_note', '')

        quality = request.data.get('quality_score')
        if quality is not None:
            ep.quality_score = max(-1.0, min(1.0, float(quality)))

        ep.save()

        return api_response(data={
            'episode_id': episode_id,
            'review_status': new_status,
            'reviewed_by': ep.reviewed_by,
        })


class EpisodeBulkReviewView(APIView):
    """
    POST /wcapi/episodes/review/bulk/

    Bulk review episodes — Athena/Allie batch processing.

    Auth: Staff or superuser.
    Body: {
        "reviews": [
            {"episode_id": "EP-xxxx", "review_status": "approved", "quality_score": 0.8},
            {"episode_id": "EP-yyyy", "review_status": "rejected", "review_note": "..."},
        ],
        "reviewed_by": "athena"
    }
    """
    permission_classes = [IsAdminUser]

    def post(self, request):
        from .models import Episode

        reviews = request.data.get('reviews', [])
        reviewed_by = request.data.get('reviewed_by', str(request.user))

        if not reviews:
            return api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="reviews list required",
                error_code="missing_reviews",
            )

        import time
        now_ms = int(time.time() * 1000)
        results = {'approved': 0, 'rejected': 0, 'archived': 0, 'not_found': 0}

        for review in reviews:
            episode_id = review.get('episode_id', '')
            new_status = review.get('review_status', '')
            if not episode_id or new_status not in ('approved', 'rejected', 'archived', 'pending'):
                continue

            ep = Episode.objects.filter(episode_id=episode_id).first()
            if not ep:
                results['not_found'] += 1
                continue

            ep.review_status = new_status
            ep.reviewed_by = reviewed_by
            ep.dt_reviewed = now_ms
            ep.review_note = review.get('review_note', '')

            quality = review.get('quality_score')
            if quality is not None:
                ep.quality_score = max(-1.0, min(1.0, float(quality)))

            ep.save()
            results[new_status] = results.get(new_status, 0) + 1

        return api_response(data=results)


class EpisodeSummaryView(APIView):
    """
    GET /wcapi/episodes/summary/

    Episode dashboard for administrators. Answers:
      1. What do we have? — counts by type, review status, severity
      2. What's new? — this period, local vs harvested
      3. What's recurring? — pattern clusters, most recalled

    Auth: Staff or superuser.
    Params:
        period: Days to look back for "new" (default: 7)
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        from .services.episode_patterns import get_episode_summary

        period = int(request.query_params.get('period', 7))
        summary = get_episode_summary(period_days=period)

        return api_response(data=summary)


class EpisodeDetectPatternsView(APIView):
    """
    POST /wcapi/episodes/detect-patterns/

    Trigger pattern detection on rejected episodes. Alice scans for
    recurring clusters and creates pattern episodes + admin notifications.

    Auth: Staff or superuser.
    Body: {
        "since_days": 30  (optional, default 30)
    }
    """
    permission_classes = [IsAdminUser]

    def post(self, request):
        from .services.episode_patterns import detect_rejected_patterns

        since_days = int(request.data.get('since_days', 30))
        result = detect_rejected_patterns(since_days=since_days)

        return api_response(data=result)


# ═════════════════════════════════════════════════════════════════════════
# Support Feed — coaching distribution, help patterns, support summary
# ═════════════════════════════════════════════════════════════════════════

class CoachingFeedView(APIView):
    """
    GET /wcapi/coaching/

    Serve coaching content to connected instances. Instances poll this
    endpoint to pick up new coaching tips, field help, and guides.

    Auth: Authorization: Athena <token>
    Params:
        since_ms: Only content modified after this timestamp (default: 0)
    """
    permission_classes = [AllowAny]

    def get(self, request):
        connection, error_resp = _validate_athena_token(request)
        if error_resp:
            return error_resp

        from .services.support_feed import build_coaching_feed

        since_ms = int(request.query_params.get('since_ms', 0))
        feed = build_coaching_feed(since_ms=since_ms)

        return Response(feed)


class SupportSummaryView(APIView):
    """
    GET /wcapi/support/summary/

    Support dashboard for administrators. Shows:
      - Q&A health (answered, unanswered, low-scored, escalated)
      - Coaching coverage (models with help content, drill completion)
      - Escalation volume
      - Active help patterns needing attention

    Auth: Staff or superuser.
    Params:
        period: Days to look back for "recent" (default: 7)
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        from .services.support_feed import get_support_summary

        period = int(request.query_params.get('period', 7))
        summary = get_support_summary(period_days=period)

        return api_response(data=summary)


class SupportDetectPatternsView(APIView):
    """
    POST /wcapi/support/detect-patterns/

    Trigger help pattern detection on escalated Q&A. Scans for
    recurring questions across instances, creates coaching candidates.

    Auth: Staff or superuser.
    Body: {
        "since_days": 30  (optional, default 30)
    }
    """
    permission_classes = [IsAdminUser]

    def post(self, request):
        from .services.support_feed import detect_help_patterns

        since_days = int(request.data.get('since_days', 30))
        result = detect_help_patterns(since_days=since_days)

        return api_response(data=result)


class CoachingFeedbackView(APIView):
    """
    POST /wcapi/coaching/feedback/

    Report coaching effectiveness back to WCHQ. Instances tell us
    which coaching content was helpful and which wasn't. Negative
    feedback creates AliceObservations for improvement.

    Auth: Authorization: Athena <token> (from connected instance)
          OR IsAuthenticated (from local user)
    Body: {
        "feedback": [
            {
                "coaching_ida": "wc:coaching:invoice",
                "tip_index": 2,
                "rating": 1,
                "comment": "Clear and helpful"
            },
            {
                "coaching_ida": "wc:coaching:order",
                "field": "shipping_method",
                "rating": -1,
                "comment": "Outdated — we use a different carrier now"
            }
        ]
    }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        from .services.support_feed import submit_coaching_feedback

        # Accept from Athena-authenticated connections or logged-in users
        connection, _ = _validate_athena_token(request)
        if not connection and not (request.user and request.user.is_authenticated):
            return api_response(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message="Requires Athena token or authenticated user",
                error_code="auth_required",
            )

        feedback_items = request.data.get('feedback', [])
        if not feedback_items:
            return api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="feedback list required",
                error_code="missing_feedback",
            )

        result = submit_coaching_feedback(feedback_items)

        return api_response(data=result)
