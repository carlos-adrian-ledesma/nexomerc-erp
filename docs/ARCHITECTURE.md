# Arquitectura técnica

- `run.py`: punto de entrada de la interfaz Qt.
- `nexomerc/ui.py`: UI PySide6 y flujos de navegación; incluye personalizaciones visuales acumuladas F22.
- `nexomerc/core.py`: capa de dominio, persistencia SQLite, transacciones y validación de permisos.
- `nexomerc/retail.py`, `stock_intent.py`, `units.py`, `currency.py`: flujos de catálogo, unidades, stock y dinero.
- `nexomerc/ticket_printer.py`: funciones de impresión de comprobantes internos.
- `nexomerc/locale_ui.py`, `translations.json`: internacionalización y traducciones.
- `nexomerc/retail.qss`, `assets/`: apariencia, iconos, marca y sonidos.
- `tests/`: verificaciones por componentes y regresiones históricas.

La app es **local-first**: el backend transaccional usa la biblioteca estándar de Python.
La GUI requiere PySide6. Las rutas a activos se calculan respecto del código.
Los datos del comercio residen en `ERP(root)` o `default_data_dir()`, no junto a los fuentes.
El acceso a módulos es comprobado por la capa de dominio; no depende únicamente de ocultar controles de interfaz.
No se identifica un servicio web ni sincronización multi-PC en este paquete.
