# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openupgradelib import openupgrade

#TODO: Migration scripts to run on databases not comming from Trescloud
def update_vat_withhold_base_percent(env):
    # For vat withhold taxes, replace factor_percent=12% with factor_percent=100%
    all_companies = env['res.company'].search([])
    ecuadorian_companies = all_companies.filtered(lambda r: r.country_code == 'EC')
    ecuadorian_taxes = env['account.tax'].search([('company_id', 'in', ecuadorian_companies.ids)])
    taxes_to_fix = ecuadorian_taxes.filtered(lambda x: x.tax_group_id.l10n_ec_type in ['withhold_vat_sale', 'withhold_vat_purchase'])
    env.cr.execute('''
        --for invoice_tax_id
        UPDATE account_tax_repartition_line
        SET factor_percent=100 
        WHERE factor_percent=12 
        AND repartition_type='tax'
        AND invoice_tax_id in %s
        ''', [tuple(taxes_to_fix.ids)])
    env.cr.execute('''
        --for refund_tax_id
        UPDATE account_tax_repartition_line
        SET factor_percent=100 
        WHERE factor_percent=12 
        AND repartition_type='tax'
        AND refund_tax_id in %s
        ''', [tuple(taxes_to_fix.ids)])

def recompute_invoice_names(env):
    #recomputes invoice name, as new l10n_latam_document_number prefixes has been provided in latam document type master data
    all_companies = env['res.company'].search([])
    ecuadorian_companies = all_companies.filtered(lambda r: r.country_code == 'EC')
    env.cr.execute('''
        --split name by space, then concatenate code prefix with last element of name
        UPDATE account_move
        SET name = CONCAT(doc.doc_code_prefix,' ',REVERSE(SPLIT_PART(REVERSE(account_move.name), ' ', 1)))
        FROM account_move am
        LEFT JOIN l10n_latam_document_type doc on doc.id = am.l10n_latam_document_type_id
        WHERE am.l10n_latam_document_type_id IS NOT NULL
        AND am.state IN ('posted','cancel')
        AND am.id = account_move.id
        AND am.company_id in %s
        ''', [tuple(ecuadorian_companies.ids)])
    
@openupgrade.logging()
def create_tax_343(env):
    '''
    Creando el impuesto 343
    '''
    companies = env['res.company'].search([])
    for company in companies:
        tax343A = env['account.tax'].search([('l10n_ec_code_ats','=','343A'), ('company_id', '=', company.id)])
        if tax343A:
            tax = tax343A.copy()
            tax.name = 'Otras Retenciones Aplicables el 1%'
            tax.description = 'Otras 1%'
            tax.l10n_ec_code_base = 343
            tax.l10n_ec_code_applied = 393
            tax.l10n_ec_code_ats = 343

@openupgrade.migrate(use_env=True)
def migrate(env, version):
    create_tax_343(env)