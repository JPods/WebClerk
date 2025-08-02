from django.contrib import admin
from django.urls import path, include
from django.shortcuts import render
from django.http import HttpResponse

def home_view(request):
    """Simple home page"""
    return HttpResponse("""
    <h1>WebClerk 3.0 Universal API</h1>
    <p>🎉 Universal API is Live!</p>
    <ul>
        <li><a href="/WCapi/contacts/manage/">Manage Contacts</a></li>
        <li><a href="/WCapi/emails/manage/">Manage Emails</a></li>
        <li><a href="/WCapi/phones/manage/">Manage Phones</a></li>
        <li><a href="/contact/">My Profile</a></li>
        <li><a href="/signup/">Sign Up</a></li>
        <li><a href="/login/">Login</a></li>
    </ul>
    """)

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # Home
    path('', home_view, name='home'),
    
    # Include ALL core URLs (your excellent core/urls.py)
    path('', include('core.urls')),
]