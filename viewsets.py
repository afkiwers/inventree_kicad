import os

from rest_framework.pagination import PageNumberPagination
from rest_framework import routers, viewsets, generics

from part.models import PartCategory, Part


def str2bool(v):
    return v.lower() in ("True", "true", "1")


# Paginator is not actually used by KiCad but helps when manually browsing
# through the parts
class DefaultPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


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


class PartsPreViewList(generics.ListAPIView):
    from .serializers import KicadPreViewPartSerializer

    serializer_class = KicadPreViewPartSerializer

    def get_queryset(self):
        queryset = Part.objects.all()
        category_id = self.kwargs['id']

        # general this will be a bulk transfer for the tree view. To speed things up only return bare minimum.
        if category_id:
            self.serializer_class = self.KicadPreViewPartSerializer
            try:
                category = PartCategory.objects.get(id=category_id)
                queryset = category.get_parts(cascade=str2bool(os.getenv('KICAD_PLUGIN_GET_SUB_PARTS')))
            except:
                queryset = Part.objects.none()

        return queryset


class PartViewSet(viewsets.ModelViewSet):
    from .serializers import KicadDetailedPartSerializer, KicadPreViewPartSerializer

    # general serialiser in use
    serializer_class = KicadDetailedPartSerializer
    pagination_class = DefaultPagination

    def get_queryset(self):
        queryset = Part.objects.all()
        category_id = self.request.GET.get('category')

        # general this will be a bulk transfer for the tree view. To speed things up only return bare minimum.
        if category_id:
            self.serializer_class = self.KicadPreViewPartSerializer
            category = PartCategory.objects.get(id=category_id)
            queryset = category.get_parts(cascade=str2bool(os.getenv('KICAD_PLUGIN_GET_SUB_PARTS')))

        return queryset
