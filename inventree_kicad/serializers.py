from rest_framework import serializers
from rest_framework.reverse import reverse_lazy

from part.models import Part, PartCategory, PartParameterTemplate


class KicadDetailedPartSerializer(serializers.ModelSerializer):
    class Meta:
        """Metaclass defining serializer fields"""
        model = Part

        fields = [
            'pk',
            'fields',
        ]

    pk = serializers.SerializerMethodField('get_pk')
    fields = serializers.SerializerMethodField('get_kicad_fields')

    def get_api_url(self):
        """Return the API url associated with this serializer"""
        return reverse_lazy('api-kicad-part-list')

    def get_pk(self, part):
        return f'{part.pk}'

    def get_kicad_fields(self, part):
        para = part.get_parameters()

        paras = {}
        for p in para:
            paras[str(p.template).capitalize()] = f'{p.data}'

        paras['Value'] = part.full_name
        paras['Description'] = f'{part.description}'
        paras['Inventree'] = f'{part.pk}'
        paras['Notes'] = f'{part.notes}' if part.notes else ""

        ################################################################################
        ################# Example, this could be part of the dataset ###################
        ################################################################################
        
        try:
            part_type = part.full_name.split('_')[0]

            if part_type == 'R':
                paras['Symbol'] = "Device:R"

                if part.full_name.split('_')[2] == '0402':
                    paras['Footprint'] = 'Resistor_SMD:R_0402_1005Metric'

                if part.full_name.split('_')[2] == '0603':
                    paras['Footprint'] = "Resistor_SMD:R_0603_1608Metric"

                if part.full_name.split('_')[2] == '0805':
                    paras['Footprint'] = 'Resistor_SMD:R_0805_2012Metric'

            elif part_type == 'C':
                paras['Symbol'] = "Device:C"
                paras['Footprint'] = "Capacitor_SMD:C_0805_2012Metric"

                if part.full_name.split('_')[2] == '0402':
                    paras['Footprint'] = 'Capacitor_SMD:R_0402_1005Metric'

                if part.full_name.split('_')[2] == '0603':
                    paras['Footprint'] = "Capacitor_SMD:R_0603_1608Metric"

                if part.full_name.split('_')[2] == '0805':
                    paras['Footprint'] = 'Capacitor_SMD:R_0805_2012Metric'

        except:
            pass

        try:
            paras['Reference'] = part.full_name.split('_')[0]
            if len(part.full_name.split('_')) <= 1:
                paras['Reference'] = "X"
        except:
            paras['Reference'] = "X"

        try:
            paras['Value'] = part.full_name.split('_')[1]
        except:
            pass

        try:
            paras['Size'] = part.full_name.split('_')[2]
        except:
            pass

        try:
            paras['Rating'] = part.full_name.split('_')[3]
        except:
            pass

        try:
            paras['Tolerance'] = part.full_name.split('_')[4]
        except:
            pass

        ################################################################################
        ################################################################################
        ################################################################################

        idx = 1
        for a in part.attachments.all():
            paras[f'attachments_{idx}'] = f'{a}'
            idx += 1

        return paras


class KicadPreViewPartSerializer(serializers.ModelSerializer):
    class Meta:
        """Metaclass defining serializer fields"""
        model = Part

        # fields = [f.name for f in Part._meta.fields]

        fields = [
            'pk',
            'name',
        ]

    pk = serializers.SerializerMethodField('get_pk')
    name = serializers.SerializerMethodField('get_name')

    def get_api_url(self):
        """Return the API url associated with this serializer"""
        return reverse_lazy('api-kicad-part-list')

    def get_name(self, part):
        return part.full_name

    def get_pk(self, part):
        return f'{part.pk}'


class KicadCategorySerializer(serializers.ModelSerializer):
    class Meta:
        """Metaclass defining serializer fields"""
        model = PartCategory
        fields = [
            'pk',
            'name',
        ]

    pk = serializers.SerializerMethodField('get_pk')
    name = serializers.SerializerMethodField('get_name')

    def get_name(self, category):
        name = f'{category.pathstring} ({category.description})' if category.description else category.pathstring

        return name

    def get_pk(self, category):
        return f'{category.pk}'


class KicadPartParameterTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        """Metaclass defining serializer fields"""
        model = PartParameterTemplate
        fields = [
            'name',
        ]


class KicadFieldsSerializer(serializers.ModelSerializer):
    class Meta:
        """Metaclass defining serializer fields"""
        model = PartParameterTemplate
        fields = [
            'name',
        ]
