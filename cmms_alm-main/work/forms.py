from django import forms
from .models import WorkRequest, WorkOrder, PaymentRequisition, PPM
from utils.models import FileAttachment


class WorkRequestForm(forms.ModelForm):
    resources = forms.FileField(
        required=False
    )
    
    require_quotation = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'onchange': 'toggleRequestToField()'})
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    class Meta:
        model = WorkRequest
        fields = [
            'type', 'category', 'subcategory', 'department',
            'require_mobilization_fee', 'description', 'attachment',
            'requester', 'facility', 'asset',
            'approval_status', 'follow_up_notes', 'payment_requisition',
            'invoice_no', 'currency', 'add_discount', 'exclude_management_fee', 
            'priority', 'require_quotation', 'request_to', 'cost',
        ]

        widgets = {
            'type': forms.Select(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'subcategory': forms.Select(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'require_mobilization_fee': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Enter description', 'rows': 3}),
            'attachment': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
            'requester': forms.Select(attrs={'class': 'form-control'}),
            'facility': forms.Select(attrs={'class': 'form-control'}),
            'asset': forms.Select(attrs={'class': 'form-control'}),
            'approval_status': forms.Select(attrs={'class': 'form-control'}),
            'follow_up_notes': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Enter follow-up notes', 'rows': 3}),
            'payment_requisition': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'invoice_no': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter invoice number'}),
            'currency': forms.Select(attrs={'class': 'form-control'}),
            'add_discount': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'exclude_management_fee': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'request_to': forms.SelectMultiple(attrs={
                'class': 'form-control',
                'style': 'min-height: 120px;',
                'id': 'request_to_field'
            }),
        }

    def save(self, commit=True):
        """
        Save work request and handle multiple file attachments.
        """
        work_request = super().save(commit=False)
        
        # If require_quotation is False, clear the request_to field
        if not self.cleaned_data.get('require_quotation'):
            self.cleaned_data['request_to'] = []
            
        if commit:
            work_request.owner = self.request.user
            work_request.requester = self.request.user
            work_request.save()
            # Save many-to-many relationships
            self.save_m2m()
        
        # Handle multiple file uploads
        files = self.files.getlist('resources')
        for file in files:
            FileAttachment.objects.create(
                content_object=work_request,
                file=file
            )
        return work_request
    


class WorkOrderForm(forms.ModelForm):

    class Meta:
        model = WorkOrder
        fields = '__all__'
    
class PaymentRequisitionForm(forms.ModelForm):
    """
    Form for creating and updating Payment Requisition.
    """
    attachment = forms.FileField(
        required=False,
    )

    class Meta:
        model = PaymentRequisition
        fields = [
            'requisition_date', 'pay_to', 'expected_payment_date', 'retirement',
            'remark', 'status', 'approval_status', 'comment', 'withholding_tax',
            'expected_payment_amount', 'items'
        ]
        widgets = {
            'requisition_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'pay_to': forms.Select(attrs={'class': 'form-control'}),
            'expected_payment_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'retirement': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'remark': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'approval_status': forms.Select(attrs={'class': 'form-control'}),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'withholding_tax': forms.Select(attrs={'class': 'form-control'}),
            'expected_payment_amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter amount'}),
            'items': forms.SelectMultiple(attrs={'class': 'form-control select2', 'multiple': 'multiple'}),
        }

    def save(self, commit=True):
        """
        Custom save method to handle file attachments.
        """
        payment_requisition = super().save(commit=False)

        if commit:
            payment_requisition.save()
            self.save_m2m()  # Ensure many-to-many fields like 'items' are saved

            # Retrieve multiple file attachments from cleaned_data
            files = self.files.getlist('attachment')
            
            print("files ==== ", self.files)

            if files:
                for file in files:
                    FileAttachment.objects.create(content_object=payment_requisition, file=file)

        return payment_requisition
    
    
    
class PPMForm(forms.ModelForm):
    """
    Form for creating and updating Planned Preventive Maintenance (PPM).
    """

    class Meta:
        model = PPM
        fields = [
            "description", "category", "subcategory", "frequency", "frequency_unit",
            "notify_before_due", "notify_unit", "send_reminder_every", "reminder_unit",
            "currency", "auto_create_work_order", "create_work_order_as_approved",
            "assets", "facilities", "apartments", "items", "activities_safety_tips"
        ]
        widgets = {
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 2, "placeholder": "Describe this maintenance task"}),
            "category": forms.Select(attrs={"class": "form-control"}),
            "subcategory": forms.Select(attrs={"class": "form-control"}),
            "frequency": forms.NumberInput(attrs={"class": "form-control", "placeholder": "Enter frequency"}),
            "frequency_unit": forms.Select(attrs={"class": "form-control"}),
            "notify_before_due": forms.NumberInput(attrs={"class": "form-control", "placeholder": "Enter days/hours before notification"}),
            "notify_unit": forms.Select(attrs={"class": "form-control"}),
            "send_reminder_every": forms.NumberInput(attrs={"class": "form-control", "placeholder": "Enter reminder frequency"}),
            "reminder_unit": forms.Select(attrs={"class": "form-control"}),
            "currency": forms.Select(attrs={"class": "form-control"}),
            "auto_create_work_order": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "create_work_order_as_approved": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "assets": forms.SelectMultiple(attrs={"class": "form-control select2", "multiple": "multiple"}),
            "facilities": forms.SelectMultiple(attrs={"class": "form-control select2", "multiple": "multiple"}),
            "apartments": forms.SelectMultiple(attrs={"class": "form-control select2", "multiple": "multiple"}),
            "items": forms.SelectMultiple(attrs={"class": "form-control select2", "multiple": "multiple"}),
            "activities_safety_tips": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Provide safety tips or activity details"}),
        }

    def save(self, commit=True):
        """
        Custom save method for handling the many-to-many relationships.
        """
        ppm_instance = super().save(commit=False)

        if commit:
            ppm_instance.save()
            self.save_m2m()  # Ensures many-to-many fields like 'items' are saved

        return ppm_instance