"""

API endpoint for Kicad REST API library.

This plugin supplies the endpoints and data needed for KiCad to display selected categories and their
corresponding parts within the Kicad environment.

"""
import datetime

from django.urls import include, re_path
from django.utils.translation import gettext_lazy as _

from plugin import InvenTreePlugin
from plugin.mixins import UrlsMixin, AppMixin, SettingsMixin

from .version import KICAD_PLUGIN_VERSION


class KiCadLibraryPlugin(UrlsMixin, AppMixin, SettingsMixin, InvenTreePlugin):
    """Plugin for KiCad Library Endpoint.
    
    Provides a set of API endpoints which conform to the KiCad REST API specification.
    """

    AUTHOR = "Andre Iwers"

    DESCRIPTION = _("Provides external library functionality for KiCad via the HTTP library interface")

    VERSION = KICAD_PLUGIN_VERSION

    TITLE = "KiCad Library Endpoint"
    SLUG = "kicad-library-plugin"
    NAME = "KiCadLibraryPlugin"

    PUBLISH_DATE = datetime.date(2023, 9, 21)

    WEBSITE = "https://github.com/afkiwers"

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
        },
        'KICAD_REFERENCE_PARAMETER': {
            'name': _('Reference Parameter'),
            'description': _('The part parameter to use for the reference name.'),
            'model': 'part.partparametertemplate',
        },
        'KICAD_VALUE_PARAMETER': {
            'name': _('Value Parameter'),
            'description': _('The part parameter to use for the value.'),
            'model': 'part.partparametertemplate',
        },
        'KICAD_EXCLUDE_FROM_BOM_PARAMETER': {
            'name': _('BOM Exclusion Parameter'),
            'description': _('The part parameter to use for to exclude it from the BOM.'),
            'model': 'part.partparametertemplate',
        },
        'KICAD_EXCLUDE_FROM_BOARD_PARAMETER': {
            'name': _('BOM Exclusion Parameter'),
            'description': _('The part parameter to use for to exclude it from the board.'),
            'model': 'part.partparametertemplate',
        },
        'KICAD_EXCLUDE_FROM_SIM_PARAMETER': {
            'name': _('BOM Exclusion Parameter'),
            'description': _('The part parameter to use for to exclude it from the simulation.'),
            'model': 'part.partparametertemplate',
        },
    }

    def setup_urls(self):
        """Returns the URLs defined by this plugin."""

        from . import viewsets

        return [
            re_path(r'v1/', include([
                re_path(r'parts/', include([
                    re_path('category/(?P<id>.+).json$', viewsets.PartsPreviewList.as_view(), {'plugin': self}, name='kicad-part-category-list'),
                    re_path('(?P<pk>.+).json$', viewsets.PartDetail.as_view(), {'plugin': self}, name='kicad-part-detail'),

                    # Anything else goes to the part list
                    re_path('.*$', viewsets.PartsPreviewList.as_view(), {'plugin': self}, name='kicad-part-list'),
                ])),

                # List of available categories
                re_path('categories(.json)?/?$', viewsets.CategoryList.as_view(), {'plugin': self}, name='kicad-category-list'),

                # Anything else goes to the index view
                re_path('^.*$', viewsets.Index.as_view(), name='kicad-index'),
            ])),

            # Anything else, redirect to our top-level v1 page
            re_path('^.*$', viewsets.Index.as_view(), name='kicad-index'),
        ]
