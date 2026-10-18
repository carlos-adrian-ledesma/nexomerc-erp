"""F05 centralized interface translations, no business data transformation.

Only translate explicit interface strings; database products, customer names and
identifiers must never be automatically rewritten.
"""
from __future__ import annotations
import json
import re
from pathlib import Path

_content=json.loads(Path(__file__).with_name('translations.json').read_text(encoding='utf-8'))
LANGUAGES=_content['languages']
CATALOG=_content['catalog']


def supported(locale):
 return locale in LANGUAGES


def translate(text,locale):
 if not isinstance(text,str) or locale=='es_AR' or not supported(locale):return text
 if text in CATALOG[locale]:return CATALOG[locale][text]
 # Preserve whitespace around known interface labels (e.g. padded navigation).
 strip=text.strip()
 if strip in CATALOG[locale]:
  return text[:len(text)-len(text.lstrip())]+CATALOG[locale][strip]+text[len(text.rstrip()):]
 # Preserve standard field suffix markers without modifying user-entered text.
 if strip.endswith(' *') and strip[:-2] in CATALOG[locale]:return CATALOG[locale][strip[:-2]]+' *'
 # Currency-labelled form fields are rendered from stable source labels.
 match=re.fullmatch(r'(Costo unitario|Precio venta|Fondo inicial|Efectivo contado|Precio promocional) \(([A-Z]{3})\)',strip)
 if match and match.group(1) in CATALOG[locale]:
  return CATALOG[locale][match.group(1)]+' ('+match.group(2)+')'
 if match and match.group(1)+' $' in CATALOG[locale]:
  return CATALOG[locale][match.group(1)+' $']+' ('+match.group(2)+')'
 # Translate each line of UI explanatory copy only when the whole line matches.
 if '\n' in text:
  lines=text.split('\n');translated=[CATALOG[locale].get(line,line) for line in lines]
  if translated!=lines:return '\n'.join(translated)
 # Keep identifiers, business data and unknown strings intact, not machine-guessed.
 return text


def localize_tree(widget,locale,recursive=True):
 """Localize current window, dialog, controls, headers and static combo items.

 Call after building a screen; call again after switching language. Each original
 string is kept in a Qt property so language switching remains reversible.
 """
 if locale=='es_AR' and not recursive:return
 try:
  from PySide6.QtWidgets import QLabel,QPushButton,QLineEdit,QComboBox,QTableWidget,QTabWidget,QCheckBox,QGroupBox,QDialog,QMainWindow,QTextEdit
 except ImportError:return
 widgets=[widget]+(widget.findChildren(__import__('PySide6').QtWidgets.QWidget) if recursive else [])
 for w in widgets:
  if isinstance(w,(QLabel,QPushButton,QCheckBox,QGroupBox)):
   original=w.property('nx_i18n_text')
   if original is None:original=w.text() if not isinstance(w,QGroupBox) else w.title();w.setProperty('nx_i18n_text',original)
   value=translate(original,locale)
   if isinstance(w,QGroupBox):w.setTitle(value)
   elif w.text()!=value:w.setText(value)
  if isinstance(w,QLineEdit):
   original=w.property('nx_i18n_placeholder')
   if original is None:original=w.placeholderText();w.setProperty('nx_i18n_placeholder',original)
   translated=translate(original,locale)
   if translated!=w.placeholderText():w.setPlaceholderText(translated)
  if isinstance(w,QComboBox):
   original=w.property('nx_i18n_items')
   if original is None:
    original=[w.itemText(i) for i in range(w.count())]
    w.setProperty('nx_i18n_items',original)
   if len(original)==w.count():
    for i,text in enumerate(original):
     trans=translate(text,locale)
     if w.itemText(i)!=trans:w.setItemText(i,trans)
  if isinstance(w,QTableWidget):
   for col in range(w.columnCount()):
    head=w.horizontalHeaderItem(col)
    if head is None:continue
    orig=head.data(257)
    if orig is None:orig=head.text();head.setData(257,orig)
    trans=translate(orig,locale)
    if trans!=head.text():head.setText(trans)
  if isinstance(w,QTabWidget):
   originals=w.property('nx_i18n_tabs')
   if originals is None:originals=[w.tabText(i) for i in range(w.count())];w.setProperty('nx_i18n_tabs',originals)
   if len(originals)==w.count():
    for i,label in enumerate(originals):w.setTabText(i,translate(label,locale))
  if hasattr(w,'toolTip') and w.toolTip():
   orig=w.property('nx_i18n_tooltip')
   if orig is None:orig=w.toolTip();w.setProperty('nx_i18n_tooltip',orig)
   w.setToolTip(translate(orig,locale))
  if isinstance(w,QDialog):
   orig=w.property('nx_i18n_title')
   if orig is None:orig=w.windowTitle();w.setProperty('nx_i18n_title',orig)
   w.setWindowTitle(translate(orig,locale))
