"""Reusable retail dialogs; no hardware identification is inferred from typing."""
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QLabel,QLineEdit,QDialogButtonBox,QMessageBox,QPushButton,QComboBox,QTabWidget,QWidget,QFormLayout,QHBoxLayout,QGridLayout,QScrollArea,QApplication,QFrame)
from .core import ERPError
from .ui import Form,fld,combo_data,shop_icon

def valid_code(text):
 text=text.strip()
 if not 1<=len(text)<=128 or any(not c.isprintable() or c.isspace() for c in text):
  raise ERPError('Usá entre 1 y 128 caracteres sin espacios ni controles.')
 return text

class ScannerDialog(QDialog):
 def __init__(self,parent):
  super().__init__(parent);self.setWindowIcon(shop_icon());self.setWindowTitle('Escanear / Probar lector');self.resize(480,250)
  lay=QVBoxLayout(self);hint=QLabel('Conectá el lector USB en modo teclado, enfocá el campo y escaneá.\nEnter confirma; Tab cambia el foco. También podés escribir manualmente.\nEsto comprueba el texto recibido, no identifica el dispositivo.\nSerial / SDK: integración no implementada.')
  hint.setWordWrap(True);lay.addWidget(hint)
  self.code=QLineEdit();self.code.setPlaceholderText('Código leído');lay.addWidget(self.code)
  self.error=QLabel();lay.addWidget(self.error)
  buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
  buttons.accepted.connect(self.accept);buttons.rejected.connect(self.reject);lay.addWidget(buttons)
  self.code.returnPressed.connect(self.accept);self.code.setFocus()
 def accept(self):
  try:self.code.setText(valid_code(self.code.text()))
  except ERPError as exc:self.error.setText(str(exc));return
  super().accept()

