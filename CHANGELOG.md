# Historial público de NexoMerc ERP

## [Portfolio DEMO V2-F22 QA1] — 2026-10-18

- Sincronización robusta del test de 60 ciclos de edición en UI, evitando reutilización de tablas Qt eliminadas durante recargas asíncronas.
- Pruebas gráficas QA1 repetidas en Windows: 4/4 aprobadas; suite completa 102/102 aprobadas.
- Sin cambios en la aplicación, datos, módulos ni autenticación.
- Galería comercial de diez imágenes cuadradas 1080 × 1080 publicada en `docs/github-images/`.
- Release `demo-v2-f22-qa1` publicada en GitHub. Pendientes las pruebas con periféricos reales y el flujo empresarial completo.

## [Portfolio DEMO V2-F22] — 2026-10-18

### Incluido desde la base del proyecto
- Aplicación de escritorio en Python/PySide6 con motor SQLite local.
- Catálogo de productos, fotografías, categorías, marcas y proveedores.
- Recepción, inventario con unidades base, paquetes/cajas, compras y traslados.
- POS, caja, ventas, promociones, cupones, clientes y tickets internos.
- Administración de usuarios, permisos, reportes y auditoría.
- Correcciones visuales del POS hasta la revisión F22 del código fuente entregado.

### Preparación de publicación
- README de portafolio y relación detallada de funciones.
- Guía de instalación Windows y dos scripts BAT de instalación/ejecución DEMO.
- Scripts de prueba no gráfica y detección estática de archivos sensibles.
- CI GitHub Actions (Python 3.12/3.13; **solo backend**, sin GUI).
- Archivos `.gitignore`, `.gitattributes`, licencia restrictiva y documentación de limitaciones.
- Exclusión de bases reales, credenciales, herramientas privadas e históricos de parches del paquete público.

**Alcance de verificación:** pruebas backend y suite gráfica QA1 en Windows (102/102 aprobadas); falta verificar periféricos reales y flujos empresariales integrales. `VERSION.txt=2.0.14` es metadato heredado, no contradice la revisión visual F22.
