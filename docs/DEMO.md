# Uso de la edición DEMO pública

Esta es una edición funcional con fuentes disponibles para evaluación personal y técnica no comercial. La versión privada del propietario se conserva aparte; aquí no hay herramientas administrativas privadas ni historial interno de mantenimiento.

## Recorrido recomendado

1. Ejecutar el programa mediante `INICIAR_DEMO_WINDOWS.bat` (o PowerShell con `NEXOMERC_DATA_DIR`).
2. Crear administrador propio en base nueva: no hay credenciales predeterminadas.
3. Registrar categorías, marcas y un proveedor ficticio.
4. Crear artículos con precios, cantidades y stock mínimo/máximo.
5. Registrar entrada de mercadería y consultar Kardex/existencias por sucursal.
6. Crear una orden de compra y recibir un pedido de prueba.
7. Abrir caja, agregar productos al POS, realizar una venta y consultar ticket **no fiscal**.
8. Consultar informes, auditoría, permisos y opciones generales.

## Datos de ejemplo para escribir manualmente

- Sucursal: `Casa central` (la crea el sistema).
- Proveedor: `Proveedor Demo`.
- Productos ficticios: `Leche`, `Arroz`, `Aceite`, `Huevos`, `Manzanas`, `Queso`, `Detergente`.
- Cliente: `Cliente Demo 1`.

No se incluye una base SQLite con usuarios ya creados, contraseñas o datos de terceros. `data/` y los archivos de base locales están ignorados por Git.

## Alcance y advertencias

- Los datos de demostración son responsabilidad de quien ejecuta el software: **no introducir clientes ni ventas reales**.
- La GUI y dispositivos de Windows se deben probar en el equipo antes de anunciar la demostración como validada.
- La galería actual contiene diez composiciones comerciales 1080 × 1080 en `docs/github-images/`, basadas en capturas de Windows. Las capturas originales F03 siguen archivadas en `docs/screenshots/`; las composiciones comerciales no sustituyen capturas sin editar.
- No hay inteligencia artificial, bots ni facturación fiscal homologada.
- Esta distribución incluye código visible. Ver `LICENSE.md` antes de reutilizarlo.
