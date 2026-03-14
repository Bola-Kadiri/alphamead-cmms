from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.contrib.contenttypes.models import ContentType
from django.views.decorators.http import require_http_methods

from django.views.generic import TemplateView, ListView, DetailView
from django.views import View
from django.core.exceptions import ValidationError
from django.db import transaction
from .forms import *
from django.db.models import Sum, F
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action, api_view
from rest_framework.permissions import IsAuthenticated
from django.core.paginator import Paginator
from django.template.loader import render_to_string

from accounts.models import Department, User
from .models import Item, InventoryRequest
from asset_inventory.models import Store
from utils.models import ImageAttachment
from django.views.generic import TemplateView, CreateView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect

from accounts.models import Vendor
from .models import  Asset, Transfer
from accounts.models import Category, Subcategory

class AssetRegisterView(TemplateView):
    template_name = 'asset_register.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'categories': Category.objects.all(),
            'subcategories': Subcategory.objects.all(),
            'page_title': 'Asset Register',
            'status_choices': [
                ("Available", "Available"),
                ("In Use", "In Use"),
                ("Under Maintenance", "Under Maintenance"),
                ("Disposed", "Disposed"),
            ],
            'assets': Asset.objects.all(),
            'total_quantity': Asset.objects.aggregate(total=Sum('quantity'))['total'] or 0,
            'total_amount': Asset.objects.aggregate(total=Sum('amount'))['total'] or 0,
            'vendors': Vendor.objects.all(),
        })
        return context

    def post(self, request, *args, **kwargs):
        try:
            data = request.POST
            asset = Asset.objects.create(
                category_id=data.get('category'),
                subcategory_id=data.get('subcategory'),
                model=data.get('model'),
                part_no=data.get('part_no'),
                serial_number=data.get('serial_number'),
                asset_tag=data.get('asset_tag'),
                quantity=data.get('quantity'),
                unit_price=data.get('unit_price'),
                reorder_level=data.get('reorder_level') or 0,
                min_stock_level=data.get('min_stock_level') or 0,
                max_stock_level=data.get('max_stock_level') or 0,
                location=data.get('location'),
                flags=data.get('flags'),
                status=data.get('status')
            )
            return JsonResponse({
                'status': 'success',
                'message': 'Asset created successfully',
                'asset_id': asset.id
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)

def inventory_adjustment(request):

     return render(request, 'asset_inventory/inventory_adjustment.html' )

def inventory(request):
    # Get all assets with related data
    assets = Asset.objects.select_related('category', 'subcategory').all()
    
    # Calculate totals
    totals = assets.aggregate(
        total_stock=Sum('quantity'),
        total_value=Sum(F('quantity') * F('unit_price'))
    )
    
    # Pagination
    paginator = Paginator(assets, 10)  # Show 10 items per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'inventory_items': page_obj,
        'page_obj': page_obj,
        'total_stock': totals['total_stock'] or 0,
        'total_value': totals['total_value'] or 0,
        'categories': Category.objects.all(),
        'status_choices': [
            ("Available", "Available"),
            ("Low Stock", "Low Stock"),
            ("Out of Stock", "Out of Stock"),
            ("Discontinued", "Discontinued"),
        ],
    }
    
    return render(request, 'inventory.html', context)

class InventoryRequestView(LoginRequiredMixin, CreateView):
    model = InventoryRequest
    template_name = 'item_request.html'
    fields = ['request_type', 'vendor', 'store', 'required_date', 'department', ]
    success_url = reverse_lazy('asset_inventory:item_request')
    
    def get_context_data(self, **kwargs):
        """Add all necessary data to the context"""
        context = super().get_context_data(**kwargs)
        
        # Add required data for dropdowns
        context['stores'] = Store.objects.all()
        context['vendors'] = Vendor.objects.all()
        context['departments'] = Department.objects.all()
        context['items'] = Item.objects.all()
        
        # Add existing inventory requests for sidebar
        context['inventory_requests'] = InventoryRequest.objects.all().order_by('-id')[:10]
        
        return context
    
    def form_valid(self, form):
        """Process the form submission, including items and attachments"""
        # Set the owner to current user
        form.instance.owner = self.request.user
        
        # Save the main form first to get an ID
        response = super().form_valid(form)
        
        # Process selected items (multiple selection)
        item_ids = self.request.POST.getlist('items')
        if item_ids:
            for item_id in item_ids:
                if item_id:  # Skip empty selections
                    item = Item.objects.get(pk=item_id)
                    self.object.items.add(item)
                    
                    
        

        # Process file attachments
        files = self.request.FILES.getlist('attachment')
        for file in files:
            attachment = ImageAttachment.objects.create(
                file=file,
                object_id=self.object.id,
                content_type=ContentType.objects.get_for_model(InventoryRequest)
            )
            self.object.attachment.add(attachment)
        
        return response
    
    

