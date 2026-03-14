from django.urls import path
from accounts.views import (
    DepartmentView, DepartmentDetailView,
    CategoryView, CategoryDetailView,
    BankAccountView, BankAccountDetailView,
    UnitOfMeasurementView, UnitOfMeasurementDetailView,
    VendorView, VendorDetailView,
    ClientView, ClientDetailView,
    PersonnelView, PersonnelDetailView,
    UserView, UserDetailView
)

app_name = "reference"

urlpatterns = [
    # Department URLs
    path('department/', DepartmentView.as_view(), name='department'),
    path('department/<str:code>/', DepartmentDetailView.as_view(), name='department_detail'),
    
    # Category URLs
    path('category/', CategoryView.as_view(), name='category'),
    path('category/<str:code>/', CategoryDetailView.as_view(), name='category_detail'),
    
    # Bank Account URLs
    path('bank-account/', BankAccountView.as_view(), name='bank_account'),
    path('bank-account/<str:slug>/', BankAccountDetailView.as_view(), name='bank_account_detail'),
    
    # Unit of Measurement URLs
    path('unit-of-measurement/', UnitOfMeasurementView.as_view(), name='unit_of_measurement'),
    path('unit-of-measurement/<str:code>/', UnitOfMeasurementDetailView.as_view(), name='unit_of_measurement_detail'),
    
    # Vendor URLs
    path('vendor/', VendorView.as_view(), name='vendor'),
    path('vendor/<str:slug>/', VendorDetailView.as_view(), name='vendor_detail'),
    
    # Client URLs
    path('client/', ClientView.as_view(), name='client'),
    path('client/<str:slug>/', ClientDetailView.as_view(), name='client_detail'),
    
    # Personnel URLs
    path('personnel/', PersonnelView.as_view(), name='personnel'),
    path('personnel/<str:slug>/', PersonnelDetailView.as_view(), name='personnel_detail'),
    
    # User URLs
    path('users/', UserView.as_view(), name='users'),
    path('users/<str:slug>/', UserDetailView.as_view(), name='user_detail'),
]

