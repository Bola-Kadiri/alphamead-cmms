from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.contrib.contenttypes.models import ContentType
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import get_user_model

from facility.models import Facility, Building, Apartment
from accounts.models import Client, Department, Category, Vendor, BankAccount,  UnitOfMeasurement, Subcategory
from asset_inventory.models import Warehouse
from utils.models import FileAttachment
from .models import User, Personnel, Contact

User = get_user_model()


class LoginForm(AuthenticationForm):
    """Custom login form for email authentication."""
    
    username = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Email Address',
                'autofocus': True
            }
        )
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Password'
            }
        )
    )
    
    error_messages = {
        'invalid_login': 'Please enter a correct email and password. Note that both fields may be case-sensitive.',
        'inactive': 'This account is inactive.',
    }

class UserRegisterForm(forms.ModelForm):
    """
    A form for registering new users. Includes all fields from the User model,
    plus a repeated password field for confirmation.
    """
    password = forms.CharField(widget=forms.PasswordInput, label="Password")
    password_2 = forms.CharField(label='Confirm Password', widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = [
            'email', 'first_name', 'last_name', 'phone', 'roles', 'designation', 'supervisor',
            'date_of_birth', 'gender', 'nationality', 'passport_number', 'address', 'status',
            'team_lead', 'generate_reports', 'approval_limit', 'is_verified', 'is_blocked',
            'is_active', 'is_staff', 'is_admin', 'is_superuser'
        ]

    def clean_email(self):
        """
        Verify email is available.
        """
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email already exists.")
        return email

    def clean(self):
        """
        Verify both passwords match.
        """
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_2 = cleaned_data.get("password_2")
        if password and password != password_2:
            raise forms.ValidationError("Your passwords must match.")
        return cleaned_data

    def save(self, commit=True):
        """
        Save the provided password in hashed format.
        """
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user



class UserChangeForm(forms.ModelForm):
    """
    A form for updating users. Includes all the fields on
    the user but replaces the password field with admin's
    disabled password hash display field.
    """
    password = ReadOnlyPasswordHashField()

    class Meta:
        model = User
        fields = [
            'email', 'password', 'first_name', 'last_name', 'roles', 'phone', 'designation',
            'supervisor', 'date_of_birth', 'gender', 'nationality', 'passport_number', 'address',
            'status', 'team_lead', 'generate_reports', 'approval_limit', 'is_verified', 'is_blocked',
            'is_active', 'is_staff', 'is_admin', 'is_superuser', 'access_to_all_facilities',
            'facility', 'access_to_all_buildings', 'buildings', 'access_to_all_apartments', 'apartments',
             'access_to_all_categories', 'categories',
            'access_to_all_warehouses', 'warehouse', 'access_to_all_clients', 'clients'
        ]


class UserAdminCreationForm(forms.ModelForm):
    """
    A form for creating new users. Includes all the required
    fields, plus a repeated password.
    """
    password = forms.CharField(widget=forms.PasswordInput)
    password_2 = forms.CharField(label='Confirm Password', widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = [
            'email', 'password', 'first_name', 'last_name', 'roles', 'phone', 'designation',
            'date_of_birth', 'gender', 'nationality', 'passport_number', 'address', 'status',
            'is_verified', 'is_blocked', 'is_active', 'is_staff', 'is_admin', 'is_superuser',
        ]

    def clean(self):
        """
        Verify both passwords match.
        """
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_2 = cleaned_data.get("password_2")
        if password and password != password_2:
            raise forms.ValidationError("Your passwords must match")
        return cleaned_data

    def save(self, commit=True):
        """
        Save the provided password in hashed format.
        """
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user

class UserAdminChangeForm(forms.ModelForm):
    """A form for updating users. Includes all the fields on
    the user, but replaces the password field with admin's
    password hash display field.
    """
    password = ReadOnlyPasswordHashField()

    class Meta:
        model = User
        fields = ['email', 'password', 'is_active', 'is_superuser',]

    def clean_password(self):
        # Regardless of what the user provides, return the initial value.
        # This is done here, rather than on the field, because the
        # field does not have access to the initial value
        return self.initial["password"]
    
    
class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'roles', 'email', 'phone', 'designation', 
            'supervisor', 'date_of_birth', 'gender', 'nationality', 'passport_number', 
            'address', 'status', 'team_lead', 'generate_reports', 'approval_limit', 
            'is_verified', 'is_blocked', 'is_active', 'is_staff', 'is_admin', 'is_superuser',
            'access_to_all_facilities', 'facility', 'access_to_all_buildings', 'buildings',
            'access_to_all_apartments', 'apartments', 
            'access_to_all_categories', 'categories', 'access_to_all_warehouses',
            'warehouse', 'access_to_all_clients', 'clients', 'categories', 'access_to_all_categories'
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'roles': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'nationality': forms.Select(attrs={'class': 'form-control'}),
        }

    def save(self, commit=True):
        # Save the main instance
        user = super().save(commit=False)
        user.set_password("TempPassword123")

        # Handle many-to-many fields
        if commit:
            user.save()
            
        if user.access_to_all_facilities:
            user.facility.set(Facility.objects.all())
        else:
            user.facility.set(self.cleaned_data.get('facility'))

        if user.access_to_all_buildings:
            user.buildings.set(Building.objects.all())
        else:
            user.buildings.set(self.cleaned_data.get('buildings'))
            
        if user.access_to_all_categories:
            user.categories.set(Category.objects.all())
        else:
            user.categories.set(self.cleaned_data.get('categories'))

        if user.access_to_all_apartments:
            user.apartments.set(Apartment.objects.all())
        else:
            user.apartments.set(self.cleaned_data.get('apartments'))


        if user.access_to_all_categories:
            user.categories.set(Category.objects.all())
        else:
            user.categories.set(self.cleaned_data.get('categories'))

        if user.access_to_all_warehouses:
            user.warehouse.set(Warehouse.objects.all())
        else:
            user.warehouse.set(self.cleaned_data.get('warehouse'))

        if user.access_to_all_clients:
            user.clients.set(Client.objects.all())
        else:
            user.clients.set(self.cleaned_data.get('clients'))

        return user

    def save_m2m(self):
        user = self.instance

        FIELD_MAPPING = [
            ("access_to_all_facilities",     "facility",              Facility,              "facilities"),
            ("access_to_all_buildings",      "buildings",             Building,              "buildings"),
            ("access_to_all_apartments",     "apartments",            Apartment,             "apartments"),
            ("access_to_all_categories",  "categories", Category,   "categories"),
            ("access_to_all_warehouses",     "warehouse",             Warehouse,             "warehouse"),
            ("access_to_all_clients",        "clients",               Client,                "clients"),
        ]

        for access_flag, m2m_field, model_class, subset_field in FIELD_MAPPING:
            # Check if "access to all" was checked in the form
            if self.cleaned_data.get(access_flag):
                # 1) Set the user's boolean field to True
                setattr(user, access_flag, True)
                # 2) Give them all objects from that model
                getattr(user, m2m_field).set(model_class.objects.all())
            else:
                # 1) Set the user's boolean field to False
                setattr(user, access_flag, False)
                # 2) Assign the subset or clear it
                subset = self.cleaned_data.get(subset_field)
                if subset:
                    getattr(user, m2m_field).set(subset)
                else:
                    getattr(user, m2m_field).clear()

        # Handle categories if it doesn’t have an “access to all” boolean
        categories = self.cleaned_data.get("categories")
        if categories:
            user.categories.set(categories)
        else:
            user.categories.clear()

        # Finally save
        user.save()

    # def save_m2m(self):
    #     """
    #     Handle many-to-many fields explicitly.
    #     """
    #     user = self.instance

    #     # Set many-to-many fields
    #     access_to_all_facilities = self.cleaned_data.get('access_to_all_facilities')
    #     access_to_all_flats = self.cleaned_data.get('access_to_all_flats')
    #     access_to_all_apartments = self.cleaned_data.get('access_to_all_apartments')
    #     access_to_all_categories = self.cleaned_data.get('access_to_all_categories')
    #     access_to_all_warehouses = self.cleaned_data.get('access_to_all_warehouses')

    #     # Assign relationships
    #     if access_to_all_facilities:
    #         user.access_to_all_facilities = access_to_all_facilities
    #         user.facility.set(access_to_all_facilities)       
    #     if access_to_all_flats:
    #         user.access_to_all_flats = access_to_all_flats
    #         user.flats.set(access_to_all_flats)           
    #     if access_to_all_apartments:
    #         user.access_to_all_apartments = access_to_all_apartments
    #         user.apartments.set(access_to_all_apartments)       
    #     if access_to_all_categories:
    #         user.categories = access_to_all_categories
    #         user.categories.set(categories)
    #     if access_to_all_warehouses:
    #         user.access_to_all_warehouses = access_to_all_warehouses
    #         user.warehouse.set(access_to_all_warehouses)
    #     if self.access_to_all_clients:
    #         user.access_to_all_clients = self.access_to_all_clients
            
        
    #     flats = self.cleaned_data.get('flats')
    #     apartments = self.cleaned_data.get('apartments')
    #     categories = self.cleaned_data.get('categories')
    #     categories = self.cleaned_data.get('categories')
    #     warehouse = self.cleaned_data.get('warehouse')
    #     clients = self.cleaned_data.get('clients')
        
            
            
    #     if flats:
    #         user.flats.set(flats)
    #     if apartments:
    #         user.apartments.set(apartments)
    #     if categories:
    #         user.categories.set(categories)
    #     if categories:
    #         user.categories.set(categories)
    #     if warehouse:
    #         user.warehouse.set(warehouse)
    #     if clients:
    #         user.clients.set(clients)

    #     # Save related fields
    #     user.save()


class PersonnelForm(forms.ModelForm):
    documents = forms.FileField(
        widget=forms.FileInput(attrs={ 'class': 'form-control'}),  # FIXED: Use FileInput instead of ClearableFileInput
        required=False  # Allow personnel creation without documents
    )
    
    class Meta:
        model = Personnel
        fields = [
            'owner', 'staff_number', 'facility', 'email', 'phone_number', 'avatar',
            'status', 'access_to_all_categories', 'categories', 'documents'
        ]
        widgets = {
            'staff_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter staff number'}),
            'facility': forms.Select(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter email address'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter phone number'}),
            'avatar': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
            'categories': forms.SelectMultiple(attrs={'class': 'form-control'}),
        }

    def save(self, commit=True):
        """
        Custom save method to handle multi-document upload.
        """
        personnel = super().save(commit=False)  # Save personnel instance but don't commit yet

        if commit:
            personnel.save()

            # Assign WorkRequestCategories if access to all is selected
            if personnel.access_to_all_categories:
                all_categories = Category.objects.all()
                personnel.categories.set(all_categories)
            else:
                personnel.categories.set(self.cleaned_data.get('categories'))

            # Handle multiple document uploads and add them to the ManyToManyField
            document_files = self.files.getlist("documents")
            file_attachments = []
        

            for file in document_files:
                file_attachment = FileAttachment.objects.create(
                    content_type=ContentType.objects.get_for_model(Personnel),
                    object_id=personnel.id,
                    file=file
                )
                file_attachments.append(file_attachment)

            # Link all created documents to the Personnel instance
            personnel.documents.add(*file_attachments)

        return personnel
    
    
