"""

API endpoint for Kicad REST API library.

This plugin supplies the endpoints and data needed for KiCad to display selected categories and their
corresponding parts within the Kicad environment.

"""
import csv
import datetime
import json

from django.conf.urls import url
from django.http import JsonResponse
from django.urls import include, re_path
from django.utils.translation import gettext_lazy as _

from part.models import Part, PartParameterTemplate, PartParameter
from part.views import PartIndex
from plugin import InvenTreePlugin
from plugin.mixins import UrlsMixin, AppMixin, SettingsMixin, PanelMixin

from .version import KICAD_PLUGIN_VERSION


class KiCadLibraryPlugin(PanelMixin, UrlsMixin, AppMixin, SettingsMixin, InvenTreePlugin):
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

    MIN_VERSION = '0.12.0'

    SETTINGS = {
        'KICAD_ENABLE_SUBCATEGORY': {
            'name': _('Enable Sub-Category Parts'),
            'description': _(
                'When activated, the plugin will provide all components associated with this category, including those located within sub-categories'),
            'validator': bool,
            'default': True,
        },
        'KICAD_INCLUDE_IPN': {
            'name': _('Include IPN in part fields'),
            'description': _(
                'When activated, the IPN is included in the KiCad fields for a part'),
            'validator': bool,
            'default': False,
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
            'name': _('Board Exclusion Parameter'),
            'description': _(
                'The part parameter to use for to exclude it from the netlist when passing from schematic to board.'),
            'model': 'part.partparametertemplate',
        },
        'KICAD_EXCLUDE_FROM_SIM_PARAMETER': {
            'name': _('Simulation Exclusion Parameter'),
            'description': _('The part parameter to use for to exclude it from the simulation.'),
            'model': 'part.partparametertemplate',
        },
    }

    def get_custom_panels(self, view, request):
        panels = []

        # This panel will *only* display on the PurchaseOrder view,
        if isinstance(view, PartIndex):
            self.part_parameter_templates = PartParameterTemplate.objects.filter(name__icontains='KiCad')

            panels.append({
                'title': 'Import KiCad Metadata',
                'icon': 'fa-file-import',
                'content_template': 'inventree_kicad/kicad_csv_import.html',
            })

        return panels

    def setup_urls(self):
        """Returns the URLs defined by this plugin."""

        from . import viewsets

        return [
            re_path(r'v1/', include([
                re_path(r'parts/', include([
                    re_path('category/(?P<id>.+).json$', viewsets.PartsPreviewList.as_view(), {'plugin': self},
                            name='kicad-part-category-list'),
                    re_path('(?P<pk>.+).json$', viewsets.PartDetail.as_view(), {'plugin': self},
                            name='kicad-part-detail'),

                    # Anything else goes to the part list
                    re_path('.*$', viewsets.PartsPreviewList.as_view(), {'plugin': self}, name='kicad-part-list'),
                ])),

                # List of available categories
                re_path('categories(.json)?/?$', viewsets.CategoryList.as_view(), {'plugin': self},
                        name='kicad-category-list'),

                # Anything else goes to the index view
                re_path('^.*$', viewsets.Index.as_view(), name='kicad-index'),
            ])),

            url(r'upload(?:\.(?P<format>json))?$', self.import_meta_data, name='meta_data_upload'),

            # Anything else, redirect to our top-level v1 page
            re_path('^.*$', viewsets.Index.as_view(), name='kicad-index'),
        ]

    # Define the function that will be called.
    def import_meta_data(self, request):
        file = request.FILES.get('file', False)

        if file:
            decoded_file = file.read().decode('utf-8').splitlines()
            reader = csv.DictReader(decoded_file)

            # create dict from selection
            field_name_matching = json.loads(request.POST['fieldNameMatching'])

            errors = ["The following PartIDs do not exist: "]

            for row in reader:

                try:
                    part = Part.objects.get(id=row['InvenTree'])

                    for csv_header, value in row.items():

                        # skip part ID
                        if csv_header == 'InvenTree':
                            continue

                        # skip unwanted columns
                        if not field_name_matching.get(csv_header, None):
                            continue

                        # find and/or add template and value
                        template = PartParameterTemplate.objects.get(id=field_name_matching[csv_header])
                        parameter = PartParameter.objects.get_or_create(part=part, template=template)
                        parameter[0].data = row[csv_header]
                        parameter[0].save()

                except Exception:
                    errors.append(row['InvenTree'])
                    part = None

                if part:
                    pass

            return JsonResponse({'error': errors}, status=422)

        return JsonResponse({'error': 'No file uploaded!'}, status=204)
