# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (http://tiny.be). All Rights Reserved
#
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License # -*- encoding: utf-8 -*-for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see http://www.gnu.org/licenses/.
#
##############################################################################
from odoo import models
from xlwt import easyxf
from datetime import datetime

class base_file_report(models.TransientModel):
    """
    Modelo en memoria para almacenar temporalmente los archivos generados al cargar un reporte.
    Todos los asistentes que generen un archivo (xls, xml, etc.) deben devolver la función show()
    """
    _name = 'xls.tools'

def cm2width(cm):
    ref = 65535/50.12
    return int(round(cm*ref))

def get_style(bold=False, font_name='Calibri', height=12, font_color='black',
              rotation=0, align='center', vertical='center', wrap=True,
              border=True, color=None, format=None):
    str_style = ''
    if bold or font_name or height or font_color:
        str_style += 'font: '
        str_style += bold and ('bold %s, '%bold) or ''
        str_style += font_name and ('name %s, '%font_name) or ''
        str_style += height and ('height %s, '%(height*20)) or ''
        str_style += font_color and ('color %s, '%font_color) or ''
        str_style = str_style[:-2] + ';'
    if rotation or align or vertical or wrap:
        str_style += 'alignment: '
        str_style += rotation and ('rotation %s, '%rotation) or ''
        str_style += align and ('horizontal %s, '%align) or ''
        str_style += vertical and ('vertical %s, '%vertical) or ''
        str_style += wrap and ('wrap %s, '%wrap) or ''
        str_style = str_style[:-2] + ';'
    str_style += border and 'border: left thin, right thin, top thin, bottom thin;' or ''
    str_style += color and 'pattern: pattern solid, fore_colour %s;'%color or ''
    return easyxf(str_style, num_format_str = format)

def GET_LETTER(index):
    COLUMNS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    aux = int(index / len(COLUMNS))
    aux2 = index - (aux * len(COLUMNS))
    return (aux and COLUMNS[aux-1] or '') + COLUMNS[aux2]

def get_excel_datas(model, sheet, CUSTOM_FIELDS={}):
    res, fields, fields_unknowed, errors = [], [], [], u''
    NO_FIELDS = ['create_uid', 'display_name', '__last_update', 'write_uid', 'write_date', 'create_date', 'id']
    NO_TYPES = ['binary', 'one2many', 'many2many', 'reference']
    model_fields = model.fields_get(); model_fields.update(CUSTOM_FIELDS)
    model_fields = [aux for aux in model_fields.iteritems() if aux[0] not in NO_FIELDS and aux[1]['type'] not in NO_TYPES]
    for col, cell in enumerate(sheet.row_slice(0)):
        if not cell.value or cell.ctype != 1: continue
        aux = None
        for ind, (model_field, field_info) in enumerate(model_fields):
            if cell.value.upper() in (model_field.upper(), field_info['string'].upper()):
                aux = (col, model_field, field_info)
                break
        if aux: fields.append(aux)
        else: fields_unknowed.append(cell.value)
    if fields:
        for row in range(1, sheet.nrows):
            vals = {}
            for col, field, field_info in fields:
                cell, vals[field] = sheet.cell(row, col), None
                if field_info['type'] == 'boolean':
                    if cell.ctype not in (2, 4, 0, 6):
                        errors += u'<li><b>En la fila "%s",</b> el valor <b>"%s"</b> no está permitido para el campo <b>"%s"</b>. Debe ser VERDADERO o FALSO.' % (row+1, cell.value, field_info['string'])
                    else: vals[field] = bool(cell.value)
                elif cell.ctype in (0, 5, 6): continue
                elif field_info['type'] == 'selection':
                    SEL = dict([(val.upper(), key) for key, val in field_info['selection']])
                    if cell.ctype != 1 or not SEL.has_key(cell.value.upper()):
                        errors += u'<li><b>En la fila "%s",</b> el valor <b>"%s"</b> no está permitido para el campo <b>"%s"</b>. Los valores posibles son: %s' % (row+1, cell.value, field_info['string'], ', '.join(SEL.keys()))
                    else: vals[field] = SEL[cell.value.upper()]
                elif field_info['type'] in ('char', 'html', 'many2one', 'text'):
                    if cell.ctype != 1:
                        errors += u'<li><b>En la fila "%s",</b> el valor <b>"%s"</b> no está permitido para el campo <b>"%s"</b>. Solamente puede ingresar texto.' % (row+1, cell.value, field_info['string'])
                    elif field_info['type'] == 'many2one':
                        aux_model = model.env[field_info['relation']]
                        aux = aux_model.name_search(name=cell.value, args=field_info.get('domain', []))
                        if len(aux) > 1: errors += u'<li><b>En la fila "%s",</b> el valor <b>"%s"</b> para el campo <b>"%s"</b> se ha encontrado más de una vez en el modelo <b>"%s"</b>. Se cargará el primer valor encontrado <b>"%s"</b>.' % (row+1, cell.value, field_info['string'], aux_model._description, aux[0][1])
                        vals[field] = aux[0][0] if aux else cell.value
                    else: vals[field] = cell.value
                elif field_info['type'] in ('datetime', 'date'):
                    if cell.ctype not in (2, 3):
                        errors += u'<li><b>En la fila "%s",</b> el valor <b>"%s"</b> no está permitido para el campo <b>"%s"</b>. Cambie al formato de fecha en el mismo excel.' % (row+1, cell.value, field_info['string'])
                    else: vals[field] = datetime.utcfromtimestamp((cell.value - 25569) * 86400.0)
                elif field_info['type'] in ('float', 'integer'):
                    if cell.ctype != 2:
                        errors += u'<li><b>En la fila "%s",</b> el valor <b>"%s"</b> no está permitido para el campo <b>"%s"</b>. Solamente ingrese números.' % (row+1, cell.value, field_info['string'])
                    else: vals[field] = cell.value
                else: assert False
            res.append(vals)
    return fields_unknowed, errors, res
