from odoo import Command, api, fields, models
from odoo.exceptions import LockError, UserError
from odoo.tools import format_date, format_datetime, formatLang, html2plaintext


REPORT_TASK_PROPERTY_LABELS = {
    'เลขที่สัญญา',
    'จำนวน',
    'ระยะส่ง',
    'วันที่ลงนาม',
    'วันหมดสัญญา',
    'ยื่นในนาม',
    'หน่วยงาน',
}


class ProjectTask(models.Model):
    _inherit = 'project.task'

    mrp_production_ids = fields.Many2many('mrp.production', 'project_task_mrp_production_rel', 'project_task_id', 'mrp_production_id', string='Manufacturing Orders')
    mrp_production_count = fields.Integer(string='MO Count', compute='_compute_mrp_production_count',)
    finish_goods_ids = fields.Many2many(
        'product.product', 'project_task_finish_goods_rel', 'project_task_id', 'product_id',
        string='Finish Goods', domain="[('type', '=', 'consu')]", copy=False)

    @api.depends('mrp_production_ids')
    def _compute_mrp_production_count(self):
        for task in self:
            task.mrp_production_count = len(task.mrp_production_ids)

    def action_view_mrp_productions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._("Manufacturing Orders"),
            'res_model': 'mrp.production',
            'view_mode': 'list,form',
            'domain': [('project_task_ids', 'in', self.ids)],
        }

    def action_open_create_mo_wizard(self):
        self.ensure_one()
        self._check_can_create_mos()
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._("Create Manufacturing Orders"),
            'res_model': 'project.task.create.mo',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_task_id': self.id},
        }

    def _check_can_create_mos(self):
        self.ensure_one()
        self.check_access('write')  # real user: ACL + record rules
        if not self.finish_goods_ids:
            raise UserError(self.env._("Add at least one Finish Goods product first."))
        if not self.project_id:
            raise UserError(self.env._("Set a project on the task before creating Manufacturing Orders."))

    def _create_mos_from_finish_goods(self, user):
        """Create one draft MO per uncovered Finish Goods product; return the new MOs."""
        self._check_can_create_mos()
        try:
            self.lock_for_update(allow_referencing=True)
        except LockError:
            raise UserError(self.env._("Manufacturing Orders are being created for this task. Try again."))
        self.invalidate_recordset(['mrp_production_ids'])
        # sudo: no custom group may create mrp.production; access to the task was checked above.
        # sudo() keeps the uid, so create_uid is the real user; user_id is the chosen assignee.
        task = self.sudo()
        covered = task.mrp_production_ids.filtered(lambda mo: mo.state != 'cancel').product_id
        todo = task.finish_goods_ids - covered
        mos = task.env['mrp.production'].create([{
            'product_id': product.id,
            'user_id': user.id,
            'project_id': task.project_id.id,
            'origin': task.name,
        } for product in todo])
        # Writing the task row makes a stale-snapshot concurrent confirm fail and be retried
        task.write({'mrp_production_ids': [Command.link(mo.id) for mo in mos]})
        return mos

    def _get_report_task_properties(self):
        """Return the task's properties for the Contract MO report, as a list of
        ``{'string': label, 'value': printable text}`` dicts.

        Reading ``task_properties`` merges the values stored on the task with the
        definition held by its project, so only properties that still exist in
        that definition come back - a property whose definition was removed (or
        that the user is not allowed to see, per ``serichai_project_security``)
        is simply skipped instead of being printed. Separators carry no value
        and are skipped too. The report only prints the fixed set of contract
        fields in ``REPORT_TASK_PROPERTY_LABELS`` (matched by property label);
        any other property defined on the project is left off the report.
        """
        self.ensure_one()
        properties = self.read(['task_properties'])[0].get('task_properties') or []
        return [
            {'string': prop['string'], 'value': self._format_report_property_value(prop)}
            for prop in properties
            if prop.get('string') and prop.get('type') != 'separator'
            and prop['string'] in REPORT_TASK_PROPERTY_LABELS
        ]

    def _format_report_property_value(self, prop):
        """Render a single property's value as printable text.

        An unset property prints blank (the label still shows, like the blank
        fields on the paper form).
        """
        value = prop.get('value')
        prop_type = prop.get('type')
        # ``value is False`` rather than ``not value`` so that 0 still prints
        if value is None or value is False or value == '':
            return ''
        if prop_type == 'boolean':
            return '✓'
        if prop_type == 'many2one':
            return value[1] or '' if isinstance(value, (list, tuple)) else ''
        if prop_type == 'many2many':
            return ', '.join(name for __, name in value if name)
        if prop_type == 'selection':
            return dict(prop.get('selection') or []).get(value) or ''
        if prop_type == 'tags':
            labels = {tag[0]: tag[1] for tag in prop.get('tags') or []}
            return ', '.join(labels[tag] for tag in value if tag in labels)
        if prop_type == 'date':
            return format_date(self.env, value)
        if prop_type == 'datetime':
            return format_datetime(self.env, value)
        if prop_type in ('float', 'monetary'):
            return formatLang(self.env, value)
        if prop_type == 'html':
            return html2plaintext(value)
        return str(value)
