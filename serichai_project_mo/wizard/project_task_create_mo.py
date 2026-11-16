from odoo import api, fields, models


class ProjectTaskCreateMo(models.TransientModel):
    _name = 'project.task.create.mo'
    _description = 'Create Manufacturing Orders from Task'

    task_id = fields.Many2one('project.task', required=True, readonly=True, ondelete='cascade')
    user_id = fields.Many2one(
        'res.users', string="Assignee", required=True,
        default=lambda self: self.env.user if self.env.user.has_group('mrp.group_mrp_user') else False,
        # UI filter only: the server does not enforce that the assignee is an MRP user (like core)
        domain=lambda self: [('all_group_ids', 'in', self.env.ref('mrp.group_mrp_user').id)])
    warning = fields.Text(compute='_compute_warning')

    @api.depends('task_id.finish_goods_ids')
    def _compute_warning(self):
        for wizard in self:
            products = wizard.task_id.finish_goods_ids
            # sudo: project users may lack mrp.bom read access; only product names are exposed
            boms = self.env['mrp.bom'].sudo()._bom_find(products)
            missing = products.filtered(lambda p: not boms.get(p))
            wizard.warning = self.env._(
                "No bill of materials for: %s. Their MOs will have no components.",
                ", ".join(missing.mapped('display_name')),
            ) if missing else False

    def action_confirm(self):
        self.ensure_one()
        mos = self.task_id._create_mos_from_finish_goods(self.user_id)
        if not mos:
            return self._notification(
                'info', self.env._("Nothing new to create: every Finish Goods product already has an MO."))
        title = self.env._("%s Manufacturing Orders created", len(mos))
        if not self.env['mrp.production'].has_access('read'):
            # the MO list would raise an AccessError for this user
            return self._notification('success', title)
        action = self.env['ir.actions.act_window']._for_xml_id('mrp.mrp_production_action')
        action.update(name=title, domain=[('project_task_ids', 'in', self.task_id.ids)])
        return action

    def _notification(self, notification_type, message):
        """Client action showing a toast, then closing the wizard."""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': notification_type,
                'message': message,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
