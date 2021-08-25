# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class grapp_rep_mrp(models.Model):
#     _name = 'grapp_rep_mrp.grapp_rep_mrp'
#     _description = 'grapp_rep_mrp.grapp_rep_mrp'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100
