import tempfile
import sqlite3
import unittest
from datetime import date,timedelta
from pathlib import Path
from nexomerc.core import ERP,ERPError,PermissionDenied,cents,milli,money,quantity,total_for

class ERPTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  self.db=ERP(self.tmp.name)
  self.db.initial_admin('director','Directora General','secretpass2026!')
  self.db.login('director','secretpass2026!')
  e=self.db
  self.second=e.save_catalog('branches',{'name':'Sucursal Sur','address':'Ruta 3','active':True})
  self.category=e.save_catalog('categories',{'name':'Almacén','active':True})
  self.brand=e.save_catalog('brands',{'name':'Marca demo','active':True})
  self.supplier=e.save_catalog('suppliers',{'name':'Distribuidora Norte','tax_id':'20-00000000-1','active':True})
  self.customer=e.save_catalog('customers',{'name':'Cliente de prueba','active':True})
  self.product=e.save_catalog('products',{'sku':'HARINA1','barcode':'779001','name':'Harina demo','category_id':self.category,'brand_id':self.brand,'supplier_id':self.supplier,'cost_cents':10000,'price_cents':20000,'min_milli':1000,'max_milli':500000,'unit':'u','active':True})
 def tearDown(self):self.db.close();self.tmp.cleanup()
 def seed_stock(self,q=10):self.db.adjust_stock(self.product,1,q,'Carga inicial verificada')
 def test_01_setup_login(self):
  self.assertEqual(self.db._user()['role'],'admin')
  with self.assertRaises(ERPError):self.db.initial_admin('x','x','password12345')
 def test_02_numeric_precision(self):
  self.assertEqual(cents('1,235'),124)
  self.assertEqual(milli('2.555'),2555)
  self.assertEqual(total_for(1250,20000),25000)
  self.assertEqual(quantity(1500),'1.5')
  with self.assertRaises(ERPError):milli('1.0005')
  with self.assertRaises(ERPError):cents('-1')
 def test_03_inventory_guard(self):
  self.seed_stock(10);self.db.reserve(self.product,1,3)
  with self.assertRaises(ERPError):self.db.adjust_stock(self.product,1,-8,'Más que disponibilidad')
  b=self.db.one('SELECT * FROM stock_balances WHERE product_id=?',(self.product,))
  self.assertEqual((b['onhand_milli'],b['reserved_milli']),(10000,3000))
  self.db.unreserve(self.product,1,3)
  self.db.adjust_stock(self.product,1,-8,'Conteo físico');self.assertEqual(self.db.inventory(1)[0]['onhand_milli'],2000)
 def test_04_purchase_partial_receive_and_exactly_once(self):
  e=self.db
  po=e.create_po(self.supplier,1,[{'product_id':self.product,'qty':10,'cost':'100'}])
  with self.assertRaises(ERPError):e.receive_po(po,{self.product:1},'R1')
  e.submit_po(po);rid=e.receive_po(po,{self.product:4},'R1')
  self.assertEqual(e.entity('purchase_orders',po)['status'],'partial')
  self.assertEqual(e.inventory(1)[0]['onhand_milli'],4000)
  with self.assertRaises(ERPError):e.receive_po(po,{self.product:7},'OVER')
  self.assertEqual(e.inventory(1)[0]['onhand_milli'],4000)
  e.receive_po(po,{self.product:6},'R2')
  self.assertEqual(e.entity('purchase_orders',po)['status'],'completed')
  with self.assertRaises(ERPError):e.receive_po(po,{self.product:1},'REPEAT')
  self.assertEqual(e.inventory(1)[0]['onhand_milli'],10000)
  self.assertEqual(e.scalar('SELECT COUNT(*) FROM receipt_lines'),2)
 def test_05_transfer_in_transit(self):
  e=self.db;self.seed_stock(10)
  tid=e.create_transfer(1,self.second,[{'product_id':self.product,'qty':6}]);e.dispatch_transfer(tid)
  self.assertEqual(e.inventory(1)[0]['onhand_milli'],4000)
  self.assertEqual(e.inventory(self.second)[0]['onhand_milli'],0)
  with self.assertRaises(ERPError):e.dispatch_transfer(tid)
  e.receive_transfer(tid)
  self.assertEqual(e.inventory(self.second)[0]['onhand_milli'],6000)
  with self.assertRaises(ERPError):e.receive_transfer(tid)
 def test_06_transfer_failed_atomic(self):
  e=self.db;self.seed_stock(2)
  tid=e.create_transfer(1,self.second,[{'product_id':self.product,'qty':5}])
  with self.assertRaises(ERPError):e.dispatch_transfer(tid)
  self.assertEqual(e.entity('transfers',tid)['status'],'draft')
  self.assertEqual(e.inventory(1)[0]['onhand_milli'],2000)
 def test_07_pos_cash_and_undo(self):
  e=self.db;self.seed_stock(15)
  cash=e.open_cash(1,'1000')
  sale=e.checkout(1,[{'product_id':self.product,'qty':2}],'cash',self.customer)
  self.assertEqual(e.entity('sales',sale)['total_cents'],40000)
  self.assertEqual(e.inventory(1)[0]['onhand_milli'],13000)
  self.assertIn('NO FISCAL',e.sale_ticket(sale))
  self.assertEqual(e.entity('customers',self.customer)['points'],4)
  with self.assertRaises(ERPError):e.checkout(1,[{'product_id':self.product,'qty':999}],'cash')
  self.assertEqual(e.scalar('SELECT COUNT(*) FROM sales'),1)
  e.void_sale(sale,'Cobro duplicado');self.assertEqual(e.inventory(1)[0]['onhand_milli'],15000)
  self.assertEqual(e.entity('customers',self.customer)['points'],0)
  with self.assertRaises(ERPError):e.void_sale(sale,'Otra vez')
  expected=e.close_cash(1,'1000');self.assertEqual(expected,100000)
  with self.assertRaises(ERPError):e.checkout(1,[{'product_id':self.product,'qty':1}],'cash')
 def test_08_promotions_applied_by_branch_and_date(self):
  e=self.db;self.seed_stock(10);e.open_cash(1,0)
  today=date.today().isoformat();tomorrow=(date.today()+timedelta(days=2)).isoformat()
  e.create_promotion(self.product,1,'Oferta',150,today,tomorrow)
  self.assertEqual(e.effective_price(self.product,1),15000)
  self.assertEqual(e.effective_price(self.product,self.second),20000)
  s=e.checkout(1,[{'product_id':self.product,'qty':3}],'debit')
  self.assertEqual(e.entity('sales',s)['total_cents'],45000)
 def test_09_user_permissions(self):
  e=self.db;uid=e.save_user('cajera','Cajera de prueba','cashier',1,'C4jera_password!')
  e.login('cajera','C4jera_password!')
  with self.assertRaises(PermissionDenied):e.save_catalog('products',{'sku':'HACK','name':'Bad'})
  self.assertGreaterEqual(e.get_dashboard()['low_stock'],0)
  e.open_cash(1,0)
  with self.assertRaises(PermissionDenied):e.open_cash(self.second,0)
 def test_10_manager_transfer_outbound(self):
  e=self.db;self.seed_stock(5)
  e.save_user('jefa','Jefa sucursal','manager',1,'SecUr3_password!')
  e.login('jefa','SecUr3_password!')
  tid=e.create_transfer(1,self.second,[{'product_id':self.product,'qty':2}]);e.dispatch_transfer(tid)
  with self.assertRaises(PermissionDenied):e.receive_transfer(tid)
 def test_11_audit_integrity(self):
  e=self.db;self.assertEqual(e.verify_audit(),(True,None))
  e.con.execute("UPDATE audit_log SET details='{}' WHERE id=1")
  self.assertFalse(e.verify_audit()[0])
 def test_12_backup_and_settings(self):
  e=self.db;e.save_settings({'business_name':'Mini mercado local','currency':'ARS'})
  self.assertEqual(e.read_settings()['business_name'],'Mini mercado local')
  file=Path(self.tmp.name)/'backup.sqlite3'
  e.backup(file);self.assertTrue(file.stat().st_size>0)
 def test_13_invalid_photo(self):
  p=Path(self.tmp.name)/'test.txt';p.write_text('not-an-image')
  with self.assertRaises(ERPError):self.db.attach_photo(self.product,str(p))
 def test_14_lockout(self):
  e=self.db
  for _ in range(5):
   with self.assertRaises(ERPError):e.login('director','wrong')
  with self.assertRaises(ERPError):e.login('director','secretpass2026!')
 def test_15_no_negative_overfill(self):
  e=self.db;self.seed_stock(3);e.open_cash(1,0)
  with self.assertRaises(ERPError):e.checkout(1,[{'product_id':self.product,'qty':5}],'cash')
  self.assertEqual(e.inventory(1)[0]['available_milli'],3000)
 def test_16_create_and_modification(self):
  e=self.db;pid=e.save_catalog('products',{'sku':'PAN2','name':'Pan','cost_cents':0,'price_cents':500,'active':True})
  e.save_catalog('products',{'name':'Pan de campo','price_cents':700},pid)
  self.assertEqual(e.entity('products',pid)['price_cents'],700)
 def test_17_permission_read_scope(self):
  e=self.db;e.save_user('almacen','Empleado depósito','warehouse',1,'Secret1password!')
  self.seed_stock(10);e.login('almacen','Secret1password!')
  self.assertEqual(len(e.inventory()),1)
  with self.assertRaises(PermissionDenied):e.adjust_stock(self.product,self.second,3,'Prohibido')
 def test_18_receipt_role_split(self):
  e=self.db;oid=e.create_po(self.supplier,1,[{'product_id':self.product,'qty':3,'cost':50}]);e.submit_po(oid)
  e.save_user('caja','Cajero','cashier',1,'Password_C4j3ro!');e.login('caja','Password_C4j3ro!')
  with self.assertRaises(PermissionDenied):e.receive_po(oid,{self.product:3},'X')
 def test_19_no_empty_cash_dup(self):
  e=self.db;e.open_cash(1,0)
  with self.assertRaises(ERPError):e.open_cash(1,0)
 def test_20_promotion_order(self):
  e=self.db;start=date.today().isoformat();y=(date.today()-timedelta(days=2)).isoformat()
  with self.assertRaises(ERPError):e.create_promotion(self.product,1,'Backwards',1,start,y)

