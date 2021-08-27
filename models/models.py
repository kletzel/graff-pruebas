# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class graff_rep_resmov(models.Model):
#     _name = 'graff_rep_resmov.graff_rep_resmov'
#     _description = 'graff_rep_resmov.graff_rep_resmov'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100
