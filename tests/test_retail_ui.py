import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import tempfile,unittest,time
from shiboken6 import isValid
from pathlib import Path
from unittest.mock import patch
from PySide6.QtCore import Qt,QTimer
from PySide6.QtWidgets import QApplication,QDialog,QMessageBox
from PySide6.QtTest import QTest
from nexomerc.core import ERP,ERPError,PermissionDenied
from nexomerc.ui import App,MENU,STYLE
from nexomerc.retail import ProductForm,ScannerDialog

class RetailTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.app=QApplication.instance() or QApplication([])
  cls.app.setStyleSheet(STYLE+Path('nexomerc/retail.qss').read_text())
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.erp=ERP(self.tmp.name)
  self.erp.initial_admin('admin','Prueba','TestPassword123!');self.erp.login('admin','TestPassword123!')
  self.pids=[self.erp.save_catalog('products',{'sku':f'P{i}','barcode':f'ABC{i}','name':name,'price_cents':10000}) for i,name in enumerate(['Yogur','Arroz'])]
  self.window=App(self.erp,Path('assets'));self.window.show();self.window.message=lambda *a:None
 def tearDown(self):
  self.window.close();self.window.deleteLater();self.app.processEvents();self.erp.close();self.tmp.cleanup()
 def _wait_for_ui(self,predicate,description,timeout_s=6):
  """Drain queued reloads before retaining references to Qt-owned widgets."""
  deadline=time.monotonic()+timeout_s
  while time.monotonic()<deadline:
   self.app.processEvents()
   try:
    if predicate():return
   except RuntimeError:
    # A former table can be destroyed while a queued GUI reload settles.
    pass
   QTest.qWait(15)
  self.fail('Tiempo agotado esperando: '+description)
 def _products_table_ready(self):
  table=getattr(self.window,'table',None)
  return (self.window.module=='products' and table is not None
          and isValid(table) and table.rowCount()>0
          and not getattr(self.window,'_edit_pending',False)
          and not getattr(self.window,'_product_open',False)
          and not getattr(self.window,'_reload_pending',False))
 def test_twenty_edit_cycles(self):
  self.window.open_module('products');self.window.activateWindow()
  # Keep the 60 actual edit/cancel interactions, but synchronize Qt's async
  # module rebuilds before referencing the next QTableWidget instance.
  for i in range(60):
   self._wait_for_ui(self._products_table_ready,f'tabla de productos antes del ciclo {i+1}')
   pid=self.pids[i%2]
   table=self.window.table
   row=next(r for r in range(table.rowCount()) if table.item(r,0).data(Qt.ItemDataRole.UserRole)==pid)
   table.selectRow(row);table.scrollToItem(table.item(row,3))
   before=self.erp.entity('products',pid)['name']
   expected=before if i%2==0 else 'Edición '+str(i)
   completed=[]
   def complete():
    form=self.app.activeModalWidget()
    if not isinstance(form,ProductForm):
     completed.append('No se abrió ProductForm')
     if isinstance(form,QDialog):form.reject()
     return
    completed.append('Producto')
    form.widgets['name'][0].setText('Edición '+str(i))
    if i%2==0:form.reject()
    else:form.accept()
   QTimer.singleShot(40,complete)
   if i%3==0:
    pos=table.visualRect(table.model().index(row,3)).center()
    QTest.mouseClick(table.viewport(),Qt.MouseButton.LeftButton,pos=pos)
    QTest.mouseDClick(table.viewport(),Qt.MouseButton.LeftButton,pos=pos)
   elif i%3==1:
    table.setFocus();QTest.keyClick(table,Qt.Key.Key_Return)
   else:self.window.safe(self.window.edit_current)
   self._wait_for_ui(
    lambda:bool(completed) and self._products_table_ready()
           and self.erp.entity('products',pid)['name']==expected,
    f'fin del ciclo {i+1} y recreación del catálogo')
   self.assertEqual(completed,['Producto'],f'Formulario inesperado en ciclo {i+1}')
   self.assertEqual(self.erp.entity('products',pid)['name'],expected)
 def test_catalog_links_cancel_and_duplicate(self):
  ids={key:self.erp.quick_catalog(table,'  Demo  catálogo ') for key,table in [('category_id','categories'),('brand_id','brands'),('supplier_id','suppliers')]}
  self.assertEqual(ids['category_id'],self.erp.quick_catalog('categories','demo catálogo'))
  self.erp.save_catalog('products',ids,self.pids[0])
  old=self.erp.entity('products',self.pids[0]);form=ProductForm(self.window,'Editar',self.window.product_fields(old),old)
  for key,pid in ids.items():self.assertEqual(form.widgets[key][0].currentData(),pid)
  form.reject();self.assertEqual(self.erp.scalar('SELECT COUNT(*) FROM categories'),1)
  with self.assertRaises(ERPError):self.erp.quick_catalog('brands',' ')
  self.erp.save_user('cashier','Cajero','cashier',1,'TestPassword123!');self.erp.login('cashier','TestPassword123!')
  with self.assertRaises(PermissionDenied):self.erp.quick_catalog('brands','Prohibido')
 def test_scanner_and_pos(self):
  dialog=ScannerDialog(self.window);dialog.show();QTest.keyClicks(dialog.code,'ABC0');QTest.keyClick(dialog.code,Qt.Key.Key_Return)
  self.assertEqual(dialog.result(),QDialog.DialogCode.Accepted)
  dialog=ScannerDialog(self.window);dialog.show();QTest.keyClicks(dialog.code,'ABC1');QTest.keyClick(dialog.code,Qt.Key.Key_Tab);dialog.accept();self.assertEqual(dialog.code.text(),'ABC1')
  self.erp.adjust_stock(self.pids[0],1,4,'Prueba');self.erp.reserve(self.pids[0],1,1)
  self.window.open_module('pos')
  for _ in range(2):
   QTest.keyClicks(self.window.pos_barcode,'ABC0');QTest.keyClick(self.window.pos_barcode,Qt.Key.Key_Return)
  self.assertEqual(self.window.cart[self.pids[0]],2000)
  self.window.pos_barcode.setText('NOEXISTE');self.window.pos_scan();self.assertEqual(len(self.window.cart),1)
  self.window.pos_qty.setValue(2)
  with self.assertRaises(ERPError):self.window.pos_add()
  with self.assertRaises(ERPError):self.erp.checkout(1,[{'product_id':self.pids[0],'qty':1}],'cash')
 def test_all_screens_render(self):
  for mod,_ in MENU:
   self.window.open_module(mod);self.app.processEvents();self.assertIsNotNone(self.window.content.widget())
