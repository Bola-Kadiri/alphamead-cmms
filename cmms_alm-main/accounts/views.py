import json

from django.shortcuts import render, HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, Http404
from django.contrib.auth import login, logout
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import FormView, TemplateView, View
from django.urls import reverse_lazy
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.urls import reverse

from accounts.models import User, Personnel, Vendor, Client, Category, Department, BankAccount, UnitOfMeasurement, Contact, Subcategory
from accounts.forms import UserForm, PersonnelForm, VendorForm, ClientForm, CategoryForm, DepartmentForm, BankAccountForm, UnitOfMeasurementForm, SubcategoryForm

from facility.models import Facility, Building, Apartment
from asset_inventory.models import Warehouse
from accounts.models import Category

from .forms import LoginForm


@csrf_exempt  # or use a proper CSRF token with your HTMX requests
def check_email(request):
    """
    This view is hit by htmx to check if an email is already in use.
    Returns a small HTML/text snippet that will be injected into the page.
    """
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        if User.objects.filter(email=email).exists():
            return HttpResponse("<span style='color:red'>Email already taken</span>")
        else:
            return HttpResponse("<span style='color:green'>Email is available</span>")
    return HttpResponse("Invalid request", status=400)


class LoginView(FormView):
    """Class-based view for handling user login with email and password."""
    
    template_name = 'login.html'
    form_class = LoginForm
    success_url = reverse_lazy('dashboard:index')
    
    def dispatch(self, request, *args, **kwargs):
        # Redirect to dashboard if already logged in
        if request.user.is_authenticated:
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        # Log the user in
        login(self.request, form.get_user())
        messages.success(self.request, f"Welcome back, {form.get_user().email}!")
        
        # Redirect to next parameter if provided, otherwise to success_url
        next_url = self.request.GET.get('next')
        if next_url:
            return redirect(next_url)
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, "Invalid email or password.")
        return super().form_invalid(form)

class LogoutView(View):
    """Class-based view for handling user logout."""
    
    def get(self, request, *args, **kwargs):
        logout(request)
        messages.success(request, "You have been logged out.")
        return redirect('accounts:login')

class UserView(LoginRequiredMixin, View):
    def get(self, request):
        users = User.objects.all().order_by("-id")
        facilities = Facility.objects.all()
        buildings = Building.objects.all()
        apartments = Apartment.objects.all()
        clients = Client.objects.all()
        categories = Category.objects.all()
        warehouses = Warehouse.objects.all()
        categories = Category.objects.all()

        context = {
            "users": users,
            "facilities": facilities,
            "buildings": buildings,
            "apartments": apartments,
            "clients": clients,
            "categories": categories,
            "warehouses": warehouses,
            "categories": categories,
        }

        return render(request, "reference/users.html", context)
    
    def post(self, request):
        """
        Create a new user.
        """
        form = UserForm(request.POST)
        
        if form.is_valid():
            form.save()
            messages.success(request, "Congrats!! You've created a new user.")
            return redirect("accounts:users")
        else:
            error_messages = []
            for field_name, field_errors in form.errors.items():
                for error in field_errors:
                    # Format it however you like, e.g. "Email: User with this Email already exists."
                    error_msg = f"{field_name.capitalize()}: {error}"
                    messages.error(request, error_msg)
                        
        return redirect("accounts:users")


class UserDetailView(LoginRequiredMixin, View):
    
    def get(self, request, slug):
        """
        Retrieve details of a specific user by slug.
        Handles both HTMX requests (partial updates) and full-page requests.
        """
        user = get_object_or_404(User, slug=slug)
        users = User.objects.all()

        # Context data for the template
        context = {
            "users": users,
            "user": user,
        }

        # Check if the request is an HTMX request
        if request.htmx:
            return render(request, "reference/partials/user_detail_partial.html", context)

        # Render the full template for non-HTMX requests
        return render(request, "reference/users.html", context)

    def put(self, request, slug):
        """
        Update an existing user by ID.
        """
        user = get_object_or_404(User, id=id)
        form = UserForm(request.POST, instance=user)  # Use `request.POST` for rendering the form in the template
        if form.is_valid():
            form.save()
            return redirect("user_list")  # Redirect to the user list after successful update
        return render(request, "reference/user_detail.html", {"form": form, "user": user})

    def delete(self, request, slug):
        """
        Delete an existing user by ID.
        """
        user = get_object_or_404(User, id=id)
        if request.method == "POST":  # Render a confirmation page for deletion
            user.delete()
            return redirect("user_list")  # Redirect to the user list after deletion
        return render(request, "reference/user_detail.html", {"user": user})
    
  
