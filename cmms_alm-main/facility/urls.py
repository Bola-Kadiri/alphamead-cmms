from django.urls import path, include
from facility import views

app_name = "facility"

urlpatterns = [
    path('api/', include('facility.api.urls'), name='facility'),

]