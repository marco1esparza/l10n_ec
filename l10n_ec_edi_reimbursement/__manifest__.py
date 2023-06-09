# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Reembolsos de Gastos como cliente para Ecuador según la normativa del SRI',
    'version': '1.0',
    'category': 'Ecuadorian Regulations',
    'description': '''
        Característica: 
            Permite manejar los reembolsos de gastos como cliente según esta establecido por el SRI.
            
        Funcionalidades:
            Agrega el control necesario en facturas de proveedor para ingresar las facturas de 
            compra entregadas por el intermediario por concepto de reembolso de gastos como cliente 
            y registrarlas en un formulario especial para incluirlas posteriormente en el ATS.
        
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
        'l10n_ec_edi'
    ],
    'data': [
        #Data
        'data/product_data.xml', 
        #Security
        'security/ir.model.access.csv',
        #Views
        'views/res_company_view.xml',
        'views/account_move_view.xml'
    ],
    'installable': True,
    'auto_install': False,
    'post_init_hook': '_post_install_hook_l10n_ec_setup_reimbursement_product',
    
}
