# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Retenciones ecuatorianas',
    'version': '1.0',
    'category': 'Localization',
    'summary': 'SRI electronic withholds, sales withholds, etc',
    'description': '''
        Característica:
            Agrega las características básicas para la emisión de Retenciones en ventas y compras.
            
        Funcionalidad:
            Registro de retenciones en facturas de clientes emitidas por los clientes. Generación de
            retenciones para facturas de proveedores, impresión, eliminación y anulación de retenciones.
        
    ''',
    'author': 'TRESCLOUD',
    'maintainer': 'TRESCLOUD CIA. LTDA.',
    'website': 'http://www.trescloud.com',
    'license': 'OEEL-1',
    'depends': [
        'base',
        'l10n_ec_edi',
    ],
    'data': [
        #Data
        #Security
        'security/ir.model.access.csv',
        #Views
        'views/account_move_view.xml',
        'views/account_journal_view.xml',
        'views/product_view.xml',
        'views/report_invoice.xml',
        'views/res_company_view.xml',
        'views/res_config_settings_views.xml',
        'views/contributor_type_view.xml',
    ],
    'installable': True,
    'auto_install': True,
    'post_init_hook': '_post_install_hook_configure_ecuadorian_withhold',
}
