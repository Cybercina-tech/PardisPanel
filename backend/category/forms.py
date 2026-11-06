from django import forms
from .models import Category, PriceType, Currency

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description'] 
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter category name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional description'
            }),
        }


class PriceTypeForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.category = kwargs.pop('category', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get('name')

        if self.category and name:
            # Only check for duplicate name within the same category
            if PriceType.objects.filter(
                category=self.category,
                name=name
            ).exclude(pk=self.instance.pk if self.instance else None).exists():
                self.add_error('name', 'A price type with this name already exists in this category.')

        return cleaned_data

    class Meta:
        model = PriceType
        fields = ['name', 'source_currency', 'target_currency', 'trade_type', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter price type name'
            }),
            'source_currency': forms.Select(attrs={'class': 'form-select'}),
            'target_currency': forms.Select(attrs={'class': 'form-select'}),
            'trade_type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
