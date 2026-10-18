"""PySide6 desktop UI for NexoMerc ERP. 16 views / 15 secured modules + login."""
from __future__ import annotations
import csv
import html
import json
import logging
import sqlite3
from datetime import date,timedelta
from pathlib import Path
from PySide6.QtCore import Qt, QSize, QTimer, Signal, QLocale
from PySide6.QtGui import QIcon,QPixmap,QFont,QKeySequence,QShortcut,QTextDocument
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QFormLayout,
 QLabel,QPushButton,QLineEdit,QComboBox,QCheckBox,QDialog,QDialogButtonBox,QTableWidget,QTableWidgetItem,
 QMessageBox,QFrame,QFileDialog,QScrollArea,QDoubleSpinBox,QSpinBox,QTextEdit,QHeaderView,QAbstractItemView,
 QStackedWidget,QSplitter,QTabWidget,QSizePolicy,QMenu)
from .core import ERP,ERPError,PermissionDenied,ROLE_PERMS,quantity,money as _money,cents,milli,total_for
from .locale_ui import LANGUAGES,translate as tr,supported as locale_supported,localize_tree
from .currency import COUNTRIES,CURRENCY_NAMES,for_country,valid_currency,price_label

def money(value):
 from decimal import Decimal
 return f'{Decimal(int(value))/100:,.2f}'.replace(',','_').replace('.',',').replace('_','.')

PRIMARY='#F47717'; ORANGE='#F66B20'; RED='#DC5138'; PALE='#FFF0D9'
_ACTIVE_CURRENCY='ARS'
def app_money(amount):return price_label(money(amount),_ACTIVE_CURRENCY)
STYLE="""
* {font-family:'Segoe UI','Arial';font-size:13px;color:#2B3035;}
QMainWindow,QWidget {background:#F4F5F7;color:#303843;}
QFrame#sidebar {background:#242B33;}
QFrame#sidebar QLabel {background:transparent;color:#FAFBFC;}
QFrame#sidebar QPushButton {text-align:left;background:transparent;border:0;color:#DCE1E5;padding:10px 14px;border-radius:9px;font-weight:500;min-height:19px;}
QFrame#sidebar QPushButton:hover {background:#434B54;color:white;}
QFrame#sidebar QPushButton[active='true'] {background:#FF7625;color:white;font-weight:800;border-left:4px solid #FFC185;}
QFrame#white,QFrame#kpi,QFrame#box,QFrame#info {background:#FFFFFF;border:1px solid #E0E3E7;border-radius:13px;}
QFrame#banner {background:#FFFFFF;border:1px solid #EBEBEA;border-radius:18px;}
QFrame#pospanel {background:#FFF9F4;border:1px solid #F9E3D5;border-radius:13px;}
QLabel#heading {font-size:27px;font-weight:800;color:#202832;background:transparent;}
QLabel#subheading {font-size:12px;color:#64717D;background:transparent;}
QLabel#helper {font-size:12px;color:#697781;background:transparent;}
QLabel#kpi_value {font-size:23px;font-weight:800;color:#EB6421;background:transparent;}
QLabel#kpi_title {font-size:12px;color:#66727D;background:transparent;}
QPushButton {background:white;color:#39414A;border:1px solid #DADEE2;padding:10px 13px;border-radius:8px;font-weight:600;}
QPushButton:hover {background:#FFF3EB;border:1px solid #FF8B40;}
QPushButton:disabled {color:#AAB1B8;background:#F2F2F3;}
QPushButton#primary {background:#F66B20;color:white;border:1px solid #F66B20;font-weight:800;}
QPushButton#primary:hover {background:#E85812;border-color:#E85812;}
QPushButton#danger {background:#FFF2EF;color:#BD3B31;border-color:#F7CAC4;}
QLineEdit,QComboBox,QSpinBox,QDoubleSpinBox,QTextEdit {background:#FFFFFF;border:1px solid #D7DDE3;border-radius:8px;padding:8px;color:#26333B;selection-background-color:#F66B20;min-height:18px;}
QLineEdit:focus,QComboBox:focus,QDoubleSpinBox:focus,QTextEdit:focus {border:2px solid #F66B20;}
QTableWidget {background:#FFFFFF;alternate-background-color:#FAFAFB;border:1px solid #E2E4E8;border-radius:10px;gridline-color:#F0F2F3;selection-background-color:#FFE2CF;selection-color:#303843;}
QHeaderView::section {background:#F2F3F5;border:0;border-bottom:1px solid #E3E6EB;padding:11px 7px;color:#4D5660;font-weight:bold;}
QScrollArea {border:0;background:transparent;}
QTabWidget::pane {border:1px solid #DDE1E5;border-radius:10px;background:white;}
QTabBar::tab {padding:11px 19px;background:#EAEDEF;}
QTabBar::tab:selected {background:#F66B20;color:white;}
QToolTip {background:#333B43;color:white;border:1px solid #333B43;padding:7px;}
"""
HELP={
'dashboard':('Resumen del negocio','Consultá ventas, alertas y actividad reciente de todas tus operaciones.'),
'products':('Catálogo comercial','Creá, editá y organizá productos, precios, categorías y fotografías.'),
'catalog':('Organización del catálogo','Administrá categorías, subcategorías y marcas; luego asignálas en Productos.'),
'inventory':('Stock y trazabilidad','Compará existencias, registrá conteos, gestioná reservas y consultá movimientos.'),
'receipts':('Ingreso de mercadería','Compará lo solicitado al proveedor con lo recibido: al confirmar se actualiza el stock.'),
'purchases':('Compras y abastecimiento','Prepará órdenes, envialas al proveedor y hacé seguimiento de entregas.'),
'suppliers':('Red de proveedores','Guardá los datos de contacto y la identificación fiscal de cada proveedor.'),
'pos':('Punto de venta rápido','Escaneá códigos de barras, armá el carrito y registrá cobros con caja abierta.'),
'customers':('Relación con clientes','Consultá datos y movimientos de compradores registrados.'),
'branches':('Sucursales y traslados','Gestioná locales y transferencias de mercadería de origen a destino.'),
'users':('Accesos controlados','Definí quién puede entrar y qué operaciones puede ejecutar.'),
'reports':('Indicadores comerciales','Analizá resultados por fechas, productos y formas de pago.'),
'promotions':('Ofertas y campañas','Creá precios especiales con fechas de vigencia.'),
'audit':('Historial de operaciones','Verificá quién realizó cada acción y cuándo ocurrió.'),
'settings':('Preferencias del comercio','Modificá el nombre, moneda, datos fiscales y datos del comprobante interno.'),
}
ACTION_HELP={
'Carga inicial':'Registrá el stock existente al empezar a usar NexoMerc.',
'Ajustar stock':'Sumá o restá unidades ante diferencias documentadas.',
'Conteo físico':'Compara unidades reales con las que informa el sistema.',
'Reservar':'Aparta existencias sin descontarlas como venta.',
'Liberar reserva':'Devuelve a disponible lo que se había apartado.',
'Kardex / movimientos':'Consulta entradas, salidas y ajustes anteriores.'
}
MENU=[('dashboard','Panel principal'),('products','Productos y stock'),('catalog','Categorías y marcas'),('receipts','Recepción de mercadería'),('purchases','Compras y proveedores'),('pos','Ventas, caja y POS'),('customers','Clientes'),('branches','Sucursales y transferencias'),('users','Usuarios y permisos'),('reports','Reportes y estadísticas'),('promotions','Promociones y precios'),('audit','Auditoría e historial'),('settings','Configuración general')]
TITLES=dict(MENU)
TITLES['suppliers']='Proveedores'  # Keep security matrix and permission labels complete.

class QuantitySpinBox(QDoubleSpinBox):
 """Store numeric quantities unchanged; show only meaningful decimal places."""
 def __init__(self):
  super().__init__();self.setLocale(QLocale('es_AR'));self.setDecimals(3);self.setGroupSeparatorShown(False)
 def textFromValue(self,value):
  return f'{value:.3f}'.rstrip('0').rstrip('.').replace('.',',')
 def valueFromText(self,text):
  value,ok=self.locale().toDouble(text.strip())
  return value if ok else 0.0

ASSETS=Path(__file__).resolve().parent.parent/'assets'
def shop_icon():
 path=ASSETS/'branding'/('nexomerc.ico' if __import__('sys').platform=='win32' else 'nexomerc_f04_icon.png')
 return QIcon(str(path))

class Form(QDialog):
 def __init__(self,parent,title,fields):
  super().__init__(parent)
  self.setWindowIcon(shop_icon());self.setWindowTitle(title+' · NexoMerc ERP');self.setMinimumWidth(540);self.resize(700,640)
  self.widgets={};self.image_path=''
  layout=QVBoxLayout(self);layout.setContentsMargins(24,20,24,18);layout.setSpacing(12)
  h=QLabel(title);h.setObjectName('heading');layout.addWidget(h)
  sub=QLabel('Completá la información y verificá los datos antes de guardar. Los campos con * son obligatorios.')
  sub.setObjectName('helper');sub.setWordWrap(True);layout.addWidget(sub)
  scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setMinimumHeight(140)
  contents=QWidget();box=QFormLayout(contents);box.setContentsMargins(6,6,16,12);box.setSpacing(14)
  helps={
   'sku':'Identificador único para búsquedas y control interno.',
   'barcode':'Usá un lector USB (modo teclado) o escribí el código manualmente.',
   'category_id':'Seleccioná una categoría creada en la pestaña Categorías y marcas.',
   'unit':'Ejemplos: u, kg, l, paquete. Elegí una unidad consistente.',
   'minimum':'Alerta cuando el stock disponible se encuentre por debajo del mínimo.',
   'maximum':'Referencia de almacenamiento; no agrega mercadería automáticamente.',
   'photo_upload':'Imagen JPG o PNG, preferiblemente cuadrada de 1080 × 1080 px; máximo 5 MB.',
  }
  for key,label,kind,value,opts in fields:
   if kind=='choice':
    w=QComboBox()
    for name,data in (opts or []):w.addItem(str(name),data)
    idx=w.findData(value)
    if idx>=0:w.setCurrentIndex(idx)
   elif kind=='bool':w=QCheckBox();w.setChecked(bool(value))
   elif kind=='long':w=QTextEdit();w.setPlainText(str(value or ''));w.setFixedHeight(85)
   elif kind=='money' or kind=='qty':
    w=QDoubleSpinBox() if kind=='money' else QuantitySpinBox();w.setLocale(QLocale('es_AR'));w.setDecimals(2 if kind=='money' else 3);w.setMaximum(999999999);w.setValue(float(value or 0));w.setMinimum(0)
   elif kind=='integer':w=QSpinBox();w.setMaximum(999999999);w.setValue(int(value or 0))
   elif kind=='image':
    w=QWidget();column=QVBoxLayout(w);column.setContentsMargins(0,0,0,0)
    self.photo_preview=QLabel('Sin fotografía\n1080 × 1080 recomendado')
    self.photo_preview.setAlignment(Qt.AlignmentFlag.AlignCenter);self.photo_preview.setFixedSize(148,148)
    self.photo_preview.setStyleSheet('background:#FFF6EE;border:1px dashed #F5A167;border-radius:10px;color:#965833;')
    column.addWidget(self.photo_preview)
    browse=QPushButton('📷  Elegir foto del producto');browse.clicked.connect(self.choose_photo)
    column.addWidget(browse);w.setMinimumHeight(200)
   else:w=QLineEdit(str(value or ''));w.setPlaceholderText(label)
   self.widgets[key]=(w,kind)
   block=QWidget();bl=QVBoxLayout(block);bl.setContentsMargins(0,0,0,0);bl.setSpacing(4);bl.addWidget(w)
   if key in helps:
    hint=QLabel(helps[key]);hint.setObjectName('helper');hint.setWordWrap(True);bl.addWidget(hint)
   box.addRow(label,block)
  scroll.setWidget(contents);layout.addWidget(scroll,1)
  btn=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
  btn.button(QDialogButtonBox.StandardButton.Ok).setText('Guardar / Confirmar')
  btn.button(QDialogButtonBox.StandardButton.Ok).setObjectName('primary')
  btn.button(QDialogButtonBox.StandardButton.Cancel).setText('Cancelar')
  btn.accepted.connect(self.accept);btn.rejected.connect(self.reject);layout.addWidget(btn)
 def showEvent(self,event):
  super().showEvent(event)
  parent=self.parentWidget()
  lang=getattr(parent,'language','es_AR')
  localize_tree(self,lang)
 def choose_photo(self):
  path,_=QFileDialog.getOpenFileName(self,'Elegir fotografía cuadrada','','Imágenes (*.png *.jpg *.jpeg)')
  if not path:return
  from pathlib import Path
  raw=Path(path).read_bytes()
  if len(raw)>5*1024*1024 or not (raw.startswith(b'\x89PNG\r\n\x1a\n') or raw.startswith(b'\xff\xd8\xff')):
   QMessageBox.warning(self,'Fotografía incompatible','Seleccioná una imagen JPG o PNG válida de menos de 5 MB.');return
  pix=QPixmap(path)
  if pix.isNull():QMessageBox.warning(self,'Imagen no válida','No se pudo abrir la imagen seleccionada.');return
  self.image_path=path
  self.photo_preview.setPixmap(pix.scaled(140,140,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
 def data(self):
  result={}
  for key,(w,kind) in self.widgets.items():
   if kind=='choice':v=w.currentData()
   elif kind=='bool':v=w.isChecked()
   elif kind=='long':v=w.toPlainText().strip()
   elif kind in ('money','qty','integer'):v=w.value()
   elif kind=='image':v=self.image_path
   else:v=w.text().strip()
   result[key]=v
  return result

class InventoryStockDialog(QDialog):
 """Guarded inventory entry: initial quantity, signed correction or absolute count.

 A count SETS onhand; an adjustment ADDS/SUBTRACTS; neither changes the
 minimum stock threshold, which remains a product-level alert setting.
 """
 def __init__(self,parent,info,mode):
  super().__init__(parent)
  self.setWindowIcon(shop_icon())
  self.mode=mode
  titles={'initial':'Registrar existencias iniciales','adjust':'Ajustar existencias','count':'Registrar conteo físico'}
  self.setWindowTitle(titles[mode]+' · NexoMerc ERP')
  self.setMinimumWidth(500);self.resize(610,510)
  layout=QVBoxLayout(self);layout.setContentsMargins(23,18,23,18);layout.setSpacing(11)
  title=QLabel(titles[mode]);title.setObjectName('heading');layout.addWidget(title)
  detail={
   'initial':'Cargá las unidades que ya tenías antes de utilizar el programa. Solo puede hacerse una vez por producto y sucursal.',
   'adjust':'Sumá o restá unidades para corregir una diferencia. No modifica el stock mínimo ni registra una venta.',
   'count':'Ingresá el TOTAL que contaste físicamente, no la diferencia. El programa ajustará las existencias a ese total.',
  }
  desc=QLabel(detail[mode]);desc.setWordWrap(True);desc.setObjectName('helper');layout.addWidget(desc)
  context=QFrame();context.setObjectName('info');grid=QGridLayout(context)
  grid.setContentsMargins(12,12,12,12);grid.setSpacing(7)
  fields=[('Producto:',info['name']),('Sucursal:',info['branch']),('Existencias actuales:',quantity(info['onhand_milli'])+' '+info.get('unit','u')),('Reservadas:',quantity(info['reserved_milli'])+' '+info.get('unit','u')),('Disponibles:',quantity(info['available_milli'])+' '+info.get('unit','u'))]
  for i,(name,val) in enumerate(fields):
   k=QLabel(name);k.setObjectName('kpi_title');v=QLabel(str(val))
   grid.addWidget(k,i,0);grid.addWidget(v,i,1)
  layout.addWidget(context)
  form=QFormLayout();form.setSpacing(10)
  self.qty=QuantitySpinBox();self.qty.setRange(0 if mode=='count' else 0.001,999999999)
  self.qty.setValue((info['onhand_milli']/1000) if mode=='count' else 1)
  self.qty.setToolTip('Ingresá la cantidad en '+info.get('unit','u')+'. Por ejemplo 0,250 kg = 250 gramos. Para productos por peso se permiten tres decimales.')
  form.addRow(('Total contado *' if mode=='count' else 'Existencias iniciales *' if mode=='initial' else 'Cantidad a corregir *')+' ('+info.get('unit','u')+')',self.qty)
  self.direction=None
  if mode=='adjust':
   self.direction=QComboBox();self.direction.addItem('Sumar · sobrante / ingreso','+')
   self.direction.addItem('Restar · faltante / rotura','-')
   form.addRow('Tipo de ajuste *',self.direction)
  self.reason=QTextEdit();self.reason.setFixedHeight(66)
  self.reason.setPlaceholderText('Ejemplo: conteo inicial de depósito, vencimiento, faltante en góndola…')
  form.addRow('Motivo *',self.reason)
  layout.addLayout(form)
  self.preview=QLabel();self.preview.setWordWrap(True);self.preview.setObjectName('helper')
  self.preview.setStyleSheet('font-size:13px;font-weight:750;color:#371408;padding:7px;')
  layout.addWidget(self.preview)
  self.qty.valueChanged.connect(self.update_preview)
  if self.direction is not None:self.direction.currentIndexChanged.connect(self.update_preview)
  self._onhand=info['onhand_milli'];self._reserved=info['reserved_milli']
  self.update_preview()
  self.buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
  ok=self.buttons.button(QDialogButtonBox.StandardButton.Ok);ok.setObjectName('primary');ok.setText('Confirmar movimiento')
  self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setText('Cancelar')
  self.buttons.accepted.connect(self.accept);self.buttons.rejected.connect(self.reject)
  layout.addWidget(self.buttons)
 def calculated(self):
  milli_qty=round(self.qty.value()*1000)
  if self.mode=='initial':return self._onhand+milli_qty
  if self.mode=='count':return milli_qty
  return self._onhand+(milli_qty if self.direction.currentData()=='+' else -milli_qty)
 def update_preview(self,*unused):
  after=self.calculated() if hasattr(self,'_onhand') else 0
  before=getattr(self,'_onhand',0)
  if self.mode=='count':text=f'Antes: {quantity(before)}  →  Después: {quantity(after)}  ·  Diferencia: {quantity(after-before)}'
  elif self.mode=='initial':text=f'Nueva existencia: {quantity(after)} unidades. Cada venta confirmada restará automáticamente.'
  else:text=f'Antes: {quantity(before)}  →  Después: {quantity(after)}  ·  Diferencia: {quantity(after-before)}'
  if after<getattr(self,'_reserved',0):text+='  ·  ERROR: el total sería menor que las reservas.'
  self.preview.setText(text)
 def accept(self):
  if not self.reason.toPlainText().strip():
   QMessageBox.warning(self,'Motivo obligatorio','Escribí el motivo para dejar trazabilidad.');return
  if self.mode!='count' and self.qty.value()<=0:
   QMessageBox.warning(self,'Cantidad inválida','La cantidad debe ser mayor que cero.');return
  if self.calculated()<self._reserved:
   QMessageBox.warning(self,'Reservas existentes','El stock resultante no puede ser menor que las unidades reservadas.');return
  super().accept()
 def data(self):
  if self.exec()!=QDialog.DialogCode.Accepted:return None
  return {'qty':self.qty.value(),'direction':self.direction.currentData() if self.direction else None,'notes':self.reason.toPlainText().strip()}

class GoodsArrivalDialog(QDialog):
 """Record deliveries independently of purchase orders, with optional expiry."""
 def __init__(self,parent,product,branch_id=None):
  super().__init__(parent)
  self.setWindowIcon(shop_icon());self.setWindowTitle('Ingresar mercadería · NexoMerc ERP')
  self.setMinimumWidth(560);self.resize(650,480)
  self.erp=parent.erp;self.product=product
  layout=QVBoxLayout(self);layout.setContentsMargins(22,18,22,18);layout.setSpacing(12)
  h=QLabel('Registrar mercadería recibida');h.setObjectName('heading');layout.addWidget(h)
  hint=QLabel('Sumá la cantidad que llegó. Si ya existe stock, se agregará: NO reemplaza el total. Las ventas descuentan automáticamente cuando se cobra.')
  hint.setObjectName('helper');hint.setWordWrap(True);layout.addWidget(hint)
  detail=QLabel(f"Producto: {product['name']}  ·  Unidad base: {product['unit']}")
  detail.setObjectName('kpi_title');layout.addWidget(detail)
  form=QFormLayout();form.setSpacing(11)
  self.branch=QComboBox()
  for b in self.erp.catalogs('branches'):
   if b.get('active',1):self.branch.addItem(b['name'],b['id'])
  if branch_id:
   ix=self.branch.findData(branch_id)
   if ix>=0:self.branch.setCurrentIndex(ix)
  form.addRow('Sucursal de ingreso *',self.branch)
  self.qty=QuantitySpinBox();self.qty.setRange(0.001,999999999);self.qty.setValue(1)
  form.addRow('Cantidad recibida *',self.qty)
  self.presentation=QComboBox();self.presentation.addItem('Unidad base · '+product['unit'],'base')
  cfg=self.erp.packaging(product['id'])
  if cfg['pack_milli']:
   self.presentation.addItem('Paquete · '+quantity(cfg['pack_milli'])+' '+product['unit'],'pack')
  if cfg['box_milli']:
   self.presentation.addItem('Caja · '+quantity(cfg['box_milli'])+' '+product['unit'],'box')
  form.addRow('Presentación de entrada *',self.presentation)
  self.expiry=QLineEdit();self.expiry.setPlaceholderText('Opcional · AAAA-MM-DD')
  form.addRow('Vencimiento (opcional)',self.expiry)
  self.reference=QLineEdit();self.reference.setPlaceholderText('Remito, factura o referencia (opcional)')
  form.addRow('Comprobante / referencia',self.reference)
  self.note=QLineEdit();self.note.setPlaceholderText('Ejemplo: Entrada de mercadería · opcional')
  form.addRow('Observaciones (opcional)',self.note)
  layout.addLayout(form)
  self.preview=QLabel();self.preview.setObjectName('helper');self.preview.setWordWrap(True)
  self.preview.setStyleSheet('font-size:14px;font-weight:750;color:#2F1609;padding:8px;')
  layout.addWidget(self.preview)
  self.qty.valueChanged.connect(self.update_preview)
  self.presentation.currentIndexChanged.connect(self.update_preview)
  self.branch.currentIndexChanged.connect(self.update_preview)
  self.update_preview()
  buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
  buttons.button(QDialogButtonBox.StandardButton.Ok).setText('Confirmar ingreso');buttons.button(QDialogButtonBox.StandardButton.Ok).setObjectName('primary')
  buttons.button(QDialogButtonBox.StandardButton.Cancel).setText('Cancelar')
  buttons.accepted.connect(self.accept);buttons.rejected.connect(self.reject);layout.addWidget(buttons)
 def update_preview(self,*ignored):
  cfg=self.erp.packaging(self.product['id'])
  factor={'base':1000,'pack':cfg['pack_milli'],'box':cfg['box_milli']}[self.presentation.currentData()]
  entered=round(self.qty.value()*1000)
  converted=(entered*factor)//1000
  bal=self.erp.one('SELECT onhand_milli FROM stock_balances WHERE product_id=? AND branch_id=?',(self.product['id'],self.branch.currentData())) if self.branch.currentData() else None
  old=bal['onhand_milli'] if bal else 0
  self.preview.setText(f'Antes: {quantity(old)} {self.product["unit"]}  +  Entrada: {quantity(converted)} {self.product["unit"]}  =  {quantity(old+converted)} {self.product["unit"]}')
 def accept(self):
  if self.qty.value()<=0:
   QMessageBox.warning(self,'Cantidad incorrecta','La cantidad debe ser mayor que cero.');return
  if (self.presentation.currentData()!='base' or self.product['unit'] not in ('kg','l')) and round(self.qty.value()*1000)%1000:
   QMessageBox.warning(self,'Presentación indivisible','Las cajas, paquetes y unidades se ingresan en cantidades enteras.');return
  if self.expiry.text().strip():
   from datetime import date
   try:date.fromisoformat(self.expiry.text().strip())
   except ValueError:
    QMessageBox.warning(self,'Vencimiento incorrecto','Usá la fecha AAAA-MM-DD o dejala vacía.');return
  super().accept()
 def data(self):
  if self.exec()!=QDialog.DialogCode.Accepted:return None
  return {'qty':self.qty.value(),'input_type':self.presentation.currentData(),'branch_id':self.branch.currentData(),'reference':self.reference.text().strip(),'note':self.note.text().strip(),'expiry':self.expiry.text().strip(),'operation_key':__import__('uuid').uuid4().hex}

def combo_data(erp,table,label='name',none=False,only_active=True):
  if table=='users':rows=erp.list_users()
  else:rows=erp.catalogs(table)
  if only_active:rows=[r for r in rows if r.get('active',1)]
  opts=[('— Ninguno —',None)] if none else []
  return opts+[(f'{r["id"]} · {r.get(label,r.get("username",""))}',r['id']) for r in rows]

def fld(key,label,kind='text',value='',opts=None):return (key,label,kind,value,opts)
def action(parent,text,fn,primary=False,danger=False):
  b=QPushButton(text);b.setObjectName('primary' if primary else 'danger' if danger else '')
  b.clicked.connect(lambda: parent.safe(fn));return b

LABELS={'user_id':'Usuario','order_id':'Orden','reference':'Remito / referencia','qty_milli':'Cantidad','received_milli':'Recibido','photo_display':'Foto','product_status':'Estado','category_name':'Categoría','brand_name':'Marca','id':'N.º','sku':'SKU','barcode':'Código de barras','name':'Nombre','unit':'Unidad','cost_cents':'Costo','price_cents':'Precio de venta','min_milli':'Stock mínimo','max_milli':'Stock máximo','active':'Estado','product_id':'Producto','branch_id':'Sucursal','branch':'Sucursal','onhand_milli':'Existencias','onhand_display':'Existencias','reserved_display':'Reservado','available_display':'Disponible','min_display':'Stock mínimo','reserved_milli':'Reservado','available_milli':'Disponible','created_at':'Fecha de creación','timestamp':'Fecha y hora','action':'Acción','entity':'Registro','entity_id':'Referencia','parent_id':'Categoría superior','supplier_name':'Proveedor','branch_name':'Sucursal','purchase_status':'Estado','qty_display':'Pedido','received_display':'Recibido','pending_display':'Pendiente','supplier_id':'Proveedor','customer_id':'Cliente','status':'Estado','total_cents':'Total','payment':'Medio de pago','username':'Usuario','full_name':'Nombre completo','role':'Rol','failures':'Intentos fallidos','origin_id':'Origen','dest_id':'Destino','received_at':'Recibido','dispatched_at':'Despachado','tax_id':'Identificación fiscal','phone':'Teléfono','email':'Correo','address':'Dirección','document':'Documento','points':'Puntos','notes':'Observaciones','starts_at':'Desde','ends_at':'Hasta','details':'Detalle'}
def column_label(key):return LABELS.get(key,key.replace('_',' ').capitalize())
class RetailTable(QTableWidget):
 enterPressed=Signal()
 def keyPressEvent(self,event):
  if event.key() in (Qt.Key.Key_Return,Qt.Key.Key_Enter):
   self.enterPressed.emit();event.accept();return
  super().keyPressEvent(event)
def table_widget(rows,cols=None):
  if cols is None:cols=list(rows[0].keys()) if rows else ['id','Datos']
  tab=RetailTable(0,len(cols));tab.setHorizontalHeaderLabels([column_label(c) for c in cols]);tab.setAlternatingRowColors(True)
  tab.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows);tab.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
  tab.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
  tab.verticalHeader().hide();tab.verticalHeader().setDefaultSectionSize(35)
  tab.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
  tab.horizontalHeader().setStretchLastSection(True)
  if cols:tab.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.ResizeToContents)
  tab.setSortingEnabled(False)
  for r in rows:
   row=tab.rowCount();tab.insertRow(row)
   for j,k in enumerate(cols):
    v=r.get(k,''); v= '' if v is None else str(v)
    if k.endswith('_cents'):v=f'{int(v)/100:,.2f}'.replace(',','_').replace('.',',').replace('_','.')
    elif k.endswith('_milli'):v=quantity(int(v)).replace('.',',')
    elif k in ('active',):v='Activo' if int(v) else 'Inactivo'
    item=QTableWidgetItem(v)
    item.setData(Qt.ItemDataRole.UserRole,r.get('id',r.get('product_id')))
    if r.get('branch_id') is not None:item.setData(Qt.ItemDataRole.UserRole+1,int(r['branch_id']))
    tab.setItem(row,j,item)
  tab.setSortingEnabled(True)
  return tab

class ItemsDialog(QDialog):
 def __init__(self,parent,erp,title,for_po=False):
  super().__init__(parent);self.erp=erp;self.for_po=for_po;self.setWindowTitle(title);self.setMinimumSize(620,470);self.items={}
  lay=QVBoxLayout(self);h=QLabel(title);h.setObjectName('heading');lay.addWidget(h)
  info=QLabel('Agregá los productos y sus cantidades; verificá antes de confirmar.');lay.addWidget(info)
  pick=QHBoxLayout();self.combo=QComboBox();self.combo.setEditable(True);self.combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
  for p in erp.catalogs('products'):
   if p['active']:self.combo.addItem(f'{p["sku"]} · {p["name"]}',p['id'])
  self.qty=QuantitySpinBox();self.qty.setDecimals(3);self.qty.setRange(0.001,9999999);self.qty.setValue(1)
  self.price=QDoubleSpinBox();self.price.setRange(0,99999999);self.price.setDecimals(2)
  pick.addWidget(self.combo,4);pick.addWidget(QLabel('Cant.'));pick.addWidget(self.qty,1)
  if for_po:pick.addWidget(QLabel('Costo'));pick.addWidget(self.price,1)
  b=QPushButton('Añadir');b.clicked.connect(self.add_item);pick.addWidget(b);lay.addLayout(pick)
  self.tbl=QTableWidget(0,4 if for_po else 3);self.tbl.setHorizontalHeaderLabels(['ID','Producto','Cantidad']+(['Costo'] if for_po else []))
  self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);lay.addWidget(self.tbl)
  rm=QPushButton('Quitar seleccionado');rm.clicked.connect(self.remove_item);lay.addWidget(rm)
  btn=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
  btn.accepted.connect(self.accept);btn.rejected.connect(self.reject);lay.addWidget(btn)
  self.combo.currentIndexChanged.connect(self.set_cost);self.set_cost()
 def set_cost(self):
  if not self.for_po:return
  pid=self.combo.currentData()
  if pid:self.price.setValue(self.erp.entity('products',pid)['cost_cents']/100)
 def add_item(self):
  pid=self.combo.currentData()
  if not pid:return
  self.items[pid]={'product_id':pid,'qty':self.qty.value()}
  if self.for_po:self.items[pid]['cost']=self.price.value()
  self.redraw()
 def remove_item(self):
  r=self.tbl.currentRow()
  if r>=0:self.items.pop(int(self.tbl.item(r,0).text()),None);self.redraw()
 def redraw(self):
  self.tbl.setRowCount(0)
  for x in self.items.values():
   r=self.tbl.rowCount();self.tbl.insertRow(r)
   p=self.erp.entity('products',x['product_id'])
   values=[x['product_id'],p['name'],x['qty']]+([x['cost']] if self.for_po else [])
   for j,v in enumerate(values):self.tbl.setItem(r,j,QTableWidgetItem(str(v)))
 def accept(self):
  if not self.items:QMessageBox.warning(self,'Productos','Agregue al menos un producto.');return
  super().accept()
 def values(self):return list(self.items.values())

