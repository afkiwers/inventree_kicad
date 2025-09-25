import logging

from django.utils.translation import gettext_lazy as _
from django.db.models import ExpressionWrapper, F, DecimalField
from django.db.models.functions import Greatest

from rest_framework import serializers
from rest_framework.reverse import reverse_lazy


from InvenTree.helpers_model import construct_absolute_url
from part.filters import annotate_total_stock, annotate_sales_order_allocations, annotate_build_order_allocations, annotate_variant_quantity, variant_stock_query
from part.models import Part, PartCategory, PartParameter
from company.models import ManufacturerPart, SupplierPart
from InvenTree.helpers import str2bool, decimal2string

from .models import SelectedCategory, FootprintParameterMapping


logger = logging.getLogger('inventree')


def _determine_part_name(part, use_ipn: bool = False) -> str:
    """Resolve part name for KiCad based on plugin setting."""

    return part.IPN or part.name if use_ipn else part.name


class KicadDetailedPartSerializer(serializers.ModelSerializer):
    """Custom model serializer for a single KiCad part instance"""

    def get_api_url(self):
        """Return the API url associated with this serializer"""
        return reverse_lazy('api-kicad-part-list')

    def __init__(self, *args, **kwargs):
        """Custom initialization for this serializer.

        As we need to have access to the parent plugin instance,
        we pass it in via the kwargs.
        """

        self.plugin = kwargs.pop('plugin')
        super().__init__(*args, **kwargs)

    class Meta:
        """Metaclass defining serializer fields"""
        model = Part

        fields = [
            'id',
            'name',
            'symbolIdStr',
            'exclude_from_bom',
            'exclude_from_board',
            'exclude_from_sim',
            'fields',
        ]

    # Serializer field definitions
    id = serializers.CharField(source='pk', read_only=True)
    symbolIdStr = serializers.SerializerMethodField('get_symbol')  # noqa: N815
    exclude_from_bom = serializers.SerializerMethodField('get_exclude_from_bom')
    exclude_from_board = serializers.SerializerMethodField('get_exclude_from_board')
    exclude_from_sim = serializers.SerializerMethodField('get_exclude_from_sim')
    name = serializers.SerializerMethodField('get_name')

    fields = serializers.SerializerMethodField('get_kicad_fields')

    def get_name(self, part):
        # Use helper to reduce duplication

        # Cache the 'use_ipn' setting
        if not hasattr(self, 'use_ipn'):
            self.use_ipn = str2bool(self.plugin.get_setting('KICAD_USE_IPN_AS_NAME', False))

        return _determine_part_name(part, self.use_ipn)

    def get_kicad_category(self, part):
        """For the provided part instance, find the associated SelectedCategory instance.

        If there are multiple possible associations, return the "deepest" one.
        """

        # Prevent duplicate lookups
        if hasattr(self, 'kicad_category'):
            return self.kicad_category

        # If the selcted part does not have a category, return None
        if not part.category:
            return None

        # Get the category tree for the selected part
        categories = part.category.get_ancestors(include_self=True)

        self.kicad_category = SelectedCategory.objects.filter(category__in=categories).order_by(
            '-category__level').first()

        return self.kicad_category

    def get_parameter_value(self, part, template_id, backup_value=''):
        """Return the value of the specified parameter for the given part instance.

        - If the parameter template is not specified, return empty string
        - If the part does not have a matching parameter, return empty string
        """

        if template_id is None:
            return backup_value

        try:
            parameter = PartParameter.objects.filter(part=part, template__pk=template_id).first()
        except (ValueError, PartParameter.DoesNotExist):
            parameter = None

        if parameter:
            return parameter.data
        else:
            return backup_value

    def get_reference(self, part):
        """Return the reference associated with this part

        - First, check if the part has a reference assigned (via parameter)
        - Otherwise, fallback to the default reference for the KiCad Category
        """

        # Default value is "X"
        reference = "X"

        # Fallback to the "default" reference for the associated SelectedCategory instance
        if kicad_category := self.get_kicad_category(part):
            reference = kicad_category.default_reference

        # Find the reference parameter value associated with this part instance
        template_id = self.plugin.get_setting('KICAD_REFERENCE_PARAMETER', None)

        reference = self.get_parameter_value(part, template_id, backup_value=reference)

        return str(reference)

    def get_symbol(self, part):
        """Return the symbol associated with this part.

        - First, check if the part has a symbol assigned (via parameter)
        - Otherwise, fallback to the default symbol for the KiCad Category
        """

        # By default, empty (unspecified) symbol value
        symbol = ''

        # Fallback to the "default" symbol for the associated SelectedCategory instance
        if kicad_category := self.get_kicad_category(part):
            symbol = kicad_category.default_symbol

        # Find the symbol parameter value associated with this part instance
        template_id = self.plugin.get_setting('KICAD_SYMBOL_PARAMETER', None)

        symbol = self.get_parameter_value(part, template_id, backup_value=symbol)

        if not symbol:
            symbol = template_id = self.plugin.get_setting('DEFAULT_FOR_MISSING_SYMBOL', "")

        # KiCad does not like colons in their symbol names.
        # Check if there is more than one colon present, if so rebuild string and honour only the first
        # colon. Replace the other colons with underscores.
        cnt = symbol.count(':')
        if cnt != 1 and len(symbol) != 0:
            spilt_str = symbol.split(':')
            tmp_str = ""

            for iter, s in enumerate(spilt_str):
                tmp_str += s

                if iter < 1:
                    tmp_str += ':'
                elif iter < cnt:    # make sure we suppress postfixes
                    tmp_str += '_'

            symbol = tmp_str

        return str(symbol)

    def get_footprint(self, part):
        """Return the footprint associated with this part.

        - First, check if the part has a footprint assigned (via parameter)
        - Then, check if there is a valid footprint mapping
        - Otherwise, fallback to the default footprint for the KiCad Category
        """

        footprint = ""
        footprint_mappings = None
        template_id = None

        if kicad_category := self.get_kicad_category(part):
            footprint = kicad_category.default_footprint
            footprint_mappings = FootprintParameterMapping.objects.filter(
                kicad_category=kicad_category,
            )
            template = kicad_category.footprint_parameter_template

            if template:
                template_id = kicad_category.footprint_parameter_template.id

        if not template_id:
            template_id = self.plugin.get_setting('KICAD_FOOTPRINT_PARAMETER', None)

        footprint = self.get_parameter_value(part, template_id, backup_value=footprint)

        if footprint_mappings:
            footprint_mapping = footprint_mappings.filter(parameter_value=footprint).first()
            if footprint_mapping:
                footprint = footprint_mapping.kicad_footprint

        return str(footprint)

    def get_datasheet(self, part):
        """Return the datasheet associated with this part.

        Here, we look at the attachments associated with the part,
        and return the first one which has a comment matching "datasheet"
        """

        datasheet = part.attachments.filter(comment__iexact='datasheet').first()

        if datasheet:
            try:
                return datasheet.fully_qualified_url()
            except AttributeError:
                # This version of InvenTree does not seem to support fully_qualified_urls
                return _("Unable to create a URL for the datasheet")

        # Default, return empty string
        return ""

    def get_value(self, part):
        """Return the value associated with this part.

        If the part value has been specified via parameter, return that.
        Otherwise, simply return the name of the part
        """

        # Fallback to the part name
        value = part.name

        # Find the value parameter value associated with this part instance
        template_id = self.plugin.get_setting('KICAD_VALUE_PARAMETER', None)

        value = self.get_parameter_value(part, template_id, backup_value=value)

        # it looks like there's not value parameter specified
        if value == part.name:
            # Fallback to the "default" value parameter for the associated SelectedCategory instance
            if kicad_category := self.get_kicad_category(part):
                value_parameter = kicad_category.default_value_parameter_template

                if value_parameter:
                    value = self.get_parameter_value(part, value_parameter.id, backup_value=value)

        return str(value)

    def get_custom_fields(self, part, excluded_field_names):
        """Return a set of 'custom' fields for this part

        Here, we return all the part parameters which are not already used
        """

        excluded_templates = [
            self.plugin.get_setting('KICAD_SYMBOL_PARAMETER', None),
            self.plugin.get_setting('KICAD_FOOTPRINT_PARAMETER', None),
            self.plugin.get_setting('KICAD_REFERENCE_PARAMETER', None),
            self.plugin.get_setting('KICAD_EXCLUDE_FROM_BOM_PARAMETER', None),
            self.plugin.get_setting('KICAD_EXCLUDE_FROM_BOARD_PARAMETER', None),
            self.plugin.get_setting('KICAD_EXCLUDE_FROM_SIM_PARAMETER', None),
            self.plugin.get_setting('KICAD_VALUE_PARAMETER', None),
            self.plugin.get_setting('KICAD_FIELD_VISIBILITY_PARAMETER', None),
        ]

        # exclude default value parameter template. This will be used for the actual value
        # so we don't want it to appear as an additional field.
        if kicad_category := self.get_kicad_category(part):
            if kicad_category.default_value_parameter_template:
                excluded_templates.append(str(kicad_category.default_value_parameter_template.id))

        # Build out an absolute URL for the part instance
        url = construct_absolute_url(f'/part/{part.id}/', request=self.context.get('request'))

        # Always include the InvenTree field, which has the ID of the part
        fields = {
            'InvenTree': {
                'value': f'{part.id}',
                'visible': 'False'
            },
            'Part URL': {
                'value': url,
                'visible': 'False'
            }
        }

        if self.plugin.get_setting('KICAD_INCLUDE_IPN', '0') != '0':
            fields['IPN'] = {
                'value': f'{part.IPN}',
                'visible': self.plugin.get_setting('KICAD_INCLUDE_IPN', 'False')
            }

        # Find the value parameter value associated with this part instance
        template_id = self.plugin.get_setting('KICAD_FIELD_VISIBILITY_PARAMETER', None)
        kicad_local_field_visibility = None
        try:
            # check if local parameter set, if so extract fields that need displaying in KiCad
            kicad_local_field_visibility = self.get_parameter_value(part, template_id, None).split(',')

            # make lower case and strip
            kicad_local_field_visibility = [field.strip().lower() for field in kicad_local_field_visibility]

        except AttributeError:
            pass  # ignore if there are any issues

        # load the global visibility settings if available and valid
        try:
            kicad_global_field_visibility = self.plugin.get_setting('KICAD_FIELD_VISIBILITY_PARAMETER_GLOBAL', None).split(',')

            kicad_global_field_visibility = [field.strip().lower() for field in kicad_global_field_visibility]

        except AttributeError:
            pass  # ignore if there are any issues

        # Check if we should include the parameter units in custom parameters
        kicad_include_units_in_parameters = self.plugin.get_setting('KICAD_INCLUDE_UNITS_IN_PARAMETERS', True)

        for parameter in part.parameters.all():
            # Exclude any which have already been used for default KiCad fields
            if str(parameter.template.pk) in excluded_templates:
                continue

            # Skip any which conflict with KiCad field names
            if parameter.template.name.lower() in excluded_field_names:
                continue

            is_visible = 'True' if parameter.template.name.lower().strip() in kicad_global_field_visibility else 'False'

            # Check if there is a local override
            if kicad_local_field_visibility is not None:
                is_visible = 'True' if parameter.template.name.lower().strip() in kicad_local_field_visibility else 'False'

            units = ""
            if kicad_include_units_in_parameters:
                units = f" {parameter.units}"

            fields[parameter.template.name] = {
                "value": f'{parameter.data}{units}'.strip(),
                "visible": is_visible
            }

        return fields
    
    def get_supplier_part_fields(self, part):
        """Return a set of fields for supplier and manufacturer information to be used in the KiCad symbol library"""

        manufacturer_parts = ManufacturerPart.objects.filter(part=part.pk).prefetch_related('supplier_parts')

        supplier_parts_used = set()
        kicad_fields = {}
        for mp_idx, mp_part in enumerate(manufacturer_parts):

            # get manufaturer and MPN
            manufacturer_name = mp_part.manufacturer.name if mp_part and mp_part.manufacturer else ''
            manufacturer_mpn = mp_part.MPN if mp_part else ''

            # create fields for manufacturer and MPN
            kicad_fields[f'Manufacturer_{mp_idx + 1}'] = {
                'value': manufacturer_name,
                'visible': 'False'
            }
            kicad_fields[f'MPN_{mp_idx + 1}'] = {
                'value': manufacturer_mpn,
                'visible': 'False'
            }

            for sp_idx, sp_part in enumerate(mp_part.supplier_parts.all()):
                supplier_parts_used.add(sp_part)

                # get supplier and SKU
                supplier_name = sp_part.supplier.name if sp_part and sp_part.supplier else ''
                supplier_sku = sp_part.SKU if sp_part else ''
                
                # create fields for supplier and SKU
                kicad_fields[f'Supplier_{mp_idx + 1}_{sp_idx + 1}'] = {
                    'value': supplier_name,
                    'visible': 'False'
                }
                kicad_fields[f'SPN_{mp_idx + 1}_{sp_idx + 1}'] = {
                    'value': supplier_sku,
                    'visible': 'False'
                }

        # add any supplier parts that are not associated with a manufacturer part
        for sp_idx, sp_part in enumerate(
            SupplierPart.objects.filter(part__pk=part.pk)
        ):
            if sp_part in supplier_parts_used:
                continue

            supplier_parts_used.add(sp_part)

            supplier_name = sp_part.supplier.name if sp_part and sp_part.supplier else ''
            supplier_sku = sp_part.SKU if sp_part else ''

            kicad_fields[f'Supplier_{sp_idx + 1}'] = {
                'value': supplier_name,
                'visible': 'False'
            }
            kicad_fields[f'SPN_{sp_idx + 1}'] = {
                'value': supplier_sku,
                'visible': 'False'
            }
               
        return kicad_fields

    def get_kicad_fields(self, part):
        """Return a set of fields to be used in the KiCad symbol library"""

        # Default KiCad Fields
        kicad_default_fields = {
            'value': {
                "value": self.get_value(part),
            },
            'footprint': {
                "value": self.get_footprint(part),
                "visible": 'False'
            },
            'datasheet': {
                "value": self.get_datasheet(part),
                "visible": 'False'
            },
            'reference': {
                "value": self.get_reference(part),
                "visible": 'True',
            },
            'description': {
                "value": str(part.description) if part.description else '',
                "visible": 'False'
            },
            'keywords': {
                "value": str(part.keywords) if part.keywords else '',
                "visible": 'False'
            },
        }

        if self.plugin.get_setting('KICAD_ENABLE_MANUFACTURER_DATA', False):
            return kicad_default_fields | self.get_supplier_part_fields(part) | self.get_custom_fields(part, list(kicad_default_fields.keys()))
        else:
            return kicad_default_fields | self.get_custom_fields(part, list(kicad_default_fields.keys()))

    def get_exclude_from_bom(self, part):
        """Return whether or not the part should be excluded from the bom.

        If the part exclusion has been specified via parameter, return that.
        Otherwise, simply return false
        """

        # Fallback to not exclude
        value = 'False'

        # Find the value parameter value associated with this part instance
        template_id = self.plugin.get_setting('KICAD_EXCLUDE_FROM_BOM_PARAMETER', None)

        value = self.get_parameter_value(part, template_id, backup_value=value)

        return value

    def get_exclude_from_board(self, part):
        """Return whether or not the part should be excluded from the netlist when passing from schematic to board.

        If the part exclusion has been specified via parameter, return that.
        Otherwise, simply return false
        """

        # Fallback to not exclude
        value = 'False'

        # Find the value parameter value associated with this part instance
        template_id = self.plugin.get_setting('KICAD_EXCLUDE_FROM_BOARD_PARAMETER', None)

        value = self.get_parameter_value(part, template_id, backup_value=value)

        return value

    def get_exclude_from_sim(self, part):
        """Return whether or not the part should be excluded from the sim.

        If the part exclusion has been specified via parameter, return that.
        Otherwise, simply return false
        """

        # Fallback to not exclude
        value = 'False'

        # Find the value parameter value associated with this part instance
        template_id = self.plugin.get_setting('KICAD_EXCLUDE_FROM_SIM_PARAMETER', None)

        value = self.get_parameter_value(part, template_id, backup_value=value)

        return value


