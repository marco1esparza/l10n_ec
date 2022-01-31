# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Facturas ecuatorianas',
    'version': '1.1',
    'summary': 'SRI electronic documents, invoices, credit notes, debit notes, RIDEs, tributary documents, printer points, etc',
    'category': 'Localization',
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
            Ing. José Miguel Rivero
    ''',
    'author': 'TRESCLOUD',
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
        'data/l10n_ec_sri_printer_point_data.xml',
        'data/l10n_ec_payment_method_data.xml',
        'data/account_edi_format_data.xml',
        'data/l10n_ec_sri_tax_support_data.xml',
        'data/l10n_latam_document_type_data.xml',
        'data/mail_template_data.xml',
        #Security
        'security/ir.model.access.csv',
        'security/l10n_ec_multicompany_security.xml',
        #Views
        'views/l10n_ec_sri_printer_point_view.xml',
        'views/l10n_ec_digital_signature_view.xml',
        'views/l10n_ec_payment_method_view.xml',
        'views/res_company_view.xml',
        'views/account_move_view.xml',
        'views/account_report.xml',
        'views/report_invoice.xml',
        'views/l10n_ec_sri_tax_support_view.xml',
    ],
    'installable': True,
    'auto_install': True,
}
