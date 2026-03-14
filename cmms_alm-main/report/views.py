from django.http import HttpResponse
from django.shortcuts import render



def user_facility(request):

    return render(request, 'report/user_facility.html' )

def scheduled(request):

     return render(request, 'report/scheduled.html' )

def user_audit(request):

    return render(request, 'report/user_audit.html' )

def usage_report(request):

     return render(request, 'report/usage_report.html' )

