from django.urls import path, include

from accounts.views import *

app_name = "accounts"

urlpatterns = [
    
    path('api/', include('accounts.api.urls'), name='reference'),
    

]


