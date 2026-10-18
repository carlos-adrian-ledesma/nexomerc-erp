"""Unit conversions for checkout and stock presentation (no Qt required)."""
from decimal import Decimal, InvalidOperation
from .core import ERPError


def sale_base_milli(qty, base_unit, presentation, pack_milli=0, box_milli=0):
    """Return milli-units of base stock represented by the selected sale form.

    u is sold in whole units; base kg/L may be fractional to three places.
    Packs and boxes must be whole and have a defined base-unit size.
    """
    try:
        q = Decimal(str(qty).replace(',', '.'))
    except (ValueError, InvalidOperation, TypeError):
        raise ERPError('Cantidad de venta inválida.')
    if not q.is_finite() or q <= 0 or (q * 1000) != (q * 1000).to_integral_value():
        raise ERPError('Ingresá una cantidad positiva con hasta tres decimales.')
    if presentation not in ('base', 'pack', 'box'):
        raise ERPError('Presentación de venta inválida.')
    if presentation != 'base' or base_unit not in ('kg', 'l'):
        if q != q.to_integral_value():
            raise ERPError('Las unidades, los paquetes y las cajas se venden enteros.')
    factor = {'base': 1000, 'pack': pack_milli, 'box': box_milli}[presentation]
    if not isinstance(factor, int) or factor <= 0:
        raise ERPError('Configurá el contenido del paquete o caja en Productos.')
    n = q * Decimal(factor)
    if n != n.to_integral_value() or n > 9223372036854775807:
        raise ERPError('La conversión de la presentación no es válida.')
    return int(n)
