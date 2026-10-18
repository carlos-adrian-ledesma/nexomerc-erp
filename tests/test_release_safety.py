"""Pruebas sin Qt para la preparación de publicación."""
import tempfile
import unittest
from pathlib import Path
from nexomerc.core import ERP, ERPError

class ReleaseSafetyTests(unittest.TestCase):
    def test_clean_database_login_and_persistence(self):
        with tempfile.TemporaryDirectory() as folder:
            db = ERP(folder)
            self.assertTrue((Path(folder) / 'nexomerc.sqlite3').is_file())
            self.assertTrue((Path(folder) / 'photos').is_dir())
            self.assertEqual(db.scalar('SELECT COUNT(*) FROM users'), 0)
            self.assertEqual(db.one('SELECT name FROM branches WHERE id=1')['name'], 'Casa central')
            db.initial_admin('admin_demo', 'Administrador Demo', 'pass_demo_2026!')
            with self.assertRaises(ERPError):
                db.login('admin_demo', 'mal_ingreso')
            self.assertEqual(db.login('admin_demo', 'pass_demo_2026!')['role'], 'admin')
            db.close()
            again = ERP(folder)
            self.assertEqual(again.scalar('SELECT COUNT(*) FROM users'), 1)
            self.assertEqual(again.con.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
            again.close()

    def test_application_resources_present(self):
        root=Path(__file__).resolve().parents[1]
        for resource in ('run.py', 'nexomerc/ui.py', 'nexomerc/core.py',
                         'nexomerc/retail.qss','nexomerc/translations.json',
                         'assets/branding/nexomerc.ico',
                         'assets/icons/checkbox_on_f13.png'):
            self.assertTrue((root/resource).is_file(), resource)

if __name__=='__main__': unittest.main()
