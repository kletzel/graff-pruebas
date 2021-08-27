# -*- coding: utf-8 -*-

import requests
import json
import io
import os
import glob
import base64
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT
from datetime import datetime, timedelta
from odoo import fields, models, exceptions, api, _


class DateRangeOccupantMovementReportWizard(models.TransientModel):
    _name = 'date.range.occupant.movement.report.wizard'

    date_start = fields.Date(string="Fecha Inicial", required=True, default=fields.Date.today)
    date_end = fields.Date(string="Fecha Final", required=True, default=fields.Date.today)
    indiviso_m2o = fields.Many2one('avb3.vaiindiviso', 'Indiviso', index=True)
    indiviso_id = fields.Integer('Indiviso ID', size=2, readonly=True)
    global_indiviso_include = fields.Boolean('Indiviso global')
    partner_type = fields.Selection([("Ocupante", "Ocupante"), ("Propietario", "Propietario"), ("Ambos", "Ambos")], string="Tipo", required=True,)
    
    @api.onchange('indiviso_m2o')
    def onchange_indiviso_m2o(self):
        indiviso_m2o = self.indiviso_m2o
        if indiviso_m2o:
            self.indiviso_id = indiviso_m2o.id
        
    @api.multi
    def get_report(self):
        """Call when button 'Get Report' clicked.
        """
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'date_start': self.date_start,
                'date_end': self.date_end,
                'indiviso_m2o' : self.indiviso_m2o,
                'indiviso_id' : self.indiviso_m2o.id,
                'global_indiviso_include' : self.global_indiviso_include,
                'partner_type' : self.partner_type,
            },
        }

        # use `module_name.report_id` as reference.
        # `report_action()` will call `get_report_values()` and pass `data` automatically.
        return self.env.ref('date_range_occupant_movement_report.date_range_occupant_movement_report').report_action(self, data=data)


