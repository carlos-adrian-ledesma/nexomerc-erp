import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest,tempfile
from pathlib import Path
from PySide6.QtWidgets import QApplication,QDialog
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt
from nexomerc.core import ERP
from nexomerc.ui import QuantitySpinBox,App
from nexomerc.retail import ProductForm
class F03Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
 def test_numeric_format_no_multiplication(self):
  spin=QuantitySpinBox();spin.setRange(0,999999)
  for value,text in [(10,'10'),(20,'20'),(1.5,'1,5'),(0.125,'0,125'),(10000,'10000')]:
   spin.setValue(value);self.assertEqual(spin.text(),text);self.assertEqual(spin.value(),value)
  spin.show();spin.setFocus();spin.selectAll();QTest.keyClicks(spin,'1,25');QTest.keyClick(spin,Qt.Key.Key_Tab)
  self.assertEqual(spin.value(),1.25);spin.close()
 def test_reopen_limits_icon_filters(self):
  with tempfile.TemporaryDirectory() as td:
   e=ERP(td)
   try:
    e.initial_admin('admin','Demo','TestPassword123!');e.login('admin','TestPassword123!')
    cat=e.quick_catalog('categories','Lácteos');brand=e.quick_catalog('brands','Marca prueba')
    pid=e.save_catalog('products',{'sku':'YOG','name':'Yogur','category_id':cat,'brand_id':brand,'min_milli':10000,'max_milli':20000})
    e.save_catalog('products',{'sku':'ARR','name':'Arroz','active':0})
    window=App(e,Path('assets'));window.open_module('products')
    old=e.entity('products',pid);f=ProductForm(window,'Editar producto',window.product_fields(old),old)
    self.assertFalse(window.windowIcon().isNull());self.assertFalse(f.windowIcon().isNull())
    self.assertEqual(f.widgets['minimum'][0].text(),'10');self.assertEqual(f.widgets['maximum'][0].text(),'20')
    d=f.data();self.assertEqual(round(d['minimum']*1000),10000);self.assertEqual(round(d['maximum']*1000),20000)
    f.reject()
    combo=window.product_filters['category_id'];combo.setCurrentIndex(combo.findData(cat));window.filter_products()
    self.assertEqual(sum(not window.table.isRowHidden(r) for r in range(window.table.rowCount())),1)
    window.clear_product_filters();window.search.setText('ARR');window.filter_products()
    self.assertEqual(sum(not window.table.isRowHidden(r) for r in range(window.table.rowCount())),1)
    window.close();window.deleteLater();self.app.processEvents()
   finally:e.close()
