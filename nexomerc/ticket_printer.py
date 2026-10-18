"""Non-fiscal ticket preview + Windows spooler printer selection.

Printer support is through the OS driver and QtPrintSupport. This is NOT
an ARCA-approved fiscal ticket / invoice generator and not ESC/POS-native.
"""
from __future__ import annotations
import html
from PySide6.QtCore import QSizeF, QMarginsF
from PySide6.QtGui import QPageSize, QPageLayout, QFont, QTextDocument
from PySide6.QtPrintSupport import QPrinter, QPrinterInfo
from PySide6.QtWidgets import (
 QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
 QPushButton, QTextEdit, QMessageBox, QDialogButtonBox)


def ticket_markup(text):
 """Use escaped plain data from the authorized ERP.sale_ticket sale query."""
 return ("<html><body style='font-family:Consolas,monospace;font-size:9pt;'>"
         "<pre style='white-space:pre-wrap;'>"+html.escape(text,quote=True)+"</pre></body></html>")


class TicketPrinterDialog(QDialog):
 def __init__(self,parent,text):
  super().__init__(parent)
  self.setWindowTitle('Impresión de ticket · NexoMerc ERP')
  self.setMinimumSize(530,510)
  self.raw_text=text
  layout=QVBoxLayout(self)
  title=QLabel('Imprimir ticket · Comprobante interno NO fiscal')
  title.setObjectName('heading');layout.addWidget(title)
  explanation=QLabel('Elegí una impresora instalada en Windows. Para ticketera térmica, '
                     'instalá primero el controlador del fabricante y seleccioná 58 u 80 mm. '
                     'El sistema no controla cortador ni cajón sin un driver compatible.')
  explanation.setWordWrap(True);layout.addWidget(explanation)
  options=QHBoxLayout()
  options.addWidget(QLabel('Impresora'))
  self.device=QComboBox()
  printers=QPrinterInfo.availablePrinters()
  for printer in printers:self.device.addItem(printer.printerName())
  default=QPrinterInfo.defaultPrinter().printerName()
  if default:
   i=self.device.findText(default)
   if i>=0:self.device.setCurrentIndex(i)
  options.addWidget(self.device,1)
  options.addWidget(QLabel('Papel'))
  self.width=QComboBox();self.width.addItem('80 mm',80);self.width.addItem('58 mm',58);options.addWidget(self.width)
  layout.addLayout(options)
  preview=QTextEdit();preview.setReadOnly(True);preview.setPlainText(text)
  preview.setFont(QFont('Consolas',10));layout.addWidget(preview,1)
  self.state=QLabel('Vista previa del comprobante. Imprimí solo luego de seleccionar la venta correcta.')
  self.state.setWordWrap(True);layout.addWidget(self.state)
  footer=QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
  self.print_button=QPushButton('Imprimir ticket')
  self.print_button.setObjectName('primary');self.print_button.setEnabled(bool(printers))
  self.print_button.clicked.connect(self.print_ticket)
  footer.addButton(self.print_button,QDialogButtonBox.ButtonRole.ActionRole)
  footer.rejected.connect(self.reject);layout.addWidget(footer)
  if not printers:self.state.setText('No se detectaron impresoras instaladas. Conectá la ticketera e instalá su controlador de Windows.')
 def print_ticket(self):
  name=self.device.currentText()
  if not name:return
  try:
   info=next((x for x in QPrinterInfo.availablePrinters() if x.printerName()==name),None)
   if info is None:raise RuntimeError('La impresora ya no está disponible.')
   printer=QPrinter(info,QPrinter.PrinterMode.HighResolution)
   if not printer.isValid():raise RuntimeError('Windows informa que la impresora no es válida.')
   width=self.width.currentData()
   # Size is adjusted to the content to avoid unnecessary blank roll paper.
   height=min(1200,max(100,30+len(self.raw_text.splitlines())*4.8))
   printer.setPageSize(QPageSize(QSizeF(float(width),float(height)),QPageSize.Unit.Millimeter))
   printer.setPageMargins(QMarginsF(2.5,3,2.5,3),QPageLayout.Unit.Millimeter)
   doc=QTextDocument()
   doc.setDefaultFont(QFont('Consolas',9 if width==80 else 8))
   doc.setHtml(ticket_markup(self.raw_text))
   # Qt submits to the configured Windows print driver/spooler.
   doc.print_(printer)
   self.state.setText('Documento enviado al controlador de impresión. Confirmá la salida física en la ticketera.')
   QMessageBox.information(self,'Ticket enviado','El documento se envió al controlador de la impresora. Verificá que la ticketera lo haya impreso correctamente.')
   self.accept()
  except Exception as exc:
   QMessageBox.warning(self,'No se pudo imprimir',f'La impresión no se completó: {exc}\nVerificá el controlador, la conexión y el tamaño del papel.')
