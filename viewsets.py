import os

from rest_framework import viewsets, generics

from InvenTree.helpers import str2bool
from part.models import PartCategory, Part


class CategoryList(generics.ListAPIView):
    """List of available KiCad categories"""

    from .serializers import KicadCategorySerializer

    serializer_class = KicadCategorySerializer

    def get_queryset(self):
        """Return only PartCategory objects which are mapped to a SelectedCategory"""

        from .models import SelectedCategory

        category_ids = SelectedCategory.objects.all().values_list('category_id', flat=True)

        return PartCategory.objects.filter(pk__in=category_ids)


class CategoryViewSet(viewsets.ModelViewSet):

    from .serializers import KicadCategorySerializer

    serializer_class = KicadCategorySerializer
    queryset = PartCategory.objects.all()

    def get_queryset(self):

        from .models import SelectedCategory
        # Use user selected categories if available, otherwise display all.
        kicad_category_ids = SelectedCategory.objects.all().values_list('category_id', flat=True)

        if len(kicad_category_ids):
            queryset = PartCategory.objects.filter(pk__in=kicad_category_ids)
        else:
            queryset = PartCategory.objects.all()

        return queryset


class PartsPreviewList(generics.ListAPIView):
    """Preview list for all parts in a given category"""

    from .serializers import KicadPreviewPartSerializer

    serializer_class = KicadPreviewPartSerializer

    def get_queryset(self):
        """Return a list of parts in the specified category
        
        We check if the plugin setting KICAD_ENABLE_SUBCATEGORY is enabled,
        to determine if sub-category parts should be returned also
        """

        category_id = self.kwargs['id']

        # Get a reference to the plugin instance
        plugin = self.kwargs['plugin']

        cascade = str2bool(plugin.get_setting('KICAD_ENABLE_SUBCATEGORY', False))

        # Get the part category
        try:
            category = PartCategory.objects.get(id=category_id)
        except PartCategory.DoesNotExist:
            return Part.objects.none()
        
        if cascade:
            return Part.objects.filter(category__in=category.get_descendants(include_self=True))
        else:
            return Part.objects.filter(category=category)


class PartDetail(generics.RetrieveAPIView):
    """Detailed information endpoint for a single part instance.
    
    Here, the lookup id (pk) is the part id.
    The custom plugin serializer formats the data into a KiCad compatible format.
    """

    from .serializers import KicadDetailedPartSerializer

    serializer_class = KicadDetailedPartSerializer
    queryset = Part.objects.all()

    def get_serializer(self, *args, **kwargs):
        """Add the parent plugin instance to the serializer contenxt"""

        kwargs['plugin'] = self.kwargs['plugin']

        return self.serializer_class(*args, **kwargs)


class PartViewSet(viewsets.ModelViewSet):


    from .serializers import KicadDetailedPartSerializer, KicadPreviewPartSerializer

    # general serialiser in use
    serializer_class = KicadDetailedPartSerializer

    def get_queryset(self):
        queryset = Part.objects.all()
        category_id = self.request.GET.get('category')

        from .serializers import KicadPreviewPartSerializer

        # general this will be a bulk transfer for the tree view. To speed things up only return bare minimum.
        if category_id:
            self.serializer_class = KicadPreviewPartSerializer
            category = PartCategory.objects.get(id=category_id)
            queryset = category.get_parts(cascade=str2bool(os.getenv('KICAD_PLUGIN_GET_SUB_PARTS')))

        return queryset