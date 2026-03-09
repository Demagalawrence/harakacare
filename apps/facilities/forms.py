from django import forms
from .models import Facility

class FacilityForm(forms.ModelForm):
    services_offered = forms.MultipleChoiceField(
        choices=Facility.MEDICAL_SERVICES_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        help_text='Select all medical services offered at this facility'
    )
    
    class Meta:
        model = Facility
        fields = [
            'name', 'facility_type', 'address', 'district', 'phone_number',
            'latitude', 'longitude', 'total_beds', 'available_beds', 'staff_count',
            'services_offered', 'average_wait_time_minutes', 'ambulance_available',
            'notification_endpoint', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter facility name'}),
            'facility_type': forms.Select(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter facility address'}),
            'district': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter district'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter phone number'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'}),
            'total_beds': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'available_beds': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'staff_count': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'average_wait_time_minutes': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'ambulance_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notification_endpoint': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://example.com/api/webhook'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # Set initial values for services_offered if editing existing facility
            self.fields['services_offered'].initial = self.instance.services_offered
