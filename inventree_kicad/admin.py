# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from .models import SelectedCategory, FootprintParameterMapping


class FootprintParameterMappingAdmin(admin.TabularInline):
    model = FootprintParameterMapping
    extra = 0


class SelectedCategoryAdmin(admin.ModelAdmin):
    """Admin class for the SelectedCategory model"""

    inlines = [FootprintParameterMappingAdmin]
    list_display = [f.name for f in SelectedCategory._meta.fields]
    list_per_page = 25

    autocomplete_fields = ['category']


admin.site.register(SelectedCategory, SelectedCategoryAdmin)
admin.site.register(FootprintParameterMapping)
