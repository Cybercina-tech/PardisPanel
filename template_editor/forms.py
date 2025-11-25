from django import forms
from .models import Template
from category.models import Category
from special_price.models import SpecialPriceType


class TemplateForm(forms.ModelForm):
    """Form for creating and editing templates."""
    
    class Meta:
        model = Template
        fields = ['name', 'category', 'special_price_type', 'image']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter template name'
            }),
            'category': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_category'
            }),
            'special_price_type': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_special_price_type'
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate category dropdown with all categories
        self.fields['category'].queryset = Category.objects.all().order_by('name')
        self.fields['category'].required = False
        self.fields['category'].empty_label = "Select a category (optional)"
        
        # Populate special_price_type dropdown with all special price types
        self.fields['special_price_type'].queryset = SpecialPriceType.objects.all().order_by('name')
        self.fields['special_price_type'].required = False
        self.fields['special_price_type'].empty_label = "Select a special price type (optional)"
    
    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get('category')
        special_price_type = cleaned_data.get('special_price_type')
        
        # Ensure only one is selected
        if category and special_price_type:
            raise forms.ValidationError(
                "Template cannot be assigned to both a category and a special price type. Please choose one."
            )
        
        return cleaned_data


class TextFieldConfigForm(forms.Form):
    """Dynamic form for configuring text fields."""
    
    field_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., english_date'
        })
    )
    x = forms.IntegerField(
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '0',
            'step': '1'
        })
    )
    y = forms.IntegerField(
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '0',
            'step': '1'
        })
    )
    font_size = forms.IntegerField(
        min_value=8,
        max_value=200,
        initial=32,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '8',
            'max': '200',
            'step': '1'
        })
    )
    font_weight = forms.CharField(
        max_length=20,
        required=False,
        initial='normal',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'normal, bold, etc.'
        })
    )
    color = forms.CharField(
        max_length=20,
        initial='#000000',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'type': 'color',
            'style': 'height: 40px;'
        })
    )
    alignment = forms.ChoiceField(
        choices=[
            ('left', 'Left'),
            ('center', 'Center'),
            ('right', 'Right'),
        ],
        initial='left',
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    max_width = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '0',
            'step': '1',
            'placeholder': 'Optional'
        })
    )

