# -*- encoding: utf-8 -*-
from odoo import models, fields
import time, base64


class base_file_report(models.TransientModel):
    """Modelo en memoria para almacenar temporalmente los archivos generados al cargar un reporte.
    Todos los asistentes que generen un archivo (xls, xml, etc.) deben devolver la función show()"""
    _name = 'base.file.report'

    file = fields.Binary('Archivo generado', readonly=True, required=True)

    filename = fields.Char('Archivo generado', required=True)

    def show(self, file, filename):
        file_report = self.env['base.file.report'].create({'file':file,'filename':filename})

        return {
            'name': filename + time.strftime(' (%Y-%m-%d %H:%M:%S)'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': self._name,
            'res_id': file_report.id,
            'target': 'new',
        }