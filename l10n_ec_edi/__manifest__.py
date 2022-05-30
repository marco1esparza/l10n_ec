# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Ecuadorian Accounting EDI",
    "version": "15.0",
    "description": """
    Ecuadorian Accounting EDI
    """,
    "author": "Stanislas Gueniffey",
    "category": "Accounting/Localizations/Account Charts",
    "maintainer": "Josse Colpaert <jco@odoo.com>",
    "license": "LGPL-3",
    "depends": [
        "account_edi",
        "l10n_ec",
    ],
    "data": [
        "data/templates/edi_document.xml",
        "data/templates/edi_authorization.xml",
        "data/templates/edi_signature.xml",

        "data/account.edi.format.csv",

        "security/ir.model.access.csv",
        "security/l10n_ec_multicompany_security.xml",

        "views/root_sri_menu.xml",
        "views/account_journal_view.xml",
        "views/account_move_views.xml",
        "views/contributor_type_view.xml",
        "views/l10n_ec_edi_certificate_views.xml",
        "views/product_view.xml",
        "views/report_invoice.xml",
        "views/res_config_settings_views.xml",
        "views/res_partner_view.xml",        
        #Wizard
        'wizard/wizard_account_withhold_view.xml',

    ],
    "installable": True,
    "auto_install": True,
    "application": False,
    'post_init_hook': '_post_install_hook_configure_ecuadorian_withhold',
    "external_dependencies": {"python": ["pyOpenSSL", "lxml"]},
}
