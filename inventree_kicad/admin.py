# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from .models import SelectedCategory, ProgressIndicator


class SelectedCategoryAdmin(admin.ModelAdmin):
    """Admin class for the SelectedCategory model"""

    list_display = [f.name for f in SelectedCategory._meta.fields]
    list_per_page = 25

    autocomplete_fields = ['category']


class ProgressIndicatorAdmin(admin.ModelAdmin):
    """Admin class for the SelectedCategory model"""

    list_display = [f.name for f in ProgressIndicator._meta.fields]
    list_per_page = 25


admin.site.register(SelectedCategory, SelectedCategoryAdmin)
admin.site.register(ProgressIndicator, ProgressIndicatorAdmin)