class ProductForm(Form):
 def __init__(self,parent,title,fields,old=None):
  super().__init__(parent,title,fields);self.erp=parent.erp;self.old=old or {}
  self.setObjectName('productEditor');self.setWindowIcon(shop_icon())
  self.setMinimumWidth(700)
  available=QApplication.primaryScreen().availableGeometry()
  self.resize(min(880,available.width()-40),min(650,available.height()-70))
  # Preserve the base fields and validation; rearrange as a real photo + form editor.
  scroll=self.findChild(QScrollArea);source=scroll.widget().layout();blocks={}
  for key,*_ in fields:
   row=source.takeRow(0);label=row.labelItem.widget();block=row.fieldItem.widget()
   label.setParent(block);block.layout().insertWidget(0,label);blocks[key]=block
   # Keep concise labels in the main editor; detailed hints remain in tooltips.
   for hint in block.findChildren(QLabel):
    if hint.objectName()=='helper':
     self.widgets[key][0].setToolTip(hint.text());hint.hide()
  body=QWidget();body_layout=QHBoxLayout(body);body_layout.setContentsMargins(0,0,0,0);body_layout.setSpacing(18)
  photo=QFrame();photo.setObjectName('photoCard');photo.setFixedWidth(190);photo_layout=QVBoxLayout(photo);photo_layout.setContentsMargins(14,16,14,16)
  photo_layout.addWidget(blocks['photo_upload']);photo_layout.addStretch()
  self.photo_preview.setFixedSize(148,148);self.photo_preview.setWordWrap(True)
  self.photo_preview.setText('Sin fotografía')
  for button in blocks['photo_upload'].findChildren(QPushButton):button.setText('Cargar foto')
  for label in blocks['photo_upload'].findChildren(QLabel):
   if label.text()=='Fotografía 1080 × 1080':label.setText('Foto del producto')
  photo_note=QLabel('Foto del producto\nJPG o PNG · hasta 5 MB\n1080 × 1080 recomendado')
  photo_note.setWordWrap(True);photo_note.setObjectName('helper');photo_layout.addWidget(photo_note)
  body_layout.addWidget(photo)
  self.tabs=QTabWidget();body_layout.addWidget(self.tabs,1)
  groups=[('Información',['sku','barcode','name','category_id','brand_id','supplier_id']),('Precios y presentación',['cost','price','minimum','maximum','unit','pack_factor','box_factor']),('Existencias / ingreso',['stock_receive','stock_qty','stock_type','stock_branch','stock_expiry','stock_ref','stock_notes']),('Otros datos',['active'])]
  for title,keys in groups:
   pane=QWidget();grid=QGridLayout(pane);grid.setContentsMargins(8,14,12,14);grid.setSpacing(12)
   row=0
   for key in keys:
    if key=='brand_id':continue
    if key=='category_id':
     grid.addWidget(blocks[key],row,0);grid.addWidget(blocks['brand_id'],row,1)
    else:grid.addWidget(blocks[key],row,0,1,2)
    row+=1
   if title=='Precios y presentación':
    hint=QLabel('Precio y costo: por 1 unidad base (1 unidad, 1 kg o 1 litro).\nUn paquete/caja multiplica su contenido al ingresar y al vender, al precio de la unidad base.\nEl stock mínimo y máximo solo son alertas. La entrada está en Existencias / ingreso.')
    hint.setWordWrap(True);hint.setObjectName('helper');grid.addWidget(hint,row,0,1,2);row+=1
   if title=='Existencias / ingreso':
    note=QLabel('Activá la casilla cuadrada para ingresar existencias. Cantidad en kg/L/u si recibís a granel, o elegí paquete/caja si cargaste su contenido. El vencimiento y el motivo son opcionales.')
    note.setObjectName('helper');note.setWordWrap(True);grid.addWidget(note,row,0,1,2);row+=1
   grid.setRowStretch(row,1)
   area=QScrollArea();area.setWidgetResizable(True);area.setWidget(pane);self.tabs.addTab(area,title)
  index=self.layout().indexOf(scroll);self.layout().removeWidget(scroll);scroll.hide();scroll.deleteLater();self.layout().insertWidget(index,body,1)
  for key,table,label in [('category_id','categories','categoría'),('brand_id','brands','marca'),('supplier_id','suppliers','proveedor')]:
   combo=self.widgets[key][0];combo.clear();combo.addItem('— Ninguno —',None)
   for row in self.erp.catalogs(table):
    if row.get('active',1):combo.addItem(row['name'],row['id'])
   combo.setCurrentIndex(max(0,combo.findData(self.old.get(key))))
   combo.setEditable(True);combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
   button=QPushButton('+ Crear '+label);button.setObjectName('textAction');combo.parentWidget().layout().addWidget(button)
   button.clicked.connect(lambda checked=False,k=key,t=table,l=label:self.quick(k,t,l))
  barcode=self.widgets['barcode'][0];button=QPushButton('Escanear / Probar lector');button.setObjectName('textAction');barcode.parentWidget().layout().addWidget(button);button.clicked.connect(self.scan)
  # Stock entry is explicitly coupled to the entered quantity (no silent omission).
  self.stock_qty=self.widgets['stock_qty'][0]
  self.stock_receive=self.widgets['stock_receive'][0]
  self.stock_receive.setText('Sí, agregar la cantidad recibida al inventario al guardar')
  self.stock_receive.setToolTip('La cantidad se SUMARÁ una sola vez al confirmar. Dejá cero si solo editás el producto.')
  self.stock_receive.setObjectName('stockReceiveF13')
  self.stock_note=QLabel('Sin entrada de stock: el producto se guarda sin cambiar existencias.')
  self.stock_note.setObjectName('helper');self.stock_note.setWordWrap(True)
  arrival_tab=self.tabs.widget(2).widget().layout()
  arrival_tab.addWidget(self.stock_note,arrival_tab.rowCount(),0,1,2)
  self.stock_qty.valueChanged.connect(self._stock_quantity_changed)
  self.widgets['unit'][0].currentIndexChanged.connect(self.update_stock_preview)
  self.widgets['unit'][0].currentIndexChanged.connect(self.update_unit_labels)
  self.widgets['stock_type'][0].currentIndexChanged.connect(self.update_unit_labels)
  self.update_unit_labels()
  self.stock_receive.toggled.connect(self.update_stock_preview)
  for field in ('stock_type','stock_branch'):
   self.widgets[field][0].currentIndexChanged.connect(self.update_stock_preview)
  for field in ('pack_factor','box_factor'):
   self.widgets[field][0].valueChanged.connect(self.update_stock_preview)
  self.update_stock_preview()
  note=QLabel('Las altas rápidas permanecen guardadas aunque canceles este producto.')
  note.setWordWrap(True);note.setObjectName('helper');self.layout().insertWidget(self.layout().count()-1,note)
  buttons=self.findChild(QDialogButtonBox)
  buttons.button(QDialogButtonBox.StandardButton.Ok).setText('Guardar producto')
  if self.old.get('photo'):
   pix=QPixmap(str(self.erp.root/'photos'/self.old['photo']))
   self.photo_preview.setPixmap(pix.scaled(140,140,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
 def update_unit_labels(self,*args):
  unit=self.widgets['unit'][0].currentData() or 'u'
  kind=self.widgets['stock_type'][0].currentData()
  label={'u':'unidades','kg':'kg','l':'litros','paquete':'paquetes (tipo heredado)','caja':'cajas (tipo heredado)'}.get(unit,unit)
  typ={'base':label,'pack':'paquetes','box':'cajas'}.get(kind,label)
  self.stock_qty.setToolTip('Cantidad en '+typ+'. Ejemplo: 3 kg agregan 3 kg, pero 3 paquetes de 5 kg agregan 15 kg.')
  field=self.widgets['stock_qty'][0]
  for lab in field.parentWidget().findChildren(QLabel):
   if lab.text().startswith('Cantidad que llegó'):
    lab.setText('Cantidad que llegó ('+typ+')')
  choice=self.widgets['stock_type'][0]
  choice.setItemText(0,{'u':'Unidades sueltas (u)','kg':'Kilogramos sueltos (kg)','l':'Litros sueltos (L)'}.get(unit,'Unidad base: '+unit))
  self.update_stock_preview()
 def _stock_quantity_changed(self,value):
  # Typing 24 must never be ignored because a small checkbox was left unchecked.
  self.stock_receive.setChecked(value > 0)
  self.update_stock_preview()
 def update_stock_preview(self,*args):
  from decimal import Decimal
  qty=Decimal(str(self.stock_qty.value()))
  enabled=self.stock_receive.isChecked()
  unit=self.widgets['unit'][0].currentData() or 'u'
  kind=self.widgets['stock_type'][0].currentData()
  factor=Decimal('1')
  if kind=='pack':factor=Decimal(str(self.widgets['pack_factor'][0].value()))
  elif kind=='box':factor=Decimal(str(self.widgets['box_factor'][0].value()))
  new=qty*factor
  if not qty:
   message='Sin entrada de stock. Guardar solo actualizará los datos del producto.'
  elif not enabled:
   message='⚠ Hay cantidad ingresada, pero el ingreso está desactivado. No podrás guardar así.'
  elif factor<=0:
   message='⚠ Configurá primero cuántas unidades tiene cada caja o paquete.'
  else:
   branch=self.widgets['stock_branch'][0].currentData()
   old=0
   if self.old.get('id') and branch:
    r=self.erp.one('SELECT onhand_milli FROM stock_balances WHERE product_id=? AND branch_id=?',(self.old['id'],branch))
    old=Decimal(r['onhand_milli'])/1000 if r else Decimal('0')
   result=old+new
   message=(f'Ingreso pendiente: {qty:g} {"cajas" if kind=="box" else "paquetes" if kind=="pack" else unit} × {factor:g} = +{new:g} {unit}. ' if kind!='base' else f'Ingreso pendiente: +{qty:g} {unit}. ')+f'Existencias: {old:g} → {result:g} {unit}. Para 250 g ingresá 0,250 kg.'
  self.stock_note.setText(message)
 def showEvent(self,event):
  super().showEvent(event)
  parent=self.parentWidget()
  if parent:
   origin=parent.mapToGlobal(QPoint(0,0));screen=self.screen().availableGeometry()
   x=max(screen.left(),min(origin.x()+parent.width()-self.width()-16,screen.right()-self.width()))
   y=max(screen.top(),min(origin.y()+70,screen.bottom()-self.height()-30))
   self.move(x,y)
 def quick(self,key,table,label):
  combo=self.widgets[key][0];name=combo.currentText()
  fields=[fld('name','Nombre *',value='' if name.startswith('—') else name)]
  if table=='categories':fields.append(fld('parent_id','Categoría superior','choice',None,combo_data(self.erp,'categories',none=True)))
  dialog=Form(self,'Crear '+label,fields)
  if dialog.exec()!=QDialog.DialogCode.Accepted:return
  try:
   data=dialog.data();pid=self.erp.quick_catalog(table,data['name'],data.get('parent_id'))
   row=self.erp.entity(table,pid)
   if not row['active']:raise ERPError('El registro existe pero está inactivo. Reactivalo desde su módulo.')
   idx=combo.findData(pid)
   if idx<0:combo.addItem(row['name'],pid);idx=combo.count()-1
   combo.setCurrentIndex(idx)
  except (ERPError,ValueError) as exc:QMessageBox.warning(self,'Alta rápida',str(exc))
 def scan(self):
  dialog=ScannerDialog(self)
  if dialog.exec()==QDialog.DialogCode.Accepted:
   self.widgets['barcode'][0].setText(dialog.code.text())
 def accept(self):
  try:
   from .stock_intent import determine_entry
   wants=determine_entry(self.stock_receive.isChecked(),self.stock_qty.value(),
      self.widgets['stock_type'][0].currentData(),
      self.widgets['pack_factor'][0].value(),self.widgets['box_factor'][0].value(),
      self.widgets['unit'][0].currentData(),self.widgets['stock_branch'][0].currentData())
   if wants:
    response=QMessageBox.question(self,'Confirmar entrada de mercadería',
       self.stock_note.text()+'\n\n¿Guardar producto y SUMAR esta cantidad al inventario?\nNo vuelvas a registrar la misma entrega.',
       QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)
    if response!=QMessageBox.StandardButton.Yes:return
   for key in ('category_id','brand_id','supplier_id'):
    combo=self.widgets[key][0]
    name=' '.join(combo.currentText().split()).casefold()
    idx=next((i for i in range(combo.count()) if ' '.join(combo.itemText(i).split()).casefold()==name),-1)
    if idx<0:raise ERPError('Seleccioná una opción existente o usá + Crear antes de guardar.')
    combo.setCurrentIndex(idx)
   sku=self.widgets['sku'][0].text().strip()
   dup=self.erp.one('SELECT id FROM products WHERE sku=?',(sku,))
   if dup and dup['id']!=self.old.get('id'):raise ERPError('El SKU ya pertenece a otro producto.')
   code=self.widgets['barcode'][0].text().strip()
   if code:
    valid_code(code)
    dup=self.erp.one('SELECT id FROM products WHERE barcode=?',(code,))
    if dup and dup['id']!=self.old.get('id'):raise ERPError('El código de barras ya pertenece a otro producto.')
   for key in ('sku','name'):
    if not self.widgets[key][0].text().strip():raise ERPError('SKU y descripción son obligatorios.')
  except ERPError as exc:QMessageBox.warning(self,'Revisá los datos',str(exc));return
  super().accept()
