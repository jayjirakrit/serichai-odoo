from odoo import _, models
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def action_scan_barcode(self, barcode):
        """Look up ``barcode`` against product barcodes and add/increment a
        move line on this picking, mimicking the scan-to-add-line behaviour
        of the (Enterprise-only) Barcode app for a single transfer form.
        """
        self.ensure_one()
        _logger.debug("Scanning barcode: %s", barcode)
        if self.state in ('done', 'cancel'):
            raise UserError(_("This transfer is done or cancelled; it can no longer be updated by scanning."))
        product = self.env['product.product'].search([('barcode', '=', barcode)], limit=1)
        if not product:
            raise UserError(_("No product found for barcode %s") % barcode)
        if product.tracking != 'none':
            raise UserError(_(
                "%(product)s is tracked by lot/serial number. Scan-to-add is only "
                "supported for untracked products; add the line manually to set "
                "the lot/serial.",
                product=product.display_name,
            ))

        move = self.move_ids.filtered(lambda m: m.product_id == product and m.state not in ('done', 'cancel'))[:1]
        if not move:
            move = self.env['stock.move'].create({
                'picking_id': self.id,
                'product_id': product.id,
                'product_uom_qty': 0,
                'product_uom': product.uom_id.id,
                'location_id': self.location_id.id,
                'location_dest_id': self.location_dest_id.id,
            })
            if self.state not in ('draft',):
                move._action_confirm()

        move_line = move.move_line_ids[:1]
        if move_line:
            move_line.quantity += 1
            move_line.picked = True
        else:
            self.env['stock.move.line'].create({
                'move_id': move.id,
                'picking_id': self.id,
                'product_id': product.id,
                'product_uom_id': product.uom_id.id,
                'location_id': move.location_id.id,
                'location_dest_id': move.location_dest_id.id,
                'quantity': 1,
                'picked': True,
            })
        return {'product_name': product.display_name}
