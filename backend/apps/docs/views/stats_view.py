from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Count

from apps.docs.models import Document, LinkageEntry, QuestionAnswer


class DocsStatsView(APIView):
    """
    Returns counts of documents, linkage_entries, and question-answers.
    GET /docs/stats/
    Response: { documents: count, linkage_entries: count, question_answers: count }
    """

    def get(self, request):
        stats = {
            'documents': Document.objects.count(),
            'linkage_entries': LinkageEntry.objects.count(),
            'question_answers': QuestionAnswer.objects.count(),
        }
        return Response(stats, status=status.HTTP_200_OK)
