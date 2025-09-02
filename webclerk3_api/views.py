

from django.shortcuts import render
def home(request):
    #   return HttpResponse("Hello, World! This is the home page.")
    return render(request, "home.html")

def about(request):
    #   return HttpResponse("This is the about page.")
    return render(request, "about.html")
