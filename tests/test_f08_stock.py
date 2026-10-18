"""F08 stock workflows; no UI dependencies needed for business assertions."""
import ast
import json
import tempfile
import unittest
from pathlib import Path
from nexomerc.core import ERP, ERPError
from nexomerc.locale_ui import translate

class StockF08Tests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory()
  self.db=ERP(self.temp.name)
  self.db.initial_admin('director','Administracion','contrasegna2026!')
  self.db.login('director','contrasegna2026!')
  self.product=self.db.save_catalog('products',{'sku':'LAVA-F08','barcode':'779555123','name':'Lavandina','cost_cents':20000,'price_cents':45000,'min_milli':10000,'max_milli':100000,'unit':'u','active':True})
 def tearDown(self):
  self.db.close();self.temp.cleanup()
 def stock(self):
  return next(r for r in self.db.inventory(1) if r['product_id']==self.product)
 def test_initial_six_and_sell_two(self):
  before=self.stock();self.assertEqual(before['onhand_milli'],0)
  self.db.adjust_stock(self.product,1,6,'CARGA INICIAL - seis unidades contadas')
  self.assertEqual(self.stock()['onhand_milli'],6000)
  session=self.db.open_cash(1,0)
  sid=self.db.checkout(1,[{'product_id':self.product,'qty':2}],'cash')
  self.assertEqual(self.stock()['onhand_milli'],4000)
  self.assertEqual(self.db.entity('sales',sid)['status'],'completed')
  self.assertEqual(self.db.scalar("SELECT COUNT(*) FROM stock_movements WHERE product_id=? AND reason='sale'",(self.product,)),1)
 def test_physical_count_is_absolute_not_plus(self):
  self.db.adjust_stock(self.product,1,6,'Carga inicial')
  diff=self.db.physical_count(self.product,1,5,'Conté cinco físicamente')
  self.assertEqual(diff,-1000)
  self.assertEqual(self.stock()['onhand_milli'],5000)
  nochange=self.db.physical_count(self.product,1,5,'Verificación de conteo')
  self.assertEqual(nochange,0)
  self.assertEqual(self.stock()['onhand_milli'],5000)
 def test_minimum_10_does_not_create_10(self):
  self.db.adjust_stock(self.product,1,6,'Carga inicial')
  info=self.stock()
  self.assertEqual(info['min_milli'],10000)
  self.assertEqual(info['onhand_milli'],6000)
 def test_reserved_quantity_cannot_be_consumed_by_count(self):
  self.db.adjust_stock(self.product,1,6,'Carga inicial')
  self.db.reserve(self.product,1,3)
  with self.assertRaises(ERPError):self.db.physical_count(self.product,1,2,'Conteo menor a reservas')
  self.assertEqual(self.stock()['onhand_milli'],6000)
 def test_branch_label_in_all_six_languages(self):
  for code in ('en_US','pt_BR','ja_JP','fil_PH','vi_VN','zh_CN'):
   self.assertNotEqual(translate('Sucursales y transferencias',code),'Sucursales y transferencias',code)
 def test_inventory_editor_is_defined_and_called(self):
  path=Path(__file__).resolve().parents[1]/'nexomerc'/'ui.py'
  source=path.read_text(encoding='utf-8');tree=ast.parse(source)
  self.assertTrue(any(isinstance(n,ast.ClassDef) and n.name=='InventoryStockDialog' for n in tree.body))
  self.assertNotIn('InventoryAdjustDialog(',source)
  # F09+ replaced the one-time opening-stock button with repeatable Goods Received.
  # Check the active UI action rather than an obsolete F08 button label.
  self.assertIn('self.stock_receive',source)
  self.assertIn('def page_inventory(self):',source)

if __name__=='__main__':unittest.main()
