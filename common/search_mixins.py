from django.db import models
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import permissions


class PrefixAndSearchView(APIView):
    """Reusable multi-term AND prefix search for simple models.

    Subclasses set:
        model (QuerySet available via model.objects)
        serializer_class
        search_fields = ['name','type']  (fields to OR within each term)
        role_set = {'staff','admin'} (optional)
        max_results = 100
    """
    permission_classes = [permissions.IsAuthenticated]
    model = None
    serializer_class = None
    search_fields: list[str] = []
    role_set: set[str] | None = None
    max_results = 100

    def _role_allowed(self, user):
        if not user.is_authenticated:
            return False
        if not self.role_set:
            return True
        return getattr(user, 'role', '') in self.role_set or getattr(user, 'is_superuser', False)

    def get_queryset(self):
        return self.model.objects.all()  # type: ignore

    def build_query(self, qs, terms):
        for term in terms:
            or_q = models.Q()
            for f in self.search_fields:
                or_q |= models.Q(**{f"{f}__istartswith": term})
            qs = qs.filter(or_q)
        return qs

    def get(self, request):
        if not self._role_allowed(request.user):
            return Response({'detail':'Forbidden'}, status=403)
        raw_q = (request.GET.get('q') or '').strip()
        if not raw_q:
            return Response({'results': [], 'count': 0})
        terms = [t for t in raw_q.split() if t]
        qs = self.get_queryset()
        qs = self.build_query(qs, terms).order_by('-dt_modified')[: self.max_results]
        data = self.serializer_class(qs, many=True, context={'request': request}).data  # type: ignore
        return Response({'results': data, 'count': len(data), 'q': raw_q, 'terms': terms})