class Login(QDialog):
 def __init__(self,erp,assets):
  super().__init__();self.erp=erp;self.assets=assets;self.setWindowIcon(shop_icon());self.setWindowTitle('NexoMerc ERP · Acceso seguro');self.setMinimumSize(520,490)
  root=QVBoxLayout(self);root.setContentsMargins(54,24,54,25);root.setSpacing(14)
  logo=QLabel();pix=QPixmap(str(assets/'branding'/'nexomerc_f04_icon.png'))
  if not pix.isNull():logo.setPixmap(pix.scaled(170,155,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
  logo.setAlignment(Qt.AlignmentFlag.AlignCenter);root.addWidget(logo)
  self.first=not erp.scalar('SELECT COUNT(*) FROM users')
  self._login_busy=False
  headline=QLabel('Configuración inicial' if self.first else 'Bienvenido de nuevo');headline.setObjectName('heading');root.addWidget(headline)
  root.addWidget(QLabel('Cree el administrador principal con una contraseña segura.' if self.first else 'Ingrese con sus credenciales para administrar el negocio.'))
  self.inputs={}
  for key,label,secret in ([('username','Nombre de usuario',False),('full_name','Nombre completo',False),('password','Contraseña (10+ caracteres)',True)] if self.first else [('username','Usuario',False),('password','Contraseña',True)]):
   edit=QLineEdit();edit.setPlaceholderText(label)
   if secret:edit.setEchoMode(QLineEdit.EchoMode.Password)
   if key=='password':edit.returnPressed.connect(self.submit)
   else:edit.returnPressed.connect(self.focusNextChild)
   root.addWidget(edit);self.inputs[key]=edit
  btn=QPushButton('Crear administrador e ingresar' if self.first else 'Iniciar sesión')
  btn.setObjectName('primary');btn.setAutoDefault(False);btn.setDefault(False)
  btn.clicked.connect(self.submit);root.addWidget(btn)
  self.login_button=btn
  root.addWidget(QLabel('Tus datos permanecen en esta computadora.\nEl comprobante de caja es interno y NO fiscal.'))
 def submit(self):
  # A Return key can activate both QLineEdit.returnPressed and the dialog button.
  # Treat one attempt as exactly one call to ERP.login and one warning at most.
  if self._login_busy:return
  self._login_busy=True
  self.login_button.setEnabled(False)
  try:
   user=self.inputs['username'].text().strip();password=self.inputs['password'].text()
   if self.first:self.erp.initial_admin(user,self.inputs['full_name'].text().strip(),password)
   self.erp.login(user,password)
   self.accept()
  except (ERPError,sqlite3.Error) as e:
   QMessageBox.warning(self,'No se pudo ingresar',str(e))
  finally:
   # Delay unlock: absorbs a second click/Return event queued by Qt.
   QTimer.singleShot(450,self._unlock_login)
 def _unlock_login(self):
  self._login_busy=False
  if self.isVisible():self.login_button.setEnabled(True)

class CenteredStoreImage(QLabel):
 """Center the shop in the banner independently of the text and locale selector."""
 def __init__(self,source,parent=None):
  super().__init__(parent)
  self.setObjectName('heroShop')
  self._source=QPixmap(str(source))
  self.setAlignment(Qt.AlignmentFlag.AlignCenter)
  self.setMinimumWidth(115)
  self.setMinimumHeight(176)
  self.setMaximumHeight(194)
  self.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Preferred)
 def sizeHint(self):return QSize(260,184)
 def resizeEvent(self,event):
  if not self._source.isNull():
   self.setPixmap(self._source.scaled(max(1,self.width()-6),max(1,self.height()-5),Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
  super().resizeEvent(event)

class PurchaseOrderDialog(QDialog):
 """Compact purchase header; the next screen adds products and quantities."""
 def __init__(self,parent,erp):
  super().__init__(parent);self.setWindowIcon(shop_icon())
  self.setWindowTitle('Nueva orden de compra · NexoMerc ERP')
  self.resize(720,430);self.setMinimumWidth(590)
  root=QVBoxLayout(self);root.setContentsMargins(24,22,24,18);root.setSpacing(13)
  title=QLabel('Nueva orden de compra');title.setObjectName('heading');root.addWidget(title)
  desc=QLabel('Elegí quién suministra la mercadería y dónde se recibirá. En el siguiente paso vas a seleccionar productos, cantidades y costos.')
  desc.setObjectName('helper');desc.setWordWrap(True);root.addWidget(desc)
  fields=QFrame();fields.setObjectName('purchaseFields');form=QFormLayout(fields)
  form.setContentsMargins(18,15,18,15);form.setHorizontalSpacing(16);form.setVerticalSpacing(12)
  self.supplier=QComboBox();self.supplier.setMinimumWidth(300)
  for item in erp.catalogs('suppliers'):
   if item.get('active',1):self.supplier.addItem(item['name'],item['id'])
  self.branch=QComboBox()
  for label,bid in parent.branch_opts():self.branch.addItem(label,bid)
  self.notes=QTextEdit();self.notes.setFixedHeight(88)
  self.notes.setPlaceholderText('Opcional: condiciones acordadas, fecha estimada de entrega, información del pedido…')
  form.addRow('Proveedor *',self.supplier)
  form.addRow('Sucursal destino *',self.branch)
  form.addRow('Observaciones',self.notes)
  root.addWidget(fields)
  guidance=QLabel('La orden se crea como borrador: no altera el stock hasta que confirmes la recepción.')
  guidance.setObjectName('helper');guidance.setWordWrap(True);root.addWidget(guidance)
  root.addStretch(1)
  foot=QHBoxLayout();foot.addStretch(1)
  btn=QPushButton('Siguiente · Elegir productos');btn.setObjectName('primary');btn.clicked.connect(self.accept)
  cancel=QPushButton('Cancelar');cancel.clicked.connect(self.reject)
  foot.addWidget(btn);foot.addWidget(cancel);root.addLayout(foot)
 def accept(self):
  if self.supplier.currentData() is None or self.branch.currentData() is None:
   QMessageBox.warning(self,'Datos incompletos','Elegí un proveedor activo y una sucursal válida.');return
  super().accept()
 def values(self):return {'supplier':self.supplier.currentData(),'branch':self.branch.currentData(),'notes':self.notes.toPlainText().strip()}

class App(QMainWindow):
 def __init__(self,erp,assets):
  super().__init__();self.erp=erp;self.assets=Path(assets);self.module='dashboard';self.table=None;self.rows=[];self.mode='branches';self.report_mode='sales';self.cart={}
  from PySide6.QtCore import QSettings
  prefs=QSettings('NexoMerc','ERP');self.language=prefs.value('ui_locale',None) or (erp.one("SELECT value FROM settings WHERE key='locale'") or {}).get('value','es_AR')
  if not locale_supported(self.language):self.language='es_AR'
  settings=erp.one("SELECT value FROM settings WHERE key='currency'")
  self.currency=(settings or {}).get('value','ARS')
  if not valid_currency(self.currency):self.currency='ARS'
  global _ACTIVE_CURRENCY
  _ACTIVE_CURRENCY=self.currency
  self.setWindowIcon(shop_icon());self.setWindowTitle('NexoMerc ERP · V2-F16');self.setMinimumSize(950,540);self.resize(1440,840)
  shell=QWidget();self.setCentralWidget(shell);layout=QHBoxLayout(shell);layout.setContentsMargins(0,0,0,0);layout.setSpacing(0)
  sidebar=QFrame();sidebar.setObjectName('sidebar');sidebar.setFixedWidth(276);side=QVBoxLayout(sidebar);side.setContentsMargins(15,20,15,16)
  brand=QHBoxLayout()
  logo=QLabel();logo.setPixmap(QPixmap(str(self.assets/'branding'/'nexomerc_f04_icon.png')).scaled(78,78,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
  brand.addWidget(logo)
  logo_text=QVBoxLayout()
  log=QLabel('NexoMerc  ERP');log.setObjectName('brandTitle');log.setStyleSheet('font-size:20px;font-weight:900;color:white;background:transparent;')
  sub=QLabel('Retail Intelligence');sub.setObjectName('brandTagline');sub.setStyleSheet('font-size:11px;color:#FFD1AD;background:transparent;font-weight:600;')
  logo_text.addWidget(log);logo_text.addWidget(sub);brand.addLayout(logo_text)
  side.addLayout(brand)
  scr=QScrollArea();scr.setWidgetResizable(True);scr.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff);scr.setStyleSheet('background:transparent;border:none;')
  contents=QWidget();contents.setObjectName('navContents');self.links={}
  sv=QVBoxLayout(contents);sv.setContentsMargins(0,20,4,0);sv.setSpacing(5)
  for mod,label in MENU:
   if mod=='products':
    if not (erp.available('products') or erp.available('inventory')):continue
   elif mod=='purchases':
    if not (erp.available('purchases') or erp.available('suppliers')):continue
   elif not erp.available(mod):continue
   short={'receipts':'Recepción de mercadería','purchases':'Compras y proveedores','branches':'Sucursales y transferencias','reports':'Reportes y estadísticas','settings':'Configuración'}.get(mod,label)
   btn=QPushButton('  '+tr(short,self.language));btn.setProperty('active',False);btn.setToolTip(tr(HELP.get(mod,('',label))[1],self.language));btn.clicked.connect(lambda _=False,m=mod:self.safe(lambda:self.open_module('inventory' if m=='products' and not self.erp.available('products') else ('suppliers' if m=='purchases' and not self.erp.available('purchases') else m))))
   sv.addWidget(btn);self.links[mod]=btn
  sv.addStretch();scr.setWidget(contents);side.addWidget(scr,1)
  account=erp._user();who=QLabel(f'{account["full_name"]}\n{account["role"].upper()}');who.setWordWrap(True);side.addWidget(who)
  self.logout_button=QPushButton(tr('Cerrar sesión',self.language));self.logout_button.clicked.connect(self.logout);side.addWidget(self.logout_button)
  layout.addWidget(sidebar)
  self.content=QScrollArea();self.content.setWidgetResizable(True)
  self.content.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
  layout.addWidget(self.content,1)
  self.statusBar().showMessage(self.text('NexoMerc ERP · Local data · Non-fiscal receipts'))
  self.open_module('dashboard')
 def text(self,source):
  return tr(source,self.language)
 def change_language(self,code):
  if not locale_supported(code) or code==self.language:return
  from PySide6.QtCore import QSettings
  self.language=code
  QSettings('NexoMerc','ERP').setValue('ui_locale',code)
  for mod,btn in self.links.items():
   short={'receipts':'Recepción de mercadería','purchases':'Compras y proveedores','branches':'Sucursales y transferencias','reports':'Reportes y estadísticas','settings':'Configuración'}.get(mod,TITLES[mod])
   btn.setText('  '+self.text(short));btn.setToolTip(self.text(HELP.get(mod,('',short))[1]))
  self.logout_button.setText(self.text('Cerrar sesión'))
  self.open_module(self.module)
 def translate_page(self):
  page=self.content.widget()
  if page is not None:localize_tree(page,self.language)
 def _money(self,amount):
  return price_label(money(amount),self.currency)
 def logout(self):
  self.erp.logout();self.close()
 def safe(self,fn):
  try:return fn()
  except sqlite3.IntegrityError as e:
   msg=str(e)
   if 'UNIQUE constraint failed' in msg:detail='Este código, nombre o identificador ya existe. Utilice un valor diferente.'
   elif 'FOREIGN KEY constraint failed' in msg:detail='El registro está asociado a operaciones previas y no se puede modificar así.'
   elif 'CHECK constraint failed' in msg:detail='La operación incumple un límite de cantidad, precio o estado.'
   else:detail='Los datos no superaron una validación de integridad.'
   QMessageBox.warning(self,'Validación de datos',detail+'\n\nNo se guardó esta operación.')
  except sqlite3.OperationalError as e:
   logging.exception('SQLite operational failure')
   QMessageBox.warning(self,'Problema de almacenamiento','No se completó la operación con la base de datos. Revisá el espacio en disco, permisos y si otra aplicación usa el archivo. Detalle: '+str(e))
  except (ERPError,ValueError,KeyError) as e:
   QMessageBox.warning(self,'Operación no completada',f'{e}\n\nSi el cambio se rechazó antes de confirmar, no se aplicó.')
  except Exception:
   logging.exception('Unhandled UI exception')
   QMessageBox.critical(self,'Error inesperado','Se produjo un error inesperado. Revisá el archivo de diagnóstico local. No repitas una operación antes de verificar su estado.')
 def message(self,txt='Operación completada correctamente.'):
  QMessageBox.information(self,'NexoMerc ERP',self.text(txt))
 def confirm(self,text):return QMessageBox.question(self,self.text('Confirmar operación'),self.text(text))==QMessageBox.StandardButton.Yes
 def prompt(self,title,fields):
  form=Form(self,title,fields)
  return form.data() if form.exec()==QDialog.DialogCode.Accepted else None
 def root(self,module):
  self.module=module
  self.product_filters_ready=False
  for k,b in self.links.items():
   b.setProperty('active',k==('products' if module=='inventory' else ('purchases' if module=='suppliers' else module)))
   b.setIcon(_f18_nav_icon(self,k,k==('products' if module=='inventory' else ('purchases' if module=='suppliers' else module))))
   b.setIconSize(QSize(20,20))
   b.style().unpolish(b);b.style().polish(b)
  old=self.content.takeWidget()
  if old:old.hide();old.deleteLater()
  pane=QWidget();pane.setObjectName('workSurface');self.content.setWidget(pane);self.outer=QVBoxLayout(pane)
  self.outer.setContentsMargins(23,22,23,24);self.outer.setSpacing(18)
  # Uniform ornamental panel across screens; visually highlights only the active page.
  hero=QFrame();hero.setObjectName('banner');hero.setMinimumHeight(198)
  row=QGridLayout(hero);row.setContentsMargins(22,15,18,15);row.setHorizontalSpacing(14);row.setVerticalSpacing(6)
  head_box=QWidget();head=QVBoxLayout(head_box);head.setContentsMargins(0,0,0,0);head.setSpacing(6)
  trail=QLabel('NexoMerc ERP  ›  '+self.text('Tienda y operaciones conectadas'));trail.setObjectName('subheading');head.addWidget(trail)
  title=QLabel(self.text('Productos y stock' if module in ('products','inventory') else ('Compras y proveedores' if module in ('purchases','suppliers') else TITLES[module])));title.setObjectName('heading');head.addWidget(title)
  description=QLabel(self.text(('Administrá productos, fotos, precios y existencias desde un solo lugar.' if module in ('products','inventory') else ('Prepará pedidos, consultá entregas y organizá los datos de tus proveedores desde un solo lugar.' if module in ('purchases','suppliers') else HELP.get(module,('','Gestión comercial'))[1]))));description.setObjectName('subheading')
  description.setWordWrap(True);head.addWidget(description)
  row.addWidget(head_box,0,0,2,1)
  illustration=CenteredStoreImage(self.assets/'branding'/'supermercado_f04.png')
  row.addWidget(illustration,0,1,2,1)
  language=QComboBox();language.setObjectName('localeSelector');language.setToolTip(self.text('Seleccionar idioma'))
  for code,name in LANGUAGES.items():language.addItem(name,code)
  language.setCurrentIndex(max(0,language.findData(self.language)))
  language.currentIndexChanged.connect(lambda:self.change_language(language.currentData()))
  row.addWidget(language,0,2,1,1,Qt.AlignmentFlag.AlignTop|Qt.AlignmentFlag.AlignRight)
  # Three equally weighted zones: storefront center aligns with the banner center.
  row.setColumnStretch(0,1);row.setColumnStretch(1,1);row.setColumnStretch(2,1)
  head_box.setMinimumWidth(140);title.setWordWrap(True);trail.setWordWrap(True)
  row.setRowStretch(1,1)
  self.outer.addWidget(hero)
  if module in ('products','inventory'):
   switch=QFrame();switch.setObjectName('catalogModeBar')
   slots=QHBoxLayout(switch);slots.setContentsMargins(8,8,8,8);slots.setSpacing(8)
   for page,label in (('products','Catálogo y precios'),('inventory','Existencias y movimientos')):
    if not self.erp.available(page):continue
    tab=QPushButton(self.text(label));tab.setObjectName('catalogModeActive' if page==module else 'catalogModeTab')
    tab.setToolTip(self.text('Productos, fotografías, categorías y precios.' if page=='products' else 'Stock real por sucursal, ingresos, conteos y reservas.'))
    tab.setMinimumHeight(44)
    tab.clicked.connect(lambda _=False,p=page:self.safe(lambda:self.open_module(p)))
    slots.addWidget(tab,1)
   self.outer.addWidget(switch)
  if module in ('purchases','suppliers'):
   self.purchase_workspace_tabs()
  self.tools=QHBoxLayout();self.tools.setSpacing(8);self.outer.addLayout(self.tools)
  self.search=QLineEdit();self.search.setPlaceholderText('Buscar por nombre, código o cualquier dato visible…');self.search.setClearButtonEnabled(True)
  self.search.textChanged.connect(self.filter_table)
  self.outer.addWidget(self.search)
  return pane
 def tool(self,text,fn,primary=False,danger=False):
  b=action(self,self.text(text),fn,primary,danger)
  b.setToolTip(ACTION_HELP.get(text,text))
  if self.module=='inventory' and text in ACTION_HELP:
   wrap=QWidget();column=QVBoxLayout(wrap);column.setContentsMargins(0,0,0,0);column.setSpacing(4)
   column.addWidget(b)
   desc=QLabel(self.text(ACTION_HELP[text]));desc.setObjectName('helper');desc.setWordWrap(True);desc.setMinimumHeight(38)
   column.addWidget(desc);self.tools.addWidget(wrap)
  else:self.tools.addWidget(b)
 def show_rows(self,rows,cols=None):
  self.rows=rows;self.table=table_widget(rows,cols)
  self.table.doubleClicked.connect(self.queue_edit)
  self.table.enterPressed.connect(self.queue_edit)
  self.table.itemSelectionChanged.connect(self._record_selection)
  self._restore_selection()
  self.outer.addWidget(self.table,1);self.filter_table(self.search.text())
 def _record_selection(self):
  if not self.table or self.table.currentRow()<0:return
  item=self.table.item(self.table.currentRow(),0)
  if item is not None:
   key=(item.data(Qt.ItemDataRole.UserRole),item.data(Qt.ItemDataRole.UserRole+1)) if self.module=='inventory' else item.data(Qt.ItemDataRole.UserRole)
   self._last_row_selection=(self.module,key)
 def _restore_selection(self):
  saved=getattr(self,'_last_row_selection',None)
  if not self.table or not saved or saved[0]!=self.module:return
  for row in range(self.table.rowCount()):
   item=self.table.item(row,0)
   if item is None:continue
   key=(item.data(Qt.ItemDataRole.UserRole),item.data(Qt.ItemDataRole.UserRole+1)) if self.module=='inventory' else item.data(Qt.ItemDataRole.UserRole)
   if key==saved[1]:self.table.selectRow(row);return
 def queue_edit(self,*args):
  if getattr(self,'_edit_pending',False):return
  try:pid=self.selected()
  except ERPError:return
  module=self.module
  self._edit_pending=True
  def invoke():
   try:
    if self.module==module:
     if module=='products':self.safe(lambda:self.product_form(pid))
     else:self.safe(self.on_double)
   finally:self._edit_pending=False
  QTimer.singleShot(0,invoke)
 def filter_table(self,text):
  if not self.table:return
  if self.module=='products' and getattr(self,'product_filters_ready',False):
   self.filter_products();return
  text=text.casefold().strip()
  for r in range(self.table.rowCount()):
   self.table.setRowHidden(r, bool(text) and not any(text in (self.table.item(r,c).text().casefold() if self.table.item(r,c) else '') for c in range(self.table.columnCount())))
 def selected(self):
  if not self.table or self.table.currentRow()<0:raise ERPError('Seleccione una fila antes de continuar.')
  it=self.table.item(self.table.currentRow(),0)
  if not it:raise ERPError('Selección inválida.')
  id=it.data(Qt.ItemDataRole.UserRole)
  if id is None:raise ERPError('No existe identificador para esta fila.')
  return int(id)
 def on_double(self):
  if self.module in ('products','suppliers','customers','users','promotions'):self.edit_current()
  elif self.module=='purchases':self.details_po()
  elif self.module=='pos':self.ticket()
 def branch_opts(self,none=False):
  self.erp._user()
  opts=([('— Ninguno —',None)] if none else [])+[(f'{r["id"]} · {r["name"]}',r['id']) for r in self.erp.all('SELECT * FROM branches WHERE active=1 ORDER BY name')]
  u=self.erp._user()
  if u['role']!='admin' and u['branch_id']:
   opts=[(n,v) for n,v in opts if v==u['branch_id'] or v is None]
  return opts
 def open_module(self,mod):
  # Products and stock are one sidebar destination but remain separate permission domains.
  # Old deep-links (dashboard -> inventory) land on the second subview.
  if mod=='products' and not self.erp.available('products') and self.erp.available('inventory'):
   mod='inventory'
  if mod=='purchases' and not self.erp.available('purchases') and self.erp.available('suppliers'):
   mod='suppliers'
  self.erp.check(mod)
  self.table=None;self.root(mod)
  handler=getattr(self,'page_'+mod)
  handler()
  self.translate_page()
  self.outer.addStretch(0)
 def reload(self):
  if getattr(self,'_reload_pending',False):return
  self._reload_pending=True
  def refresh():
   self._reload_pending=False
   self.safe(lambda:self.open_module(self.module))
  QTimer.singleShot(0,refresh)
 def page_dashboard(self):
  stats=self.erp.get_dashboard()
  cards=QHBoxLayout()
  for label,value in [('VENTAS DEL DÍA',self._money(stats['today_cents'])),('VENTAS DEL MES',self._money(stats['month_cents'])),('STOCK BAJO',str(stats['low_stock'])),('ÓRDENES PENDIENTES',str(stats['pending_orders']))]:
   card=QFrame();card.setObjectName('kpi');c=QVBoxLayout(card);a=QLabel(label);a.setObjectName('kpi_title');v=QLabel(value);v.setObjectName('kpi_value');c.addWidget(a);c.addWidget(v);cards.addWidget(card)
  self.outer.addLayout(cards)
  self.tool('Actualizar panel',self.reload,True)
  if self.erp.available('inventory'):self.tool('Ir al inventario',lambda:self.open_module('inventory'))
  if self.erp.available('pos'):self.tool('Ir a caja',lambda:self.open_module('pos'))
  self.outer.addWidget(QLabel('Actividad reciente · Operaciones auditadas'))
  self.show_rows(stats['recent'],['timestamp','action','entity','entity_id'])
 def center_photo_cells(self,photos):
  # Qt's QTableWidgetItem decoration is left-aligned and causes the offset in F10.
  from PySide6.QtWidgets import QHeaderView
  col=1
  self.table.setIconSize(QSize(42,42))
  header=self.table.horizontalHeader()
  header.setSectionResizeMode(col,QHeaderView.ResizeMode.Fixed)
  header.resizeSection(col,80)
  for row in range(self.table.rowCount()):
   first=self.table.item(row,0)
   if first is None:continue
   key=first.data(Qt.ItemDataRole.UserRole)
   photo=photos.get(int(key)) if key is not None else None
   label=QLabel()
   label.setObjectName('tablePhoto')
   label.setAlignment(Qt.AlignmentFlag.AlignCenter)
   label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents,True)
   label.setStyleSheet('background:transparent;border:0;padding:0;margin:0;')
   if photo:
    pix=QPixmap(str(self.erp.root/'photos'/photo))
    if not pix.isNull():label.setPixmap(pix.scaled(42,42,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
    else:label.setText('—')
   else:label.setText('—')
   item=self.table.item(row,col)
   if item is not None:
    item.setText('')
    item.setIcon(QIcon())
   self.table.setCellWidget(row,col,label)
   self.table.setRowHeight(row,56)
 def page_products(self):
  # Common catalog & stock workspace: only everyday tasks are primary actions.
  if self.erp.available('products','create'):
   self.tool('+ Nuevo producto',lambda:self.product_form(),True)
  if self.erp.available('products','edit'):
   self.tool('Editar',self.edit_current)
  self.tool('Ver ficha',self.product_detail)
  more=QPushButton(self.text('Más opciones ▾'))
  more.setToolTip(self.text('Activar, eliminar, restaurar o exportar productos.'))
  options=QMenu(more)
  if self.erp.available('products','edit'):
   toggle=options.addAction(self.text('Activar / desactivar'))
   toggle.triggered.connect(lambda checked=False:self.safe(self.product_toggle))
  self.delete_action=None;self.restore_action=None
  if self.erp.available('products','delete'):
   self.delete_action=options.addAction(self.text('Eliminar producto'))
   self.delete_action.triggered.connect(lambda checked=False:self.safe(self.product_archive))
   self.restore_action=options.addAction(self.text('Restaurar producto'))
   self.restore_action.triggered.connect(lambda checked=False:self.safe(self.product_restore))
   self.restore_action.setVisible(False)
  options.addSeparator()
  export=options.addAction(self.text('Exportar CSV'))
  export.triggered.connect(lambda checked=False:self.safe(self.product_export))
  more.setMenu(options);self.tools.addWidget(more)
  self.tools.addStretch(1)
  self.search.setPlaceholderText('Buscar por nombre, SKU o código de barras…')
  filter_row=QHBoxLayout();filter_row.setSpacing(12)
  self.product_filters={}
  for key,title,table in [('category_id','Categoría','categories'),('brand_id','Marca','brands')]:
   combo=QComboBox();combo.addItem('Todas',None)
   for item in self.erp.catalogs(table):combo.addItem(item['name'],item['id'])
   combo.setMinimumWidth(100);self.product_filters[key]=combo
   filter_row.addWidget(QLabel(title));filter_row.addWidget(combo,1)
   combo.currentIndexChanged.connect(lambda *_:self.filter_products())
  active=QComboBox();active.addItem('Todos',None);active.addItem('Activos',1);active.addItem('Inactivos',0);active.addItem('Eliminados (archivo)','archived')
  self.product_filters['active']=active;filter_row.addWidget(QLabel('Estado'));filter_row.addWidget(active,1)
  clear=QPushButton('Limpiar filtros');clear.clicked.connect(self.clear_product_filters);filter_row.addWidget(clear)
  self.outer.removeWidget(self.search);self.search.setMinimumWidth(180);filter_row.insertWidget(0,self.search,3)
  self.outer.addLayout(filter_row)
  self.outer.removeItem(self.tools);self.outer.addLayout(self.tools)
  categories={x['id']:x['name'] for x in self.erp.catalogs('categories')}
  brands={x['id']:x['name'] for x in self.erp.catalogs('brands')}
  rows=[dict(r,photo_display='',product_status=('Eliminado' if r.get('archived') else ('Activo' if r['active'] else 'Inactivo')),category_name=categories.get(r['category_id'],'—'),brand_name=brands.get(r['brand_id'],'—')) for r in self.erp.catalogs('products',include_archived=True)]
  self.product_by_id={r['id']:r for r in rows}
  self.show_rows(rows,['id','photo_display','sku','barcode','name','category_name','brand_name','price_cents','product_status'])
  self.table.setMinimumHeight(210)
  self.center_photo_cells({r['id']:r.get('photo') for r in rows})
  self.product_count=QLabel();self.product_count.setObjectName('helper');self.outer.addWidget(self.product_count)
  self.product_filters_ready=True;self.filter_products()
 def filter_products(self):
  if not getattr(self,'product_filters_ready',False) or not self.table:return
  text=self.search.text().strip().casefold();count=0
  archived_filter=self.product_filters['active'].currentData()=='archived'
  if getattr(self,'delete_action',None) is not None:self.delete_action.setVisible(not archived_filter)
  if getattr(self,'restore_action',None) is not None:self.restore_action.setVisible(archived_filter)
  for row in range(self.table.rowCount()):
   pid=self.table.item(row,0).data(Qt.ItemDataRole.UserRole);record=self.product_by_id[pid]
   match=not text or any(text in str(record.get(k,'')).casefold() for k in ('name','sku','barcode'))
   for key,combo in self.product_filters.items():
    selected=combo.currentData()
    if key=='active':
     if selected=='archived':match=match and bool(record.get('archived'))
     else:
      match=match and not bool(record.get('archived'))
      if selected is not None and record.get('active')!=selected:match=False
    elif selected is not None and record.get(key)!=selected:match=False
   self.table.setRowHidden(row,not match);count+=int(match)
  self.product_count.setText(f'{count} productos visibles · Doble clic o Enter para editar · Eliminados: elegí Estado > Eliminados (archivo) para restaurar. Los movimientos históricos se conservan.')
 def clear_product_filters(self):
  self.search.clear()
  for combo in self.product_filters.values():combo.setCurrentIndex(0)
 def product_archive(self):
  pid=self.selected()
  if self.erp.is_product_archived(pid):
   raise ERPError('Este producto ya está eliminado del catálogo. Podés restaurarlo.')
  impact=self.erp.archive_impact(pid)
  product=impact['product']
  def qty(value):return quantity(value).replace('.',',')
  balances=[f"  • {r['name']}: {qty(r['onhand_milli'])} en stock; {qty(r['reserved_milli'])} reservadas" for r in impact['branches'] if r['onhand_milli'] or r['reserved_milli']]
  detail='\n'.join(balances) if balances else '  • Sin existencias registradas.'
  dependencies=(f"Ventas: {impact['sale_lines']}  |  Ingresos: {impact['receipt_lines']+impact['manual_receipts']}  |  "
                f"Movimientos: {impact['stock_movements']}\n"
                f"Compras pendientes: {impact['purchases_pending']}  |  Traslados pendientes: {impact['transfers_pending']}")
  text=(f"¿SEGURO QUE QUERÉS ELIMINAR '{product['name']}' DEL CATÁLOGO?\n"
        f"SKU: {product['sku']}\n\n"
        f"Existencias actuales: {qty(impact['onhand_milli'])}\n{detail}\n\n"
        f"{dependencies}\n\n"
        'Al confirmar, el producto se oculta del catálogo, del inventario activo y del POS.\n'
        'NO se borran fotos, ingresos, ventas, existencias ni movimientos históricos. '
        'Las promociones de este producto quedarán desactivadas.\n'
        'Podés recuperarlo desde Estado > Eliminados (archivo).')
  warning=QMessageBox(self)
  warning.setWindowIcon(shop_icon())
  warning.setIcon(QMessageBox.Icon.Warning)
  warning.setWindowTitle('Confirmar eliminación de producto')
  warning.setText(text)
  yes=warning.addButton('Sí, eliminar del catálogo',QMessageBox.ButtonRole.DestructiveRole)
  cancel=warning.addButton('Cancelar',QMessageBox.ButtonRole.RejectRole)
  warning.setDefaultButton(cancel)
  warning.exec()
  if warning.clickedButton() is not yes:return
  self.erp.archive_product(pid,'Confirmación explícita desde Productos')
  self.reload()
  self.message('El producto se retiró de las listas activas. El historial, las fotos y las existencias se conservaron. Podés restaurarlo desde Eliminados (archivo).')
 def product_restore(self):
  pid=self.selected();product=self.erp.entity('products',pid)
  if not self.erp.is_product_archived(pid):raise ERPError('Ese producto no está eliminado. Elegí Estado > Eliminados (archivo).')
  if not self.confirm(f'¿Restaurar {product["name"]}? Quedará inactivo hasta que lo actives desde Productos.'):
   return
  self.erp.restore_product(pid)
  self.reload();self.message('Producto restaurado como inactivo. Filtrá Estado > Inactivos y usá Activar / desactivar.')
 def product_toggle(self):
  pid=self.selected();record=self.erp.entity('products',pid)
  if self.erp.is_product_archived(pid):raise ERPError('Primero restaure el producto desde Estado > Eliminados (archivo).')
  if not self.confirm(('Desactivar' if record['active'] else 'Activar')+' '+record['name']+'? Se conserva su historial.'):return
  self.erp.save_catalog('products',{'active':not record['active']},pid);self.reload()
 def product_export(self):
  self.erp.check('products')
  path,_=QFileDialog.getSaveFileName(self,'Exportar catálogo visible','','CSV (*.csv)')
  if not path:return
  cols=['sku','barcode','name','category_name','brand_name','price_cents','min_milli','max_milli','product_status']
  with open(path,'w',encoding='utf-8-sig',newline='') as stream:
   writer=csv.writer(stream,delimiter=';');writer.writerow([column_label(k) for k in cols])
   for i in range(self.table.rowCount()):
    if self.table.isRowHidden(i):continue
    record=self.product_by_id[self.table.item(i,0).data(Qt.ItemDataRole.UserRole)]
    writer.writerow([_money(record[k]).replace('.',',') if k.endswith('_cents') else quantity(record[k]).replace('.',',') if k.endswith('_milli') else record[k] for k in cols])
  self.message('Catálogo visible exportado.')
 def product_fields(self,old=None):
  old=old or {}
  return [fld('sku','SKU *',value=old.get('sku','')),fld('barcode','Código de barras',value=old.get('barcode','')),
   fld('name','Descripción *',value=old.get('name','')),fld('category_id','Categoría','choice',old.get('category_id'),combo_data(self.erp,'categories',none=True)),
   fld('brand_id','Marca','choice',old.get('brand_id'),combo_data(self.erp,'brands',none=True)),fld('supplier_id','Proveedor','choice',old.get('supplier_id'),combo_data(self.erp,'suppliers',none=True)),
   fld('cost',f'Costo unitario ({self.currency})','money',old.get('cost_cents',0)/100),fld('price',f'Precio venta ({self.currency})','money',old.get('price_cents',0)/100),
   fld('minimum','Stock mínimo','qty',old.get('min_milli',0)/1000),fld('maximum','Stock máximo','qty',old.get('max_milli',0)/1000),
   fld('unit','Unidad base de control/venta','choice',old.get('unit','u'),[('Unidad (u)','u'),('Kilogramo (kg)','kg'),('Litro (L)','l')]+([('Paquete (tipo anterior; revisar)','paquete')] if old.get('unit')=='paquete' else [])+([('Caja (tipo anterior; revisar)','caja')] if old.get('unit')=='caja' else [])),
   fld('pack_factor','Contenido de 1 paquete (en unidad base)','qty',self.erp.packaging(old['id'])['pack_milli']/1000 if old.get('id') else 0),
   fld('box_factor','Contenido de 1 caja (en unidad base)','qty',self.erp.packaging(old['id'])['box_milli']/1000 if old.get('id') else 0),
   fld('stock_receive','Stock activo · registrar entrada ahora','bool',False),
   fld('stock_qty','Cantidad que llegó','qty',0),
   fld('stock_type','Presentación recibida','choice','base',[('Unidad base del producto','base'),('Paquete (requiere contenido configurado)','pack'),('Caja (requiere contenido configurado)','box')]),
   fld('stock_branch','Sucursal de entrada','choice',1,self.branch_opts()),
   fld('stock_expiry','Vencimiento opcional (AAAA-MM-DD)',value=''),
   fld('stock_ref','Referencia / remito (opcional)',value=''),
   fld('stock_notes','Motivo (opcional)',value=''),
   fld('photo_upload','Fotografía 1080 × 1080','image'),fld('active','Producto activo','bool',old.get('active',1))]
 def product_form(self,id=None):
  if getattr(self,'_product_open',False):return
  self._product_open=True
  try:self._product_form(id)
  finally:self._product_open=False
 def _product_form(self,id=None):
  old=self.erp.entity('products',id) if id else None
  if id and self.erp.is_product_archived(id):raise ERPError('Producto archivado. Restauralo antes de editarlo.')
  from .retail import ProductForm
  form=ProductForm(self,'Editar producto' if id else 'Nuevo producto',self.product_fields(old),old)
  d=form.data() if form.exec()==QDialog.DialogCode.Accepted else None
  if d is None:return
  photo_path=d.pop('photo_upload','')
  pack=d.pop('pack_factor');box=d.pop('box_factor')
  use_stock=d.pop('stock_receive')
  qty=d.pop('stock_qty');kind=d.pop('stock_type');bid=d.pop('stock_branch')
  expiry=d.pop('stock_expiry');reference=d.pop('stock_ref');note=d.pop('stock_notes')
  # Explicit entry intention: never silently discard quantities typed in the product editor.
  from .stock_intent import determine_entry
  stock_request=determine_entry(use_stock,qty,kind,pack,box,d.get('unit','u'),bid)
  if old and old.get('unit','u')!=d.get('unit','u'):
   movements=self.erp.scalar('SELECT COUNT(*) FROM stock_movements WHERE product_id=?',(id,))
   active_stock=self.erp.scalar('SELECT COUNT(*) FROM stock_balances WHERE product_id=? AND (onhand_milli<>0 OR reserved_milli<>0)',(id,))
   if movements or active_stock:
    raise ERPError('No se puede cambiar la unidad base de un producto que ya tiene existencias o movimientos. Usá un producto nuevo o una migración supervisada: cambiar u por kg reinterpretaría los datos existentes.')
  entry={'branch_id':bid,'qty':qty,'input_type':kind,'expiry':expiry,'reference':reference,'note':note,
         'operation_key':__import__('uuid').uuid4().hex} if stock_request else None
  d['cost_cents']=cents(d.pop('cost'));d['price_cents']=cents(d.pop('price'));d['min_milli']=round(d.pop('minimum')*1000);d['max_milli']=round(d.pop('maximum')*1000)
  pid=self.erp.save_product_with_stock(d,pack,box,entry,id)
  if photo_path:self.erp.attach_photo(pid,photo_path)
  self.reload();self.message(f'Producto #{pid} guardado'+(' y entrada de mercadería registrada.' if entry else '.')+(' Foto actualizada.' if photo_path else ''))
 def product_receive(self):
  product=self.erp.entity('products',self.selected())
  dialog=GoodsArrivalDialog(self,product)
  entry=dialog.data()
  if entry is None:return
  if not self.confirm('¿Confirmar la entrada? Se SUMARÁ al inventario de la sucursal elegida.'):
   return
  rid=self.erp.receive_manual(product['id'],**entry)
  self.reload();self.message(f'Entrada #{rid} guardada. Revisá Inventario para ver las nuevas existencias.')
 def product_detail(self):
  r=self.erp.entity('products',self.selected());photo=self.erp.root/'photos'/r['photo'] if r['photo'] else None
  m=QDialog(self);m.setWindowTitle('Ficha del producto');m.resize(520,480);l=QVBoxLayout(m)
  for k in ('sku','barcode','name','unit','cost_cents','price_cents','min_milli','max_milli'):
   value=money(r[k]) if k.endswith('_cents') else quantity(r[k]) if k.endswith('_milli') else r[k]
   l.addWidget(QLabel(f'{column_label(k)}: {value}'))
  if photo and photo.exists():
   im=QLabel();im.setPixmap(QPixmap(str(photo)).scaled(320,230,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation));l.addWidget(im)
  else:l.addWidget(QLabel('Sin fotografía cargada.'))
  close=QPushButton('Cerrar');close.clicked.connect(m.accept);l.addWidget(close);m.exec()
 def photo_product(self):
  pid=self.selected();name,_=QFileDialog.getOpenFileName(self,'Fotografía del producto','','Imágenes (*.png *.jpg *.jpeg *.webp)')
  if name:self.erp.attach_photo(pid,name);self.message('Fotografía validada y guardada en la carpeta privada del sistema.')
 def page_catalog(self):
  self.mode=getattr(self,'catalog_mode','categories')
  self.tool('Categorías',lambda:self.catalog_switch('categories'))
  self.tool('Marcas',lambda:self.catalog_switch('brands'))
  if self.erp.available('catalog','create'):self.tool('Nuevo registro',lambda:self.catalog_form(),True)
  if self.erp.available('catalog','edit'):self.tool('Editar',self.edit_current)
  self.show_rows(self.erp.catalogs(self.mode),['id','name']+(['parent_id'] if self.mode=='categories' else [])+['active'])
 def catalog_switch(self,t):self.catalog_mode=t;self.reload()
 def catalog_form(self,id=None):
  t=self.mode;old=self.erp.entity(t,id) if id else {}
  fs=[fld('name','Nombre *',value=old.get('name',''))]
  if t=='categories':fs.append(fld('parent_id','Categoría superior','choice',old.get('parent_id'),combo_data(self.erp,'categories',none=True)))
  fs.append(fld('active','Activo','bool',old.get('active',1)))
  d=self.prompt('Categoría' if t=='categories' else 'Marca',fs)
  if d is None:return
  if t=='categories' and id and d['parent_id']==id:raise ERPError('Una categoría no puede depender de sí misma.')
  self.erp.save_catalog(t,d,id);self.reload()
 def page_inventory(self):
  if self.erp.available('inventory','adjust'):
   self.tools.addWidget(action(self,self.text('Ingresar mercadería'),self.stock_receive,True))
   self.tools.addWidget(action(self,self.text('Conteo físico'),self.stock_count))
  self.tools.addWidget(action(self,self.text('Kardex / movimientos'),self.stock_history))
  more=QPushButton(self.text('Más opciones ▾'))
  more.setToolTip(self.text('Ajustes, reservas, liberaciones e ingresos anteriores.'))
  options=QMenu(more)
  if self.erp.available('inventory','adjust'):
   for caption,handler in [('Ajustar stock',self.stock_adjust),('Reservar',lambda:self.stock_reservation(True)),('Liberar reserva',lambda:self.stock_reservation(False))]:
    cmd=options.addAction(self.text(caption))
    cmd.triggered.connect(lambda checked=False,fn=handler:self.safe(fn))
  receipts=options.addAction(self.text('Ingresos y vencimientos'))
  receipts.triggered.connect(lambda checked=False:self.safe(self.stock_receipts))
  more.setMenu(options);self.tools.addWidget(more)
  self.tools.addStretch(1)
  tip=QLabel('💡  Seleccioná una fila. Ingresar mercadería SUMA; Conteo físico FIJA la cantidad real; Kardex muestra el historial. En Más opciones encontrás correcciones y reservas. La venta cobrada descuenta existencias.')
  tip.setObjectName('helper');tip.setWordWrap(True);self.outer.addWidget(tip)
  records=[]
  for item in self.erp.inventory():
   record=dict(item,photo_display='')
   base=record.get('unit','u')
   suffix={'u':'u','kg':'kg','l':'L','paquete':'paquetes','caja':'cajas'}.get(base,base)
   for source,target in [('onhand_milli','onhand_display'),('reserved_milli','reserved_display'),('available_milli','available_display'),('min_milli','min_display')]:
    record[target]=quantity(record[source]).replace('.',',')+' '+suffix
   records.append(record)
  self.show_rows(records,['product_id','photo_display','sku','name','branch','onhand_display','reserved_display','available_display','min_display'])
  self.center_photo_cells({int(e['product_id']):e.get('photo') for e in records})
 def inventory_record(self):
  if not self.table or self.table.currentRow()<0:
   raise ERPError('Primero seleccioná la fila del producto y la sucursal en la tabla.')
  identity=self.table.item(self.table.currentRow(),0)
  if identity is None:raise ERPError('No se encontró el producto seleccionado.')
  pid=identity.data(Qt.ItemDataRole.UserRole)
  bid=identity.data(Qt.ItemDataRole.UserRole+1)
  if pid is None or bid is None:
   raise ERPError('No se pudo identificar producto y sucursal. Actualizá el inventario.')
  record=next((r for r in self.rows if int(r['product_id'])==int(pid) and int(r['branch_id'])==int(bid)),None)
  if record is None:raise ERPError('La fila seleccionada ya no coincide con el inventario. Actualizá la lista.')
  return int(pid),int(bid)
 def inventory_context(self):
  pid,bid=self.inventory_record()
  info=next((r for r in self.rows if int(r['product_id'])==pid and int(r['branch_id'])==bid),None)
  if info is None:raise ERPError('Actualizá el inventario y volvé a seleccionar el producto.')
  return info
 def stock_receive(self):
  pid,bid=self.inventory_record()
  product=self.erp.entity('products',pid)
  dialog=GoodsArrivalDialog(self,product,bid)
  result=dialog.data()
  if result is None:return
  if not self.confirm('¿Confirmar entrada de mercadería? Esta operación SUMA las unidades al stock y queda auditada.'):
   return
  rid=self.erp.receive_manual(pid,**result)
  self.reload();self.message(f'Ingreso #{rid} registrado. Stock actualizado; cada venta descontará las unidades vendidas.')
 def stock_receipts(self):
  pid,bid=self.inventory_record()
  rows=self.erp.manual_receipts(pid,bid)
  self.popup_table('Entradas registradas y vencimientos (informativos)',rows)
 def stock_initial(self):
  pid,bid=self.inventory_record()
  current=self.inventory_context()
  if current['onhand_milli']!=0 or current['reserved_milli']!=0:
   raise ERPError('Ya existen unidades registradas. Para corregir lo que hay realmente, utilizá Conteo físico.')
  if self.erp.scalar('SELECT COUNT(*) FROM stock_movements WHERE product_id=? AND branch_id=?',(pid,bid)):
   raise ERPError('Este producto ya tiene movimientos históricos. Utilizá Conteo físico para corregir el total.')
  dialog=InventoryStockDialog(self,current,'initial');d=dialog.data()
  if d is None:return
  if not self.confirm(f'¿Registrar {quantity(round(d["qty"]*1000))} unidades iniciales de {current["name"]} en {current["branch"]}?'):return
  # Revalidate after the dialog in case another operation updated the same DB.
  if self.erp.scalar('SELECT COUNT(*) FROM stock_movements WHERE product_id=? AND branch_id=?',(pid,bid)):
   raise ERPError('Se registró otro movimiento durante esta operación. Actualizá la lista.')
  self.erp.adjust_stock(pid,bid,d['qty'],'CARGA INICIAL · '+d['notes'])
  self.reload();self.message('Existencias iniciales guardadas. Se descontarán automáticamente al cobrar las ventas.')
 def stock_adjust(self):
  pid,bid=self.inventory_record()
  dialog=InventoryStockDialog(self,self.inventory_context(),'adjust');d=dialog.data()
  if d is None:return
  delta=d['qty'] if d['direction']=='+' else -d['qty']
  if not self.confirm(f'¿Confirmar ajuste de {quantity(round(delta*1000))} unidades? Se registrará en el Kardex.'):return
  self.erp.adjust_stock(pid,bid,delta,d['notes'])
  self.reload();self.message('Ajuste guardado. El movimiento quedó registrado en el Kardex y la auditoría.')
 def stock_count(self):
  pid,bid=self.inventory_record()
  current=self.inventory_context()
  dialog=InventoryStockDialog(self,current,'count');d=dialog.data()
  if d is None:return
  counted=round(d['qty']*1000)
  delta=counted-current['onhand_milli']
  if not self.confirm(f'Sistema: {quantity(current["onhand_milli"])} · Contadas: {quantity(counted)} · Diferencia: {quantity(delta)}. ¿Confirmar conteo?'):return
  diff=self.erp.physical_count(pid,bid,d['qty'],d['notes']);self.reload()
  self.message(f'Conteo registrado. Existencia real: {quantity(counted)}. Diferencia: {quantity(diff)} unidades.')
 def stock_reservation(self,add):
  pid,bid=self.inventory_record();d=self.prompt('Reservar stock · Apartar sin vender' if add else 'Liberar reserva · Devolver a disponible',[fld('qty','Cantidad','qty',1)])
  if d is None:return
  if add:self.erp.reserve(pid,bid,d['qty'])
  else:self.erp.unreserve(pid,bid,d['qty'])
  self.reload()
 def stock_history(self):
  pid,bid=self.inventory_record()
  rows=self.erp.all('SELECT timestamp,delta_milli,reason,ref,notes FROM stock_movements WHERE product_id=? AND branch_id=? ORDER BY id DESC LIMIT 200',(pid,bid))
  self.popup_table('Movimientos de inventario',rows)
 def page_receipts(self):
  notice=QLabel('PASO 1: Creá y enviá una orden de compra.   ›   PASO 2: Seleccioná la orden y registrá remito.   ›   PASO 3: Indicá cantidades recibidas.   ›   PASO 4: Confirmá: se suma al stock.')
  notice.setWordWrap(True);notice.setObjectName('helper');self.outer.addWidget(notice)
  if self.erp.available('receipts','create'):self.tool('Recibir una orden',self.receive_order,True)
  self.tool('Ver líneas recibidas',self.receipt_details)
  self.show_rows(self.erp.list_simple('receipts'),['id','order_id','reference','created_at','user_id'])
 def receipt_details(self):
  rid=self.selected();self.popup_table('Detalle de recepción',self.erp.all('SELECT * FROM receipt_lines WHERE receipt_id=?',(rid,)))
 def receive_order(self):
  orders=[x for x in self.erp.list_simple('purchase_orders') if x['status'] in ('submitted','partial')]
  if not orders:raise ERPError('No hay órdenes enviadas con saldo pendiente.')
  opts=[(f'OC #{x["id"]} · sucursal {x["branch_id"]} · {x["status"]}',x['id']) for x in orders]
  d=self.prompt('Seleccionar compra',[fld('order','Orden de compra','choice',opts[0][1],opts),fld('ref','N.º remito / factura del proveedor *')])
  if d is None:return
  lines=self.erp.all('SELECT l.*,p.name FROM purchase_lines l JOIN products p ON p.id=l.product_id WHERE l.order_id=? AND l.received_milli<l.qty_milli',(d['order'],))
  fs=[fld(str(x['product_id']),f'{x["name"]} (máx. {quantity(x["qty_milli"]-x["received_milli"])})','qty',0) for x in lines]
  amounts=self.prompt('Cantidades físicamente recibidas (0 = pendiente)',fs)
  if amounts is None:return
  valid={int(k):v for k,v in amounts.items() if v>0}
  self.erp.receive_po(d['order'],valid,d['ref']);self.reload();self.message('Recepción validada. Stock incrementado una sola vez.')
 def purchase_workspace_tabs(self):
  # Group navigation only: original purchase/supplier permission domains stay independent.
  switch=QFrame();switch.setObjectName('catalogModeBar')
  box=QHBoxLayout(switch);box.setContentsMargins(8,8,8,8);box.setSpacing(8)
  for module,label in (('purchases','Órdenes de compra'),('suppliers','Proveedores')):
   if not self.erp.available(module):continue
   b=QPushButton(self.text(label));b.setObjectName('catalogModeActive' if self.module==module else 'catalogModeTab')
   b.setMinimumHeight(44);b.clicked.connect(lambda checked=False,m=module:self.safe(lambda:self.open_module(m)))
   box.addWidget(b,1)
  self.outer.addWidget(switch)
 def page_purchases(self):
  if self.erp.available('purchases','create'):self.tool('Crear orden',self.new_po,True)
  if self.erp.available('purchases','approve'):
   self.tool('Enviar / aprobar',lambda:self.po_change('submit'))
  if self.erp.available('receipts','create'):self.tool('Recibir mercadería',self.receive_order)
  self.tool('Ver detalle',self.details_po)
  more=QPushButton('Más opciones ▾');opts=QMenu(more)
  if self.erp.available('purchases','approve'):
   item=opts.addAction('Cancelar borrador');item.triggered.connect(lambda checked=False:self.safe(lambda:self.po_change('cancel')))
  more.setMenu(opts);self.tools.addWidget(more)
  hint=QLabel('① Crear un pedido y agregar productos   →   ② Enviar / aprobar   →   ③ Registrar recepción con remito. Solo recibir incrementa las existencias.')
  hint.setObjectName('helper');hint.setWordWrap(True);self.outer.addWidget(hint)
  records=[]
  suppliers={int(s['id']):s['name'] for s in self.erp.catalogs('suppliers')} if self.erp.available('suppliers') else {}
  branches={int(b['id']):b['name'] for b in self.erp.catalogs('branches')} if self.erp.available('branches') else {}
  labels={'draft':'Borrador','submitted':'Enviada','partial':'Recibida parcialmente','completed':'Completada','canceled':'Cancelada','cancelled':'Cancelada'}
  for row in self.erp.list_simple('purchase_orders'):
   item=dict(row)
   item['supplier_name']=suppliers.get(int(row['supplier_id']),f'Proveedor #{row["supplier_id"]}')
   item['branch_name']=branches.get(int(row['branch_id']),f'Sucursal #{row["branch_id"]}')
   item['purchase_status']=labels.get(row['status'],str(row['status']))
   records.append(item)
  self.show_rows(records,['id','supplier_name','branch_name','purchase_status','created_at','notes'])
 def new_po(self):
  dlg=PurchaseOrderDialog(self,self.erp)
  if dlg.exec()!=QDialog.DialogCode.Accepted:return
  data=dlg.values()
  items=ItemsDialog(self,self.erp,'Productos de la orden',True)
  if items.exec()!=QDialog.DialogCode.Accepted:return
  oid=self.erp.create_po(data['supplier'],data['branch'],items.values(),data['notes'])
  self.reload();self.message(f'OC #{oid} creada como borrador. Enviá la orden antes de recibir mercadería.')
 def po_change(self,what):
  oid=self.selected()
  if not self.confirm(f'¿Confirmar {"envío" if what=="submit" else "cancelación"} de la orden #{oid}?'):return
  if what=='submit':self.erp.submit_po(oid)
  else:self.erp.cancel_po(oid)
  self.reload()
 def details_po(self):
  oid=self.selected()
  lines=self.erp.all('SELECT l.id,p.name,p.unit,l.qty_milli,l.received_milli,l.cost_cents FROM purchase_lines l JOIN products p ON p.id=l.product_id WHERE l.order_id=?',(oid,))
  if not lines:raise ERPError('La orden seleccionada no tiene líneas registradas.')
  records=[]
  for line in lines:
   u={'u':'u','kg':'kg','l':'L'}.get(line.get('unit'),line.get('unit','u'))
   item=dict(line)
   item['qty_display']=quantity(line['qty_milli'])+' '+u
   item['received_display']=quantity(line['received_milli'])+' '+u
   item['pending_display']=quantity(line['qty_milli']-line['received_milli'])+' '+u
   records.append(item)
  self.popup_table('Detalle de orden #'+str(oid),[{k:r[k] for k in ('name','qty_display','received_display','pending_display','cost_cents')} for r in records])
 def page_suppliers(self):
  if self.erp.available('suppliers','create'):self.tool('Nuevo proveedor',lambda:self.generic_form('suppliers'),True)
  if self.erp.available('suppliers','edit'):self.tool('Editar proveedor',self.edit_current)
  hint=QLabel('Directorio de proveedores y datos de contacto. Los pedidos de compra se registran en la vista anterior.')
  hint.setObjectName('helper');hint.setWordWrap(True);self.outer.addWidget(hint)
  self.show_rows(self.erp.catalogs('suppliers'),['id','name','tax_id','phone','email','active'])
 def page_customers(self):
  if self.erp.available('customers','create'):self.tool('Nuevo cliente',lambda:self.generic_form('customers'),True)
  if self.erp.available('customers','edit'):self.tool('Editar',self.edit_current)
  self.tool('Historial de compras',self.customer_history)
  self.show_rows(self.erp.catalogs('customers'),['id','name','document','phone','email','points','active'])
 def customer_history(self):
  id=self.selected();self.popup_table('Compras del cliente',self.erp.all('SELECT id,created_at,total_cents,status,payment FROM sales WHERE customer_id=? ORDER BY id DESC',(id,)))
 def generic_form(self,table,id=None):
  old=self.erp.entity(table,id) if id else {}
  formats={'suppliers':[('name','Razón social / nombre'),('tax_id','CUIT / identificación fiscal'),('phone','Teléfono'),('email','Correo'),('address','Domicilio')],
  'customers':[('name','Nombre del cliente'),('document','Documento / ID'),('phone','Teléfono'),('email','Correo'),('notes','Notas')],
  'branches':[('name','Nombre de sucursal'),('address','Dirección')]}
  fs=[fld(k,l,value=old.get(k,'')) for k,l in formats[table]]+[fld('active','Activo','bool',old.get('active',1))]
  d=self.prompt('Editar registro' if id else 'Nuevo registro',fs)
  if d is None:return
  self.erp.save_catalog(table,d,id);self.reload()
 def edit_current(self):
  id=self.selected()
  if self.module=='products':self.product_form(id)
  elif self.module=='catalog':self.catalog_form(id)
  elif self.module in ('suppliers','customers'):self.generic_form(self.module,id)
  elif self.module=='users':self.user_form(id)
  elif self.module=='branches' and self.mode=='branches':self.generic_form('branches',id)
  else:raise ERPError('Edición no disponible en esta vista.')
 def page_branches(self):
  self.mode=getattr(self,'branch_mode','branches')
  self.tool('Sucursales',lambda:self.switch_branch('branches'))
  self.tool('Transferencias',lambda:self.switch_branch('transfers'))
  if self.mode=='branches':
   if self.erp.available('branches','create'):self.tool('Nueva sucursal',lambda:self.generic_form('branches'),True)
   if self.erp.available('branches','edit'):self.tool('Editar sucursal',self.edit_current)
   self.show_rows(self.erp.catalogs('branches'),['id','name','address','active'])
  else:
   if self.erp.available('branches','transfer'):
    self.tool('Crear transferencia',self.transfer_new,True)
    self.tool('Despachar',lambda:self.transfer_action('dispatch'))
    self.tool('Confirmar recepción',lambda:self.transfer_action('receive'))
    self.tool('Cancelar borrador',lambda:self.transfer_action('cancel'),danger=True)
   self.tool('Ver productos',self.transfer_lines)
   self.show_rows(self.erp.list_simple('transfers'),['id','origin_id','dest_id','status','created_at','dispatched_at','received_at'])
 def switch_branch(self,m):self.branch_mode=m;self.reload()
 def transfer_new(self):
  opts=self.branch_opts()
  d=self.prompt('Nueva transferencia',[fld('origin','Desde sucursal','choice',None,opts),fld('dest','Hacia sucursal','choice',None,opts),fld('notes','Observaciones','long')])
  if d is None:return
  items=ItemsDialog(self,self.erp,'Productos a transferir')
  if items.exec()!=QDialog.DialogCode.Accepted:return
  self.erp.create_transfer(d['origin'],d['dest'],items.values(),d['notes']);self.reload();self.message('Transferencia en borrador: no se descontó stock todavía.')
 def transfer_action(self,act):
  id=self.selected()
  if not self.confirm(f'¿Confirmar {act} para la transferencia #{id}?'):return
  {'dispatch':self.erp.dispatch_transfer,'receive':self.erp.receive_transfer,'cancel':self.erp.cancel_transfer}[act](id)
  self.reload();self.message('Transferencia actualizada y movimiento auditado.')
 def transfer_lines(self):
  id=self.selected();self.popup_table('Productos en transferencia',self.erp.all('SELECT * FROM transfer_lines WHERE transfer_id=?',(id,)))
 def page_users(self):
  self.tool('Crear usuario',lambda:self.user_form(),True);self.tool('Editar / restablecer contraseña',self.edit_current)
  self.tool('Permisos personalizados',self.custom_permissions,True)
  self.tool('Matriz de roles',self.roles_matrix)
  self.show_rows(self.erp.list_users(),['id','username','full_name','role','branch_id','active','failures'])
 def user_form(self,id=None):
  old=self.erp.entity('users',id) if id else {}
  fs=[fld('username','Usuario',value=old.get('username','')),fld('name','Nombre completo',value=old.get('full_name','')),
    fld('role','Rol','choice',old.get('role','cashier'),[(x,x) for x in ROLE_PERMS]),
    fld('branch','Sucursal autorizada','choice',old.get('branch_id'),self.branch_opts(none=True)),
    fld('password','Contraseña nueva (vacía = mantener)' if id else 'Contraseña (mín. 10 caracteres)'),fld('active','Cuenta activa','bool',old.get('active',1))]
  d=self.prompt('Editar usuario' if id else 'Alta de usuario',fs)
  if d is None:return
  self.erp.save_user(d['username'],d['name'],d['role'],d['branch'],d['password'] or None,id,d['active']);self.reload()
 def custom_permissions(self):
  uid=self.selected();user=self.erp.entity('users',uid)
  if user['role']=='admin':raise ERPError('Las cuentas administradoras siempre tienen todos los permisos.')
  grid=self.erp.permission_grid(uid)
  actions=['view','create','edit','delete','adjust','approve','sell','void','cash','transfer','export']
  dlg=QDialog(self);dlg.setWindowTitle('Permisos por módulo y acción · '+user['username']);dlg.resize(1150,740)
  lay=QVBoxLayout(dlg);lay.addWidget(QLabel('Marcá las operaciones autorizadas; los cambios se validarán en la lógica de negocio.'))
  tabs=QTableWidget(len(TITLES),len(actions)+1)
  tabs.setHorizontalHeaderLabels(['Módulo']+['Ver','Crear','Editar','Eliminar','Ajustar','Aprobar','Vender','Anular','Caja','Transferir','Exportar'])
  tabs.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
  lookup={(e['module'],e['action']):e['allowed'] for e in grid}
  for i,m in enumerate(TITLES):
   label=QTableWidgetItem(TITLES[m]);label.setFlags(Qt.ItemFlag.ItemIsEnabled);tabs.setItem(i,0,label)
   for j,a in enumerate(actions,1):
    item=QTableWidgetItem('');item.setFlags(Qt.ItemFlag.ItemIsUserCheckable|Qt.ItemFlag.ItemIsEnabled)
    item.setCheckState(Qt.CheckState.Checked if lookup.get((m,a),False) else Qt.CheckState.Unchecked)
    tabs.setItem(i,j,item)
  lay.addWidget(tabs)
  foot=QLabel('Importante: acceder a la pestaña requiere «Ver». Los permisos de sucursal se comprueban además de esta matriz.')
  lay.addWidget(foot)
  buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel)
  buttons.accepted.connect(dlg.accept);buttons.rejected.connect(dlg.reject);lay.addWidget(buttons)
  if dlg.exec()!=QDialog.DialogCode.Accepted:return
  entries=[{'module':m,'action':a,'allowed':tabs.item(i,j).checkState()==Qt.CheckState.Checked} for i,m in enumerate(TITLES) for j,a in enumerate(actions,1)]
  self.erp.save_permissions(uid,entries);self.message('Permisos personalizados guardados y auditados.')
 def roles_matrix(self):
  rows=[]
  for role,mods in ROLE_PERMS.items():
   for mod,acts in mods.items():rows.append({'role':role,'module':mod,'actions':', '.join(sorted(acts))})
  self.popup_table('Permisos aplicados por el motor de datos',rows)
 def page_promotions(self):
  if self.erp.available('promotions','create'):self.tool('Nueva promoción',self.promo_new,True)
  if self.erp.available('promotions','edit'):self.tool('Activar / desactivar',self.promo_toggle)
  self.show_rows(self.erp.catalogs('promotions'),['id','product_id','branch_id','name','price_cents','starts_at','ends_at','active'])
 def promo_new(self):
  dates=date.today()
  d=self.prompt('Nueva promoción',[fld('product','Producto','choice',None,combo_data(self.erp,'products')),fld('branch','Sucursal (vacío = global)','choice',None,self.branch_opts(none=True)),
   fld('name','Nombre campaña'),fld('price',f'Precio promocional ({self.currency})','money',0),fld('from','Válida desde (AAAA-MM-DD)',value=dates.isoformat()),fld('to','Válida hasta (AAAA-MM-DD)',value=(dates+timedelta(days=30)).isoformat())])
  if d is None:return
  for key in ('from','to'):
   try:date.fromisoformat(d[key])
   except ValueError:raise ERPError('Fecha inválida: utilice AAAA-MM-DD.')
  self.erp.create_promotion(d['product'],d['branch'],d['name'],d['price'],d['from'],d['to']);self.reload()
 def promo_toggle(self):
  id=self.selected();p=self.erp.entity('promotions',id)
  self.erp.set_promotion_active(id,not p['active']);self.reload()
 def page_reports(self):
  self.tool('Filtrar fechas / sucursal',self.report_filters,True)
  self.tool('Ventas por día',lambda:self.switch_reports('sales'))
  self.tool('Productos líderes',lambda:self.switch_reports('top'))
  self.tool('Medios de pago',lambda:self.switch_reports('payments'))
  self.tool('Margen estimado',lambda:self.switch_reports('gross_margin'))
  if self.erp.available('reports','export'):
   self.tool('Exportar CSV',self.report_csv,True)
   self.tool('Exportar PDF',self.report_pdf)
  self.tool('Actualizar',self.reload)
  self.report_mode=getattr(self,'report_mode','sales')
  self.show_rows(self.erp.reports(**getattr(self,'report_filter',{}))[self.report_mode])
 def report_filters(self):
  old=getattr(self,'report_filter',{})
  data=self.prompt('Filtros de informes (fechas UTC)',[fld('branch','Sucursal','choice',old.get('branch'),self.branch_opts(none=True)),fld('start','Desde AAAA-MM-DD',value=old.get('start','')),fld('end','Hasta AAAA-MM-DD',value=old.get('end',''))])
  if data is None:return
  self.erp.reports(**data)
  self.report_filter=data;self.reload()
 def switch_reports(self,m):self.report_mode=m;self.reload()
 def report_csv(self):
  if not self.rows:raise ERPError('No hay datos para exportar.')
  filename,_=QFileDialog.getSaveFileName(self,'Exportar reporte','','CSV (*.csv)')
  if filename:self.erp.export_csv(self.rows,filename);self.message('Archivo CSV generado correctamente.')
 def report_pdf(self):
  self.erp.check('reports','export')
  if not self.rows:raise ERPError('No existen datos para el reporte.')
  filename,_=QFileDialog.getSaveFileName(self,'Guardar reporte en PDF','','PDF (*.pdf)')
  if not filename:return
  rows=self.rows;headers=list(rows[0]);markup='<h2>NexoMerc ERP - Reporte '+html.escape(self.report_mode)+'</h2><p>Resumen interno. No fiscal.</p><table border="1" cellspacing="0" cellpadding="5"><tr>'
  markup+=''.join('<th>'+html.escape(k)+'</th>' for k in headers)+'</tr>'
  for r in rows:markup+='<tr>'+''.join('<td>'+html.escape(str(r[k]))+'</td>' for k in headers)+'</tr>'
  markup+='</table>'
  doc=QTextDocument();doc.setHtml(markup);printer=QPrinter(QPrinter.PrinterMode.HighResolution)
  printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat);printer.setOutputFileName(filename);doc.print_(printer)
  self.message('Reporte PDF guardado.')
 def page_audit(self):
  self.tool('Verificar integridad de la cadena',self.audit_verify,True)
  self.tool('Exportar auditoría CSV',self.audit_export)
  self.show_rows(self.erp.list_audit(),['id','timestamp','username','action','entity','entity_id','details'])
 def audit_verify(self):
  ok,which=self.erp.verify_audit();self.message('Cadena íntegra dentro de esta base.' if ok else f'ATENCIÓN: discrepancia detectada en el evento #{which}.')
 def audit_export(self):
  rows=self.erp.list_audit();fn,_=QFileDialog.getSaveFileName(self,'Exportar eventos','','CSV (*.csv)')
  if fn and rows:
   with open(fn,'w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,list(rows[0]));w.writeheader();w.writerows(rows)
   self.message('Auditoría exportada.')
 def page_settings(self):
  self.search.hide();settings=self.erp.read_settings()
  editable=self.erp.available('settings','edit')
  if editable:
   self.tool('Guardar configuración',self.settings_save,True)
   self.tool('Respaldo completo ZIP',self.settings_backup,True)
   self.tool('Copia solo de SQLite',self.settings_db_backup)
  self.tool('Ver carpeta privada',lambda:self.message(str(self.erp.root)))
  self.fields={};card=QFrame();card.setObjectName('white');form=QFormLayout(card)
  form.setContentsMargins(25,25,25,25);form.setSpacing(16)
  labels={'business_name':'Nombre del comercio','tax_id':'Identificación fiscal',
          'country':'País / región','currency':'Moneda de operación',
          'receipt_footer':'Pie de ticket interno','address':'Domicilio comercial',
          'telephone':'Teléfono','locale':'Idioma / localización'}
  for key,label in labels.items():
   if key in ('locale','country','currency'):
    widget=QComboBox()
    if key=='locale':items=[(name,code) for code,name in LANGUAGES.items()]
    elif key=='country':items=[(name,code) for code,(name,currency) in COUNTRIES.items()]
    else:items=[(name,code) for code,name in CURRENCY_NAMES.items()]
    for name,code in items:widget.addItem(name,code)
    initial=(self.language if key=='locale' else settings.get(key,{'locale':'es_AR','country':'AR','currency':'ARS'}[key]))
    idx=widget.findData(initial);widget.setCurrentIndex(max(0,idx))
    widget.setEnabled(editable)
   else:
    widget=QLineEdit(settings.get(key,''));widget.setReadOnly(not editable)
   form.addRow(self.text(label),widget);self.fields[key]=widget
  self.fields['country'].currentIndexChanged.connect(self.suggest_currency)
  self.outer.addWidget(card)
  note=QLabel('La moneda se elige según el país. Cambiarla NO convierte precios, compras ni ventas anteriores; se conserva el valor numérico original. La facturación es interna, NO fiscal.')
  note.setObjectName('helper');note.setWordWrap(True);self.outer.addWidget(note)
 def suggest_currency(self,*_):
  if not hasattr(self,'fields') or 'currency' not in self.fields:return
  selected=for_country(self.fields['country'].currentData())
  idx=self.fields['currency'].findData(selected)
  if idx>=0:self.fields['currency'].setCurrentIndex(idx)
 def settings_save(self):
  data={key:(widget.currentData() if isinstance(widget,QComboBox) else widget.text().strip())
        for key,widget in self.fields.items()}
  if not valid_currency(data['currency']):raise ERPError('Moneda no disponible.')
  if data['currency']!=self.currency:
   warning=('ATENCIÓN: cambiar la moneda solo cambia cómo se etiquetan los importes. '
            'NO convierte automáticamente los precios, el inventario, las ventas ni los tickets existentes. '
            'Revisá los precios antes de vender. ¿Querés continuar?')
   if not self.confirm(warning):return
  self.erp.save_settings(data)
  old_language=self.language
  self.currency=data['currency'];global _ACTIVE_CURRENCY;_ACTIVE_CURRENCY=self.currency
  if data['locale']!=self.language:self.change_language(data['locale'])
  else:self.reload()
  self.message(self.text('Configuración guardada en SQLite.'))
 def settings_backup(self):
  f,_=QFileDialog.getSaveFileName(self,'Guardar respaldo integral','','Respaldo ZIP (*.zip)')
  if f:self.erp.backup_bundle(f);self.message('Backup ZIP íntegro: base SQLite y fotografías. Guárdelo en otro medio seguro.')
 def settings_db_backup(self):
  f,_=QFileDialog.getSaveFileName(self,'Guardar copia verificada','','Base SQLite (*.sqlite3)')
  if f:self.erp.backup(f);self.message('Copia realizada con API de respaldo consistente de SQLite.')
 def page_pos(self):
  self.search.hide()
  top=QHBoxLayout();top.addWidget(QLabel('Sucursal de venta:'))
  self.pos_branch=QComboBox()
  for label,id in self.branch_opts():self.pos_branch.addItem(label,id)
  self.pos_branch.currentIndexChanged.connect(lambda:self.safe(self.pos_refresh))
  top.addWidget(self.pos_branch);top.addStretch()
  if self.erp.available('pos','cash'):
   top.addWidget(action(self,'Abrir caja',self.pos_open))
   top.addWidget(action(self,'Cerrar caja / arqueo',self.pos_close))
  top.addWidget(action(self,self.text('Imprimir ticket'),self.print_ticket,True))
  top.addWidget(action(self,self.text('Exportar ticket'),self.ticket))
  if self.erp.available('pos','void'):top.addWidget(action(self,'Anular venta',self.pos_void,danger=True))
  self.outer.addLayout(top)
  self.pos_status=QLabel('');self.outer.addWidget(self.pos_status)
  add=QHBoxLayout();self.pos_product=QComboBox();self.pos_product.setEditable(True)
  for p in self.erp.catalogs('products'):
   if p['active']:self.pos_product.addItem(f'{p["sku"]} · {p["name"]} | {self._money(p["price_cents"])}',p['id'])
  self.pos_barcode=QLineEdit();self.pos_barcode.setPlaceholderText('▥   ESCANEAR CÓDIGO DE BARRAS + ENTER');self.pos_barcode.setMinimumHeight(50);self.pos_barcode.setToolTip('Compatible con lector USB HID modo teclado. Escaneá para agregar al carrito.');self.pos_barcode.returnPressed.connect(lambda:self.safe(self.pos_scan))
  self.pos_qty=QuantitySpinBox();self.pos_qty.setRange(.001,999999);self.pos_qty.setDecimals(3);self.pos_qty.setValue(1)
  self.pos_presentation=QComboBox();self.pos_presentation.setMinimumWidth(175)
  self.pos_product.currentIndexChanged.connect(self.pos_update_presentation)
  self.pos_presentation.currentIndexChanged.connect(self.pos_update_sale_hint)
  self.pos_qty.valueChanged.connect(self.pos_update_sale_hint)
  self.pos_sale_hint=QLabel('');self.pos_sale_hint.setObjectName('helper');self.pos_sale_hint.setWordWrap(True)
  self.pos_update_presentation()
  hint=QLabel('Lector USB: enfocá este campo y escaneá. Se agregará al carrito; el foco volverá automáticamente aquí.');hint.setObjectName('helper');hint.setWordWrap(True);self.outer.addWidget(hint)
  scan_row=QHBoxLayout();scan_row.addWidget(self.pos_barcode,4);scan_row.addWidget(action(self,'Escanear / Probar lector',self.pos_capture));self.outer.addLayout(scan_row)
  add.addWidget(self.pos_product,4);add.addWidget(QLabel('Venta por'));add.addWidget(self.pos_presentation,2);add.addWidget(QLabel('Cant.'));add.addWidget(self.pos_qty,1)
  add.addWidget(action(self,'Añadir producto',self.pos_add,True));self.outer.addLayout(add);self.outer.addWidget(self.pos_sale_hint)
  self.pos_cart=table_widget([],['id','producto','cantidad','unitario','subtotal']);self.outer.addWidget(self.pos_cart,1)
  bottom=QHBoxLayout();bottom.addWidget(action(self,'Quitar del carrito',self.pos_remove))
  bottom.addStretch();bottom.addWidget(QLabel('Cliente'))
  self.pos_customer=QComboBox();self.pos_customer.addItem('Consumidor final',None)
  for name,id in combo_data(self.erp,'customers'):self.pos_customer.addItem(name,id)
  bottom.addWidget(self.pos_customer);bottom.addWidget(QLabel('Pago'))
  self.pos_payment=QComboBox()
  for k,label in [('cash','Efectivo'),('debit','Débito'),('credit','Crédito'),('transfer','Transferencia'),('qr','QR'),('check','Cheque')]:self.pos_payment.addItem(label,k)
  bottom.addWidget(self.pos_payment)
  if self.erp.available('pos','sell'):bottom.addWidget(action(self,'COBRAR',self.pos_checkout,True))
  self.outer.addLayout(bottom)
  summary=QFrame();summary.setObjectName('pospanel');summary_layout=QHBoxLayout(summary)
  self.pos_total=QLabel(self.text('Total')+': '+self._money(0));self.pos_total.setObjectName('heading');summary_layout.addWidget(self.pos_total)
  self.outer.addWidget(summary)
  self.outer.addWidget(QLabel('El precio es por unidad base (unidad, kg o litro). Vender caja o paquete multiplica ese precio por su contenido; todavía no hay precios independientes por embalaje. COBRAR descuenta el stock.'))
  self.outer.addWidget(QLabel('Ventas recientes: seleccioná una operación para imprimir o exportar ticket interno NO fiscal.'))
  self.rows=self.erp.list_simple('sales');self.table=table_widget(self.rows,['id','created_at','branch_id','total_cents','payment','status'])
  self.outer.addWidget(self.table)
  self.pos_refresh();self.render_cart();self.pos_barcode.setFocus()
 def pos_update_presentation(self,*args):
  if not hasattr(self,'pos_presentation'):return
  pid=self.pos_product.currentData()
  self.pos_presentation.blockSignals(True);self.pos_presentation.clear()
  if pid:
   record=self.erp.entity('products',pid)
   unit=record.get('unit','u')
   self.pos_presentation.addItem({'u':'Unidad suelta','kg':'Kilogramo (kg)','l':'Litro (L)'}.get(unit,'Base ('+unit+')'),'base')
   cfg=self.erp.packaging(pid)
   if cfg.get('pack_milli',0):self.pos_presentation.addItem('Paquete · '+quantity(cfg['pack_milli'])+' '+unit,'pack')
   if cfg.get('box_milli',0):self.pos_presentation.addItem('Caja · '+quantity(cfg['box_milli'])+' '+unit,'box')
  self.pos_presentation.blockSignals(False)
  self.pos_update_sale_hint()
 def pos_sale_qty_milli(self):
  from .units import sale_base_milli
  pid=self.pos_product.currentData()
  if pid is None:raise ERPError('Seleccioná un producto para vender.')
  product=self.erp.entity('products',pid);cfg=self.erp.packaging(pid)
  return sale_base_milli(self.pos_qty.value(),product['unit'],self.pos_presentation.currentData() or 'base',cfg['pack_milli'],cfg['box_milli'])
 def pos_update_sale_hint(self,*args):
  if not hasattr(self,'pos_sale_hint'):return
  pid=self.pos_product.currentData()
  if not pid:return
  try:
   p=self.erp.entity('products',pid)
   qty_milli=self.pos_sale_qty_milli()
   price=self.erp.effective_price(pid,self.pos_branch.currentData()) if self.pos_branch.currentData() else p['price_cents']
   kind=self.pos_presentation.currentData() or 'base'
   detail='Paquete' if kind=='pack' else 'Caja' if kind=='box' else 'A granel / unidad'
   self.pos_sale_hint.setText(f'{detail}: {self.pos_qty.value():g} → {quantity(qty_milli)} {p["unit"]}. Subtotal estimado: {self._money(total_for(qty_milli,price))}. El stock se descontará en {p["unit"]} al COBRAR.')
  except ERPError as e:self.pos_sale_hint.setText(str(e))
 def pos_capture(self):
  from .retail import ScannerDialog
  d=ScannerDialog(self)
  if d.exec()==QDialog.DialogCode.Accepted:
   self.pos_barcode.setText(d.code.text());self.pos_scan()
 def pos_scan(self):
  barcode=self.pos_barcode.text().strip()
  if not barcode:return
  r=self.erp.one('SELECT id FROM products WHERE active=1 AND (barcode=? OR sku=?)',(barcode,barcode))
  if not r:
   self.pos_barcode.selectAll();self.pos_barcode.setFocus()
   self.statusBar().showMessage('Código no encontrado: revisá el código o creá el producto.',8000)
   return
  idx=self.pos_product.findData(r['id']);self.pos_product.setCurrentIndex(idx);self.pos_presentation.setCurrentIndex(0);self.pos_add();self.pos_barcode.clear();self.pos_barcode.setFocus()
 def pos_add(self):
  pid=self.pos_product.currentData()
  if pid is None:raise ERPError('Primero cargue un producto activo.')
  amount=self.cart.get(pid,0)+self.pos_sale_qty_milli()
  balance=self.erp.one('SELECT onhand_milli-reserved_milli AS available FROM stock_balances WHERE product_id=? AND branch_id=?',(pid,self.pos_branch.currentData()))
  if not balance or amount>balance['available']:raise ERPError('Stock disponible insuficiente para el carrito.')
  self.cart[pid]=amount;self.render_cart();self.pos_update_sale_hint()
 def pos_remove(self):
  r=self.pos_cart.currentRow()
  if r<0:raise ERPError('Seleccione un producto en el carrito.')
  pid=int(self.pos_cart.item(r,0).text());self.cart.pop(pid,None);self.render_cart()
 def render_cart(self):
  bid=self.pos_branch.currentData();self.pos_cart.setRowCount(0);total=0
  for pid,qty_milli in self.cart.items():
   p=self.erp.entity('products',pid);price=self.erp.effective_price(pid,bid);sub=total_for(qty_milli,price);total+=sub
   r=self.pos_cart.rowCount();self.pos_cart.insertRow(r)
   for i,v in enumerate([pid,p['name'],quantity(qty_milli)+' '+p['unit'],money(price),money(sub)]):self.pos_cart.setItem(r,i,QTableWidgetItem(str(v)))
  self.pos_total.setText(self.text('Total')+': '+self._money(total))
 def pos_refresh(self):
  bid=self.pos_branch.currentData()
  if not bid:return
  sess=self.erp.cash_session(bid)
  self.pos_status.setText((f'{self.text("Caja actual: ABIERTA")} #{sess["id"]} · {self.text("Apertura")} {self._money(sess["opening_cents"])}') if sess else self.text('Caja actual: CERRADA · Debe abrirla antes de cobrar'))
  self.render_cart()
 def pos_open(self):
  d=self.prompt('Apertura de caja',[fld('opening',f'Fondo inicial ({self.currency})','money',0)])
  if d is None:return
  self.erp.open_cash(self.pos_branch.currentData(),d['opening']);self.pos_refresh();self.message('Caja abierta. Las ventas quedarán vinculadas a este turno.')
 def pos_close(self):
  d=self.prompt('Cierre y arqueo',[fld('counted',f'Efectivo contado ({self.currency})','money',0)])
  if d is None:return
  if not self.confirm('Se cerrará el turno de caja. ¿Confirma el arqueo?'):return
  exp=self.erp.close_cash(self.pos_branch.currentData(),d['counted']);self.pos_refresh()
  self.message('Arqueo guardado. Efectivo esperado: '+self._money(exp)+' / contado: '+self._money(cents(d['counted'])))
 def pos_checkout(self):
  if not self.cart:raise ERPError('El carrito está vacío.')
  if not self.confirm('¿Confirmar el cobro? Se descontará el stock y se registrará la venta.'):return
  items=[{'product_id':pid,'qty':quantity(qty_milli)} for pid,qty_milli in self.cart.items()]
  id=self.erp.checkout(self.pos_branch.currentData(),items,self.pos_payment.currentData(),self.pos_customer.currentData())
  self.cart={}
  should_print=QMessageBox.question(self,'Venta registrada',f'Venta #{id} confirmada. ¿Querés imprimir ahora el ticket interno NO fiscal?',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes
  if should_print:self.print_ticket(id)
  self.reload()
 def pos_void(self):
  sid=self.selected()
  d=self.prompt(f'Anulación de venta #{sid}',[fld('reason','Motivo obligatorio','long')])
  if d is None:return
  if not self.confirm('¿Confirmar la anulación? Se reintegrarán existencias y se recalculará la caja si sigue abierta.'):return
  self.erp.void_sale(sid,d['reason']);self.reload();self.message('Venta anulada con movimiento de stock inverso.')
 def print_ticket(self,sale_id=None):
  if sale_id is None or isinstance(sale_id,bool):sale_id=self.selected()
  from .ticket_printer import TicketPrinterDialog
  text=self.erp.sale_ticket(sale_id)
  dlg=TicketPrinterDialog(self,text);dlg.exec()
 def ticket(self):
  id=self.selected();filename,_=QFileDialog.getSaveFileName(self,'Guardar ticket interno','','Texto (*.txt)')
  if filename:Path(filename).write_text(self.erp.sale_ticket(id),encoding='utf-8');self.message('Comprobante interno guardado (NO fiscal).')
 def popup_table(self,title,rows):
  dia=QDialog(self);dia.resize(850,520);dia.setWindowTitle(title);lay=QVBoxLayout(dia)
  label=QLabel(title);label.setObjectName('heading');lay.addWidget(label)
  t=table_widget(rows);lay.addWidget(t)
  b=QPushButton('Cerrar');b.clicked.connect(dia.accept);lay.addWidget(b);dia.exec()


# === F15 monkey patches: faster horizontal navigation, softer success dialog,
#     and richer Categories/Brands workspace with notes + brand photo ===
from pathlib import Path as _Path
import json as _json, uuid as _uuid
from PySide6.QtWidgets import QToolButton, QSplitter


def _f15_meta_path(self):
 return self.erp.root/'catalog_meta_f15.json'


def _f15_meta_load(self):
 path=_f15_meta_path(self)
 if not path.exists():
  return {'categories':{},'brands':{}}
 try:
  data=_json.loads(path.read_text(encoding='utf-8'))
  if not isinstance(data,dict): raise ValueError
 except Exception:
  return {'categories':{},'brands':{}}
 data.setdefault('categories',{})
 data.setdefault('brands',{})
 return data


def _f15_meta_save(self,data):
 path=_f15_meta_path(self)
 path.write_text(_json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')


def _f15_catalog_meta(self,entity,entity_id):
 data=_f15_meta_load(self)
 bucket=data.setdefault(entity,{})
 item=bucket.get(str(entity_id),{})
 if not isinstance(item,dict): item={}
 return {'notes':str(item.get('notes','')),'photo':str(item.get('photo',''))}


def _f15_set_catalog_meta(self,entity,entity_id,notes=None,photo=None):
 data=_f15_meta_load(self)
 bucket=data.setdefault(entity,{})
 item=bucket.setdefault(str(entity_id),{})
 if notes is not None: item['notes']=str(notes)
 if photo is not None: item['photo']=str(photo)
 _f15_meta_save(self,data)


def _f15_copy_visual(self,source):
 src=_Path(source)
 if not src.is_file() or src.stat().st_size>5*1024*1024:
  raise ERPError('Imagen inexistente o mayor a 5 MB.')
 content=src.read_bytes()
 if content.startswith(b'\x89PNG\r\n\x1a\n'): ext='.png'
 elif content.startswith(b'\xff\xd8\xff'): ext='.jpg'
 elif content.startswith(b'RIFF') and content[8:12]==b'WEBP': ext='.webp'
 else: raise ERPError('Solo se admiten PNG, JPG y WebP válidos.')
 dest=self.erp.root/'photos'/(_uuid.uuid4().hex+ext)
 dest.write_bytes(content)
 return dest.name


def _f15_scroll(self,direction=1):
 if not getattr(self,'table',None): return
 bar=self.table.horizontalScrollBar()
 step=max(180,bar.pageStep() or 180)
 bar.setValue(bar.value() + direction*step)


def _f15_table_shell(self,table):
 table.horizontalScrollBar().setSingleStep(80)
 table.horizontalScrollBar().setPageStep(220)
 wrap=QWidget()
 root=QVBoxLayout(wrap);root.setContentsMargins(0,0,0,0);root.setSpacing(6)
 root.addWidget(table,1)
 nav=QHBoxLayout();nav.setContentsMargins(0,0,0,0);nav.setSpacing(6)
 nav.addStretch(1)
 for glyph,tip,delta in [('◀','Mover tabla hacia la izquierda',-1),('▶','Mover tabla hacia la derecha',1)]:
  btn=QToolButton();btn.setObjectName('tableNudgeButton');btn.setText(glyph);btn.setToolTip(tip)
  btn.setAutoRepeat(True);btn.setAutoRepeatInterval(90);btn.setFixedSize(34,28)
  btn.clicked.connect(lambda checked=False,d=delta:_f15_scroll(self,d))
  nav.addWidget(btn)
 root.addLayout(nav)
 return wrap


def _f15_success_sound():
 try:
  import winsound
  for freq,dur in ((784,55),(988,70),(1175,85)):
   winsound.Beep(freq,dur)
 except Exception:
  pass


def _f15_message(self,txt='Operación completada correctamente.'):
 _f15_success_sound()
 dia=QDialog(self);dia.setWindowTitle('NexoMerc ERP');dia.setModal(True);dia.setMinimumWidth(430)
 lay=QVBoxLayout(dia);lay.setContentsMargins(22,18,22,18);lay.setSpacing(12)
 top=QHBoxLayout();top.setSpacing(12)
 icon=QLabel('i');icon.setObjectName('infoBubble');icon.setAlignment(Qt.AlignmentFlag.AlignCenter);icon.setFixedSize(44,44)
 top.addWidget(icon,0,Qt.AlignmentFlag.AlignTop)
 label=QLabel(self.text(txt));label.setWordWrap(True);top.addWidget(label,1)
 lay.addLayout(top)
 buttons=QHBoxLayout();buttons.addStretch(1)
 ok=QPushButton('OK');ok.setMinimumWidth(118);ok.clicked.connect(dia.accept);buttons.addWidget(ok)
 lay.addLayout(buttons)
 dia.exec()


def _f15_show_rows(self,rows,cols=None):
 self.rows=rows;self.table=table_widget(rows,cols)
 self.table.doubleClicked.connect(self.queue_edit)
 self.table.enterPressed.connect(self.queue_edit)
 self.table.itemSelectionChanged.connect(self._record_selection)
 self._restore_selection()
 self.outer.addWidget(_f15_table_shell(self,self.table),1)
 self.filter_table(self.search.text())


def _f15_catalog_load_side(self):
 if not getattr(self,'catalog_notes',None): return
 if not getattr(self,'table',None) or self.table.currentRow()<0:
  self.catalog_title.setText('📒 Libreta comercial')
  self.catalog_notes.blockSignals(True);self.catalog_notes.setPlainText('');self.catalog_notes.blockSignals(False)
  if getattr(self,'catalog_photo_box',None):
   self.catalog_photo_box.setVisible(self.mode=='brands')
   self.catalog_photo_label.setText('Sin foto de marca')
   self.catalog_photo_label.setPixmap(QPixmap())
  return
 rid=self.selected()
 entity='brands' if self.mode=='brands' else 'categories'
 row=self.erp.entity(entity,rid)
 meta=_f15_catalog_meta(self,entity,rid)
 self.catalog_title.setText(('📒 Libreta de marca' if entity=='brands' else '📒 Libreta de categoría')+f' · {row.get("name",rid)}')
 self.catalog_notes.blockSignals(True);self.catalog_notes.setPlainText(meta.get('notes',''));self.catalog_notes.blockSignals(False)
 if getattr(self,'catalog_photo_box',None):
  self.catalog_photo_box.setVisible(entity=='brands')
  if entity=='brands' and meta.get('photo'):
   pix=QPixmap(str(self.erp.root/'photos'/meta['photo']))
   if not pix.isNull():
    self.catalog_photo_label.setPixmap(pix.scaled(150,150,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
    self.catalog_photo_label.setText('')
   else:
    self.catalog_photo_label.setPixmap(QPixmap());self.catalog_photo_label.setText('Sin foto de marca')
  else:
   self.catalog_photo_label.setPixmap(QPixmap());self.catalog_photo_label.setText('Sin foto de marca')


def _f15_catalog_save_notes(self):
 rid=self.selected();entity='brands' if self.mode=='brands' else 'categories'
 _f15_set_catalog_meta(self,entity,rid,notes=self.catalog_notes.toPlainText().strip())
 self.message('Notas guardadas en la libreta del catálogo.')


def _f15_catalog_upload_photo(self):
 if self.mode!='brands':
  raise ERPError('La fotografía lateral está disponible para marcas.')
 rid=self.selected()
 name,_=QFileDialog.getOpenFileName(self,'Fotografía de la marca','','Imágenes (*.png *.jpg *.jpeg *.webp)')
 if not name: return
 filename=_f15_copy_visual(self,name)
 _f15_set_catalog_meta(self,'brands',rid,photo=filename)
 _f15_catalog_load_side(self)
 self.reload()


def _f15_catalog_remove_photo(self):
 if self.mode!='brands': return
 rid=self.selected();meta=_f15_catalog_meta(self,'brands',rid)
 photo=meta.get('photo','')
 if photo:
  try:(self.erp.root/'photos'/photo).unlink(missing_ok=True)
  except Exception: pass
 _f15_set_catalog_meta(self,'brands',rid,photo='')
 _f15_catalog_load_side(self);self.reload()


def _f15_catalog_switch(self,t):
 self.catalog_mode=t;self.reload()


def _f15_page_catalog(self):
 self.mode=getattr(self,'catalog_mode','categories')
 self.tool('Categorías',lambda:_f15_catalog_switch(self,'categories'))
 self.tool('Marcas',lambda:_f15_catalog_switch(self,'brands'))
 if self.erp.available('catalog','create'):self.tool('Nuevo registro',lambda:self.catalog_form(),True)
 if self.erp.available('catalog','edit'):self.tool('Editar',self.edit_current)
 if self.mode=='brands':
  photo_btn=QPushButton('Foto de marca');photo_btn.clicked.connect(lambda checked=False:self.safe(_f15_catalog_upload_photo.__get__(self,App)));self.tools.addWidget(photo_btn)
 self.tools.addStretch(1)

 self.search.setPlaceholderText('Buscar por nombre, código o cualquier dato visible…')
 rows=[]
 photos={}
 if self.mode=='categories':
  for r in self.erp.catalogs('categories'):
   meta=_f15_catalog_meta(self,'categories',r['id'])
   rows.append(dict(r,_notes=meta.get('notes','')))
  cols=['id','name','parent_id','active']
 else:
  for r in self.erp.catalogs('brands'):
   meta=_f15_catalog_meta(self,'brands',r['id'])
   rows.append(dict(r,photo_display='',_notes=meta.get('notes','')))
   if meta.get('photo'): photos[int(r['id'])]=meta['photo']
  cols=['id','photo_display','name','active']
 self.rows=rows;self.table=table_widget(rows,cols)
 self.table.doubleClicked.connect(self.queue_edit)
 self.table.enterPressed.connect(self.queue_edit)
 self.table.itemSelectionChanged.connect(self._record_selection)
 self.table.itemSelectionChanged.connect(lambda:_f15_catalog_load_side(self))
 self._restore_selection()
 hdr=self.table.horizontalHeader()
 hdr.setStretchLastSection(False)
 if self.mode=='categories':
  hdr.setSectionResizeMode(0,QHeaderView.ResizeMode.ResizeToContents)
  hdr.setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch)
  hdr.setSectionResizeMode(2,QHeaderView.ResizeMode.Stretch)
  hdr.setSectionResizeMode(3,QHeaderView.ResizeMode.Fixed);hdr.resizeSection(3,96)
 else:
  hdr.setSectionResizeMode(0,QHeaderView.ResizeMode.ResizeToContents)
  hdr.setSectionResizeMode(1,QHeaderView.ResizeMode.Fixed);hdr.resizeSection(1,84)
  hdr.setSectionResizeMode(2,QHeaderView.ResizeMode.Stretch)
  hdr.setSectionResizeMode(3,QHeaderView.ResizeMode.Fixed);hdr.resizeSection(3,96)
  self.center_photo_cells(photos)
 self.filter_table(self.search.text())

 split=QSplitter(Qt.Orientation.Horizontal)
 split.setChildrenCollapsible(False)
 left=_f15_table_shell(self,self.table)
 split.addWidget(left)
 card=QFrame();card.setObjectName('notebookPanel')
 side=QVBoxLayout(card);side.setContentsMargins(14,14,14,14);side.setSpacing(10)
 ribbon=QLabel('🧾  Recordatorios');ribbon.setObjectName('noteRibbon');side.addWidget(ribbon)
 self.catalog_title=QLabel('📒 Libreta comercial');self.catalog_title.setObjectName('kpi_title');self.catalog_title.setWordWrap(True);side.addWidget(self.catalog_title)
 helper=QLabel('Guardá observaciones útiles para compras, reposición o acuerdos internos.');helper.setObjectName('helper');helper.setWordWrap(True);side.addWidget(helper)
 self.catalog_photo_box=QFrame();phl=QVBoxLayout(self.catalog_photo_box);phl.setContentsMargins(0,0,0,0);phl.setSpacing(8)
 self.catalog_photo_label=QLabel('Sin foto de marca');self.catalog_photo_label.setObjectName('brandPhotoPreview');self.catalog_photo_label.setAlignment(Qt.AlignmentFlag.AlignCenter);self.catalog_photo_label.setFixedHeight(170)
 phl.addWidget(self.catalog_photo_label)
 row=QHBoxLayout();btn1=QPushButton('Cargar foto');btn1.clicked.connect(lambda checked=False:self.safe(_f15_catalog_upload_photo.__get__(self,App)));row.addWidget(btn1)
 btn2=QPushButton('Quitar');btn2.clicked.connect(lambda checked=False:self.safe(_f15_catalog_remove_photo.__get__(self,App)));row.addWidget(btn2)
 phl.addLayout(row);side.addWidget(self.catalog_photo_box)
 self.catalog_notes=QTextEdit();self.catalog_notes.setPlaceholderText('Ejemplo: marca local con entrega rápida, categoría que rota mucho, producto estacional, etc.');self.catalog_notes.setMinimumHeight(220);side.addWidget(self.catalog_notes,1)
 actions=QHBoxLayout();actions.addStretch(1)
 save=QPushButton('Guardar nota');save.clicked.connect(lambda checked=False:self.safe(_f15_catalog_save_notes.__get__(self,App)));actions.addWidget(save)
 side.addLayout(actions)
 split.addWidget(card)
 split.setStretchFactor(0,3);split.setStretchFactor(1,1)
 self.outer.addWidget(split,1)
 _f15_catalog_load_side(self)

App.message=_f15_message
App.show_rows=_f15_show_rows
App.page_catalog=_f15_page_catalog
App.catalog_switch=_f15_catalog_switch
App.catalog_meta=_f15_catalog_meta
App.catalog_save_notes=_f15_catalog_save_notes
App.catalog_load_side=_f15_catalog_load_side
App.catalog_upload_photo=_f15_catalog_upload_photo
App.catalog_remove_photo=_f15_catalog_remove_photo




# === F17 monkey patches: cashier-oriented POS workspace, softer dialog sound,
#     resizable product/cart area, and horizontal table nudges ===
LABELS.update({'qty_label':'Cantidad','price_label':'Unitario','line_total':'Subtotal'})

def _f17_success_sound():
 try:
  import winsound
  for freq,dur in ((446,42),(446,58)):
   winsound.Beep(freq,dur)
 except Exception:
  pass


def _f17_message(self,txt='Operación completada correctamente.'):
 _f17_success_sound()
 dia=QDialog(self);dia.setWindowTitle('NexoMerc ERP');dia.setModal(True);dia.setMinimumWidth(450)
 lay=QVBoxLayout(dia);lay.setContentsMargins(22,18,22,18);lay.setSpacing(12)
 top=QHBoxLayout();top.setSpacing(12)
 icon=QLabel('i');icon.setObjectName('infoBubble');icon.setAlignment(Qt.AlignmentFlag.AlignCenter);icon.setFixedSize(44,44)
 top.addWidget(icon,0,Qt.AlignmentFlag.AlignTop)
 label=QLabel(self.text(txt));label.setWordWrap(True);top.addWidget(label,1)
 lay.addLayout(top)
 buttons=QHBoxLayout();buttons.addStretch(1)
 ok=QPushButton('OK');ok.setMinimumWidth(118);ok.clicked.connect(dia.accept);buttons.addWidget(ok)
 lay.addLayout(buttons)
 dia.exec()


def _f17_photo_filename(self,pid):
 try:
  return (self.erp.entity('products',pid) or {}).get('photo','')
 except Exception:
  return ''


def _f17_center_photo_table(self,table,photos,col=1,size=46):
 table.setIconSize(QSize(size,size))
 header=table.horizontalHeader()
 header.setSectionResizeMode(col,QHeaderView.ResizeMode.Fixed)
 header.resizeSection(col,max(82,size+26))
 for row in range(table.rowCount()):
  first=table.item(row,0)
  if first is None: continue
  try:
   key=int(first.text())
  except Exception:
   key=first.data(Qt.ItemDataRole.UserRole)
  photo=photos.get(int(key)) if key is not None and str(key).isdigit() else None
  label=QLabel();label.setAlignment(Qt.AlignmentFlag.AlignCenter)
  label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents,True)
  label.setStyleSheet('background:transparent;border:0;padding:0;margin:0;')
  if photo:
   pix=QPixmap(str(self.erp.root/'photos'/photo))
   if not pix.isNull():
    label.setPixmap(pix.scaled(size,size,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
   else:
    label.setText('—')
  else:
   label.setText('—')
  item=table.item(row,col)
  if item is not None:
   item.setText('')
   item.setIcon(QIcon())
  table.setCellWidget(row,col,label)
  table.setRowHeight(row,max(60,size+14))


def _f17_filter_aux_table(table,text):
 needle=(text or '').strip().lower()
 for row in range(table.rowCount()):
  visible=(needle=='')
  if not visible:
   for col in range(table.columnCount()):
    item=table.item(row,col)
    if item and needle in item.text().lower():
     visible=True; break
  table.setRowHidden(row,not visible)


def _f17_build_catalog_rows(self):
 bid=self.pos_branch.currentData() if hasattr(self,'pos_branch') else None
 rows=[];photos={}
 for p in self.erp.catalogs('products',include_archived=False):
  if not p.get('active',1):
   continue
  price=self.erp.effective_price(p['id'],bid) if bid else p['price_cents']
  bal=self.erp.one('SELECT COALESCE(onhand_milli,0)-COALESCE(reserved_milli,0) AS available FROM stock_balances WHERE product_id=? AND branch_id=?',(p['id'],bid)) if bid else None
  available=int(bal['available']) if bal else 0
  rows.append({'id':p['id'],'photo_display':'','sku':p.get('sku',''),'name':p.get('name',''),'price_cents':price,'available_display':quantity(available)+' '+p.get('unit','u')})
  if p.get('photo'): photos[int(p['id'])]=p.get('photo')
 return rows,photos




def _f17_table_shell(table):
 table.horizontalScrollBar().setSingleStep(80)
 table.horizontalScrollBar().setPageStep(220)
 wrap=QWidget()
 root=QVBoxLayout(wrap);root.setContentsMargins(0,0,0,0);root.setSpacing(6)
 root.addWidget(table,1)
 nav=QHBoxLayout();nav.setContentsMargins(0,0,0,0);nav.setSpacing(6)
 nav.addStretch(1)
 for glyph,tip,delta in [('◀','Mover tabla hacia la izquierda',-1),('▶','Mover tabla hacia la derecha',1)]:
  btn=QToolButton();btn.setObjectName('tableNudgeButton');btn.setText(glyph);btn.setToolTip(tip)
  btn.setAutoRepeat(True);btn.setAutoRepeatInterval(90);btn.setFixedSize(34,28)
  btn.clicked.connect(lambda checked=False,d=delta,t=table: t.horizontalScrollBar().setValue(t.horizontalScrollBar().value()+d*max(180,t.horizontalScrollBar().pageStep() or 180)))
  nav.addWidget(btn)
 root.addLayout(nav)
 return wrap

def _f17_fill_catalog(self):
 if not hasattr(self,'pos_catalog'): return
 rows,photos=_f17_build_catalog_rows(self)
 self.pos_catalog.setRowCount(0)
 for row in rows:
  r=self.pos_catalog.rowCount();self.pos_catalog.insertRow(r)
  values=[row['id'],row['photo_display'],row['sku'],row['name'],money(row['price_cents']),row['available_display']]
  for c,val in enumerate(values):
   item=QTableWidgetItem(str(val))
   if c==0:
    item.setData(Qt.ItemDataRole.UserRole,row['id'])
   self.pos_catalog.setItem(r,c,item)
 _f17_center_photo_table(self,self.pos_catalog,photos)
 _f17_filter_aux_table(self.pos_catalog,self.pos_catalog_search.text() if hasattr(self,'pos_catalog_search') else '')


def _f17_pick_catalog(self):
 if not hasattr(self,'pos_catalog') or self.pos_catalog.currentRow()<0: return
 item=self.pos_catalog.item(self.pos_catalog.currentRow(),0)
 if item is None: return
 try:
  pid=int(item.text())
 except Exception:
  return
 idx=self.pos_product.findData(pid)
 if idx>=0:
  self.pos_product.setCurrentIndex(idx)
  self.pos_qty.setFocus()


def _f17_sync_catalog_selection(self,*_):
 pid=self.pos_product.currentData()
 if not hasattr(self,'pos_catalog') or pid is None: return
 for row in range(self.pos_catalog.rowCount()):
  item=self.pos_catalog.item(row,0)
  if item and item.text()==str(pid):
   self.pos_catalog.blockSignals(True)
   self.pos_catalog.setCurrentCell(row,0)
   self.pos_catalog.blockSignals(False)
   break
 _f17_update_preview(self)


def _f17_update_preview(self,*_):
 if not hasattr(self,'pos_preview_title'): return
 pid=self.pos_product.currentData()
 if not pid:
  self.pos_preview_title.setText('Sin producto seleccionado')
  self.pos_preview_meta.setText('Elegí un producto del catálogo rápido o escaneá un código.')
  self.pos_preview_price.setText('—')
  self.pos_preview_photo.setPixmap(QPixmap())
  self.pos_preview_photo.setText('Sin foto')
  return
 p=self.erp.entity('products',pid)
 bid=self.pos_branch.currentData()
 bal=self.erp.one('SELECT COALESCE(onhand_milli,0)-COALESCE(reserved_milli,0) AS available FROM stock_balances WHERE product_id=? AND branch_id=?',(pid,bid)) if bid else None
 available=int(bal['available']) if bal else 0
 price=self.erp.effective_price(pid,bid) if bid else p['price_cents']
 self.pos_preview_title.setText(p.get('name','Producto'))
 unit={'u':'unidad','kg':'kg','l':'l'}.get(p.get('unit','u'),p.get('unit','u'))
 self.pos_preview_meta.setText(f'SKU: {p.get("sku","")} · Disponible: {quantity(available)} {unit}')
 self.pos_preview_price.setText(self._money(price))
 photo=p.get('photo','')
 if photo:
  pix=QPixmap(str(self.erp.root/'photos'/photo))
  if not pix.isNull():
   self.pos_preview_photo.setPixmap(pix.scaled(126,126,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
   self.pos_preview_photo.setText('')
   return
 self.pos_preview_photo.setPixmap(QPixmap())
 self.pos_preview_photo.setText('Sin foto')


def _f17_render_cart(self):
 bid=self.pos_branch.currentData() if hasattr(self,'pos_branch') else None
 if not hasattr(self,'pos_cart'): return
 self.pos_cart.setRowCount(0);total=0;photos={}
 for pid,qty_milli in self.cart.items():
  p=self.erp.entity('products',pid);price=self.erp.effective_price(pid,bid);sub=total_for(qty_milli,price);total+=sub
  r=self.pos_cart.rowCount();self.pos_cart.insertRow(r)
  photo=p.get('photo','')
  if photo: photos[int(pid)]=photo
  values=[pid,'',p['name'],quantity(qty_milli)+' '+p['unit'],money(price),money(sub)]
  for c,val in enumerate(values):
   item=QTableWidgetItem(str(val))
   if c==0:item.setData(Qt.ItemDataRole.UserRole,pid)
   self.pos_cart.setItem(r,c,item)
 _f17_center_photo_table(self,self.pos_cart,photos)
 self.pos_total.setText(self.text('Total')+': '+self._money(total))
 if hasattr(self,'pos_cart_title'):
  self.pos_cart_title.setText(f'Carrito actual · {len(self.cart)} producto(s)')
 if hasattr(self,'pos_empty_hint'):
  self.pos_empty_hint.setVisible(self.pos_cart.rowCount()==0)


def _f17_pos_refresh(self):
 bid=self.pos_branch.currentData() if hasattr(self,'pos_branch') else None
 if not bid:return
 sess=self.erp.cash_session(bid)
 if hasattr(self,'pos_status'):
  self.pos_status.setText((f'{self.text("Caja actual: ABIERTA")} #{sess["id"]} · {self.text("Apertura")} {self._money(sess["opening_cents"])}') if sess else self.text('Caja actual: CERRADA · Debe abrirla antes de cobrar'))
 _f17_fill_catalog(self)
 _f17_render_cart(self)
 _f17_update_preview(self)


def _f17_toggle_history(self):
 visible=not self.pos_history_body.isVisible()
 self.pos_history_body.setVisible(visible)
 self.pos_history_toggle.setText('▾ Historial reciente' if visible else '▸ Historial reciente')
 if hasattr(self,'pos_vertical_splitter'):
  self.pos_vertical_splitter.setSizes([720,260 if visible else 1])


def _f17_pos_history_rows(self):
 rows=[]
 for sale in self.erp.list_simple('sales'):
  row=dict(sale)
  row['payment']={'cash':'Efectivo','debit':'Débito','credit':'Crédito','transfer':'Transferencia','qr':'QR','check':'Cheque'}.get(row.get('payment'),row.get('payment'))
  row['status']={'completed':'Completada','void':'Anulada','pending':'Pendiente'}.get(row.get('status'),row.get('status'))
  bid=row.get('branch_id')
  row['branch']=next((label for label,id in self.branch_opts() if id==bid), str(bid))
  rows.append(row)
 return rows


def _f17_page_pos(self):
 self.search.hide()
 head=QHBoxLayout();head.addWidget(QLabel('Sucursal de venta:'))
 self.pos_branch=QComboBox()
 for label,id in self.branch_opts(): self.pos_branch.addItem(label,id)
 self.pos_branch.currentIndexChanged.connect(lambda:self.safe(_f17_pos_refresh.__get__(self,App)))
 head.addWidget(self.pos_branch)
 head.addSpacing(10)
 self.pos_status=QLabel('');self.pos_status.setObjectName('helper');head.addWidget(self.pos_status,1)
 head.addStretch(1)
 if self.erp.available('pos','cash'):
  head.addWidget(action(self,'Abrir caja',self.pos_open))
  head.addWidget(action(self,'Cerrar caja / arqueo',self.pos_close))
 self.outer.addLayout(head)

 self.pos_vertical_splitter=QSplitter(Qt.Orientation.Vertical)
 self.pos_vertical_splitter.setChildrenCollapsible(False)
 workspace=QWidget();workspace_l=QHBoxLayout(workspace);workspace_l.setContentsMargins(0,0,0,0);workspace_l.setSpacing(12)
 panes=QSplitter(Qt.Orientation.Horizontal);panes.setChildrenCollapsible(False)
 workspace_l.addWidget(panes)

 # Left: catalog + scanner
 left=QFrame();left.setObjectName('posCatalogCard');ll=QVBoxLayout(left);ll.setContentsMargins(14,14,14,14);ll.setSpacing(10)
 cap=QLabel('Terminal de venta');cap.setObjectName('kpi_title');ll.addWidget(cap)
 self.pos_barcode=QLineEdit();self.pos_barcode.setPlaceholderText('▥   ESCANEAR O PEGAR CÓDIGO DE BARRAS + ENTER');self.pos_barcode.setMinimumHeight(50);self.pos_barcode.returnPressed.connect(lambda:self.safe(self.pos_scan))
 scan=QHBoxLayout();scan.addWidget(self.pos_barcode,1);scan.addWidget(action(self,'Escanear / Probar lector',self.pos_capture));ll.addLayout(scan)
 helper=QLabel('También podés buscar por nombre, elegir presentación y agregar al carrito como en una app de caja.');helper.setObjectName('helper');helper.setWordWrap(True);ll.addWidget(helper)
 self.pos_product=QComboBox();self.pos_product.setEditable(True)
 for p in self.erp.catalogs('products'):
  if p.get('active'): self.pos_product.addItem(f'{p.get("sku","")} · {p.get("name","")} | {self._money(p.get("price_cents",0))}',p['id'])
 self.pos_product.currentIndexChanged.connect(self.pos_update_presentation)
 self.pos_product.currentIndexChanged.connect(lambda *_:_f17_sync_catalog_selection(self))
 self.pos_presentation=QComboBox();self.pos_presentation.setMinimumWidth(180);self.pos_presentation.currentIndexChanged.connect(self.pos_update_sale_hint)
 self.pos_qty=QuantitySpinBox();self.pos_qty.setRange(.001,999999);self.pos_qty.setDecimals(3);self.pos_qty.setValue(1);self.pos_qty.valueChanged.connect(self.pos_update_sale_hint)
 top_sel=QHBoxLayout();top_sel.addWidget(self.pos_product,4);top_sel.addWidget(QLabel('Venta por'));top_sel.addWidget(self.pos_presentation,2);top_sel.addWidget(QLabel('Cant.'));top_sel.addWidget(self.pos_qty,1);top_sel.addWidget(action(self,'Añadir producto',self.pos_add,True));ll.addLayout(top_sel)

 preview=QFrame();preview.setObjectName('posPreviewCard');pv=QHBoxLayout(preview);pv.setContentsMargins(12,12,12,12);pv.setSpacing(12)
 self.pos_preview_photo=QLabel('Sin foto');self.pos_preview_photo.setObjectName('posPreviewPhoto');self.pos_preview_photo.setAlignment(Qt.AlignmentFlag.AlignCenter);self.pos_preview_photo.setFixedSize(138,138);pv.addWidget(self.pos_preview_photo)
 inf=QVBoxLayout();self.pos_preview_title=QLabel('Sin producto seleccionado');self.pos_preview_title.setObjectName('heading');self.pos_preview_title.setStyleSheet('font-size:18px;');inf.addWidget(self.pos_preview_title)
 self.pos_preview_meta=QLabel('Elegí un producto del catálogo rápido o escaneá un código.');self.pos_preview_meta.setObjectName('helper');self.pos_preview_meta.setWordWrap(True);inf.addWidget(self.pos_preview_meta)
 self.pos_preview_price=QLabel('—');self.pos_preview_price.setObjectName('posBigTotal');inf.addWidget(self.pos_preview_price)
 self.pos_sale_hint=QLabel('');self.pos_sale_hint.setObjectName('helper');self.pos_sale_hint.setWordWrap(True);inf.addWidget(self.pos_sale_hint)
 inf.addStretch(1);pv.addLayout(inf,1);ll.addWidget(preview)

 cat_title=QHBoxLayout();title=QLabel('Catálogo rápido con fotos');title.setObjectName('kpi_title');cat_title.addWidget(title);cat_title.addStretch(1);ll.addLayout(cat_title)
 self.pos_catalog_search=QLineEdit();self.pos_catalog_search.setPlaceholderText('Buscar producto dentro de caja…');self.pos_catalog_search.textChanged.connect(lambda text:_f17_filter_aux_table(self.pos_catalog,text));ll.addWidget(self.pos_catalog_search)
 self.pos_catalog=table_widget([],['id','photo_display','sku','name','price_cents','available_display']);self.pos_catalog.setObjectName('posCatalogTable')
 self.pos_catalog.doubleClicked.connect(lambda *_: self.safe(_f17_pick_catalog.__get__(self,App)))
 self.pos_catalog.itemSelectionChanged.connect(lambda:_f17_pick_catalog(self))
 ll.addWidget(_f17_table_shell(self.pos_catalog),1)
 panes.addWidget(left)

 # Right: cart + charge controls
 right=QFrame();right.setObjectName('posCartCard');rl=QVBoxLayout(right);rl.setContentsMargins(14,14,14,14);rl.setSpacing(10)
 self.pos_cart_title=QLabel('Carrito actual · 0 producto(s)');self.pos_cart_title.setObjectName('kpi_title');rl.addWidget(self.pos_cart_title)
 self.pos_cart=table_widget([],['id','photo_display','name','qty_label','price_label','line_total']);self.pos_cart.setObjectName('posCartTable')
 self.pos_empty_hint=QLabel('El carrito está vacío. Escaneá un código, elegí un producto o hacé doble clic en el catálogo.');self.pos_empty_hint.setObjectName('helper');self.pos_empty_hint.setWordWrap(True)
 rl.addWidget(self.pos_empty_hint)
 rl.addWidget(_f17_table_shell(self.pos_cart),1)
 actions=QHBoxLayout();actions.addWidget(action(self,'Quitar del carrito',self.pos_remove));actions.addStretch(1);actions.addWidget(QLabel('Cliente'))
 self.pos_customer=QComboBox();self.pos_customer.addItem('Consumidor final',None)
 for name,id in combo_data(self.erp,'customers'): self.pos_customer.addItem(name,id)
 actions.addWidget(self.pos_customer);actions.addWidget(QLabel('Pago'))
 self.pos_payment=QComboBox()
 for k,label in [('cash','Efectivo'),('debit','Débito'),('credit','Crédito'),('transfer','Transferencia'),('qr','QR'),('check','Cheque')]: self.pos_payment.addItem(label,k)
 actions.addWidget(self.pos_payment);rl.addLayout(actions)
 summary=QFrame();summary.setObjectName('pospanel');sl=QHBoxLayout(summary);sl.setContentsMargins(16,12,16,12)
 col=QVBoxLayout();lab=QLabel('TOTAL A COBRAR');lab.setObjectName('kpi_title');col.addWidget(lab);self.pos_total=QLabel(self.text('Total')+': '+self._money(0));self.pos_total.setObjectName('posBigTotal');col.addWidget(self.pos_total);sl.addLayout(col,1)
 btns=QVBoxLayout();row1=QHBoxLayout();row1.addWidget(action(self,self.text('Imprimir ticket'),self.print_ticket));row1.addWidget(action(self,self.text('Exportar ticket'),self.ticket));btns.addLayout(row1)
 row2=QHBoxLayout();
 if self.erp.available('pos','void'): row2.addWidget(action(self,'Anular venta',self.pos_void,danger=True))
 if self.erp.available('pos','sell'): row2.addWidget(action(self,'COBRAR',self.pos_checkout,True))
 btns.addLayout(row2);sl.addLayout(btns)
 rl.addWidget(summary)
 note=QLabel('Los precios se expresan por unidad base (unidad, kg o litro). Si vendés por caja o paquete, la cantidad cargada se multiplica por el contenido configurado del producto.');note.setObjectName('helper');note.setWordWrap(True);rl.addWidget(note)
 panes.addWidget(right)
 panes.setStretchFactor(0,5);panes.setStretchFactor(1,4)
 self.pos_vertical_splitter.addWidget(workspace)

 # History section
 history=QFrame();history.setObjectName('historyCard');hl=QVBoxLayout(history);hl.setContentsMargins(12,12,12,12);hl.setSpacing(8)
 head2=QHBoxLayout();self.pos_history_toggle=QToolButton();self.pos_history_toggle.setObjectName('historyToggle');self.pos_history_toggle.setText('▾ Historial reciente');self.pos_history_toggle.clicked.connect(lambda checked=False:_f17_toggle_history(self));head2.addWidget(self.pos_history_toggle)
 head2.addStretch(1)
 head2.addWidget(QLabel('Seleccioná una venta para imprimir o exportar el ticket interno.'))
 hl.addLayout(head2)
 self.pos_history_body=QWidget();body_l=QVBoxLayout(self.pos_history_body);body_l.setContentsMargins(0,0,0,0);body_l.setSpacing(6)
 self.rows=_f17_pos_history_rows(self);self.table=table_widget(self.rows,['id','created_at','branch','total_cents','payment','status']);self.table.setObjectName('posRecentTable')
 body_l.addWidget(_f17_table_shell(self.table),1)
 self.pos_history_body.setVisible(True);hl.addWidget(self.pos_history_body,1)
 self.pos_vertical_splitter.addWidget(history)
 self.pos_vertical_splitter.setStretchFactor(0,5);self.pos_vertical_splitter.setStretchFactor(1,2)
 self.outer.addWidget(self.pos_vertical_splitter,1)

 self.pos_update_presentation()
 _f17_pos_refresh(self)
 self.pos_barcode.setFocus()
 self.pos_vertical_splitter.setSizes([760,260])

App.message=_f17_message
App.page_pos=_f17_page_pos
App.render_cart=_f17_render_cart
App.pos_refresh=_f17_pos_refresh



# === F18: Lightweight POS, soft melody, collapsible navigation and note bubbles ===
from PySide6.QtWidgets import QToolButton
from PySide6.QtCore import QUrl, QSettings

_F18_ICON_CACHE={}
def _f18_nav_icon(self,key,active=False):
 # Cache SVG decoding; refresh active state without rereading the asset from disk.
 code='shop' if active else str(self.assets/'icons'/f'{key}.svg')
 if code not in _F18_ICON_CACHE:
  _F18_ICON_CACHE[code]=shop_icon() if active else QIcon(code)
 return _F18_ICON_CACHE[code]

def _f18_pixmap(self, filename, size):
    """
    Carga y escala una fotografía de producto.

    Acepta:
    - int: tamaño cuadrado, por ejemplo 48
    - QSize: ancho y alto específicos, por ejemplo QSize(48, 48)

    Centraliza el escalado de imágenes para evitar incompatibilidades
    entre las distintas pantallas de NexoMerc.
    """

    if not filename:
        return QPixmap()

    path = self.erp.root / 'photos' / filename

    try:
        stamp = path.stat().st_mtime_ns
    except OSError:
        return QPixmap()

    # Normalizar siempre el tamaño a QSize.
    if isinstance(size, QSize):
        target_size = QSize(size.width(), size.height())
    else:
        try:
            side = int(size)
        except (TypeError, ValueError):
            side = 38

        target_size = QSize(side, side)

    if target_size.width() <= 0 or target_size.height() <= 0:
        return QPixmap()

    cache = getattr(self, '_f18_pixmaps', None)

    if cache is None:
        cache = {}
        self._f18_pixmaps = cache

    # La clave usa números simples en lugar del objeto QSize.
    key = (
        str(path),
        stamp,
        target_size.width(),
        target_size.height(),
    )

    if key in cache:
        return cache[key]

    pix = QPixmap(str(path))

    if pix.isNull():
        scaled = QPixmap()
    else:
        scaled = pix.scaled(
            target_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

    if len(cache) > 300:
        cache.clear()

    cache[key] = scaled
    return scaled

def _f18_center_photo_table(self,table,photos,col=1,size=38):
 hdr=table.horizontalHeader()
 hdr.setSectionResizeMode(col,QHeaderView.ResizeMode.Fixed);hdr.resizeSection(col,size+16)
 for row in range(table.rowCount()):
  first=table.item(row,0)
  if first is None: continue
  try:pid=int(first.text())
  except (ValueError,TypeError):pid=None
  pic=photos.get(pid)
  label=QLabel();label.setAlignment(Qt.AlignmentFlag.AlignCenter)
  label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents,True)
  label.setStyleSheet('background:transparent;border:0;padding:0;margin:0;')
  pix=_f18_pixmap(self,pic,size) if pic else QPixmap()
  if not pix.isNull(): label.setPixmap(pix)
  else:label.setText('—')
  table.setCellWidget(row,col,label)
  table.setRowHeight(row,size+10)

def _f18_catalog_rows(self):
 bid=self.pos_branch.currentData() if hasattr(self,'pos_branch') else None
 balances={}
 if bid:
  for b in self.erp.all('SELECT product_id,onhand_milli,reserved_milli FROM stock_balances WHERE branch_id=?',(bid,)):
   balances[b['product_id']]=int(b['onhand_milli'])-int(b['reserved_milli'])
 rows=[];photos={}
 for p in self.erp.catalogs('products',include_archived=False):
  if not p.get('active',1):continue
  pid=p['id'];price=self.erp.effective_price(pid,bid) if bid else p['price_cents']
  rows.append({'id':pid,'photo_display':'','sku':p.get('sku',''),'name':p.get('name',''),
               'price_cents':price,'available_display':quantity(balances.get(pid,0))+' '+p.get('unit','u')})
  if p.get('photo'):photos[pid]=p['photo']
 return rows,photos

def _f18_melody(self):
 if str(QSettings('NexoMerc','ERP').value('f18_sound','soft')).lower()=='off':return
 try:
  from PySide6.QtMultimedia import QSoundEffect
  effect=getattr(self,'_f18_audio',None)
  if effect is None:
   effect=QSoundEffect(self)
   path=Path(__file__).resolve().parent.parent/'assets'/'audio'/'soft_confirm_f18.wav'
   effect.setSource(QUrl.fromLocalFile(str(path)))
   effect.setLoopCount(1);effect.setVolume(0.14)
   self._f18_audio=effect
  if effect.isLoaded():effect.play()
  # If Multimedia/audio device is unavailable, remain silent rather than beep.
 except Exception:pass

def _f18_message(self,txt='Operación completada correctamente.'):
 _f18_melody(self)
 dialog=QDialog(self);dialog.setWindowTitle('NexoMerc ERP');dialog.setModal(True);dialog.setMinimumWidth(420)
 layout=QVBoxLayout(dialog);layout.setContentsMargins(22,18,22,18);layout.setSpacing(12)
 line=QHBoxLayout();line.setSpacing(12)
 badge=QLabel('✓');badge.setObjectName('infoBubble');badge.setAlignment(Qt.AlignmentFlag.AlignCenter);badge.setFixedSize(42,42)
 line.addWidget(badge,0,Qt.AlignmentFlag.AlignTop)
 message=QLabel(self.text(txt));message.setWordWrap(True);line.addWidget(message,1);layout.addLayout(line)
 controls=QHBoxLayout();controls.addStretch(1)
 mute=QPushButton('Silenciar avisos' if QSettings('NexoMerc','ERP').value('f18_sound','soft')!='off' else 'Activar melodía')
 def toggle_sound():
  prefs=QSettings('NexoMerc','ERP')
  on=prefs.value('f18_sound','soft')!='off'
  prefs.setValue('f18_sound','off' if on else 'soft')
  mute.setText('Activar melodía' if on else 'Silenciar avisos')
 mute.clicked.connect(toggle_sound);controls.addWidget(mute)
 ok=QPushButton('Aceptar');ok.clicked.connect(dialog.accept);controls.addWidget(ok)
 layout.addLayout(controls);dialog.exec()

def _f18_side_button(self):
 if getattr(self,'_f18_nav_control',None):return
 side=self.findChild(QFrame,'sidebar')
 if side is None:return
 self._f18_sidebar=side
 btn=QToolButton(self);btn.setObjectName('f18NavButton')
 def toggle():
  side.setVisible(not side.isVisible())
  btn.setText('☰ Mostrar menú' if not side.isVisible() else '◀ Ocultar menú')
 btn.setText('◀ Ocultar menú');btn.clicked.connect(toggle)
 self.statusBar().addPermanentWidget(btn)
 self._f18_nav_control=btn

def _f18_note_data(self):
 path=self.erp.root/'catalog_meta_f15.json'
 try:
  stamp=path.stat().st_mtime_ns
 except OSError:stamp=None
 if getattr(self,'_f18_note_stamp','_')==stamp:return getattr(self,'_f18_note_cache',{})
 try:
  data=json.loads(path.read_text(encoding='utf-8')) if stamp else {}
  if not isinstance(data,dict):data={}
 except (OSError,ValueError):data={}
 self._f18_note_stamp=stamp;self._f18_note_cache=data
 return data

def _f18_show_note_bubbles(self):
 self.erp.check('catalog')
 data=_f18_note_data(self);dlg=QDialog(self);dlg.setWindowTitle('Libretas comerciales · NexoMerc ERP')
 dlg.setMinimumSize(520,420);dlg.resize(650,560)
 root=QVBoxLayout(dlg);root.setContentsMargins(18,18,18,18)
 title=QLabel('💬  Anotaciones de categorías y marcas');title.setObjectName('heading');root.addWidget(title)
 helper=QLabel('Recordatorios guardados. Podés editarlos desde Categorías y marcas.');helper.setObjectName('helper');root.addWidget(helper)
 search=QLineEdit();search.setPlaceholderText('Buscar dentro de mis notas…');root.addWidget(search)
 scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setObjectName('f18NoteScroll')
 body=QWidget();v=QVBoxLayout(body);v.setContentsMargins(8,8,8,8);v.setSpacing(10)
 cards=[]
 for table,label in (('categories','Categoría'),('brands','Marca')):
  names={str(x['id']):x['name'] for x in self.erp.catalogs(table)}
  for rid,item in sorted(data.get(table,{}).items(),key=lambda kv:str(kv[0])):
   if not isinstance(item,dict) or not str(item.get('notes','')).strip():continue
   box=QFrame();box.setObjectName('f18NoteBubble')
   vl=QVBoxLayout(box);vl.setContentsMargins(16,12,16,12);vl.setSpacing(6)
   head=QLabel(f'{label} · {names.get(str(rid),"Registro #"+str(rid))}');head.setObjectName('kpi_title');vl.addWidget(head)
   note=QLabel(str(item['notes']));note.setWordWrap(True);note.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse);vl.addWidget(note)
   v.addWidget(box);cards.append((box,(head.text()+' '+note.text()).casefold()))
 if not cards:
  label=QLabel('Todavía no hay anotaciones guardadas. Escribí una nota en Categorías y marcas para verla aquí.');label.setWordWrap(True);v.addWidget(label)
 v.addStretch(1);scroll.setWidget(body);root.addWidget(scroll,1)
 search.textChanged.connect(lambda query:[box.setVisible(query.casefold() in text) for box,text in cards])
 close=QPushButton('Cerrar');close.clicked.connect(dlg.accept);root.addWidget(close)
 dlg.exec()

def _f18_catalog_page(self):
 _f18_original_catalog(self)
 self.tools.addWidget(action(self,'💬 Ver anotaciones',lambda:_f18_show_note_bubbles(self)))

def _f18_make_pos_compact(self):
 # Reuse the F17 transactional workflow, but turn its two-pane layout into a
 # single spacious catalog by default. The cart can be shown with one click.
 _f17_page_pos(self)
 # F17's monumental hero and its minimum sizes were causing viewport clipping.
 hero=self.content.widget().findChild(QFrame,'banner')
 if hero: hero.hide()
 self.outer.setContentsMargins(12,10,12,12);self.outer.setSpacing(9)
 self.content.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
 self.pos_preview_photo.setFixedSize(92,92)
 self.pos_preview_title.setStyleSheet('font-size:16px;font-weight:800;')
 # Restrict minimum widths for controls with long product strings.
 self.pos_product.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
 self.pos_product.setMinimumContentsLength(9)
 self.pos_product.setMinimumWidth(100)
 self.pos_presentation.setMinimumWidth(105)
 self.pos_qty.setMaximumWidth(100)
 self.pos_catalog.setMinimumWidth(0);self.pos_cart.setMinimumWidth(0)
 self.pos_catalog.horizontalHeader().setStretchLastSection(False)
 self.pos_catalog.setColumnHidden(2,True) # SKU remains searchable, not redundant in fast visual mode
 h=self.pos_catalog.horizontalHeader()
 h.setSectionResizeMode(0,QHeaderView.ResizeMode.Fixed);h.resizeSection(0,48)
 h.setSectionResizeMode(3,QHeaderView.ResizeMode.Stretch)
 for col,width in ((4,100),(5,86)):
  h.setSectionResizeMode(col,QHeaderView.ResizeMode.Fixed);h.resizeSection(col,width)
 self.pos_cart.setColumnHidden(0,True)
 hc=self.pos_cart.horizontalHeader();hc.setStretchLastSection(False)
 hc.setSectionResizeMode(2,QHeaderView.ResizeMode.Stretch)
 for col,width in ((3,85),(4,90),(5,105)):
  hc.setSectionResizeMode(col,QHeaderView.ResizeMode.Fixed);hc.resizeSection(col,width)
 # POS is a workstation, so start with history closed and a large product list.
 self.pos_history_body.hide();self.pos_history_toggle.setText('▸ Historial reciente')
 self.pos_vertical_splitter.setSizes([1000,55])
 self._f18_panels=self.pos_vertical_splitter.widget(0).findChild(QSplitter)
 if self._f18_panels:
  self._f18_catalog_panel=self._f18_panels.widget(0)
  self._f18_cart_panel=self._f18_panels.widget(1)
  self._f18_cart_panel.hide()
  self._f18_panels.setSizes([980,1])
 top=QHBoxLayout();top.setSpacing(7)
 def button(text,callback,primary=False):
  b=QPushButton(text)
  if primary:b.setObjectName('primary')
  b.clicked.connect(callback);top.addWidget(b)
  return b
 self._f18_cart_btn=button('🛒 Mostrar carrito / cobrar',lambda:_f18_toggle_cart(self),True)
 button('☰ Mostrar / ocultar menú',lambda:self._f18_nav_control.click())
 if self.erp.available('catalog'):button('💬 Ver anotaciones',lambda:self.safe(lambda:_f18_show_note_bubbles(self)))
 top.addStretch(1)
 self.outer.insertLayout(0,top)
 self.pos_barcode.setFocus()

def _f18_toggle_cart(self):
 if not getattr(self,'_f18_cart_panel',None):return
 visible=not self._f18_cart_panel.isVisible()
 self._f18_cart_panel.setVisible(visible)
 if visible:
  self._f18_panels.setOrientation(Qt.Orientation.Vertical)
  self._f18_panels.setSizes([560,300])
  self._f18_cart_btn.setText('◀ Ampliar catálogo')
 else:
  self._f18_panels.setOrientation(Qt.Orientation.Horizontal)
  self._f18_panels.setSizes([1080,1])
  self._f18_cart_btn.setText('🛒 Mostrar carrito / cobrar')
 self.pos_barcode.setFocus()

_F18_ORIGINAL_INIT=App.__init__
def _f18_init(self,*args,**kwargs):
 _F18_ORIGINAL_INIT(self,*args,**kwargs)
 self.setWindowTitle('NexoMerc ERP · V2-F18')
 _f18_side_button(self)

_F18_ORIGINAL_OPEN=App.open_module
def _f18_open_module(self,mod):
 previous=getattr(self,'module',None)
 if previous=='pos' and mod!='pos':
  self.content.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
 return _F18_ORIGINAL_OPEN(self,mod)

# Cache note metadata within a screen; writing a note refreshes the file mtime.
if '_f15_meta_load' in globals():_f15_meta_load=_f18_note_data

# Global functions in the previous implementation resolve these names at runtime.
_f17_center_photo_table=_f18_center_photo_table
_f17_build_catalog_rows=_f18_catalog_rows
_f18_original_catalog=App.page_catalog
App.__init__=_f18_init
App.open_module=_f18_open_module
App.page_pos=_f18_make_pos_compact
App.page_catalog=_f18_catalog_page
App.message=_f18_message




# === F19: expandable workspaces, softer melody, richer purchases, internal messages ===
from PySide6.QtWidgets import QScrollBar, QFormLayout


def _f19_set_layout_visible(layout, visible, states=None):
 if layout is None:return
 for i in range(layout.count()):
  item=layout.itemAt(i)
  w=item.widget()
  if w is not None:
   if states is not None and w not in states: states[w]=w.isVisible()
   if states is None: w.setVisible(visible)
   else: w.setVisible(False if not visible else states.get(w,True))
  else:
   inner=item.layout()
   if inner is not None:_f19_set_layout_visible(inner,visible,states)


def _f19_attach_focus_button(self,target,label='tabla'):
 if target is None or getattr(target,'_f19_focus_ready',False):return
 target._f19_focus_ready=True
 if hasattr(target,'layout') and target.layout() is not None:
  head=QHBoxLayout();head.setContentsMargins(0,0,0,0);head.setSpacing(6)
  badge=QLabel('Vista');badge.setObjectName('helper');head.addWidget(badge)
  head.addStretch(1)
  btn=QToolButton();btn.setObjectName('f19FocusButton');btn.setText('▴ Expandir '+label);head.addWidget(btn)
  try:target.layout().insertLayout(0,head)
  except Exception:return
  def toggle():
   expanded=not getattr(target,'_f19_focus_mode',False)
   target._f19_focus_mode=expanded
   if expanded:
    states={};target._f19_outer_states=states
    for i in range(self.outer.count()):
     item=self.outer.itemAt(i)
     w=item.widget()
     if w is target:continue
     if w is not None:
      states[w]=w.isVisible();w.hide()
     else:
      lay=item.layout()
      if lay is not None and lay is not head:
       _f19_set_layout_visible(lay,False,states)
    btn.setText('▾ Restaurar vista')
   else:
    states=getattr(target,'_f19_outer_states',{})
    for obj,was in list(states.items()):
     try: obj.setVisible(was)
     except Exception: pass
    btn.setText('▴ Expandir '+label)
   # keep the focused area at full stretch
   try:self.content.ensureWidgetVisible(target)
   except Exception:pass
  btn.clicked.connect(toggle)
  target._f19_focus_button=btn


def _f19_ops_path(self):
 return self.erp.root/'operations_meta_f19.json'


def _f19_ops_data(self):
 path=_f19_ops_path(self)
 try:
  data=json.loads(path.read_text(encoding='utf-8'))
  if not isinstance(data,dict):data={}
 except Exception:data={}
 return data


def _f19_ops_save(self,data):
 path=_f19_ops_path(self)
 path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')


def _f19_ops_scope(self):
 if self.module=='receipts': return 'receipts'
 if self.module=='suppliers': return 'suppliers'
 return 'purchases'


def _f19_ops_selected_key(self):
 try:return str(self.selected())
 except Exception:return ''


def _f19_ops_load(self):
 if not getattr(self,'_f19_ops_editor',None):return
 scope=_f19_ops_scope(self);key=_f19_ops_selected_key(self)
 data=_f19_ops_data(self).get(scope,{})
 item=data.get(key,{}) if key else {}
 self._f19_ops_target.blockSignals(True)
 idx=max(0,self._f19_ops_target.findData(item.get('target','all')))
 self._f19_ops_target.setCurrentIndex(idx)
 self._f19_ops_target.blockSignals(False)
 self._f19_ops_editor.blockSignals(True);self._f19_ops_editor.setPlainText(str(item.get('notes','')));self._f19_ops_editor.blockSignals(False)
 title={'receipts':'Remito / reposición','suppliers':'Mensaje para proveedor','purchases':'Pedido / reposición'}[scope]
 row='Sin selección' if not key else f'Registro #{key}'
 self._f19_ops_title.setText(f'💬 {title} · {row}')


def _f19_ops_commit(self):
 if not getattr(self,'_f19_ops_editor',None):return
 key=_f19_ops_selected_key(self)
 if not key:raise ERPError('Seleccione una fila antes de guardar el mensaje interno.')
 scope=_f19_ops_scope(self)
 data=_f19_ops_data(self)
 section=data.setdefault(scope,{})
 section[key]={'target':self._f19_ops_target.currentData(),'notes':self._f19_ops_editor.toPlainText().strip()}
 _f19_ops_save(self,data);self.message('Mensaje interno guardado correctamente.')


def _f19_ops_view(self):
 scope=_f19_ops_scope(self);data=_f19_ops_data(self).get(scope,{})
 dlg=QDialog(self);dlg.setWindowTitle('Mensajes internos · NexoMerc ERP');dlg.resize(560,500)
 root=QVBoxLayout(dlg);root.setContentsMargins(18,16,18,16);root.setSpacing(10)
 title=QLabel('💬 Historial de mensajes internos');title.setObjectName('heading');root.addWidget(title)
 helper=QLabel('Mensajes guardados para reposición, remitos y coordinación interna.');helper.setObjectName('helper');helper.setWordWrap(True);root.addWidget(helper)
 search=QLineEdit();search.setPlaceholderText('Buscar en los mensajes…');root.addWidget(search)
 area=QScrollArea();area.setWidgetResizable(True);body=QWidget();box=QVBoxLayout(body);box.setContentsMargins(6,6,6,6);box.setSpacing(8)
 cards=[]
 targets={'all':'Todos','admin':'Administración','cashier':'Caja'}
 for key,payload in sorted(data.items(),key=lambda kv: kv[0]):
  note=str(payload.get('notes','')).strip()
  if not note: continue
  frame=QFrame();frame.setObjectName('opsBubble')
  lay=QVBoxLayout(frame);lay.setContentsMargins(14,12,14,12);lay.setSpacing(4)
  who=QLabel(f'Registro #{key} · Destino: {targets.get(payload.get("target","all"),"Todos")}');who.setObjectName('kpi_title');lay.addWidget(who)
  txt=QLabel(note);txt.setWordWrap(True);txt.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse);lay.addWidget(txt)
  box.addWidget(frame);cards.append((frame,(who.text()+' '+note).casefold()))
 if not cards:
  empty=QLabel('Todavía no hay mensajes guardados en esta sección.');empty.setWordWrap(True);box.addWidget(empty)
 box.addStretch(1);area.setWidget(body);root.addWidget(area,1)
 search.textChanged.connect(lambda query:[frame.setVisible(query.casefold() in text) for frame,text in cards])
 close=QPushButton('Cerrar');close.clicked.connect(dlg.accept);root.addWidget(close)
 dlg.exec()


def _f19_attach_ops_panel(self,shell):
 if shell is None or getattr(shell,'_f19_ops_ready',False):return shell
 shell._f19_ops_ready=True
 panel=QFrame();panel.setObjectName('opsNotebookPanel')
 lay=QVBoxLayout(panel);lay.setContentsMargins(14,14,14,14);lay.setSpacing(10)
 ribbon=QLabel('📝 Mensajes internos');ribbon.setObjectName('noteRibbon');lay.addWidget(ribbon)
 self._f19_ops_title=QLabel('💬 Pedido / reposición');self._f19_ops_title.setObjectName('kpi_title');self._f19_ops_title.setWordWrap(True);lay.addWidget(self._f19_ops_title)
 helper=QLabel('Guardá observaciones para reposición, remitos o avisos destinados a administración o caja.');helper.setObjectName('helper');helper.setWordWrap(True);lay.addWidget(helper)
 self._f19_ops_target=QComboBox();
 for label,key in [('Todos','all'),('Administración','admin'),('Caja','cashier')]: self._f19_ops_target.addItem(label,key)
 lay.addWidget(self._f19_ops_target)
 self._f19_ops_editor=QTextEdit();self._f19_ops_editor.setPlaceholderText('Ejemplo: reponer limpiadores de baño, avisar faltante a caja, recibir remito con control de stock…');self._f19_ops_editor.setMinimumHeight(220);lay.addWidget(self._f19_ops_editor,1)
 actions=QHBoxLayout();view=QPushButton('Ver mensajes');view.clicked.connect(lambda checked=False:self.safe(_f19_ops_view.__get__(self,App)));actions.addWidget(view);actions.addStretch(1)
 save=QPushButton('Guardar mensaje');save.clicked.connect(lambda checked=False:self.safe(_f19_ops_commit.__get__(self,App)));actions.addWidget(save);lay.addLayout(actions)
 split=QSplitter(Qt.Orientation.Horizontal);split.setChildrenCollapsible(False);split.addWidget(shell);split.addWidget(panel);split.setStretchFactor(0,4);split.setStretchFactor(1,1)
 self.outer.removeWidget(shell);self.outer.addWidget(split,1)
 self.table.itemSelectionChanged.connect(lambda:_f19_ops_load(self));_f19_ops_load(self)
 _f19_attach_focus_button(self,split,'lista')
 return split


class _F19PurchaseItemsDialog(QDialog):
 def __init__(self,parent,erp):
  super().__init__(parent);self.parent_window=parent;self.erp=erp;self.lines={};self.setWindowTitle('Productos del pedido · NexoMerc ERP');self.resize(1040,700)
  root=QVBoxLayout(self);root.setContentsMargins(18,16,18,16);root.setSpacing(10)
  title=QLabel('Elegí productos para la orden');title.setObjectName('heading');root.addWidget(title)
  helper=QLabel('Buscá por nombre, SKU o categoría. Podés ver la foto antes de añadir el producto.');helper.setObjectName('helper');helper.setWordWrap(True);root.addWidget(helper)
  top=QHBoxLayout();self.search=QLineEdit();self.search.setPlaceholderText('Buscar limpiadores, lavandina, baño, arroz, etc.');top.addWidget(self.search,3)
  self.category=QComboBox();self.category.addItem('Todas las categorías',None)
  cats={int(x['id']):x['name'] for x in erp.catalogs('categories')} if hasattr(erp,'catalogs') else {}
  for cid,name in sorted(cats.items(), key=lambda kv: kv[1].lower()): self.category.addItem(name,cid)
  top.addWidget(self.category,1);root.addLayout(top)
  body=QSplitter(Qt.Orientation.Horizontal);body.setChildrenCollapsible(False)
  left=QFrame();ll=QVBoxLayout(left);ll.setContentsMargins(0,0,0,0);ll.setSpacing(8)
  self.table=QTableWidget(0,5);self.table.setHorizontalHeaderLabels(['ID','Foto','SKU','Producto','Categoría'])
  self.table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.ResizeToContents)
  self.table.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.Fixed);self.table.horizontalHeader().resizeSection(1,80)
  self.table.horizontalHeader().setSectionResizeMode(2,QHeaderView.ResizeMode.ResizeToContents)
  self.table.horizontalHeader().setSectionResizeMode(3,QHeaderView.ResizeMode.Stretch)
  self.table.horizontalHeader().setSectionResizeMode(4,QHeaderView.ResizeMode.ResizeToContents)
  ll.addWidget(self.table,1);body.addWidget(left)
  right=QFrame();rl=QVBoxLayout(right);rl.setContentsMargins(8,4,8,4);rl.setSpacing(8)
  self.photo=QLabel('Sin foto');self.photo.setAlignment(Qt.AlignmentFlag.AlignCenter);self.photo.setFixedHeight(168);self.photo.setObjectName('brandPhotoPreview');rl.addWidget(self.photo)
  self.name=QLabel('Seleccione un producto');self.name.setObjectName('kpi_title');self.name.setWordWrap(True);rl.addWidget(self.name)
  self.meta=QLabel('');self.meta.setObjectName('helper');self.meta.setWordWrap(True);rl.addWidget(self.meta)
  form=QFormLayout();self.qty=QuantitySpinBox();self.qty.setDecimals(3);self.qty.setRange(0.001,999999);self.qty.setValue(1);form.addRow('Cantidad',self.qty)
  self.cost=QDoubleSpinBox();self.cost.setRange(0,99999999);self.cost.setDecimals(2);form.addRow('Costo unitario',self.cost)
  rl.addLayout(form)
  add=QPushButton('Añadir al pedido');add.setObjectName('primary');add.clicked.connect(self.add_current);rl.addWidget(add)
  extra=QLabel('Pedido libre (opcional)');extra.setObjectName('kpi_title');rl.addWidget(extra)
  self.free_text=QTextEdit();self.free_text.setPlaceholderText('Ejemplo: limpiador perfumado para baño, si aún no está creado en el catálogo. Este texto se agregará a las observaciones de la orden.');self.free_text.setFixedHeight(110);rl.addWidget(self.free_text)
  rl.addStretch(1);body.addWidget(right)
  body.setStretchFactor(0,3);body.setStretchFactor(1,2);root.addWidget(body,3)
  lower=QFrame();lv=QVBoxLayout(lower);lv.setContentsMargins(0,0,0,0);lv.setSpacing(8)
  cap=QLabel('Líneas del pedido');cap.setObjectName('kpi_title');lv.addWidget(cap)
  self.lines_table=QTableWidget(0,5);self.lines_table.setHorizontalHeaderLabels(['ID','Foto','Producto','Cantidad','Costo'])
  self.lines_table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.ResizeToContents)
  self.lines_table.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.Fixed);self.lines_table.horizontalHeader().resizeSection(1,80)
  self.lines_table.horizontalHeader().setSectionResizeMode(2,QHeaderView.ResizeMode.Stretch)
  self.lines_table.horizontalHeader().setSectionResizeMode(3,QHeaderView.ResizeMode.ResizeToContents)
  self.lines_table.horizontalHeader().setSectionResizeMode(4,QHeaderView.ResizeMode.ResizeToContents)
  lv.addWidget(self.lines_table,1)
  rm=QPushButton('Quitar seleccionado');rm.clicked.connect(self.remove_selected);lv.addWidget(rm,0,Qt.AlignmentFlag.AlignRight)
  root.addWidget(lower,2)
  buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
  buttons.accepted.connect(self.accept);buttons.rejected.connect(self.reject);root.addWidget(buttons)
  self.products=[];self.cat_names=cats
  for p in erp.catalogs('products'):
   if p.get('active',1): self.products.append(p)
  self.search.textChanged.connect(self.refill);self.category.currentIndexChanged.connect(self.refill)
  self.table.itemSelectionChanged.connect(self.sync_preview)
  self.refill()
 def product_photo(self,filename,size=52):
  if not filename:return QPixmap()
  pix=QPixmap(str(self.erp.root/'photos'/filename))
  return pix.scaled(size,size,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation) if not pix.isNull() else QPixmap()
 def refill(self):
  needle=self.search.text().casefold().strip();cat=self.category.currentData();self.table.setRowCount(0)
  rows=[]
  for p in self.products:
   if cat and int(p.get('category_id') or 0)!=int(cat):continue
   text=' '.join(str(p.get(k,'')) for k in ('sku','name')).casefold()+' '+str(self.cat_names.get(int(p.get('category_id') or 0),'' )).casefold()
   if needle and needle not in text:continue
   rows.append(p)
  for p in rows:
   r=self.table.rowCount();self.table.insertRow(r)
   vals=[p['id'],'',p.get('sku',''),p.get('name',''),self.cat_names.get(int(p.get('category_id') or 0),'—')]
   for c,val in enumerate(vals):
    item=QTableWidgetItem(str(val));
    if c==0:item.setData(Qt.ItemDataRole.UserRole,p['id'])
    self.table.setItem(r,c,item)
   lab=QLabel();lab.setAlignment(Qt.AlignmentFlag.AlignCenter);pix=self.product_photo(p.get('photo',''))
   if not pix.isNull():lab.setPixmap(pix)
   else:lab.setText('—')
   self.table.setCellWidget(r,1,lab);self.table.setRowHeight(r,58)
  if self.table.rowCount(): self.table.selectRow(0)
 def current_product(self):
  r=self.table.currentRow()
  if r<0:return None
  item=self.table.item(r,0)
  pid=item.data(Qt.ItemDataRole.UserRole) if item else None
  if pid is None:return None
  return self.erp.entity('products',int(pid))
 def sync_preview(self):
  p=self.current_product()
  if not p:
   self.name.setText('Seleccione un producto');self.meta.setText('');self.photo.setText('Sin foto');self.photo.setPixmap(QPixmap());return
  self.name.setText(p.get('name','Producto'))
  self.meta.setText(f'SKU: {p.get("sku","")} · Categoría: {self.cat_names.get(int(p.get("category_id") or 0),"—")}')
  self.cost.setValue(float(p.get('cost_cents',0))/100)
  pix=self.product_photo(p.get('photo',''),150)
  if pix.isNull():self.photo.setPixmap(QPixmap());self.photo.setText('Sin foto')
  else:self.photo.setText('');self.photo.setPixmap(pix)
 def add_current(self):
  p=self.current_product()
  if not p:return
  pid=int(p['id']);self.lines[pid]={'product_id':pid,'qty':self.qty.value(),'cost':self.cost.value()};self.redraw_lines()
 def redraw_lines(self):
  self.lines_table.setRowCount(0)
  for pid,line in self.lines.items():
   p=self.erp.entity('products',pid)
   r=self.lines_table.rowCount();self.lines_table.insertRow(r)
   vals=[pid,'',p.get('name',''),line['qty'],line['cost']]
   for c,val in enumerate(vals):
    it=QTableWidgetItem(str(val));
    if c==0:it.setData(Qt.ItemDataRole.UserRole,pid)
    self.lines_table.setItem(r,c,it)
   lab=QLabel();lab.setAlignment(Qt.AlignmentFlag.AlignCenter);pix=self.product_photo(p.get('photo',''))
   if not pix.isNull():lab.setPixmap(pix)
   else:lab.setText('—')
   self.lines_table.setCellWidget(r,1,lab);self.lines_table.setRowHeight(r,58)
 def remove_selected(self):
  r=self.lines_table.currentRow()
  if r<0:return
  item=self.lines_table.item(r,0)
  pid=item.data(Qt.ItemDataRole.UserRole) if item else None
  if pid in self.lines:self.lines.pop(pid,None);self.redraw_lines()
 def accept(self):
  if not self.lines:QMessageBox.warning(self,'Productos','Agregá al menos un producto a la orden.');return
  super().accept()
 def values(self): return list(self.lines.values())
 def free_notes(self): return self.free_text.toPlainText().strip()


def _f19_new_po(self):
 dlg=PurchaseOrderDialog(self,self.erp)
 if dlg.exec()!=QDialog.DialogCode.Accepted:return
 data=dlg.values()
 items=_F19PurchaseItemsDialog(self,self.erp)
 if items.exec()!=QDialog.DialogCode.Accepted:return
 extra=items.free_notes().strip()
 notes=data['notes']
 if extra:
  notes=(notes+'\n' if notes else '')+'Pedido libre / aclaración: '+extra
 oid=self.erp.create_po(data['supplier'],data['branch'],items.values(),notes)
 self.reload();self.message(f'OC #{oid} creada como borrador. Podés registrar el remito desde Compras y proveedores.')


def _f19_page_receipts(self):
 _F19_ORIGINAL_RECEIPTS(self)
 shell=self.table.parentWidget() if getattr(self,'table',None) and self.table.parentWidget() else getattr(self,'table',None)
 if shell is not None:
  _f19_attach_ops_panel(self,shell)


def _f19_page_purchases(self):
 _F19_ORIGINAL_PURCHASES(self)
 shell=self.table.parentWidget() if getattr(self,'table',None) and self.table.parentWidget() else getattr(self,'table',None)
 if shell is not None:
  _f19_attach_ops_panel(self,shell)


def _f19_page_suppliers(self):
 _F19_ORIGINAL_SUPPLIERS(self)
 shell=self.table.parentWidget() if getattr(self,'table',None) and self.table.parentWidget() else getattr(self,'table',None)
 if shell is not None:
  _f19_attach_ops_panel(self,shell)


def _f19_page_products_like(self,orig,label='tabla'):
 orig(self)
 shell=self.table.parentWidget() if getattr(self,'table',None) and self.table.parentWidget() else None
 if shell is not None:_f19_attach_focus_button(self,shell,label)


def _f19_page_catalog(self):
 _F19_ORIGINAL_CATALOG(self)
 # hide outer notes from POS request? keep here, but allow expanding the whole workspace.
 item=self.outer.itemAt(self.outer.count()-1)
 target=item.widget() if item is not None else None
 if target is not None:_f19_attach_focus_button(self,target,'catálogo')


def _f19_remove_pos_notes_button(self):
 item=self.outer.itemAt(0)
 lay=item.layout() if item is not None else None
 if lay is None:return
 for i in range(lay.count()-1,-1,-1):
  w=lay.itemAt(i).widget()
  if isinstance(w,QPushButton) and 'anot' in w.text().casefold():
   w.hide();w.setParent(None)


def _f19_toggle_pos_focus(self):
 card=self.content.widget().findChild(QFrame,'posCatalogCard')
 if card is None:return
 expanded=not getattr(self,'_f19_pos_focus',False)
 self._f19_pos_focus=expanded
 lay=card.layout(); indexes=[0,2,4,5]  # title, helper, preview, small caption
 if expanded:
  states={}; self._f19_pos_states=states
  for idx in indexes:
   item=lay.itemAt(idx)
   if item is None: continue
   w=item.widget()
   if w is not None:
    states[w]=w.isVisible(); w.hide()
   else:
    inner=item.layout(); _f19_set_layout_visible(inner,False,states)
  if getattr(self,'pos_history_body',None): self.pos_history_body.hide()
  if hasattr(self,'pos_history_toggle'): self.pos_history_toggle.setText('▸ Historial reciente')
  self.pos_vertical_splitter.setSizes([1260,1])
  self._f19_pos_expand_btn.setText('▾ Restaurar vista de caja')
 else:
  for obj,was in getattr(self,'_f19_pos_states',{}).items():
   try: obj.setVisible(was)
   except Exception: pass
  self._f19_pos_expand_btn.setText('▴ Más productos')
  self.pos_vertical_splitter.setSizes([920,180])
  if getattr(self,'pos_history_body',None): self.pos_history_body.show()
 self.pos_barcode.setFocus()


def _f19_page_pos(self):
 _F19_ORIGINAL_POS(self)
 _f19_remove_pos_notes_button(self)
 # Add dedicated expand button; keep cart toggle from F18.
 top=self.outer.itemAt(0).layout() if self.outer.count() else None
 if top is not None and not getattr(self,'_f19_pos_focus_button_added',False):
  btn=QPushButton('▴ Más productos');btn.clicked.connect(lambda checked=False:_f19_toggle_pos_focus(self))
  self._f19_pos_expand_btn=btn
  # place after cart button if present
  top.insertWidget(1,btn)
  self._f19_pos_focus_button_added=True
 # make the cart a little less dominant when shown
 if getattr(self,'_f18_cart_panel',None):
  try:self._f18_panels.setSizes([1180,1])
  except Exception:pass


def _f19_toggle_cart(self):
 _F19_ORIGINAL_TOGGLE_CART(self)
 if getattr(self,'_f18_cart_panel',None) and self._f18_cart_panel.isVisible():
  try:self._f18_panels.setSizes([690,220])
  except Exception:pass


def _f19_melody(self):
 if str(QSettings('NexoMerc','ERP').value('f19_sound','soft')).lower()=='off':return
 try:
  from PySide6.QtMultimedia import QSoundEffect
  effect=getattr(self,'_f19_audio',None)
  if effect is None:
   effect=QSoundEffect(self)
   path=Path(__file__).resolve().parent.parent/'assets'/'audio'/'soft_confirm_f19.wav'
   effect.setSource(QUrl.fromLocalFile(str(path)))
   effect.setLoopCount(1);effect.setVolume(0.08)
   self._f19_audio=effect
  if effect.isLoaded():effect.play()
 except Exception:pass


def _f19_message(self,txt='Operación completada correctamente.'):
 _f19_melody(self)
 dialog=QDialog(self);dialog.setWindowTitle('NexoMerc ERP');dialog.setModal(True);dialog.setMinimumWidth(440)
 layout=QVBoxLayout(dialog);layout.setContentsMargins(22,18,22,18);layout.setSpacing(12)
 line=QHBoxLayout();line.setSpacing(12)
 badge=QLabel('✓');badge.setObjectName('infoBubble');badge.setAlignment(Qt.AlignmentFlag.AlignCenter);badge.setFixedSize(42,42)
 line.addWidget(badge,0,Qt.AlignmentFlag.AlignTop)
 message=QLabel(self.text(txt));message.setWordWrap(True);line.addWidget(message,1);layout.addLayout(line)
 controls=QHBoxLayout();controls.addStretch(1)
 mute=QPushButton('Silenciar avisos' if QSettings('NexoMerc','ERP').value('f19_sound','soft')!='off' else 'Activar melodía')
 def toggle_sound():
  prefs=QSettings('NexoMerc','ERP');on=prefs.value('f19_sound','soft')!='off';prefs.setValue('f19_sound','off' if on else 'soft')
  mute.setText('Activar melodía' if on else 'Silenciar avisos')
 mute.clicked.connect(toggle_sound);controls.addWidget(mute)
 ok=QPushButton('Aceptar');ok.clicked.connect(dialog.accept);controls.addWidget(ok)
 layout.addLayout(controls);dialog.exec()


_F19_ORIGINAL_INIT=App.__init__
def _f19_init(self,*args,**kwargs):
 _F19_ORIGINAL_INIT(self,*args,**kwargs)
 self.setWindowTitle('NexoMerc ERP · V2-F19')
 try:self.content.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
 except Exception:pass


def _f19_page_products(self): _f19_page_products_like(self,_F19_ORIGINAL_PRODUCTS,'catálogo')
def _f19_page_inventory(self): _f19_page_products_like(self,_F19_ORIGINAL_INVENTORY,'existencias')


_F19_ORIGINAL_PRODUCTS=getattr(App,'page_products')
_F19_ORIGINAL_INVENTORY=getattr(App,'page_inventory')
_F19_ORIGINAL_CATALOG=getattr(App,'page_catalog')
_F19_ORIGINAL_RECEIPTS=getattr(App,'page_receipts')
_F19_ORIGINAL_PURCHASES=getattr(App,'page_purchases')
_F19_ORIGINAL_SUPPLIERS=getattr(App,'page_suppliers',lambda self: None)
_F19_ORIGINAL_POS=getattr(App,'page_pos')
_F19_ORIGINAL_TOGGLE_CART=globals().get('_f18_toggle_cart', lambda self: None)
App.__init__=_f19_init
App.page_products=_f19_page_products
App.page_inventory=_f19_page_inventory
App.page_catalog=_f19_page_catalog
App.page_receipts=_f19_page_receipts
App.page_purchases=_f19_page_purchases
App.page_suppliers=_f19_page_suppliers
App.page_pos=_f19_page_pos
App.new_po=_f19_new_po
App.message=_f19_message
if '_f18_toggle_cart' in globals(): _f18_toggle_cart=_f19_toggle_cart



# === F20 — POS de uso comercial, cupones internos y promociones agrupadas ===
from PySide6.QtWidgets import QProgressBar

for _idx,(_module,_label) in enumerate(MENU):
 if _module=='promotions':
  MENU[_idx]=(_module,'Promociones y cupones')
TITLES['promotions']='Promociones y cupones'


def _f20_pos_current_total(self):
 bid=self.pos_branch.currentData() if hasattr(self,'pos_branch') else None
 if not bid:return 0
 return sum(total_for(qty,self.erp.effective_price(pid,bid)) for pid,qty in self.cart.items())


def _f20_offer_preview(self):
 if not hasattr(self,'f20_total'):return
 subtotal=_f20_pos_current_total(self)
 customer_id=self.pos_customer.currentData()
 code=self.f20_coupon_code.text().strip()
 discount=0
 if code and subtotal:
  try:
   c=self.erp.coupon_preview(code,customer_id,self.pos_branch.currentData(),subtotal)
   discount=c['amount_cents']
   self.f20_coupon_status.setText(f'Cupón válido: descuento {self._money(discount)}')
   self.f20_coupon_status.setStyleSheet('color:#256438;font-weight:700;')
  except ERPError as e:
   self.f20_coupon_status.setText(str(e))
   self.f20_coupon_status.setStyleSheet('color:#9B2312;font-weight:700;')
 else:
  self.f20_coupon_status.setText('Ingresá un cupón interno del cliente para validarlo antes de cobrar.' if not code else 'Agregá productos al carrito.')
 self.f20_subtotal.setText(self._money(subtotal))
 self.f20_discount.setText('- '+self._money(discount))
 self.f20_total.setText(self._money(subtotal-discount))
 # El cupón se entrega después de cobrar, solo con regla activa y cliente identificado.
 if customer_id:
  rule=self.erp.one('SELECT threshold_cents,award_cents FROM coupon_rules WHERE active=1 AND (branch_id IS NULL OR branch_id=?) AND threshold_cents<=? ORDER BY award_cents DESC,id LIMIT 1',(self.pos_branch.currentData(),subtotal-discount))
  self.f20_reward.setText(('🎟️ Compra elegible: se emitirá cupón de '+self._money(rule['award_cents'])+' al cobrar.') if rule else 'Sin beneficio automático para el monto de esta compra.')
 else:
  self.f20_reward.setText('Elegí un cliente registrado para acumular puntos y recibir cupones de fidelidad.')


def _f20_render_cart(self):
 _F20_ORIGINAL_RENDER_CART(self)
 if hasattr(self,'f20_total'):_f20_offer_preview(self)


def _f20_add(self):
 _F20_ORIGINAL_POS_ADD(self)
 if hasattr(self,'f20_total'):_f20_offer_preview(self)


def _f20_checkout(self):
 if not self.cart:raise ERPError('El carrito está vacío.')
 subtotal=_f20_pos_current_total(self)
 code=self.f20_coupon_code.text().strip().upper() if hasattr(self,'f20_coupon_code') else ''
 customer_id=self.pos_customer.currentData()
 if code:self.erp.coupon_preview(code,customer_id,self.pos_branch.currentData(),subtotal)
 if not self.confirm('¿Confirmar el cobro? Se aplicarán los descuentos validados y se descontará el stock.'):
  return
 items=[{'product_id':pid,'qty':quantity(qty_milli)} for pid,qty_milli in self.cart.items()]
 sale_id=self.erp.checkout(self.pos_branch.currentData(),items,self.pos_payment.currentData(),customer_id,code or None)
 self.cart={}
 if hasattr(self,'f20_coupon_code'):self.f20_coupon_code.clear()
 ticket=self.erp.sale_ticket(sale_id)
 reward=self.erp.one('SELECT code,amount_cents,expires_on FROM coupon_issues WHERE issued_sale_id=? AND voided=0',(sale_id,))
 msg=f'Venta #{sale_id} registrada. Total cobrado: {self._money(self.erp.entity("sales",sale_id)["total_cents"])}.'
 if reward:msg+='\nCupón entregado: '+reward['code']+' · '+self._money(reward['amount_cents'])
 self.message(msg)
 if QMessageBox.question(self,'Ticket de venta','¿Imprimir ticket interno NO fiscal ahora?',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.Yes)==QMessageBox.StandardButton.Yes:
  self.print_ticket(sale_id)
 self.reload()


def _f20_cash_view(self):
 visible=not getattr(self,'_f20_cash_active',False)
 self._f20_cash_active=visible
 panels=getattr(self,'_f18_panels',None)
 if panels:
  panels.setOrientation(Qt.Orientation.Horizontal)
  if getattr(self,'_f18_cart_panel',None):self._f18_cart_panel.setVisible(visible)
  panels.setSizes([650,350] if visible else [990,1])
 if hasattr(self,'_f18_cart_btn'):self._f18_cart_btn.setText('🛒 Volver al catálogo' if visible else '🛒 Mostrar carrito / cobrar')
 if hasattr(self,'f20_focus_btn'):self.f20_focus_btn.setText('▥ Volver a vista normal' if visible else '▤ Caja expandida')
 # Libera altura para las miniaturas y el carrito. No mueve ni destruye tablas.
 if getattr(self,'_f20_preview',None):self._f20_preview.setVisible(not visible)
 if hasattr(self,'pos_history_body'):self.pos_history_body.hide()
 if hasattr(self,'pos_history_toggle'):self.pos_history_toggle.setText('▸ Historial reciente')
 if hasattr(self,'pos_vertical_splitter'):self.pos_vertical_splitter.setSizes([1100,55])
 if hasattr(self,'pos_catalog'):
  self.pos_catalog.setMinimumHeight(300 if visible else 220)
  self.pos_catalog.horizontalHeader().setStretchLastSection(False)
  self.pos_catalog.horizontalHeader().setSectionResizeMode(3,QHeaderView.ResizeMode.Stretch)
  self.pos_catalog.setColumnHidden(0,True)
  self.pos_catalog.setColumnHidden(2,True)
 if hasattr(self,'pos_cart'):
  self.pos_cart.setColumnHidden(0,True)
  self.pos_cart.setColumnHidden(4,True)
 if hasattr(self,'pos_barcode'):self.pos_barcode.setFocus()


def _f20_page_pos(self):
 _F20_ORIGINAL_PAGE_POS(self)
 # Amplía catálogo, elimina ayuda repetida y ajusta la cantidad real de filas visibles.
 self.pos_catalog.setMinimumHeight(260)
 self.pos_catalog.setColumnHidden(0,True)
 self.pos_catalog.setColumnHidden(2,True)
 self.pos_catalog.horizontalHeader().setSectionResizeMode(3,QHeaderView.ResizeMode.Stretch)
 self.pos_catalog.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.Fixed)
 self.pos_catalog.horizontalHeader().resizeSection(1,82)
 self.pos_catalog.verticalHeader().setDefaultSectionSize(59)
 self.pos_catalog.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
 # Prioridad: fotos/nombre/precio/existencias. La caja debe mostrar más de una fila.
 self.pos_vertical_splitter.setSizes([1100,55])
 if getattr(self,'_f18_panels',None):
  self._f18_panels.setHandleWidth(6)
  self._f18_panels.setOrientation(Qt.Orientation.Horizontal)
  self._f18_panels.setSizes([950,1])
 self._f20_preview=self.pos_preview_photo.parentWidget() if hasattr(self,'pos_preview_photo') else None
 if self._f20_preview and isinstance(self._f20_preview,QFrame):self._f20_preview.hide()
 top=self.outer.itemAt(0).layout() if self.outer.count() else None
 if top:
  self.f20_focus_btn=QPushButton('▤ Caja expandida')
  self.f20_focus_btn.clicked.connect(_f20_cash_view.__get__(self,App))
  top.insertWidget(1,self.f20_focus_btn)
 # Footer permanente, incluso con el carrito oculto: subtotal, descuento, total y cierre de venta.
 footer=QFrame();footer.setObjectName('f20CheckoutFooter')
 fl=QVBoxLayout(footer);fl.setContentsMargins(12,10,12,10);fl.setSpacing(7)
 line=QHBoxLayout();line.setSpacing(9)
 line.addWidget(QLabel('Cliente'))
 # Move the same customer selector from original cart actions to footer without resetting selection.
 self.pos_customer.setMinimumWidth(150)
 line.addWidget(self.pos_customer)
 line.addWidget(QLabel('Pago'))
 self.pos_payment.setMinimumWidth(115)
 line.addWidget(self.pos_payment)
 line.addWidget(QLabel('Cupón interno'))
 self.f20_coupon_code=QLineEdit();self.f20_coupon_code.setPlaceholderText('NXM-XXXXXXXXXX');self.f20_coupon_code.setMaximumWidth(180)
 self.f20_coupon_code.textChanged.connect(lambda *_:_f20_offer_preview(self))
 line.addWidget(self.f20_coupon_code)
 fl.addLayout(line)
 line2=QHBoxLayout();line2.setSpacing(9)
 self.f20_subtotal=QLabel();self.f20_discount=QLabel();self.f20_total=QLabel()
 for label,value in [('Subtotal:',self.f20_subtotal),('Descuento:',self.f20_discount),('TOTAL:',self.f20_total)]:
  cap=QLabel(label);line2.addWidget(cap);line2.addWidget(value)
 self.f20_total.setObjectName('f20BigTotal')
 line2.addStretch(1)
 close=QPushButton('✓ COBRAR Y CERRAR VENTA');close.setObjectName('primary');close.clicked.connect(lambda checked=False:self.safe(_f20_checkout.__get__(self,App)))
 line2.addWidget(close)
 fl.addLayout(line2)
 self.f20_coupon_status=QLabel('');self.f20_coupon_status.setObjectName('helper');self.f20_coupon_status.setWordWrap(True);fl.addWidget(self.f20_coupon_status)
 self.f20_reward=QLabel('');self.f20_reward.setObjectName('helper');self.f20_reward.setWordWrap(True);fl.addWidget(self.f20_reward)
 self.outer.addWidget(footer)
 self.pos_customer.currentIndexChanged.connect(lambda *_:_f20_offer_preview(self))
 self.pos_payment.currentIndexChanged.connect(lambda *_:_f20_offer_preview(self))
 _f20_offer_preview(self)
 if hasattr(self,'pos_barcode'):self.pos_barcode.setFocus()


def _f20_promo_tab(self,mode):
 self.f20_promo_mode=mode;self.reload()


def _f20_create_rule(self):
 self.erp.check('promotions','create')
 d=self.prompt('Regla de cupón por compra',[fld('name','Nombre de campaña'),fld('threshold','Compra mínima (ARS)','money',100000),fld('award','Valor del cupón (ARS)','money',5000),fld('days','Vigencia del cupón en días','integer',30),fld('branch','Sucursal (vacío = todas)','choice',None,self.branch_opts(none=True))])
 if d is None:return
 self.erp.create_coupon_rule(d['name'],d['threshold'],d['award'],d['branch'],d['days']);self.reload();self.message('Regla creada. El cupón se entrega únicamente tras una compra elegible con cliente identificado.')


def _f20_toggle_rule(self):
 rid=self.selected();row=self.erp.entity('coupon_rules',rid)
 self.erp.set_coupon_rule_active(rid,not bool(row['active']));self.reload()


def _f20_issue_for_customer(self):
 self.erp.check('promotions','create')
 d=self.prompt('Cupón para cliente registrado',[fld('customer','Cliente','choice',None,combo_data(self.erp,'customers')),fld('award','Monto a descontar en una futura compra (ARS)','money',5000),fld('days','Vigencia (días)','integer',30)])
 if d is None:return
 if not d['customer']:raise ERPError('Seleccioná un cliente.')
 code=self.erp.issue_coupon(d['customer'],d['award'],d['days']);self.reload();self.message('Cupón emitido: '+code+' · Entregalo al cliente titular.')


def _f20_coupon_list(self):
 rows=self.erp.all('''SELECT i.id,i.code,c.name AS cliente,i.amount_cents,i.issued_at,i.expires_on,i.redeemed_sale_id,i.voided
 FROM coupon_issues i JOIN customers c ON c.id=i.customer_id ORDER BY i.id DESC''')
 today=date.today().isoformat()
 for r in rows:
  r['estado']='Anulado' if r['voided'] else 'Utilizado' if r['redeemed_sale_id'] is not None else 'Vencido' if r['expires_on']<today else 'Disponible'
 return rows


def _f20_page_promotions(self):
 mode=getattr(self,'f20_promo_mode','prices')
 # Tab-like toolbar with two categories of business tasks, no extra menu clutter.
 for key,label in [('prices','Precios promocionales'),('rules','Reglas de recompensa'),('coupons','Cupones por cliente')]:
  self.tool(('● ' if key==mode else '')+label,lambda key=key:_f20_promo_tab(self,key),key==mode)
 if mode=='prices':
  if self.erp.available('promotions','create'):self.tool('Nueva promoción',self.promo_new)
  if self.erp.available('promotions','edit'):self.tool('Activar / desactivar',self.promo_toggle)
  self.show_rows(self.erp.catalogs('promotions'),['id','product_id','branch_id','name','price_cents','starts_at','ends_at','active'])
 elif mode=='rules':
  if self.erp.available('promotions','create'):self.tool('Nueva regla de recompensa',lambda:self.safe(_f20_create_rule.__get__(self,App)),True)
  if self.erp.available('promotions','edit'):self.tool('Activar / desactivar',lambda:self.safe(_f20_toggle_rule.__get__(self,App)))
  hint=QLabel('Ejemplo: compras desde ARS 100.000 → emitir cupón de ARS 5.000 al cliente identificado. No se descuenta de la compra que lo genera.')
  hint.setObjectName('helper');hint.setWordWrap(True);self.outer.addWidget(hint)
  self.show_rows(self.erp.all('SELECT id,name,threshold_cents,award_cents,branch_id,valid_days,active FROM coupon_rules ORDER BY id DESC'))
 else:
  if self.erp.available('promotions','create'):self.tool('Emitir cupón a cliente',lambda:self.safe(_f20_issue_for_customer.__get__(self,App)),True)
  hint=QLabel('Los cupones locales tienen titular, vencimiento, código único y un solo uso. Integraciones bancarias: no conectadas, requieren convenio y API certificada.')
  hint.setObjectName('helper');hint.setWordWrap(True);self.outer.addWidget(hint)
  self.show_rows(_f20_coupon_list(self),['id','code','cliente','amount_cents','issued_at','expires_on','estado'])


_F20_ORIGINAL_PAGE_POS=App.page_pos
_F20_ORIGINAL_RENDER_CART=App.render_cart
_F20_ORIGINAL_POS_ADD=App.pos_add
App.page_pos=_f20_page_pos
App.render_cart=_f20_render_cart
App.pos_add=_f20_add
App.pos_checkout=_f20_checkout
App.page_promotions=_f20_page_promotions




# === F21.0: POS rediseñado. Una única tabla de carrito y catálogo bajo demanda. ===
from PySide6.QtGui import QColor


class _F21BuscarProducto(QDialog):
 def __init__(self,owner):
  super().__init__(owner)
  self.erp=owner.erp; self.owner=owner;self.pid=None
  self.setWindowTitle('Buscar producto para agregar a la venta · NexoMerc ERP')
  self.resize(920,580);self.setMinimumSize(680,420)
  main=QVBoxLayout(self);main.setContentsMargins(16,14,16,14);main.setSpacing(10)
  title=QLabel('Buscar en el catálogo');title.setObjectName('heading');main.addWidget(title)
  tip=QLabel('Los productos aparecen aquí para buscar y seleccionar. Solo los artículos añadidos se muestran en la caja.');tip.setWordWrap(True);tip.setObjectName('helper');main.addWidget(tip)
  self.query=QLineEdit();self.query.setClearButtonEnabled(True);self.query.setPlaceholderText('Nombre, SKU o código de barras…');main.addWidget(self.query)
  self.results=QTableWidget(0,5)
  self.results.setHorizontalHeaderLabels(['Foto','Nombre / descripción','SKU / código','Precio de venta','Disponible'])
  self.results.verticalHeader().hide()
  self.results.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
  self.results.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
  self.results.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
  self.results.setSortingEnabled(False)
  h=self.results.horizontalHeader();h.setStretchLastSection(False)
  h.setSectionResizeMode(0,QHeaderView.ResizeMode.Fixed);h.resizeSection(0,78)
  h.setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch)
  h.setSectionResizeMode(2,QHeaderView.ResizeMode.Fixed);h.resizeSection(2,165)
  h.setSectionResizeMode(3,QHeaderView.ResizeMode.Fixed);h.resizeSection(3,140)
  h.setSectionResizeMode(4,QHeaderView.ResizeMode.Fixed);h.resizeSection(4,110)
  main.addWidget(self.results,1)
  buttons=QHBoxLayout();buttons.addStretch(1)
  choose=QPushButton('Seleccionar producto');choose.setObjectName('primary');choose.clicked.connect(self.pick)
  close=QPushButton('Cancelar');close.clicked.connect(self.reject)
  buttons.addWidget(choose);buttons.addWidget(close);main.addLayout(buttons)
  self.query.textChanged.connect(self.refill)
  self.results.doubleClicked.connect(self.pick)
  self.refill();self.query.setFocus()
 def refill(self,*_):
  value=self.query.text().strip().casefold()
  bid=self.owner.pos_branch.currentData()
  all_products=[p for p in self.erp.catalogs('products') if p.get('active',1)]
  balances={x['product_id']:int(x['onhand_milli'])-int(x['reserved_milli']) for x in self.erp.all('SELECT product_id,onhand_milli,reserved_milli FROM stock_balances WHERE branch_id=?',(bid,))}
  self.results.setRowCount(0)
  for p in all_products:
   hay=' '.join(str(p.get(k,'') or '') for k in ('name','sku','barcode')).casefold()
   if value and value not in hay:continue
   row=self.results.rowCount();self.results.insertRow(row)
   pic=QLabel();pic.setAlignment(Qt.AlignmentFlag.AlignCenter)
   pix=_f18_pixmap(self.owner,p.get('photo',''),QSize(50,50))
   if pix.isNull():pic.setText('—')
   else:pic.setPixmap(pix)
   self.results.setCellWidget(row,0,pic)
   price=self.erp.effective_price(p['id'],bid)
   fields=[p.get('name') or 'Producto sin nombre',p.get('sku') or p.get('barcode') or '—',self.owner._money(price),quantity(balances.get(p['id'],0))+' '+str(p.get('unit','u'))]
   for col,text in enumerate(fields,1):
    item=QTableWidgetItem(str(text));item.setData(Qt.ItemDataRole.UserRole,int(p['id']))
    self.results.setItem(row,col,item)
   self.results.setRowHeight(row,58)
  if self.results.rowCount():self.results.selectRow(0)
 def pick(self,*_):
  row=self.results.currentRow()
  if row<0:return
  cell=self.results.item(row,1)
  if cell is None:return
  self.pid=cell.data(Qt.ItemDataRole.UserRole)
  if self.pid is not None:self.accept()


def _f21_cart_total(self):
 bid=self.pos_branch.currentData()
 if bid is None:return 0
 return sum(total_for(amount,self.erp.effective_price(pid,bid)) for pid,amount in self.cart.items())


def _f21_cart_row_pid(self):
 row=self.pos_cart.currentRow()
 if row<0:return None
 item=self.pos_cart.item(row,2)
 return int(item.data(Qt.ItemDataRole.UserRole)) if item and item.data(Qt.ItemDataRole.UserRole) is not None else None


def _f21_can_add(self,pid,new_amount):
 if new_amount<=0:raise ERPError('La cantidad debe ser mayor que cero.')
 if new_amount>int(10**12):raise ERPError('Cantidad demasiado grande.')
 branch=self.pos_branch.currentData()
 stock=self.erp.one('SELECT onhand_milli-reserved_milli AS available FROM stock_balances WHERE product_id=? AND branch_id=?',(pid,branch))
 available=int(stock['available']) if stock else 0
 if new_amount>available:
  p=self.erp.entity('products',pid)
  raise ERPError(f'Stock insuficiente para {p["name"]}: disponibles {quantity(available)} {p["unit"]}.')


def _f21_change_cart(self,pid,delta=0,set_amount=None):
 if pid not in self.cart:return
 amount=int(set_amount if set_amount is not None else self.cart[pid]+delta)
 if amount<=0:
  self.cart.pop(pid,None)
 else:
  _f21_can_add(self,pid,amount)
  self.cart[pid]=amount
 _f21_render_cart(self)
 self.pos_barcode.setFocus()


def _f21_remove(self,pid=None):
 if pid is None:pid=_f21_cart_row_pid(self)
 if pid is None:raise ERPError('Seleccioná un producto del carrito para retirarlo.')
 if pid not in self.cart:return
 name=self.erp.entity('products',pid)['name']
 choice=QMessageBox.question(self,'Quitar producto',f'¿Quitar «{name}» del carrito actual?\n\nNo cambia el stock hasta confirmar una venta.',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.Yes)
 if choice!=QMessageBox.StandardButton.Yes:return
 self.cart.pop(pid,None);_f21_render_cart(self)
 self.pos_barcode.setFocus()


def _f21_edit_qty(self,pid=None):
 if pid is None:pid=_f21_cart_row_pid(self)
 if pid not in self.cart:raise ERPError('Seleccioná una línea para modificar la cantidad.')
 product=self.erp.entity('products',pid)
 spin=QDoubleSpinBox(self)
 decimals=0 if product['unit']=='u' else 3
 spin.setDecimals(decimals);spin.setRange(0,999999)
 spin.setSingleStep(1 if product['unit']=='u' else 0.25)
 spin.setValue(self.cart[pid]/1000)
 dlg=QDialog(self);dlg.setWindowTitle('Editar cantidad · '+product['name'])
 form=QVBoxLayout(dlg);form.setContentsMargins(20,18,20,18);form.setSpacing(12)
 description=QLabel('Cantidad del carrito en '+product['unit']+'. Ingresá 0 para quitarla.');description.setWordWrap(True);form.addWidget(description)
 form.addWidget(spin)
 row=QHBoxLayout();save=QPushButton('Aplicar cantidad');save.clicked.connect(dlg.accept);cancel=QPushButton('Cancelar');cancel.clicked.connect(dlg.reject)
 row.addWidget(save);row.addWidget(cancel);form.addLayout(row)
 if dlg.exec()!=QDialog.DialogCode.Accepted:return
 milli_amount=round(spin.value()*1000)
 _f21_change_cart(self,pid,set_amount=milli_amount)


def _f21_add(self):
 pid=self.pos_product.currentData()
 if pid is None:raise ERPError('Buscá o escaneá un producto antes de agregarlo.')
 qty=self.pos_sale_qty_milli()
 next_amount=self.cart.get(pid,0)+qty
 _f21_can_add(self,pid,next_amount)
 self.cart[pid]=next_amount
 _f21_render_cart(self)
 self.pos_barcode.clear();self.pos_barcode.setFocus()


def _f21_add_one(self,pid):
 p=self.erp.entity('products',pid)
 step=1000 # una unidad, un kilogramo o un litro según el producto
 _f21_change_cart(self,pid,delta=step)


def _f21_less_one(self,pid):
 if pid not in self.cart:return
 p=self.erp.entity('products',pid)
 if self.cart[pid]<=1000:
  _f21_remove(self,pid)
 else:
  _f21_change_cart(self,pid,delta=-1000)


def _f21_render_cart(self):
 if not hasattr(self,'pos_cart'):return
 selected=_f21_cart_row_pid(self)
 table=self.pos_cart
 table.setUpdatesEnabled(False)
 try:
  table.setRowCount(0)
  bid=self.pos_branch.currentData()
  for pid,qty_milli in self.cart.items():
   product=self.erp.entity('products',pid)
   price=self.erp.effective_price(pid,bid)
   subtotal=total_for(qty_milli,price)
   row=table.rowCount();table.insertRow(row)
   photo=QLabel();photo.setAlignment(Qt.AlignmentFlag.AlignCenter)
   pix=_f18_pixmap(self,product.get('photo',''),QSize(46,46))
   if pix.isNull():photo.setText('—')
   else:photo.setPixmap(pix)
   table.setCellWidget(row,1,photo)
   labels=['', '',product.get('name') or 'Producto sin descripción',quantity(qty_milli)+' '+product['unit'],self._money(price),self._money(subtotal),'']
   for c in (0,2,3,4,5):
    item=QTableWidgetItem(str(pid) if c==0 else labels[c]);item.setData(Qt.ItemDataRole.UserRole,int(pid))
    if c in (3,4,5):item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter|Qt.AlignmentFlag.AlignRight)
    table.setItem(row,c,item)
   actions=QWidget();h=QHBoxLayout(actions);h.setContentsMargins(2,2,2,2);h.setSpacing(4)
   for symbol,action_cb,tip in [('−',lambda pid=pid:_f21_less_one(self,pid),'Quitar una unidad base'),('+',lambda pid=pid:_f21_add_one(self,pid),'Agregar una unidad base'),('✕',lambda pid=pid:_f21_remove(self,pid),'Quitar producto completo')]:
    b=QPushButton(symbol);b.setObjectName('f21RowAction');b.setFixedSize(34,34);b.setToolTip(tip)
    b.clicked.connect(lambda _=False,fn=action_cb:self.safe(fn));h.addWidget(b)
   table.setCellWidget(row,6,actions);table.setRowHeight(row,60)
   if selected==pid:table.selectRow(row)
 finally:table.setUpdatesEnabled(True);table.viewport().update()
 if hasattr(self,'f21_cart_caption'):
  self.f21_cart_caption.setText(f'ARTÍCULOS EN EL CARRITO  ·  {len(self.cart)} tipos  ·  {sum(q/1000 for q in self.cart.values()):g} unidades base acumuladas')
 if hasattr(self,'pos_total'):self.pos_total.setText(self._money(_f21_cart_total(self)))
 if hasattr(self,'f20_total'):_f20_offer_preview(self)
 if hasattr(self,'f21_empty'):
  self.f21_empty.setVisible(not self.cart)


def _f21_pick_product(self):
 dialog=_F21BuscarProducto(self)
 if dialog.exec()!=QDialog.DialogCode.Accepted:return
 index=self.pos_product.findData(dialog.pid)
 if index<0:raise ERPError('Producto no disponible en el selector de venta.')
 self.pos_product.setCurrentIndex(index)
 self.pos_qty.setValue(1)
 self.pos_barcode.setFocus()


def _f21_history(self):
 dialog=QDialog(self);dialog.setWindowTitle('Historial de ventas y tickets internos')
 dialog.resize(900,560);v=QVBoxLayout(dialog)
 title=QLabel('Historial de ventas');title.setObjectName('heading');v.addWidget(title)
 rows=_f17_pos_history_rows(self)
 table=table_widget(rows,['id','created_at','branch','total_cents','payment','status'])
 table.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch)
 v.addWidget(table,1)
 bar=QHBoxLayout();bar.addStretch(1)
 def chosen():
  row=table.currentRow()
  if row<0:raise ERPError('Seleccioná la venta que querés consultar.')
  item=table.item(row,0)
  return int(item.data(Qt.ItemDataRole.UserRole))
 def print_selected():
  from .ticket_printer import TicketPrinterDialog
  sale_id=chosen(); TicketPrinterDialog(dialog,self.erp.sale_ticket(sale_id)).exec()
 def export_selected():
  sale_id=chosen();dest,_=QFileDialog.getSaveFileName(dialog,'Exportar ticket interno','','Texto (*.txt)')
  if dest:Path(dest).write_text(self.erp.sale_ticket(sale_id),encoding='utf-8')
 def void_selected():
  sale_id=chosen();self.table=table;self.pos_void();dialog.accept()
 for label,fn in [('Imprimir ticket',print_selected),('Exportar ticket',export_selected)]:
  b=QPushButton(label);b.clicked.connect(lambda _=False,fn=fn:self.safe(fn));bar.addWidget(b)
 if self.erp.available('pos','void'):
  b=QPushButton('Anular venta registrada');b.clicked.connect(lambda _=False:self.safe(void_selected));bar.addWidget(b)
 close=QPushButton('Cerrar');close.clicked.connect(dialog.accept);bar.addWidget(close);v.addLayout(bar)
 dialog.exec()


