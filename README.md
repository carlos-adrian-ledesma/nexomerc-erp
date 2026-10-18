# 🛒 NexoMerc ERP — Edición DEMO de portafolio

**Gestión para supermercados y comercios minoristas · QuintaDimensión Tecnología**

![Identidad NexoMerc ERP](assets/branding/banner_tienda_naranja.png)

[![Pruebas del motor (sin GUI)](https://github.com/carlos-adrian-ledesma/nexomerc-erp/actions/workflows/backend-tests.yml/badge.svg)](https://github.com/carlos-adrian-ledesma/nexomerc-erp/actions/workflows/backend-tests.yml)

`Python` · `PySide6` · `SQLite` · `Windows` · `Desktop ERP` · `POS` · `Inventario` · `Comercio minorista`

NexoMerc ERP es una aplicación de escritorio orientada a centralizar la gestión comercial: **productos, stock, compras, recepción, proveedores, ventas, caja, clientes, sucursales, permisos, reportes y auditoría**. Incluye una interfaz visual en tonos naranja/gris y utiliza una base de datos SQLite local.

> **Alcance:** repositorio de portafolio con código de demostración para evaluación no comercial. No ofrece sincronización multi-PC/Internet ni IA/bots; los tickets son comprobantes **internos, NO FISCALES**. No se declara aptitud para producción sin validación funcional y normativa.

## 📌 Funcionalidades principales

| Área | Capacidades incluidas en el código de esta revisión |
| --- | --- |
| **Panel principal** | Indicadores de ventas diarias/mensuales, alertas de stock, órdenes pendientes y actividad reciente. |
| **Productos** | SKU, código de barras, fotografías, categorías, marcas, proveedor, costo/precio, presentación y archivo/restauración de productos. |
| **Inventario** | Existencia y disponible por sucursal, stock mínimo/máximo, entradas, ajustes, conteo físico, reservas y Kardex. |
| **Recepción** | Recepción manual por unidad base, paquete o caja; factor de conversión, referencia/remito, vencimiento y registro de movimientos. |
| **Compras** | Órdenes de compra, aprobación/envío, recepción de pedidos y actualización transaccional de stock. |
| **Proveedores** | Datos comerciales y vinculación a compras/productos. |
| **Ventas y POS** | Catálogo visual, lector tipo teclado para códigos de barras, carrito, control de disponibilidad, medios de pago, caja y anulaciones. |
| **Caja** | Apertura, cierre, arqueo y consulta de ventas recientes. |
| **Clientes y promociones** | Fichas de clientes, historial de compras, precios promocionales, reglas/cupones de fidelización. |
| **Sucursales** | Gestión de sucursales y traslados de mercancía con salida y recepción. |
| **Usuarios y permisos** | Administrador inicial, roles predefinidos, permisos granulares y restricciones por sucursal. |
| **Reportes** | Ventas, productos y reportes operativos; exportación CSV. |
| **Auditoría** | Histórico de operaciones, cadena de hashes y exportación CSV. |
| **Configuración** | Identidad comercial, moneda/localización, preferencias e impresión de tickets internos. |

La explicación técnica y funcional, los límites y cada operación están en [**docs/FUNCIONALIDADES.md**](docs/FUNCIONALIDADES.md).

## 🖼️ Galería visual — NexoMerc ERP

Las siguientes son **composiciones de presentación 1080 × 1080** elaboradas a partir de capturas de NexoMerc ERP tomadas durante las pruebas de Windows del 18 de octubre de 2026. Se utilizan para **portafolio comercial**; las composiciones pueden tener ajustes gráficos y no sustituyen las capturas originales de la interfaz.

| Panel principal | Productos y stock |
| :---: | :---: |
| ![Panel principal y actividad de NexoMerc](docs/github-images/01_panel_principal.png) | ![Catálogo, productos y existencias](docs/github-images/02_productos_y_stock.png) |

| Categorías y marcas | Recepción de mercadería |
| :---: | :---: |
| ![Administración de categorías y marcas](docs/github-images/03_categorias_y_marcas.png) | ![Recepción de mercadería](docs/github-images/04_recepcion_de_mercaderia.png) |

| Compras y proveedores | Ventas, caja y POS |
| :---: | :---: |
| ![Compras y proveedores](docs/github-images/05_compras_y_proveedores.png) | ![Punto de venta con catálogo visual](docs/github-images/06_ventas_caja_y_pos.png) |

| POS visual ampliado | Caja en operación |
| :---: | :---: |
| ![Diseño de catálogo y carrito ampliado](docs/github-images/07_pos_visual.png) | ![Venta en curso con artículos en carrito](docs/github-images/08_caja_en_operacion.png) |

| Clientes | Usuarios y configuración |
| :---: | :---: |
| ![Gestión de clientes](docs/github-images/09_clientes.png) | ![Usuarios, permisos y configuración](docs/github-images/10_usuarios_permisos_y_configuracion.png) |

**Capturas originales históricas:** se conservan en [`docs/screenshots/`](docs/screenshots/) como referencia F03, no como representación visual de la revisión actual. Algunas imágenes de presentación contienen datos ficticios o de prueba; revisarlos antes de redistribuir.

## 🖥️ Instalación rápida — Windows 10/11 (64 bits)

- **Python 3.13 de 64 bits recomendado para esta entrega**. Python 3.12 también es una opción. En Windows, con Python 3.13 y PySide6, se ejecutaron satisfactoriamente las 102 pruebas de la suite QA1; esta validación no equivale a certificar hardware ni uso productivo.
- Dependencia de interfaz: `PySide6==6.10.2`.
- Git opcional para clonar; no es necesario para ejecutar el ZIP.

**Opción sencilla:** ejecutar `INSTALAR_DEMO_WINDOWS.bat` y después `INICIAR_DEMO_WINDOWS.bat` (consola visible para detectar errores).

**Opción PowerShell:**

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:NEXOMERC_DATA_DIR = (Join-Path (Get-Location) 'data\demo_local')
.\.venv\Scripts\python.exe run.py
```

Al abrir una base nueva, la aplicación solicita crear un **administrador propio**. No hay contraseña fija ni cuenta preconfigurada. Usar exclusivamente datos ficticios. `data/demo_local/` está ignorada por Git.

Instrucciones ampliadas: [**docs/INSTALACION_WINDOWS.md**](docs/INSTALACION_WINDOWS.md) · [**docs/DEMO.md**](docs/DEMO.md).

## 🧪 Pruebas

Sin abrir Qt, se puede ejecutar la batería de lógica de negocio:

```powershell
.\.venv\Scripts\python.exe scripts\test_backend.py
```

En un equipo con PySide6 instalado, ejecutar la batería total:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Para revisar archivos sensibles antes de subir a GitHub:

```powershell
.\.venv\Scripts\python.exe scripts\check_publication.py
```

Las pruebas no sustituyen una inspección visual completa ni la validación de impresoras o lectores físicos. Ver [**PUBLIC_RELEASE_CHECKLIST.md**](PUBLIC_RELEASE_CHECKLIST.md).

## 🔐 Seguridad, datos y alcance

- Autenticación con **PBKDF2-HMAC-SHA256**, salt individual y 310.000 iteraciones. No incluye claves maestras.
- Control de acceso por rol/módulo y restricciones de sucursal en el motor.
- Base SQLite creada fuera del código; con la variable `NEXOMERC_DATA_DIR` se puede aislar un entorno DEMO.
- Los datos almacenados en SQLite **no están cifrados completamente**. No se deben cargar datos sensibles reales en la demostración pública.
- El software no es un sistema de facturación fiscal homologado.
- No se incluyen APIs de IA, bots, sincronización por LAN/Internet, ni licencias comerciales transferibles.

[Arquitectura](docs/ARCHITECTURE.md) · [Seguridad](docs/SECURITY.md) · [Base de datos](docs/DATABASE.md) · [Licencia](LICENSE.md)

## 📂 Estructura

```text
NexoMerc_ERP/
├── nexomerc/                  # Núcleo, GUI, traducciones y lógica comercial
├── assets/                    # Iconos, identidad y recursos de la aplicación
├── docs/                      # Capturas y manuales técnicos/funcionales
├── tests/                     # Pruebas de regresión
├── scripts/                   # Validación del motor y control de publicación
├── .github/workflows/         # CI de pruebas de lógica sin Qt
├── run.py                     # Entrada principal
├── INSTALAR_DEMO_WINDOWS.bat  # Crea .venv e instala requisitos
├── INICIAR_DEMO_WINDOWS.bat   # Arranca con datos DEMO aislados
├── requirements.txt
├── PUBLIC_RELEASE_CHECKLIST.md
├── CHANGELOG.md
└── LICENSE.md
```

## 🏷️ Estado y versiones

**Revisión de interfaz/código recibido:** V2-F22. El archivo `VERSION.txt` conserva `2.0.14` por compatibilidad histórica con pruebas y scripts antiguos; no representa el número visual F22. La suite QA1 se ejecutó con 102/102 pruebas aprobadas en Windows y se revisaron visualmente pantallas principales. La validación de periféricos y escenarios empresariales completos permanece pendiente.

## 🧑‍💻 Autoría y contacto

**QuintaDimensión Tecnología** · [GitHub: carlos-adrian-ledesma](https://github.com/carlos-adrian-ledesma).

Para solicitar personalizaciones, implementación empresarial o una licencia comercial, utilizar los canales públicos indicados en el perfil de GitHub. No publicar claves, contraseñas ni datos de clientes en Issues.

## 📜 Licencia

**Código disponible para evaluación no comercial, no open source.** Ver [LICENSE.md](LICENSE.md). El hecho de poder leer y clonar el repositorio no concede permiso para revender el producto ni utilizar su código en un sistema comercial sin autorización.
