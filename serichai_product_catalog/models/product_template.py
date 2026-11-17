from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    catalog_price_incl_tax = fields.Monetary(
        compute='_compute_catalog_price_incl_tax',
        currency_field='currency_id')
    catalog_cost_incl_tax = fields.Monetary(
        compute='_compute_catalog_cost_incl_tax',
        currency_field='currency_id',
        groups='purchase.group_purchase_user')
    catalog_margin = fields.Monetary(
        compute='_compute_catalog_margin',
        currency_field='currency_id',
        groups='purchase.group_purchase_user')

    @api.depends('list_price', 'taxes_id')
    @api.depends_context('company')
    def _compute_catalog_price_incl_tax(self):
        for tmpl in self:
            taxes = tmpl.taxes_id._filter_taxes_by_company(self.env.company)
            tmpl.catalog_price_incl_tax = taxes.compute_all(
                tmpl.list_price, tmpl.currency_id, 1, product=tmpl,
            )['total_included']

    @api.depends('standard_price', 'supplier_taxes_id')
    @api.depends_context('company')
    def _compute_catalog_cost_incl_tax(self):
        for tmpl in self:
            taxes = tmpl.supplier_taxes_id._filter_taxes_by_company(
                self.env.company)
            tmpl.catalog_cost_incl_tax = taxes.compute_all(
                tmpl.standard_price, tmpl.currency_id, 1, product=tmpl,
            )['total_included']

    @api.depends('list_price', 'standard_price')
    @api.depends_context('company')
    def _compute_catalog_margin(self):
        for tmpl in self:
            tmpl.catalog_margin = tmpl.list_price - tmpl.standard_price

    def action_open_standard_form(self):
        """Open this product in the regular product form (catalog shortcut)."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'product.template',
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(self.env.ref(
                'product.product_template_only_form_view').id, 'form')],
        }
