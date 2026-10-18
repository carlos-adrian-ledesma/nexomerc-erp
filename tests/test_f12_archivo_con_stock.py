"""F12: archived products with physical stock and historical links."""
import tempfile,unittest
from nexomerc.core import ERP,ERPError,PermissionDenied

class F12Tests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.erp=ERP(self.temp.name)
  self.erp.initial_admin('f12admin','Administrador F12','ClaveF12!!')
  self.erp.login('f12admin','ClaveF12!!')
 def tearDown(self):self.erp.close();self.temp.cleanup()
 def product(self,sku='F12-LECHE'):
  return self.erp.save_catalog('products',{'sku':sku,'name':'Leche','active':1,'unit':'u','price_cents':15000,'min_milli':1000})
 def balance(self,p):
  return self.erp.scalar('SELECT COALESCE(SUM(onhand_milli),0) FROM stock_balances WHERE product_id=?',(p,))
 def test_archive_with_stock_hides_and_restore_keeps_stock(self):
  p=self.product();self.erp.adjust_stock(p,1,12,'Carga de prueba')
  impact=self.erp.archive_impact(p);self.assertEqual(impact['onhand_milli'],12000)
  self.erp.archive_product(p,'Ya no comercializado')
  self.assertTrue(self.erp.is_product_archived(p));self.assertEqual(self.balance(p),12000)
  self.assertNotIn(p,[r['product_id'] for r in self.erp.inventory()])
  self.erp.restore_product(p)
  self.erp.save_catalog('products',{'active':1},p)
  self.assertEqual(self.balance(p),12000)
  self.assertIn(p,[r['product_id'] for r in self.erp.inventory()])
 def test_archive_keeps_sale_and_remittance_history(self):
  p=self.product();self.erp.adjust_stock(p,1,10,'Carga de prueba');self.erp.open_cash(1,0)
  sale=self.erp.checkout(1,[{'product_id':p,'qty':2}],'cash')
  old_balance=self.balance(p);self.assertEqual(old_balance,8000)
  self.erp.archive_product(p)
  self.assertEqual(self.erp.scalar('SELECT COUNT(*) FROM sale_lines WHERE product_id=?',(p,)),1)
  self.assertEqual(self.balance(p),old_balance)
  self.assertIn('Leche',self.erp.sale_ticket(sale))
  self.assertEqual(self.erp.con.execute('PRAGMA foreign_key_check').fetchall(),[])
 def test_archived_product_cannot_be_sold(self):
  p=self.product();self.erp.adjust_stock(p,1,6,'Entrada')
  self.erp.open_cash(1,0);self.erp.archive_product(p)
  with self.assertRaisesRegex(ERPError,'inactivo|archivado'):
   self.erp.checkout(1,[{'product_id':p,'qty':1}],'cash')
 def test_reserved_stock_blocks_archive(self):
  p=self.product();self.erp.adjust_stock(p,1,6,'Entrada');self.erp.reserve(p,1,2)
  with self.assertRaisesRegex(ERPError,'reservadas'):
   self.erp.archive_product(p)
  self.assertFalse(self.erp.is_product_archived(p));self.assertEqual(self.balance(p),6000)
 def test_pending_purchase_blocks_archive(self):
  p=self.product();supplier=self.erp.save_catalog('suppliers',{'name':'Mayorista F12','active':1})
  self.erp.create_po(supplier,1,[{'product_id':p,'qty':2,'cost':10}])
  with self.assertRaisesRegex(ERPError,'órdenes de compra'):
   self.erp.archive_product(p)
 def test_pending_transfer_blocks_archive(self):
  p=self.product();branch=self.erp.save_catalog('branches',{'name':'Nueva sucursal F12','active':1})
  self.erp.create_transfer(1,branch,[{'product_id':p,'qty':2}])
  with self.assertRaisesRegex(ERPError,'traslados pendientes'):
   self.erp.archive_product(p)
 def test_archive_transaction_rolls_back_on_failure(self):
  p=self.product();self.erp.adjust_stock(p,1,4,'Entrada')
  self.erp.con.execute('''CREATE TRIGGER f12_no_archive BEFORE INSERT ON product_archives BEGIN SELECT RAISE(ABORT,'prohibido'); END''')
  with self.assertRaises(Exception):self.erp.archive_product(p)
  self.assertFalse(self.erp.is_product_archived(p));self.assertEqual(self.balance(p),4000)
  self.assertTrue(self.erp.entity('products',p)['active'])
 def test_archive_deactivates_promotions_and_preserves_record(self):
  p=self.product();promo=self.erp.create_promotion(p,1,'Promo',100,'2026-01-01','2026-12-31')
  self.erp.archive_product(p)
  self.assertEqual(self.erp.entity('promotions',promo)['active'],0)
  self.assertEqual(self.erp.scalar('SELECT COUNT(*) FROM promotions WHERE product_id=?',(p,)),1)
 def test_archive_impact_is_read_only(self):
  p=self.product();self.erp.adjust_stock(p,1,5,'Entrada')
  before=self.erp.scalar('SELECT COUNT(*) FROM audit_log')
  report=self.erp.archive_impact(p)
  self.assertEqual(report['onhand_milli'],5000)
  self.assertEqual(before,self.erp.scalar('SELECT COUNT(*) FROM audit_log'))
 def test_idempotency_and_permissions(self):
  p=self.product();self.erp.archive_product(p)
  with self.assertRaisesRegex(ERPError,'ya está eliminado'):
   self.erp.archive_product(p)
  self.erp.save_user('f12cashier','Cajero','cashier',1,password='ClaveF12Cajero!!')
  self.erp.login('f12cashier','ClaveF12Cajero!!')
  with self.assertRaises(PermissionDenied):self.erp.archive_impact(p)
if __name__=='__main__':unittest.main()
