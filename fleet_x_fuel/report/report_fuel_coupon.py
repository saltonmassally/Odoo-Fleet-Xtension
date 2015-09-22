#-*- coding:utf-8 -*-

##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    d$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time
from openerp.osv import osv
from openerp.report import report_sxw
import base64
import logging

try:
    from reportlab.graphics.barcode import createBarcodeDrawing
except:
    _logger = logging.getLogger(__name__)
    _logger.info("ERROR IMPORTING REPORT LAB")

def get_barcode_image(self, value, width=False, hight=False, hr=True, code='QR'):
        """ genrating image for barcode """
        options = {}
        if width:
            options['width'] = width
        if hight:
            options['hight'] = hight
        if hr:
            options['humanReadable'] = hr
        try:
            ret_val = createBarcodeDrawing(code, value=str(value), **options)
        except Exception, e:
            raise osv.except_osv('Error', e)
        return base64.encodestring(ret_val.asString('jpg'))

class fuel_coupon_report(report_sxw.rml_parse):
    
    def __init__(self, cr, uid, name, context):
        super(fuel_coupon_report, self).__init__(cr, uid, name, context=context)
        #lets scream if state is not right
        coupon_ids  = context.get('active_ids', False)
        if coupon_ids:
            for coupon in self.pool.get('fleet.fuel.coupon').read(cr, uid, coupon_ids, ['state'], context=context):
                if coupon['state'] != 'active':
                    raise osv.except_osv('Error', 'Only active coupons can be printed!')

        user = self.pool['res.users'].browse(cr, uid, uid, context=context)
        partner = user.company_id.partner_id

        self.localcontext.update({
            'time': time,
            'partner': partner or False,
            'user': user or False,
            'barcode': self.render_image,
        })
    
    
    def render_image(self, barcode):
        barcode = get_barcode_image(value=barcode, code='QR')
        return barcode

class wrapped_report_fuel_coupon(osv.AbstractModel):
    _name = 'report.fleet_x_fuel.report_fuel_coupon'
    _inherit = 'report.abstract_report'
    _template = 'fleet_x_fuel.report_fuel_coupon'
    _wrapped_report_class = fuel_coupon_report

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
