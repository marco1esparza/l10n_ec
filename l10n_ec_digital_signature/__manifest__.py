# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Firma Electronica del SRI basado en JAVA para Documentos electrónicos',
    'version': '1.0',
    'category': 'Ecuadorian Regulations',
    'description': '''            
        Característica: 
            Este modulo agrega la logica necesaria de la firma electronica requerida por el SRI, 
            esta basado en el codigo publicado en https://github.com/joselo/sri 
            
        Funcionalidad:
            Permite integrar la firma digital requerida por el SRI entre las funcionalidades de Documentos Electronicos
            mediante la libreria JAVA publicada
            
        Autor:
            - Ing. Patricio Rangles
        
        Agradecimiento especial a Jose Carrion (joseloc@gmail.com) pues el presente modulo hace uso de la libreria DevelopedSignature.java desarrollada por él

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