class PersonnelView(LoginRequiredMixin, View):
    def get(self, request):
        """
        Handle GET requests: Load the personnel page with necessary context data.
        """
        users = User.objects.exclude(
            id__in=Personnel.objects.values_list('user_id', flat=True)
        )
        facilities = Facility.objects.all()
        categories = Category.objects.all()

        context = {
            "personnels": Personnel.objects.all(),
            "facilities": facilities,
            "users": users,
            "categories": categories,
        }
        
        return render(request, "reference/personnel.html", context)

    def post(self, request):
        """
        Handle POST requests: Create or update personnel records.
        """
        form = PersonnelForm(request.POST, request.FILES)  # Include request.FILES for file uploads

        if form.is_valid():
            form.save()
            messages.success(request, "Personnel record has been successfully created.")
            return redirect("accounts:personnel")  # Replace with the appropriate URL name
        else:
            for field_name, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field_name.capitalize()}: {error}")

        return redirect("accounts:personnel")
    
    
class PersonnelDetailView(LoginRequiredMixin, View):
    
    def get(self, request, slug):
        """
        Retrieve details of a specific user by slug.
        Handles both HTMX requests (partial updates) and full-page requests.
        """

        context = {
            "personnels": Personnel.objects.all(),
            "personnel": Personnel.objects.get(user__slug=slug),
        }

        # Check if the request is an HTMX request
        if request.htmx:
            return render(request, "reference/partials/personnel_detail_partial.html", context)

        # Render the full template for non-HTMX requests
        return render(request, "reference/users.html", context)
    
    

class VendorView(LoginRequiredMixin, View):
    def get(self, request):
        """
        Handle GET requests: Load the vendor page with necessary context data.
        """
        # Exclude users already associated with a Vendor

        categories = Category.objects.all()
        facilities = Facility.objects.all()

        context = {
            "vendors": Vendor.objects.all(),
      
            "categories": categories,
            "facilities": facilities,
        }

        return render(request, "reference/vendor.html", context)

    def post(self, request):
        """
        Handle POST requests: Create or update vendor records.
        """
        form = VendorForm(request.POST, request.FILES)  # Include request.FILES for file uploads

        if form.is_valid():
            form.save()
            messages.success(request, "Vendor record has been successfully created.")
            return redirect("accounts:vendor")
        else:
            for field_name, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field_name.capitalize()}: {error}")

        return redirect("accounts:vendor")


class VendorDetailView(LoginRequiredMixin, View):
    def get(self, request, slug):
        """
        Retrieve details of a specific vendor by slug.
        Handles both HTMX requests (partial updates) and full-page requests.
        """
        context = {
            "vendors": Vendor.objects.all(),
            "vendor": Vendor.objects.get(slug=slug),
        }

        # Check if the request is an HTMX request
        if request.htmx:
            return render(request, "reference/partials/vendor_detail_partial.html", context)

        # Render the full template for non-HTMX requests
        return render(request, "reference/vendor_detail.html", context)
    
    
