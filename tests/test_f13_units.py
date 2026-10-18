import unittest
from nexomerc.units import sale_base_milli
from nexomerc.core import ERPError

class F13UnitsTests(unittest.TestCase):
    def test_rice_loose_3kg(self): self.assertEqual(sale_base_milli(3,'kg','base',5000,0),3000)
    def test_rice_250g(self): self.assertEqual(sale_base_milli(.250,'kg','base',5000,0),250)
    def test_rice_three_packs(self): self.assertEqual(sale_base_milli(3,'kg','pack',5000,0),15000)
    def test_detergent_two_bottles(self):self.assertEqual(sale_base_milli(2,'l','pack',5000,0),10000)
    def test_milk_two_boxes(self):self.assertEqual(sale_base_milli(2,'u','box',0,12000),24000)
    def test_milk_single(self):self.assertEqual(sale_base_milli(1,'u','base',0,12000),1000)
    def test_reject_fractional_box(self):
        with self.assertRaises(ERPError):sale_base_milli(.5,'u','box',0,12000)
    def test_reject_unconfigured_package(self):
        with self.assertRaises(ERPError):sale_base_milli(2,'kg','pack',0,0)
    def test_reject_fractional_units(self):
        with self.assertRaises(ERPError):sale_base_milli(.25,'u','base',0,0)
    def test_reject_too_many_decimals(self):
        with self.assertRaises(ERPError):sale_base_milli(.0005,'kg','base')
    def test_reject_invalid_type(self):
        with self.assertRaises(ERPError):sale_base_milli(2,'kg','crate',5000,10000)
    def test_reject_negative(self):
        with self.assertRaises(ERPError):sale_base_milli(-3,'kg','base')

if __name__=='__main__':unittest.main()
