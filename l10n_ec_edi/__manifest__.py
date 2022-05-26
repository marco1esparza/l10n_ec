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

        "views/root_sri_menu.xml",
        "views/account_move_views.xml",
        "views/l10n_ec_edi_certificate_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "auto_install": True,
    "application": False,
    "external_dependencies": {"python": ["pyOpenSSL", "lxml"]},
}
