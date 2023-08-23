from django.http import JsonResponse

from part.models import PartParameterTemplate


def kicad_settings(request):
    is_displayed = {
        "value": '1',
        "footprint": '0',
        "datasheet": '0',
        "symbol": '0',
        "reference": '1',
        "description": '0',
        "keywords": '0',
        "Inventree": '0',
        "Size": '1'
    }

    # hide all parameters for now
    paras = PartParameterTemplate.objects.all()
    for p in paras:
        if is_displayed[p.name.lower()]:
            continue

        is_displayed[p.name.lower()] = "1"

    data = {
        "show_field": is_displayed,
    }

    return JsonResponse(data)
