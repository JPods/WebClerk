"""
AI Assistant API views.

Endpoints:
    POST /wcapi/ai/ask/       — ask a question (RAG-powered)
    POST /wcapi/ai/feedback/   — submit feedback on an answer
    GET  /wcapi/ai/health/     — system health check
    GET  /wcapi/ai/history/    — conversation history for current user
"""
import json
import logging

from django.http import StreamingHttpResponse, JsonResponse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView

from common.api_responses import api_response
from .models import Conversation, Message
from .services.rag_service import RAGService

logger = logging.getLogger(__name__)


class AskView(APIView):
    """
    POST /wcapi/ai/ask/
    Body: {"question": "...", "conversation_id": null, "context_page": "", "stream": false}
    """
    permission_classes = [IsAuthenticated]

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
        do_stream = request.data.get("stream", False)

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
            return self._stream_response(rag, question, history, conversation)

        # Non-streaming response
        try:
            result = rag.ask(question, history=history)
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
            "conversation_id": conversation.pk,
            "message_id": msg.pk,
        })

    def _stream_response(self, rag, question, history, conversation):
        """Return a streaming response for real-time output."""

        def event_stream():
            try:
                stream, sources = rag.ask_stream(question, history=history)
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
