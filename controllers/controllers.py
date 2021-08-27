# -*- coding: utf-8 -*-
# from odoo import http


# class GraffRepResmov(http.Controller):
#     @http.route('/graff_rep_resmov/graff_rep_resmov/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/graff_rep_resmov/graff_rep_resmov/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('graff_rep_resmov.listing', {
#             'root': '/graff_rep_resmov/graff_rep_resmov',
#             'objects': http.request.env['graff_rep_resmov.graff_rep_resmov'].search([]),
#         })

#     @http.route('/graff_rep_resmov/graff_rep_resmov/objects/<model("graff_rep_resmov.graff_rep_resmov"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('graff_rep_resmov.object', {
#             'object': obj
#         })
