# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from .models import SelectedCategory, FootprintParameterMapping, ProgressIndicator


class FootprintParameterMappingAdmin(admin.TabularInline):
    model = FootprintParameterMapping
    extra = 0


class SelectedCategoryAdmin(admin.ModelAdmin):
    """Admin class for the SelectedCategory model"""

    inlines = [FootprintParameterMappingAdmin]
    list_display = [f.name for f in SelectedCategory._meta.fields]
    list_per_page = 25

    autocomplete_fields = ['category']


class ProgressIndicatorAdmin(admin.ModelAdmin):
    """Admin class for the Progress Indicator model"""

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    readonly_fields = [field.name for field in ProgressIndicator._meta.get_fields()]

    list_display = [f.name for f in ProgressIndicator._meta.fields]
    list_per_page = 25


admin.site.register(FootprintParameterMapping)
admin.site.register(SelectedCategory, SelectedCategoryAdmin)
admin.site.register(ProgressIndicator, ProgressIndicatorAdmin)
