from django.urls import path
from core.views import (
    HomeView, AboutView,
    WebSignupView, WebLoginView, WebLogoutView,
    UniversalCRUDView
    
)
from django.views.generic import TemplateView

urlpatterns = [
    # Home and About pages
    path('', HomeView.as_view(), name='home'),
    path('about/', AboutView.as_view(), name='about'),
    
    # Authentication
    path('signup/', WebSignupView.as_view(), name='signup'),
    path('login/', WebLoginView.as_view(), name='login'),
    path('logout/', WebLogoutView.as_view(), name='logout'),
    
   
        # Dedicated Management Pages
    path('manage/actions/', TemplateView.as_view(template_name='core/manage_actions.html'), name='manage-actions'),
    path('user/', TemplateView.as_view(template_name='core/user.html'), name='users'),
    path('manager/', TemplateView.as_view(template_name='core/manager.html'), name='manager'),
    # Universal API endpoints
    # Rare for sockets. We will more likely create an api app for websockets
    
]
