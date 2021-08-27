from odoo import models, fields, api, tools
from datetime import datetime

class graffresmovWizardavb(models.Model):
    _name = 'graff_rep_resmov.wizardavb'

    date_start = fields.Date(string="Fecha Inicial", required=True, default=fields.Date.today)
    date_end = fields.Date(string="Fecha Final", required=True, default=fields.Date.today)

#class graffresmovWizard(models.TransientModel):
 #   _name = 'graff_rep_resmov.wizard'

  #  date_start = fields.Date(string="Fecha Inicial", required=True, default=fields.Date.today)
  #  date_end = fields.Date(string="Fecha Final", required=True, default=fields.Date.today)

    #@api.multi
   # def get_report(self):
    #    """Call when button 'Get Report' clicked.
     #   """
      #  data = {
       #     'ids': self.ids,
        #    'model': self._name,
         #   'form': {
          #      'date_start': self.date_start,
           #     'date_end': self.date_end,
          #  },
       # }

        # use `module_name.report_id` as reference.
        # `report_action()` will call `get_report_values()` and pass `data` automatically.
        #return self.env.ref('date_range_occupant_movement_report.date_range_occupant_movement_report').report_action(self, data=data)
        #return self.env.ref('graff_rep_resmov.graff_rep_resmov').report_action(self, data=data)

class graffresmov(models.Model):
    _name = 'graff_rep_resmov.graffresmov'
    _description = 'Lista de Productos por Orden de produccion'
    _auto = False

    name = fields.Char("Identificador", size=20)
    resmov_fecha_mrp = fields.Date(string="Fecha de Orden de Produccion")
    resmov_docto_mrp = fields.Char(string="Numero de Orden de Produccion", size=150)
    resmov_producto_id = fields.Char(string="id de Producto", size=150)
    resmov_producto_codigo = fields.Char(string="Codigo de Producto", size=50)
    resmov_producto_nombre = fields.Char(string="Nombre de Producto", size=150)
    resmov_producto_cant = fields.Char(string="Num. doc. Prov./Referencia", size=50)
    
    def init(self):
        self._cr.execute("""DROP VIEW IF EXISTS graff_rep_resmov_resmov""")
        self._cr.execute("""CREATE OR REPLACE VIEW graff_rep_resmov_resmov as select sm.id as id, mrp.name, cast(mrp.date_planned_start as date) as resmov_fecha_mrp, sm.reference as resmov_docto_mrp, sm.product_id as resmov_producto_id, pt.default_code as resmov_producto_codigo, pt.name  as resmov_producto_nombre, sm.product_uom_qty as resmov_producto_cant from mrp_production mrp, stock_move sm, product_product pp, product_template pt where sm.product_id = pp.id and pp.product_tmpl_id = pt.id and mrp.name = sm.reference order by sm.product_id""")
