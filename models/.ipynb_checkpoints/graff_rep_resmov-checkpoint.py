import requests
import json
import io
import os
import glob
import base64
from odoo import models, fields, api, tools, exceptions, _
from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT

#class graffresmovWizardavb(models.Model):
 #   _name = 'graff_rep_resmov.wizardavb'

  #  date_start = fields.Date(string="Fecha Inicial", required=True, default=fields.Date.today)
   # date_end = fields.Date(string="Fecha Final", required=True, default=fields.Date.today)

class graffresmovWizard(models.TransientModel):
    _name = 'graff_rep_resmov.wizard'

    date_start = fields.Date(string="Fecha Inicial", required=True, default=fields.Date.today)
    date_end = fields.Date(string="Fecha Final", required=True, default=fields.Date.today)
    #resmov_producto_codigo = fields.Char(string="Codigo de Producto", size=50)

    #@api.multi
    def get_report(self):
    #    """Call when button 'Get Report' clicked.
     #   """
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'date_start': self.date_start,
                'date_end': self.date_end,
            },
        }

        # use `module_name.report_id` as reference.
        # `report_action()` will call `get_report_values()` and pass `data` automatically.
        #return self.env.ref('date_range_occupant_movement_report.date_range_occupant_movement_report').report_action(self, data=data)
        return self.env.ref('graff_rep_resmov.graff_rep_resmov').report_action(self, data=data)

class graffresmov(models.AbstractModel):
    #_name = 'graff_rep_resmov.reporte_resmov_template'
    _name = 'report.graff_rep_resmov.reporte_resmov_template'
    #_description = 'Lista de Productos por Orden de produccion'
    #_auto = False

    #name = fields.Char("Identificador", size=20)
    #resmov_fecha_mrp = fields.Date(string="Fecha de Orden de Produccion")
    #resmov_docto_mrp = fields.Char(string="Numero de Orden de Produccion", size=150)
    #resmov_producto_id = fields.Char(string="id de Producto", size=150)
    #resmov_producto_codigo = fields.Char(string="Codigo de Producto", size=50)YY
    #resmov_producto_nombre = fields.Char(string="Nombre de Producto", size=150)
    #resmov_producto_cant = fields.Float(string="Cantidad de Producto" )
    
    #def init(self):
    def _get_report_values(self, docids, data=None):
        date_start = data['form']['date_start']
        date_end = data['form']['date_end']
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

        #self._cr.execute("select sm.id as id, mrp.name, cast(mrp.date_planned_start as date) as resmov_fecha_mrp, sm.reference as resmov_docto_mrp, sm.product_id as resmov_producto_id, pt.default_code as resmov_producto_codigo, pt.name  as resmov_producto_nombre, sm.product_uom_qty as resmov_producto_cant from mrp_production mrp, stock_move sm, product_product pp, product_template pt where sm.product_id = pp.id and pp.product_tmpl_id = pt.id and mrp.name = sm.reference and cast(mrp.date_planned_start as date) >= %s and cast(mrp.date_planned_start as date) <= %s order by sm.product_id", (date_start, date_end))
        #self.env.cr.execute("select sm.id as id, mrp.name ord_prod, to_char(mrp.date_planned_start::date, 'DD/MM/YYYY') as resmov_fecha_mrp, sm.reference as resmov_docto_mrp, sm.product_id as resmov_producto_id, pt.default_code as resmov_producto_codigo, pt.name  as resmov_producto_nombre, sm.product_uom_qty as resmov_producto_cant, 0 res_det from mrp_production mrp, stock_move sm, product_product pp, product_template pt where sm.product_id = pp.id and pp.product_tmpl_id = pt.id and mrp.name = sm.reference and cast(mrp.date_planned_start as date) >= '%s' and cast(mpr.date_planned_start as date) <= '%s' union select null as id, null ord_prod, null resmov_fecha_mrp, null as resmov_docto_mrp, sm.product_id as resmov_producto_id, pt.default_code as resmov_producto_codigo, pt.name as resmov_producto_nombre, sum(sm.product_uom_qty) as resmov_producto_cant, 1 res_det from mrp_production mrp, stock_move sm, product_product pp, product_template pt where mrp.name = sm.reference and sm.product_id = pp.id and pp.product_tmpl_id = pt.id and cast(mrp.date_planned_start as date) >= '%s' and cast(mpr.date_planned_start as date) <= '%s' group by sm.product_id, pt.default_code, pt.name order by resmov_producto_id, res_det", (date_starts, date_ends, date_starts, date_ends))
        self.env.cr.execute("select sm.id as id, mrp.name ord_prod, to_char(mrp.date_planned_start::date, 'DD/MM/YYYY') as resmov_fecha_mrp, sm.reference as resmov_docto_mrp, sm.product_id as resmov_producto_id, pt.default_code as resmov_producto_codigo, pt.name  as resmov_producto_nombre, sm.product_uom_qty as resmov_producto_cant, 0 res_det from mrp_production mrp, stock_move sm, product_product pp, product_template pt where sm.product_id = pp.id and pp.product_tmpl_id = pt.id and mrp.name = sm.reference and date_planned_start >= '{}' and date_planned_start <= '{}' union select null as id, null ord_prod, null resmov_fecha_mrp, null as resmov_docto_mrp, sm.product_id as resmov_producto_id, pt.default_code as resmov_producto_codigo, pt.name as resmov_producto_nombre, sum(sm.product_uom_qty) as resmov_producto_cant, 1 res_det from mrp_production mrp, stock_move sm, product_product pp, product_template pt where mrp.name = sm.reference and sm.product_id = pp.id and pp.product_tmpl_id = pt.id and date_planned_start >= '{}' and date_planned_start <= '{}' group by sm.product_id, pt.default_code, pt.name order by resmov_producto_id, res_det".format(date_start, date_end, date_start, date_end))
        if self.env.cr.rowcount:
            res = self.env.cr.fetchall() 
            docs = []
            for dato in res:
              fecha = dato[2]
              docto = dato[3]
              prod_codigo = dato[5]
              prod_nombre = dato[6]
              prod_cantidad = dato[7]
              res_det = dato[8]
           #     for row in result:
              docs.append({
                        'resmov_fecha_mrp': fecha,
                        'resmov_docto_mrp': docto,
                        #'resmov_producto_codigo': dato.get('resmov_producto_codigo'),
                        'resmov_producto_codigo': prod_codigo,
                        'resmov_producto_nombre': prod_nombre,
                        'resmov_producto_cant': prod_cantidad,
                        'res_det': res_det,
                    })
        return {
            'doc_ids': data['ids'],
            'doc_model': data['model'],
            'date_start': date_starts,
            'date_end': date_ends,
            'docs': docs,
        }                    
