# Author: Damien Crier
# Author: Julien Coux
# Copyright 2016 Camptocamp SA
# Copyright 2020 ForgeFlow S.L. (https://www.forgeflow.com)
# Copyright 2021 Tecnativa - João Marques
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Informes Financieros Excel",
    "version": "14.0.1.0.0",
    "category": "Reporting",
    "summary": "Informes Financieros Excel",
    "author": "Trescloud Cia. Ltda, "
    "Camptocamp SA,"
    "initOS GmbH,"
    "redCOR AG,"
    "ForgeFlow,"
    "Odoo Community Association (OCA)",
    "website": "http://www.trescloud.com",
    "depends": ["account", "date_range", "report_xlsx"],
    "data": [
        "security/ir.model.access.csv",
        "wizard/aged_partner_balance_wizard_view.xml",
        "wizard/general_ledger_wizard_view.xml",
        "wizard/journal_ledger_wizard_view.xml",
        "wizard/open_items_wizard_view.xml",
        "wizard/trial_balance_wizard_view.xml",
        "wizard/vat_report_wizard_view.xml",
        "wizard/wizard_report_balance_general.xml",
        "wizard/wizard_report_balance_resultados.xml",
        "wizard/wizard_report_balance_comprobacion.xml",
        "menuitems.xml",
        "reports.xml",
        "report/templates/layouts.xml",
        "report/templates/aged_partner_balance.xml",
        "report/templates/general_ledger.xml",
        "report/templates/journal_ledger.xml",
        "report/templates/open_items.xml",
        "report/templates/trial_balance.xml",
        "report/templates/vat_report.xml",
        "view/account_view.xml",
        "view/report_template.xml",
        "view/report_general_ledger.xml",
        "view/report_journal_ledger.xml",
        "view/report_trial_balance.xml",
        "view/report_open_items.xml",
        "view/report_aged_partner_balance.xml",
        "view/report_vat_report.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
    "license": "AGPL-3",
    "support": "soporte@trescloud.com",
    "price": 200,
    "currency": "USD",
    'images': [
        'static/description/icon.png'
    ],
    'assets': {
        'web.assets_backend': [
            'trescloud_financial_reports/static/src/js/account_financial_report_backend.js',
            'trescloud_financial_reports/static/src/js/account_financial_report_widgets.js',
        ],
    }
}
