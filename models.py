"""Models for Kicad Library Plugin."""

from django.db import models
from django.utils.translation import gettext_lazy as _

from part.models import PartCategory


class SelectedCategory(models.Model):
    """Categories which are used in Kicad."""

    category = models.OneToOneField(
        PartCategory,
        on_delete=models.CASCADE,
        related_name='get_enabled_kicad_categories',
        verbose_name=_('Category')
    )
