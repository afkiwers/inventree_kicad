"""

API endpoint for Kicad REST API library.

This plugin supplies the endpoints and data needed for KiCad to display selected categories and their
corresponding parts within the Kicad environment.

"""
import datetime

from django.conf.urls import url

from django.urls import include
from rest_framework import viewsets

from plugin import InvenTreePlugin
from plugin.mixins import UrlsMixin, AppMixin

from part.models import PartCategory, Part, PartParameterTemplate

from rest_framework import routers

from django.utils.translation import gettext_lazy as _


# ---------------------------- KiCad API Endpoint Plugin --------------------------------------------------
class KiCadLibraryPlugin(UrlsMixin, AppMixin, InvenTreePlugin):
    AUTHOR = "Andre Iwers"

    DESCRIPTION = _(
        "KiCad EDA conform API endpoint for KiCad's parts library tool. This plugin provides metadata only "
        "and requires matching symbol and footprint libraries within the KiCad EDA.")

    VERSION = "0.0.1"

    NAME = "KiCadLibraryPlugin"
    SLUG = "kicad"
    TITLE = "KiCad Library Endpoint"
    PUBLISH_DATE = datetime.date(2023, 6, 9)
    WEBSITE = "https://www.aioz.com.au"

    MIN_VERSION = '0.11.0'

    class CategoryViewSet(viewsets.ModelViewSet):
        from .serializers import KicadCategorySerializer

        serializer_class = KicadCategorySerializer
        queryset = PartCategory.objects.all()

        def get_queryset(self):
            from .models import SelectedCategory

            # Use user selected categories if available, otherwise display all.
            kicad_category_ids = SelectedCategory.objects.all().values_list('id', flat=True)

            if len(kicad_category_ids):
                queryset = PartCategory.objects.filter(id__in=kicad_category_ids)
            else:
                queryset = PartCategory.objects.all()

            return queryset

    class FieldViewSet(viewsets.ModelViewSet):
        from .serializers import KicadPartParameterTemplateSerializer

        serializer_class = KicadPartParameterTemplateSerializer
        queryset = PartParameterTemplate.objects.all()

    class PartViewSet(viewsets.ModelViewSet):
        from .serializers import KicadPartSerializer, KicadPreViewPartSerializer

        # general serialiser in use
        serializer_class = KicadPartSerializer

        def get_queryset(self):
            queryset = Part.objects.all()
            category_id = self.request.GET.get('table_id')
            part_id = self.request.GET.get('id')

            # general this will be a bulk transfer for the tree view. To speed things up only return bare minimum.
            if category_id:
                self.serializer_class = self.KicadPreViewPartSerializer
                queryset = queryset.filter(category=category_id)

            if part_id:
                queryset = queryset.filter(id=part_id)

            return queryset

    router_kicad = routers.DefaultRouter()
    router_kicad.register(r'category', CategoryViewSet, basename='kicad-category')
    router_kicad.register(r'field', FieldViewSet, basename='kicad-fields')
    router_kicad.register(r'part', PartViewSet, basename='kicad-parts')

    def setup_urls(self):
        """Returns the URLs defined by this plugin."""

        return [
            url(r'', include(self.router_kicad.urls)),
        ]