def _f21_refresh(self):
 bid=self.pos_branch.currentData()
 if bid is None:return
 session=self.erp.cash_session(bid)
 if hasattr(self,'pos_status'):
  self.pos_status.setText(('● CAJA ABIERTA  ·  Turno #'+str(session['id'])+'  ·  Fondo '+self._money(session['opening_cents'])) if session else '● CAJA CERRADA  ·  Abrí caja antes de cobrar')
  self.pos_status.setStyleSheet('color:#0D683C;font-weight:800;' if session else 'color:#A82317;font-weight:800;')
 _f21_render_cart(self)


def _f21_set_expanded(self):
 expanded=not getattr(self,'f21_fullscreen',False);self.f21_fullscreen=expanded
 side=getattr(self,'_f18_sidebar',None)
 if side is not None:side.setVisible(not expanded)
 if getattr(self,'_f18_nav_control',None):
  self._f18_nav_control.setText('☰ Mostrar menú' if expanded else '◀ Ocultar menú')
 self.f21_expand.setText('◱ Restaurar caja' if expanded else '⛶ Expandir caja')
 self.f21_detail.setVisible(not expanded)
 self.pos_cart.setMinimumHeight(360 if expanded else 260)
 self.pos_barcode.setFocus()


def _f21_page_pos(self):
 self.search.hide()
 # No renderizar el catálogo duplicado de F17-F20 ni los dos carritos de F20.
 banner=self.content.widget().findChild(QFrame,'banner')
 if banner:banner.hide()
 self.outer.setContentsMargins(14,12,14,13);self.outer.setSpacing(8)
 self.content.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
 self.f21_fullscreen=False
 titlebar=QHBoxLayout();titlebar.setSpacing(7)
 name=QLabel('CAJA · VENTA EN CURSO');name.setObjectName('f21Title');titlebar.addWidget(name)
 titlebar.addStretch(1)
 self.f21_expand=QPushButton('⛶ Expandir caja');self.f21_expand.clicked.connect(lambda _=False:_f21_set_expanded(self));titlebar.addWidget(self.f21_expand)
 history=QPushButton('Historial / tickets');history.clicked.connect(lambda _=False:self.safe(lambda:_f21_history(self)));titlebar.addWidget(history)
 self.outer.addLayout(titlebar)
 session_row=QHBoxLayout();session_row.setSpacing(9)
 session_row.addWidget(QLabel('Sucursal:'))
 self.pos_branch=QComboBox();
 for label,id in self.branch_opts():self.pos_branch.addItem(label,id)
 self.pos_branch.currentIndexChanged.connect(lambda *_:self.safe(lambda:_f21_refresh(self)))
 session_row.addWidget(self.pos_branch)
 self.pos_status=QLabel('');session_row.addWidget(self.pos_status,1)
 self.f21_open=QPushButton('Abrir caja');self.f21_open.clicked.connect(lambda _=False:self.safe(self.pos_open));session_row.addWidget(self.f21_open)
 self.f21_close=QPushButton('Cerrar / arqueo');self.f21_close.clicked.connect(lambda _=False:self.safe(self.pos_close));session_row.addWidget(self.f21_close)
 self.outer.addLayout(session_row)

 # Scanner / entry: always present, no duplicate catalog table.
 actions_card=QFrame();actions_card.setObjectName('f21ScanCard');a=QVBoxLayout(actions_card);a.setContentsMargins(12,10,12,10);a.setSpacing(7)
 scan=QHBoxLayout();scan.setSpacing(8)
 self.pos_barcode=QLineEdit();self.pos_barcode.setMinimumHeight(42);self.pos_barcode.setPlaceholderText('▥ ESCANEAR CÓDIGO DE BARRAS + ENTER')
 self.pos_barcode.returnPressed.connect(lambda:self.safe(self.pos_scan));scan.addWidget(self.pos_barcode,1)
 picker=QPushButton('⌕ Buscar en catálogo');picker.clicked.connect(lambda _=False:self.safe(lambda:_f21_pick_product(self)));scan.addWidget(picker)
 self.pos_product=QComboBox();self.pos_product.setEditable(True)
 self.pos_product.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
 self.pos_product.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
 self.pos_product.setMinimumContentsLength(12)
 for product in self.erp.catalogs('products'):
  if product.get('active'):self.pos_product.addItem(f'{product["name"]} · {product["sku"]}',int(product['id']))
 self.pos_product.currentIndexChanged.connect(self.pos_update_presentation)
 self.pos_presentation=QComboBox();self.pos_presentation.currentIndexChanged.connect(self.pos_update_sale_hint)
 self.pos_qty=QuantitySpinBox();self.pos_qty.setRange(.001,999999);self.pos_qty.setDecimals(3);self.pos_qty.setValue(1)
 self.pos_qty.valueChanged.connect(self.pos_update_sale_hint)
 self.pos_sale_hint=QLabel('');self.pos_sale_hint.setObjectName('helper');self.pos_sale_hint.setWordWrap(True)
 self.pos_update_presentation()
 self.pos_product.setMinimumWidth(150);self.pos_presentation.setMinimumWidth(125)
 scan.addWidget(QLabel('Producto:'));scan.addWidget(self.pos_product,2)
 a.addLayout(scan)
 detail=QHBoxLayout();detail.setSpacing(8)
 detail.addWidget(QLabel('Venta por:'));detail.addWidget(self.pos_presentation,2)
 detail.addWidget(QLabel('Cantidad:'));detail.addWidget(self.pos_qty,1)
 add=QPushButton('＋ Agregar al carrito');add.setObjectName('primary');add.clicked.connect(lambda _=False:self.safe(lambda:_f21_add(self)));detail.addWidget(add)
 self.f21_detail=QWidget();self.f21_detail.setLayout(detail);a.addWidget(self.f21_detail)
 self.outer.addWidget(actions_card)

 # Main cart: visible on every POS state, selected products only.
 cart_frame=QFrame();cart_frame.setObjectName('f21CartCard');v=QVBoxLayout(cart_frame);v.setContentsMargins(12,10,12,10);v.setSpacing(8)
 cap=QHBoxLayout();self.f21_cart_caption=QLabel('ARTÍCULOS EN EL CARRITO');self.f21_cart_caption.setObjectName('f21CartHeading');cap.addWidget(self.f21_cart_caption,1)
 edit=QPushButton('Editar cantidad');edit.clicked.connect(lambda _=False:self.safe(lambda:_f21_edit_qty(self)));cap.addWidget(edit)
 remove=QPushButton('Quitar seleccionado');remove.clicked.connect(lambda _=False:self.safe(lambda:_f21_remove(self)));cap.addWidget(remove)
 v.addLayout(cap)
 self.pos_cart=QTableWidget(0,7);self.pos_cart.setObjectName('f21CartTable')
 self.pos_cart.setHorizontalHeaderLabels(['ID','Foto','Producto escaneado','Cantidad','Precio unitario','Subtotal','Acciones'])
 self.pos_cart.verticalHeader().hide();self.pos_cart.setColumnHidden(0,True)
 self.pos_cart.setAlternatingRowColors(True)
 self.pos_cart.setSortingEnabled(False)
 self.pos_cart.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
 self.pos_cart.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
 self.pos_cart.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
 self.pos_cart.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
 self.pos_cart.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
 self.pos_cart.setMinimumHeight(270)
 hdr=self.pos_cart.horizontalHeader();hdr.setStretchLastSection(False)
 for col,width in ((1,74),(3,105),(4,125),(5,130),(6,135)):
  hdr.setSectionResizeMode(col,QHeaderView.ResizeMode.Fixed);hdr.resizeSection(col,width)
 hdr.setSectionResizeMode(2,QHeaderView.ResizeMode.Stretch)
 self.pos_cart.doubleClicked.connect(lambda *_:self.safe(lambda:_f21_edit_qty(self)))
 v.addWidget(self.pos_cart,1)
 self.f21_empty=QLabel('Carrito vacío · Escaneá un producto o usá «Buscar en catálogo».');self.f21_empty.setAlignment(Qt.AlignmentFlag.AlignCenter);self.f21_empty.setObjectName('helper');v.addWidget(self.f21_empty)
 self.outer.addWidget(cart_frame,1)

 # Permanent checkout panel: no horizontal clipping of money or buttons.
 checkout=QFrame();checkout.setObjectName('f21CheckoutCard');foot=QVBoxLayout(checkout);foot.setContentsMargins(14,12,14,12);foot.setSpacing(8)
 payment=QHBoxLayout();payment.setSpacing(7)
 payment.addWidget(QLabel('Cliente'))
 self.pos_customer=QComboBox();self.pos_customer.addItem('Consumidor final',None)
 for label,key in combo_data(self.erp,'customers'):self.pos_customer.addItem(label,key)
 payment.addWidget(self.pos_customer,2)
 payment.addWidget(QLabel('Medio de pago'))
 self.pos_payment=QComboBox()
 for k,label in [('cash','Efectivo'),('debit','Débito'),('credit','Crédito'),('transfer','Transferencia'),('qr','QR'),('check','Cheque')]:self.pos_payment.addItem(label,k)
 payment.addWidget(self.pos_payment,1)
 payment.addWidget(QLabel('Cupón'))
 self.f20_coupon_code=QLineEdit();self.f20_coupon_code.setPlaceholderText('NXM-...');self.f20_coupon_code.setMaximumWidth(170);payment.addWidget(self.f20_coupon_code,1)
 foot.addLayout(payment)
 amounts=QHBoxLayout();amounts.setSpacing(10)
 def money_area(label,large=False):
  box=QVBoxLayout();caption=QLabel(label);caption.setObjectName('f21SmallText');box.addWidget(caption)
  number=QLabel('ARS 0,00');number.setObjectName('f21GrandTotal' if large else 'f21Amount');box.addWidget(number)
  amounts.addLayout(box,2 if large else 1)
  return number
 self.f20_subtotal=money_area('SUBTOTAL');self.f20_discount=money_area('DESCUENTO');self.f20_total=money_area('TOTAL A COBRAR',True)
 self.pos_total=QLabel('');self.pos_total.hide()
 collect=QPushButton('✓ COBRAR Y CERRAR VENTA');collect.setObjectName('f21CollectButton');collect.setMinimumHeight(58)
 collect.clicked.connect(lambda _=False:self.safe(self.pos_checkout));collect.setEnabled(self.erp.available('pos','sell'));amounts.addWidget(collect)
 foot.addLayout(amounts)
 self.f20_coupon_status=QLabel('');self.f20_coupon_status.setObjectName('helper');self.f20_coupon_status.setWordWrap(True)
 self.f20_reward=QLabel('');self.f20_reward.setObjectName('helper');self.f20_reward.setWordWrap(True)
 foot.addWidget(self.f20_coupon_status);foot.addWidget(self.f20_reward)
 self.outer.addWidget(checkout)
 self.f20_coupon_code.textChanged.connect(lambda *_:_f20_offer_preview(self))
 self.pos_customer.currentIndexChanged.connect(lambda *_:_f20_offer_preview(self))
 self.pos_payment.currentIndexChanged.connect(lambda *_:_f20_offer_preview(self))
 # Separate historical table solely for legacy ticket/void hooks; not shown in POS.
 self.table=table_widget([],['id','created_at','branch_id','total_cents'])
 _f21_refresh(self)
 self.pos_barcode.setFocus()