class InventoryRequestDetailView(LoginRequiredMixin, DetailView):
    """View for showing individual inventory request details with HTMX"""
    model = InventoryRequest
    template_name = 'partials/item_request_detail.html'
    context_object_name = 'inventory_request'
    
    def get(self, request, *args, **kwargs):
        """Handle GET request with HTMX support"""
        # Check if this is an HTMX request
        is_htmx = request.headers.get('HX-Request', False)
        
        if is_htmx:
            # For HTMX requests, return just the partial
            inventory_request = self.get_object()
            html = render_to_string(
                self.template_name,
                {'inventory_request': inventory_request},
                request
            )
            return HttpResponse(html)
        else:
            # For regular requests, use the standard DetailView behavior
            return super().get(request, *args, **kwargs)
        
    def post(self, request, *args, **kwargs):
        """Handle POST for updating the inventory request"""
        inventory_request = self.get_object()
        
        # Simple permission check
        if request.user != inventory_request.owner:
            return HttpResponse("Permission denied", status=403)
        
        # Update basic fields
        request_type = request.POST.get('request_type')
        if request_type:
            inventory_request.request_type = request_type
            
            # Handle vendor or store based on request type
            if request_type == 'vendor':
                vendor_id = request.POST.get('vendor')
                if vendor_id:
                    inventory_request.vendor = Vendor.objects.get(pk=vendor_id)
                    inventory_request.store = None
            else:
                store_id = request.POST.get('store')
                if store_id:
                    inventory_request.store = Store.objects.get(pk=store_id)
                    inventory_request.vendor = None
        
        # Update other fields
        if 'required_date' in request.POST and request.POST['required_date']:
            inventory_request.required_date = request.POST['required_date']
            
        if 'department' in request.POST and request.POST['department']:
            inventory_request.department = Department.objects.get(pk=request.POST['department'])
            
        if 'priority' in request.POST:
            inventory_request.priority = request.POST['priority']
        
        # Save the updated request
        inventory_request.save()
        
        # Process selected items (multiple selection)
        if 'items' in request.POST:
            # Clear existing items and add new ones
            inventory_request.items.clear()
            item_ids = request.POST.getlist('items')
            for item_id in item_ids:
                if item_id and item_id != '':
                    try:
                        item = Item.objects.get(pk=item_id)
                        inventory_request.items.add(item)
                    except Item.DoesNotExist:
                        pass
        
        # Process file attachments
        if request.FILES:
            files = request.FILES.getlist('attachment')
            for file in files:
                attachment = ImageAttachment.objects.create(
                    file=file,
                    name=file.name,
                    uploaded_by=request.user
                )
                inventory_request.attachment.add(attachment)
        
        # Return to the detail view (not edit mode)
        html = render_to_string(
            self.template_name,
            {'inventory_request': inventory_request},
            request
        )
        return HttpResponse(html)
    
    
    
class TransferView(LoginRequiredMixin, View):
    template_name = 'transfer_form.html'

    def get(self, request, *args, **kwargs):
        """Handle GET request to render the form with required context"""
        context = {
            'stores': Store.objects.all(),
            'items': Item.objects.all(),
            'select_from': User.objects.all(),
        }

        # Add recent transfers for sidebar or similar functionality
        context['transfers'] = Transfer.objects.all().order_by('-id')[:10]

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        """Handle POST request to create a new transfer"""
        form = TransferForm(request.POST, request.FILES)

        # Check if the form is valid
        if form.is_valid():
            # Create Transfer instance
            transfer = form.save(commit=False)
            transfer.user = request.user
            transfer.save()

            # Process selected items (multiple selection)
            item_ids = request.POST.getlist('items')
            for item_id in item_ids:
                if item_id:
                    item = Item.objects.get(pk=item_id)
                    transfer.items.add(item)

            # Process file attachments
            files = request.FILES.getlist('attachment')
            for file in files:
                attachment = ImageAttachment.objects.create(
                    file=file,
                    object_id=transfer.id,
                    content_type=ContentType.objects.get_for_model(Transfer),
                    uploaded_by=request.user
                )
                transfer.attachment.add(attachment)

            # Return JSON response or redirect
            return JsonResponse({'message': 'Transfer created successfully', 'transfer_id': transfer.id})

        # If form is invalid, return errors
        return JsonResponse({'errors': form.errors}, status=400)
 
