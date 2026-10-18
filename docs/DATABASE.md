# Base de datos SQLite

`ERP(root=None)` determina el directorio por `NEXOMERC_DATA_DIR`, o en Windows por `%LOCALAPPDATA%\NexoMercERP`; en otros sistemas usa `~/.nexomerc_erp`.
La aplicación crea `nexomerc.sqlite3` y `photos/` al primer inicio. Usa `SCHEMA` en `nexomerc/core.py`, `PRAGMA journal_mode=WAL` y `PRAGMA busy_timeout=15000`.

Se genera una sucursal inicial `Casa central` y la configuración local; **el administrador se crea mediante el formulario inicial** al abrir la GUI. No se incluyen usuarios, contraseñas ni bases preconfiguradas.

No versionar archivos SQLite, WAL, SHM, fotos del usuario, respaldos ni exportaciones con datos reales.
Hacer copias de respaldo consistentes mediante mecanismos de SQLite y almacenarlas fuera del repositorio.
