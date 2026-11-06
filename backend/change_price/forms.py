from django import forms
from .models import PriceHistory
from category.models import Category, PriceType


class CategoryPriceUpdateForm(forms.Form):
    def __init__(self, category, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.category = category
        
        # Get all price types for this category
        price_types = PriceType.objects.filter(category=category)
        
        # Create fields for each price type
        for price_type in price_types:
            self.fields[f'price_{price_type.id}'] = forms.DecimalField(
                label=f'Price - {price_type.name}',
                min_value=0,
                decimal_places=2,
                required=False,
                widget=forms.NumberInput(attrs={
                    'class': 'form-control theme-input',
                    'placeholder': f'Enter new price for {price_type.name} (leave empty to keep current)',
                    'step': '0.01',
                    'min': '0'
                })
            )
    
    notes = forms.CharField(
        label='Notes',
        widget=forms.Textarea(attrs={
            'class': 'form-control theme-input',
            'rows': 3,
            'placeholder': 'Enter any notes about this price update (optional)'
        }),
        required=False
    )


class PriceUpdateForm(forms.ModelForm):
    class Meta:
        model = PriceHistory
        fields = ['price', 'notes']
        widgets = {
            'price': forms.NumberInput(attrs={
                'class': 'form-control theme-input',
                'placeholder': 'Enter price',
                'step': '0.01',
                'min': '0'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control theme-input',
                'rows': 3,
                'placeholder': 'Enter any notes about this price update (optional)'
            })
        }