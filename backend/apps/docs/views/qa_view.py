"""
QA Views - API endpoints for question/answer operations.

Templates are Document records with refs.keywords containing 'qa_template'.

Endpoints:
- POST /api/docs/qa/apply/ - Apply a question template to a parent record
- GET  /api/docs/qa/groups/ - List available question templates
- GET  /api/docs/qa/{parent_model}/{parent_id}/ - Get QA records for a parent
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import ValidationError, ObjectDoesNotExist
import logging

from apps.docs.services.qa_service import QAService
from apps.docs.serializers.question_answer_serializer import QuestionAnswerSerializer

logger = logging.getLogger(__name__)


class ApplyQuestionsView(APIView):
    """Apply a question template (Document) to a parent record.

    POST /api/docs/qa/apply/

    Request body:
    {
        "document_name": "JPods Daily Pre-Op Vehicle Inspection",
        "parent_model": "item",
        "parent_id": 123,
        "contact_data": {"id": 456, "attention": "John Doe"}  // optional
    }

    Or use document_id for direct lookup:
    {
        "document_id": 789,
        "parent_model": "item",
        "parent_id": 123
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        document_name = request.data.get('document_name')
        document_id = request.data.get('document_id')
        parent_model = request.data.get('parent_model')
        parent_id = request.data.get('parent_id')
        contact_data = request.data.get('contact_data')

        if not document_name and not document_id:
            return Response(
                {'error': 'document_name or document_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not parent_model:
            return Response(
                {'error': 'parent_model is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not parent_id:
            return Response(
                {'error': 'parent_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            service = QAService()
            records = service.apply_questions(
                document_name=document_name,
                document_id=int(document_id) if document_id else None,
                parent_model=parent_model,
                parent_id=int(parent_id),
                user=request.user,
                contact_data=contact_data
            )

            serializer = QuestionAnswerSerializer(records, many=True)

            existing_count = sum(1 for r in records if r.status != 'open')
            created_count = len(records) - existing_count

            return Response({
                'success': True,
                'created_count': created_count,
                'existing_count': existing_count,
                'records': serializer.data
            }, status=status.HTTP_200_OK)

        except ObjectDoesNotExist as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.exception(f"Error applying questions: {e}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ListQuestionGroupsView(APIView):
    """List available question templates (Documents with qa_template keyword).

    GET /api/docs/qa/groups/

    Response:
    {
        "groups": [
            {
                "id": 113,
                "name": "JPods Daily Pre-Op Vehicle Inspection",
                "description": "Daily vehicle inspection — ASTM F770",
                "question_count": 19,
                "standards": ["ASTM F770"],
                "spec_refs": ["SPEC-01", "SPEC-02"]
            }
        ]
    }
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            service = QAService()
            groups = service.list_available_groups()
            return Response({'groups': groups}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception(f"Error listing question groups: {e}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ParentQAView(APIView):
    """Get QA records for a parent record.

    GET /api/docs/qa/{parent_model}/{parent_id}/
    GET /api/docs/qa/{parent_model}/{parent_id}/?template_name=JPods+Daily+Pre-Op

    Response:
    {
        "records": [ ... QuestionAnswer records ... ]
    }
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, parent_model, parent_id):
        template_name = request.query_params.get('template_name')

        try:
            service = QAService()
            records = service.get_questions_for_parent(
                parent_model=parent_model,
                parent_id=int(parent_id),
                template_name=template_name
            )

            serializer = QuestionAnswerSerializer(records, many=True)
            return Response({'records': serializer.data}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception(f"Error fetching QA records: {e}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
