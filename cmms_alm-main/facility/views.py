import json

from django.shortcuts import render, HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages

from .models import Facility
from asset_inventory.models import Store
from accounts.models import User
from .forms import StoreForm, FacilityForm



class StoreView(View):
    def get(self, request):
        """
        Handle GET requests: Load the store page with necessary context data.
        """
        context = {
            "stores": Store.objects.all(),
        }
        return render(request, "facility/store.html", context)

    def post(self, request):
        """
        Handle POST requests: Create or update store records.
        """
        form = StoreForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Store has been successfully created.")
            return redirect("facility:store")  # Replace with the appropriate URL name
        else:
            for field_name, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field_name.capitalize()}: {error}")

        return redirect("facility:store")


class StoreDetailView(View):
    def get(self, request, pk):
        """
        Handle GET requests: Load details for a specific store.
        """
        store = get_object_or_404(Store, pk=pk)
        context = {
            "store": store,
        }
        return render(request, "facility/store_detail.html", context)


class FacilityView(View):
    def get(self, request):
        """
        Handle GET requests: Load the facility page with necessary context data.
        """
        facilities = Facility.objects.all()
        stores = Store.objects.all()  # If you need to display associated stores
        users = User.objects.all()
        context = {
            "facilities": facilities,
            "stores": stores,
            "users": users
        }
        return render(request, "facility.html", context)

    def post(self, request):
        """
        Handle POST requests: Create or update facility records.
        """
        form = FacilityForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Facility has been successfully created.")
            return redirect("facility:facility")  # Replace with the appropriate URL name
        else:
            for field_name, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field_name.capitalize()}: {error}")

        return redirect("facility:facility")


from .models import Building

class FacilityDetailView(View):
    def get(self, request, code):
        """
        Handle GET requests: Load details for a specific facility.
        """
        facility = get_object_or_404(Facility, code=code)
        
        # Get associated buildings for this facility
        buildings = Building.objects.filter(facility=facility)
        
        # Get all rooms associated with this facility
        # rooms = Room.objects.filter(building__facility=facility)
        
        context = {
            "facility": facility,
            "buildings": buildings,
            "rooms": None
        }
        # Check if this is an HTMX request
        if request.headers.get('HX-Request'):
            # Return only the facility detail partial template for HTMX requests
            return render(request, "partials/facility_detail.html", context)
        
        # For regular requests, return the full page
        return render(request, "facility/facility_detail.html", context)


def occupant(request):

     return render(request, 'occupant.html' )

def bulk_notification(request):

    return render(request, 'bulk_notification.html' )

def facility_invoice(request):

     return render(request, 'facility_invoice.html' )

def apartment_type(request):

     return render(request, 'apartment_type.html' )

def landlord(request):

     return render(request, 'landlord.html' )