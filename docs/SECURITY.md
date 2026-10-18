# Seguridad y límites

- Las contraseñas se derivan con PBKDF2-HMAC-SHA256, 310 000 iteraciones, salt aleatorio individual (16 bytes aleatorios codificados en hexadecimal).
- La autenticación compara valores derivados con `hmac.compare_digest`; implementa bloqueo temporal de 15 minutos luego de cinco intentos erróneos por cuenta.
- El administrador inicial se crea en una base nueva y no existe una contraseña predeterminada.
- El control de acceso por roles opera en el motor SQLite; existen permisos individuales y restricciones de sucursal.
- La auditoría usa hashes encadenados para detectar manipulaciones accidentales; no es un registro inmutable frente a administradores con acceso al archivo físico.
- SQLite y fotografías son locales: el sistema **no cifra automáticamente la base completa**. Proteger carpetas, copias, dispositivos y accesos al sistema operativo.
- No expongas la carpeta de datos por Internet sin infraestructura de autenticación adicional.
- Los comprobantes imprimibles son **internos y NO fiscales**; no reemplazan facturación fiscal homologada.

## Reporte de vulnerabilidades

No incluyas tokens o bases reales en issues públicos. Contactar privadamente a los responsables del proyecto antes de publicar hallazgos sensibles.
