from rest_framework import serializers
from rest_framework.reverse import reverse_lazy

from part.models import Part, PartCategory, PartParameter


class KicadDetailedPartSerializer(serializers.ModelSerializer):
    """Custom model serializer for a single KiCad part instance"""

    def get_api_url(self):
        """Return the API url associated with this serializer"""
        return reverse_lazy('api-kicad-part-list')

    def __init__(self, *args, **kwargs):
        """Custom initialization for this seriailzer.
        
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

    fields = serializers.SerializerMethodField('get_kicad_fields')

    def get_kicad_category(self, part):
        """For the provided part instance, find the associated SelectedCategory instance.
        
        If there are multiple possible associations, return the "deepest" one.
        """

        # Prevent duplicate lookups
        if hasattr(self, 'kicad_category'):
            return self.kicad_category

        from .models import SelectedCategory

        # If the selcted part does not have a category, return None
        if not part.category:
            return None

        # Get the category tree for the selected part
        categories = part.category.get_ancestors(include_self=True)

        self.kicad_category = SelectedCategory.objects.filter(category__in=categories).order_by('-category__level').first()

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

        return reference

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

        return symbol

    def get_footprint(self, part):
        """Return the footprint associated with this part.
        
        - First, check if the part has a footprint assigned (via parameter)
        - Otherwise, fallback to the default footprint for the KiCad Category
        """

        footprint = ""

        if kicad_category := self.get_kicad_category(part):
            footprint = kicad_category.default_footprint
        
        template_id = self.plugin.get_setting('KICAD_FOOTPRINT_PARAMETER', None)

        footprint = self.get_parameter_value(part, template_id, backup_value=footprint)

        return footprint

    def get_datasheet(self, part):
        """Return the datasheet associated with this part.
        
        Here, we look at the attachments associated with the part,
        and return the first one which has a comment matching "datasheet"
        """

        datasheet = None

        for attachment in part.attachments.all():
            if attachment.comment.lower() == 'datasheet':
                datasheet = attachment
                break

        if datasheet:
            return datasheet.fully_qualified_url()

        # Default, return empty string
        return ""

    def get_value(self, part):
        """Return the value associated with this part.
        
        If the part value has been specified via parameter, return that.
        Otherwise, simply return the name of the part
        """

        # Fallback to the part name
        value = part.full_name

        # Find the value parameter value associated with this part instance
        template_id = self.plugin.get_setting('KICAD_VALUE_PARAMETER', None)

        value = self.get_parameter_value(part, template_id, backup_value=value)

        return value

    def get_custom_fields(self, part):
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
        ]

        excluded_field_names = [
            'value',
            'footprint',
            'datasheet',
            'reference',
            'description',
            'keywords',
        ]

        # Always include the InvenTree field, which has the ID of the part
        fields = {
            'InvenTree': {
                'value': f'{part.id}',
                'visible': 'False'
            }
        }

        for parameter in part.parameters.all():
            # Exclude any which have already been used for default KiCad fields
            if str(parameter.template.pk) in excluded_templates:
                continue
                
            # Skip any which conflict with KiCad field names
            if parameter.template.name in excluded_field_names:
                continue

            fields[parameter.template.name] = {
                "value": parameter.data,
                "visible": 'False'
            }

        return fields

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
                "value": part.description,
                "visible": 'False'
            },
            'keywords': {
                "value": part.keywords,
                "visible": 'False'
            },
        }

        return kicad_default_fields | self.get_custom_fields(part)

    def get_exclude_from_bom(self, part):
        """Return the whether or not the part should be excluded from the bom.
        
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
        """Return the whether or not the part should be excluded from the board.
        
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
        """Return the whether or not the part should be excluded from the sim.
        
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
        ]

    def __init__(self, *args, **kwargs):
        """Custom initialization for this seriailzer.
        
        As we need to have access to the parent plugin instance,
        we pass it in via the kwargs.
        """

        self.plugin = kwargs.pop('plugin')
        super().__init__(*args, **kwargs)

    id = serializers.CharField(source='pk', read_only=True)


class KicadCategorySerializer(serializers.ModelSerializer):
    """Custom model serializer for a single KiCad category instance"""

    class Meta:
        """Metaclass defining serializer fields"""
        model = PartCategory
        fields = [
            'id',
            'name',
            'description',
            'pathstring',
        ]

    id = serializers.CharField(source='pk', read_only=True)
