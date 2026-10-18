# Instalación y ejecución en Windows — NexoMerc ERP DEMO

## Requisitos

- Windows 10/11 de 64 bits.
- Python **3.13 de 64 bits** recomendado (también puede probarse 3.12). La versión final F22 requiere pruebas interactivas en cada plataforma.
- Conexión a Internet para instalar `PySide6==6.10.2`.
- Espacio suficiente para entorno Python y recursos Qt.

## Método 1: instalador de dependencias

1. Extraer el ZIP en una carpeta normal, nunca ejecutar desde dentro del ZIP.
2. Abrir la carpeta `NexoMerc_ERP` (donde está `run.py`).
3. Ejecutar `INSTALAR_DEMO_WINDOWS.bat`.
4. Esperar hasta que muestre instalación completada. Si se produce un error, leer el mensaje de la consola y no continuar hasta corregirlo.
5. Ejecutar `INICIAR_DEMO_WINDOWS.bat`.

El inicio automático crea una **base de datos DEMO aislada** en `data/demo_local/` dentro del directorio de la aplicación y excluida mediante `.gitignore`.

## Método 2: PowerShell (recomendado para diagnosticar)

Abrir PowerShell desde la barra de direcciones de `NexoMerc_ERP` y ejecutar **uno por uno**:

```powershell
py --list
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:NEXOMERC_DATA_DIR = (Join-Path (Get-Location) 'data\demo_local')
.\.venv\Scripts\python.exe run.py
```

Si Python 3.13 no aparece en `py --list` pero sí Python 3.12, cambiar **solo** `py -3.13` por `py -3.12`. No mezclar `.venv` creados con versiones distintas: para cambiar versión se debe recrear ese entorno local.

## Primer acceso

- Al ejecutar por primera vez con base vacía, crear un nombre de usuario y contraseña de administrador a elección; no viene ninguna cuenta incluida.
- Crear productos, proveedores y clientes **ficticios**.
- Abrir caja antes de registrar cobros.
- Probar altas, stock, compra, recepción y una venta ficticia.

## Tests

```powershell
.\.venv\Scripts\python.exe scripts\test_backend.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts\check_publication.py
```

Los tests de interfaz necesitan PySide6. La instalación del paquete no certifica impresoras ni dispositivos reales.

## Dónde quedan los datos

- Inicio mediante `INICIAR_DEMO_WINDOWS.bat`: `data/demo_local/nexomerc.sqlite3` (no subir a GitHub).
- Inicio directo sin configurar variable: `%LOCALAPPDATA%\NexoMercERP\nexomerc.sqlite3` (Windows).
- Fotografías y metadatos locales pueden quedar junto a la base.
- **Nunca borrar bases de producción para reinstalar una demo.**

## Si el programa no abre

Comprobar el intérprete exacto:

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -c "import PySide6; print(PySide6.__version__)"
.\.venv\Scripts\python.exe -c "import nexomerc.ui; print('IMPORT OK')"
.\.venv\Scripts\python.exe run.py
```

Copiar el error de PowerShell para diagnóstico y evitar editar la base o restablecer contraseñas manualmente.