# Preserve F20 coupon, ERP checkout and ticket logic. Replace visual POS only.
App.page_pos=_f21_page_pos
App.render_cart=_f21_render_cart
App.pos_refresh=_f21_refresh
App.pos_add=_f21_add
App.pos_remove=_f21_remove


# =====================
# F22 — Caja visual tipo app con carrito único estable
# =====================

def _f22_load_product_combo(self,selected_pid=None):
 bid=self.pos_branch.currentData() if hasattr(self,'pos_branch') else None
 current=selected_pid if selected_pid is not None else (self.pos_product.currentData() if hasattr(self,'pos_product') else None)
 if not hasattr(self,'pos_product'):return
 self.pos_product.blockSignals(True);self.pos_product.clear()
 for p in self.erp.catalogs('products'):
  if not p.get('active',1):continue
  price=self.erp.effective_price(p['id'],bid) if bid else p['price_cents']
  label=f'{p.get("name") or "Producto sin nombre"} · {p.get("sku") or p.get("barcode") or "SIN-COD"} · {self._money(price)}'
  self.pos_product.addItem(label,p['id'])
 idx=self.pos_product.findData(current)
 if idx<0 and self.pos_product.count():idx=0
 if idx>=0:self.pos_product.setCurrentIndex(idx)
 self.pos_product.blockSignals(False)
 self.pos_update_presentation()
 _f22_update_preview(self)


