# QA1 — Sincronización de pruebas de interfaz (Windows)

## Incidencia observada

En Windows / PySide6 6.10.2, la ejecución de `python -m unittest discover -s tests -v` produjo un `RuntimeError: Internal C++ object (RetailTable) already deleted` en `test_twenty_edit_cycles` (102 pruebas, 1 error). Las 96 pruebas del backend y la inspección estática de archivos aprobaron.

## Hipótesis técnica

El test conservaba una referencia local a una tabla Qt durante una espera fija de 20 ms. La edición de productos recarga la página mediante `QTimer.singleShot(0, ...)`, por lo que la tabla anterior puede ser destruida antes de que el test vuelva a usarla. El fallo no demuestra por sí solo un defecto del POS ni de SQLite.

## Cambio QA1

Se ha actualizado solamente `tests/test_retail_ui.py`:

- Esperar a que terminen las recargas pendientes antes de utilizar la tabla.
- Comprobar la validez del objeto Qt con `shiboken6.isValid`.
- No conservar la tabla a través de esperas durante las cuales puede ser reemplazada.
- Mantener **los 60 ciclos reales** de edición/cancelación y verificar que los valores persistidos son los esperados.
- Fallar con un mensaje descriptivo si la UI no se estabiliza, sin omitir pruebas ni silenciar excepciones.

**No se modificó el código de la aplicación ni la base de datos.**

## Comprobar en Windows (dentro de NexoMerc_ERP)

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_retail_ui.py -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts\check_publication.py
```

En el entorno de empaquetado no estaba instalado PySide6. **Posteriormente el propietario ejecutó la corrección en Windows (18/10/2026): 4/4 pruebas gráficas aprobadas en dos ejecuciones y 102/102 pruebas de la suite completa aprobadas**. El control estático de publicación también finalizó correctamente. Esto valida las pruebas automatizadas ejecutadas, no el funcionamiento de cada periférico físico ni la totalidad de escenarios empresariales.
