"""

API endpoint for Kicad REST API library.

This plugin supplies the endpoints and data needed for KiCad to display selected categories and their
corresponding parts within the Kicad environment.

"""
from django.core.validators import URLValidator

from django.http import JsonResponse
from django.template.loader import render_to_string
from django.urls import include, re_path
from django.utils.translation import gettext_lazy as _

from rest_framework import routers

from InvenTree.helpers import str2bool
from common.notifications import logger
from part.models import Part, PartParameterTemplate, PartParameter
from plugin import InvenTreePlugin

from plugin.mixins import UrlsMixin, AppMixin, SettingsMixin
import xml.etree.ElementTree as elementTree

from .models import ProgressIndicator
from .version import KICAD_PLUGIN_VERSION

try:
    from plugin.base.integration.mixins import SettingsContentMixin
except ImportError:
    class SettingsContentMixin:  # noqa: F811
        """Dummy mixin class for backwards compatibility.

        With the move the modern UI, this mixin is no longer used.
        It is included here to maintain compatibility with older versions of InvenTree.
        """
        ...


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
        'KICAD_ENABLE_STOCK_COUNT': {
            'name': _('Display Available Stock'),
            'description': _(
                'When activated, the plugin will provide stock information which will be displayed as part of the top level description in KiCad'),
            'validator': bool,
            'default': False,
        },
        'KICAD_ENABLE_STOCK_COUNT_FORMAT': {
            'name': _('Stock Count Display Format'),
            'description': _('This will be displayed after the part\'s description in KiCad (right column). Note: {1} contains the Stock information, {0} the description of the part.'),
            'default': "[Stock: {1}] {0}"
        },
        'DEFAULT_FOR_MISSING_SYMBOL': {
            'name': _('Backup KiCad Symbol'),
            'description': _('This backup symbol will be used if none has been defined'),
            'default': ""
        },
        'KICAD_INCLUDE_IPN': {
            'name': _('Include IPN'),
            'description': _('When activated, the IPN is included in the KiCad fields for a part'),
            'choices': [('0', 'Do not Include'), ('False', 'Include but Hide in Schematic'), ('True', 'Include and Show in Schematic')],
            'default': '0',
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
        'KICAD_FIELD_VISIBILITY_PARAMETER': {
            'name': _('Field Visibility Parameter'),
            'description': _('Set field visibility in KiCad using this parameter. Enter comma-separated InvenTree parameter names to show per part.'),
            'model': 'part.partparametertemplate',
        },
        'KICAD_FIELD_VISIBILITY_PARAMETER_GLOBAL': {
            'name': _('GLobal Field Visibility Parameter'),
            'description': _('Global version of KICAD_FIELD_VISIBILITY_PARAMETER; overridden if set locally.'),
            'default': "Kicad_Visible_Fields"
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
        'KICAD_META_DATA_IMPORT_ADD_DATASHEET': {
            'name': _('[KiCad Metadata Import] Add Datasheet if URL is Valid'),
            'description': _(
                'When activated, the plugin will add the datasheet URL (comment will be \'datasheet\') to the '
                'attachments.'),
            'validator': bool,
            'default': False,
        },
        'KICAD_USE_IPN_AS_NAME': {
            'name': _('Use IPN Instead of Name'),
            'description': _('When True, the plugin will use IPN instead of Name'),
            'validator': bool,
            'default': False,
        },
        'IMPORT_INVENTREE_ID_FALLBACK': {
            'name': _('[KiCad Metadata Import] Match Against Part Name'),
            'description': _(
                'When activated, the import tool will use the part name as fallback if the ID does not return an existing part.'),
            'validator': bool,
            'default': False,
        },
        'IMPORT_INVENTREE_OVERRIDE_PARAS': {
            'name': _('[KiCad Metadata Import] Override Parmeters'),
            'description': _(
                'When activated, the import tool will override existing KiCad parameters.'),
            'validator': bool,
            'default': False,
        },
        'IMPORT_INVENTREE_ID_IDENTIFIER': {
            'name': _('[KiCad Metadata Import] Inventree Part ID Identifier'),
            'description': _('This identifier specifies what key the import tool looks for to get the part ID'),
            'default': "InvenTree"
        },
        'KICAD_ENABLE_MANUFACTURER_DATA': {
            'name': _('Add Manufacturer Data to KiCad Parts'),
            'description': _('When activated, the supplier and manufacturer data will be added to the KiCad parts.'),
            'validator': bool,
            'default': False,
        },
        'KICAD_INCLUDE_UNITS_IN_PARAMETERS': {
            'name': _('Include Units in Parameters'),
            'description': _('When activated, if a parameter has units it will be included'),
            'validator': bool,
            'default': True,
        },
        'KICAD_HIDE_INACTIVE_PARTS': {
            'name': _('Hide Inactive Parts'),
            'description': _('When activated, inactive parts will be hidden from the KiCad parts preview list'),
            'validator': bool,
            'default': True,
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

        api_category_router = routers.DefaultRouter()
        api_category_router.register(r'category', viewsets.CategoryApi, basename='selectedcategory')

        api_urls = [
            re_path('', include(api_category_router.urls)),
        ]

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

            re_path(r'api/', include(api_urls), name='api'),

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

                t_ids = []
                t_ids.append(kicad_reference_param_id)
                t_ids.append(kicad_footprint_param_id)
                t_ids.append(kicad_symbol_param_id)

                t_id_values = []
                t_id_values .append(ref)
                t_id_values .append(footprint)
                t_id_values .append(symbol)

                for idx, t_id in enumerate(t_ids):
                    # find and/or add template and value
                    template = PartParameterTemplate.objects.get(id=t_id)
                    parameter = PartParameter.objects.get_or_create(part=part, template=template)
                    # Don't override
                    if parameter[1] or self.get_setting('IMPORT_INVENTREE_OVERRIDE_PARAS', None):
                        parameter[0].data = t_id_values[idx]
                        parameter[0].save()

                if datasheet and str2bool(self.get_setting('KICAD_META_DATA_IMPORT_ADD_DATASHEET', False)):
                    try:
                        URLValidator()(datasheet)
                    except Exception as e:
                        logger.debug(f'URL is invalid: {e}')
                        continue

                    # only add a datasheet if there is not already one which is already called out to be one.
                    self.add_attachment(inventree_part_id, datasheet)

            return JsonResponse({}, status=200)

        return JsonResponse({'error': 'No file uploaded!'}, status=204)

    def add_attachment(self, part_id, link):
        """Add an external link as an attachment for the part.
        
        Note: We support the 'legacy' and 'modern' attachment tables.

        Ref: https://github.com/inventree/InvenTree/pull/7420
        """

        # First, try the 'modern' attachment table
        try:
            from common.models import Attachment

            # Check if there is an existing attachment
            attachment = Attachment.objects.filter(
                model_type='part',
                model_id=part_id,
                comment__iexact='datasheet'
            )

            if not attachment.exists():
                Attachment.objects.create(
                    model_type='part',
                    model_id=part_id,
                    link=link,
                    comment='Datasheet'
                )
            
            return
        except Exception:
            pass

        # Second, try the 'legacy' attachment table
        try:
            from part.models import PartAttachment

            # Check if there is an existing attachment
            attachment = PartAttachment.objects.filter(
                part=part_id,
                comment__iexact='datasheet'
            )

            if not attachment.exists():
                PartAttachment.objects.create(
                    part=part_id,
                    link=link,
                    comment='Datasheet'
                )
        
        except Exception:
            pass
