"""F10 regression: actual stock linking, packaging, photos, branch isolation and payments."""
import base64
import tempfile
import unittest
from pathlib import Path
from nexomerc.core import ERP, ERPError, PermissionDenied
from nexomerc.stock_intent import determine_entry


class F10ProductInventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.erp = ERP(self.temp.name)
        self.erp.initial_admin('tester', 'Admin QA', 'ClaveSegura2026!')
        self.erp.login('tester', 'ClaveSegura2026!')

    def tearDown(self):
        self.erp.close()
        self.temp.cleanup()

    def product(self, sku, unit='u', pack=0, box=0, qty=0, input_type='base', branch_id=1):
        stock_entry = None
        wants = determine_entry(qty > 0, qty, input_type, pack, box, unit, branch_id)
        if wants:
            stock_entry = {'branch_id': branch_id, 'qty': qty, 'input_type': input_type,
                           'reference': 'LAB-F10', 'note': 'Práctica de ingreso'}
        pid = self.erp.save_product_with_stock(
            {'sku':sku, 'name':sku, 'unit':unit, 'price_cents':2000, 'active':True},
            pack_factor=pack, box_factor=box, entry=stock_entry)
        return pid

    def balance(self, pid, bid=1):
        return self.erp.one('SELECT onhand_milli FROM stock_balances WHERE product_id=? AND branch_id=?',
                            (pid,bid))['onhand_milli']

    def test_01_nonzero_input_requires_recording(self):
        with self.assertRaisesRegex(ERPError, 'desactivada'):
            determine_entry(False,24,'base',0,0,'u',1)
        self.assertFalse(determine_entry(False,0,'base',0,0,'u',1))

    def test_02_active_zero_rejected(self):
        with self.assertRaises(ERPError): determine_entry(True,0,'base',0,0,'u',1)

    def test_03_missing_package_factor_rejected(self):
        with self.assertRaises(ERPError): determine_entry(True,2,'box',0,0,'u',1)
        with self.assertRaises(ERPError): determine_entry(True,2,'pack',0,0,'u',1)

    def test_04_fractional_base_weight_allowed(self):
        self.assertTrue(determine_entry(True,2.5,'base',0,0,'kg',1))
        self.assertTrue(determine_entry(True,1.25,'base',0,0,'l',1))
        with self.assertRaises(ERPError): determine_entry(True,2.5,'base',0,0,'u',1)
        with self.assertRaises(ERPError): determine_entry(True,1.5,'box',0,12,'u',1)

    def test_05_ten_practice_products_connected(self):
        examples=[
            ('LECHE_F10','u',0,12,2,'box',24000),
            ('HUEVOS_F10','u',24,0,2,'pack',48000),
            ('LAVANDINA_F10','u',0,0,6,'base',6000),
            ('YOGUR_F10','u',0,0,10,'base',10000),
            ('ARROZ_F10','kg',5,0,2,'pack',10000),
            ('ACEITE_F10','u',0,12,1,'box',12000),
            ('AGUA_F10','u',6,0,3,'pack',18000),
            ('DETERGENTE_F10','l',5,0,2,'pack',10000),
            ('QUESO_F10','kg',0,0,2.5,'base',2500),
            ('MANZANAS_F10','kg',0,0,4.75,'base',4750),
        ]
        for sku,unit,pack,box,qty,kind,expected in examples:
            with self.subTest(sku=sku):
                pid=self.product(sku,unit,pack,box,qty,kind)
                self.assertEqual(self.balance(pid),expected)
                record=next(item for item in self.erp.inventory() if item['product_id']==pid)
                self.assertEqual(record['onhand_milli'],expected)
                self.assertEqual(record['available_milli'],expected)

    def test_06_sale_deducts_milk(self):
        pid=self.product('LECHE_CAJA','u',box=12,qty=2,input_type='box')
        self.erp.open_cash(1,0)
        self.erp.checkout(1,[{'product_id':pid,'qty':3}],'cash')
        self.assertEqual(self.balance(pid),21000)

    def test_07_reservation_and_release(self):
        pid=self.product('LAVANDINA','u',qty=6)
        self.erp.reserve(pid,1,2)
        row=next(item for item in self.erp.inventory() if item['product_id']==pid)
        self.assertEqual((row['onhand_milli'],row['reserved_milli'],row['available_milli']),
                          (6000,2000,4000))
        self.erp.unreserve(pid,1,1)
        row=next(item for item in self.erp.inventory() if item['product_id']==pid)
        self.assertEqual(row['available_milli'],5000)

    def test_08_physical_count_sets_total_not_adds(self):
        pid=self.product('HUEVOS','u',pack=24,qty=2,input_type='pack')
        difference=self.erp.physical_count(pid,1,46,'Conteo verificado')
        self.assertEqual(difference,-2000)
        self.assertEqual(self.balance(pid),46000)

    def test_09_adjustments_and_stock_alert_threshold_independent(self):
        pid=self.product('ARROZ','kg',pack=5,qty=2,input_type='pack')
        self.erp.save_catalog('products',{'min_milli':15000},pid)
        self.assertEqual(self.balance(pid),10000)
        self.erp.adjust_stock(pid,1,3,'Ingreso de regularización')
        self.assertEqual(self.balance(pid),13000)
        self.assertEqual(self.erp.entity('products',pid)['min_milli'],15000)

    def test_10_inventory_photo_path_and_scope(self):
        pid=self.product('FOTO','u',qty=3)
        photo_path=Path(self.temp.name)/'sample.png'
        photo_path.write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO9eGxkAAAAASUVORK5CYII='))
        self.erp.attach_photo(pid,photo_path)
        photo=self.erp.entity('products',pid)['photo']
        self.assertTrue((Path(self.temp.name)/'photos'/photo).exists())
        record=next(item for item in self.erp.inventory() if item['product_id']==pid)
        self.assertEqual(record['photo'],photo)

    def test_11_branch_separation_even_duplicate_sku_rows(self):
        pid=self.product('SUCURSALES','u',qty=6)
        branch=self.erp.save_catalog('branches',{'name':'Sucursal F10','active':True})
        self.erp.receive_manual(pid,branch,10,'base')
        balances={r['branch_id']:r['onhand_milli'] for r in self.erp.inventory() if r['product_id']==pid}
        self.assertEqual(balances[1],6000)
        self.assertEqual(balances[branch],10000)

    def test_12_duplicate_operation_id_and_atomicity(self):
        pid=self.product('DUPL','u')
        self.erp.receive_manual(pid,1,1,'base',operation_key='f10-one-shot')
        with self.assertRaises(ERPError):
            self.erp.receive_manual(pid,1,1,'base',operation_key='f10-one-shot')
        self.assertEqual(self.balance(pid),1000)
        with self.assertRaises(ERPError):
            self.erp.save_product_with_stock({'sku':'BAD-F10','name':'Error','unit':'u'},entry={
                'branch_id':1,'qty':3,'input_type':'box'})
        self.assertEqual(self.erp.scalar("SELECT COUNT(*) FROM products WHERE sku='BAD-F10'"),0)

    def test_13_invalid_quantity_or_nan_rejected(self):
        for bad in (-1, 'NaN', 'Infinity', 'abc'):
            with self.subTest(bad=bad),self.assertRaises(ERPError):
                determine_entry(True,bad,'base',0,0,'u',1)

    def test_14_audit_integrity_after_sale_and_receipt(self):
        pid=self.product('AUDIT','u',qty=4)
        self.erp.open_cash(1,0)
        self.erp.checkout(1,[{'product_id':pid,'qty':1}],'cash')
        self.assertEqual(self.erp.verify_audit(),(True,None))

if __name__=='__main__':unittest.main()
