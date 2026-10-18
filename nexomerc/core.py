"""NexoMerc ERP: transactional local-first domain layer (Python standard library)."""
from __future__ import annotations
import csv
import hashlib
import hmac
import json
import os
import secrets
import shutil
import tempfile
import zipfile
import sqlite3
import uuid
from contextlib import contextmanager, closing
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

MODULES = ['dashboard','products','catalog','inventory','receipts','purchases','suppliers','pos','customers','branches','users','reports','promotions','audit','settings']
ROLE_PERMS = {
 'admin': {'*': {'*'}},
 'manager': {'dashboard':{'view'},'products':{'view','create','edit'},'catalog':{'view','create','edit'},'inventory':{'view','adjust'},'receipts':{'view','create'},'purchases':{'view','create','edit','approve'},'suppliers':{'view','create','edit'},'pos':{'view','sell','void','cash'},'customers':{'view','create','edit'},'branches':{'view','transfer'},'reports':{'view','export'},'promotions':{'view','create','edit'},'audit':{'view'},'settings':{'view'}},
 'warehouse': {'dashboard':{'view'},'products':{'view'},'inventory':{'view','adjust'},'receipts':{'view','create'},'purchases':{'view'},'suppliers':{'view'},'branches':{'view','transfer'}},
 'purchasing': {'dashboard':{'view'},'products':{'view'},'inventory':{'view'},'purchases':{'view','create','edit','approve'},'receipts':{'view','create'},'suppliers':{'view','create','edit'},'branches':{'view'},'reports':{'view'}},
 'cashier': {'dashboard':{'view'},'products':{'view'},'pos':{'view','sell','cash'},'customers':{'view','create'},'promotions':{'view'}},
 'auditor': {'dashboard':{'view'},'products':{'view'},'inventory':{'view'},'purchases':{'view'},'receipts':{'view'},'pos':{'view'},'suppliers':{'view'},'customers':{'view'},'branches':{'view'},'reports':{'view','export'},'promotions':{'view'},'audit':{'view'}},
}
TABLES = {'products','categories','brands','suppliers','customers','branches','purchase_orders','purchase_lines','receipts','receipt_lines','stock_balances','stock_movements','product_packaging','manual_receipts','sales','sale_lines','cash_sessions','transfers','transfer_lines','users','promotions','audit_log','product_archives'}
SCHEMA = '''
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS branches(id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, address TEXT DEFAULT '', active INTEGER NOT NULL DEFAULT 1 CHECK(active IN(0,1)));
CREATE TABLE IF NOT EXISTS categories(id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, parent_id INTEGER REFERENCES categories(id), active INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS brands(id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, active INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS suppliers(id INTEGER PRIMARY KEY, name TEXT NOT NULL, tax_id TEXT UNIQUE, phone TEXT DEFAULT '', email TEXT DEFAULT '', address TEXT DEFAULT '', active INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS customers(id INTEGER PRIMARY KEY, name TEXT NOT NULL, document TEXT UNIQUE, phone TEXT DEFAULT '', email TEXT DEFAULT '', notes TEXT DEFAULT '', points INTEGER NOT NULL DEFAULT 0, active INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY, sku TEXT NOT NULL UNIQUE, barcode TEXT UNIQUE, name TEXT NOT NULL, category_id INTEGER REFERENCES categories(id), brand_id INTEGER REFERENCES brands(id), supplier_id INTEGER REFERENCES suppliers(id), cost_cents INTEGER NOT NULL DEFAULT 0 CHECK(cost_cents>=0), price_cents INTEGER NOT NULL DEFAULT 0 CHECK(price_cents>=0), min_milli INTEGER NOT NULL DEFAULT 0 CHECK(min_milli>=0), max_milli INTEGER NOT NULL DEFAULT 0 CHECK(max_milli>=0), unit TEXT NOT NULL DEFAULT 'u', photo TEXT DEFAULT '', active INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS stock_balances(product_id INTEGER NOT NULL REFERENCES products(id), branch_id INTEGER NOT NULL REFERENCES branches(id), onhand_milli INTEGER NOT NULL DEFAULT 0 CHECK(onhand_milli>=0), reserved_milli INTEGER NOT NULL DEFAULT 0 CHECK(reserved_milli>=0), PRIMARY KEY(product_id,branch_id), CHECK(onhand_milli >= reserved_milli));
CREATE TABLE IF NOT EXISTS product_packaging(product_id INTEGER PRIMARY KEY REFERENCES products(id), pack_milli INTEGER NOT NULL DEFAULT 0 CHECK(pack_milli>=0), box_milli INTEGER NOT NULL DEFAULT 0 CHECK(box_milli>=0));
CREATE TABLE IF NOT EXISTS manual_receipts(id INTEGER PRIMARY KEY, product_id INTEGER NOT NULL REFERENCES products(id), branch_id INTEGER NOT NULL REFERENCES branches(id), input_qty_milli INTEGER NOT NULL CHECK(input_qty_milli>0), input_type TEXT NOT NULL CHECK(input_type IN('base','pack','box')), factor_milli INTEGER NOT NULL CHECK(factor_milli>0), total_milli INTEGER NOT NULL CHECK(total_milli>0), received_at TEXT NOT NULL, expiry_date TEXT, reference TEXT NOT NULL, note TEXT NOT NULL DEFAULT '', operation_key TEXT NOT NULL UNIQUE, actor_id INTEGER NOT NULL REFERENCES users(id));
CREATE INDEX IF NOT EXISTS idx_manual_receipt_expiry ON manual_receipts(expiry_date,branch_id);
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE COLLATE NOCASE, full_name TEXT NOT NULL, password_salt TEXT NOT NULL, password_hash TEXT NOT NULL, role TEXT NOT NULL, branch_id INTEGER REFERENCES branches(id), active INTEGER NOT NULL DEFAULT 1, failures INTEGER NOT NULL DEFAULT 0, locked_until TEXT);
CREATE TABLE IF NOT EXISTS user_permissions(user_id INTEGER NOT NULL REFERENCES users(id), module TEXT NOT NULL, action TEXT NOT NULL, allowed INTEGER NOT NULL CHECK(allowed IN(0,1)), PRIMARY KEY(user_id,module,action));
CREATE TABLE IF NOT EXISTS stock_movements(id INTEGER PRIMARY KEY, timestamp TEXT NOT NULL, product_id INTEGER NOT NULL REFERENCES products(id), branch_id INTEGER NOT NULL REFERENCES branches(id), delta_milli INTEGER NOT NULL, reason TEXT NOT NULL, ref TEXT NOT NULL, user_id INTEGER NOT NULL REFERENCES users(id), notes TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS purchase_orders(id INTEGER PRIMARY KEY, supplier_id INTEGER NOT NULL REFERENCES suppliers(id), branch_id INTEGER NOT NULL REFERENCES branches(id), status TEXT NOT NULL DEFAULT 'draft', created_at TEXT NOT NULL, notes TEXT DEFAULT '', user_id INTEGER NOT NULL REFERENCES users(id));
CREATE TABLE IF NOT EXISTS purchase_lines(id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL REFERENCES purchase_orders(id), product_id INTEGER NOT NULL REFERENCES products(id), qty_milli INTEGER NOT NULL CHECK(qty_milli>0), received_milli INTEGER NOT NULL DEFAULT 0 CHECK(received_milli>=0), cost_cents INTEGER NOT NULL CHECK(cost_cents>=0), UNIQUE(order_id,product_id), CHECK(received_milli<=qty_milli));
CREATE TABLE IF NOT EXISTS receipts(id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL REFERENCES purchase_orders(id), reference TEXT NOT NULL, created_at TEXT NOT NULL, user_id INTEGER NOT NULL REFERENCES users(id), UNIQUE(order_id,reference));
CREATE TABLE IF NOT EXISTS receipt_lines(id INTEGER PRIMARY KEY, receipt_id INTEGER NOT NULL REFERENCES receipts(id), product_id INTEGER NOT NULL REFERENCES products(id), qty_milli INTEGER NOT NULL CHECK(qty_milli>0));
CREATE TABLE IF NOT EXISTS cash_sessions(id INTEGER PRIMARY KEY, branch_id INTEGER NOT NULL REFERENCES branches(id), user_id INTEGER NOT NULL REFERENCES users(id), opened_at TEXT NOT NULL, opening_cents INTEGER NOT NULL DEFAULT 0 CHECK(opening_cents>=0), closed_at TEXT, counted_cents INTEGER, expected_cents INTEGER, UNIQUE(id,branch_id));
CREATE UNIQUE INDEX IF NOT EXISTS unique_active_cash ON cash_sessions(branch_id,user_id) WHERE closed_at IS NULL;
CREATE TABLE IF NOT EXISTS sales(id INTEGER PRIMARY KEY, branch_id INTEGER NOT NULL REFERENCES branches(id), session_id INTEGER NOT NULL REFERENCES cash_sessions(id), user_id INTEGER NOT NULL REFERENCES users(id), customer_id INTEGER REFERENCES customers(id), created_at TEXT NOT NULL, payment TEXT NOT NULL, subtotal_cents INTEGER NOT NULL, total_cents INTEGER NOT NULL CHECK(total_cents>=0), status TEXT NOT NULL DEFAULT 'completed', canceled_at TEXT);
CREATE TABLE IF NOT EXISTS sale_lines(id INTEGER PRIMARY KEY, sale_id INTEGER NOT NULL REFERENCES sales(id), product_id INTEGER NOT NULL REFERENCES products(id), qty_milli INTEGER NOT NULL CHECK(qty_milli>0), base_cents INTEGER NOT NULL, unit_cents INTEGER NOT NULL, cost_cents INTEGER NOT NULL DEFAULT 0, line_cents INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS transfers(id INTEGER PRIMARY KEY, origin_id INTEGER NOT NULL REFERENCES branches(id), dest_id INTEGER NOT NULL REFERENCES branches(id), created_at TEXT NOT NULL, dispatched_at TEXT, received_at TEXT, status TEXT NOT NULL DEFAULT 'draft', user_id INTEGER NOT NULL REFERENCES users(id), notes TEXT NOT NULL DEFAULT '', CHECK(origin_id != dest_id));
CREATE TABLE IF NOT EXISTS transfer_lines(id INTEGER PRIMARY KEY, transfer_id INTEGER NOT NULL REFERENCES transfers(id), product_id INTEGER NOT NULL REFERENCES products(id), qty_milli INTEGER NOT NULL CHECK(qty_milli>0), UNIQUE(transfer_id,product_id));
CREATE TABLE IF NOT EXISTS promotions(id INTEGER PRIMARY KEY, product_id INTEGER NOT NULL REFERENCES products(id), branch_id INTEGER REFERENCES branches(id), name TEXT NOT NULL, price_cents INTEGER NOT NULL CHECK(price_cents>=0), starts_at TEXT NOT NULL, ends_at TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1, CHECK(starts_at <= ends_at));
CREATE TABLE IF NOT EXISTS audit_log(id INTEGER PRIMARY KEY, timestamp TEXT NOT NULL, actor_id INTEGER, action TEXT NOT NULL, entity TEXT NOT NULL, entity_id TEXT NOT NULL, details TEXT NOT NULL, prev_hash TEXT NOT NULL, entry_hash TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS product_archives(product_id INTEGER PRIMARY KEY REFERENCES products(id),archived_at TEXT NOT NULL,archived_by INTEGER NOT NULL REFERENCES users(id),reason TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_moves_product ON stock_movements(product_id,branch_id,timestamp);
CREATE INDEX IF NOT EXISTS idx_sales_time ON sales(created_at,branch_id);
'''

