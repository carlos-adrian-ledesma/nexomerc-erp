# Public release checklist — NexoMerc ERP Demo V2-F22

Fecha de empaquetado: 2026-10-18.

## Comprobaciones automatizadas

- [x] Fuentes, iconos, traducciones, pantallas F03 etiquetadas, scripts y documentación presentes.
- [x] Se excluyó del ZIP público la herramienta privada `reset_admin_password.py`.
- [x] No se empaquetaron `.venv`, SQLite, registros reales ni respaldos.
- [x] `scripts/check_publication.py` ejecutado sobre el paquete público: **sin coincidencias críticas detectadas**.
- [x] Compilación sintáctica de Python (backend, UI y scripts).
- [x] Suite de pruebas no gráficas: **96/96**, sin errores.
- [x] Inicialización de base temporal SQLite, `Casa central`, alta de admin, login válido/inválido e integridad `ok` verificados con tests.
- [x] ZIP abierto y verificado después de su generación.

## Incidencia GUI detectada en Windows y corrección QA1

- [x] En Windows, el usuario ejecutó 96/96 pruebas no gráficas correctamente.
- [x] Suite Qt inicial: 102 pruebas, **1 error** (`RetailTable already deleted` en el test de 60 ciclos).
- [x] Test de UI actualizado para esperar recargas y comprobar la validez del widget (sin alterar lógica del ERP).
- [ ] **Repetir suite Qt con QA1** en Windows y verificar que el error haya desaparecido.

Ver `docs/GUI_TEST_QA1.md`.

## Validaciones externas pendientes

- [x] PySide6 ejecutó pruebas Qt en Windows (resultado inicial: 1 error; pendiente repetición QA1).
- [ ] Ejecutar todos los tests, incluyendo los módulos Qt.
- [ ] Comprobar inicio GUI, asistente de administrador y navegación real.
- [ ] Confirmar el layout/scroll/fotografías F22 del POS.
- [ ] Probar operaciones completas de venta, caja, cupón, stock, recepción y compras.
- [ ] Probar ticketera y lector de códigos, si se publicitan como compatibles con hardware real.
- [ ] Comprobar derechos de uso de logos/capturas e identidad comercial.
- [ ] Confirmar conscientemente que se autoriza publicar este código funcional con licencia no comercial.

## Resultado

**⚠️ LISTO PARA GITHUB CON OBSERVACIONES**: paquete publicable desde el punto de vista de empaquetado y pruebas backend. La validación GUI Windows permanece pendiente. El escáner automatizado no sustituye una auditoría humana integral.

No marcar tareas pendientes como realizadas antes de ejecutarlas.
