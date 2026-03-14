from collections import defaultdict

from django.http import HttpResponse
from django.shortcuts import render
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.contrib import messages
from django.db.models import Q

from .models import WorkRequest, WorkOrder, PaymentRequisition, PaymentItem, PPM
from .forms import WorkRequestForm, WorkOrderForm, PaymentRequisitionForm, PPMForm
from accounts.models import Category, Subcategory, Department, User, Vendor
from facility.models import Facility, Apartment
from asset_inventory.models import Asset


class WorkRequestView(LoginRequiredMixin, View):
    def get(self, request):
        """
        Retrieve and display all work requests.
        """
        work_requests = WorkRequest.objects.filter(
            Q(owner=request.user) | Q(request_to=request.user)
        ).distinct().order_by("-id")
        users = User.objects.filter(roles="Facility Procurement")
        user = request.user
        categories = Category.objects.all()
        subcategories = Subcategory.objects.all()
        departments = user.departments.all()
        facilities = user.facility.all()
        apartments = user.apartments.all()
        assets = user.categories.all()

        context = {
            "work_requests": work_requests,
            "categories": categories,
            "subcategories": subcategories,
            "departments": departments,
            "facilities": facilities,
            "apartments": apartments,
            "assets": assets,
            "users": users, 
        }

        return render(request, "work_request.html", context)
    
    def post(self, request):
        """
        Create a new work request and optionally a work order if approved.
        """
        form = WorkRequestForm(request.POST, request.FILES, request=request)
        
        if form.is_valid():
            # Save the work request
            work_request = form.save()
            messages.success(request, "Work request created successfully.")
            
            # Check if the work request is approved and create a work order
            if work_request.approval_status == "Approved":
                try:
                    work_request.status = "Inactive"
                    work_request.save(update_fields=['status'])
                    # Create a new work order based on the work request
                    work_order, created = WorkOrder.objects.get_or_create(
                        # Fields to check for existing entry
                        title=f"Work Order from Request #{work_request.work_request_number}",
                        defaults={
                            # Fields to set if creating a new entry
                            'type': work_request.type,
                            'facility': work_request.facility,
                            'category': work_request.category,
                            'subcategory': work_request.subcategory,
                            'department': work_request.department,
                            'priority': work_request.priority,
                            'description': work_request.description,
                            'requester': work_request.requester or request.user,
                            'request_to': work_request.owner,  # Assign to the owner of the work request
                            'approval_status': work_request.approval_status,
                            'currency': work_request.currency,
                            'add_discount': work_request.add_discount,
                            'exclude_management_fee': work_request.exclude_management_fee,
                            'require_mobilization_fee': work_request.require_mobilization_fee,
                            'follow_up_notes': work_request.follow_up_notes,
                            'invoice_no': work_request.invoice_no,
                            'payment_requisition': work_request.payment_requisition,
                            'apartment': work_request.apartment,
                            'asset': work_request.asset,
                            'owner': request.user,
                        }
                    )
                    
                    # Transfer any attachments from work request to work order
                    for attachment in work_request.files.all():
                        work_order.files.add(attachment)
                    
                    messages.success(request, "Work order created successfully from the approved request.")
                    
                except Exception as e:
                    # Log the error but don't fail the entire request
                    messages.error(request, f"Error creating work order: {str(e)}")
                    
            return redirect("work:work_request")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.capitalize()}: {error}")
                        
        return redirect("work:work_request")

