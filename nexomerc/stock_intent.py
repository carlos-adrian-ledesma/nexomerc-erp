"""Pure validation for incoming stock entered in Products (independent of Qt)."""
from decimal import Decimal, InvalidOperation
from .core import ERPError


def determine_entry(enabled, quantity, kind, pack_factor, box_factor, base_unit, branch_id):
    """Return True if a stock operation was intentionally requested, else False.

    Fail closed on nonzero quantities with the switch disabled: never silently
    report product saved when the operator expected the stock to be added.
    """
    try:
        qty = Decimal(str(quantity).replace(',', '.'))
    except (ValueError, InvalidOperation, TypeError):
        raise ERPError('La cantidad recibida no es válida.')
    if not qty.is_finite() or qty < 0:
        raise ERPError('La cantidad debe ser positiva o cero.')
    if qty and not enabled:
        raise ERPError('Ingresaste una cantidad, pero la opción de registrar stock está desactivada. Activala antes de guardar o poné cantidad cero.')
    if enabled and not qty:
        raise ERPError('Activaste el ingreso de stock, pero no indicaste la cantidad que llegó.')
    if not enabled:
        return False
    if not branch_id:
        raise ERPError('Elegí la sucursal en la que ingresa la mercadería.')
    if kind not in {'base','pack','box'}:
        raise ERPError('La presentación recibida no es válida.')
    if qty * 1000 != (qty * 1000).to_integral_value():
        raise ERPError('Se permiten hasta tres decimales.')
    if (kind != 'base' or base_unit not in ('kg','l')) and qty != qty.to_integral_value():
        raise ERPError('Las unidades, cajas y paquetes deben ingresarse enteros.')
    if kind in ('box','pack'):
        factor = Decimal(str(box_factor if kind == 'box' else pack_factor).replace(',', '.'))
        if not factor.is_finite() or factor <= 0:
            raise ERPError('Antes de cargar cajas/paquetes configurá el contenido de la presentación en Precios y presentación.')
        if qty * factor * 1000 != (qty * factor * 1000).to_integral_value():
            raise ERPError('La conversión de esta presentación supera tres decimales.')
    return True
