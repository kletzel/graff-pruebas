# -*- coding: utf-8 -*-
# from odoo import http


# class GrappRepMrp(http.Controller):
#     @http.route('/grapp_rep_mrp/grapp_rep_mrp/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/grapp_rep_mrp/grapp_rep_mrp/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('grapp_rep_mrp.listing', {
#             'root': '/grapp_rep_mrp/grapp_rep_mrp',
#             'objects': http.request.env['grapp_rep_mrp.grapp_rep_mrp'].search([]),
#         })

#     @http.route('/grapp_rep_mrp/grapp_rep_mrp/objects/<model("grapp_rep_mrp.grapp_rep_mrp"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('grapp_rep_mrp.object', {
#             'object': obj
#         })