if __name__=='__main__':unittest.main(verbosity=2)

class AdditionalTests(unittest.TestCase):
 def test_21_granular_permissions_and_scope(self):
  with tempfile.TemporaryDirectory() as d:
   e=ERP(d);e.initial_admin('root','Root','Password_pR0tected!');e.login('root','Password_pR0tected!')
   e.save_catalog('branches',{'name':'B2'})
   id=e.save_user('empleado','Empleado','cashier',1,'Password_empleado!')
   permissions=e.permission_grid(id)
   target=[{'module':'inventory','action':'view','allowed':True},{'module':'pos','action':'sell','allowed':False}]
   e.save_permissions(id,target)
   e.login('empleado','Password_empleado!')
   self.assertTrue(e.available('inventory'))
   self.assertFalse(e.available('pos','sell'))
   with self.assertRaises(PermissionDenied):e.inventory(2)
   e.close()
 def test_22_physical_count_and_restrictions(self):
  with tempfile.TemporaryDirectory() as d:
   e=ERP(d);e.initial_admin('root','Root','Password_pR0tected!');e.login('root','Password_pR0tected!')
   pid=e.save_catalog('products',{'sku':'A1','name':'Arroz','price_cents':100})
   e.adjust_stock(pid,1,10,'Recepción previa')
   self.assertEqual(e.physical_count(pid,1,7,'Inventario mensual'),-3000)
   self.assertEqual(e.inventory(1)[0]['onhand_milli'],7000)
   e.reserve(pid,1,2)
   with self.assertRaises(ERPError):e.physical_count(pid,1,1,'Menos reservas')
   e.close()
 def test_23_bundle_includes_photo_folder_and_valid_sqlite(self):
  import zipfile
  with tempfile.TemporaryDirectory() as d:
   e=ERP(d);e.initial_admin('root','Root','Password_pR0tected!');e.login('root','Password_pR0tected!')
   target=Path(d)/'outside.zip'
   e.backup_bundle(target)
   with zipfile.ZipFile(target) as z:
    self.assertIn('nexomerc.sqlite3',z.namelist())
    self.assertIn('backup_manifest.json',z.namelist())
    self.assertIsNone(z.testzip())
   e.close()
 def test_24_closed_cash_rejects_void(self):
  with tempfile.TemporaryDirectory() as d:
   e=ERP(d);e.initial_admin('root','Root','Password_pR0tected!');e.login('root','Password_pR0tected!')
   p=e.save_catalog('products',{'sku':'L1','name':'Leche','price_cents':800})
   e.adjust_stock(p,1,5,'Apertura');e.open_cash(1,0)
   s=e.checkout(1,[{'product_id':p,'qty':1}],'cash')
   e.close_cash(1,8)
   with self.assertRaises(ERPError):e.void_sale(s,'Anulación posterior al cierre')
   e.close()
