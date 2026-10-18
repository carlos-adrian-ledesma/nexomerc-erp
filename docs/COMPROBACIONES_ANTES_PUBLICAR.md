# Control manual antes de publicar el repositorio

La entrega del ZIP se prepara en un entorno Linux sin PySide6 instalada. Superar la batería no gráfica **no equivale** a aprobar la GUI en Windows. Completar esta lista en el equipo del propietario.

- [ ] Instalar dependencias con `INSTALAR_DEMO_WINDOWS.bat` o mediante PowerShell.
- [ ] Ejecutar `scripts/test_backend.py` y confirmar todos los casos aprobados.
- [ ] Ejecutar `python -m unittest discover -s tests -v` con la `.venv` activa y PySide6 instalado.
- [ ] Ejecutar `scripts/check_publication.py` y revisar resultados.
- [ ] Crear administrador nuevo en `data/demo_local` sin tocar datos reales.
- [ ] Verificar panel, búsqueda, idioma y acciones de navegación.
- [ ] Crear productos, adjuntar foto genérica, modificar y archivar/restaurar.
- [ ] Registrar stock, paquete/caja, conteo físico y movimientos.
- [ ] Probar orden de compra, recepción y remito.
- [ ] Probar apertura de caja, venta ficticia, anulación, ticket interno y cierre.
- [ ] Verificar splitter y scroll horizontal POS F22, incluida la escala de fotografías.
- [ ] Validar clientes, promociones/cupones y permisos.
- [ ] Inspeccionar el estado de la ventana, textos y traducciones.
- [ ] Verificar que `.venv`, `data`, fotos y bases no aparezcan en `git status --short` ni `git ls-files`.
- [ ] Revisar licencia y derechos de uso de fotografías/marcas de la presentación.
- [ ] Confirmar que el repositorio DEMO sea **Public** y el FULL sea **Private** (repositorios distintos).

No marcar como completado un control que no haya sido efectuado.
