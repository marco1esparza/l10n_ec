# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Facturas ecuatorianas',
    'version': '1.0',
    'category': 'Ecuadorian Regulations',
    'description': '''
        Característica: 
            Aplica reglas específicas de la facturación en Ecuador.
            
        Funcionalidades:
            Agrega campos, restricciones y bloques constructivos básicos, en lo referente a facturas y puntos de emisión
            para la tributación Ecuatoriana. Este módulo permite almacenar los datos de las facturas creadas de tal forma que
            si cambia un dato del cliente en el futuro los documentos históricos generados hasta dicha fecha se mantenga los 
            datos previos al cambio, estos datos deben incluir: Nombre, Dirección, RUC y teléfono.
        
        Autores:
            Ing. Andres Calle
            Ing. Patricio Rangles
            Ing. José Miguel Rivero
            Ing. Santiago Orozco        
    ''',
    'author': 'TRESCLOUD CIA LTDA',
    'maintainer': 'TRESCLOUD CIA. LTDA.',
    'website': 'http://www.trescloud.com',
    'license': 'OEEL-1',
    'depends': [
        'base',
        'l10n_ec',
        'account_edi'
    ],    
    'data': [
        #Data
        'data/printer_point_data.xml',
        'data/payment_method_data.xml',
        'data/account_edi_format_data.xml',
        #Security
       'security/ir.model.access.csv',
        #Views
        'views/printer_point_view.xml',
        'views/res_users_view.xml',
        'views/payment_method_view.xml',
        'views/account_move_view.xml'
    ],
    'installable': True
}