class ClientView(LoginRequiredMixin, View):
    def get(self, request):
        """
        Handle GET requests: Load the client page with necessary context data.
        """
        # Exclude users already associated with a Client
        users = User.objects.exclude(
            id__in=Client.objects.values_list('owner_id', flat=True)
        )

        context = {
            "clients": Client.objects.all(),
            "users": users,
        }

        return render(request, "reference/client.html", context)

    def post(self, request):
        """
        Handle POST requests: Create a new client and dynamically add multiple contacts.
        """
        client_form = ClientForm(request.POST)

        if client_form.is_valid():
            client = client_form.save()  # Save client instance

            # Extract contact data from form
            contact_first_names = request.POST.getlist("contact_first_name[]")
            contact_last_names = request.POST.getlist("contact_last_name[]")
            contact_emails = request.POST.getlist("contact_email[]")
            contact_phones = request.POST.getlist("contact_phone[]")
            contact_statuses = request.POST.getlist("contact_status[]")

            # Create and link contacts
            contact_instances = []  
            for i in range(len(contact_first_names)):
                contact = Contact.objects.create(
                    first_name=contact_first_names[i],
                    last_name=contact_last_names[i],
                    email=contact_emails[i],
                    phone=contact_phones[i],
                    status=contact_statuses[i]
                )
                contact_instances.append(contact)

            # Save contacts to the client's Many-to-Many field
            client.contacts.set(contact_instances)

            messages.success(request, "Client and contacts created successfully.")
            return redirect("accounts:client")

        else:
            for field_name, errors in client_form.errors.items():
                for error in errors:
                    messages.error(request, f"{field_name.capitalize()}: {error}")

        return redirect("accounts:client")


    
    # def post(self, request):
    #     """
    #     Handle POST requests: Create or update client records.
    #     """
    #     form = ClientForm(request.POST, request.FILES)  # Include request.FILES for file uploads

    #     if form.is_valid():
    #         form.save()
    #         messages.success(request, "Client record has been successfully created.")
    #         return redirect("accounts:client")  # Replace with the appropriate URL name
    #     else:
    #         for field_name, errors in form.errors.items():
    #             for error in errors:
    #                 messages.error(request, f"{field_name.capitalize()}: {error}")

    #     return redirect("accounts:client")


class ClientDetailView(LoginRequiredMixin, View):
    def get(self, request, slug):
        """
        Retrieve details of a specific client by slug.
        Handles both HTMX requests (partial updates) and full-page requests.
        """
        context = {
            "clients": Client.objects.all(),
            "client": Client.objects.get(slug=slug),
        }

        # Check if the request is an HTMX request
        if request.htmx:
            return render(request, "reference/partials/client_detail_partial.html", context)

        # Render the full template for non-HTMX requests
        return render(request, "reference/client_detail.html", context)
    
class CategoryView(LoginRequiredMixin, View):
    def get(self, request):
        """
        Handle GET requests: Load the category page with necessary context data.
        """
        context = {
            "categories": Category.objects.all(),
        }
        return render(request, "reference/category.html", context)

    def post(self, request):
        """
        Handle POST requests: Create or update category records.
        """
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Category has been successfully created.")
            return redirect("accounts:category")  # Replace with the appropriate URL name
        else:
            for field_name, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field_name.capitalize()}: {error}")

        return redirect("accounts:category")


class CategoryDetailView(LoginRequiredMixin, View):
    def get(self, request, code):
        """
        Retrieve details of a specific category by slug.
        Handles both HTMX requests (partial updates) and full-page requests.
        """
        wo = Category.objects.get(code=code)
        context = {
            "category": wo,
            "categories": Category.objects.all(),
            "subcategories": Subcategory.objects.filter(category=wo),
        }
        

        if request.htmx:
            return render(request, "reference/partials/category_detail.html", context)

        # Render the full template for non-HTMX requests
        return render(request, "reference/category.html", context)
    
    def post(self, request, code):
        """
        Handle POST requests: Create a new subcategory under the selected category.
        """
        category = get_object_or_404(Category, code=code)
        form = SubcategoryForm(request.POST)

        if form.is_valid():
            subcategory = form.save(commit=False)
            subcategory.category = category  # Assign the subcategory to the selected category
            subcategory.save()

            messages.success(request, "Subcategory has been successfully created.")
            return redirect(reverse("accounts:category_detail", kwargs={"code": code}))

        else:
            for field_name, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field_name.capitalize()}: {error}")

        return redirect(reverse("accounts:category_detail", kwargs={"code": code}))
        
    
def data_facility(request):

     return render(request, 'reference/data_facility.html' )


def data_inventory(request):

     return render(request, 'reference/data_inventory.html' )


def category_pro(request):

     return render(request, 'reference/category_pro.html' )




class DepartmentView(LoginRequiredMixin, View):
    def get(self, request):
        """
        Handle GET requests: Load the department page with necessary context data.
        """
        context = {
            "form": DepartmentForm(),
        }
        return render(request, "reference/department.html", context)

    def post(self, request):
        """
        Handle POST requests: Create or update department records.
        """
        form = DepartmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Department has been successfully created.")
            return redirect("accounts:department")  # Replace with the appropriate URL name
        else:
            for field_name, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field_name.capitalize()}: {error}")

        return redirect("accounts:department")


