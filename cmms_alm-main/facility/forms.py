from django import forms
from .models import Facility
from asset_inventory.models import Store 

class StoreForm(forms.ModelForm):
    class Meta:
        model = Store
        fields = ['code', 'name', 'location']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter store code'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter store name'}),
            'location': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Enter store location'}),
        }


class FacilityForm(forms.ModelForm):
    class Meta:
        model = Facility
        fields = '__all__'