class VendorForm(forms.ModelForm):
    class Meta:
        model = Vendor
        fields = ["name", "type", "phone", "email", "account_name", "bank", "account_number", "currency", "status"]



class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = [
             'type', 'code', 'name', 'email', 'phone', 'group', 
            'address', 'contacts', 'status',
        ]
        widgets = {
            'type': forms.Select(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter client code'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter client name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter email address'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter phone number'}),
            'group': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter group name'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Enter address', 'rows': 3}),
        }

    def save(self, commit=True):
        # Save the main instance
        client = super().save(commit=False)
        if commit:
            client.save()
        return client
    
    
class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ['first_name', 'last_name', 'email', 'phone', 'status']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter first name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter last name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter email'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter phone number'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }

    
    
class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = [
            'code', 'description', 'problem_type', 'work_request_approved',
            'exclude_costing_limit', 'power', 'create_payment_requisition',
        ]
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter unique code'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Enter description', 'rows': 3}),
            'problem_type': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Enter problem type', 'rows': 3}),
            'work_request_approved': forms.Select(attrs={'class': 'form-control'}),
            'exclude_costing_limit': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'power': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'create_payment_requisition': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def save(self, commit=True):
        # Save the main instance
        category = super().save(commit=False)
        if commit:
            category.save()
        return category
    
    
