from django.urls import path
from .views.connection import ConnectionListView, ConnectionDetailView, ConnectionSearchView
from .views.google_calendar import GCAL_StartAuthView, GCAL_OAuthCallbackView, GCAL_ListEventsView

app_name = 'sync'

urlpatterns = [
    path('connections/', ConnectionListView.as_view(), name='connection-list'),
    path('connections/<int:pk>/', ConnectionDetailView.as_view(), name='connection-detail'),
    path('connections/search/', ConnectionSearchView.as_view(), name='connection-search'),
    # Google Calendar integration
    path('google/calendar/start', GCAL_StartAuthView.as_view(), name='gcal-start'),
    path('google/calendar/callback', GCAL_OAuthCallbackView.as_view(), name='gcal-callback'),
    path('google/calendar/events', GCAL_ListEventsView.as_view(), name='gcal-events'),
]
