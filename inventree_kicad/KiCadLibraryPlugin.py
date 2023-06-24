"""

API endpoint for Kicad REST API library.

This plugin supplies the endpoints and data needed for KiCad to display selected categories and their
corresponding parts within the Kicad environment.

"""
import datetime

from django.conf.urls import url

from django.urls import include

from plugin import InvenTreePlugin
from plugin.mixins import UrlsMixin, AppMixin, SettingsMixin

from django.utils.translation import gettext_lazy as _

from plugins.inventree_kicad.viewsets import router_kicad


# ---------------------------- KiCad API Endpoint Plugin --------------------------------------------------
class KiCadLibraryPlugin(UrlsMixin, AppMixin, SettingsMixin, InvenTreePlugin):
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

    SETTINGS = {
        'FOOTPRINT': {
            'name': _('Key for footprint field'),
            'description':  _('Kicad will look for this key to copy this to the FOOTPRINT field'),
            'default': 'Footprint',
        },
        'SYMBOL': {
            'name': _('Key for symbol field'),
            'description':  _('Kicad will look for this key to copy this to the SYMBOL field'),
            'default': 'Symbol',
        },
        'DATASHEET': {
            'name': _('Key for datasheet field'),
            'description':  _('Kicad will look for this key to copy this to the DATSHEET field'),
            'default': 'Datasheet',
        },
        'VALUE': {
            'name': _('Key for value field'),
            'description': _('Kicad will look for this key to copy this to the VALUE field'),
            'default': 'Value',
        },
    }

    def setup_urls(self):
        """Returns the URLs defined by this plugin."""

        return [
            url(r'', include(router_kicad.urls)),
        ]
