# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# import odoo
# from odoo import api, SUPERUSER_ID
# from openupgradelib import openupgrade
# 
# @openupgrade.migrate()
# def migrate(env, version):
#     rename_salary_journal(env)
# 
# @openupgrade.logging()
# def rename_salary_journal(env):
#     companies = env['res.company'].search([])
#     for company in companies:
#         salary_journal = env['account.journal'].search([
#                 ('code', '=', 'SALAR'),
#                 ('company_id', '=', company.id)])
#         salary_journal.write({
#             'name': 'Rol de Pagos',
#             'code': 'ROLDP',
#             })
    