"""

API endpoint for Kicad REST API library.

This plugin supplies the endpoints and data needed for KiCad to display selected categories and their
corresponding parts within the Kicad environment.

"""
import datetime

from django.core.validators import URLValidator

from django.http import JsonResponse
from django.template.loader import render_to_string
from django.urls import include, re_path
from django.utils.translation import gettext_lazy as _

from InvenTree.helpers import str2bool
from common.notifications import logger
from part.models import Part, PartParameterTemplate, PartParameter, PartAttachment
from plugin import InvenTreePlugin
from plugin.base.integration.mixins import SettingsContentMixin
from plugin.mixins import UrlsMixin, AppMixin, SettingsMixin
import xml.etree.ElementTree as elementTree

from .models import ProgressIndicator
from .version import KICAD_PLUGIN_VERSION


class KiCadLibraryPlugin(UrlsMixin, AppMixin, SettingsMixin, SettingsContentMixin, InvenTreePlugin):
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
            'name': _('Include IPN'),
            'description': _('When activated, the IPN is included in the KiCad fields for a part'),
            'choices': [('0', 'Do not Include'), ('False', 'Include but Hide in Schematic'), ('True', 'Include and Show in Schematic')],
            'default': '0',
        },
        'KICAD_META_DATA_IMPORT_ADD_DATASHEET': {
            'name': _('Add datasheet if URL is valid'),
            'description': _(
                'When activated, the plugin will add the datasheet URL (comment will be \'datasheet\') to the '
                'attachments.'),
            'validator': bool,
            'default': False,
        },
        'IMPORT_INVENTREE_ID_FALLBACK': {
            'name': _('Also Match Against Part Name'),
            'description': _(
                'When activated, the import tool will use the part name as fallback if the ID does not return an existing part.'),
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
        'IMPORT_INVENTREE_ID_IDENTIFIER': {
            'name': _('Inventree Part ID Identifier'),
            'description': _('This identifier specifies what key the import tool looks for to get the part ID'),
            'default': "InvenTree"
        },
        'DEFAULT_FOR_MISSING_SYMBOL': {
            'name': _('Backup KiCad Symbol'),
            'description': _('This backup symbol will be used if none has been defined'),
            'default': ""
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

            re_path(r'upload(?:\.(?P<format>json))?$', self.import_meta_data, name='meta_data_upload'),
            re_path(r'progress_bar_status', self.get_import_progress, name='get_import_progress'),

            # Anything else, redirect to our top-level v1 page
            re_path('^.*$', viewsets.Index.as_view(), name='kicad-index'),
        ]

    def get_import_progress(self, request):
        progress = ProgressIndicator.objects.get_or_create(user=request.user)[0]

        return JsonResponse({
            'value': progress.current_progress,
            'file_name': progress.file_name
        }, status=200)

    def import_meta_data(self, request):  # noqa

        if request.FILES.get('file', False):
            file = request.FILES.get('file', False)

            kicad_footprint_param_id = self.get_setting('KICAD_FOOTPRINT_PARAMETER', None)
            kicad_reference_param_id = self.get_setting('KICAD_REFERENCE_PARAMETER', None)
            kicad_symbol_param_id = self.get_setting('KICAD_SYMBOL_PARAMETER', None)

            if kicad_footprint_param_id == '' or kicad_reference_param_id == '' or kicad_symbol_param_id == '':
                return JsonResponse(
                    {
                        'error': 'Missing parameters. Please make sure you have selected appropriate parameters in the settings before attempting to import anything.'
                    },
                    status=422)

            # Make sure we have got a xml file
            if 'xml' not in file.content_type:
                return JsonResponse({'error': 'XML file expected!'}, status=422)

            # Read the XML file, and find all components
            tree = elementTree.parse(file)
            root = tree.getroot()

            # Grab the "components" list
            components = root.find('components')
            inventree_parts = set()

            # get and reset user specific progress bar status
            import_progress = ProgressIndicator.objects.get_or_create(user=request.user)[0]
            import_progress.current_progress = 0
            import_progress.file_name = file

            # we start at 0
            comp_cnt = len(components.findall('comp')) - 1

            # Iterate through all child components with the tag 'comp'
            for idx, comp in enumerate(components.findall('comp')):

                # update user specific progress bar status
                import_progress.current_progress = int((idx / comp_cnt) * 100)
                import_progress.save()

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

                inventree_part_id = None

                # check if there are fields, some parts may not have any like fiducials.
                fields = comp.find('fields')
                if not fields:
                    logger.debug('Missing fields skipping')
                    continue

                # load the inventree ID identifier
                inventree_id_identifier = self.get_setting('IMPORT_INVENTREE_ID_IDENTIFIER', None)

                for field in fields:
                    if str(field.attrib.get('name', '')).lower().startswith(inventree_id_identifier.lower()):
                        inventree_part_id = field.text
                        break

                # Missing inventree_id, cannot continue
                if not inventree_part_id:
                    logger.debug('Missing part id, skipping')
                    continue

                # Already checked this one
                if inventree_part_id in inventree_parts:
                    continue

                # add to our cache, we use this to not add the same data multiple times
                inventree_parts.add(inventree_part_id)

                # try load part from database
                part = None
                try:
                    part = Part.objects.get(id=inventree_part_id)

                except Part.DoesNotExist:
                    invalid_part = True

                    # try also the part name if user wants it
                    if self.get_setting('IMPORT_INVENTREE_ID_FALLBACK', None):
                        try:
                            part = Part.objects.get(name=inventree_part_id)
                            invalid_part = False

                            # map actual id as we now know which part we are referencing
                            inventree_part_id = part.id

                        except Part.DoesNotExist:
                            invalid_part = True

                    if invalid_part:
                        logger.debug(f'Part ID: {inventree_part_id} does not belong to an existing part, skipping')
                        continue

                except Exception as exp:
                    logger.debug(f'Part ID: {inventree_part_id} caused uknown error {exp}')
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

                    try:
                        # inventree is not happy with urls which are too long, so let's make sure that this
                        # doesn't prevent us from importing all the following parts.
                        PartAttachment.objects.get_or_create(part_id=inventree_part_id, link=datasheet, comment='datasheet')
                    except Exception as exp:
                        logger.debug(exp)
                        pass

            return JsonResponse({}, status=200)

        return JsonResponse({'error': 'No file uploaded!'}, status=204)
