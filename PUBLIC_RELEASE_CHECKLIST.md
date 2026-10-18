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
- [x] **Suite Qt con QA1 repetida en Windows**: 4/4 tests gráficos y 102/102 pruebas de la suite completa, sin errores (2026-10-18; resultados aportados por el propietario).

Ver `docs/GUI_TEST_QA1.md`.

## Validaciones externas pendientes

- [x] PySide6 ejecutó pruebas Qt en Windows: fallo inicial resuelto en QA1 y suite final 102/102 aprobada.
- [x] Ejecutar todos los tests, incluyendo los módulos Qt: 102/102 (Windows).
- [x] Comprobar inicio GUI y navegación: se verificó inicio de sesión y se capturaron varias pantallas reales. El flujo de alta de primer administrador está cubierto mediante tests; prueba interactiva del alta en una instalación totalmente nueva todavía recomendable.
- [x] Verificación visual del layout/scroll/fotografías del POS en Windows, incluyendo catálogo ampliado y carrito (capturas del propietario).
- [ ] Probar operaciones completas de venta, caja, cupón, stock, recepción y compras.
- [ ] Probar ticketera y lector de códigos, si se publicitan como compatibles con hardware real.
- [ ] Comprobar derechos de uso de logos/capturas e identidad comercial.
- [x] El propietario confirmó expresamente que acepta publicar la DEMO con código funcional antes de integraciones de IA/bots. Revisar compatibilidad legal y licencias antes de uso comercial.

## Resultado

**⚠️ PUBLICADO COMO DEMO, CON OBSERVACIONES**: el propietario confirmó 102/102 pruebas automatizadas en Windows y realizó inspecciones visuales de varias pantallas. Persisten validaciones pendientes: periféricos físicos, flujo integral empresarial, y revisión final de imágenes/licencias. El escáner automatizado no sustituye una auditoría humana integral.

No marcar tareas pendientes como realizadas antes de ejecutarlas.
