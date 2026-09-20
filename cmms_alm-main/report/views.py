from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render

from facility.models import Facility


@login_required
def user_facility(request):
    context = {
        "facilities": Facility.objects.all().order_by('name'),
    }
    return render(request, 'report/user_facility.html', context)

def scheduled(request):

     return render(request, 'report/scheduled.html' )

def user_audit(request):

    return render(request, 'report/user_audit.html' )

def usage_report(request):

     return render(request, 'report/usage_report.html' )

