# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from .models import SelectedCategory


class SelectedCategoryAdmin(admin.ModelAdmin):
    """Admin class for the SelectedCategory model"""

    list_display = [f.name for f in SelectedCategory._meta.fields]
    list_per_page = 25

    autocomplete_fields = ['category']


admin.site.register(SelectedCategory, SelectedCategoryAdmin)
