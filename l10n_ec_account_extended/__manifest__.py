# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Posiciones fiscales ecuatorianas',
    'version': '1.5',
    'category': 'Parametrization',
    'description': '''         
        Característica: 
            Este módulo agrega la lógica para el manejo de posiciones fiscales ecuatorianas, incluyendo los tipos de 
            agentes de retención, las reglas de su pirámide fiscal, así como validaciones en facturas de compra y venta.
        
        Funcionalidad:
            Instalar la posición fiscal adecuada según la configuración seleccionada usando uno de los módulos complementarios.
            Se agrega mensaje de advertencia en las facturas de compra al cambiar la posición fiscal del proveedor. Recomputo 
            automático de impuestos en facturas de compra al cambiar de posición fiscal.
        
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
        #'object_merger',
        'l10n_ec_edi'
    ],   
    'data': [
        #Data
        #wizard
        #Views
        'views/account_fiscal_position_view.xml',        
        'views/res_company_view.xml',
        'views/res_partner_view.xml',
    ],
    'installable': True
}
