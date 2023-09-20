"""

API endpoint for Kicad REST API library.

This plugin supplies the endpoints and data needed for KiCad to display selected categories and their
corresponding parts within the Kicad environment.

"""
import datetime
import os

from django.conf.urls import url
from django.urls import include, re_path
from django.utils.translation import gettext_lazy as _

from rest_framework import routers

from plugin import InvenTreePlugin
from plugin.mixins import UrlsMixin, AppMixin, SettingsMixin

from .version import KICAD_PLUGIN_VERSION

# ---------------------------- KiCad API Endpoint Plugin --------------------------------------------------
class KiCadLibraryPlugin(UrlsMixin, AppMixin, InvenTreePlugin, SettingsMixin):
    AUTHOR = "Andre Iwers"

    DESCRIPTION = _(
        "KiCad EDA conform API endpoint for KiCad's parts library tool. This plugin provides metadata only "
        "and requires matching symbol and footprint libraries within the KiCad EDA.")

    VERSION = KICAD_PLUGIN_VERSION

    TITLE = "KiCad Library Endpoint"
    SLUG = "kicad-library-plugin"
    NAME = "KiCadLibraryPlugin"

    PUBLISH_DATE = datetime.date(2023, 6, 9)
    WEBSITE = "https://www.aioz.com.au"

    MIN_VERSION = '0.11.0'

    SETTINGS = {
        'KICAD_ENABLE_SUBCATEGORY': {
            'name': _('Enable Sub-Category Parts'),
            'description': _(
                'If enabled, plugin will return all the part under this category even if they are in a sub-category.'),
            'validator': bool,
            'default': True,
        },
        'KICAD_SYMBOL_PARAMETER': {
            'name': _('Symbol Parameter'),
            'description': _('The part parameter to use for the symbol name.'),
            'model': 'part.partparametertemplate',
        },
        'KICAD_FOOTPRINT_PARAMETER': {
            'name': _('Footprint Parameter'),
            'description': _('The part parameter to use for the footprint name.'),
            'model': 'part.partparametertemplate',
        }
    }

    def setup_urls(self):
        """Returns the URLs defined by this plugin."""

        from . import viewsets
        from . import views

        # Construct view set router
        router = routers.DefaultRouter()
        router.register(r'categories', viewsets.CategoryViewSet, basename='kicad-category')
        router.register(r'parts', viewsets.PartViewSet, basename='kicad-parts')

        return [
            re_path(r'v1/', include([
                re_path(r'settings.json', views.kicad_settings, name='kicad-settings'),
                re_path('^parts/category/(?P<id>.+).json$', viewsets.PartsPreviewList.as_view(), {'plugin': self}, name='kicad-part-preview-list'),
                re_path('^parts/(?P<pk>.+).json$', viewsets.PartDetail.as_view(), {'plugin': self}, name='kicad-part-detail'),
                re_path('^categories/', viewsets.CategoryList.as_view(), {'plugin': self}, name='kicad-category-list'),
                url('', include(router.urls))
            ]))
        ]
