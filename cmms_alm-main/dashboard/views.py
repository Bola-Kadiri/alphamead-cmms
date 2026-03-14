from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.db import models
from django.conf import settings
from django.contrib.auth.decorators import login_required

import requests


from dashboard import models as dashboard_models



@login_required
def index(request):
    # products = dashboard_models.Product.objects.filter(status="Published")
    # categories = store_models.Category.objects.all()
    context = {
        # "products": products,
        # "categories": categories,
    }
    return render(request, "dashboard/index.html", context)

def dashboard(request):

    return render(request, 'dashboard/index.html' )

def calendar(request):

    return render(request, 'dashboard/calendar.html' )