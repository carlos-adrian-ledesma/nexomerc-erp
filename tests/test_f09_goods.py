import tempfile, unittest
from nexomerc.core import ERP,ERPError,PermissionDenied

class GoodsF09(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.e=ERP(self.temp.name)
  self.e.initial_admin('admin','Administrador','ClaveCorrecta123!');self.e.login('admin','ClaveCorrecta123!')
  self.pid=self.e.save_product_with_stock({'sku':'LAV-1','name':'Lavandina','unit':'u','price_cents':210000,'active':True},pack_factor=6,box_factor=24)
 def tearDown(self):self.e.close();self.temp.cleanup()
 def balance(self):
  return self.e.one('SELECT onhand_milli FROM stock_balances WHERE product_id=? AND branch_id=1',(self.pid,))['onhand_milli']
 def test_01_packaging_and_delivery(self):
  a=self.e.receive_manual(self.pid,1,2,'pack',expiry='2027-12-01',reference='R-123')
  self.assertEqual(self.balance(),12000)
  self.e.receive_manual(self.pid,1,1,'box')
  self.assertEqual(self.balance(),36000)
  lines=self.e.manual_receipts(self.pid,1)
  self.assertEqual(len(lines),2)
  self.assertEqual(lines[1]['expiry_date'],'2027-12-01')
  self.assertEqual(lines[1]['reference'],'R-123')
  self.assertEqual(self.e.one('SELECT reason FROM stock_movements ORDER BY id LIMIT 1')['reason'],'manual_receipt')
 def test_02_pos_reduces_balance(self):
  self.e.receive_manual(self.pid,1,6,'base')
  self.e.open_cash(1,0)
  self.e.checkout(1,[{'product_id':self.pid,'qty':2}],'cash')
  self.assertEqual(self.balance(),4000)
 def test_03_duplicate_operation_idempotency(self):
  self.e.receive_manual(self.pid,1,1,'base',operation_key='MY-OP-UNIQUE')
  with self.assertRaises(ERPError):self.e.receive_manual(self.pid,1,1,'base',operation_key='MY-OP-UNIQUE')
  self.assertEqual(self.balance(),1000)
 def test_04_missing_factor_and_fractional_box(self):
  with self.assertRaises(ERPError):self.e.receive_manual(self.pid,1,0.5,'box')
  p=self.e.save_catalog('products',{'sku':'SIN-CAJA','name':'Sin caja','unit':'u'})
  with self.assertRaises(ERPError):self.e.receive_manual(p,1,1,'box')
  self.assertEqual(self.e.scalar('SELECT COUNT(*) FROM stock_movements WHERE product_id=?',(p,)),0)
 def test_05_product_stock_atomic_rollback(self):
  with self.assertRaises(ERPError):
   self.e.save_product_with_stock({'sku':'PRUEBA','name':'Prueba','unit':'u'},pack_factor=0,box_factor=0,
     entry={'qty':2,'input_type':'box','branch_id':1})
  self.assertEqual(self.e.scalar("SELECT COUNT(*) FROM products WHERE sku='PRUEBA'"),0)
 def test_06_kg_and_fraction_precision(self):
  p=self.e.save_product_with_stock({'sku':'Q-KG','name':'Queso','unit':'kg','price_cents':100000},pack_factor=2.5)
  self.e.receive_manual(p,1,1.250,'base')
  self.e.receive_manual(p,1,2,'pack')
  self.assertEqual(self.e.one('SELECT onhand_milli FROM stock_balances WHERE product_id=?',(p,))['onhand_milli'],6250)
 def test_07_stock_from_product_form(self):
  p=self.e.save_product_with_stock({'sku':'ACEITE','name':'Aceite','unit':'u'},box_factor=12,
      entry={'qty':3,'input_type':'box','branch_id':1,'note':'','reference':'rem-22'})
  self.assertEqual(self.e.one('SELECT onhand_milli FROM stock_balances WHERE product_id=?',(p,))['onhand_milli'],36000)
 def test_08_unit_change_rejected_after_movements(self):
  self.e.receive_manual(self.pid,1,1)
  with self.assertRaises(ERPError):self.e.save_product_with_stock({'unit':'kg'},id=self.pid)
  self.assertEqual(self.e.entity('products',self.pid)['unit'],'u')
 def test_09_expiry_validation_and_optional_reason(self):
  with self.assertRaises(ERPError):self.e.receive_manual(self.pid,1,1,expiry='2026-02-89')
  self.e.receive_manual(self.pid,1,1,note='')
  self.assertEqual(self.balance(),1000)
 def test_10_permissions(self):
  self.e.save_user('cashier1','Cajero','cashier',1,'CajeroSeguro2026!')
  self.e.login('cashier1','CajeroSeguro2026!')
  with self.assertRaises(PermissionDenied):self.e.receive_manual(self.pid,1,1)
  self.assertEqual(self.e.scalar('SELECT COUNT(*) FROM stock_movements'),0)
 def test_11_set_count_is_not_added(self):
  self.e.receive_manual(self.pid,1,6)
  self.e.physical_count(self.pid,1,5,'Conteo real')
  self.assertEqual(self.balance(),5000)
 def test_12_audit_integrity(self):
  self.e.receive_manual(self.pid,1,6)
  self.assertEqual(self.e.verify_audit(),(True,None))

if __name__=='__main__':unittest.main()
