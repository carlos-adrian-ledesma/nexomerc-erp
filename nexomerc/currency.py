"""Display currency preferences; never performs FX conversion.

Amounts in NexoMerc are recorded as integer hundredths regardless of currency.
Changing display currency doesn't modify or exchange historical amounts.
"""
from __future__ import annotations

COUNTRIES={
 'AR':('Argentina','ARS'), 'BR':('Brasil','BRL'), 'US':('Estados Unidos','USD'),
 'JP':('日本 (Japón)','JPY'), 'PH':('Pilipinas (Filipinas)','PHP'),
 'VN':('Việt Nam','VND'), 'CN':('中国 (China)','CNY'),
 'CL':('Chile','CLP'), 'UY':('Uruguay','UYU'), 'PY':('Paraguay','PYG'),
 'BO':('Bolivia','BOB'), 'PE':('Perú','PEN'), 'CO':('Colombia','COP'),
 'MX':('México','MXN'), 'ES':('España','EUR'), 'PT':('Portugal','EUR'),
 'GB':('United Kingdom','GBP'), 'CA':('Canada','CAD'), 'AU':('Australia','AUD'),
}
CURRENCY_NAMES={
 'ARS':'ARS · Peso argentino ($)', 'BRL':'BRL · Real brasileño (R$)',
 'USD':'USD · Dólar estadounidense (US$)', 'JPY':'JPY · Yen japonés (¥)',
 'PHP':'PHP · Peso filipino (₱)', 'VND':'VND · Đồng vietnamita (₫)',
 'CNY':'CNY · Yuan chino (¥)', 'CLP':'CLP · Peso chileno',
 'UYU':'UYU · Peso uruguayo', 'PYG':'PYG · Guaraní paraguayo',
 'BOB':'BOB · Boliviano', 'PEN':'PEN · Sol peruano',
 'COP':'COP · Peso colombiano', 'MXN':'MXN · Peso mexicano',
 'EUR':'EUR · Euro (€)', 'GBP':'GBP · Libra (£)',
 'CAD':'CAD · Dólar canadiense', 'AUD':'AUD · Dólar australiano',
}

def for_country(country):
 return COUNTRIES.get(country, COUNTRIES['AR'])[1]

def valid_currency(code):
 return str(code).upper() in CURRENCY_NAMES

def price_label(number,code='ARS'):
 return f'{code} {number}'
