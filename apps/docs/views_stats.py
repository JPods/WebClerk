from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Count

from apps.docs.models import Document, Linkage, QuestionAnswer


class DocsStatsView(APIView):
    """
    Returns counts of documents, linkages, and question-answers.
    GET /docs/stats/
    Response: { documents: count, linkages: count, question_answers: count }
    """

    def get(self, request):
        stats = {
            'documents': Document.objects.count(),
            'linkages': Linkage.objects.count(),
            'question_answers': QuestionAnswer.objects.count(),
        }
        return Response(stats, status=status.HTTP_200_OK)