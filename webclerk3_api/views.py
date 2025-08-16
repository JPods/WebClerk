# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/webclerk3_api/views.py


from django.shortcuts import render
def home(request):
    #   return HttpResponse("Hello, World! This is the home page.")
    return render(request, "home.html")

def about(request):
    #   return HttpResponse("This is the about page.")
    return render(request, "about.html")
