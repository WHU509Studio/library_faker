from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.urls import reverse


def log_in(request):
    if request.method == 'GET':
        return render(request,'library/log_in.html')
    elif request.method == 'POST':
        return redirect(reverse('library:library'))
    

def library_form(request):
    if request.method == 'GET':
        return render(request,'library/text.html')
    elif request.method == 'POST':
       # print(request.POST.get('library'))
        return HttpResponse(request.POST.get('library'))
# Create your views here.
