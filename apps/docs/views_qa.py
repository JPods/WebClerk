"""
QA Views - API endpoints for question/answer operations.

Endpoints:
- POST /api/docs/qa/apply/ - Apply a question template to a parent record
- GET  /api/docs/qa/groups/ - List available question groups
- GET  /api/docs/qa/{parent_type}/{parent_id}/ - Get QA records for a parent
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import ValidationError, ObjectDoesNotExist
import logging

from apps.docs.services.qa_service import QAService
from apps.docs.serializers.question_answer import QuestionAnswerSerializer

logger = logging.getLogger(__name__)


class ApplyQuestionsView(APIView):
    """Apply a question group template to a parent record.
    
    POST /api/docs/qa/apply/
    
    Request body:
    {
        "question_group": "Planning",
        "parent_type": "sales_order",
        "parent_id": 123,
        "contact_data": {"id": 456, "attention": "John Doe"}  // optional
    }
    
    Response:
    {
        "success": true,
        "created_count": 5,
        "existing_count": 0,
        "records": [ ... QuestionAnswer records ... ]
    }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        question_group = request.data.get('question_group')
        parent_type = request.data.get('parent_type')
        parent_id = request.data.get('parent_id')
        contact_data = request.data.get('contact_data')
        
        if not question_group:
            return Response(
                {'error': 'question_group is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not parent_type:
            return Response(
                {'error': 'parent_type is required'},
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
                question_group=question_group,
                parent_type=parent_type,
                parent_id=int(parent_id),
                user=request.user,
                contact_data=contact_data
            )
            
            # Serialize results
            serializer = QuestionAnswerSerializer(records, many=True)
            
            # Count new vs existing
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
    """List available question groups.
    
    GET /api/docs/qa/groups/
    
    Response:
    {
        "groups": [
            {
                "id": 113,
                "name": "Planning",
                "question_count": 8,
                "template": {
                    "allow_freeform": false,
                    "allow_multiple": false,
                    ...
                }
            },
            ...
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
    
    GET /api/docs/qa/{parent_type}/{parent_id}/
    GET /api/docs/qa/{parent_type}/{parent_id}/?question_group=Planning
    
    Response:
    {
        "records": [ ... QuestionAnswer records ... ]
    }
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, parent_type, parent_id):
        question_group = request.query_params.get('question_group')
        
        try:
            service = QAService()
            records = service.get_questions_for_parent(
                parent_type=parent_type,
                parent_id=int(parent_id),
                question_group=question_group
            )
            
            serializer = QuestionAnswerSerializer(records, many=True)
            return Response({'records': serializer.data}, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.exception(f"Error fetching QA records: {e}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