class ERPError(Exception): pass
class PermissionDenied(ERPError): pass

def timestamp(): return datetime.now(timezone.utc).isoformat(timespec='seconds')
def cents(value):
 try:
  d=Decimal(str(value).replace(',','.'))
  if not d.is_finite() or d<0: raise ValueError
  return int((d*100).quantize(Decimal('1'),rounding=ROUND_HALF_UP))
 except (InvalidOperation,ValueError): raise ERPError('Importe monetario no válido.')
def milli(value):
 try:
  d=Decimal(str(value).replace(',','.'))
  if not d.is_finite() or d<=0: raise ValueError
  m=d*1000
  if m!=m.to_integral_value(): raise ERPError('Máximo tres decimales para cantidades.')
  return int(m)
 except (InvalidOperation,ValueError): raise ERPError('Cantidad no válida (debe ser positiva).')
def money(n): return f'{Decimal(int(n))/100:.2f}'
def quantity(n): return f'{Decimal(int(n))/1000:.3f}'.rstrip('0').rstrip('.')
def total_for(q,price): return int((Decimal(int(q))*Decimal(int(price))/1000).quantize(Decimal('1'),rounding=ROUND_HALF_UP))
def password_hash(password,salt=None):
 if len(password)<10: raise ERPError('La contraseña debe tener al menos 10 caracteres.')
 s=salt or secrets.token_hex(16)
 return s, hashlib.pbkdf2_hmac('sha256',password.encode('utf-8'),bytes.fromhex(s),310000).hex()

def default_data_dir():
 base=os.getenv('NEXOMERC_DATA_DIR') or (str(Path(os.getenv('LOCALAPPDATA'))/'NexoMercERP') if os.getenv('LOCALAPPDATA') else str(Path.home()/'.nexomerc_erp'))
 return Path(base).expanduser().resolve()