class ReportDateRangeOccupantMovement(models.AbstractModel):
    """Abstract Model for report template.

    for `_name` model, please use `report.` as prefix then add `module_name.report_name`.
    """

    _name = 'report.date_range_occupant_movement_report.dromr_view'

    @api.model
    def _get_report_values(self, docids, data=None):
        date_start = data['form']['date_start']
        date_end = data['form']['date_end']
        indiviso_ids = data['form']['indiviso_id']
        global_indiviso_includes = data['form']['global_indiviso_include']
        partner_types = data['form']['partner_type']
        date_start_obj = datetime.strptime(date_start, DATE_FORMAT)
        date_end_obj = datetime.strptime(date_end, DATE_FORMAT)
        if len(str(date_start_obj.day)) == 1:
            day = "0" + str(date_start_obj.day)
        else:
            day = str(date_start_obj.day)

        if len(str(date_start_obj.month)) == 1:
            month = "0" + str(date_start_obj.month)
        else:
            month = str(date_start_obj.month)

        date_starts = day + "/" + month + "/" + str(date_start_obj.year)

        if len(str(date_end_obj.day)) == 1:
            day = "0" + str(date_end_obj.day)
        else:
            day = str(date_end_obj.day)

        if len(str(date_end_obj.month)) == 1:
            month = "0" + str(date_end_obj.month)
        else:
            month = str(date_end_obj.month)

        date_ends = day + "/" + month + "/" + str(date_end_obj.year)
        current_company_id = self.env.user.company_id.id;

        self._cr.execute("""DROP TABLE IF EXISTS occupant_movement_invoices_payments""")
        self._cr.execute("select distinct rp.id rp_id, rp.name rp_name, ai.id ai_id, ai.number ai_number, ai.factcte_indiviso ai_indiviso, ai.company_id ai_company_id, ap.id ap_id, ap.name ap_name, ap.payment_date ap_payment_date from account_payment ap inner join account_invoice_payment_rel aipr on ap.id = aipr.payment_id inner join account_invoice ai on aipr.invoice_id = ai.id inner join res_partner rp on ap.partner_id = rp.id where ap.payment_date <= '{}' and not ap.state = 'cancelled' and not ap.state = 'draft' and ap.payment_type = 'inbound' and rp.customer = 't' and not ai.state = 'cancel' and not ai.state = 'draft' and ai.type = 'out_invoice' and (ai.factcte_receptor = '1' or ai.factcte_receptor = '2') and ai.company_id = {} order by rp.id, rp.name, ai.id, ai.number, ai.factcte_indiviso, ai.company_id, ap.id, ap.name, ap.payment_date".format(date_end, current_company_id))
        result = self._cr.fetchall()

        if self._cr.rowcount:
            count = self._cr.rowcount
            results_json = ''
            self._cr.execute("""CREATE TABLE occupant_movement_invoices_payments (rp_id int, rp_name varchar(250), ai_id int, ai_number varchar(250), ai_indiviso varchar(250), ai_company_id int, ap_id int, ap_name varchar(250), ap_payment_date date, amount float)""")
            for i in range(0, len(result)):
                rp_id = result[i][0]
                rp_name = result[i][1]
                ai_id = result[i][2]
                ai_number = result[i][3]
                ai_indiviso = result[i][4]
                ai_company_id = result[i][5]
                ap_id = result[i][6]
                ap_name = result[i][7]
                ap_payment_date = result[i][8]

                payments_widget = self.env['account.invoice'].search([
                    ('id', '=', ai_id),
                    ('company_id', '=', ai_company_id),
                ]).payments_widget

                if payments_widget:
                    json_payments_widgets = json.loads(payments_widget)
                    if json_payments_widgets:
                        try:
                            json_payments = json_payments_widgets.get('content') or []
                            for json_payment in json_payments:
                                account_payment_id = json_payment['account_payment_id']
                                if ap_id == account_payment_id:
                                    amount = json_payment['amount']
                                    results_json = results_json + 'account_payment_id: %s, amount: %s | '%(account_payment_id, amount)
                                    self._cr.execute("""INSERT INTO occupant_movement_invoices_payments (rp_id, rp_name, ai_id, ai_number, ai_indiviso, ai_company_id, ap_id, ap_name, ap_payment_date, amount) values ({}, '{}', {}, '{}', {}, {}, {}, '{}', '{}', {})""".format(rp_id, rp_name, ai_id, ai_number, ai_indiviso, ai_company_id, ap_id, ap_name, ap_payment_date, amount))
                        except Exception as e:
                            raise Warning('ai_number: %s'%(ai_number))
        else:
            self._cr.execute("""CREATE TABLE occupant_movement_invoices_payments (rp_id int, rp_name varchar(250), ai_id int, ai_number varchar(250), ai_indiviso varchar(250), ai_company_id int, ap_id int, ap_name varchar(250), ap_payment_date date, amount float)""")
            self._cr.execute("""INSERT INTO occupant_movement_invoices_payments (rp_id, rp_name, ai_id, ai_number, ai_indiviso, ai_company_id, ap_id, ap_name, ap_payment_date, amount) values (-1, '-1', -1, '-1', -1, -1, -1, '-1', null, -1)""")

        if partner_types == 'Ocupante':
            if global_indiviso_includes:
                indiviso_ids = ''
                indiviso_names = 'Indiviso Global'
                    
                query = "select * from (select rps.display_name rp_name, CASE WHEN sa.sum_sa is null THEN 0 ELSE sa.sum_sa END sum_sa, CASE WHEN i.sum_i is null THEN 0 ELSE i.sum_i END sum_i, CASE WHEN a.sum_a is null THEN 0 ELSE a.sum_a END sum_a, CASE WHEN sa.sum_sa is null THEN 0 ELSE sa.sum_sa END + CASE WHEN i.sum_i is null THEN 0 ELSE i.sum_i END - CASE WHEN a.sum_a is null THEN 0 ELSE a.sum_a END sum_s, u.agg_u from (select ocup_nombre from (select distinct ocup_nombre from avb3_vaiunidad where company_id = {}) props union (select distinct p.bitocup_id ocup_nombre from avb3_vaiunidad u inner join avb3_vaibitocup p on u.id = cast(p.unidadprivid as integer) where u.company_id = {})) uni inner join res_partner rps on uni.ocup_nombre = rps.id left join (select case when sa1.rp_id is null then sa2.rp_id else sa1.rp_id end rp_id, case when sa1.rp_name is null then sa2.rp_name else sa1.rp_name end rp_name, case when sa1.sum_sa is null then 0 else sa1.sum_sa end - case when sa2.sum_sa is null then 0 else sa2.sum_sa end sum_sa from (select rp_id, rp_name, sum_sa from (select case when ai.rp_id is null then aicn.rp_id else ai.rp_id end rp_id, case when ai.rp_name is null then aicn.rp_name else ai.rp_name end rp_name, case when ai.amount_total is null then 0 else ai.amount_total end + case when aicn.amount_total is null then 0 else aicn.amount_total end sum_sa from (select rp.id rp_id, rp.name rp_name, sum(case when ai.amount_total is null then 0 else ai.amount_total end) amount_total from res_partner rp inner join account_invoice ai on rp.id = ai.partner_id and rp.customer = 't' and ai.type = 'out_invoice' and not ai.state = 'cancel' and not ai.state = 'draft' and ai.factcte_receptor = '1' and ai.company_id = {} and ai.date_invoice < %s group by rp_id, rp_name order by rp_id) ai left outer join (select rp.id rp_id, rp.name rp_name, sum(case when aicn.amount_total_signed is null then 0 else aicn.amount_total_signed end) amount_total from res_partner rp inner join account_invoice aicn on rp.id = aicn.partner_id and rp.customer = 't' and aicn.type = 'out_refund' and not aicn.state = 'cancel' and not aicn.state = 'draft' and aicn.factcte_receptor = '1' and aicn.company_id = {} and aicn.date_invoice < %s group by rp_id, rp_name order by rp_id) aicn on ai.rp_id = aicn.rp_id) aiaicn order by rp_id) sa1 full outer join (select pre_sa2.rp_id rp_id, pre_sa2.rp_name rp_name, sum(pre_sa2.sum_sa) sum_sa from (select distinct rp.id rp_id, rp.name rp_name, ap.id ap_id, case when aml.debit is null then 0 else aml.debit end sum_sa from res_partner rp inner join account_invoice ai on rp.id = ai.partner_id and rp.customer = 't' and not ai.state = 'cancel' and not ai.state = 'draft' and ai.type = 'out_invoice' and ai.factcte_receptor = '1' and ai.company_id = {} inner join account_invoice_payment_rel aipr on ai.id = aipr.invoice_id inner join account_payment ap on aipr.payment_id = ap.id and ap.payment_date < %s and not ap.state = 'cancelled' and not ap.state = 'draft' inner join account_move_line aml on ap.id = aml.payment_id order by rp_id) pre_sa2 group by rp_id, rp_name order by rp_id) sa2 on sa1.rp_id = sa2.rp_id) sa on uni.ocup_nombre = sa.rp_id left join (select rp_id, rp_name, sum_i from (select case when ai.rp_id is null then aicn.rp_id else ai.rp_id end rp_id, case when ai.rp_name is null then aicn.rp_name else ai.rp_name end rp_name, case when ai.amount_total is null then 0 else ai.amount_total end + case when aicn.amount_total is null then 0 else aicn.amount_total end sum_i from (select rp.id rp_id, rp.name rp_name, sum(case when ai.amount_total is null then 0 else ai.amount_total end) amount_total from res_partner rp inner join account_invoice ai on rp.id = ai.partner_id and rp.customer = 't' and ai.type = 'out_invoice' and not ai.state = 'cancel' and not ai.state = 'draft' and ai.factcte_receptor = '1' and ai.company_id = {} and ai.date_invoice >= %s and ai.date_invoice <= %s group by rp_id, rp_name order by rp_id) ai left outer join (select rp.id rp_id, rp.name rp_name, sum(case when aicn.amount_total_signed is null then 0 else aicn.amount_total_signed end) amount_total from res_partner rp inner join account_invoice aicn on rp.id = aicn.partner_id and rp.customer = 't' and aicn.type = 'out_refund' and not aicn.state = 'cancel' and not aicn.state = 'draft' and aicn.factcte_receptor = '1' and aicn.company_id = {} and aicn.date_invoice >= %s and aicn.date_invoice <= %s group by rp_id, rp_name order by rp_id) aicn on ai.rp_id = aicn.rp_id) aiaicn order by rp_id) i on uni.ocup_nombre = i.rp_id left join (select pre_a.rp_id rp_id, pre_a.rp_name rp_name, sum(pre_a.sum_a) sum_a from (select distinct rp.id rp_id, rp.name rp_name, ap.id ap_id, case when aml.debit is null then 0 else aml.debit end sum_a from res_partner rp inner join account_invoice ai on rp.id = ai.partner_id and rp.customer = 't' and not ai.state = 'cancel' and not ai.state = 'draft' and ai.type = 'out_invoice' and ai.factcte_receptor = '1' and ai.company_id = {} inner join account_invoice_payment_rel aipr on ai.id = aipr.invoice_id inner join account_payment ap on aipr.payment_id = ap.id and ap.payment_date >= %s and ap.payment_date <= %s and not ap.state = 'cancelled' and not ap.state = 'draft' inner join account_move_line aml on ap.id = aml.payment_id order by rp_id) pre_a group by rp_id, rp_name order by rp_id) a on uni.ocup_nombre = a.rp_id left join (select undds.rp_id rp_id, string_agg(distinct(undds.u_name), ',' order by undds.u_name) agg_u from (select distinct(u_id, u_name, rp_id), u_id, u_name, rp_id from (select ocups.* from (select * from (select avb3u.id u_id, avb3u.name u_name, avb3u.ocup_nombre rp_id from avb3_vaiunidad avb3u where avb3u.company_id = {} order by avb3u.id) ocups union (select distinct u.id u_id, u.name u_name, p.bitocup_id rp_id from avb3_vaiunidad u inner join avb3_vaibitocup p on u.id = cast(p.unidadprivid as integer) where u.company_id = {})) ocups left join (select u_id, u_name, rp_id from (select distinct(avb3vpup.pago_unidadprivid, avb3vpup.pago_unidadpriv, ai.partner_id), avb3vpup.pago_unidadprivid u_id, avb3vpup.pago_unidadpriv u_name, ai.partner_id rp_id, rp.name rp_name from avb3_vaipagunidpriv avb3vpup inner join account_invoice ai on avb3vpup.pago_idfac = ai.id inner join res_partner rp on ai.partner_id = rp.id where ai.factcte_receptor = '1' and ai.company_id = {} and avb3vpup.company_id = {} order by avb3vpup.pago_unidadprivid) uavb3vpup) invs on ocups.u_id = invs.u_id and ocups.rp_id = invs.rp_id) unid) undds group by undds.rp_id order by agg_u) u on uni.ocup_nombre = u.rp_id) as finaliio order by agg_u"
                    
                self._cr.execute(query.format(current_company_id, current_company_id, current_company_id, current_company_id, current_company_id, current_company_id, current_company_id, current_company_id, current_company_id, current_company_id, current_company_id, current_company_id), (date_start, date_start, date_start, date_start, date_end, date_start, date_end, date_start, date_end))
                result = self._cr.dictfetchall()

                count = self.env.cr.rowcount
                print("*************************************************DATOS*****************************************************",count)
                
                docs = []
                for row in result:
                    docs.append({
                        'partnername': row.get('rp_name'),
                        'sumsa': row.get('sum_sa'),
                        'sumi': row.get('sum_i'),
                        'suma': row.get('sum_a'),
                        'sums': row.get('sum_s'),
                        'aggu': row.get('agg_u'),
                    })
            else:
                if not global_indiviso_includes and indiviso_ids:
                    self.env.cr.execute("select name from avb3_vaiindiviso where id = {} and company_id = {}".format(indiviso_ids, current_company_id))
                    indiviso_names = self.env.cr.fetchone()[0]

                    query = "select * from (select rps.display_name rp_name, CASE WHEN sa.sum_sa is null THEN 0 ELSE sa.sum_sa END sum_sa, CASE WHEN i.sum_i is null THEN 0 ELSE i.sum_i END sum_i, CASE WHEN a.sum_a is null THEN 0 ELSE a.sum_a END sum_a, CASE WHEN sa.sum_sa is null THEN 0 ELSE sa.sum_sa END + CASE WHEN i.sum_i is null THEN 0 ELSE i.sum_i END - CASE WHEN a.sum_a is null THEN 0 ELSE a.sum_a END sum_s, u.agg_u from (select ocup_nombre from (select distinct ocup_nombre from avb3_vaiunidad where company_id = {}) props union(select distinct p.bitocup_id ocup_nombre from avb3_vaiunidad u inner join avb3_vaibitocup p on u.id = cast(p.unidadprivid as integer) where u.company_id = {})) uni inner join res_partner rps on uni.ocup_nombre = rps.id left join (select case when sa1.rp_id is null then sa2.rp_id else sa1.rp_id end rp_id, case when sa1.rp_name is null then sa2.rp_name else sa1.rp_name end rp_name, case when sa1.sum_sa is null then 0 else sa1.sum_sa end - case when sa2.sum_sa is null then 0 else sa2.sum_sa end sum_sa from (select rp_id, rp_name, sum_sa from (select case when ai.rp_id is null then aicn.rp_id else ai.rp_id end rp_id, case when ai.rp_name is null then aicn.rp_name else ai.rp_name end rp_name, case when ai.amount_total is null then 0 else ai.amount_total end + case when aicn.amount_total is null then 0 else aicn.amount_total end sum_sa from (select rp.id rp_id, rp.name rp_name, sum(case when ai.amount_total is null then 0 else ai.amount_total end) amount_total from res_partner rp inner join account_invoice ai on rp.id = ai.partner_id and rp.customer = 't' and ai.type = 'out_invoice' and not ai.state = 'cancel' and not ai.state = 'draft' and ai.factcte_receptor = '1' and ai.company_id = {} and ai.factcte_indiviso = {} and ai.date_invoice < %s group by rp_id, rp_name order by rp_id) ai left outer join (select rp.id rp_id, rp.name rp_name, sum(case when aicn.amount_total_signed is null then 0 else aicn.amount_total_signed end) amount_total from res_partner rp inner join account_invoice aicn on rp.id = aicn.partner_id and rp.customer = 't' and aicn.type = 'out_refund' and not aicn.state = 'cancel' and not aicn.state = 'draft' and aicn.factcte_receptor = '1' and aicn.company_id = {} and aicn.factcte_indiviso = {} and aicn.date_invoice < %s group by rp_id, rp_name order by rp_id) aicn on ai.rp_id = aicn.rp_id) aiaicn order by rp_id) sa1 full outer join (select pre_sa2.rp_id rp_id, pre_sa2.rp_name rp_name, sum(pre_sa2.sum_sa) sum_sa from (select distinct rp.id rp_id, rp.name rp_name, ap.id ap_id, case when aml.debit is null then 0 else aml.debit end sum_sa from res_partner rp inner join account_invoice ai on rp.id = ai.partner_id and rp.customer = 't' and not ai.state = 'cancel' and not ai.state = 'draft' and ai.type = 'out_invoice' and ai.factcte_receptor = '1' and ai.company_id = {} and ai.factcte_indiviso = {} inner join account_invoice_payment_rel aipr on ai.id = aipr.invoice_id inner join account_payment ap on aipr.payment_id = ap.id and ap.payment_date < %s and not ap.state = 'cancelled' and not ap.state = 'draft' inner join account_move_line aml on ap.id = aml.payment_id order by rp_id) pre_sa2 group by rp_id, rp_name order by rp_id) sa2 on sa1.rp_id = sa2.rp_id) sa on uni.ocup_nombre = sa.rp_id left join (select rp_id, rp_name, sum_i from (select case when ai.rp_id is null then aicn.rp_id else ai.rp_id end rp_id, case when ai.rp_name is null then aicn.rp_name else ai.rp_name end rp_name, case when ai.amount_total is null then 0 else ai.amount_total end + case when aicn.amount_total is null then 0 else aicn.amount_total end sum_i from (select rp.id rp_id, rp.name rp_name, sum(case when ai.amount_total is null then 0 else ai.amount_total end) amount_total from res_partner rp inner join account_invoice ai on rp.id = ai.partner_id and rp.customer = 't' and ai.type = 'out_invoice' and not ai.state = 'cancel' and not ai.state = 'draft' and ai.factcte_receptor = '1' and ai.company_id = {} and ai.factcte_indiviso = {} and ai.date_invoice >= %s and ai.date_invoice <= %s group by rp_id, rp_name order by rp_id) ai left outer join (select rp.id rp_id, rp.name rp_name, sum(case when aicn.amount_total_signed is null then 0 else aicn.amount_total_signed end) amount_total from res_partner rp inner join account_invoice aicn on rp.id = aicn.partner_id and rp.customer = 't' and aicn.type = 'out_refund' and not aicn.state = 'cancel' and not aicn.state = 'draft' and aicn.factcte_receptor = '1' and aicn.company_id = {} and aicn.factcte_indiviso = {} and aicn.date_invoice >= %s and aicn.date_invoice <= %s group by rp_id, rp_name order by rp_id) aicn on ai.rp_id = aicn.rp_id) aiaicn order by rp_id) i on uni.ocup_nombre = i.rp_id left join (select pre_a.rp_id rp_id, pre_a.rp_name rp_name, sum(pre_a.sum_a) sum_a from (select distinct rp.id rp_id, rp.name rp_name, ap.id ap_id, case when aml.debit is null then 0 else aml.debit end sum_a from res_partner rp inner join account_invoice ai on rp.id = ai.partner_id and rp.customer = 't' and not ai.state = 'cancel' and not ai.state = 'draft' and ai.type = 'out_invoice' and ai.factcte_receptor = '1' and ai.company_id = {} and ai.factcte_indiviso = {} inner join account_invoice_payment_rel aipr on ai.id = aipr.invoice_id inner join account_payment ap on aipr.payment_id = ap.id and ap.payment_date >= %s and ap.payment_date <= %s and not ap.state = 'cancelled' and not ap.state = 'draft' inner join account_move_line aml on ap.id = aml.payment_id order by rp_id) pre_a group by rp_id, rp_name order by rp_id) a on uni.ocup_nombre = a.rp_id left join (select undds.rp_id rp_id, string_agg(distinct(undds.u_name), ',' order by undds.u_name) agg_u from (select distinct(u_id, u_name, rp_id), u_id, u_name, rp_id from (select ocups.* from (select * from (select avb3u.id u_id, avb3u.name u_name, avb3u.ocup_nombre rp_id from avb3_vaiunidad avb3u where avb3u.company_id = {} order by avb3u.id) ocups union (select distinct u.id u_id, u.name u_name, p.bitocup_id rp_id from avb3_vaiunidad u inner join avb3_vaibitocup p on u.id = cast(p.unidadprivid as integer) where u.company_id = {})) ocups left join (select u_id, u_name, rp_id from (select distinct(avb3vpup.pago_unidadprivid, avb3vpup.pago_unidadpriv, ai.partner_id), avb3vpup.pago_unidadprivid u_id, avb3vpup.pago_unidadpriv u_name, ai.partner_id rp_id, rp.name rp_name from avb3_vaipagunidpriv avb3vpup inner join account_invoice ai on avb3vpup.pago_idfac = ai.id inner join res_partner rp on ai.partner_id = rp.id where ai.factcte_receptor = '1' and ai.company_id = {} and avb3vpup.company_id = {} order by avb3vpup.pago_unidadprivid) uavb3vpup) invs on ocups.u_id = invs.u_id and ocups.rp_id = invs.rp_id) unid) undds group by undds.rp_id order by agg_u) u on uni.ocup_nombre = u.rp_id) as finaliio order by agg_u"
                    
                    self._cr.execute(query.format(current_company_id, current_company_id, current_company_id, indiviso_ids, current_company_id, indiviso_ids, current_company_id, indiviso_ids, current_company_id, indiviso_ids, current_company_id, indiviso_ids, current_company_id, indiviso_ids, current_company_id, current_company_id, current_company_id, current_company_id), (date_start, date_start, date_start, date_start, date_end, date_start, date_end, date_start, date_end))
                    result = self._cr.dictfetchall()

                    count = self.env.cr.rowcount
                    print("*************************************************DATOS*****************************************************",count)

                    docs = []
                    for row in result:
                        docs.append({
                            'partnername': row.get('rp_name'),
                            'sumsa': row.get('sum_sa'),
                            'sumi': row.get('sum_i'),
                            'suma': row.get('sum_a'),
                            'sums': row.get('sum_s'),
                            'aggu': row.get('agg_u'),
                        })
                else:
                    indiviso_ids = ''
                    indiviso_names = ''
                    docs = []
                    docs.append({
                        'partnername': '',
                        'sumsa': 0,
                        'sumi': 0,
                        'suma': 0,
                        'sums': 0,
                        'aggu': '',
                    })
        if partner_types == 'Propietario':
            if global_indiviso_includes:
                indiviso_ids = ''
                indiviso_names = 'Indiviso Global'
                    
                query = "select * from (select rps.display_name rp_name, CASE WHEN sa.sum_sa is null THEN 0 ELSE sa.sum_sa END sum_sa, CASE WHEN i.sum_i is null THEN 0 ELSE i.sum_i END sum_i, CASE WHEN a.sum_a is null THEN 0 ELSE a.sum_a END sum_a, CASE WHEN sa.sum_sa is null THEN 0 ELSE sa.sum_sa END + CASE WHEN i.sum_i is null THEN 0 ELSE i.sum_i END - CASE WHEN a.sum_a is null THEN 0 ELSE a.sum_a END sum_s, u.agg_u from (select prop_nombre from (select distinct prop_nombre from avb3_vaiunidad where company_id = {}) props union (select distinct p.bitprop_id prop_nombre from avb3_vaiunidad u inner join avb3_vaibitprop p on u.id = cast(p.unidadprivid as integer) where u.company_id = {})) uni inner join res_partner rps on uni.prop_nombre = rps.id left join (select case when sa1.rp_id is null then sa2.rp_id else sa1.rp_id end rp_id, case when sa1.rp_name is null then sa2.rp_name else sa1.rp_name end rp_name, Case when sa1.sum_sa is null then 0 else sa1.sum_sa end - case when sa2.sum_sa is null then 0 else sa2.sum_sa end sum_sa from (select rp_id, rp_name, sum_sa from (select case when ai.rp_id is null then aicn.rp_id else ai.rp_id end rp_id, case when ai.rp_name is null then aicn.rp_name else ai.rp_name end rp_name, case when ai.amount_total is null then 0 else ai.amount_total end + case when aicn.amount_total is null then 0 else aicn.amount_total end sum_sa from (select rp.id rp_id, rp.name rp_name, sum(case when ai.amount_total is null then 0 else ai.amount_total end) amount_total from res_partner rp inner join account_invoice ai on rp.id = ai.partner_id and rp.customer = 't' and ai.type = 'out_invoice' and not ai.state = 'cancel' and not ai.state = 'draft' and ai.factcte_receptor = '2' and ai.company_id = {} and ai.date_invoice < %s group by rp_id, rp_name order by rp_id) ai left outer join (select rp.id rp_id, rp.name rp_name, sum(case when aicn.amount_total_signed is null then 0 else aicn.amount_total_signed end) amount_total from res_partner rp inner join account_invoice aicn on rp.id = aicn.partner_id and rp.customer = 't' and aicn.type = 'out_refund' and not aicn.state = 'cancel' and not aicn.state = 'draft' and aicn.factcte_receptor = '2' and aicn.company_id = {} and aicn.date_invoice < %s group by rp_id, rp_name order by rp_id) aicn on ai.rp_id = aicn.rp_id) aiaicn order by rp_id) sa1 full outer join (select pre_sa2.rp_id rp_id, pre_sa2.rp_name rp_name, sum(pre_sa2.sum_sa) sum_sa from (select distinct rp.id rp_id, rp.name rp_name, ap.id ap_id, case when aml.debit is null then 0 else aml.debit end sum_sa from res_partner rp inner join account_invoice ai on rp.id = ai.partner_id and rp.customer = 't' and not ai.state = 'cancel' and not ai.state = 'draft' and ai.type = 'out_invoice' and ai.factcte_receptor = '2' and ai.company_id = {} inner join account_invoice_payment_rel aipr on ai.id = aipr.invoice_id inner join account_payment ap on aipr.payment_id = ap.id and ap.payment_date < %s and not ap.state = 'cancelled' and not ap.state = 'draft' inner join account_move_line aml on ap.id = aml.payment_id order by rp_id) pre_sa2 group by rp_id, rp_name order by rp_id) sa2 on sa1.rp_id = sa2.rp_id) sa on uni.prop_nombre = sa.rp_id left join (select rp_id, rp_name, sum_i from (select case when ai.rp_id is null then aicn.rp_id else ai.rp_id end rp_id, case when ai.rp_name is null then aicn.rp_name else ai.rp_name end rp_name, case when ai.amount_total is null then 0 else ai.amount_total end + case when aicn.amount_total is null then 0 else aicn.amount_total end sum_i from (select rp.id rp_id, rp.name rp_name, sum(case when ai.amount_total is null then 0 else ai.amount_total end) amount_total from res_partner rp inner join account_invoice ai on rp.id = ai.partner_id and rp.customer = 't' and ai.type = 'out_invoice' and not ai.state = 'cancel' and not ai.state = 'draft' and ai.factcte_receptor = '2' and ai.company_id = {} and ai.date_invoice >= %s and ai.date_invoice <= %s group by rp_id, rp_name order by rp_id) ai left outer join (select rp.id rp_id, rp.name rp_name, sum(case when aicn.amount_total_signed is null then 0 else aicn.amount_total_signed end) amount_total from res_partner rp inner join account_invoice aicn on rp.id = aicn.partner_id and rp.customer = 't' and aicn.type = 'out_refund' and not aicn.state = 'cancel' and not aicn.state = 'draft' and aicn.factcte_receptor = '2' and aicn.company_id = {} and aicn.date_invoice >= %s and aicn.date_invoice <= %s group by rp_id, rp_name order by rp_id) aicn on ai.rp_id = aicn.rp_id) aiaicn order by rp_id) i on uni.prop_nombre = i.rp_id left join (select pre_a.rp_id rp_id, pre_a.rp_name rp_name, sum(pre_a.sum_a) sum_a from (select distinct rp.id rp_id, rp.name rp_name, ap.id ap_id, case when aml.debit is null then 0 else aml.debit end sum_a from res_partner rp inner join account_invoice ai on rp.id = ai.partner_id and rp.customer = 't' and not ai.state = 'cancel' and not ai.state = 'draft' and ai.type = 'out_invoice' and ai.factcte_receptor = '2' and ai.company_id = {} inner join account_invoice_payment_rel aipr on ai.id = aipr.invoice_id inner join account_payment ap on aipr.payment_id = ap.id and ap.payment_date >= %s and ap.payment_date <= %s and not ap.state = 'cancelled' and not ap.state = 'draft' inner join account_move_line aml on ap.id = aml.payment_id order by rp_id) pre_a group by rp_id, rp_name order by rp_id) a on uni.prop_nombre = a.rp_id left join (select undds.rp_id rp_id, string_agg(distinct(undds.u_name), ',' order by undds.u_name) agg_u from (select distinct(u_id, u_name, rp_id), u_id, u_name, rp_id from (select ocups.* from (select * from (select avb3u.id u_id, avb3u.name u_name, avb3u.prop_nombre rp_id from avb3_vaiunidad avb3u where avb3u.company_id = {} order by avb3u.id) ocups union (select distinct u.id u_id, u.name u_name, p.bitprop_id rp_id from avb3_vaiunidad u inner join avb3_vaibitprop p on u.id = cast(p.unidadprivid as integer) where u.company_id = {})) ocups left join (select u_id, u_name, rp_id from (select distinct(avb3vpup.pago_unidadprivid, avb3vpup.pago_unidadpriv, ai.partner_id), avb3vpup.pago_unidadprivid u_id, avb3vpup.pago_unidadpriv u_name, ai.partner_id rp_id, rp.name rp_name from avb3_vaipagunidpriv avb3vpup inner join account_invoice ai on avb3vpup.pago_idfac = ai.id inner join res_partner rp on ai.partner_id = rp.id where ai.factcte_receptor = '2' and ai.company_id = {} and avb3vpup.company_id = {} order by avb3vpup.pago_unidadprivid) uavb3vpup) invs on ocups.u_id = invs.u_id and ocups.rp_id = invs.rp_id) unid) undds group by undds.rp_id order by agg_u) u on uni.prop_nombre = u.rp_id) as finaliio order by agg_u"
                    
                self._cr.execute(query.format(current_company_id, current_company_id, current_company_id, current_company_id, current_company_id, current_company_id, current_company_id, current_company_id, current_company_id, current_company_id, current_company_id, current_company_id), (date_start, date_start, date_start, date_start, date_end, date_start, date_end, date_start, date_end))
                result = self._cr.dictfetchall()

                count = self.env.cr.rowcount
                print("*************************************************DATOS*****************************************************",count)
                
                docs = []
                for row in result:
                    docs.append({
                        'partnername': row.get('rp_name'),
                        'sumsa': row.get('sum_sa'),
                        'sumi': row.get('sum_i'),
                        'suma': row.get('sum_a'),
                        'sums': row.get('sum_s'),
                        'aggu': row.get('agg_u'),
                    })
            else:
                if not global_indiviso_includes and indiviso_ids:
                    self.env.cr.execute("select name from avb3_vaiindiviso where id = {} and company_id = {}".format(indiviso_ids, current_company_id))
                    indiviso_names = self.env.cr.fetchone()[0]

                    query = "select * from (select rps.display_name rp_name, CASE WHEN sa.sum_sa is null THEN 0 ELSE sa.sum_sa END sum_sa, CASE WHEN i.sum_i is null THEN 0 ELSE i.sum_i END sum_i, CASE WHEN a.sum_a is null THEN 0 ELSE a.sum_a END sum_a, CASE WHEN sa.sum_sa is null THEN 0 ELSE sa.sum_sa END + CASE WHEN i.sum_i is null THEN 0 ELSE i.sum_i END - CASE WHEN a.sum_a is null THEN 0 ELSE a.sum_a END sum_s, u.agg_u from (select prop_nombre from (select distinct prop_nombre from avb3_vaiunidad where company_id = {}) props union (select distinct p.bitprop_id prop_nombre from avb3_vaiunidad u inner join avb3_vaibitprop p on u.id = cast(p.unidadprivid as integer) where u.company_id = {})) uni inner join res_partner rps on uni.prop_nombre = rps.id left join (select case when sa1.rp_id is null then sa2.rp_id else sa1.rp_id end rp_id, case when sa1.rp_name is null then sa2.rp_name else sa1.rp_name end rp_name, case when sa1.sum_sa is null then 0 else sa1.sum_sa end - case when sa2.sum_sa is null then 0 else sa2.sum_sa end sum_sa from (select rp_id, rp_name, sum_sa from (select case when ai.rp_id is null then aicn.rp_id else ai.rp_id end rp_id, case when ai.rp_name is null then aicn.rp_name else ai.rp_name end rp_name, case when ai.amount_total is null then 0 else ai.amount_total end + case when aicn.amount_total is null then 0 else aicn.amount_total end sum_sa from (select rp.id rp_id, rp.name rp_name, sum(case when ai.amount_total is null then 0 else ai.amount_total end) amount_total from res_partner rp inner join account_invoice ai on rp.id = ai.partner_id and rp.customer = 't' and ai.type = 'out_invoice' and not ai.state = 'cancel' and not ai.state = 'draft' and ai.factcte_receptor = '2' and ai.company_id = {} and ai.factcte_indiviso = {} and ai.date_invoice < %s group by rp_id, rp_name order by rp_id) ai left outer join (select rp.id rp_id, rp.name rp_name, sum(case when aicn.amount_total_signed is null then 0 else aicn.amount_total_signed end) amount_total from res_partner rp inner join account_invoice aicn on rp.id = aicn.partner_id and rp.customer = 't' and aicn.type = 'out_refund' and not aicn.state = 'cancel' and not aicn.state = 'draft' and aicn.factcte_receptor = '2' and aicn.company_id = {} and aicn.factcte_indiviso = {} and aicn.date_invoice < %s group by rp_id, rp_name order by rp_id) aicn on ai.rp_id = aicn.rp_id) aiaicn order by rp_id) sa1 full outer join (select pre_sa2.rp_id rp_id, pre_sa2.rp_name rp_name, sum(pre_sa2.sum_sa) sum_sa from (select distinct rp.id rp_id, rp.name rp_name, ap.id ap_id, case when aml.debit is null then 0 else aml.debit end sum_sa from res_partner rp inner join account_invoice ai on rp.id = ai.partner_id and rp.customer = 't' and not ai.state = 'cancel' and not ai.state = 'draft' and ai.type = 'out_invoice' and ai.factcte_receptor = '2' and ai.company_id = {} and ai.factcte_indiviso = {} inner join account_invoice_payment_rel aipr on ai.id = aipr.invoice_id inner join account_payment ap on aipr.payment_id = ap.id and ap.payment_date < %s and not ap.state = 'cancelled' and not ap.state = 'draft' inner join account_move_line aml on ap.id = aml.payment_id order by rp_id) pre_sa2 group by rp_id, rp_name order by rp_id) sa2 on sa1.rp_id = sa2.rp_id) sa on uni.prop_nombre = sa.rp_id left join (select rp_id, rp_name, sum_i from (select case when ai.rp_id is null then aicn.rp_id else ai.rp_id end rp_id, case when ai.rp_name is null then aicn.rp_name else ai.rp_name end rp_name, case when ai.amount_total is null then 0 else ai.amount_total end + case when aicn.amount_total is null then 0 else aicn.amount_total end sum_i from (select rp.id rp_id, rp.name rp_name, sum(case when ai.amount_total is null then 0 else ai.amount_total end) amount_total from res_partner rp inner join account_invoice ai on rp.id = ai.partner_id and rp.customer = 't' and ai.type = 'out_invoice' and not ai.state = 'cancel' and not ai.state = 'draft' and ai.factcte_receptor = '2' and ai.company_id = {} and ai.factcte_indiviso = {} and ai.date_invoice >= %s and ai.date_invoice <= %s group by rp_id, rp_name order by rp_id) ai left outer join (select rp.id rp_id, rp.name rp_name, sum(case when aicn.amount_total_signed is null then 0 else aicn.amount_total_signed end) amount_total from res_partner rp inner join account_invoice aicn on rp.id = aicn.partner_id and rp.customer = 't' and aicn.type = 'out_refund' and not aicn.state = 'cancel' and not aicn.state = 'draft' and aicn.factcte_receptor = '2' and aicn.company_id = {} and aicn.factcte_indiviso = {} and aicn.date_invoice >= %s and aicn.date_invoice <= %s group by rp_id, rp_name order by rp_id) aicn on ai.rp_id = aicn.rp_id) aiaicn order by rp_id) i on uni.prop_nombre = i.rp_id left join (select pre_a.rp_id rp_id, pre_a.rp_name rp_name, sum(pre_a.sum_a) sum_a from (select distinct rp.id rp_id, rp.name rp_name, ap.id ap_id, case when aml.debit is null then 0 else aml.debit end sum_a from res_partner rp inner join account_invoice ai on rp.id = ai.partner_id and rp.customer = 't' and not ai.state = 'cancel' and not ai.state = 'draft' and ai.type = 'out_invoice' and ai.factcte_receptor = '2' and ai.company_id = {} and ai.factcte_indiviso = {} inner join account_invoice_payment_rel aipr on ai.id = aipr.invoice_id inner join account_payment ap on aipr.payment_id = ap.id and ap.payment_date >= %s and ap.payment_date <= %s and not ap.state = 'cancelled' and not ap.state = 'draft' inner join account_move_line aml on ap.id = aml.payment_id order by rp_id) pre_a group by rp_id, rp_name order by rp_id) a on uni.prop_nombre = a.rp_id left join (select undds.rp_id rp_id, string_agg(distinct(undds.u_name), ',' order by undds.u_name) agg_u from (select distinct(u_id, u_name, rp_id), u_id, u_name, rp_id from (select ocups.* from (select * from (select avb3u.id u_id, avb3u.name u_name, avb3u.prop_nombre rp_id from avb3_vaiunidad avb3u where avb3u.company_id = {} order by avb3u.id) ocups union (select distinct u.id u_id, u.name u_name, p.bitprop_id rp_id from avb3_vaiunidad u inner join avb3_vaibitprop p on u.id = cast(p.unidadprivid as integer) where u.company_id = {})) ocups left join (select u_id, u_name, rp_id from (select distinct(avb3vpup.pago_unidadprivid, avb3vpup.pago_unidadpriv, ai.partner_id), avb3vpup.pago_unidadprivid u_id, avb3vpup.pago_unidadpriv u_name, ai.partner_id rp_id, rp.name rp_name from avb3_vaipagunidpriv avb3vpup inner join account_invoice ai on avb3vpup.pago_idfac = ai.id inner join res_partner rp on ai.partner_id = rp.id where ai.factcte_receptor = '2' and ai.company_id = {} and avb3vpup.company_id = {} order by avb3vpup.pago_unidadprivid) uavb3vpup) invs on ocups.u_id = invs.u_id and ocups.rp_id = invs.rp_id) unid) undds group by undds.rp_id order by agg_u) u on uni.prop_nombre = u.rp_id) as finaliio order by agg_u"
                    
                    self._cr.execute(query.format(current_company_id, current_company_id, current_company_id, indiviso_ids, current_company_id, indiviso_ids, current_company_id, indiviso_ids, current_company_id, indiviso_ids, current_company_id, indiviso_ids, current_company_id, indiviso_ids, current_company_id, current_company_id, current_company_id, current_company_id), (date_start, date_start, date_start, date_start, date_end, date_start, date_end, date_start, date_end))
                    result = self._cr.dictfetchall()

                    count = self.env.cr.rowcount
                    print("*************************************************DATOS*****************************************************",count)

                    docs = []
                    for row in result:
                        docs.append({
                            'partnername': row.get('rp_name'),
                            'sumsa': row.get('sum_sa'),
                            'sumi': row.get('sum_i'),
                            'suma': row.get('sum_a'),
                            'sums': row.get('sum_s'),
                            'aggu': row.get('agg_u'),
                        })
                else:
                    indiviso_ids = ''
                    indiviso_names = ''
                    docs = []
                    docs.append({
                        'partnername': '',
                        'sumsa': 0,
                        'sumi': 0,
                        'suma': 0,
                        'sums': 0,
                        'aggu': '',
                    })
        if partner_types == 'Ambos':
            if global_indiviso_includes:
                indiviso_ids = ''
                indiviso_names = 'Indiviso Global'
                    
                query = "select * from (select rps.display_name rp_name, case when sa.sum_sa is null then 0 else sa.sum_sa end sum_sa, case when i.sum_i is null then 0 else i.sum_i end sum_i, case when a.sum_a is null then 0 else a.sum_a end sum_a, case when sa.sum_sa is null then 0 else sa.sum_sa end + case when i.sum_i is null then 0 else i.sum_i end - case when a.sum_a is null then 0 else a.sum_a end sum_s, case when u.agg_u is null then u_aux.agg_u else u.agg_u end agg_u from (select rp_id from (select ai.partner_id rp_id from account_invoice ai inner join res_partner rp on ai.partner_id = rp.id where not ai.state = 'cancel' and not ai.state = 'draft' and ai.type = 'out_invoice' and (ai.factcte_receptor = '1' or ai.factcte_receptor = '2') and ai.company_id = {}) invs union (select ocup_nombre rp_id from avb3_vaiunidad where company_id = {}) union (select prop_nombre rp_id from avb3_vaiunidad where company_id = {}) order by rp_id) prtnrs inner join res_partner rps on prtnrs.rp_id = rps.id left join (select case when sa1.rp_id is null then sa2.rp_id else sa1.rp_id end rp_id, case when sa1.rp_name is null then sa2.rp_name else sa1.rp_name end rp_name, case when sa1.sum_sa is null then 0 else sa1.sum_sa end - case when sa2.sum_sa is null then 0 else sa2.sum_sa end sum_sa from (select rp_id, rp_name, sum_sa from (select case when ai.rp_id is null then aicn.rp_id else ai.rp_id end rp_id, case when ai.rp_name is null then aicn.rp_name else ai.rp_name end rp_name, case when ai.amount_total is null then 0 else ai.amount_total end + case when aicn.amount_total is null then 0 else aicn.amount_total end sum_sa from (select rp.id rp_id, rp.name rp_name, sum(case when ai.amount_total is null then 0 else ai.amount_total end) amount_total from res_partner rp inner join account_invoice ai on rp.id = ai.partner_id and rp.customer = 't' and ai.type = 'out_invoice' and not ai.state = 'cancel' and not ai.state = 'draft' and (ai.factcte_receptor = '1' or ai.factcte_receptor = '2') and ai.company_id = {} and ai.date_invoice < %s group by rp_id, rp_name order by rp_id) ai left outer join (select rp.id rp_id, rp.name rp_name, sum(case when aicn.amount_total_signed is null then 0 else aicn.amount_total_signed end) amount_total from res_partner rp inner join account_invoice aicn on rp.id = aicn.partner_id and rp.customer = 't' and aicn.type = 'out_refund' and not aicn.state = 'cancel' and not aicn.state = 'draft' and (aicn.factcte_receptor = '1' or aicn.factcte_receptor = '2') and aicn.company_id = {} and aicn.date_invoice < %s group by rp_id, rp_name order by rp_id) aicn on ai.rp_id = aicn.rp_id) aiaicn order by rp_id) sa1 full outer join (select pre_sa2.rp_id rp_id, pre_sa2.rp_name rp_name, sum(pre_sa2.sum_sa) sum_sa from (select rp.id rp_id, rp.name rp_name, ap.id, ai.id, case when omip.amount is null then 0 else omip.amount end sum_sa from occupant_movement_invoices_payments omip inner join account_invoice ai on omip.ai_id = ai.id and not ai.state = 'cancel' and not ai.state = 'draft' and ai.type = 'out_invoice' and (ai.factcte_receptor = '1' or ai.factcte_receptor = '2') and ai.company_id = {} inner join res_partner rp on ai.partner_id = rp.id and rp.customer = 't' inner join account_payment ap on omip.ap_id = ap.id and ap.payment_date < %s and not ap.state = 'cancelled' and not ap.state = 'draft' order by rp.id, ap.id, ai.id) pre_sa2 group by rp_id, rp_name order by rp_id) sa2 on sa1.rp_id = sa2.rp_id) sa on prtnrs.rp_id = sa.rp_id left join (select rp_id, rp_name, sum_i from (select case when ai.rp_id is null then aicn.rp_id else ai.rp_id end rp_id, case when ai.rp_name is null then aicn.rp_name else ai.rp_name end rp_name, case when ai.amount_total is null then 0 else ai.amount_total end + case when aicn.amount_total is null then 0 else aicn.amount_total end sum_i from (select rp.id rp_id, rp.name rp_name, sum(case when ai.amount_total is null then 0 else ai.amount_total end) amount_total from res_partner rp inner join account_invoice ai on rp.id = ai.partner_id and rp.customer = 't' and ai.type = 'out_invoice' and not ai.state = 'cancel' and not ai.state = 'draft' and (ai.factcte_receptor = '1' or ai.factcte_receptor = '2') and ai.company_id = {} and ai.date_invoice >= %s and ai.date_invoice <= %s group by rp_id, rp_name order by rp_id) ai left outer join (select rp.id rp_id, rp.name rp_name, sum(case when aicn.amount_total_signed is null then 0 else aicn.amount_total_signed end) amount_total from res_partner rp inner join account_invoice aicn on rp.id = aicn.partner_id and rp.customer = 't' and aicn.type = 'out_refund' and not aicn.state = 'cancel' and not aicn.state = 'draft' and (aicn.factcte_receptor = '1' or aicn.factcte_receptor = '2') and aicn.company_id = {} and aicn.date_invoice >= %s and aicn.date_invoice <= %s group by rp_id, rp_name order by rp_id) aicn on ai.rp_id = aicn.rp_id) aiaicn order by rp_id) i on prtnrs.rp_id = i.rp_id left join (select pre_a.rp_id rp_id, pre_a.rp_name rp_name, sum(pre_a.sum_a) sum_a from (select rp.id rp_id, rp.name rp_name, case when omip.amount is null then 0 else omip.amount end sum_a from occupant_movement_invoices_payments omip inner join account_invoice ai on omip.ai_id = ai.id and not ai.state = 'cancel' and not ai.state = 'draft' and ai.type = 'out_invoice' and (ai.factcte_receptor = '1' or ai.factcte_receptor = '2') and ai.company_id = {} inner join res_partner rp on ai.partner_id = rp.id and rp.customer = 't' inner join account_payment ap on omip.ap_id = ap.id and ap.payment_date >= %s and ap.payment_date <= %s and not ap.state = 'cancelled' and not ap.state = 'draft' order by rp.id, ap.id, ai.id) pre_a group by rp_id, rp_name order by rp_id) a on prtnrs.rp_id = a.rp_id left join (select undds.rp_id rp_id, string_agg(distinct(undds.u_name), ',' order by undds.u_name) agg_u from (select distinct(u_id, u_name, rp_id), u_id, u_name, rp_id from (select u_id, u_name, rp_id from (select distinct id u_id, name u_name, prop_nombre rp_id from avb3_vaiunidad where company_id = {}) prop union all (select distinct id u_id, name u_name, ocup_nombre rp_id from avb3_vaiunidad where company_id = {}) union all (select u_id, u_name, rp_id from (select distinct(avb3vpup.pago_unidadprivid, avb3vpup.pago_unidadpriv, ai.partner_id), avb3vpup.pago_unidadprivid u_id, avb3vpup.pago_unidadpriv u_name, ai.partner_id rp_id from avb3_vaipagunidpriv avb3vpup inner join account_invoice ai on avb3vpup.pago_idfac = ai.id inner join res_partner rp on ai.partner_id = rp.id where not ai.state = 'cancel' and not ai.state = 'draft' and not ai.state = 'paid' and ai.type = 'out_invoice' and (ai.factcte_receptor = '1' or ai.factcte_receptor = '2') and ai.company_id = {} and avb3vpup.company_id = {} order by avb3vpup.pago_unidadprivid) uavb3vpup) order by u_id) unid) undds group by undds.rp_id order by agg_u) u on prtnrs.rp_id = u.rp_id left join (select undds.rp_id rp_id, string_agg(distinct(undds.u_name), ',' order by undds.u_name) agg_u from (select u_id, u_name, rp_id from (select distinct (u.id, u.name, rp.id, rp.name), u.id u_id, u.name u_name, rp.id rp_id, rp.name rp_name from res_partner rp inner join account_invoice ai on rp.id = ai.partner_id and rp.customer = 't' and ai.type = 'out_invoice' and not ai.state = 'cancel' and not ai.state = 'draft' and (ai.factcte_receptor = '1' or ai.factcte_receptor = '2') and ai.company_id = {} and ai.date_invoice <= %s inner join avb3_vaiunidad u on ai.factcte_unidpriv = u.id order by u_id) uavb3vpup order by u_id) undds group by undds.rp_id order by agg_u) u_aux on prtnrs.rp_id = u_aux.rp_id) as finaliio order by agg_u"

                self._cr.execute(query.format(current_company_id, current_company_id, current_company_id, current_company_id, current_company_id, current_company_id, current_company_id, current_company_id, current_company_id, current_company_id, current_company_id, current_company_id, current_company_id, current_company_id), (date_start, date_start, date_start, date_start, date_end, date_start, date_end, date_start, date_end, date_end))
                result = self._cr.dictfetchall()

                count = self.env.cr.rowcount
                print("*************************************************DATOS*****************************************************",count)
                
                docs = []
                for row in result:
                    docs.append({
                        'partnername': row.get('rp_name'),
                        'sumsa': row.get('sum_sa'),
                        'sumi': row.get('sum_i'),
                        'suma': row.get('sum_a'),
                        'sums': row.get('sum_s'),
                        'aggu': row.get('agg_u'),
                    })
            else:
                if not global_indiviso_includes and indiviso_ids:
                    self.env.cr.execute("select name from avb3_vaiindiviso where id = {} and company_id = {}".format(indiviso_ids, current_company_id))
                    indiviso_names = self.env.cr.fetchone()[0]

                    query = "select * from (select rps.display_name rp_name, case when sa.sum_sa is null then 0 else sa.sum_sa end sum_sa, case when i.sum_i is null then 0 else i.sum_i end sum_i, case when a.sum_a is null then 0 else a.sum_a end sum_a, case when sa.sum_sa is null then 0 else sa.sum_sa end + case when i.sum_i is null then 0 else i.sum_i end - case when a.sum_a is null then 0 else a.sum_a end sum_s, case when u.agg_u is null then u_aux.agg_u else u.agg_u end agg_u from (select rp_id from (select ai.partner_id rp_id from account_invoice ai inner join res_partner rp on ai.partner_id = rp.id where not ai.state = 'cancel' and not ai.state = 'draft' and ai.type = 'out_invoice' and (ai.factcte_receptor = '1' or ai.factcte_receptor = '2') and ai.company_id = {} and ai.factcte_indiviso = {}) invs union (select ocup_nombre rp_id from avb3_vaiunidad where company_id = {}) union (select prop_nombre rp_id from avb3_vaiunidad where company_id = {}) order by rp_id) prtnrs inner join res_partner rps on prtnrs.rp_id = rps.id left join (select case when sa1.rp_id is null then sa2.rp_id else sa1.rp_id end rp_id, case when sa1.rp_name is null then sa2.rp_name else sa1.rp_name end rp_name, case when sa1.sum_sa is null then 0 else sa1.sum_sa end - case when sa2.sum_sa is null then 0 else sa2.sum_sa end sum_sa from (select rp_id, rp_name, sum_sa from (select case when ai.rp_id is null then aicn.rp_id else ai.rp_id end rp_id, case when ai.rp_name is null then aicn.rp_name else ai.rp_name end rp_name, case when ai.amount_total is null then 0 else ai.amount_total end + case when aicn.amount_total is null then 0 else aicn.amount_total end sum_sa from (select rp.id rp_id, rp.name rp_name, sum(case when ai.amount_total is null then 0 else ai.amount_total end) amount_total from res_partner rp inner join account_invoice ai on rp.id = ai.partner_id and rp.customer = 't' and ai.type = 'out_invoice' and not ai.state = 'cancel' and not ai.state = 'draft' and (ai.factcte_receptor = '1' or ai.factcte_receptor = '2') and ai.company_id = {} and ai.factcte_indiviso = {} and ai.date_invoice < %s group by rp_id, rp_name order by rp_id) ai left outer join (select rp.id rp_id, rp.name rp_name, sum(case when aicn.amount_total_signed is null then 0 else aicn.amount_total_signed end) amount_total from res_partner rp inner join account_invoice aicn on rp.id = aicn.partner_id and rp.customer = 't' and aicn.type = 'out_refund' and not aicn.state = 'cancel' and not aicn.state = 'draft' and (aicn.factcte_receptor = '1' or aicn.factcte_receptor = '2') and aicn.company_id = {} and aicn.factcte_indiviso = {} and aicn.date_invoice < %s group by rp_id, rp_name order by rp_id) aicn on ai.rp_id = aicn.rp_id) aiaicn order by rp_id) sa1 full outer join (select pre_sa2.rp_id rp_id, pre_sa2.rp_name rp_name, sum(pre_sa2.sum_sa) sum_sa from (select rp.id rp_id, rp.name rp_name, ap.id, ai.id, case when omip.amount is null then 0 else omip.amount end sum_sa from occupant_movement_invoices_payments omip inner join account_invoice ai on omip.ai_id = ai.id and not ai.state = 'cancel' and not ai.state = 'draft' and ai.type = 'out_invoice' and (ai.factcte_receptor = '1' or ai.factcte_receptor = '2') and ai.company_id = {} and ai.factcte_indiviso = {} inner join res_partner rp on ai.partner_id = rp.id and rp.customer = 't' inner join account_payment ap on omip.ap_id = ap.id and ap.payment_date < %s and not ap.state = 'cancelled' and not ap.state = 'draft' order by rp.id, ap.id, ai.id) pre_sa2 group by rp_id, rp_name order by rp_id) sa2 on sa1.rp_id = sa2.rp_id) sa on prtnrs.rp_id = sa.rp_id left join (select rp_id, rp_name, sum_i from (select case when ai.rp_id is null then aicn.rp_id else ai.rp_id end rp_id, case when ai.rp_name is null then aicn.rp_name else ai.rp_name end rp_name, case when ai.amount_total is null then 0 else ai.amount_total end + case when aicn.amount_total is null then 0 else aicn.amount_total end sum_i from (select rp.id rp_id, rp.name rp_name, sum(case when ai.amount_total is null then 0 else ai.amount_total end) amount_total from res_partner rp inner join account_invoice ai on rp.id = ai.partner_id and rp.customer = 't' and ai.type = 'out_invoice' and not ai.state = 'cancel' and not ai.state = 'draft' and (ai.factcte_receptor = '1' or ai.factcte_receptor = '2') and ai.company_id = {} and ai.factcte_indiviso = {} and ai.date_invoice >= %s and ai.date_invoice <= %s group by rp_id, rp_name order by rp_id) ai left outer join (select rp.id rp_id, rp.name rp_name, sum(case when aicn.amount_total_signed is null then 0 else aicn.amount_total_signed end) amount_total from res_partner rp inner join account_invoice aicn on rp.id = aicn.partner_id and rp.customer = 't' and aicn.type = 'out_refund' and not aicn.state = 'cancel' and not aicn.state = 'draft' and (aicn.factcte_receptor = '1' or aicn.factcte_receptor = '2') and aicn.company_id = {} and aicn.factcte_indiviso = {} and aicn.date_invoice >= %s and aicn.date_invoice <= %s group by rp_id, rp_name order by rp_id) aicn on ai.rp_id = aicn.rp_id) aiaicn order by rp_id) i on prtnrs.rp_id = i.rp_id left join (select pre_a.rp_id rp_id, pre_a.rp_name rp_name, sum(pre_a.sum_a) sum_a from (select rp.id rp_id, rp.name rp_name, case when omip.amount is null then 0 else omip.amount end sum_a from occupant_movement_invoices_payments omip inner join account_invoice ai on omip.ai_id = ai.id and not ai.state = 'cancel' and not ai.state = 'draft' and ai.type = 'out_invoice' and (ai.factcte_receptor = '1' or ai.factcte_receptor = '2') and ai.company_id = {} and ai.factcte_indiviso = {} inner join res_partner rp on ai.partner_id = rp.id and rp.customer = 't' inner join account_payment ap on omip.ap_id = ap.id and ap.payment_date >= %s and ap.payment_date <= %s and not ap.state = 'cancelled' and not ap.state = 'draft' order by rp.id, ap.id, ai.id) pre_a group by rp_id, rp_name order by rp_id) a on prtnrs.rp_id = a.rp_id left join (select undds.rp_id rp_id, string_agg(distinct(undds.u_name), ',' order by undds.u_name) agg_u from (select distinct(u_id, u_name, rp_id), u_id, u_name, rp_id from (select u_id, u_name, rp_id from (select distinct id u_id, name u_name, prop_nombre rp_id from avb3_vaiunidad where company_id = {}) prop union all (select distinct id u_id, name u_name, ocup_nombre rp_id from avb3_vaiunidad where company_id = {}) union all (select u_id, u_name, rp_id from (select distinct(avb3vpup.pago_unidadprivid, avb3vpup.pago_unidadpriv, ai.partner_id), avb3vpup.pago_unidadprivid u_id, avb3vpup.pago_unidadpriv u_name, ai.partner_id rp_id from avb3_vaipagunidpriv avb3vpup inner join account_invoice ai on avb3vpup.pago_idfac = ai.id inner join res_partner rp on ai.partner_id = rp.id where not ai.state = 'cancel' and not ai.state = 'draft' and not ai.state = 'paid' and ai.type = 'out_invoice' and (ai.factcte_receptor = '1' or ai.factcte_receptor = '2') and ai.company_id = {} and ai.factcte_indiviso = {} and avb3vpup.company_id = {} order by avb3vpup.pago_unidadprivid) uavb3vpup) order by u_id) unid) undds group by undds.rp_id order by agg_u) u on prtnrs.rp_id = u.rp_id left join (select undds.rp_id rp_id, string_agg(distinct(undds.u_name), ',' order by undds.u_name) agg_u from (select u_id, u_name, rp_id from (select distinct (u.id, u.name, rp.id, rp.name), u.id u_id, u.name u_name, rp.id rp_id, rp.name rp_name from res_partner rp inner join account_invoice ai on rp.id = ai.partner_id and rp.customer = 't' and ai.type = 'out_invoice' and not ai.state = 'cancel' and not ai.state = 'draft' and (ai.factcte_receptor = '1' or ai.factcte_receptor = '2') and ai.company_id = {} and ai.factcte_indiviso = {} and ai.date_invoice <= %s inner join avb3_vaiunidad u on ai.factcte_unidpriv = u.id order by u_id) uavb3vpup order by u_id) undds group by undds.rp_id order by agg_u) u_aux on prtnrs.rp_id = u_aux.rp_id) as finaliio order by agg_u"

                    self._cr.execute(query.format(current_company_id, indiviso_ids, current_company_id, current_company_id, current_company_id, indiviso_ids, current_company_id, indiviso_ids, current_company_id, indiviso_ids, current_company_id, indiviso_ids, current_company_id, indiviso_ids, current_company_id, indiviso_ids, current_company_id, current_company_id, current_company_id, indiviso_ids, current_company_id, current_company_id, indiviso_ids), (date_start, date_start, date_start, date_start, date_end, date_start, date_end, date_start, date_end, date_end))
                    result = self._cr.dictfetchall()

                    count = self.env.cr.rowcount
                    print("*************************************************DATOS*****************************************************",count)

                    docs = []
                    for row in result:
                        docs.append({
                            'partnername': row.get('rp_name'),
                            'sumsa': row.get('sum_sa'),
                            'sumi': row.get('sum_i'),
                            'suma': row.get('sum_a'),
                            'sums': row.get('sum_s'),
                            'aggu': row.get('agg_u'),
                        })
                else:
                    indiviso_ids = ''
                    indiviso_names = ''
                    docs = []
                    docs.append({
                        'partnername': '',
                        'sumsa': 0,
                        'sumi': 0,
                        'suma': 0,
                        'sums': 0,
                        'aggu': '',
                    })

        return {
            'doc_ids': data['ids'],
            'doc_model': data['model'],
            'date_start': date_starts,
            'date_end': date_ends,
            'indiviso_id': indiviso_ids,
            'indiviso_name': indiviso_names,
            'partner_type': partner_types,
            'docs': docs,
        }