"""

API endpoint for Kicad REST API library.

This plugin supplies the endpoints and data needed for KiCad to display selected categories and their
corresponding parts within the Kicad environment.

"""
import datetime
import json

from django.core.validators import URLValidator

from django.conf.urls import url
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.urls import include, re_path
from django.utils.translation import gettext_lazy as _

from InvenTree.helpers import str2bool
from common.notifications import logger
from part.models import Part, PartParameterTemplate, PartParameter, PartAttachment
from plugin import InvenTreePlugin
from plugin.base.integration.mixins import SettingsContentMixin
from plugin.mixins import UrlsMixin, AppMixin, SettingsMixin, PanelMixin
import xml.etree.ElementTree as elementTree

from .version import KICAD_PLUGIN_VERSION


class KiCadLibraryPlugin(PanelMixin, UrlsMixin, AppMixin, SettingsMixin, SettingsContentMixin, InvenTreePlugin):
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
        'KICAD_META_DATA_IMPORT_ADD_DATASHEET': {
            'name': _('Add datasheet if URL is valid'),
            'description': _(
                'When activated, the plugin will add the datasheet URL (comment will be \'datasheet\') to the '
                'attachments.'),
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

    def get_settings_content(self, request):
        """Custom settings content for the plugin."""

        try:
            # Use djangos template rendering engine and return html as string
            return render_to_string('inventree_kicad/kicad_bom_import.html',
                                    context={
                                        'kicad_parameters': ['Reference', 'Footprint', 'Symbol'],
                                        'part_parameter_templates': PartParameterTemplate.objects.filter(
                                            name__icontains='KiCad')
                                    },
                                    request=request)
        except Exception as exp:
            return f'<div class="panel-heading"><h4>KiCad Metadata Import</h4></div><div class=\'panel-content\'><div class=\'alert alert-info alert-block\'>Error: {exp}</div></div>'

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

    def import_meta_data(self, request):  # noqa

        if request.FILES.get('file', False):
            file = request.FILES.get('file', False)

            # Make sure we have got a xml file
            if 'xml' not in file.content_type:
                return JsonResponse({'error': 'XML file expected!'}, status=422)

            # Read the XML file, and find all components
            tree = elementTree.parse(file)
            root = tree.getroot()

            # Grab the "components" list
            components = root.find('components')
            inventree_parts = set()

            # create dict from selection
            field_name_matching = json.loads(request.POST['fieldNameMatching'])

            # user needs to match all KiCad Parameter
            if 'false' in field_name_matching.values():
                return JsonResponse(
                    {'error': 'Some KiCad Parameters were not matched with an InvenTree parameter.'},
                    status=406
                )

            kicad_footprint_param_id = field_name_matching['Footprint']
            kicad_reference_param_id = field_name_matching['Reference']
            kicad_symbol_param_id = field_name_matching['Symbol']

            # Iterate through all child components with the tag 'comp'
            for idx, comp in enumerate(components.findall('comp')):

                ref = comp.attrib.get('ref', None)

                # Missing ref - continue
                if not ref:
                    logger.debug('Missing ref, skipping')
                    continue

                # Reformat the reference from CAV123 to CAV? or R2 to R
                ref = ''.join([c for c in ref if not c.isdigit()])

                datasheet = None
                if comp.find('datasheet') is not None:
                    datasheet = comp.find('datasheet').text

                footprint = None
                if comp.find('footprint') is not None:
                    footprint = comp.find('footprint').text
                else:
                    logger.debug('Missing footprint, skipping')
                    continue

                lib_name = None
                lib_part = None
                if comp.find('libsource') is not None:
                    libsource = comp.find('libsource')

                    lib_name = libsource.attrib.get('lib', None)
                    lib_part = libsource.attrib.get('part', None)

                if not lib_name or not lib_part:
                    logger.debug('Missing lib_name or lib_part, skipping')
                    continue

                symbol = f'{lib_name}:{lib_part}'

                inventree_id = None

                for field in comp.find('fields'):
                    if str(field.attrib.get('name', '')).lower().startswith('inventree'):
                        inventree_id = field.text
                        break

                # Missing inventree_id, cannot continue
                if not inventree_id:
                    logger.debug('Missing inventree_id, skipping')
                    continue

                try:
                    inventree_id = int(inventree_id)
                except ValueError:
                    logger.debug('InvenTree ID is not an integer, skipping')
                    continue

                # Already checked this one
                if inventree_id in inventree_parts:
                    continue

                # add to our cache, we use this to not add the same data multiple times
                inventree_parts.add(inventree_id)

                try:
                    part = Part.objects.get(id=inventree_id)
                except Part.DoesNotExist:
                    logger.debug(f'Part ID: {inventree_id} does not belong to an existing part, skipping')
                    continue

                # find and/or add template and value
                template = PartParameterTemplate.objects.get(id=kicad_reference_param_id)
                parameter = PartParameter.objects.get_or_create(part=part, template=template)
                parameter[0].data = ref
                parameter[0].save()

                template = PartParameterTemplate.objects.get(id=kicad_footprint_param_id)
                parameter = PartParameter.objects.get_or_create(part=part, template=template)
                parameter[0].data = footprint
                parameter[0].save()

                template = PartParameterTemplate.objects.get(id=kicad_symbol_param_id)
                parameter = PartParameter.objects.get_or_create(part=part, template=template)
                parameter[0].data = symbol
                parameter[0].save()

                if datasheet and str2bool(self.get_setting('KICAD_META_DATA_IMPORT_ADD_DATASHEET', False)):
                    try:
                        URLValidator()(datasheet)
                    except Exception as e:
                        logger.debug(f'URL is invalid: {e}')
                        continue

                    PartAttachment.objects.get_or_create(part_id=inventree_id, link=datasheet,
                                                         comment='datasheet')

            return JsonResponse({}, status=200)

        return JsonResponse({'error': 'No file uploaded!'}, status=204)