class ERP:
 def __init__(self,root=None):
  self.root=Path(root).resolve() if root else default_data_dir()
  self.root.mkdir(parents=True,exist_ok=True)
  (self.root/'photos').mkdir(exist_ok=True)
  self.db_path=self.root/'nexomerc.sqlite3'
  self.con=sqlite3.connect(str(self.db_path),timeout=15,isolation_level=None,check_same_thread=False)
  self.con.row_factory=sqlite3.Row
  self.con.execute('PRAGMA journal_mode=WAL')
  self.con.execute('PRAGMA busy_timeout=15000')
  self.con.executescript(SCHEMA)
  self.con.execute("INSERT OR IGNORE INTO branches(id,name,address) VALUES(1,'Casa central','')")
  for k,v in {'business_name':'NexoMerc ERP Demo','tax_id':'','currency':'ARS','receipt_footer':'Gracias por su compra','address':'','telephone':'','locale':'es_AR'}.items():
   self.con.execute('INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)',(k,v))
  self.actor=None
 def close(self): self.con.close()
 def one(self,sql,params=()):
  row=self.con.execute(sql,params).fetchone()
  return dict(row) if row else None
 def all(self,sql,params=()): return [dict(x) for x in self.con.execute(sql,params).fetchall()]
 def scalar(self,sql,params=()):
  r=self.con.execute(sql,params).fetchone()
  return r[0] if r else None
 def entity(self,table,id):
  if table not in TABLES: raise ERPError('Tabla no admitida.')
  r=self.one(f'SELECT * FROM {table} WHERE id=?',(id,))
  if not r: raise ERPError(f'No se encontró el registro de {table} ({id}).')
  return r
 @contextmanager
 def tx(self):
  # Nested business operations use SAVEPOINT to keep the combined product+stock
  # workflow atomic. No nested BEGIN; either every step succeeds or none does.
  if self.con.in_transaction:
   marker='nxm_'+uuid.uuid4().hex
   self.con.execute('SAVEPOINT '+marker)
   try:
    yield
    self.con.execute('RELEASE SAVEPOINT '+marker)
   except BaseException:
    self.con.execute('ROLLBACK TO SAVEPOINT '+marker)
    self.con.execute('RELEASE SAVEPOINT '+marker)
    raise
   return
  self.con.execute('BEGIN IMMEDIATE')
  try:
   yield
   self.con.execute('COMMIT')
  except BaseException:
   self.con.execute('ROLLBACK')
   raise
 def _user(self):
  if self.actor is None: raise PermissionDenied('Debe iniciar sesión.')
  user=self.one('SELECT * FROM users WHERE id=?',(self.actor,))
  if not user or not user['active']: raise PermissionDenied('Su cuenta está desactivada.')
  return user
 def check(self,module,action='view',branch=None):
  u=self._user()
  permissions=ROLE_PERMS.get(u['role'],{})
  if u['role']!='admin':
   granted=action in permissions.get(module,set()) or '*' in permissions.get(module,set())
   override=self.one('SELECT allowed FROM user_permissions WHERE user_id=? AND module=? AND action=?',(u['id'],module,action))
   if override is not None: granted=bool(override['allowed'])
   if not granted:raise PermissionDenied(f'Sin permiso: {module}.{action}.')
  if branch is not None and u['role']!='admin' and u['branch_id'] is not None and int(branch)!=u['branch_id']:
   raise PermissionDenied('Sin autorización para operar sobre otra sucursal.')
  return u
 def available(self,module,action='view',branch=None):
  try: self.check(module,action,branch); return True
  except ERPError: return False
 def initial_admin(self,username,name,password):
  if self.scalar('SELECT COUNT(*) FROM users') != 0: raise ERPError('La cuenta inicial ya fue creada.')
  if not username.strip() or not name.strip(): raise ERPError('Usuario y nombre completo son obligatorios.')
  salt,hash_=password_hash(password)
  with self.tx():
   self.con.execute('INSERT INTO users(username,full_name,password_salt,password_hash,role,branch_id) VALUES(?,?,?,?,?,NULL)',(username.strip(),name.strip(),salt,hash_,'admin'))
  return True
 def login(self,username,password):
  self.actor=None
  u=self.one('SELECT * FROM users WHERE username=? COLLATE NOCASE',(username.strip(),))
  if not u or not u['active']:
   raise ERPError('Usuario o contraseña incorrectos.')
  if u['locked_until'] and datetime.fromisoformat(u['locked_until'])>datetime.now(timezone.utc):
   raise ERPError('Cuenta bloqueada temporalmente tras varios intentos. Vuelva a intentarlo más tarde.')
  actual=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(u['password_salt']),310000).hex()
  if not hmac.compare_digest(actual,u['password_hash']):
   failures=u['failures']+1
   until=(datetime.now(timezone.utc)+timedelta(minutes=15)).isoformat() if failures>=5 else None
   self.con.execute('UPDATE users SET failures=?,locked_until=? WHERE id=?',(failures,until,u['id']))
   raise ERPError('Usuario o contraseña incorrectos.')
  self.con.execute('UPDATE users SET failures=0,locked_until=NULL WHERE id=?',(u['id'],))
  self.actor=u['id']
  with self.tx(): self._audit('login','users',u['id'],{'username':u['username']})
  return self._user()
 def logout(self): self.actor=None
 def _audit(self,action,entity,entity_id,details):
  when=timestamp(); message=json.dumps(details,ensure_ascii=False,sort_keys=True,default=str)
  prev=self.scalar('SELECT entry_hash FROM audit_log ORDER BY id DESC LIMIT 1') or 'GENESIS'
  payload=json.dumps([when,self.actor,action,entity,str(entity_id),message,prev],ensure_ascii=False)
  digest=hashlib.sha256(payload.encode()).hexdigest()
  self.con.execute('INSERT INTO audit_log(timestamp,actor_id,action,entity,entity_id,details,prev_hash,entry_hash) VALUES(?,?,?,?,?,?,?,?)',(when,self.actor,action,entity,str(entity_id),message,prev,digest))
 def verify_audit(self):
  self.check('audit')
  prev='GENESIS'
  for r in self.all('SELECT * FROM audit_log ORDER BY id'):
   p=json.dumps([r['timestamp'],r['actor_id'],r['action'],r['entity'],r['entity_id'],r['details'],prev],ensure_ascii=False)
   if r['prev_hash']!=prev or r['entry_hash']!=hashlib.sha256(p.encode()).hexdigest(): return False,r['id']
   prev=r['entry_hash']
  return True,None
 def list_users(self):
  self.check('users'); return self.all('SELECT id,username,full_name,role,branch_id,active,failures,locked_until FROM users ORDER BY username')
 def save_user(self,username,name,role,branch_id,password=None,id=None,active=True):
  self.check('users','create' if id is None else 'edit')
  if role not in ROLE_PERMS: raise ERPError('Rol desconocido.')
  if not username.strip() or not name.strip():raise ERPError('Usuario y nombre son obligatorios.')
  if branch_id: self.entity('branches',branch_id)
  if role!='admin' and not branch_id: raise ERPError('Los usuarios operativos deben tener una sucursal asignada.')
  with self.tx():
   if id is None:
    salt,hash_=password_hash(password or '')
    cur=self.con.execute('INSERT INTO users(username,full_name,role,branch_id,password_salt,password_hash,active) VALUES(?,?,?,?,?,?,?)',(username.strip(),name.strip(),role,branch_id,salt,hash_,int(active)))
    id=cur.lastrowid
   else:
    old=self.entity('users',id)
    if id==self.actor and (role!='admin' or not active): raise ERPError('No puede quitarse sus propios privilegios ni desactivar su cuenta.')
    if old['role']=='admin' and (role!='admin' or not active) and self.scalar("SELECT COUNT(*) FROM users WHERE role='admin' AND active=1")<=1: raise ERPError('Debe permanecer al menos un administrador activo.')
    self.con.execute('UPDATE users SET username=?,full_name=?,role=?,branch_id=?,active=? WHERE id=?',(username.strip(),name.strip(),role,branch_id,int(active),id))
    if password:
     salt,hash_=password_hash(password)
     self.con.execute('UPDATE users SET password_salt=?,password_hash=?,failures=0,locked_until=NULL WHERE id=?',(salt,hash_,id))
   self._audit('user.save','users',id,{'username':username,'role':role,'branch_id':branch_id,'active':active})
  return id
 def permission_grid(self,user_id):
  self.check('users','view')
  u=self.entity('users',user_id)
  actions=['view','create','edit','delete','adjust','approve','sell','void','cash','transfer','export']
  overrides={(r['module'],r['action']):bool(r['allowed']) for r in self.all('SELECT * FROM user_permissions WHERE user_id=?',(user_id,))}
  defaults=ROLE_PERMS.get(u['role'],{})
  return [{'module':m,'action':a,'allowed':overrides.get((m,a),u['role']=='admin' or a in defaults.get(m,set()))} for m in MODULES for a in actions]
 def save_permissions(self,user_id,entries):
  self.check('users','edit')
  u=self.entity('users',user_id)
  if u['role']=='admin':raise ERPError('El administrador mantiene control total y no admite restricción de permisos.')
  allowed_actions={'view','create','edit','delete','adjust','approve','sell','void','cash','transfer','export'}
  if not entries:raise ERPError('La matriz no puede quedar vacía.')
  if any(e.get('module') not in MODULES or e.get('action') not in allowed_actions for e in entries):raise ERPError('Permiso no reconocido.')
  if len({(e['module'],e['action']) for e in entries})!=len(entries):raise ERPError('Se repitió un permiso.')
  with self.tx():
   self.con.execute('DELETE FROM user_permissions WHERE user_id=?',(user_id,))
   for e in entries:self.con.execute('INSERT INTO user_permissions(user_id,module,action,allowed) VALUES(?,?,?,?)',(user_id,e['module'],e['action'],int(bool(e['allowed']))))
   self._audit('user.permissions','users',user_id,{'matrix':entries})
 def catalogs(self,table,include_archived=False):
  acl={'products':'products','categories':'catalog','brands':'catalog','suppliers':'suppliers','customers':'customers','branches':'branches','promotions':'promotions'}
  if table not in acl:raise ERPError('Catálogo desconocido.')
  self.check(acl[table])
  u=self._user()
  if table=='promotions' and u['role']!='admin' and u['branch_id']:
   return self.all('SELECT * FROM promotions WHERE branch_id IS NULL OR branch_id=? ORDER BY id DESC',(u['branch_id'],))
  if table=='products':
   where='' if include_archived else 'WHERE a.product_id IS NULL'
   return self.all('SELECT p.*,CASE WHEN a.product_id IS NULL THEN 0 ELSE 1 END archived FROM products p LEFT JOIN product_archives a ON a.product_id=p.id '+where+' ORDER BY p.id DESC')
  return self.all(f'SELECT * FROM {table} ORDER BY id DESC')
 def save_catalog(self,table,values,id=None):
  configs={
   'categories':('catalog',('name','parent_id','active')),
   'brands':('catalog',('name','active')),
   'suppliers':('suppliers',('name','tax_id','phone','email','address','active')),
   'customers':('customers',('name','document','phone','email','notes','active')),
   'branches':('branches',('name','address','active')),
   'products':('products',('sku','barcode','name','category_id','brand_id','supplier_id','cost_cents','price_cents','min_milli','max_milli','unit','active')),
  }
  if table not in configs: raise ERPError('Entidad no editable.')
  if table=='products' and id and self.is_product_archived(id):raise ERPError('Producto archivado: restauralo antes de editarlo.')
  module,keys=configs[table]
  self.check(module,'edit' if id else 'create')
  data={k:values[k] for k in keys if k in values}
  for k in ('name','sku'):
   if k in keys and (id is None or k in data) and not str(data.get(k,'')).strip(): raise ERPError(f'{k} es obligatorio.')
  for k in ('barcode','tax_id','document'):
   if k in data and not data[k]:data[k]=None
  for k in ('cost_cents','price_cents','min_milli','max_milli'):
   if k in data and (not isinstance(data[k],int) or data[k]<0):raise ERPError(f'{k} no puede ser negativo.')
  if table=='branches' and id and not data.get('active',True):
   if self.scalar('SELECT COUNT(*) FROM stock_balances WHERE branch_id=? AND onhand_milli>0',(id,)):
    raise ERPError('No puede desactivar una sucursal con stock físico.')
  if table=='categories' and data.get('parent_id'):
   parent=data['parent_id'];seen={id} if id else set()
   while parent:
    if parent in seen:raise ERPError('La jerarquía de categorías genera un ciclo.')
    seen.add(parent)
    parent=self.entity('categories',parent).get('parent_id')
  if not data: raise ERPError('No hay datos para guardar.')
  with self.tx():
   if id:
    self.entity(table,id)
    self.con.execute(f"UPDATE {table} SET {','.join(k+'=?' for k in data)} WHERE id=?",(*data.values(),id))
   else:
    cur=self.con.execute(f"INSERT INTO {table}({','.join(data)}) VALUES({','.join('?' for _ in data)})",tuple(data.values()))
    id=cur.lastrowid
   self._audit('catalog.save',table,id,data)
  return id
 def is_product_archived(self,product_id):
  return bool(self.one('SELECT product_id FROM product_archives WHERE product_id=?',(int(product_id),)))
 def archive_impact(self,product_id):
  """Describe linked data prior to reversible removal. Read only; no write or data deletion."""
  self.check('products','delete')
  p=self.entity('products',product_id)
  branches=self.all('''SELECT b.name,s.branch_id,s.onhand_milli,s.reserved_milli
    FROM stock_balances s JOIN branches b ON b.id=s.branch_id WHERE s.product_id=? ORDER BY b.id''',(product_id,))
  purchases=self.scalar('''SELECT COUNT(*) FROM purchase_lines l JOIN purchase_orders o ON o.id=l.order_id
    WHERE l.product_id=? AND o.status NOT IN ('received','completed','canceled')''',(product_id,))
  transfers=self.scalar('''SELECT COUNT(*) FROM transfer_lines l JOIN transfers t ON t.id=l.transfer_id
    WHERE l.product_id=? AND t.status NOT IN ('received','canceled')''',(product_id,))
  return {
   'product':p,
   'branches':branches,
   'onhand_milli':sum(row['onhand_milli'] for row in branches),
   'reserved_milli':sum(row['reserved_milli'] for row in branches),
   'purchases_pending':purchases,
   'transfers_pending':transfers,
   'sale_lines':self.scalar('SELECT COUNT(*) FROM sale_lines WHERE product_id=?',(product_id,)),
   'receipt_lines':self.scalar('SELECT COUNT(*) FROM receipt_lines WHERE product_id=?',(product_id,)),
   'manual_receipts':self.scalar('SELECT COUNT(*) FROM manual_receipts WHERE product_id=?',(product_id,)),
   'stock_movements':self.scalar('SELECT COUNT(*) FROM stock_movements WHERE product_id=?',(product_id,)),
   'promotions':self.scalar('SELECT COUNT(*) FROM promotions WHERE product_id=?',(product_id,)),
  }
 def archive_product(self,product_id,reason='Retirado del catálogo por confirmación del administrador'):
  self.check('products','delete')
  # Perform checks and changes in one transaction to avoid a TOCTOU gap.
  with self.tx():
   impact=self.archive_impact(product_id)
   product=impact['product']
   if self.is_product_archived(product_id):raise ERPError('El producto ya está eliminado; utilizá Restaurar producto.')
   if impact['reserved_milli']:
    raise ERPError('El producto tiene unidades reservadas. Liberá primero las reservas para no perder compromisos.')
   if impact['purchases_pending']:
    raise ERPError('El producto tiene órdenes de compra pendientes. Cerrá o cancelá esas operaciones antes de eliminarlo.')
   if impact['transfers_pending']:
    raise ERPError('El producto tiene traslados pendientes. Completalos o cancelalos antes de eliminarlo.')
   note=(str(reason).strip() or 'Retirado del catálogo por el administrador')[:500]
   self.con.execute('INSERT INTO product_archives(product_id,archived_at,archived_by,reason) VALUES(?,?,?,?)',
                    (product_id,timestamp(),self.actor,note))
   self.con.execute('UPDATE products SET active=0 WHERE id=?',(product_id,))
   # Never DELETE stock rows or history; they remain available if the item is restored.
   self.con.execute('UPDATE promotions SET active=0 WHERE product_id=?',(product_id,))
   self._audit('product.archive','products',product_id,{
    'sku':product['sku'],'reason':note,'onhand_milli_retained':impact['onhand_milli'],
    'reserved_milli':impact['reserved_milli'],'branches':len(impact['branches']),
    'promotions_deactivated':impact['promotions']
   })
 def restore_product(self,product_id):
  self.check('products','delete')
  product=self.entity('products',product_id)
  if not self.is_product_archived(product_id):raise ERPError('El producto no está archivado.')
  with self.tx():
   self.con.execute('DELETE FROM product_archives WHERE product_id=?',(product_id,))
   # It remains inactive until explicitly reactivated by an authorized user.
   self._audit('product.restore','products',product_id,{'sku':product['sku'],'active':0})
 def quick_catalog(self,table,name,parent_id=None):
  if table not in ('categories','brands','suppliers'):raise ERPError('Catálogo no permitido.')
  module='suppliers' if table=='suppliers' else 'catalog'
  self.check(module,'create')
  name=' '.join(str(name).split())
  if not name:raise ERPError('El nombre es obligatorio.')
  for row in self.all(f'SELECT id,name FROM {table}'):
   if ' '.join(row['name'].split()).casefold()==name.casefold():return row['id']
  values={'name':name,'active':True}
  if table=='categories':values['parent_id']=parent_id
  return self.save_catalog(table,values)
 def attach_photo(self,product_id,file_path):
  self.check('products','edit'); self.entity('products',product_id)
  src=Path(file_path)
  if not src.is_file() or src.stat().st_size>5*1024*1024: raise ERPError('Imagen inexistente o mayor a 5 MB.')
  content=src.read_bytes()
  if content.startswith(b'\x89PNG\r\n\x1a\n'): ext='.png'
  elif content.startswith(b'\xff\xd8\xff'): ext='.jpg'
  elif content.startswith(b'RIFF') and content[8:12]==b'WEBP': ext='.webp'
  else: raise ERPError('Solo se admiten PNG, JPG y WebP válidos.')
  dest=self.root/'photos'/(uuid.uuid4().hex+ext)
  dest.write_bytes(content)
  with self.tx():
   old=self.entity('products',product_id)['photo']
   self.con.execute('UPDATE products SET photo=? WHERE id=?',(dest.name,product_id))
   self._audit('product.photo','products',product_id,{'old':old,'new':dest.name})
  return dest
 def _branch(self,branch_id):
  b=self.entity('branches',branch_id)
  if not b['active']: raise ERPError('La sucursal está inactiva.')
 def _product(self,product_id):
  p=self.entity('products',product_id)
  if not p['active'] or self.is_product_archived(product_id):raise ERPError('Producto inactivo o archivado.')
  return p
 def _balance(self,product_id,branch_id):
  self.con.execute('INSERT OR IGNORE INTO stock_balances(product_id,branch_id) VALUES(?,?)',(product_id,branch_id))
  return self.one('SELECT * FROM stock_balances WHERE product_id=? AND branch_id=?',(product_id,branch_id))
 def _stock_move(self,pid,bid,delta,reason,ref,notes=''):
  before=self._balance(pid,bid)
  after=before['onhand_milli']+delta
  if after<before['reserved_milli']: raise ERPError('Stock insuficiente; no se permiten existencias negativas ni consumo de reservas.')
  self.con.execute('UPDATE stock_balances SET onhand_milli=? WHERE product_id=? AND branch_id=?',(after,pid,bid))
  self.con.execute('INSERT INTO stock_movements(timestamp,product_id,branch_id,delta_milli,reason,ref,user_id,notes) VALUES(?,?,?,?,?,?,?,?)',(timestamp(),pid,bid,delta,reason,str(ref),self.actor,notes))
 def packaging(self,pid):
  self.check('products','view')
  self.entity('products',pid)
  result=self.one('SELECT pack_milli,box_milli FROM product_packaging WHERE product_id=?',(pid,))
  return result or {'pack_milli':0,'box_milli':0}
 def save_product_with_stock(self,values,pack_factor=0,box_factor=0,entry=None,id=None):
  # All product/catalog/packaging/initial stock changes commit in ONE transaction.
  self.check('products','edit' if id else 'create')
  if entry:self.check('inventory','adjust',entry['branch_id'])
  if id and 'unit' in values:
   previous=self.entity('products',id)
   if previous['unit']!=values['unit'] and self.scalar('SELECT COUNT(*) FROM stock_movements WHERE product_id=?',(id,)):
    raise ERPError('La unidad base no puede cambiar si el producto ya tiene movimientos. Creá otro SKU o realizá una migración documentada.')
  p=milli(pack_factor) if Decimal(str(pack_factor).replace(',','.'))>0 else 0
  b=milli(box_factor) if Decimal(str(box_factor).replace(',','.'))>0 else 0
  with self.tx():
   pid=self.save_catalog('products',values,id)
   self.con.execute('INSERT INTO product_packaging(product_id,pack_milli,box_milli) VALUES(?,?,?) ON CONFLICT(product_id) DO UPDATE SET pack_milli=excluded.pack_milli,box_milli=excluded.box_milli',(pid,p,b))
   if entry:
    self.receive_manual(pid,entry['branch_id'],entry['qty'],entry['input_type'],entry.get('reference',''),entry.get('note',''),entry.get('expiry',''),entry.get('operation_key'))
  return pid
 def receive_manual(self,pid,bid,qty,input_type='base',reference='',note='',expiry='',operation_key=None):
  self.check('inventory','adjust',bid);self._branch(bid)
  product=self._product(pid)
  if input_type not in ('base','pack','box'):raise ERPError('Presentación de entrada inválida.')
  input_qty=milli(qty)
  # Packages are counted in complete items; kilograms/litres can be fractional.
  if input_type!='base' or product['unit'] not in ('kg','l'):
   if input_qty%1000:raise ERPError('Las unidades, paquetes y cajas deben ingresarse como números enteros.')
  config=self.one('SELECT pack_milli,box_milli FROM product_packaging WHERE product_id=?',(pid,)) or {'pack_milli':0,'box_milli':0}
  factor={'base':1000,'pack':config['pack_milli'],'box':config['box_milli']}[input_type]
  if factor<=0:raise ERPError('Configurá el contenido de esta presentación desde Productos antes de ingresar mercadería.')
  total_raw=input_qty*factor
  if total_raw%1000:raise ERPError('La conversión excede los tres decimales permitidos.')
  total=total_raw//1000
  if total<=0 or total>9223372036854775807:raise ERPError('Cantidad resultante inválida.')
  expiration=str(expiry or '').strip()
  if expiration:
   from datetime import date
   try:date.fromisoformat(expiration)
   except ValueError:raise ERPError('Vencimiento inválido: utilizá AAAA-MM-DD.')
  reference=' '.join(str(reference or '').split())[:120]
  notes=' '.join(str(note or '').split())[:500] or 'Ingreso de mercadería'
  op=str(operation_key or uuid.uuid4().hex)
  with self.tx():
   if self.one('SELECT id FROM manual_receipts WHERE operation_key=?',(op,)):
    raise ERPError('Esta entrada ya fue confirmada; actualizá el inventario antes de reintentar.')
   cur=self.con.execute('''INSERT INTO manual_receipts(product_id,branch_id,input_qty_milli,input_type,factor_milli,total_milli,received_at,expiry_date,reference,note,operation_key,actor_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''',
    (pid,bid,input_qty,input_type,factor,total,timestamp(),expiration or None,reference,notes,op,self.actor))
   rid=cur.lastrowid
   self._stock_move(pid,bid,total,'manual_receipt',f'REC-{rid}',f'{notes} | {input_type}: {quantity(input_qty)} | venc.: {expiration or "sin informar"} | {reference}')
   self._audit('stock.manual_receipt','products',pid,{'branch':bid,'id':rid,'delta_milli':total,'input_unit':input_type,'reference':reference,'expiry':expiration})
  return rid
 def manual_receipts(self,pid,bid):
  self.check('inventory','view',bid)
  return self.all('SELECT id,received_at,input_qty_milli,input_type,factor_milli,total_milli,expiry_date,reference,note FROM manual_receipts WHERE product_id=? AND branch_id=? ORDER BY id DESC',(pid,bid))
 def inventory(self,branch_id=None):
  self.check('inventory','view',branch_id)
  q='''SELECT p.id product_id,p.sku,p.name,p.photo,p.unit,p.min_milli,b.id branch_id,b.name branch,COALESCE(s.onhand_milli,0) onhand_milli,COALESCE(s.reserved_milli,0) reserved_milli,COALESCE(s.onhand_milli,0)-COALESCE(s.reserved_milli,0) available_milli
  FROM products p CROSS JOIN branches b LEFT JOIN stock_balances s ON s.product_id=p.id AND s.branch_id=b.id WHERE p.active=1 AND b.active=1 AND NOT EXISTS (SELECT 1 FROM product_archives a WHERE a.product_id=p.id)'''
  args=[]
  if branch_id:q+=' AND b.id=?';args.append(branch_id)
  u=self._user()
  if u['role']!='admin' and u['branch_id']:
   q+=' AND b.id=?';args.append(u['branch_id'])
  return self.all(q+' ORDER BY p.name,b.name',args)
 def adjust_stock(self,pid,bid,delta_qty,notes):
  self.check('inventory','adjust',bid); self._branch(bid);self._product(pid)
  if not str(notes).strip():raise ERPError('El ajuste exige un motivo.')
  delta=milli(abs(Decimal(str(delta_qty))))*(1 if Decimal(str(delta_qty))>0 else -1) if Decimal(str(delta_qty))!=0 else 0
  if delta==0:raise ERPError('El ajuste no puede ser cero.')
  with self.tx():
   self._stock_move(pid,bid,delta,'adjustment','MANUAL',notes)
   self._audit('stock.adjust','products',pid,{'branch':bid,'delta_milli':delta,'reason':notes})
 def physical_count(self,pid,bid,qty,notes):
  self.check('inventory','adjust',bid);self._branch(bid);self._product(pid)
  if not notes.strip(): raise ERPError('Ingrese una observación para el conteo físico.')
  try:
   d=Decimal(str(qty).replace(',','.'))
   q=d*1000
   if not q.is_finite() or q<0 or q!=q.to_integral_value():raise ValueError
   counted=int(q)
  except (InvalidOperation,ValueError):raise ERPError('Cantidad de conteo inválida.')
  with self.tx():
   before=self._balance(pid,bid)['onhand_milli']
   if counted<self._balance(pid,bid)['reserved_milli']:
    raise ERPError('El conteo es menor que las unidades reservadas. Libere reservas con autorización.')
   diff=counted-before
   if diff:
    self._stock_move(pid,bid,diff,'physical_count','COUNT',notes)
   self._audit('stock.physical_count','products',pid,{'branch':bid,'before_milli':before,'counted_milli':counted,'difference_milli':diff,'notes':notes})
  return diff
 def reserve(self,pid,bid,qty):
  self.check('inventory','adjust',bid);m=milli(qty)
  with self.tx():
   b=self._balance(pid,bid)
   if b['onhand_milli']-b['reserved_milli']<m:raise ERPError('No hay stock disponible para reservar.')
   self.con.execute('UPDATE stock_balances SET reserved_milli=reserved_milli+? WHERE product_id=? AND branch_id=?',(m,pid,bid))
   self._audit('stock.reserve','products',pid,{'branch':bid,'qty_milli':m})
 def unreserve(self,pid,bid,qty):
  self.check('inventory','adjust',bid);m=milli(qty)
  with self.tx():
   b=self._balance(pid,bid)
   if b['reserved_milli']<m:raise ERPError('Reserva insuficiente.')
   self.con.execute('UPDATE stock_balances SET reserved_milli=reserved_milli-? WHERE product_id=? AND branch_id=?',(m,pid,bid))
   self._audit('stock.unreserve','products',pid,{'branch':bid,'qty_milli':m})
 def create_po(self,supplier_id,branch_id,items,notes=''):
  self.check('purchases','create',branch_id);self._branch(branch_id);self.entity('suppliers',supplier_id)
  if not items: raise ERPError('Agregue al menos un producto a la orden.')
  if len({int(x['product_id']) for x in items})!=len(items):raise ERPError('Hay productos duplicados en la orden.')
  with self.tx():
   cur=self.con.execute('INSERT INTO purchase_orders(supplier_id,branch_id,created_at,notes,user_id) VALUES(?,?,?,?,?)',(supplier_id,branch_id,timestamp(),notes,self.actor)); oid=cur.lastrowid
   for item in items:
    self._product(item['product_id'])
    self.con.execute('INSERT INTO purchase_lines(order_id,product_id,qty_milli,cost_cents) VALUES(?,?,?,?)',(oid,item['product_id'],milli(item['qty']),cents(item['cost'])))
   self._audit('purchase.create','purchase_orders',oid,{'lines':items})
  return oid
 def submit_po(self,id):
  po=self.entity('purchase_orders',id);self.check('purchases','approve',po['branch_id'])
  if po['status']!='draft':raise ERPError('Solo puede enviar órdenes en borrador.')
  with self.tx():
   self.con.execute("UPDATE purchase_orders SET status='submitted' WHERE id=?",(id,))
   self._audit('purchase.submit','purchase_orders',id,{})
 def cancel_po(self,id):
  po=self.entity('purchase_orders',id);self.check('purchases','approve',po['branch_id'])
  if po['status'] not in ('draft','submitted'):raise ERPError('La orden no puede cancelarse en este estado.')
  with self.tx():
   self.con.execute("UPDATE purchase_orders SET status='canceled' WHERE id=?",(id,))
   self._audit('purchase.cancel','purchase_orders',id,{})
 def receive_po(self,id,items,reference):
  po=self.entity('purchase_orders',id);self.check('receipts','create',po['branch_id'])
  if po['status'] not in ('submitted','partial'):raise ERPError('Debe enviar la orden antes de recibir mercadería.')
  if not reference.strip() or not items:raise ERPError('Indique remito/referencia y cantidades recibidas.')
  if len(set(items))!=len(items):raise ERPError('Productos duplicados en recepción.')
  with self.tx():
   allowed={r['product_id']:r for r in self.all('SELECT * FROM purchase_lines WHERE order_id=?',(id,))}
   processed=[]
   for pid,qty in items.items():
    pid=int(pid);q=milli(qty)
    if pid not in allowed or q>allowed[pid]['qty_milli']-allowed[pid]['received_milli']:raise ERPError('Recepción supera la cantidad pendiente de la orden.')
    processed.append((pid,q))
   cur=self.con.execute('INSERT INTO receipts(order_id,reference,created_at,user_id) VALUES(?,?,?,?)',(id,reference.strip(),timestamp(),self.actor)); rid=cur.lastrowid
   for pid,q in processed:
    self.con.execute('INSERT INTO receipt_lines(receipt_id,product_id,qty_milli) VALUES(?,?,?)',(rid,pid,q))
    self.con.execute('UPDATE purchase_lines SET received_milli=received_milli+? WHERE order_id=? AND product_id=?',(q,id,pid))
    self._stock_move(pid,po['branch_id'],q,'purchase_receipt',rid,reference)
   pending=self.scalar('SELECT COUNT(*) FROM purchase_lines WHERE order_id=? AND qty_milli>received_milli',(id,))
   self.con.execute('UPDATE purchase_orders SET status=? WHERE id=?',('partial' if pending else 'completed',id))
   self._audit('purchase.receive','receipts',rid,{'order':id,'reference':reference,'qty':processed})
  return rid
 def create_transfer(self,origin,dest,items,notes=''):
  self.check('branches','transfer',origin)
  self._branch(origin);self._branch(dest)
  if origin==dest or not items or len({int(x['product_id']) for x in items})!=len(items):raise ERPError('Transferencia inválida: revise sucursales y productos.')
  with self.tx():
   cur=self.con.execute('INSERT INTO transfers(origin_id,dest_id,created_at,user_id,notes) VALUES(?,?,?,?,?)',(origin,dest,timestamp(),self.actor,notes));tid=cur.lastrowid
   for item in items:
    self._product(item['product_id'])
    self.con.execute('INSERT INTO transfer_lines(transfer_id,product_id,qty_milli) VALUES(?,?,?)',(tid,item['product_id'],milli(item['qty'])))
   self._audit('transfer.create','transfers',tid,{'items':items,'from':origin,'to':dest})
  return tid
 def dispatch_transfer(self,id):
  t=self.entity('transfers',id);self.check('branches','transfer',t['origin_id'])
  if t['status']!='draft':raise ERPError('Solo se despachan transferencias en borrador.')
  with self.tx():
   for r in self.all('SELECT * FROM transfer_lines WHERE transfer_id=?',(id,)):
    self._stock_move(r['product_id'],t['origin_id'],-r['qty_milli'],'transfer_dispatch',id)
   self.con.execute("UPDATE transfers SET status='in_transit',dispatched_at=? WHERE id=?",(timestamp(),id))
   self._audit('transfer.dispatch','transfers',id,{})
 def receive_transfer(self,id):
  t=self.entity('transfers',id);self.check('branches','transfer',t['dest_id'])
  if t['status']!='in_transit':raise ERPError('La transferencia no está en tránsito.')
  with self.tx():
   for r in self.all('SELECT * FROM transfer_lines WHERE transfer_id=?',(id,)):
    self._stock_move(r['product_id'],t['dest_id'],r['qty_milli'],'transfer_receive',id)
   self.con.execute("UPDATE transfers SET status='received',received_at=? WHERE id=?",(timestamp(),id))
   self._audit('transfer.receive','transfers',id,{})
 def cancel_transfer(self,id):
  t=self.entity('transfers',id);self.check('branches','transfer',t['origin_id'])
  if t['status']!='draft':raise ERPError('No se puede cancelar un traslado expedido; requiere una devolución trazable.')
  with self.tx():
   self.con.execute("UPDATE transfers SET status='canceled' WHERE id=?",(id,))
   self._audit('transfer.cancel','transfers',id,{})
 def create_promotion(self,pid,branch,name,price,start,end):
  self.check('promotions','create',branch);p=self._product(pid)
  if branch:self._branch(branch)
  if price<0 or cents(price)>p['price_cents']:raise ERPError('El precio promocional debe ser menor o igual al precio base.')
  if start>end:raise ERPError('Las fechas de vigencia están invertidas.')
  with self.tx():
   cur=self.con.execute('INSERT INTO promotions(product_id,branch_id,name,price_cents,starts_at,ends_at) VALUES(?,?,?,?,?,?)',(pid,branch,name,cents(price),start,end));id=cur.lastrowid
   self._audit('promotion.create','promotions',id,{'product':pid,'price':price,'start':start,'end':end})
  return id
 def set_promotion_active(self,id,active):
  p=self.entity('promotions',id);self.check('promotions','edit',p['branch_id'])
  with self.tx():
   self.con.execute('UPDATE promotions SET active=? WHERE id=?',(int(active),id))
   self._audit('promotion.toggle','promotions',id,{'active':active})
 def effective_price(self,pid,branch,date=None):
  p=self._product(pid)
  d=date or datetime.now().date().isoformat()
  r=self.one('SELECT MIN(price_cents) best FROM promotions WHERE product_id=? AND active=1 AND (branch_id IS NULL OR branch_id=?) AND starts_at<=? AND ends_at>=?', (pid,branch,d,d))
  return min(p['price_cents'],r['best']) if r and r['best'] is not None else p['price_cents']
 def open_cash(self,branch,opening):
  self.check('pos','cash',branch);self._branch(branch)
  if self.one('SELECT id FROM cash_sessions WHERE branch_id=? AND user_id=? AND closed_at IS NULL',(branch,self.actor)):
   raise ERPError('Ya tiene una caja abierta en esta sucursal. Ciérrela antes de abrir otra.')
  with self.tx():
   cur=self.con.execute('INSERT INTO cash_sessions(branch_id,user_id,opened_at,opening_cents) VALUES(?,?,?,?)',(branch,self.actor,timestamp(),cents(opening))); id=cur.lastrowid
   self._audit('cash.open','cash_sessions',id,{'branch':branch,'opening':opening})
  return id
 def cash_session(self,branch):
  self.check('pos','view',branch)
  return self.one('SELECT * FROM cash_sessions WHERE user_id=? AND branch_id=? AND closed_at IS NULL',(self.actor,branch))
 def _cash_expected(self,session):
  sales=self.scalar("SELECT COALESCE(SUM(CASE WHEN status='completed' THEN total_cents ELSE 0 END),0) FROM sales WHERE session_id=? AND payment='cash'",(session['id'],))
  return session['opening_cents']+sales
 def close_cash(self,branch,counted):
  self.check('pos','cash',branch); sess=self.cash_session(branch)
  if not sess:raise ERPError('No hay caja abierta.')
  expected=self._cash_expected(sess)
  with self.tx():
   self.con.execute('UPDATE cash_sessions SET closed_at=?,counted_cents=?,expected_cents=? WHERE id=?',(timestamp(),cents(counted),expected,sess['id']))
   self._audit('cash.close','cash_sessions',sess['id'],{'expected_cents':expected,'counted_cents':cents(counted),'difference_cents':cents(counted)-expected})
  return expected
 def checkout(self,branch,items,payment,customer_id=None):
  self.check('pos','sell',branch);self._branch(branch)
  if payment not in ('cash','debit','credit','transfer','qr','check'):raise ERPError('Medio de pago no reconocido.')
  if not items:raise ERPError('El carrito está vacío.')
  if len({int(x['product_id']) for x in items})!=len(items):raise ERPError('El carrito contiene productos duplicados.')
  if customer_id:self.entity('customers',customer_id)
  with self.tx():
   sess=self.cash_session(branch)
   if not sess:raise ERPError('Abra su caja antes de vender.')
   lines=[]
   for item in items:
    p=self._product(item['product_id']);q=milli(item['qty']);b=self._balance(p['id'],branch)
    if b['onhand_milli']-b['reserved_milli']<q:raise ERPError(f'Stock insuficiente para {p["name"]}.')
    price=self.effective_price(p['id'],branch)
    lines.append((p,q,price,total_for(q,price)))
   subtotal=sum(total_for(q,p['price_cents']) for p,q,price,line in lines)
   total=sum(line for p,q,price,line in lines)
   cur=self.con.execute('INSERT INTO sales(branch_id,session_id,user_id,customer_id,created_at,payment,subtotal_cents,total_cents) VALUES(?,?,?,?,?,?,?,?)',(branch,sess['id'],self.actor,customer_id,timestamp(),payment,subtotal,total));sid=cur.lastrowid
   for p,q,price,line in lines:
    self.con.execute('INSERT INTO sale_lines(sale_id,product_id,qty_milli,base_cents,unit_cents,cost_cents,line_cents) VALUES(?,?,?,?,?,?,?)',(sid,p['id'],q,p['price_cents'],price,p['cost_cents'],line))
    self._stock_move(p['id'],branch,-q,'sale',sid)
   if customer_id:
    self.con.execute('UPDATE customers SET points=points+? WHERE id=?',(total//10000,customer_id))
   self._audit('sale.checkout','sales',sid,{'total_cents':total,'branch':branch,'payment':payment,'lines':len(lines)})
  return sid
 def void_sale(self,id,reason):
  sale=self.entity('sales',id);self.check('pos','void',sale['branch_id'])
  if sale['status']!='completed': raise ERPError('Esta venta ya fue anulada.')
  if self.entity('cash_sessions',sale['session_id'])['closed_at']:
   raise ERPError('La caja ya fue cerrada. Esta operación requiere un procedimiento de devolución separado.')
  if not reason.strip():raise ERPError('La anulación requiere un motivo.')
  with self.tx():
   for line in self.all('SELECT * FROM sale_lines WHERE sale_id=?',(id,)):
    self._stock_move(line['product_id'],sale['branch_id'],line['qty_milli'],'sale_void',id,reason)
   self.con.execute("UPDATE sales SET status='void',canceled_at=? WHERE id=?",(timestamp(),id))
   if sale['customer_id']:
    self.con.execute('UPDATE customers SET points=MAX(0,points-?) WHERE id=?',(sale['total_cents']//10000,sale['customer_id']))
   self._audit('sale.void','sales',id,{'reason':reason,'total_cents':sale['total_cents']})
 def sale_ticket(self,id):
  s=self.entity('sales',id);self.check('pos','view',s['branch_id'])
  settings=dict((r['key'],r['value']) for r in self.all('SELECT * FROM settings'))
  lines=self.all('SELECT sl.*,p.name,p.sku FROM sale_lines sl JOIN products p ON p.id=sl.product_id WHERE sl.sale_id=?',(id,))
  text=[settings.get('business_name','NexoMerc ERP'),settings.get('address',''),'COMPROBANTE INTERNO - NO FISCAL',f'Operación #{id} | {s["created_at"]}',f'Estado: {s["status"]} | Medio: {s["payment"]}','-'*44]
  for r in lines:text.append(f'{r["name"]}  {quantity(r["qty_milli"])} x {money(r["unit_cents"])} = {money(r["line_cents"])}')
  text += ['-'*44,f'TOTAL: {settings.get("currency","ARS")} {money(s["total_cents"])}',settings.get('receipt_footer','')]
  return '\n'.join(text)
 def _low_stock_count(self,branch=None):
  q='''SELECT COUNT(*) FROM products p CROSS JOIN branches b LEFT JOIN stock_balances s ON s.product_id=p.id AND s.branch_id=b.id WHERE p.active=1 AND b.active=1 AND COALESCE(s.onhand_milli,0)<p.min_milli'''
  return self.scalar(q+(' AND b.id=?' if branch else ''), (branch,) if branch else ())
 def get_dashboard(self,branch=None):
  self.check('dashboard','view',branch)
  u=self._user()
  if u['branch_id'] and u['role']!='admin':branch=u['branch_id']
  clause=' AND branch_id=?' if branch else ''
  args=(branch,) if branch else ()
  today=datetime.now().astimezone().date().isoformat()
  tz=datetime.now().astimezone().tzinfo
  local_midnight=datetime.combine(datetime.now().date(),datetime.min.time(),tzinfo=tz).astimezone(timezone.utc).isoformat(timespec='seconds')
  local_month=datetime.combine(datetime.now().date().replace(day=1),datetime.min.time(),tzinfo=tz).astimezone(timezone.utc).isoformat(timespec='seconds')
  return {
   'today_cents':self.scalar("SELECT COALESCE(SUM(total_cents),0) FROM sales WHERE status='completed' AND created_at>=?"+clause,(local_midnight,)+args),
   'month_cents':self.scalar("SELECT COALESCE(SUM(total_cents),0) FROM sales WHERE status='completed' AND created_at>=?"+clause,(local_month,)+args),
   'sales':self.scalar("SELECT COUNT(*) FROM sales WHERE status='completed'"+clause,args),
   'pending_orders':self.scalar("SELECT COUNT(*) FROM purchase_orders WHERE status IN ('submitted','partial')"+clause,args),
   'low_stock':self._low_stock_count(branch),
   'recent':self.all('SELECT a.timestamp,a.action,a.entity,a.entity_id FROM audit_log a ORDER BY id DESC LIMIT 10') if u['role']=='admin' else [],
  }
 def reports(self,branch=None,start=None,end=None):
  self.check('reports','view',branch)
  u=self._user()
  if u['branch_id'] and u['role']!='admin':branch=u['branch_id']
  args=(branch,) if branch else ();clause=' AND s.branch_id=?' if branch else ''
  from datetime import date
  if start:date.fromisoformat(start);clause+=' AND substr(s.created_at,1,10)>=?';args+=(start,)
  if end:date.fromisoformat(end);clause+=' AND substr(s.created_at,1,10)<=?';args+=(end,)
  if start and end and start>end:raise ERPError('La fecha inicial debe ser anterior a la final.')
  return {
   'sales':self.all("SELECT substr(s.created_at,1,10) date, COUNT(*) tickets, SUM(s.total_cents) total_cents FROM sales s WHERE s.status='completed'"+clause+' GROUP BY substr(s.created_at,1,10) ORDER BY date DESC LIMIT 40',args),
   'top':self.all("SELECT p.sku,p.name,SUM(sl.qty_milli) qty_milli,SUM(sl.line_cents) total_cents FROM sale_lines sl JOIN sales s ON s.id=sl.sale_id JOIN products p ON p.id=sl.product_id WHERE s.status='completed'"+clause+' GROUP BY p.id ORDER BY total_cents DESC LIMIT 30',args),
   'gross_margin':self.all("SELECT substr(s.created_at,1,10) date, SUM(sl.line_cents) revenue_cents, SUM(CAST((sl.qty_milli * sl.cost_cents + 500)/1000 AS INTEGER)) cost_cents FROM sales s JOIN sale_lines sl ON s.id=sl.sale_id WHERE s.status='completed'"+clause+' GROUP BY substr(s.created_at,1,10) ORDER BY date DESC LIMIT 40',args),
   'payments':self.all("SELECT s.payment, COUNT(*) tickets,SUM(s.total_cents) total_cents FROM sales s WHERE s.status='completed'"+clause+' GROUP BY s.payment',args),
  }
 def list_audit(self,limit=500):
  self.check('audit')
  u=self._user()
  if u['role']!='admin' and u['branch_id']:
   return self.all('SELECT a.*,u.username FROM audit_log a LEFT JOIN users u ON a.actor_id=u.id WHERE u.branch_id=? ORDER BY a.id DESC LIMIT ?', (u['branch_id'],min(int(limit),5000)))
  return self.all('SELECT a.*,u.username FROM audit_log a LEFT JOIN users u ON a.actor_id=u.id ORDER BY a.id DESC LIMIT ?', (min(int(limit),5000),))
 def list_simple(self,table):
  maps={'purchase_orders':'purchases','purchase_lines':'purchases','receipts':'receipts','receipt_lines':'receipts','sales':'pos','sale_lines':'pos','cash_sessions':'pos','transfers':'branches','transfer_lines':'branches','stock_movements':'inventory','promotions':'promotions'}
  if table not in maps:raise ERPError('Listado no admitido.')
  self.check(maps[table])
  u=self._user()
  clause=''
  if u['branch_id'] and u['role']!='admin':
   bid=int(u['branch_id'])
   if table in ('purchase_orders','sales','cash_sessions'):
    clause=f' WHERE branch_id={bid}'
   elif table=='transfers':clause=f' WHERE origin_id={bid} OR dest_id={bid}'
   elif table=='receipts':clause=f' WHERE order_id IN (SELECT id FROM purchase_orders WHERE branch_id={bid})'
   elif table=='stock_movements':clause=f' WHERE branch_id={bid}'
  return self.all(f'SELECT * FROM {table}{clause} ORDER BY id DESC LIMIT 1000')
 def read_settings(self):
  self.check('settings');return {r['key']:r['value'] for r in self.all('SELECT * FROM settings ORDER BY key')}
 def save_settings(self,data):
  self.check('settings','edit')
  allowed={'business_name','tax_id','country','currency','receipt_footer','address','telephone','locale'}
  if not set(data)<=allowed:raise ERPError('Parámetros no reconocidos.')
  if 'currency' in data:
   from .currency import valid_currency
   if not valid_currency(data['currency']):raise ERPError('Código de moneda no admitido.')
  if 'country' in data:
   from .currency import COUNTRIES
   if data['country'] not in COUNTRIES:raise ERPError('País no admitido.')
  with self.tx():
   for k,v in data.items():self.con.execute('INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(k,str(v)))
   self._audit('settings.save','settings','general',data)
 def backup(self,destination):
  self.check('settings','edit')
  dest=Path(destination).expanduser().resolve()
  if dest==self.db_path:raise ERPError('El respaldo debe guardarse en otra ruta.')
  dest.parent.mkdir(parents=True,exist_ok=True)
  with closing(sqlite3.connect(str(dest))) as backup_con: self.con.backup(backup_con)
  with self.tx():self._audit('backup.create','settings','database',{'file':dest.name})
  return dest
 def backup_bundle(self,destination):
  self.check('settings','edit')
  dest=Path(destination).expanduser().resolve()
  if dest.suffix.lower()!='.zip':dest=dest.with_suffix('.zip')
  dest.parent.mkdir(parents=True,exist_ok=True)
  with tempfile.TemporaryDirectory() as temp:
   snapshot=Path(temp)/'nexomerc.sqlite3'
   with closing(sqlite3.connect(str(snapshot))) as copied:self.con.backup(copied)
   check=sqlite3.connect(str(snapshot))
   try:
    if check.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ERPError('La copia no superó el control de integridad.')
   finally:check.close()
   tmpzip=dest.parent/(dest.name+'.partial')
   try:
    with zipfile.ZipFile(tmpzip,'w',compression=zipfile.ZIP_DEFLATED) as archive:
     archive.write(snapshot,'nexomerc.sqlite3')
     for p in (self.root/'photos').iterdir():
      if p.is_file():archive.write(p,'photos/'+p.name)
     archive.writestr('backup_manifest.json',json.dumps({'product':'NexoMerc ERP','version':'1.0.0-mvp','created_utc':timestamp(),'format':'sqlite+photos','includes_password_hashes':True},indent=2))
    with zipfile.ZipFile(tmpzip) as archive:
     if archive.testzip():raise ERPError('El ZIP generado no superó la verificación CRC.')
    tmpzip.replace(dest)
   finally:tmpzip.unlink(missing_ok=True)
  with self.tx():self._audit('backup.bundle','settings','archive',{'filename':dest.name})
  return dest
 def export_csv(self,rows,file_path):
  self.check('reports','export')
  if not rows:raise ERPError('No existen filas para exportar.')
  with open(file_path,'w',newline='',encoding='utf-8-sig') as f:
   writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)



# NexoMerc F20 — cupones locales con canje atómico y auditoría.
# No valida ni autoriza promociones bancarias externas.
import secrets as _coupon_secrets
import re as _coupon_re
from datetime import timedelta as _coupon_timedelta

SCHEMA += '''
CREATE TABLE IF NOT EXISTS coupon_rules(
 id INTEGER PRIMARY KEY, name TEXT NOT NULL, threshold_cents INTEGER NOT NULL CHECK(threshold_cents>0),
 award_cents INTEGER NOT NULL CHECK(award_cents>0), branch_id INTEGER REFERENCES branches(id),
 valid_days INTEGER NOT NULL DEFAULT 30 CHECK(valid_days BETWEEN 1 AND 365),
 active INTEGER NOT NULL DEFAULT 1 CHECK(active IN(0,1)), created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS coupon_issues(
 id INTEGER PRIMARY KEY, code TEXT NOT NULL UNIQUE, rule_id INTEGER REFERENCES coupon_rules(id),
 customer_id INTEGER NOT NULL REFERENCES customers(id), amount_cents INTEGER NOT NULL CHECK(amount_cents>0),
 issued_at TEXT NOT NULL, expires_on TEXT NOT NULL, issued_sale_id INTEGER REFERENCES sales(id),
 redeemed_sale_id INTEGER REFERENCES sales(id), voided INTEGER NOT NULL DEFAULT 0 CHECK(voided IN(0,1)));
CREATE UNIQUE INDEX IF NOT EXISTS idx_coupon_issues_one_reward ON coupon_issues(issued_sale_id) WHERE issued_sale_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_coupon_issues_one_redeem ON coupon_issues(redeemed_sale_id) WHERE redeemed_sale_id IS NOT NULL;
CREATE TABLE IF NOT EXISTS sale_discounts(
 sale_id INTEGER PRIMARY KEY REFERENCES sales(id), coupon_issue_id INTEGER NOT NULL UNIQUE REFERENCES coupon_issues(id),
 amount_cents INTEGER NOT NULL CHECK(amount_cents>0));
CREATE INDEX IF NOT EXISTS idx_coupon_customers ON coupon_issues(customer_id,expires_on);
'''

TABLES.update({'coupon_rules','coupon_issues','sale_discounts'})

_f20_original_init=ERP.__init__
def _f20_init(self,*args,**kwargs):
 _f20_original_init(self,*args,**kwargs)
 # Executescript is idempotent and retained in F20 SCHEMA above.
 self.con.executescript('''CREATE TABLE IF NOT EXISTS coupon_rules(id INTEGER PRIMARY KEY,name TEXT NOT NULL,threshold_cents INTEGER NOT NULL CHECK(threshold_cents>0),award_cents INTEGER NOT NULL CHECK(award_cents>0),branch_id INTEGER REFERENCES branches(id),valid_days INTEGER NOT NULL DEFAULT 30 CHECK(valid_days BETWEEN 1 AND 365),active INTEGER NOT NULL DEFAULT 1 CHECK(active IN(0,1)),created_at TEXT NOT NULL);
 CREATE TABLE IF NOT EXISTS coupon_issues(id INTEGER PRIMARY KEY,code TEXT NOT NULL UNIQUE,rule_id INTEGER REFERENCES coupon_rules(id),customer_id INTEGER NOT NULL REFERENCES customers(id),amount_cents INTEGER NOT NULL CHECK(amount_cents>0),issued_at TEXT NOT NULL,expires_on TEXT NOT NULL,issued_sale_id INTEGER REFERENCES sales(id),redeemed_sale_id INTEGER REFERENCES sales(id),voided INTEGER NOT NULL DEFAULT 0 CHECK(voided IN(0,1)));
 CREATE UNIQUE INDEX IF NOT EXISTS idx_coupon_issues_one_reward ON coupon_issues(issued_sale_id) WHERE issued_sale_id IS NOT NULL;
 CREATE UNIQUE INDEX IF NOT EXISTS idx_coupon_issues_one_redeem ON coupon_issues(redeemed_sale_id) WHERE redeemed_sale_id IS NOT NULL;
 CREATE TABLE IF NOT EXISTS sale_discounts(sale_id INTEGER PRIMARY KEY REFERENCES sales(id),coupon_issue_id INTEGER NOT NULL UNIQUE REFERENCES coupon_issues(id),amount_cents INTEGER NOT NULL CHECK(amount_cents>0));
 CREATE INDEX IF NOT EXISTS idx_coupon_customers ON coupon_issues(customer_id,expires_on);''')

def _f20_rule_create(self,name,threshold,award,branch=None,days=30):
 self.check('promotions','create',branch)
 threshold_c=cents(threshold); award_c=cents(award)
 if not str(name).strip() or threshold_c<=0 or award_c<=0:raise ERPError('Ingresá nombre, mínimo y beneficio mayores que cero.')
 if award_c>threshold_c:raise ERPError('El beneficio debe ser menor o igual que el monto mínimo de compra.')
 days=int(days)
 if days<1 or days>365:raise ERPError('La vigencia debe estar entre 1 y 365 días.')
 if branch:self._branch(branch)
 with self.tx():
  cur=self.con.execute('INSERT INTO coupon_rules(name,threshold_cents,award_cents,branch_id,valid_days,created_at) VALUES(?,?,?,?,?,?)',(str(name).strip(),threshold_c,award_c,branch,days,timestamp()))
  rid=cur.lastrowid;self._audit('coupon.rule_create','coupon_rules',rid,{'minimum_cents':threshold_c,'award_cents':award_c})
 return rid

def _f20_rule_toggle(self,rid,active):
 r=self.entity('coupon_rules',rid);self.check('promotions','edit',r.get('branch_id'))
 with self.tx():
  self.con.execute('UPDATE coupon_rules SET active=? WHERE id=?',(int(bool(active)),rid))
  self._audit('coupon.rule_toggle','coupon_rules',rid,{'active':bool(active)})

def _f20_issue_coupon_in_tx(self,customer_id,award_cents,rule_id=None,issued_sale_id=None,days=30):
 today=datetime.now(timezone.utc).date()
 for _ in range(8):
  code='NXM-'+_coupon_secrets.token_hex(5).upper()
  try:
   cur=self.con.execute('INSERT INTO coupon_issues(code,rule_id,customer_id,amount_cents,issued_at,expires_on,issued_sale_id) VALUES(?,?,?,?,?,?,?)',
    (code,rule_id,customer_id,int(award_cents),timestamp(),(today+_coupon_timedelta(days=int(days))).isoformat(),issued_sale_id))
   cid=cur.lastrowid
   self._audit('coupon.issue','coupon_issues',cid,{'rule_id':rule_id,'customer_id':customer_id,'amount_cents':int(award_cents),'issued_sale':issued_sale_id})
   return code
  except sqlite3.IntegrityError as exc:
   if 'coupon_issues.code' not in str(exc):raise
 raise ERPError('No se pudo generar un código único para el cupón.')

def _f20_issue_coupon(self,customer_id,amount,days=30):
 self.check('promotions','create')
 customer=self.entity('customers',customer_id)
 if not customer['active']:raise ERPError('El cliente está inactivo.')
 amount_c=cents(amount)
 if amount_c<=0:raise ERPError('El monto del cupón debe ser positivo.')
 if amount_c>10000000:raise ERPError('El monto del cupón supera el límite administrativo de $100.000.')
 days=int(days)
 if not 1<=days<=365:raise ERPError('Vigencia inválida.')
 with self.tx():return _f20_issue_coupon_in_tx(self,customer_id,amount_c,days=days)

def _f20_coupon_preview(self,code,customer_id,branch,total_cents):
 self.check('pos','sell',branch)
 code=str(code or '').strip().upper()
 if not _coupon_re.fullmatch(r'[A-Z0-9-]{6,32}',code):raise ERPError('Código de cupón inválido.')
 if not customer_id:raise ERPError('Seleccioná el cliente titular del cupón antes de aplicarlo.')
 coupon=self.one('''SELECT c.*,r.branch_id AS restricted_branch FROM coupon_issues c
 LEFT JOIN coupon_rules r ON r.id=c.rule_id WHERE c.code=?''',(code,))
 if not coupon:raise ERPError('Cupón inexistente.')
 if coupon['customer_id']!=int(customer_id):raise ERPError('El cupón pertenece a otro cliente.')
 if coupon['redeemed_sale_id'] is not None or coupon['voided']:raise ERPError('El cupón ya fue utilizado o fue anulado.')
 if coupon['expires_on']<datetime.now(timezone.utc).date().isoformat():raise ERPError('El cupón está vencido.')
 if coupon['restricted_branch'] is not None and coupon['restricted_branch']!=branch:raise ERPError('El cupón no corresponde a esta sucursal.')
 if total_cents<=0:raise ERPError('No se puede aplicar un cupón a un carrito vacío.')
 return {'id':coupon['id'],'code':coupon['code'],'amount_cents':min(coupon['amount_cents'],int(total_cents)),'face_value_cents':coupon['amount_cents']}

def _f20_checkout(self,branch,items,payment,customer_id=None,coupon_code=None):
 self.check('pos','sell',branch);self._branch(branch)
 if payment not in ('cash','debit','credit','transfer','qr','check'):raise ERPError('Medio de pago no reconocido.')
 if not items:raise ERPError('El carrito está vacío.')
 if len({int(i['product_id']) for i in items})!=len(items):raise ERPError('Carrito con productos duplicados.')
 if customer_id:
  customer=self.entity('customers',customer_id)
  if not customer['active']:raise ERPError('Cliente inactivo.')
 with self.tx():
  sess=self.cash_session(branch)
  if not sess:raise ERPError('Abrí caja antes de vender.')
  lines=[]
  for item in items:
   p=self._product(item['product_id']);q=milli(item['qty']);balance=self._balance(p['id'],branch)
   if balance['onhand_milli']-balance['reserved_milli']<q:raise ERPError('Stock insuficiente para '+p['name'])
   price=self.effective_price(p['id'],branch)
   lines.append((p,q,price,total_for(q,price)))
  subtotal=sum(total_for(q,p['price_cents']) for p,q,price,line in lines)
  after_promos=sum(line for p,q,price,line in lines)
  coupon=_f20_coupon_preview(self,coupon_code,customer_id,branch,after_promos) if str(coupon_code or '').strip() else None
  coupon_discount=coupon['amount_cents'] if coupon else 0
  total=after_promos-coupon_discount
  cur=self.con.execute('INSERT INTO sales(branch_id,session_id,user_id,customer_id,created_at,payment,subtotal_cents,total_cents) VALUES(?,?,?,?,?,?,?,?)',
    (branch,sess['id'],self.actor,customer_id,timestamp(),payment,subtotal,total))
  sid=cur.lastrowid
  for p,q,price,line in lines:
   self.con.execute('INSERT INTO sale_lines(sale_id,product_id,qty_milli,base_cents,unit_cents,cost_cents,line_cents) VALUES(?,?,?,?,?,?,?)',
    (sid,p['id'],q,p['price_cents'],price,p['cost_cents'],line))
   self._stock_move(p['id'],branch,-q,'sale',sid)
  if coupon:
   cursor=self.con.execute('UPDATE coupon_issues SET redeemed_sale_id=? WHERE id=? AND redeemed_sale_id IS NULL AND voided=0', (sid,coupon['id']))
   if cursor.rowcount!=1:raise ERPError('El cupón ya fue usado en otra caja.')
   self.con.execute('INSERT INTO sale_discounts(sale_id,coupon_issue_id,amount_cents) VALUES(?,?,?)',(sid,coupon['id'],coupon_discount))
   self._audit('coupon.redeem','coupon_issues',coupon['id'],{'sale_id':sid,'discount_cents':coupon_discount})
  if customer_id:
   self.con.execute('UPDATE customers SET points=points+? WHERE id=?',(total//10000,customer_id))
   # Sólo un cupón por venta; elegir la campaña vigente de mayor valor.
   rules=self.all('''SELECT * FROM coupon_rules WHERE active=1 AND (branch_id IS NULL OR branch_id=?)
      AND threshold_cents<=? ORDER BY award_cents DESC,id LIMIT 1''',(branch,total))
   if rules:
    rule=rules[0]
    _f20_issue_coupon_in_tx(self,customer_id,rule['award_cents'],rule['id'],sid,rule['valid_days'])
  self._audit('sale.checkout','sales',sid,{'total_cents':total,'branch':branch,'payment':payment,'lines':len(lines),'coupon_discount_cents':coupon_discount})
 return sid

_f20_original_void=ERP.void_sale
def _f20_void_sale(self,sid,reason):
 sale=self.entity('sales',sid);self.check('pos','void',sale['branch_id'])
 with self.tx():
  if self.one('SELECT id FROM coupon_issues WHERE issued_sale_id=? AND redeemed_sale_id IS NOT NULL',(sid,)):
   raise ERPError('La venta generó un cupón ya utilizado. Requiere reversión administrativa supervisada.')
  _f20_original_void(self,sid,reason)
  # No anular cupones si la venta no se anuló realmente.
  self.con.execute('UPDATE coupon_issues SET voided=1 WHERE issued_sale_id=? AND redeemed_sale_id IS NULL',(sid,))
  self.con.execute('UPDATE coupon_issues SET redeemed_sale_id=NULL WHERE redeemed_sale_id=?',(sid,))
  self._audit('coupon.sale_void','sales',sid,{'reason':'void-reconcile'})

_f20_original_ticket=ERP.sale_ticket
def _f20_sale_ticket(self,sid):
 text=_f20_original_ticket(self,sid)
 disc=self.one('SELECT d.amount_cents,c.code FROM sale_discounts d JOIN coupon_issues c ON c.id=d.coupon_issue_id WHERE d.sale_id=?',(sid,))
 reward=self.one('SELECT code,amount_cents,expires_on FROM coupon_issues WHERE issued_sale_id=? AND voided=0',(sid,))
 if disc:
  text+='\nDESCUENTO CUPÓN '+disc['code']+': -'+money(disc['amount_cents'])
 if reward:
  text+='\nCUPÓN OBTENIDO: '+reward['code']+' | VALOR: '+money(reward['amount_cents'])+' | VENCE: '+reward['expires_on']
 text+='\nLos cupones son internos. No suponen validación bancaria ni comprobante fiscal.'
 return text

ERP.__init__=_f20_init
ERP.create_coupon_rule=_f20_rule_create
ERP.set_coupon_rule_active=_f20_rule_toggle
ERP.issue_coupon=_f20_issue_coupon
ERP.coupon_preview=_f20_coupon_preview
ERP.checkout=_f20_checkout
ERP.void_sale=_f20_void_sale
ERP.sale_ticket=_f20_sale_ticket
