from django import forms
from .models import *

class AssetForm(forms.ModelForm):
    class Meta:
        model = Asset
        fields = '__all__'
    
class TransferForm(forms.ModelForm):
    # items = forms.ModelMultipleChoiceField(
    #     queryset=Item.objects.all(),
    #     widget=forms.CheckboxSelectMultiple,
    #     required=False
    # )
    # select_from = forms.ModelChoiceField(
    #     queryset=User.objects.all(),
    #     required=True
    # )
    # store = forms.ModelChoiceField(
    #     queryset=Store.objects.all(),
    #     required=True
    # )
    
    class Meta:
        model = Transfer
        fields = '__all__'