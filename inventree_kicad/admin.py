from django.contrib import admin

from .models import FootprintParameterMapping, SelectedCategory


class FootprintParameterMappingAdmin(admin.TabularInline):
    model = FootprintParameterMapping
    extra = 0


class SelectedCategoryAdmin(admin.ModelAdmin):
    """Admin class for the SelectedCategory model"""

    inlines = [FootprintParameterMappingAdmin]
    list_display = [f.name for f in SelectedCategory._meta.fields]
    list_per_page = 25

    autocomplete_fields = [
        "category",
        "default_value_parameter_template",
        "footprint_parameter_template",
    ]


admin.site.register(FootprintParameterMapping)
admin.site.register(SelectedCategory, SelectedCategoryAdmin)