class KicadPreviewPartSerializer(serializers.ModelSerializer):
    """Simplified serializer for previewing each part in a category.

    Simply returns the part ID and name.
    """

    class Meta:
        """Metaclass defining serializer fields"""
        model = Part

        fields = [
            'id',
            'name',
            'description',
            'stock',
        ]

    def __init__(self, *args, **kwargs):
        """Custom initialization for this serializer.

        As we need to have access to the parent plugin instance,
        we pass it in via the kwargs.
        """

        self.plugin = kwargs.pop('plugin')
        super().__init__(*args, **kwargs)

    id = serializers.CharField(source='pk', read_only=True)

    description = serializers.SerializerMethodField('get_description')
    stock = serializers.SerializerMethodField('get_stock')

    name = serializers.SerializerMethodField('get_name')

    def get_name(self, part):
        # Use helper to reduce duplication

        # Cache the 'use_ipn' setting
        if not hasattr(self, 'use_ipn'):
            self.use_ipn = str2bool(self.plugin.get_setting('KICAD_USE_IPN_AS_NAME', False))

        return _determine_part_name(part, self.use_ipn)

    def get_stock(self, part):
        """Custom name function.

        This will extract stock information and add it to a separate key variable which
        can be displayed inside the symbol picker
        """

        # In-stock quantity should be annotated to the queryset
        stock_count = getattr(part, 'unallocated_stock', 0)

        try:
            stock_count = decimal2string(stock_count)
        except Exception as e:
            logger.exception("Failed to format stock count: %s", e)

        return stock_count

    def get_description(self, part):
        """Custom name function.

        This will allow users to display stock information
        if they enable it.
        """

        if not hasattr(self, 'enable_stock_count'):
            self.enable_stock_count = str2bool(self.plugin.get_setting('KICAD_ENABLE_STOCK_COUNT', False))

        if not hasattr(self, 'stock_count_format'):
            self.stock_count_format = self.plugin.get_setting("KICAD_ENABLE_STOCK_COUNT_FORMAT", False)

        description = part.description

        # In-stock quantity should be annotated to the queryset
        stock_count = getattr(part, 'unallocated_stock', 0)

        if self.enable_stock_count:
            try:
                description = self.stock_count_format.format(part.description, decimal2string(stock_count))
            except Exception as e:
                logger.exception("Failed to format stock count: %s", e)

        return description

    @staticmethod
    def annotate_queryset(queryset):
        """Add extra annotations to the queryset."""

        # Annotate with the total variant stock quantity
        variant_query = variant_stock_query()
        queryset = queryset.annotate(
            in_stock=annotate_total_stock(),
            allocated_to_sales_orders=annotate_sales_order_allocations(),
            allocated_to_build_orders=annotate_build_order_allocations(),
            variant_stock=annotate_variant_quantity(variant_query, reference='quantity')
        )

        queryset = queryset.annotate(
            total_in_stock=ExpressionWrapper(
                F('in_stock') + F('variant_stock'),
                output_field=DecimalField()
            )
        )

        # Annotate with the total 'available stock' quantity
        # This is the current stock, minus any allocations
        queryset = queryset.annotate(
            unallocated_stock=Greatest(
                ExpressionWrapper(
                    F('total_in_stock') - F('allocated_to_sales_orders') - F('allocated_to_build_orders'),
                    output_field=DecimalField(),
                ),
                0,
                output_field=DecimalField(),
            )
        )

        return queryset


class KicadCategorySerializer(serializers.ModelSerializer):
    """Custom model serializer for a single KiCad category instance"""

    class Meta:
        """Metaclass defining serializer fields"""
        model = PartCategory
        fields = [
            'id',
            'name',
            'description'
        ]

    id = serializers.CharField(source='pk', read_only=True)
    name = serializers.SerializerMethodField('get_name')

    def get_name(self, category):
        return category.pathstring


class KicadDetailedCategorySerializer(serializers.ModelSerializer):
    """Custom model serializer for a single KiCad category instance"""

    class Meta:
        """Metaclass defining serializer fields"""
        model = SelectedCategory
        fields = [
            'pk',
            'category',
            'default_symbol',
            'default_footprint',
            'default_reference',
            'default_value_parameter_template',
            'footprint_parameter_template',
        ]

    def __init__(self, *args, **kwargs):
        super(KicadDetailedCategorySerializer, self).__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and request.method in ["POST", "PUT", "PATCH"]:
            self.Meta.depth = 0
        else:
            self.Meta.depth = 1
