from django.http import HttpResponse

def home(request):
    return HttpResponse("Welcome to payment gateway. Go to api/v1/docs ")
