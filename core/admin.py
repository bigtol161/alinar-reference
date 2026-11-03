from django.contrib import admin

from .models import Category, District, Master, Review, Service, ServiceRequest


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'sort_order')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ('name',)


class ServiceInline(admin.TabularInline):
    model = Service
    extra = 0


class ReviewInline(admin.TabularInline):
    model = Review
    extra = 0


@admin.register(Master)
class MasterAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'title', 'rating', 'reviews_count', 'verified', 'online')
    list_filter = ('category', 'verified', 'online')
    search_fields = ('name', 'title', 'phone')
    inlines = [ServiceInline, ReviewInline]


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('author', 'master', 'rating', 'created_at')
    list_filter = ('rating',)


@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = ('number', 'service', 'name', 'phone', 'status', 'created_at')
    list_filter = ('status', 'category')
    search_fields = ('number', 'name', 'phone')
