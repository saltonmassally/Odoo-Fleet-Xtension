
import time
from datetime import date, datetime, timedelta

from openerp import models, fields, api
from openerp.exceptions import except_orm, Warning, RedirectWarning, ValidationError
from openerp.tools import float_compare, float_is_zero
from openerp.tools.translate import _

class fleet_vehicle_cost(models.Model):
    _inherit = 'fleet.vehicle.cost'

    move_id = fields.Many2one('account.move', 'Accounting Entry', readonly=True, 
                              copy=False, ondelete='restrict')

    
    
    @api.model
    @api.returns('self', lambda value:value.id)
    def create(self, vals):
        res = super(fleet_vehicle_cost, self).create(vals)
        self.post_cost()
        return res

    @api.multi
    def unlink(self):
        move_pool = self.env['account.move']
        move_ids = []
        move_to_cancel = []
        for cost in self:
            if cost.move_id:
                if cost.move_id.state == 'posted':
                    cost.move_id.button_cancel()
                cost.move_id.unlink()
        return super(fleet_vehicle_cost, self).unlink()

    @api.multi
    def post_cost(self):
        move_pool = self.env['account.move']
        period_pool = self.env['account.period']
        precision = self.env['decimal.precision'].precision_get('Account')
        timenow = fields.Date.today()

        for cost in self:
            line_ids = []
            debit_sum = 0.0
            credit_sum = 0.0
            search_periods = period_pool.find(cost.date)
            period_id = search_periods[0]

            default_partner_id = cost.vendor_id.id
            name = _('%s cost of %s') % (cost.cost_subtype_id.name.capitalize(), cost.vehicle_id.name)
            move = {
                'narration': name,
                'date': timenow,
                'ref': cost.ref,
                'journal_id': cost.cost_subtype_id.journal_id,
                'period_id': period_id,
            }
            amt = cost.amount
            if float_is_zero(amt, precision_digits=precision):
                return
            partner_id = default_partner_id
            account_info = cost.get_account_info()
            debit_account_id = account_info['account_debit']
            credit_account_id = account_info['account_credit']
            analytic_account_id = account_info['analytic_account_id']
            journal_id = account_info['journal_id']

            if debit_account_id:
                debit_line = (0, 0, {
                'name': cost.name,
                'date': timenow,
                'partner_id': partner_id or False,
                'account_id': debit_account_id,
                'journal_id': journal_id.id,
                'period_id': period_id,
                'debit': amt > 0.0 and amt or 0.0,
                'credit': amt < 0.0 and -amt or 0.0,
                'analytic_account_id': analytic_account_id or False,
            })
                line_ids.append(debit_line)
                debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']

            if credit_account_id:
                credit_line = (0, 0, {
                'name': cost.name,
                'date': timenow,
                'partner_id': partner_id or False,
                'account_id': debit_account_id,
                'journal_id': journal_id.id,
                'period_id': period_id,
                'debit': amt < 0.0 and -amt or 0.0,
                'credit': amt > 0.0 and amt or 0.0,
                'analytic_account_id': analytic_account_id or False,
            })
                line_ids.append(credit_line)
                credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']

            if float_compare(credit_sum, debit_sum, precision_digits=precision) == -1:
                acc_id = journal_id.default_credit_account_id.id
                if not acc_id:
                    raise Warning(_('The Expense Journal "%s" has not properly configured the Credit Account!') % (journal_id.name))
                adjust_credit = (0, 0, {
                    'name': _('Adjustment Entry'),
                    'date': timenow,
                    'partner_id': False,
                    'account_id': acc_id,
                    'journal_id': journal_id.id,
                    'period_id': period_id,
                    'debit': 0.0,
                    'credit': debit_sum - credit_sum,
                })
                line_ids.append(adjust_credit)

            elif float_compare(debit_sum, credit_sum, precision_digits=precision) == -1:
                acc_id = cost.journal_id.default_debit_account_id.id
                if not acc_id:
                    raise osv.except_osv(_('Configuration Error!'), _('The Expense Journal "%s" has not properly configured the Debit Account!') % (cost.journal_id.name))
                adjust_debit = (0, 0, {
                    'name': _('Adjustment Entry'),
                    'date': timenow,
                    'partner_id': False,
                    'account_id': acc_id,
                    'journal_id': journal_id.id,
                    'period_id': period_id,
                    'debit': credit_sum - debit_sum,
                    'credit': 0.0,
                })
                line_ids.append(adjust_debit)

            move.update({'line_id': line_ids})
            move = move_pool.create(cr, uid, move, context=context)
            cost.move_id = move
            if journal_id.entry_posted:
                move.post()
            return move
    
class fleet_service_type(models.Model):
    _inherit = 'fleet.service.type'

    def _get_default_analytic(self):
        res = self.env["ir.config_parameter"].get_param("fleet.default_analytic_account_id")
        return res and self.env['account.account'].browse(res) or False
    
    def _get_default_debit(self):
        res = self.env["ir.config_parameter"].get_param("fleet.default_account_debit")
        return res and self.env['account.account'].browse(res) or False
    
    def _get_default_credit(self):
        res = self.env["ir.config_parameter"].get_param("fleet.default_account_credit")
        return res and self.env['account.account'].browse(res) or False
    
    def _get_default_journal(self):
        res = self.env["ir.config_parameter"].get_param("fleet.default_journal_id")
        return res and self.env['account.journal'].browse(res) or False

    
    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account',
                                          domain=[('type', '!=', 'view')])
    account_debit = fields.Many2one('account.account', 'Debit Account', 
                                    domain=[('type', '=', 'other')])
    account_credit = fields.Many2one('account.account', 'Credit Account', 
                                     domain=[('type', '=', 'other')])
    journal_id = fields.Many2one('account.journal', 'Journal')
    
    @api.one
    def get_account_info(self):
        
        return {
               'analytic_account_id' : self.analytic_account_id or self._get_default_analytic(),
               'account_debit' : self.account_debit or self._get_default_debit(),
               'account_credit' : self.account_credit or self._get_default_credit(),
               'journal_id' : self.journal_id or self._get_default_journal(),
               
               }
   
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
