from rest_framework import serializers
from rest_framework.reverse import reverse_lazy

from part.models import Part, PartCategory, PartParameterTemplate


class KicadDetailedPartSerializer(serializers.ModelSerializer):
    class Meta:
        """Metaclass defining serializer fields"""
        model = Part

        # fields = [f.name for f in Part._meta.fields]

        fields = [
            'pk',
            'name',
            'fields',
        ]

    pk = serializers.SerializerMethodField('get_pk')
    name = serializers.SerializerMethodField('get_name')
    fields = serializers.SerializerMethodField('get_kicad_fields')

    def get_api_url(self):
        """Return the API url associated with this serializer"""
        return reverse_lazy('api-kicad-part-list')

    def get_name(self, part):
        return part.full_name

    def get_pk(self, part):
        return f'{part.pk}'

    def get_kicad_fields(self, part):
        para = part.get_parameters()

        paras = {}
        for p in para:
            paras[str(p.template).capitalize()] = f'{p.data}'

        paras['Description'] = f'{part.description}'
        paras['Inventree'] = f'{part.pk}'
        paras['Notes'] = f'{part.notes}' if part.notes else ""

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
        name = f'{category.pathstring.replace("/", "->")} ({category.description})' if category.description else category.pathstring.replace(
            "/", "->")

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
