# Funcionalidades de NexoMerc ERP — revisión V2-F22

Este inventario describe funciones identificadas en el **código entregado** (`nexomerc/core.py`, `ui.py`, `retail.py`, `ticket_printer.py`, `translations.json`). No afirma que todos los recorridos se hayan validado manualmente en Windows. Las capturas incluidas en el repositorio son de F03 y se marcan como históricas.

## 1. Panel principal
- Resumen de ventas del día y del mes.
- Contador de productos con stock bajo.
- Indicador de órdenes de compra pendientes.
- Acceso al inventario y a la caja.
- Vista de actividad reciente registrada en auditoría.

## 2. Productos, categorías y marcas
- Alta, edición, consulta y archivo/restauración de productos conservando el historial.
- SKU único, código de barras, nombre, categoría, marca y proveedor.
- Precio de venta y costo, con tratamiento monetario de precisión decimal.
- Unidad base del producto (unidad, kilogramo o litro, según configuración).
- Umbrales de stock mínimo y máximo (no equivalen a cantidades existentes).
- Fotografía asociada a cada producto, almacenada en el directorio de datos local.
- Carga conjunta de producto y su stock inicial, dentro de una transacción.
- Libreta/anotaciones para categorías y marcas; fotografía de marca donde la interfaz lo permite.
- Exportación del catálogo visible a CSV.

## 3. Inventario
- Existencias por producto y sucursal, unidades reservadas y stock disponible.
- Ingreso manual, ajustes positivos/negativos y conteo físico.
- Registro de movimientos / Kardex por producto.
- Reservas y liberación de stock.
- Restricciones de stock para evitar saldos negativos o inconsistentes.
- Consulta de movimientos y recepciones manuales recientes.

## 4. Recepción de mercadería
- Ingreso en unidad base, paquete o caja, con factores de conversión configurados por producto.
- Referencia o remito, notas y fecha de vencimiento opcional en recepciones manuales.
- Acumulación de stock recibido en lugar de sustitución del total existente.
- Operaciones identificadas con claves que evitan duplicaciones accidentales de recepción.
- Historial de entrada con sucursal y usuario responsable.

## 5. Compras y proveedores
- Fichas y mantenimiento de proveedores.
- Órdenes de compra y líneas de productos.
- Preparación, envío/aprobación y cancelación de órdenes según su estado.
- Recepción parcial o completa contra orden y remito, con actualización del inventario.
- Seguimiento de lo pedido y lo recibido.

## 6. Ventas, POS y caja
- Búsqueda y selección de artículos mediante catálogo y lectura de códigos tipo teclado.
- Carrito de compra, unidades/presentaciones y cálculo de subtotal.
- Validación de disponibilidad antes del cobro.
- Apertura de caja, cierre/arqueo y seguimiento de sesión.
- Registro transaccional de ventas y descuento de existencias.
- Selección de cliente y medio de pago.
- Historial de ventas recientes, anulación autorizada con reversión de stock.
- Tickets/comprobantes **internos NO fiscales**, exportación a texto e integración de impresión a través de Qt (sujeta a impresoras y controladores reales).
- POS con panel de catálogo y carrito redimensionables (QSplitter), ajustes de espacio y scroll incorporados hasta F22.

## 7. Clientes, precios y cupones
- Registro de clientes y consulta de compras por cliente.
- Promociones con precio específico, fecha inicial/final y ámbito de sucursal.
- Validación de promociones vigentes en el precio aplicado.
- Reglas de cupones por monto de compra, emisión y canje sujeto a validaciones.
- Descuentos por cupón y vinculación de recompensas al cliente registrado.

## 8. Sucursales y traslados
- Catálogo de sucursales con asignación de usuarios y productos.
- Stock por sucursal.
- Transferencias origen/destino: borrador, despacho, recepción y cancelación donde el estado lo permite.
- Registro de movimientos asociado al traslado.

## 9. Usuarios y acceso
- Alta inicial del primer administrador en una base nueva (sin credenciales por defecto).
- Roles incluidos: `admin`, `manager`, `warehouse`, `purchasing`, `cashier`, `auditor`.
- Permisos por módulo y acción; restricciones por sucursal y usuario.
- Verificación de contraseña con PBKDF2-HMAC-SHA256, sal individual y bloqueo temporal por intentos fallidos.
- Herramientas privadas de restablecimiento de contraseñas **no incluidas** en el código público.

## 10. Reportes, auditoría y resguardo
- Reportes de ventas por período y sucursal y consulta de indicadores de actividad.
- Exportación de reportes y de registro de auditoría a CSV.
- Registro de operaciones con hashes encadenados para evidenciar alteraciones; no es inmutable frente a quien controle físicamente la base.
- Copias de seguridad locales por funciones del motor. Se recomienda verificar la restauración en un entorno aislado.

## 11. Configuración, idioma y presentación
- Datos comerciales básicos, moneda/localización y texto de pie de comprobante.
- Traducciones presentes para español, inglés, portugués, japonés, filipino, vietnamita y chino. **La cobertura puede variar por pantalla y textos añadidos en parches.**
- Recursos gráficos de marca, tema de interfaz QSS y avisos opcionales según configuración.
- Accesos rápidos, tablas con desplazamiento y paneles redimensionables.

## Límites declarados

- No incluye asistentes de inteligencia artificial ni bots automatizados.
- No implementa servidor o sincronización corporativa LAN/Internet en este paquete.
- No constituye software fiscal homologado: los comprobantes son internos no fiscales.
- No se garantiza compatibilidad con cualquier ticketera/lector ni todos los sistemas operativos sin pruebas de hardware.
- La distribución contiene una parte importante del código real autorizado por el propietario para evaluación; la licencia limita permisos legales, **no evita la copia técnica**.
- Validación de PySide6/Windows y recorridos completos todavía pendiente según `PUBLIC_RELEASE_CHECKLIST.md`.
