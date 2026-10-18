# 📤 NexoMerc ERP — Publicación del repositorio DEMO público

**Objetivo:** subir el contenido de `NexoMerc_ERP_GITHUB_PORTFOLIO_V2_F22.zip` al repositorio `carlos-adrian-ledesma/nexomerc-erp` como fuente visible de evaluación. **No subir el ZIP privado aquí.**

## A. Validar la DEMO en el equipo

1. Descargá y **extraé** el ZIP público, ingresá a la carpeta interna `NexoMerc_ERP` donde está `run.py`.
2. Ejecutá `INSTALAR_DEMO_WINDOWS.bat`, y después `INICIAR_DEMO_WINDOWS.bat`.
3. Abrí PowerShell desde la barra de direcciones de esa misma carpeta y ejecutá:

```powershell
.\.venv\Scripts\python.exe scripts\test_backend.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts\check_publication.py
```

Si fallan los tests, **corregir antes del push**. Ejecutar además el recorrido del archivo `docs/COMPROBACIONES_ANTES_PUBLICAR.md` (especialmente POS F22 y permisos).

## B. Preparar Git

Instalá Git for Windows solo si el comando `git --version` no existe. Confirmá:

```powershell
git --version
git config --global user.name
git config --global user.email
```

Si falta nombre o correo, configurarlos con tus datos públicos de GitHub. Para privacidad, en GitHub Settings → Emails puede activarse **Keep my email addresses private** y usar el correo `noreply` que **GitHub te asigna**; no inventar esa dirección.

```powershell
git config --global user.name "QuintaDimension Tecnologia"
git config --global user.email "REEMPLAZAR_CON_TU_CORREO_DE_GITHUB"
```

> Sustituí el correo de ejemplo por uno real. No pongas contraseñas, tokens o claves en el comando ni en archivos de este repositorio.

## C. Crear repo público vacío

Abrí https://github.com/new y elegí:

- Owner: `carlos-adrian-ledesma` (si es la cuenta correcta).
- Name: `nexomerc-erp`.
- Description: `Supermarket & Retail ERP | Python · PySide6 · SQLite | Portfolio Demo`.
- Visibility: **Public**.
- No agregar README, `.gitignore` ni licencia desde el formulario (ya existen en el ZIP).

## D. Crear tres commits iniciales desde PowerShell

Situate en la carpeta que contiene `run.py`, NO en Descargas ni dentro del ZIP comprimido.

```powershell
git init -b main
git status --short
```

**Commit 1 — código y verificaciones:**

```powershell
git add .gitignore .gitattributes VERSION.txt requirements.txt run.py nexomerc assets tests scripts .github
git diff --cached --stat
git commit -m "feat: publicar NexoMerc ERP Demo V2-F22 con pruebas backend"
```

**Commit 2 — documentación, funciones y licencia:**

```powershell
git add README.md CHANGELOG.md LICENSE.md docs PUBLIC_RELEASE_CHECKLIST.md SHA256SUMS.txt
git diff --cached --stat
git commit -m "docs: documentar funcionalidades, seguridad e instalacion DEMO"
```

**Commit 3 — inicio local Windows:**

```powershell
git add INSTALAR_DEMO_WINDOWS.bat INICIAR_DEMO_WINDOWS.bat
git diff --cached --stat
git commit -m "chore: facilitar instalacion y arranque DEMO en Windows"
```

Si `git commit` te dice `nothing to commit`, no fuerces un commit vacío: revisá el estado y continuá. No hace falta que los nombres de los commits coincidan exactamente con la versión interna `VERSION.txt`.

## E. Control antes de publicar

```powershell
git status --short
git log --oneline -3
git ls-files | Select-String -Pattern '(\.venv/|__pycache__/|\.sqlite3?$|\.db$|\.env$|reset_admin_password)'
```

El último comando **no debería listar ninguno de esos archivos**. `git status --short` debería quedar sin cambios pendientes. También revisar visualmente el listado en GitHub tras el push.

## F. Vincular y subir GitHub

Este URL funcionará **después de crear** el repositorio bajo la cuenta indicada:

```powershell
git remote add origin https://github.com/carlos-adrian-ledesma/nexomerc-erp.git
git remote -v
git push -u origin main
```

Si GitHub solicita autenticación, usar el navegador/Git Credential Manager de Git for Windows. **Nunca compartir un token personal en el chat ni escribirlo dentro del proyecto.**

Si ya existía el remote `origin`, comprobar con `git remote -v` y actualizarlo solo si apunta al repositorio incorrecto:

```powershell
git remote set-url origin https://github.com/carlos-adrian-ledesma/nexomerc-erp.git
```

## G. Etiqueta de versión y GitHub Release (cuando esté validado)

Solo después de validar el arranque GUI y las funciones básicas:

```powershell
git tag -a demo-v2-f22 -m "NexoMerc ERP Portfolio Demo V2-F22"
git push origin demo-v2-f22
```

Abrí GitHub → repositorio → **Releases → Draft a new release**, seleccioná `demo-v2-f22`, título `NexoMerc ERP · Portfolio Demo V2-F22` y describí características/limitaciones. Es opcional adjuntar el ZIP DEMO como archivo de la release. **No adjuntar el privado.**

## H. Commits de futuras mejoras (NO ejecutarlos sin cambios reales)

**Nuevas capturas reales F22:**

```powershell
git add docs/screenshots README.md
git commit -m "docs: actualizar capturas verificadas del POS F22"
git push
```

**Corrección de funcionamiento:**

```powershell
git add nexomerc tests CHANGELOG.md
git commit -m "fix: corregir comportamiento del POS y agregar pruebas"
git push
```

**Ampliación de idiomas:**

```powershell
git add nexomerc/translations.json nexomerc/locale_ui.py CHANGELOG.md
git commit -m "i18n: ampliar cobertura de traducciones del sistema"
git push
```

**Nuevas pruebas de regresión:**

```powershell
git add tests scripts CHANGELOG.md
git commit -m "test: ampliar pruebas de compras e inventario"
git push
```

GitHub → Settings → General → About: agregar los topics `python`, `pyside6`, `sqlite`, `erp`, `point-of-sale`, `inventory-management`, `retail`, `desktop-app`, `supermarket`.

## I. Recordatorios

- GitHub **Public** significa que cualquiera puede leer/clonar el código; una licencia restrictiva solo establece límites legales de reutilización.
- Esta edición no ofrece facturación fiscal homologada, IA, bots ni multi-PC por red.
- No crear cuentas DEMO con passwords fijos publicadas en README.
- Bases, clientes y fotografías creados en ejecución **no deben formar parte de Git**.
- Si el sistema ya guardaba datos en `%LOCALAPPDATA%`, ejecutar `INICIAR_DEMO_WINDOWS.bat` para mantener la base DEMO aislada.
