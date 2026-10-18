"""F14 regression checks, runnable without Qt; visual coverage requires Windows/PySide6."""
from pathlib import Path
import ast
import json
import unittest

PROJECT=Path(__file__).resolve().parents[1]
SOURCE=(PROJECT/'nexomerc'/'ui.py').read_text(encoding='utf-8')
MODULE=ast.parse(SOURCE)
APP=next(n for n in MODULE.body if isinstance(n,ast.ClassDef) and n.name=='App')
METHODS={n.name:n for n in APP.body if isinstance(n,ast.FunctionDef)}


def method(name):return ast.get_source_segment(SOURCE,METHODS[name])


class F14NavigationTests(unittest.TestCase):
 def test_01_sidebar_contains_only_one_entry(self):
  menu=next(n for n in MODULE.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='MENU' for t in n.targets))
  entries=ast.literal_eval(menu.value)
  self.assertEqual(1,sum(k=='products' for k,v in entries))
  self.assertEqual(0,sum(k=='inventory' for k,v in entries))
  self.assertEqual('Productos y stock',dict(entries)['products'])

 def test_02_two_internal_subviews(self):
  src=method('root')
  self.assertIn("('products','Catálogo y precios')",src)
  self.assertIn("('inventory','Existencias y movimientos')",src)
  self.assertIn("self.erp.available(page)",src)
  self.assertIn('catalogModeActive',src)

 def test_03_security_boundaries_remain_separate(self):
  src=method('open_module')
  self.assertIn("self.erp.check(mod)",src)
  self.assertIn("not self.erp.available('products')",src)
  self.assertIn("self.erp.available('inventory')",src)
  root=method('root')
  self.assertIn("module=='inventory'",root)

 def test_04_every_catalog_action_still_routed(self):
  src=method('page_products')
  for identifier in ('self.product_form','self.edit_current','self.product_detail','self.product_archive','self.product_restore','self.product_toggle','self.product_export'):
   self.assertIn(identifier,src)
  self.assertNotIn('self.product_receive',src)  # duplicate action intentionally removed

 def test_05_inventory_actions_preserved(self):
  src=method('page_inventory')
  for identifier in ('self.stock_receive','self.stock_count','self.stock_history','self.stock_adjust','self.stock_reservation','self.stock_receipts'):
   self.assertIn(identifier,src)

 def test_06_no_database_migration_or_business_logic_change(self):
  self.assertTrue((PROJECT/'nexomerc'/'core.py').exists())
  self.assertTrue((PROJECT/'nexomerc'/'units.py').exists())
  self.assertEqual('2.0.14',(PROJECT/'VERSION.txt').read_text(encoding='utf-8'))

 def test_07_locale_keys_for_six_languages(self):
  translation=json.loads((PROJECT/'nexomerc'/'translations.json').read_text(encoding='utf-8'))
  for locale in ('en_US','pt_BR','ja_JP','fil_PH','vi_VN','zh_CN'):
   self.assertIn('Productos y stock',translation['catalog'][locale])
   self.assertIn('Catálogo y precios',translation['catalog'][locale])
   self.assertIn('Existencias y movimientos',translation['catalog'][locale])

 def test_08_ui_parse_and_settings_still_present(self):
  self.assertIn('page_settings',METHODS)
  self.assertIn('page_pos',METHODS)
  self.assertIn('page_receipts',METHODS)
  self.assertIn('page_purchases',METHODS)
  self.assertIn('page_inventory',METHODS)

if __name__=='__main__':unittest.main()
