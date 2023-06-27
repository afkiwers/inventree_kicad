# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from .models import SelectedCategory

from part.models import PartCategory


class SelectedCategoryAdmin(admin.ModelAdmin):
    list_display = [f.name for f in SelectedCategory._meta.fields]
    list_per_page = 25

    # remove already chosen categories
    def get_form(self, request, obj=None, **kwargs):
        form = super(SelectedCategoryAdmin, self).get_form(request, obj, **kwargs)
        kicad_category_ids = SelectedCategory.objects.all().values_list('id', flat=True)
        form.base_fields['category'].queryset = PartCategory.objects.exclude(id__in=kicad_category_ids)

        return form


admin.site.register(SelectedCategory, SelectedCategoryAdmin)
