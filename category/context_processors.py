from .models import Category

def categories_processor(request):
    """
    A context processor to make categories available in all templates.
    """
    return {
        'categories': Category.objects.prefetch_related('price_types').all()
    }