class DepartmentDetailView(LoginRequiredMixin, View):
    def get(self, request, code):
        """
        Retrieve details of a specific department by primary key (pk).
        """
        department = get_object_or_404(Department, code=code)
        context = {
            "department": department,
            "form": DepartmentForm(instance=department),
        }
        
        if request.htmx:
            return render(request, "reference/partials/department_detail_partial.html", context)
        
        return render(request, "reference/department.html", context)

    def post(self, request, code):
        """
        Handle POST requests to update a specific department.
        """
        department = get_object_or_404(Department, code=code)
        form = DepartmentForm(request.POST, instance=department)
        if form.is_valid():
            form.save()
            messages.success(request, "Department has been successfully updated.")
            return redirect("reference:department_detail", code=code)  # Replace with the appropriate URL name
        else:
            for field_name, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field_name.capitalize()}: {error}")

        return redirect("reference:department_detail", code=code)
    
    

class BankAccountView(LoginRequiredMixin, View):
    def get(self, request):
        """
        Handle GET requests: Load the bank account page with necessary context data.
        """
        users = User.objects.exclude(
            id__in=BankAccount.objects.values_list('user_id', flat=True)
        )
        context = {
            "bank_accounts": BankAccount.objects.all(),
            "users": users,
        }
        return render(request, "reference/bank_account.html", context)

    def post(self, request):
        """
        Handle POST requests: Create or update bank account records.
        """
        form = BankAccountForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Bank account has been successfully created.")
            return redirect("accounts:bank_account")  # Replace with the appropriate URL name
        else:
            for field_name, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field_name.capitalize()}: {error}")

        return redirect("accounts:bank_account")


class BankAccountDetailView(LoginRequiredMixin, View):
    def get(self, request, slug):
        """
        Retrieve details of a specific bank account by primary key (slug).
        """
        bank_account = get_object_or_404(BankAccount, slug=slug)
        context = {
            "bank_account": bank_account,
            "form": BankAccountForm(instance=bank_account),
        }
        return render(request, "reference/partials/bank_detail_partial.html", context)

    def post(self, request, slug):
        """
        Handle POST requests to update a specific bank account.
        """
        bank_account = get_object_or_404(BankAccount, slug=slug)
        
        # Process the form data
        form = BankAccountForm(request.POST, instance=bank_account)
        if form.is_valid():
            updated_account = form.save()
            messages.success(request, "Bank account has been successfully updated.")
            
            # Redirect back to the main bank account page
            return redirect("accounts:bank_account")
        else:
            # Handle form validation errors
            for field_name, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field_name.capitalize()}: {error}")
            
            # Redirect back to the main bank account page
            return redirect("accounts:bank_account")
    

class UnitOfMeasurementView(LoginRequiredMixin, View):
    def get(self, request):
        """
        Handle GET requests: Load the unit of measurement page with necessary context data.
        """
        context = {
            "units": UnitOfMeasurement.objects.all(),
            "form": UnitOfMeasurementForm(),
        }
        return render(request, "reference/unit_measurement.html", context)

    def post(self, request):
        """
        Handle POST requests: Create or update unit of measurement records.
        """
        form = UnitOfMeasurementForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Unit of Measurement has been successfully created.")
            return redirect("accounts:unit_of_measurement")  # Replace with the appropriate URL name
        else:
            for field_name, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field_name.capitalize()}: {error}")

        return redirect("accounts:unit_of_measurement")


class UnitOfMeasurementDetailView(LoginRequiredMixin, View):
    def get(self, request, code):
        """
        Retrieve details of a specific unit of measurement by primary key (code).
        """
        unit = get_object_or_404(UnitOfMeasurement, code=code)

        context = {
            "unit": unit,
            "form": UnitOfMeasurementForm(instance=unit),
        }
        
        if request.htmx:
            return render(request, "reference/partials/unit_of_measurement_detail_partial.html", context)
        
        return render(request, "reference/partials/unit_of_measurement_detail_partial.html", context)

