from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, PersonnelViewSet, VendorViewSet, ClientViewSet, CategoryViewSet, BankAccountViewSet, UnitOfMeasurementViewSet, SubcategoryViewSet, DepartmentViewSet, OnboardingViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user'),
router.register(r'personnels', PersonnelViewSet, basename='personnel'),
router.register(r'vendors', VendorViewSet, basename='vendor'),
router.register(r'clients', ClientViewSet, basename='client')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'subcategories', SubcategoryViewSet, basename='subcategory')
router.register(r'bank-accounts', BankAccountViewSet, basename='bank-account')
router.register(r'departments', DepartmentViewSet, basename='department')
router.register(r'units', UnitOfMeasurementViewSet, basename='unit')
router.register(r'onboarding', OnboardingViewSet, basename='onboarding')

urlpatterns = [
    path('', include(router.urls)),
]