def _f22_catalog_rows(self):
 bid=self.pos_branch.currentData() if hasattr(self,'pos_branch') else None
 query=(self.f22_catalog_filter.text().strip().casefold() if hasattr(self,'f22_catalog_filter') else '')
 balances={}
 if bid:
  for b in self.erp.all('SELECT product_id,onhand_milli,reserved_milli FROM stock_balances WHERE branch_id=?',(bid,)):
   balances[b['product_id']]=int(b['onhand_milli'])-int(b['reserved_milli'])
 rows=[]
 for p in self.erp.catalogs('products'):
  if not p.get('active',1):continue
  hay=' '.join(str(p.get(k,'') or '') for k in ('name','sku','barcode')).casefold()
  if query and query not in hay:continue
  rows.append((p,self.erp.effective_price(p['id'],bid) if bid else p['price_cents'],balances.get(p['id'],0)))
 rows.sort(key=lambda x:(x[0].get('name') or '').casefold())
 return rows


def _f22_catalog_row_pid(self):
 table=getattr(self,'f22_catalog',None)
 if table is None:return None
 row=table.currentRow()
 if row<0:return None
 item=table.item(row,2)
 return int(item.data(Qt.ItemDataRole.UserRole)) if item and item.data(Qt.ItemDataRole.UserRole) is not None else None


