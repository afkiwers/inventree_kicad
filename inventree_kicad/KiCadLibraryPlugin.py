"""

API endpoint for Kicad REST API library.

This plugin supplies the endpoints and data needed for KiCad to display selected categories and their
corresponding parts within the Kicad environment.

"""

from django.urls import include, re_path
from django.utils.translation import gettext_lazy as _
from plugin import InvenTreePlugin
from plugin.mixins import AppMixin, SettingsMixin, UrlsMixin
from rest_framework import routers

from .version import KICAD_PLUGIN_VERSION


class KiCadLibraryPlugin(UrlsMixin, AppMixin, SettingsMixin, InvenTreePlugin):
    """Plugin for KiCad Library Endpoint.

    Provides a set of API endpoints which conform to the KiCad REST API specification.
    """

    AUTHOR = "Andre Iwers"

    DESCRIPTION = _(
        "Provides external library functionality for KiCad via the HTTP library interface"
    )

    VERSION = KICAD_PLUGIN_VERSION

    TITLE = "KiCad Library Endpoint"
    SLUG = "kicad-library-plugin"
    NAME = "KiCadLibraryPlugin"

    WEBSITE = "https://github.com/afkiwers"

    MIN_VERSION = "1.2.0"
    MAX_VERSION = "1.99.99"

    # Custom settings panel (supplier selection), see static/kicad_settings.js
    ADMIN_SOURCE = "kicad_settings.js"

    SETTINGS = {
        "KICAD_ENABLE_SUBCATEGORY": {
            "name": _("Enable Sub-Category Parts"),
            "description": _(
                "When activated, the plugin will provide all components associated with this category, including those located within sub-categories"
            ),
            "validator": bool,
            "default": True,
        },
        "KICAD_ENABLE_STOCK_COUNT": {
            "name": _("Display Available Stock"),
            "description": _(
                "When activated, the plugin will provide stock information which will be displayed as part of the top level description in KiCad"
            ),
            "validator": bool,
            "default": False,
        },
        "KICAD_ENABLE_STOCK_COUNT_FORMAT": {
            "name": _("Stock Count Display Format"),
            "description": _(
                "This will be displayed after the part's description in KiCad (right column). Note: {1} contains the Stock information, {0} the description of the part."
            ),
            "default": "[Stock: {1}] {0}",
        },
        "DEFAULT_FOR_MISSING_SYMBOL": {
            "name": _("Backup KiCad Symbol"),
            "description": _(
                "This backup symbol will be used if none has been defined"
            ),
            "default": "",
        },
        "KICAD_INCLUDE_IPN": {
            "name": _("Include IPN"),
            "description": _(
                "When activated, the IPN is included in the KiCad fields for a part. Note: Including IPN as value will supercede the KICAD_VALUE_PARAMETER setting."
            ),
            "choices": [
                ("dont_include", "Do not Include"),
                ("include_hidden", "Include but Hide in Schematic"),
                ("include_visible", "Include and Show in Schematic"),
                ("include_as_value", "Include as Value"),
            ],
            "default": "dont_include",
        },
        "KICAD_SYMBOL_PARAMETER": {
            "name": _("Symbol Parameter"),
            "description": _("The part parameter to use for the symbol name."),
            "model": "common.parametertemplate",
        },
        "KICAD_FOOTPRINT_PARAMETER": {
            "name": _("Footprint Parameter"),
            "description": _("The part parameter to use for the footprint name."),
            "model": "common.parametertemplate",
        },
        "KICAD_REFERENCE_PARAMETER": {
            "name": _("Reference Parameter"),
            "description": _("The part parameter to use for the reference name."),
            "model": "common.parametertemplate",
        },
        "KICAD_VALUE_PARAMETER": {
            "name": _("Value Parameter"),
            "description": _("The part parameter to use for the value."),
            "model": "common.parametertemplate",
        },
        "KICAD_FIELD_VISIBILITY_PARAMETER": {
            "name": _("Field Visibility Parameter"),
            "description": _(
                "Set field visibility in KiCad using this parameter. Enter comma-separated InvenTree parameter names to show per part."
            ),
            "model": "common.parametertemplate",
        },
        "KICAD_FIELD_VISIBILITY_PARAMETER_GLOBAL": {
            "name": _("Global Field Visibility Parameter"),
            "description": _(
                "Global version of KICAD_FIELD_VISIBILITY_PARAMETER; overridden if set locally."
            ),
            "default": "Kicad_Visible_Fields",
        },
        "KICAD_EXCLUDE_FROM_BOM_PARAMETER": {
            "name": _("BOM Exclusion Parameter"),
            "description": _(
                "The part parameter to use for to exclude it from the BOM."
            ),
            "model": "common.parametertemplate",
        },
        "KICAD_EXCLUDE_FROM_BOARD_PARAMETER": {
            "name": _("Board Exclusion Parameter"),
            "description": _(
                "The part parameter to use for to exclude it from the netlist when passing from schematic to board."
            ),
            "model": "common.parametertemplate",
        },
        "KICAD_EXCLUDE_FROM_SIM_PARAMETER": {
            "name": _("Simulation Exclusion Parameter"),
            "description": _(
                "The part parameter to use for to exclude it from the simulation."
            ),
            "model": "common.parametertemplate",
        },
        "KICAD_USE_IPN_AS_NAME": {
            "name": _("Use IPN Instead of Name"),
            "description": _("When True, the plugin will use IPN instead of Name"),
            "validator": bool,
            "default": False,
        },
        "KICAD_ENABLE_MANUFACTURER_DATA": {
            "name": _("Add Manufacturer Data to KiCad Parts"),
            "description": _(
                "When activated, the supplier and manufacturer data will be added to the KiCad parts."
            ),
            "validator": bool,
            "default": False,
        },
        "KICAD_SUPPLIER_FIELD_PARAMETER": {
            "name": _("Supplier Field Parameter"),
            "description": _(
                "Supplier (company) parameter which holds a custom KiCad field name, e.g. 'LCSC Part #'. "
                "For suppliers with this parameter, the supplier part number is added under that field name "
                "instead of the default Supplier_x / SPN_x fields."
            ),
            "model": "common.parametertemplate",
        },
        "KICAD_INCLUDE_UNITS_IN_PARAMETERS": {
            "name": _("Include Units in Parameters"),
            "description": _(
                "When activated, if a parameter has units it will be included"
            ),
            "validator": bool,
            "default": True,
        },
        "KICAD_HIDE_INACTIVE_PARTS": {
            "name": _("Hide Inactive Parts"),
            "description": _(
                "When activated, inactive parts will be hidden from the KiCad parts preview list"
            ),
            "validator": bool,
            "default": True,
        },
        "KICAD_HIDE_TEMPLATE_PARTS": {
            "name": _("Hide Template Parts"),
            "description": _(
                "When activated, template parts will be hidden from the KiCad parts preview list"
            ),
            "validator": bool,
            "default": False,
        },
    }

    # Metadata key used to store the supplier filter.
    # This is stored as plugin metadata (not a setting) so it does not show up in the settings list.
    SUPPLIER_FILTER_KEY = "kicad_supplier_filter"

    def get_supplier_filter(self) -> list[int]:
        """Return the list of supplier IDs whose data is added to KiCad parts (empty = all)."""
        value = self.plugin_config().get_metadata(self.SUPPLIER_FILTER_KEY, [])
        return [int(x) for x in value or [] if str(x).isdigit()]

    def set_supplier_filter(self, supplier_ids: list[int]):
        """Store the list of supplier IDs whose data is added to KiCad parts."""
        self.plugin_config().set_metadata(
            self.SUPPLIER_FILTER_KEY, sorted({int(x) for x in supplier_ids})
        )

    def get_admin_context(self) -> dict:
        """Context data for the custom settings panel."""
        return {
            "supplier_filter_url": f"/{self.base_url}api/supplier-filter/",
            "enable_setting_url": f"/api/plugins/{self.slug}/settings/KICAD_ENABLE_MANUFACTURER_DATA/",
        }

    def setup_urls(self):
        """Returns the URLs defined by this plugin."""

        from . import viewsets

        api_category_router = routers.DefaultRouter()
        api_category_router.register(
            r"category", viewsets.CategoryApi, basename="selectedcategory"
        )

        api_urls = [
            re_path(
                r"^supplier-filter/$",
                viewsets.SupplierFilter.as_view(),
                {"plugin": self},
                name="kicad-supplier-filter",
            ),
            re_path("", include(api_category_router.urls)),
        ]

        return [
            re_path(
                r"v1/",
                include([
                    re_path(
                        r"parts/",
                        include([
                            re_path(
                                "category/(?P<id>.+).json$",
                                viewsets.PartsPreviewList.as_view(),
                                {"plugin": self},
                                name="kicad-part-category-list",
                            ),
                            re_path(
                                "(?P<pk>.+).json$",
                                viewsets.PartDetail.as_view(),
                                {"plugin": self},
                                name="kicad-part-detail",
                            ),
                            # Anything else goes to the part list
                            re_path(
                                ".*$",
                                viewsets.PartsPreviewList.as_view(),
                                {"plugin": self},
                                name="kicad-part-list",
                            ),
                        ]),
                    ),
                    # List of available categories
                    re_path(
                        "categories(.json)?/?$",
                        viewsets.CategoryList.as_view(),
                        {"plugin": self},
                        name="kicad-category-list",
                    ),
                    # Anything else goes to the index view
                    re_path("^.*$", viewsets.Index.as_view(), name="kicad-index"),
                ]),
            ),
            re_path(r"api/", include(api_urls), name="api"),
            # Anything else, redirect to our top-level v1 page
            re_path("^.*$", viewsets.Index.as_view(), name="kicad-index"),
        ]

