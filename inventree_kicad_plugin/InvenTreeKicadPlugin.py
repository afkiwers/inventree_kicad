"""

API endpoints for KiCad HTTP library.

This plugin supplies the endpoints and data needed for KiCad to display selected categories and their
corresponding parts within the KiCad environment.

"""
import datetime
import os

from django.conf.urls import url

from django.urls import include

from plugin import InvenTreePlugin
from plugin.mixins import UrlsMixin, AppMixin, SettingsMixin

from django.utils.translation import gettext_lazy as _

from .viewsets import router_kicad
from .version import KICAD_PLUGIN_VERSION


# ---------------------------- KiCad API Endpoint Plugin --------------------------------------------------
class InvenTreeKiCadPlugin(AppMixin, UrlsMixin, InvenTreePlugin):
    AUTHOR = "Andre Iwers"

    DESCRIPTION = _(
        "KiCad EDA conform API endpoint for KiCad's parts library tool. This plugin provides metadata only "
        "and requires matching symbol and footprint libraries within the KiCad EDA.")

    VERSION = KICAD_PLUGIN_VERSION

    TITLE = "KiCad HTTP Library Endpoints"
    SLUG = "inventree-kicad-plugin"
    NAME = "InvenTreeKiCadPlugin"

    PUBLISH_DATE = datetime.date(2023, 6, 9)
    WEBSITE = "https://www.aioz.com.au"

    MIN_VERSION = '0.11.0'

    os.environ['KICAD_PLUGIN_GET_SUB_PARTS'] = 'True'

    def setup_urls(self):
        """Returns the URLs defined by this plugin."""

        return [
            url(r'', include(router_kicad.urls)),
        ]

    # SETTINGS = {
    #     'FOOTPRINT': {
    #         'name': _('Key for footprint field'),
    #         'description':  _('Kicad will look for this key to copy this to the FOOTPRINT field'),
    #         'default': 'Footprint',
    #     },
    #     'SYMBOL': {
    #         'name': _('Key for symbol field'),
    #         'description':  _('Kicad will look for this key to copy this to the SYMBOL field'),
    #         'default': 'Symbol',
    #     },
    #     'DATASHEET': {
    #         'name': _('Key for datasheet field'),
    #         'description':  _('Kicad will look for this key to copy this to the DATASHEET field'),
    #         'default': 'Datasheet',
    #     },
    #     'VALUE': {
    #         'name': _('Key for value field'),
    #         'description': _('Kicad will look for this key to copy this to the VALUE field'),
    #         'default': 'Value',
    #     },
    # }