def _f22_fill_catalog(self):
 table=getattr(self,'f22_catalog',None)
 if table is None:return
 selected=_f22_catalog_row_pid(self)
 rows=_f22_catalog_rows(self)
 table.setUpdatesEnabled(False)
 try:
  table.setRowCount(0)
  for p,price,available in rows:
   row=table.rowCount();table.insertRow(row)
   photo=QLabel();photo.setAlignment(Qt.AlignmentFlag.AlignCenter)
   pix=_f18_pixmap(self,p.get('photo',''),QSize(48,48))
   if pix.isNull():photo.setText('—')
   else:photo.setPixmap(pix)
   table.setCellWidget(row,0,photo)
   fields=[p.get('sku') or p.get('barcode') or '—',p.get('name') or 'Producto sin nombre',self._money(price),quantity(available)+' '+str(p.get('unit','u'))]
   for col,text in enumerate(fields,1):
    item=QTableWidgetItem(str(text));item.setData(Qt.ItemDataRole.UserRole,int(p['id']))
    if col in (3,4):item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter|Qt.AlignmentFlag.AlignRight)
    table.setItem(row,col,item)
   table.setRowHeight(row,58)
   if selected==p['id']:table.selectRow(row)
  if table.currentRow()<0 and table.rowCount():table.selectRow(0)
 finally:
  table.setUpdatesEnabled(True);table.viewport().update()
 if hasattr(self,'f22_catalog_caption'):self.f22_catalog_caption.setText(f'Catálogo rápido con fotos · {table.rowCount()} producto(s) visibles')