class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['code', 'name', 'email', 'phone', 'status']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter unique department code'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter department name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter department email'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter department phone (optional)'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }

    def save(self, commit=True):
        # Save the main instance
        department = super().save(commit=False)
        if commit:
            department.save()
        return department
    
    
class BankAccountForm(forms.ModelForm):
    class Meta:
        model = BankAccount
        fields = [
            'bank', 'account_name', 'account_number', 
            'currency', 'address', 'details', 'status', 'owner',
        ]
        widgets = {
            'bank': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter bank name'}),
            'account_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter account holder name'}),
            'account_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter account number'}),
            'currency': forms.Select(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Enter address (optional)', 'rows': 3}),
            'details': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Enter additional details (optional)', 'rows': 3}),
        }

    def save(self, commit=True):
        # Save the main instance
        bank_account = super().save(commit=False)
        if commit:
            bank_account.save()
        return bank_account
    

class UnitOfMeasurementForm(forms.ModelForm):
    class Meta:
        model = UnitOfMeasurement
        fields = ['code', 'description', 'symbol', 'type', 'status', ]

    def save(self, commit=True):
        # Save the main instance
        unit = super().save(commit=False)
        if commit:
            unit.save()
        return unit


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = [
            'code', 'title', 'description', 'problem_type', 
            'work_request_approved', 'exclude_costing_limit', 
            'power', 'create_payment_requisition'
        ]
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter unique code'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Enter description', 'rows': 3}),
            'problem_type': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Enter problem type', 'rows': 3}),
            'work_request_approved': forms.Select(attrs={'class': 'form-control'}),
            'exclude_costing_limit': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'power': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'create_payment_requisition': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def save(self, commit=True):
        category = super().save(commit=False)
        if commit:
            category.save()
        return category

class SubcategoryForm(forms.ModelForm):
    class Meta:
        model = Subcategory
        fields = [ 'description', 'title', 'exclude_costing_limit', 'status']
        widgets = {
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Enter description', 'rows': 3}),
            'exclude_costing_limit': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def save(self, commit=True):
        subcategory = super().save(commit=False)
        if commit:
            subcategory.save()
        return subcategory

