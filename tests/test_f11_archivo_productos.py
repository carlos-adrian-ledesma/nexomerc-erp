"""F11 regressions for reversible removal and preserved commercial history."""
import tempfile
import unittest
from nexomerc.core import ERP, ERPError, PermissionDenied

class ProductArchiveF11Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  self.erp=ERP(self.tmp.name)
  self.erp.initial_admin('adminf11','Administrador','ClaveSeguraF11!')
  self.erp.login('adminf11','ClaveSeguraF11!')
 def tearDown(self):
  self.erp.close();self.tmp.cleanup()
 def product(self,s):
  return self.erp.save_catalog('products',{'sku':s,'name':s,'unit':'u','active':1,'price_cents':2000})
 def test_archive_restore_hides_from_active_catalog(self):
  p=self.product('TEST-F11-A')
  self.erp.archive_product(p,'Duplicado creado por error')
  self.assertTrue(self.erp.is_product_archived(p))
  self.assertFalse(self.erp.entity('products',p)['active'])
  self.assertNotIn(p,[x['id'] for x in self.erp.catalogs('products')])
  self.assertIn(p,[x['id'] for x in self.erp.catalogs('products',include_archived=True)])
  self.erp.restore_product(p)
  self.assertFalse(self.erp.is_product_archived(p))
  self.assertFalse(self.erp.entity('products',p)['active'])
  self.erp.save_catalog('products',{'active':1},p)
  self.assertTrue(self.erp.entity('products',p)['active'])
 def test_double_archive_and_double_restore_rejected(self):
  p=self.product('TEST-F11-B');self.erp.archive_product(p)
  with self.assertRaises(ERPError):self.erp.archive_product(p)
  self.erp.restore_product(p)
  with self.assertRaises(ERPError):self.erp.restore_product(p)
 def test_stock_is_preserved_while_archived_and_reappears_after_restore(self):
  p=self.product('TEST-F11-C')
  self.erp.adjust_stock(p,1,6,'Inventario prueba')
  self.erp.archive_product(p)
  self.assertTrue(self.erp.is_product_archived(p))
  self.assertEqual(self.erp.one('SELECT onhand_milli FROM stock_balances WHERE product_id=?',(p,))['onhand_milli'],6000)
  self.assertNotIn(p,[r['product_id'] for r in self.erp.inventory()])
  self.erp.restore_product(p)
  self.erp.save_catalog('products',{'active':1},p)
  self.assertIn(p,[r['product_id'] for r in self.erp.inventory()])
 def test_archive_preserves_sale_and_audit_history(self):
  p=self.product('TEST-F11-D')
  self.erp.adjust_stock(p,1,1,'Prueba de entrada')
  self.erp.open_cash(1,0)
  result=self.erp.checkout(1,[{'product_id':p,'qty':1}],'cash')
  self.erp.archive_product(p)
  self.assertEqual(self.erp.scalar('SELECT COUNT(*) FROM sale_lines WHERE product_id=?',(p,)),1)
  self.assertEqual(self.erp.scalar('SELECT COUNT(*) FROM stock_movements WHERE product_id=?',(p,)),2)
  self.assertEqual(self.erp.scalar("SELECT COUNT(*) FROM audit_log WHERE action='product.archive' AND entity_id=?",(str(p),)),1)
  self.assertEqual(self.erp.con.execute('PRAGMA foreign_key_check').fetchall(),[])
 def test_pending_purchase_blocks_archive(self):
  p=self.product('TEST-F11-E')
  sid=self.erp.save_catalog('suppliers',{'name':'Proveedor F11','active':1})
  oid=self.erp.create_po(sid,1,[{'product_id':p,'qty':2,'cost':10}],notes='Prueba')
  with self.assertRaisesRegex(ERPError,'órdenes de compra'):
   self.erp.archive_product(p)
 def test_cashier_not_allowed_to_delete(self):
  p=self.product('TEST-F11-F')
  self.erp.save_user('cajero_f11','Cajero','cashier',1,password='ClaveCajeroF11!')
  self.erp.login('cajero_f11','ClaveCajeroF11!')
  self.assertFalse(self.erp.available('products','delete'))
  with self.assertRaises(PermissionDenied):self.erp.archive_product(p)
 def test_history_and_photo_retained_and_archive_prevents_edit(self):
  p=self.product('TEST-F11-G')
  self.erp.archive_product(p)
  with self.assertRaises(ERPError):self.erp.save_catalog('products',{'name':'Nuevo nombre'},p)
  self.assertIsNotNone(self.erp.entity('products',p))
 def test_managers_can_receive_delete_permission(self):
  p=self.product('TEST-F11-H')
  userid=self.erp.save_user('gerente_f11','Gerente','manager',1,password='ClaveGerenteF11!')
  self.erp.login('gerente_f11','ClaveGerenteF11!')
  with self.assertRaises(PermissionDenied):self.erp.archive_product(p)
  self.erp.login('adminf11','ClaveSeguraF11!')
  grid=self.erp.permission_grid(userid)
  for entry in grid:
   if entry['module']=='products' and entry['action']=='delete':entry['allowed']=True
  self.erp.save_permissions(userid,grid)
  self.erp.login('gerente_f11','ClaveGerenteF11!')
  self.erp.archive_product(p)
  self.assertTrue(self.erp.is_product_archived(p))

if __name__=='__main__': unittest.main()