class WorkRequestDetailView(LoginRequiredMixin, View):
    def get(self, request, slug):
        """
        Retrieve details of a specific work request.
        Supports both full-page and HTMX partial updates.
        """
        work_request = get_object_or_404(WorkRequest, slug=slug)
        users = User.objects.all()
        categories = Category.objects.all()
        subcategories = Subcategory.objects.all()
        departments = Department.objects.all()
        facilities = Facility.objects.all()
        apartments = Apartment.objects.all()
        assets = Asset.objects.all()

        context = {
            "work_request": work_request,
            "categories": categories,
            "subcategories": subcategories,
            "departments": departments,
            "facilities": facilities,
            "apartments": apartments,
            "assets": assets,
            "users": users, 
        }


        if request.htmx:
            return render(request, "partials/work_request_detail.html", context)

        return render(request, "work_request.html", context)
    
    def post(self, request, slug):
        """
        Update an existing work request and create a work order if approved.
        """
        work_request = get_object_or_404(WorkRequest, slug=slug)
        old_status = work_request.approval_status
        form = WorkRequestForm(request.POST, request.FILES, instance=work_request, request=request)
        
        if form.is_valid():
            work_request = form.save()
            messages.success(request, "Work request updated successfully.")
            
            # Check if the approval status changed to "Approved" and create a work order
            if work_request.approval_status == "Approved" and old_status != "Approved":
                try:
                    work_order, created = WorkOrder.objects.get_or_create(
                        # Fields to check for existing entry
                        title=f"Work Order from Request #{work_request.work_request_number}",
                        defaults={
                            # Fields to set if creating a new entry
                            'type': work_request.type,
                            'facility': work_request.facility,
                            'category': work_request.category,
                            'subcategory': work_request.subcategory,
                            'department': work_request.department,
                            'priority': work_request.priority,
                            'description': work_request.description,
                            'requester': work_request.requester or request.user,
                            'request_to': work_request.owner,  # Assign to the owner of the work request
                            'approval_status': work_request.approval_status,
                            'currency': work_request.currency,
                            'add_discount': work_request.add_discount,
                            'exclude_management_fee': work_request.exclude_management_fee,
                            'require_mobilization_fee': work_request.require_mobilization_fee,
                            'follow_up_notes': work_request.follow_up_notes,
                            'invoice_no': work_request.invoice_no,
                            'payment_requisition': work_request.payment_requisition,
                            'apartment': work_request.apartment,
                            'asset': work_request.asset,
                            'owner': request.user,
                        }
                    )
                    
                    # Transfer any attachments from work request to work order
                    for attachment in work_request.files.all():
                        work_order.files.add(attachment)
                    
                    work_request.status = "Inactive"
                    work_request.save(update_fields=['status'])
                    
                    messages.success(request, "Work order created successfully from the approved request.")
                except Exception as e:
                    # Log the error but don't fail the entire request
                    messages.error(request, f"Error creating work order: {str(e)}")
                    
            return redirect("work:work_request")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.capitalize()}: {error}")
                        
        return redirect("work:work_request")


class WorkOrderView(View):
    def get(self, request):
        """
        Retrieve and display all work orders.
        """
        work_orders = WorkOrder.objects.all().order_by("-id")
        users = User.objects.filter(roles="Facility Procurement")
        categories = Category.objects.all()
        subcategories = Subcategory.objects.all()
        departments = Department.objects.all()
        facilities = Facility.objects.all()
        apartments = Apartment.objects.all()
        assets = Asset.objects.all()

        context = {
            "work_orders": work_orders,
            "categories": categories,
            "subcategories": subcategories,
            "departments": departments,
            "facilities": facilities,
            "apartments": apartments,
            "assets": assets,
            "users": users, 
        }

        return render(request, "work_order.html", context)
    
    def post(self, request):
        """
        Create a new work order.
        """
        form = WorkOrderForm(request.POST, request.FILES, request=request)
        
        if form.is_valid():
            work_order = form.save(commit=False)
            work_order.save()
            messages.success(request, "Work order created successfully.")
            return redirect("work:work_order")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.capitalize()}: {error}")
                        
        return redirect("work:work_order")

class WorkOrderDetailView(View):
    def get(self, request, slug):
        """
        Retrieve details of a specific work order.
        Supports both full-page and HTMX partial updates.
        """
        work_order = get_object_or_404(WorkOrder, slug=slug)
        users = User.objects.filter(roles="Facility Procurement")
        categories = Category.objects.all()
        subcategories = Subcategory.objects.all()
        departments = Department.objects.all()
        facilities = Facility.objects.all()
        apartments = Apartment.objects.all()
        assets = Asset.objects.all()

        context = {
            "work_order": work_order,
            "categories": categories,
            "subcategories": subcategories,
            "departments": departments,
            "facilities": facilities,
            "apartments": apartments,
            "assets": assets,
            "users": users, 
        }
        context = {"work_order": work_order}

        if request.htmx:
            return render(request, "partials/work_order_detail.html", context)

        return render(request, "work_order.html", context)
    
    def post(self, request, slug):
        """
        Update an existing work request.
        """
        work_request = get_object_or_404(WorkOrder, slug=slug)
        form = WorkOrderForm(request.POST, request.FILES, instance=work_request)
        
        if form.is_valid():
            work_order = form.save(commit=False)
            work_order.save()
            messages.success(request, "Work order updated successfully.")
            return redirect("work:work_order")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.capitalize()}: {error}")
                    
        return redirect("work:work_order")