def _f22_pick_from_catalog(self,add=False):
 pid=_f22_catalog_row_pid(self)
 if pid is None:return
 idx=self.pos_product.findData(pid)
 if idx>=0:self.pos_product.setCurrentIndex(idx)
 self.pos_barcode.clear()
 self.pos_barcode.setFocus()
 if add:self.pos_add()


def _f22_cart_row_pid(self):
 table=getattr(self,'pos_cart',None)
 if table is None:return None
 row=table.currentRow()
 if row<0:return None
 item=table.item(row,2)
 return int(item.data(Qt.ItemDataRole.UserRole)) if item and item.data(Qt.ItemDataRole.UserRole) is not None else None


def _f22_cart_total(self):
 bid=self.pos_branch.currentData() if hasattr(self,'pos_branch') else None
 if bid is None:return 0
 return sum(total_for(amount,self.erp.effective_price(pid,bid)) for pid,amount in self.cart.items())


def _f22_change_cart(self,pid,delta=0,set_amount=None):
 if pid not in self.cart and set_amount is None and delta==0:return
 amount=int(set_amount if set_amount is not None else self.cart.get(pid,0)+delta)
 if amount<=0:
  self.cart.pop(pid,None)
 else:
  _f21_can_add(self,pid,amount)
  self.cart[pid]=amount
 _f22_render_cart(self)
 self.pos_barcode.setFocus()