class TransferDetailView(LoginRequiredMixin, DetailView):
    """View for showing individual transfer details with HTMX"""
    model = Transfer
    template_name = 'partials/transfer_detail.html'
    context_object_name = 'transfer'
    
    def get(self, request, *args, **kwargs):
        """Handle GET request with HTMX support"""
        # Check if this is an HTMX request
        is_htmx = request.headers.get('HX-Request', False)
        
        if is_htmx:
            # For HTMX requests, return just the partial
            transfer = self.get_object()
            html = render_to_string(
                self.template_name,
                {'transfer': transfer},
                request
            )
            return HttpResponse(html)
        else:
            # For regular requests, use the standard DetailView behavior
            return super().get(request, *args, **kwargs)
        
    def post(self, request, *args, **kwargs):
        """Handle POST for updating the transfer"""
        transfer = self.get_object()
        
        # Simple permission check
        if request.user != transfer.owner:
            return HttpResponse("Permission denied", status=403)
        
        # Update basic fields
        transfer_type = request.POST.get('type')
        if transfer_type:
            transfer.type = transfer_type
            
        # Handle select_from (user) and store (store)
        select_from_id = request.POST.get('select_from')
        if select_from_id:
            transfer.select_from = User.objects.get(pk=select_from_id)
        
        store_id = request.POST.get('store')
        if store_id:
            transfer.store = Store.objects.get(pk=store_id)
        
        # Update other fields
        transfer.remark = request.POST.get('remark', transfer.remark)
        transfer.status = request.POST.get('status', transfer.status)
        transfer.approval = request.POST.get('approval', transfer.approval)
        
        # Save the updated transfer
        transfer.save()
        
        # Process selected items (multiple selection)
        if 'items' in request.POST:
            # Clear existing items and add new ones
            transfer.items.clear()
            item_ids = request.POST.getlist('items')
            for item_id in item_ids:
                if item_id and item_id != '':
                    try:
                        item = Item.objects.get(pk=item_id)
                        transfer.items.add(item)
                    except Item.DoesNotExist:
                        pass
        
        # Process file attachments
        if request.FILES:
            files = request.FILES.getlist('attachment')
            for file in files:
                attachment = FileAttachment.objects.create(
                    file=file,
                    name=file.name,
                    uploaded_by=request.user
                )
                transfer.attachment.add(attachment)
        
        # Return to the detail view (not edit mode)
        html = render_to_string(
            self.template_name,
            {'transfer': transfer},
            request
        )
        return HttpResponse(html)
    
    
def asset_performance(request):

     return render(request, 'asset_performance.html' )
def inventory_summary(request):

     return render(request, 'inventory_summary.html' )

def category(request):

     return render(request, 'category.html' )

def subcategory(request):

     return render(request, 'subcategory.html' )

def model(request):

     return render(request, 'model.html' )

def manufacturer(request):

     return render(request, 'manufacturer.html' )

def warehouse(request):

     return render(request, 'warehouse.html' )

def unit_measurement(request):

     return render(request, 'unit_measurement.html' )


def movement_history(request):
  
     return render(request, 'movement_history.html' )

class InventoryListView(ListView):
    template_name = 'inventory.html'
    context_object_name = 'inventory_items'
    paginate_by = 10

    def get_queryset(self):
        return Asset.objects.select_related('category', 'subcategory').all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        
        # Calculate totals
        totals = queryset.aggregate(
            total_stock=Sum('quantity'),
            total_value=Sum(F('quantity') * F('unit_price'))
        )
        
        context.update({
            'total_stock': totals['total_stock'] or 0,
            'total_value': totals['total_value'] or 0,
            'assets': Asset.objects.all(),
            'categories': Category.objects.all(),
            'subcategories': Subcategory.objects.all(),
            'status_choices': [
                ("Available", "Available"),
                ("Low Stock", "Low Stock"),
                ("Out of Stock", "Out of Stock"),
                ("Discontinued", "Discontinued"),
            ],
        })
        
        return context

@api_view(['GET'])
def get_asset_details(request, asset_id):
    try:
        asset = Asset.objects.select_related('category', 'subcategory').get(id=asset_id)
        data = {
            'category': asset.category_id,
            'category_name': asset.category.title,
            'subcategory': asset.subcategory_id,
            'subcategory_name': asset.subcategory.title,
            'unit_price': asset.unit_price,
            'reorder_level': asset.reorder_level,
            'min_stock_level': asset.min_stock_level,
            'max_stock_level': asset.max_stock_level,
        }
        return Response(data)
    except Asset.DoesNotExist:
        return Response({'error': 'Asset not found'}, status=404)

