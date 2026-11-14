"""Templates for values sent to KiCad, e.g. "{part.IPN}" or "{param[Tolerance]}".

Used by the stock count display format, the field mapping (template rows) and the
part name template. Python format strings are used, with these variables:

- part: selected part attributes, see TemplatePart
- param: the part's parameter values by parameter name, see ParameterValues

This module deliberately imports no models, so the plugin class can use it at load time.
"""

from decimal import Decimal
from functools import cached_property
from types import SimpleNamespace

from django.core.exceptions import ValidationError


class TemplatePart:
    """The 'part' object available in templates, e.g. {part.name}."""

    def __init__(self, part, stock=None):
        self._part = part
        self.pk = part.pk
        self.name = part.name
        self.IPN = part.IPN or ""
        self.description = part.description or ""
        self.revision = part.revision or ""
        self.keywords = part.keywords or ""
        self.units = part.units or ""
        self.link = part.link or ""

        # Only available if stock information is enabled (the stock queries are skipped otherwise),
        # so {part.stock} fails with a clear error instead of rendering an empty value.
        if stock is not None:
            self.stock = stock

    @cached_property
    def category(self):
        """Full category path, e.g. 'Electronics/Passives/Resistors'."""
        category = self._part.category
        return category.pathstring if category else ""

    @cached_property
    def used_in(self):
        """Number of assemblies whose BOM uses this part.

        This needs several database queries per part, so it is only evaluated
        if the template actually contains {part.used_in}.
        """
        return self._part.used_in_count


# Kept for compatibility, this was the name before templates were used outside the stock format
StockFormatPart = TemplatePart


class ParameterValues(dict):
    """Parameter values by parameter name, as {param[<name>]} in templates.

    Names match case-insensitively, and a parameter the part doesn't have is an
    empty string, so a single part without the parameter doesn't fail the template.
    """

    def __init__(self, values=None):
        super().__init__({str(k).lower(): v for k, v in (values or {}).items()})

    def __getitem__(self, key):
        return super().get(str(key).lower(), "")


def render_template(format_string: str, part, *, stock=None, params=None, args=()):
    """Render a template for the given part. Raises an exception if the template is invalid."""
    return format_string.format(
        *args,
        part=TemplatePart(part, stock),
        param=params if params is not None else ParameterValues(),
    ).strip()


def template_error(exc, positional_hint=None) -> str:
    """Return a readable message for an exception raised while rendering a template."""
    if isinstance(exc, KeyError):
        return f"Unknown placeholder {{{exc.args[0]}}} - use {{part.<name>}} or {{param[<name>]}}"

    if isinstance(exc, IndexError):
        return positional_hint or "Placeholders like {0} are not available here"

    if isinstance(exc, AttributeError):
        name = getattr(exc, "name", None)

        if name == "stock":
            return (
                "{part.stock} is only available if 'Display Available Stock' is enabled"
            )

        return f"Unknown part attribute: {name or exc}"

    return str(exc)


# Example part, used to preview and validate templates
EXAMPLE_PART = SimpleNamespace(
    pk=42,
    name="RES-10K-0603",
    IPN="R-0001",
    description="Resistor 10k 1% 0603",
    revision="A",
    keywords="resistor smd",
    units="pcs",
    link="https://www.example.com/datasheet.pdf",
    category=SimpleNamespace(pathstring="Electronics/Passives/Resistors"),
    used_in_count=3,
)
EXAMPLE_STOCK = Decimal(1250)
EXAMPLE_PARAMS = ParameterValues({
    "Resistance": "10k",
    "Tolerance": "1%",
    "Package": "0603",
})


def preview_template(format_string: str, *, stock_enabled=False) -> str:
    """Render a template for the example part. Raises an exception if it is invalid."""
    return render_template(
        format_string,
        EXAMPLE_PART,
        stock=EXAMPLE_STOCK if stock_enabled else None,
        params=EXAMPLE_PARAMS,
    )


def validate_name_template(value):
    """Setting validator for the part name template (empty = not used)."""
    if not str(value or "").strip():
        return

    try:
        preview_template(str(value))
    except Exception as exc:
        raise ValidationError(template_error(exc))