def _f22_add(self):
 pid=self.pos_product.currentData()
 if pid is None:raise ERPError('Buscá o escaneá un producto antes de agregarlo.')
 qty=self.pos_sale_qty_milli()
 next_amount=self.cart.get(pid,0)+qty
 _f21_can_add(self,pid,next_amount)
 self.cart[pid]=next_amount
 _f22_render_cart(self)
 self.pos_barcode.clear();self.pos_qty.setValue(1);self.pos_barcode.setFocus()
 if hasattr(self,'f22_catalog'):
  idx=self.f22_catalog.currentRow()
  if idx>=0:self.f22_catalog.scrollToItem(self.f22_catalog.item(idx,2))


def _f22_remove(self,pid=None):
 if pid is None:pid=_f22_cart_row_pid(self)
 if pid is None:raise ERPError('Seleccioná un producto del carrito para retirarlo.')
 self.cart.pop(pid,None)
 _f22_render_cart(self)
 self.pos_barcode.setFocus()


def _f22_edit_qty(self,pid=None):
 if pid is None:pid=_f22_cart_row_pid(self)
 if pid not in self.cart:raise ERPError('Seleccioná una línea del carrito para modificar la cantidad.')
 product=self.erp.entity('products',pid)
 spin=QuantitySpinBox();spin.setRange(0,999999)
 spin.setValue(self.cart[pid]/1000)
 if product['unit']=='u':spin.setDecimals(0);spin.setSingleStep(1)
 else:spin.setDecimals(3);spin.setSingleStep(0.25)
 dlg=QDialog(self);dlg.setWindowTitle('Editar cantidad · '+(product.get('name') or 'Producto'))
 lay=QVBoxLayout(dlg);lay.setContentsMargins(18,16,18,16);lay.setSpacing(10)
 msg=QLabel('Cambiá la cantidad del artículo en el carrito. Si ingresás 0, el artículo se elimina.');msg.setWordWrap(True);lay.addWidget(msg)
 lay.addWidget(spin)
 row=QHBoxLayout();row.addStretch(1)
 ok=QPushButton('Aplicar');ok.setObjectName('primary');ok.clicked.connect(dlg.accept)
 cancel=QPushButton('Cancelar');cancel.clicked.connect(dlg.reject)
 row.addWidget(ok);row.addWidget(cancel);lay.addLayout(row)
 if dlg.exec()!=QDialog.DialogCode.Accepted:return
 _f22_change_cart(self,pid,set_amount=round(spin.value()*1000))


def _f22_render_cart(self):
 table=getattr(self,'pos_cart',None)
 if table is None:return
 selected=_f22_cart_row_pid(self)
 bid=self.pos_branch.currentData() if hasattr(self,'pos_branch') else None
 table.setUpdatesEnabled(False)
 try:
  table.setRowCount(0)
  for pid,qty_milli in self.cart.items():
   product=self.erp.entity('products',pid)
   price=self.erp.effective_price(pid,bid)
   subtotal=total_for(qty_milli,price)
   row=table.rowCount();table.insertRow(row)
   photo=QLabel();photo.setAlignment(Qt.AlignmentFlag.AlignCenter)
   pix=_f18_pixmap(self,product.get('photo',''),QSize(46,46))
   if pix.isNull():photo.setText('—')
   else:photo.setPixmap(pix)
   table.setCellWidget(row,1,photo)
   name=(product.get('name') or 'Producto sin nombre')
   qty_text=quantity(qty_milli)+' '+product.get('unit','u')
   fields=['',name,qty_text,self._money(price),self._money(subtotal),'']
   for col,text in enumerate(fields):
    real_col=0 if col==0 else col+1
    if real_col==1:continue
    item=QTableWidgetItem(str(pid) if real_col==0 else str(text))
    item.setData(Qt.ItemDataRole.UserRole,int(pid))
    if real_col in (3,4,5):item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter|Qt.AlignmentFlag.AlignRight)
    table.setItem(row,real_col,item)
   actions=QWidget();h=QHBoxLayout(actions);h.setContentsMargins(2,2,2,2);h.setSpacing(4)
   for symbol,cb,tip in [('−',lambda pid=pid:_f22_change_cart(self,pid,delta=-1000),'Restar una unidad base'),('＋',lambda pid=pid:_f22_change_cart(self,pid,delta=1000),'Sumar una unidad base'),('✕',lambda pid=pid:_f22_remove(self,pid),'Quitar producto del carrito')]:
    b=QPushButton(symbol);b.setObjectName('f22RowAction');b.setFixedSize(34,34);b.setToolTip(tip);b.clicked.connect(lambda _=False,fn=cb:self.safe(fn));h.addWidget(b)
   table.setCellWidget(row,6,actions);table.setRowHeight(row,58)
   if selected==pid:table.selectRow(row)
 finally:
  table.setUpdatesEnabled(True);table.viewport().update()
 if hasattr(self,'f22_cart_caption'):self.f22_cart_caption.setText(f'Artículos en el carrito · {len(self.cart)} tipo(s) · {sum(q/1000 for q in self.cart.values()):g} unidades base acumuladas')
 if hasattr(self,'f22_empty'):self.f22_empty.setVisible(not self.cart)
 if hasattr(self,'f20_total'):_f20_offer_preview(self)


def _f22_update_preview(self,*_):
 if not hasattr(self,'f22_preview_name'):return
 pid=self.pos_product.currentData() if hasattr(self,'pos_product') else None
 if pid is None:
  self.f22_preview_name.setText('Sin producto seleccionado')
  self.f22_preview_price.setText('ARS 0,00')
  self.f22_preview_meta.setText('Escaneá un código o elegí un producto del catálogo.')
  self.f22_preview_photo.clear();return
 p=self.erp.entity('products',pid)
 bid=self.pos_branch.currentData() if hasattr(self,'pos_branch') else None
 price=self.erp.effective_price(pid,bid) if bid else p['price_cents']
 bal=self.erp.one('SELECT onhand_milli-reserved_milli AS available FROM stock_balances WHERE product_id=? AND branch_id=?',(pid,bid)) if bid else None
 available=int(bal['available']) if bal else 0
 pix=_f18_pixmap(self,p.get('photo',''),QSize(92,92))
 if pix.isNull():self.f22_preview_photo.setText('Sin\nfoto')
 else:self.f22_preview_photo.setPixmap(pix)
 self.f22_preview_name.setText(p.get('name') or 'Producto sin nombre')
 self.f22_preview_price.setText(self._money(price))
 kind=self.pos_presentation.currentData() if hasattr(self,'pos_presentation') else 'base'
 kind_name='Unidad base' if kind=='base' else 'Paquete' if kind=='pack' else 'Caja'
 qty_milli=self.pos_sale_qty_milli() if hasattr(self,'pos_qty') else 0
 self.f22_preview_meta.setText(f'SKU: {p.get("sku") or p.get("barcode") or "SIN-COD"} · Disponible: {quantity(available)} {p.get("unit","u")}\n{kind_name}: {quantity(qty_milli)} {p.get("unit","u")} · Subtotal estimado: {self._money(total_for(qty_milli,price))}')


def _f22_refresh(self):
 bid=self.pos_branch.currentData() if hasattr(self,'pos_branch') else None
 if bid is None:return
 session=self.erp.cash_session(bid)
 if hasattr(self,'pos_status'):
  self.pos_status.setText(('● CAJA ABIERTA  ·  Turno #'+str(session['id'])+'  ·  Fondo '+self._money(session['opening_cents'])) if session else '● CAJA CERRADA  ·  Abrí caja antes de cobrar')
  self.pos_status.setStyleSheet('color:#0D683C;font-weight:900;' if session else 'color:#A82317;font-weight:900;')
 _f22_load_product_combo(self)
 _f22_fill_catalog(self)
 _f22_update_preview(self)
 _f22_render_cart(self)
 self.pos_update_sale_hint()


def _f22_set_expanded(self):
 expanded=not getattr(self,'f22_expanded',False)
 self.f22_expanded=expanded
 side=getattr(self,'_f18_sidebar',None)
 if side is not None:side.setVisible(not expanded)
 if getattr(self,'_f18_nav_control',None):self._f18_nav_control.setText('☰ Mostrar menú' if expanded else '◀ Ocultar menú')
 if hasattr(self,'f22_expand_btn'):self.f22_expand_btn.setText('▥ Vista normal' if expanded else '⛶ Expandir caja')
 if hasattr(self,'f22_splitter'):self.f22_splitter.setSizes([700,500] if expanded else [820,380])
 if hasattr(self,'f22_catalog'):self.f22_catalog.setMinimumHeight(430 if expanded else 300)
 if hasattr(self,'pos_cart'):self.pos_cart.setMinimumHeight(430 if expanded else 290)
 self.pos_barcode.setFocus()


def _f22_page_pos(self):
    self.search.hide()

    banner = self.content.widget().findChild(QFrame, 'banner')
    if banner:
        banner.hide()

    self.outer.setContentsMargins(14, 12, 14, 13)
    self.outer.setSpacing(10)

    # Permite que aparezca desplazamiento horizontal
    # solamente cuando la pantalla realmente lo necesita.
    self.content.setHorizontalScrollBarPolicy(
        Qt.ScrollBarPolicy.ScrollBarAsNeeded
    )

    self.f22_expanded = False

    # =========================================================
    # CABECERA
    # =========================================================

    titlebar = QHBoxLayout()
    titlebar.setSpacing(8)

    title = QLabel('CAJA · VENTA EN CURSO')
    title.setObjectName('f22Title')
    titlebar.addWidget(title)

    titlebar.addStretch(1)

    self.f22_expand_btn = QPushButton('⛶ Expandir caja')
    self.f22_expand_btn.setObjectName('f22GhostButton')
    self.f22_expand_btn.clicked.connect(
        lambda _=False: _f22_set_expanded(self)
    )
    titlebar.addWidget(self.f22_expand_btn)

    history = QPushButton('🧾 Historial / tickets')
    history.setObjectName('f22GhostButton')
    history.clicked.connect(
        lambda _=False: self.safe(lambda: _f21_history(self))
    )
    titlebar.addWidget(history)

    self.f21_open = QPushButton('Abrir caja')
    self.f21_open.clicked.connect(
        lambda _=False: self.safe(self.pos_open)
    )
    titlebar.addWidget(self.f21_open)

    self.f21_close = QPushButton('Cerrar / arqueo')
    self.f21_close.clicked.connect(
        lambda _=False: self.safe(self.pos_close)
    )
    titlebar.addWidget(self.f21_close)

    self.outer.addLayout(titlebar)

    # =========================================================
    # SESIÓN / SUCURSAL
    # =========================================================

    session = QHBoxLayout()
    session.setSpacing(8)

    session.addWidget(QLabel('Sucursal:'))

    self.pos_branch = QComboBox()

    for label, id in self.branch_opts():
        self.pos_branch.addItem(label, id)

    self.pos_status = QLabel('')
    self.pos_status.setObjectName('f22Status')

    self.pos_branch.currentIndexChanged.connect(
        lambda *_: self.safe(lambda: _f22_refresh(self))
    )

    session.addWidget(self.pos_branch)
    session.addWidget(self.pos_status, 1)

    self.outer.addLayout(session)

    # =========================================================
    # ESCANEO / SELECCIÓN DE PRODUCTO
    # =========================================================

    scan_card = QFrame()
    scan_card.setObjectName('f22ScanCard')

    scan_l = QVBoxLayout(scan_card)
    scan_l.setContentsMargins(14, 12, 14, 12)
    scan_l.setSpacing(8)

    line1 = QHBoxLayout()
    line1.setSpacing(8)

    self.pos_barcode = QLineEdit()
    self.pos_barcode.setMinimumHeight(42)
    self.pos_barcode.setPlaceholderText(
        '▥ ESCANEAR CÓDIGO DE BARRAS + ENTER'
    )
    self.pos_barcode.returnPressed.connect(
        lambda: self.safe(self.pos_scan)
    )

    find = QPushButton('⌕ Buscar en catálogo')
    find.setObjectName('f22GhostButton')
    find.clicked.connect(
        lambda _=False: self.safe(
            lambda: _f22_pick_from_catalog(self, False)
        )
    )

    self.pos_product = QComboBox()
    self.pos_product.setMinimumWidth(340)

    self.pos_product.currentIndexChanged.connect(
        self.pos_update_presentation
    )
    self.pos_product.currentIndexChanged.connect(
        lambda *_: _f22_update_preview(self)
    )

    line1.addWidget(self.pos_barcode, 2)
    line1.addWidget(find)
    line1.addWidget(QLabel('Producto:'))
    line1.addWidget(self.pos_product, 4)

    scan_l.addLayout(line1)

    line2 = QHBoxLayout()
    line2.setSpacing(8)

    self.pos_presentation = QComboBox()
    self.pos_presentation.setMinimumWidth(180)
    self.pos_presentation.currentIndexChanged.connect(
        self.pos_update_sale_hint
    )
    self.pos_presentation.currentIndexChanged.connect(
        lambda *_: _f22_update_preview(self)
    )

    self.pos_qty = QuantitySpinBox()
    self.pos_qty.setRange(.001, 999999)
    self.pos_qty.setDecimals(3)
    self.pos_qty.setValue(1)
    self.pos_qty.valueChanged.connect(
        self.pos_update_sale_hint
    )
    self.pos_qty.valueChanged.connect(
        lambda *_: _f22_update_preview(self)
    )

    scan_capture = QPushButton('Escanear / Probar lector')
    scan_capture.clicked.connect(
        lambda _=False: self.safe(self.pos_capture)
    )

    add = QPushButton('＋ Agregar al carrito')
    add.setObjectName('primary')
    add.clicked.connect(
        lambda _=False: self.safe(lambda: _f22_add(self))
    )

    line2.addWidget(QLabel('Venta por:'))
    line2.addWidget(self.pos_presentation, 2)
    line2.addWidget(QLabel('Cantidad:'))
    line2.addWidget(self.pos_qty, 1)
    line2.addWidget(scan_capture)
    line2.addWidget(add)

    scan_l.addLayout(line2)

    self.pos_sale_hint = QLabel('')
    self.pos_sale_hint.setObjectName('helper')
    self.pos_sale_hint.setWordWrap(True)
    scan_l.addWidget(self.pos_sale_hint)

    self.outer.addWidget(scan_card)

    # =========================================================
    # SPLITTER PRINCIPAL
    # CATÁLOGO  <----->  CARRITO
    # =========================================================

    self.f22_splitter = QSplitter(Qt.Orientation.Horizontal)
    self.f22_splitter.setChildrenCollapsible(False)
    self.f22_splitter.setHandleWidth(10)

    # =========================================================
    # PANEL IZQUIERDO — CATÁLOGO
    # =========================================================

    left = QFrame()
    left.setObjectName('f22CatalogCard')
    left.setMinimumWidth(330)

    left_l = QVBoxLayout(left)
    left_l.setContentsMargins(12, 10, 12, 10)
    left_l.setSpacing(8)

    self.f22_catalog_caption = QLabel(
        'Catálogo rápido con fotos'
    )
    self.f22_catalog_caption.setObjectName(
        'f22SectionTitle'
    )
    left_l.addWidget(self.f22_catalog_caption)

    self.f22_preview = QFrame()
    self.f22_preview.setObjectName('f22PreviewCard')

    pv = QHBoxLayout(self.f22_preview)
    pv.setContentsMargins(12, 12, 12, 12)
    pv.setSpacing(12)

    self.f22_preview_photo = QLabel('Sin\nfoto')
    self.f22_preview_photo.setObjectName(
        'f22PreviewPhoto'
    )
    self.f22_preview_photo.setAlignment(
        Qt.AlignmentFlag.AlignCenter
    )
    self.f22_preview_photo.setFixedSize(100, 100)
    pv.addWidget(self.f22_preview_photo)

    txt = QVBoxLayout()

    self.f22_preview_name = QLabel(
        'Sin producto seleccionado'
    )
    self.f22_preview_name.setObjectName(
        'f22PreviewName'
    )
    self.f22_preview_name.setWordWrap(True)

    self.f22_preview_price = QLabel('ARS 0,00')
    self.f22_preview_price.setObjectName(
        'f22PreviewPrice'
    )

    self.f22_preview_meta = QLabel(
        'Escaneá un código o elegí un producto del catálogo.'
    )
    self.f22_preview_meta.setObjectName('helper')
    self.f22_preview_meta.setWordWrap(True)

    txt.addWidget(self.f22_preview_name)
    txt.addWidget(self.f22_preview_price)
    txt.addWidget(self.f22_preview_meta)

    pv.addLayout(txt, 1)
    left_l.addWidget(self.f22_preview)

    self.f22_catalog_filter = QLineEdit()
    self.f22_catalog_filter.setPlaceholderText(
        'Buscar producto dentro de caja...'
    )
    self.f22_catalog_filter.textChanged.connect(
        lambda *_: _f22_fill_catalog(self)
    )
    left_l.addWidget(self.f22_catalog_filter)

    self.f22_catalog = QTableWidget(0, 5)
    self.f22_catalog.setObjectName('f22CatalogTable')

    self.f22_catalog.setHorizontalHeaderLabels([
        'Foto',
        'SKU',
        'Nombre',
        'Precio de venta',
        'Disponible'
    ])

    self.f22_catalog.verticalHeader().hide()
    self.f22_catalog.setAlternatingRowColors(True)

    self.f22_catalog.setSelectionBehavior(
        QAbstractItemView.SelectionBehavior.SelectRows
    )

    self.f22_catalog.setSelectionMode(
        QAbstractItemView.SelectionMode.SingleSelection
    )

    self.f22_catalog.setEditTriggers(
        QAbstractItemView.EditTrigger.NoEditTriggers
    )

    # Scroll horizontal del catálogo
    self.f22_catalog.setHorizontalScrollBarPolicy(
        Qt.ScrollBarPolicy.ScrollBarAsNeeded
    )

    self.f22_catalog.setHorizontalScrollMode(
        QAbstractItemView.ScrollMode.ScrollPerPixel
    )

    self.f22_catalog.setMinimumHeight(300)

    h = self.f22_catalog.horizontalHeader()

    h.setSectionResizeMode(
        0,
        QHeaderView.ResizeMode.Fixed
    )
    h.resizeSection(0, 78)

    h.setSectionResizeMode(
        1,
        QHeaderView.ResizeMode.Fixed
    )
    h.resizeSection(1, 150)

    h.setSectionResizeMode(
        2,
        QHeaderView.ResizeMode.Stretch
    )

    h.setSectionResizeMode(
        3,
        QHeaderView.ResizeMode.Fixed
    )
    h.resizeSection(3, 130)

    h.setSectionResizeMode(
        4,
        QHeaderView.ResizeMode.Fixed
    )
    h.resizeSection(4, 115)

    self.f22_catalog.itemSelectionChanged.connect(
        lambda: _f22_pick_from_catalog(self, False)
    )

    self.f22_catalog.doubleClicked.connect(
        lambda *_: self.safe(
            lambda: _f22_pick_from_catalog(self, True)
        )
    )

    left_l.addWidget(self.f22_catalog, 1)

    self.f22_splitter.addWidget(left)

    # =========================================================
    # PANEL DERECHO — CARRITO
    # =========================================================

    right = QFrame()
    right.setObjectName('f22CartCard')
    right.setMinimumWidth(500)

    right_l = QVBoxLayout(right)
    right_l.setContentsMargins(12, 10, 12, 10)
    right_l.setSpacing(8)

    cap = QHBoxLayout()

    self.f22_cart_caption = QLabel(
        'Artículos en el carrito'
    )
    self.f22_cart_caption.setObjectName(
        'f22SectionTitle'
    )
    cap.addWidget(self.f22_cart_caption, 1)

    edit = QPushButton('Editar cantidad')
    edit.clicked.connect(
        lambda _=False: self.safe(
            lambda: _f22_edit_qty(self)
        )
    )

    remove = QPushButton('Quitar seleccionado')
    remove.clicked.connect(
        lambda _=False: self.safe(
            lambda: _f22_remove(self)
        )
    )

    cap.addWidget(edit)
    cap.addWidget(remove)
    right_l.addLayout(cap)

    self.pos_cart = QTableWidget(0, 7)
    self.pos_cart.setObjectName('f22CartTable')

    self.pos_cart.setHorizontalHeaderLabels([
        'ID',
        'Foto',
        'Producto',
        'Cantidad',
        'Precio unitario',
        'Subtotal',
        'Acciones'
    ])

    self.pos_cart.verticalHeader().hide()
    self.pos_cart.setColumnHidden(0, True)
    self.pos_cart.setAlternatingRowColors(True)

    self.pos_cart.setSelectionBehavior(
        QAbstractItemView.SelectionBehavior.SelectRows
    )

    self.pos_cart.setSelectionMode(
        QAbstractItemView.SelectionMode.SingleSelection
    )

    self.pos_cart.setEditTriggers(
        QAbstractItemView.EditTrigger.NoEditTriggers
    )

    # Scroll horizontal del carrito
    self.pos_cart.setHorizontalScrollBarPolicy(
        Qt.ScrollBarPolicy.ScrollBarAsNeeded
    )

    self.pos_cart.setHorizontalScrollMode(
        QAbstractItemView.ScrollMode.ScrollPerPixel
    )

    self.pos_cart.setMinimumHeight(290)

    self.pos_cart.doubleClicked.connect(
        lambda *_: self.safe(
            lambda: _f22_edit_qty(self)
        )
    )

    hh = self.pos_cart.horizontalHeader()

    hh.setSectionResizeMode(
        1,
        QHeaderView.ResizeMode.Fixed
    )
    hh.resizeSection(1, 76)

    hh.setSectionResizeMode(
        2,
        QHeaderView.ResizeMode.Stretch
    )

    hh.setSectionResizeMode(
        3,
        QHeaderView.ResizeMode.Fixed
    )
    hh.resizeSection(3, 110)

    hh.setSectionResizeMode(
        4,
        QHeaderView.ResizeMode.Fixed
    )
    hh.resizeSection(4, 128)

    hh.setSectionResizeMode(
        5,
        QHeaderView.ResizeMode.Fixed
    )
    hh.resizeSection(5, 128)

    hh.setSectionResizeMode(
        6,
        QHeaderView.ResizeMode.Fixed
    )
    hh.resizeSection(6, 138)

    right_l.addWidget(self.pos_cart, 1)

    self.f22_empty = QLabel(
        'Carrito vacío · escaneá un producto '
        'o elegí uno del catálogo visual.'
    )

    self.f22_empty.setAlignment(
        Qt.AlignmentFlag.AlignCenter
    )
    self.f22_empty.setObjectName('helper')

    right_l.addWidget(self.f22_empty)

    # =========================================================
    # CHECKOUT
    # =========================================================

    checkout = QFrame()
    checkout.setObjectName('f22CheckoutCard')

    foot = QVBoxLayout(checkout)
    foot.setContentsMargins(14, 12, 14, 12)
    foot.setSpacing(8)

    row1 = QHBoxLayout()
    row1.setSpacing(8)

    row1.addWidget(QLabel('Cliente'))

    self.pos_customer = QComboBox()
    self.pos_customer.addItem(
        'Consumidor final',
        None
    )

    for name, id in combo_data(
        self.erp,
        'customers'
    ):
        self.pos_customer.addItem(name, id)

    row1.addWidget(self.pos_customer, 2)
    row1.addWidget(QLabel('Medio de pago'))

    self.pos_payment = QComboBox()

    for k, label in [
        ('cash', 'Efectivo'),
        ('debit', 'Débito'),
        ('credit', 'Crédito'),
        ('transfer', 'Transferencia'),
        ('qr', 'QR'),
        ('check', 'Cheque')
    ]:
        self.pos_payment.addItem(label, k)

    row1.addWidget(self.pos_payment, 1)
    row1.addWidget(QLabel('Cupón'))

    self.f20_coupon_code = QLineEdit()
    self.f20_coupon_code.setPlaceholderText(
        'NXM-...'
    )
    row1.addWidget(self.f20_coupon_code, 1)

    foot.addLayout(row1)

    row2 = QHBoxLayout()
    row2.setSpacing(10)

    def _f22_amount_box(label, big=False):
        box = QVBoxLayout()

        lab = QLabel(label)
        lab.setObjectName('f22Tiny')
        box.addWidget(lab)

        num = QLabel('ARS 0,00')
        num.setObjectName(
            'f22GrandTotal'
            if big
            else 'f22Amount'
        )
        box.addWidget(num)

        row2.addLayout(
            box,
            2 if big else 1
        )

        return num

    self.f20_subtotal = _f22_amount_box(
        'SUBTOTAL'
    )

    self.f20_discount = _f22_amount_box(
        'DESCUENTO'
    )

    self.f20_total = _f22_amount_box(
        'TOTAL A COBRAR',
        True
    )

    btns = QVBoxLayout()
    btns.setSpacing(6)

    collect = QPushButton(
        '✓ COBRAR Y CERRAR VENTA'
    )
    collect.setObjectName(
        'f22CollectButton'
    )
    collect.setMinimumHeight(54)

    collect.clicked.connect(
        lambda _=False: self.safe(
            self.pos_checkout
        )
    )

    btns.addWidget(collect)
    row2.addLayout(btns)

    foot.addLayout(row2)

    self.f20_coupon_status = QLabel('')
    self.f20_coupon_status.setObjectName(
        'helper'
    )
    self.f20_coupon_status.setWordWrap(True)

    self.f20_reward = QLabel('')
    self.f20_reward.setObjectName('helper')
    self.f20_reward.setWordWrap(True)

    foot.addWidget(self.f20_coupon_status)
    foot.addWidget(self.f20_reward)

    right_l.addWidget(checkout)

    self.f22_splitter.addWidget(right)

    # =========================================================
    # SPLITTER RESPONSIVO
    # =========================================================

    self.f22_splitter.setStretchFactor(0, 2)
    self.f22_splitter.setStretchFactor(1, 3)

    self.f22_splitter.setStyleSheet("""
        QSplitter::handle:horizontal {
            background: #E96A00;
            width: 10px;
            margin: 2px 1px;
            border-radius: 4px;
        }

        QSplitter::handle:horizontal:hover {
            background: #FF8A1F;
        }
    """)

    self.f22_splitter.setSizes([
        430,
        700
    ])

    # =========================================================
    # BOTONES PARA AMPLIAR LOS PANELES
    # =========================================================

    split_controls = QHBoxLayout()
    split_controls.setContentsMargins(
        4,
        0,
        4,
        2
    )
    split_controls.setSpacing(6)

    split_controls.addStretch(1)

    btn_more_cart = QPushButton(
        '◀ Ampliar carrito'
    )

    btn_balance = QPushButton(
        '↔ Equilibrar'
    )

    btn_more_catalog = QPushButton(
        'Ampliar catálogo ▶'
    )

    btn_more_cart.setToolTip(
        'Mover la división hacia la izquierda '
        'y dar más espacio al carrito'
    )

    btn_balance.setToolTip(
        'Restablecer una distribución equilibrada'
    )

    btn_more_catalog.setToolTip(
        'Mover la división hacia la derecha '
        'y dar más espacio al catálogo'
    )

    def _f22_resize_panels(direction):
        sizes = self.f22_splitter.sizes()

        if len(sizes) < 2:
            return

        total = sum(sizes)

        if total <= 0:
            return

        min_left = 330
        min_right = 500
        step = 90

        if total < min_left + min_right:
            self.f22_splitter.setSizes([
                min_left,
                min_right
            ])
            return

        left_size = sizes[0]

        if direction < 0:
            # Más espacio para el carrito
            left_size -= step

        elif direction > 0:
            # Más espacio para el catálogo
            left_size += step

        else:
            # Distribución 40 / 60
            left_size = int(total * 0.40)

        left_size = max(
            min_left,
            left_size
        )

        left_size = min(
            left_size,
            total - min_right
        )

        right_size = total - left_size

        self.f22_splitter.setSizes([
            left_size,
            right_size
        ])

    btn_more_cart.clicked.connect(
        lambda _=False:
        _f22_resize_panels(-1)
    )

    btn_balance.clicked.connect(
        lambda _=False:
        _f22_resize_panels(0)
    )

    btn_more_catalog.clicked.connect(
        lambda _=False:
        _f22_resize_panels(1)
    )

    split_controls.addWidget(
        btn_more_cart
    )

    split_controls.addWidget(
        btn_balance
    )

    split_controls.addWidget(
        btn_more_catalog
    )

    split_controls.addStretch(1)

    self.outer.addLayout(split_controls)
    self.outer.addWidget(
        self.f22_splitter,
        1
    )

    # =========================================================
    # CONEXIONES FINALES
    # =========================================================

    self.table = table_widget(
        [],
        [
            'id',
            'created_at',
            'branch_id',
            'total_cents'
        ]
    )

    self.f20_coupon_code.textChanged.connect(
        lambda *_:
        _f20_offer_preview(self)
    )

    self.pos_customer.currentIndexChanged.connect(
        lambda *_:
        _f20_offer_preview(self)
    )

    self.pos_payment.currentIndexChanged.connect(
        lambda *_:
        _f20_offer_preview(self)
    )

    _f22_load_product_combo(self)
    _f22_refresh(self)

    self.pos_barcode.setFocus()


App.page_pos=_f22_page_pos
App.render_cart=_f22_render_cart
App.pos_refresh=_f22_refresh
App.pos_add=_f22_add
App.pos_remove=_f22_remove


class _DialogLocaleFilter(__import__('PySide6').QtCore.QObject):
 def eventFilter(self,obj,event):
  from PySide6.QtCore import QEvent,QSettings
  if event.type()==QEvent.Type.Show and isinstance(obj,QDialog):
   code=QSettings('NexoMerc','ERP').value('ui_locale','es_AR')
   if locale_supported(code):localize_tree(obj,code)
  return False

def start_app():
  import sys
  QLocale.setDefault(QLocale('es_AR'))
  if sys.platform=='win32':
   try:
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('NexoMerc.ERP.Retail.V2F05')
   except (OSError,AttributeError):pass
  app=QApplication(sys.argv);app.setWindowIcon(shop_icon());app.setStyle('Fusion');app.setStyleSheet(STYLE+ (Path(__file__).with_name('retail.qss')).read_text(encoding='utf-8').replace('__NX_CHECK_ON__',str(ASSETS/'icons'/'checkbox_on_f13.png').replace('\\','/')).replace('__NX_CHECK_OFF__',str(ASSETS/'icons'/'checkbox_off_f13.png').replace('\\','/')))
  translator=_DialogLocaleFilter(app);app.installEventFilter(translator)
  root=Path(__file__).resolve().parent.parent/'assets'
  erp=ERP()
  logging.basicConfig(filename=str(erp.root/'errors.log'),level=logging.ERROR,format='%(asctime)s %(levelname)s %(message)s')
  import faulthandler
  crash=open(erp.root/'native-crash.log','a',encoding='utf-8')
  faulthandler.enable(crash)
  def report_exception(kind,value,tb):
   logging.error('Excepción fuera de callback protegido',exc_info=(kind,value,tb))
  sys.excepthook=report_exception
  try:
   login=Login(erp,root)
   if login.exec()!=QDialog.DialogCode.Accepted:return 0
   window=App(erp,root);window.setWindowTitle('NexoMerc ERP · V2-F22');window.show()
   return app.exec()
  finally:
   erp.close();faulthandler.disable();crash.close()
