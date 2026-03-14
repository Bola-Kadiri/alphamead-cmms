from django.urls import path, include
from work import views

app_name = "work"

urlpatterns = [
    path('api/', include('work.api.urls'), name='facility'),

]