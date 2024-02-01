"""Models for Kicad Library Plugin."""
from django.core import validators
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User

from part.models import PartCategory, PartParameterTemplate


class SelectedCategory(models.Model):
    """Categories which are used in Kicad."""

    class Meta:
        app_label = 'inventree_kicad'
        verbose_name = 'KiCad Category'
        verbose_name_plural = 'KiCad Categories'

    category = models.OneToOneField(
        PartCategory,
        on_delete=models.CASCADE,
        related_name='get_enabled_kicad_categories',
        verbose_name=_('Category')
    )

    default_symbol = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('Default Symbol'),
        help_text=_('Default symbol for this category, if not specified for an individual part'),
    )

    default_footprint = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('Default Footprint'),
        help_text=_('Default footprint for this category, if not specified for an individual part'),
    )

    default_reference = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_('Default Reference'),
        help_text=_('Default reference for this category, if not specified for an individual part'),
    )

    default_value_parameter_template = models.ForeignKey(
        PartParameterTemplate,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name=_('Default Value Parameter Template'),
        help_text=_('Default value parameter template for this category, if not specified for an individual part'),
    )

    footprint_parameter_template = models.ForeignKey(
        PartParameterTemplate,
        on_delete=models.SET_NULL,
        related_name="footprint_kicad_categories",
        blank=True,
        null=True,
        verbose_name=_('Footprint Parameter Template'),
        help_text=_('Footprint parameter template for this category. Overrides the KICAD_FOOTPRINT_PARAMETER setting for this category.'),
    )

    def __str__(self):
        """Default name string which is returned when object is called"""
        return f'{self.category.pathstring}'


class FootprintParameterMapping(models.Model):
    """Mapping entry to map from the footprint parameter value to a KiCad footprint name"""

    class Meta:
        app_label = "inventree_kicad"
        verbose_name = "Footprint Mapping"
        unique_together = ("kicad_category", "parameter_value")

    kicad_category = models.ForeignKey(SelectedCategory, on_delete=models.CASCADE)

    parameter_value = models.CharField(
        max_length=200,
        verbose_name="Footprint Parameter Value",
    )

    kicad_footprint = models.CharField(
        max_length=200,
        verbose_name="KiCad Footprint",
    )

    def __str__(self):
        """Default name string which is returned when object is called"""
        return f"{self.kicad_category}: {self.parameter_value} -> {self.kicad_footprint}"


class ProgressIndicator(models.Model):
    """Progress indicators which are used to display a loading bar inside a multiuser environment."""

    class Meta:
        app_label = 'inventree_kicad'
        verbose_name = 'Progress Indicator'
        verbose_name_plural = 'Progress Indicators'

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='get_progress_bar_users',
        verbose_name=_('Category')
    )

    current_progress = models.IntegerField(
        default=0,
        validators=[validators.MinValueValidator(0), validators.MaxValueValidator(100)],
        help_text=_('current progress')
    )

    file_name = models.CharField(
        max_length=100,
        default='',
        help_text=_('Name of currently processed file.')
    )

    def __str__(self):
        """Default name string which is returned when object is called"""
        return f'{self.user.username}'
