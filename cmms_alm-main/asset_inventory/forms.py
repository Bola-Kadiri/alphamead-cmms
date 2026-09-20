from django import forms
from .models import *

class AssetForm(forms.ModelForm):
    class Meta:
        model = Asset
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ('facility', 'zone', 'subsystem', 'category', 'subcategory'):
            self.fields[field_name].required = True

class AssetImportForm(forms.Form):
    csv_file = forms.FileField(
        label="CSV file",
        help_text=(
            "Columns: site_code, zone_code, subzone_name, system_name, "
            "component_name, description, asset_tag, qr_code, asset_status. "
            "Sites, zones and spaces referenced in the file are created "
            "automatically if they don't already exist."
        ),
    )

    def clean_csv_file(self):
        f = self.cleaned_data['csv_file']
        if not f.name.lower().endswith('.csv'):
            raise forms.ValidationError("Please upload a .csv file.")
        return f
    
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