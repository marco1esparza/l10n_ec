# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'SRI XAdES Digital Signature',
    'version': '1.0',
    'category': 'Ecuadorian Regulations',
    'description': '''            
        Característica: 
            Este modulo agrega la logica necesaria de la firma electronica requerida por el SRI. 
            
        Funcionalidad:
            Permite integrar la firma digital requerida por el SRI basada en el estandar XAdES
    ''',
    'author': 'TRESCLOUD CIA LTDA',
    'maintainer': 'TRESCLOUD CIA. LTDA.',
    'website': 'http://www.trescloud.com',
    'license': 'OEEL-1',
    'depends': [
        'base',
        'l10n_ec_edi',
    ],    
    'data': [
    ],
    'installable': True
}
