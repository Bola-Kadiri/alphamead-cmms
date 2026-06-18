from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from dashboard.services import get_dashboard_data


@login_required
def index(request):
    context = get_dashboard_data(request.user)
    return render(request, 'dashboard/index.html', context)


def dashboard(request):
    return render(request, 'dashboard/index.html')


def calendar(request):
    return render(request, 'dashboard/calendar.html')
