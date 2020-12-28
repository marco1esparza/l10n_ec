# Part of Odoo. See LICENSE file for full copyright and licensing details.


def update_mail_template(cr):
    cr.execute("UPDATE mail_template SET subject=%s, report_name=%s WHERE name=%s", ("${object.company_id.name} (${not object.l10n_latam_document_type_id and 'Invoice' or object.l10n_latam_document_type_id.report_name or object.l10n_latam_document_type_id.name}  ${object.name or 'n/a'})", "${(object.name or '').replace('/','_')}${object.state == 'draft' and '_draft' or ''}", "Invoice: Send by email"))
    cr.commit()

def migrate(cr, version):
    update_mail_template(cr)
