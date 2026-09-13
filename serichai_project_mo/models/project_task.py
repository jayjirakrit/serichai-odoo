from odoo import models, fields, api
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

    @api.depends('mrp_production_ids')
    def _compute_mrp_production_count(self):
        for task in self:
            task.mrp_production_count = len(task.mrp_production_ids)

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
