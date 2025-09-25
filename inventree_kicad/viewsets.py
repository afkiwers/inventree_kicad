from rest_framework import generics, permissions, response, views

from InvenTree.helpers import str2bool
from part.models import PartCategory, Part

from rest_framework import viewsets as rest_viewsets

from inventree_kicad import serializers
from django.shortcuts import get_object_or_404


class Index(views.APIView):
    """Index view which provides a list of available endpoints"""

    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request, *args, **kwargs):
        """Provide an index of the available endpoints"""

        # Get the base URL for the request, and construct secondary urls based on this
        # TODO: There is probably a better way of handling this!
        base_url = request.build_absolute_uri('/plugin/kicad-library-plugin/v1/')

        return response.Response(
            data={
                'categories': base_url + 'categories/',
                'parts': base_url + 'parts/',
            }
        )


class CategoryApi(rest_viewsets.ViewSet):
    from .models import SelectedCategory
    queryset = SelectedCategory.objects.all()
    serializer_class = serializers.KicadDetailedCategorySerializer

    def get_serializer(self, *args, **kwargs):
        """Add the parent plugin instance to the serializer contenxt"""

        kwargs['context'] = {'request': self.request}

        return self.serializer_class(*args, **kwargs)

    def get_part_parameter_id_by_name(self, name):
        from .models import PartParameterTemplate
        
        ret = None
        part_parameter = None

        if isinstance(name, int):
            # an integer was passed to the function -> assume it's the ID already
            ret = name
        elif isinstance(name, str):
            part_parameter = PartParameterTemplate.objects.filter(name=name).first()

            if part_parameter:
                ret = part_parameter.pk

        return ret

    def list(self, request):
        from .models import SelectedCategory
        
        queryset = SelectedCategory.objects.all()
        serializer = serializers.KicadDetailedCategorySerializer(queryset, many=True)

        return response.Response(serializer.data)
    
    def retrieve(self, request, pk=None):
        from .models import SelectedCategory

        category = get_object_or_404(SelectedCategory, pk=pk)
        serializer = serializers.KicadDetailedCategorySerializer(category)

        return response.Response(serializer.data)
    
    def partial_update(self, request, pk=None):
        return self.update(request, pk, partial=True)
    
    def update(self, request, pk=None, **kwargs):
        from .models import SelectedCategory

        category = get_object_or_404(SelectedCategory, pk=pk)

        for parameter in ['default_value_parameter_template', 'footprint_parameter_template']:
            if parameter in request.data:
                request.data[parameter] = self.get_part_parameter_id_by_name(request.data.pop(parameter))

        serializer = self.get_serializer(category, data=request.data, partial=kwargs.get('partial', False))
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return response.Response(serializer.data)

    def create(self, request):
        from part.models import PartCategory, PartParameterTemplate

        part_category = get_object_or_404(PartCategory, pk=request.data.get('category'))

        validated_data = {
            "category": part_category,
            "default_symbol": request.data.get('default_symbol', ''),
            "default_footprint": request.data.get('default_footprint', ''),
            "default_reference": request.data.get('default_reference', ''),
        }

        # Add PartParameterTemplate keys
        # Allow passing the parameter name instead of the id
        for parameter in ['default_value_parameter_template', 'footprint_parameter_template']:
            key = 'name' if isinstance(request.data.get(parameter), str) else 'pk'
            validated_data[parameter] = PartParameterTemplate.objects.filter(**{key: request.data.get(parameter)}).first()

        serializer = serializers.KicadDetailedCategorySerializer()
        created_category = serializer.create(validated_data)

        serializer = serializers.KicadDetailedCategorySerializer(created_category)

        return response.Response(serializer.data)
    
    def destroy(self, request, pk):
        from .models import SelectedCategory

        category = get_object_or_404(SelectedCategory, pk=pk)
        category.delete()

        return response.Response(status=204)


class CategoryList(generics.ListAPIView):
    """List of available KiCad categories"""

    serializer_class = serializers.KicadCategorySerializer

    def get_queryset(self):
        """Return only PartCategory objects which are mapped to a SelectedCategory"""

        from .models import SelectedCategory

        category_ids = SelectedCategory.objects.all().values_list('category_id', flat=True)

        return PartCategory.objects.filter(pk__in=category_ids)


class PartsPreviewList(generics.ListAPIView):
    """Preview list for all parts in a given category"""

    serializer_class = serializers.KicadPreviewPartSerializer

    def get_serializer(self, *args, **kwargs):
        """Add the parent plugin instance to the serializer contenxt"""

        kwargs['plugin'] = self.kwargs['plugin']

        return self.serializer_class(*args, **kwargs)

    def get_queryset(self):
        """Return a list of parts in the specified category
        
        We check if the plugin setting KICAD_ENABLE_SUBCATEGORY is enabled,
        to determine if sub-category parts should be returned also
        """

        category_id = self.kwargs.get('id', None)

        # Get a reference to the plugin instance
        plugin = self.kwargs['plugin']

        cascade = str2bool(plugin.get_setting('KICAD_ENABLE_SUBCATEGORY', False))

        queryset = Part.objects.all()

        category = PartCategory.objects.filter(id=category_id).first()

        if category is not None:
            if cascade:
                queryset = queryset.filter(
                    category__in=category.get_descendants(include_self=True)
                )
            else:
                queryset = queryset.filter(category=category)

        if str2bool(plugin.get_setting('KICAD_HIDE_INACTIVE_PARTS', True)):
            queryset = queryset.filter(active=True)

        if str2bool(plugin.get_setting('KICAD_HIDE_TEMPLATE_PARTS', True)):
            queryset = queryset.filter(is_template=False)

        queryset = serializers.KicadPreviewPartSerializer.annotate_queryset(queryset)

        return queryset


class PartDetail(generics.RetrieveAPIView):
    """Detailed information endpoint for a single part instance.
    
    Here, the lookup id (pk) is the part id.
    The custom plugin serializer formats the data into a KiCad compatible format.
    """

    serializer_class = serializers.KicadDetailedPartSerializer
    queryset = Part.objects.all()

    def get_queryset(self):
        """Prefetch related fields to speed up query"""

        queryset = super().get_queryset()

        queryset = queryset.prefetch_related(
            'parameters',
        )

        return queryset

    def get_serializer(self, *args, **kwargs):
        """Add the parent plugin instance to the serializer contenxt"""

        kwargs['plugin'] = self.kwargs['plugin']
        kwargs['context'] = {'request': self.request}

        return self.serializer_class(*args, **kwargs)