class RequisitionView(View):
    def get(self, request):
        """
        Retrieve and display all payment requisitions along with related data.
        """
        requisitions = PaymentRequisition.objects.all().order_by("-id") 
        items = PaymentItem.objects.all()
        users = Vendor.objects.all()

        context = {
            "payment_requisitions": requisitions,
            "items": items,
            "users": users,
        }

        return render(request, "requisition.html", context)

    def post(self, request):
        """
        Create a new payment requisition and handle form validation.
        """
        form = PaymentRequisitionForm(request.POST, request.FILES)
        
        if form.is_valid():
            payment_requisition = form.save()  # Save form data
            
            # ManyToMany fields require explicit saving
            if "items" in request.POST:
                payment_requisition.items.set(request.POST.getlist("items"))

            messages.success(request, "Payment requisition created successfully.")
            return redirect("work:requisition")  # Redirect after successful submission

        else:
            # Loop through errors and display them as messages
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.capitalize()}: {error}")

        return redirect("work:requisition")
    
    
    
class RequisitionDetailView(View):
    def get(self, request, requisition_number):
        """
        Retrieve details of a specific payment requisition.
        Supports both full-page and HTMX partial updates.
        """
        requisition = get_object_or_404(PaymentRequisition, requisition_number=requisition_number)
        context = {"requisition": requisition}

        if request.htmx:
            return render(request, "partials/requisition_detail.html", context)

        return render(request, "requisition_detail.html", context)

class PPMSettingView(View):
    def get(self, request):
        """
        Retrieve and display all Planned Preventive Maintenance (PPM) settings.
        """
        ppm_settings = PPM.objects.all().order_by("-id")  
        items = PaymentItem.objects.all()
        facilities = Facility.objects.all()
        assets = Asset.objects.all()
        categories = Category.objects.all()
        subcategories = Subcategory.objects.all()
        currencies = [('NGN', 'Nigerian Naira'), ('USD', 'US Dollar'), ('EUR', 'Euro')]
        
        context = {
            "ppm_settings": ppm_settings,
            "items": items,
            "facilities": facilities,
            "assets": assets,
            "currencies": currencies,
            "categories": categories,
            "subcategories": subcategories,
        }

        return render(request, "ppm_setting.html", context)

    def post(self, request):
        """
        Create a new Planned Preventive Maintenance (PPM) setting and handle form validation.
        """
        form = PPMForm(request.POST, request.FILES)

        if form.is_valid():
            ppm_setting = form.save()  # Save form data

            # Handle ManyToMany fields
            if "assets" in request.POST:
                ppm_setting.assets.set(request.POST.getlist("assets"))
            if "facilities" in request.POST:
                ppm_setting.facilities.set(request.POST.getlist("facilities"))
            if "apartments" in request.POST:
                ppm_setting.apartments.set(request.POST.getlist("apartments"))
            if "items" in request.POST:
                ppm_setting.items.set(request.POST.getlist("items"))

            messages.success(request, "PPM setting created successfully.")
            return redirect("work:ppm_setting")  # Redirect after successful submission

        else:
            # Loop through errors and display them as messages
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.capitalize()}: {error}")

        return redirect("work:ppm_setting")


class PPMDetailView(View):
    def get(self, request, id):
        """
        Retrieve details of a specific PPM setting.
        Supports both full-page and HTMX partial updates.
        """
        ppm_setting = get_object_or_404(PPM, id=id)
        context = {"ppm": ppm_setting}

        if request.htmx:
            return render(request, "partials/ppm_detail.html", context)

        return render(request, "ppm_detail.html", context)
    
    
class PendingPPMView(View):
    def get(self, request):
        """
        Retrieve and display all pending Planned Preventive Maintenance (PPM) settings, grouped by facility.
        """
        ppm_settings = PPM.objects.all().order_by("-id")
        
        # Group PPMs by facility
        ppm_grouped_by_facility = defaultdict(list)
        for ppm in ppm_settings:
            for facility in ppm.facilities.all():
                ppm_grouped_by_facility[facility.name].append(ppm)

        context = {
            "ppm_grouped_by_facility": dict(ppm_grouped_by_facility),
        }

        return render(request, "pending_ppm.html", context)


def budget(request):

     return render(request, 'budget.html' )