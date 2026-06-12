from django.contrib import admin
from .models import Site, Report


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ['name', 'path', 'created_at']
    search_fields = ['name']


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['site', 'overall_health', 'created_at']
    list_filter = ['overall_health', 'site']
    search_fields = ['site__name']
    readonly_fields = ['created_at']
