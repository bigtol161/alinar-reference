from django.db.models import Count

from .models import Category


def categories_menu(request):
    return {'footer_categories': Category.objects.all()[:6]}
