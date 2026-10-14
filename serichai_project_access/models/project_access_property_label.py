from odoo import api, fields, models

from ._utils import norm_label


class ProjectAccessPropertyLabel(models.Model):
    """A task property label that access lines can hide. Shown as a tag on the line; the text
    field ``hidden_property_names`` of the line mirrors the tags for the resolver."""
    _name = 'project.access.property.label'
    _description = 'Hidden Task Property Label'
    _order = 'name, id'

    name = fields.Char(string='Property label', required=True)
    line_count = fields.Integer(string='Used in lines', compute='_compute_line_count')
    name_norm = fields.Char(compute='_compute_name_norm', store=True, index=True)

    _name_norm_unique = models.Constraint(
        'unique(name_norm)', "This property label already exists.")

    def _compute_line_count(self):
        counts = {}
        if self.ids:
            groups = self.env['project.access.line']._read_group(
                [('hidden_property_label_ids', 'in', self.ids)],
                ['hidden_property_label_ids'], ['__count'])
            counts = {label.id: count for label, count in groups}
        for label in self:
            label.line_count = counts.get(label.id, 0)

    @api.depends('name')
    def _compute_name_norm(self):
        for label in self:
            label.name_norm = norm_label(label.name)

    @api.model
    def _get_or_create(self, names):
        """Labels for ``names`` (matched by normalised form); missing ones are created."""
        labels = self.browse()
        seen = set()
        for name in names:
            key = norm_label(name)
            if not key or key in seen:
                continue
            seen.add(key)
            label = self.search([('name_norm', '=', key)], limit=1)
            labels |= label or self.create({'name': ' '.join(name.split())})
        return labels

    @api.model
    def name_create(self, name):
        # quick create from the tags input: reuse the label when it exists (case, spaces)
        label = self._get_or_create([name])
        return label.id, label.display_name

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [dict(v, name=' '.join(v['name'].split())) if v.get('name') else v
                     for v in vals_list]
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('name'):
            vals = dict(vals, name=' '.join(vals['name'].split()))
        res = super().write(vals)
        if 'name' in vals:  # the resolver caches the labels of the lines
            self.env.registry.clear_cache()
        return res

    def unlink(self):
        # the m2m rows cascade in SQL: refresh the text mirror of the lines that used the labels
        lines = self.env['project.access.line'].search(
            [('hidden_property_label_ids', 'in', self.ids)])
        res = super().unlink()
        lines.invalidate_recordset(['hidden_property_label_ids'])
        self.env.add_to_compute(lines._fields['hidden_property_names'], lines)
        self.env.registry.clear_cache()
        return res
