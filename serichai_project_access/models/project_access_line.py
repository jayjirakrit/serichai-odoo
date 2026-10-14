from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Command

from ._utils import norm_label
from .res_users import _norm


class ProjectAccessLine(models.Model):
    _name = 'project.access.line'
    _description = 'Project Access Line'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    profile_id = fields.Many2one('project.access.profile', required=True, ondelete='cascade',
                                 index=True)
    project_ids = fields.Many2many(
        'project.project', 'project_access_line_project_rel', 'line_id', 'project_id',
        string='Projects', required=True)
    access_level = fields.Selection(
        [('read', 'Read'), ('write', 'Write')], required=True, default='read')
    task_access = fields.Selection(
        [('list', 'List only'), ('detail', 'Open detail')],
        compute='_compute_task_access', store=True, readonly=False, default='list', required=True)
    stage_ids = fields.Many2many(
        'project.task.type', 'project_access_line_stage_rel', 'line_id', 'stage_id',
        string='Stages', help="Empty means all stages. Applies to Read lines only.")
    hidden_property_label_ids = fields.Many2many(
        'project.access.property.label', 'project_access_line_property_label_rel',
        'line_id', 'label_id', string='Hidden properties',
        help="Task properties members do not see. Applies to Read lines only.")
    hidden_property_names = fields.Text(
        compute='_compute_hidden_property_names', inverse='_inverse_hidden_property_names',
        store=True, readonly=False,
        help="One task property label per line, kept in sync with the hidden properties tags "
             "(read by the access resolver). Applies to Read lines only.")
    available_property_labels = fields.Char(compute='_compute_available_property_labels')
    stages_exhausted = fields.Boolean(
        help="All selected stages were deleted: grant no stage.")
    warning_message = fields.Text(compute='_compute_warning_message')

    @api.depends('hidden_property_label_ids.name')
    def _compute_hidden_property_names(self):
        for line in self:
            line.hidden_property_names = '\n'.join(line.hidden_property_label_ids.mapped('name')) or False

    def _inverse_hidden_property_names(self):
        Label = self.env['project.access.property.label']
        for line in self:
            names = (line.hidden_property_names or '').splitlines()
            line.hidden_property_label_ids = Label._get_or_create(names)

    @api.depends('project_ids.task_properties_definition')
    def _compute_available_property_labels(self):
        for line in self:
            labels = sorted({p['string'] for d in line.project_ids.mapped('task_properties_definition')
                             for p in d or [] if p.get('string')})
            line.available_property_labels = ', '.join(labels)

    @api.depends('project_ids', 'project_ids.privacy_visibility',
                 'project_ids.task_properties_definition', 'hidden_property_names',
                 'hidden_property_label_ids.name', 'access_level', 'stages_exhausted')
    def _compute_warning_message(self):  # FR-009
        for line in self:
            known = {norm_label(p.get('string'))
                     for d in line.project_ids.mapped('task_properties_definition')
                     for p in d or []}
            unknown = _norm(line.hidden_property_names) - known \
                if line.access_level == 'read' else ()
            blocked = line.project_ids.filtered(
                lambda p: p.privacy_visibility not in ('employees', 'portal'))
            messages = [self.env._("No property named '%s' in the selected projects.", n)
                        for n in sorted(unknown)]
            if line.stages_exhausted and line.access_level == 'read':
                messages.append(self.env._(
                    "All selected stages were deleted: members see no tasks; select stages."))
            if blocked:
                messages.append(self.env._(
                    "Visibility may block members: %s", ', '.join(blocked.mapped('name'))))
            line.warning_message = '\n'.join(messages)

    @api.depends('access_level')
    def _compute_task_access(self):  # FR-008
        for line in self.filtered(lambda l: l.access_level == 'write'):
            line.task_access = 'detail'

    @api.constrains('project_ids', 'profile_id')
    def _check_project_unique_in_profile(self):  # FR-007
        for line in self:
            dupes = line.project_ids & (line.profile_id.line_ids - line).project_ids
            if dupes:
                raise ValidationError(self.env._(
                    "%(projects)s already granted in this department.",
                    projects=', '.join(dupes.mapped('name'))))

    @api.onchange('access_level')
    def _onchange_access_level(self):
        if self.access_level == 'write':
            self.stage_ids = False
            self.hidden_property_label_ids = False

    @api.model
    def _normalize_vals(self, vals, was_write=False):
        """Write lines carry no stages, hidden properties or exhausted flag and always open
        the detail (FR-006, FR-008); moving write -> read resets task_access to list unless
        given explicitly."""
        level = vals.get('access_level', 'write' if was_write else 'read')
        if level == 'write':
            # the text mirror is recomputed from the (cleared) tags; keeping it out of vals also
            # avoids its inverse writing the tags again
            vals = {k: v for k, v in vals.items() if k != 'hidden_property_names'}
            return dict(vals, task_access='detail', stage_ids=[Command.clear()],
                        hidden_property_label_ids=[Command.clear()], stages_exhausted=False)
        if was_write and 'task_access' not in vals:
            return dict(vals, task_access='list')
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        # the field default wins over the compute at create time, so force it here (FR-008)
        vals_list = [self._normalize_vals(v) for v in vals_list]
        lines = super().create(vals_list)
        self.env.registry.clear_cache()
        return lines

    def write(self, vals):
        if 'stage_ids' in vals and 'stages_exhausted' not in vals:
            vals = dict(vals, stages_exhausted=False)  # admin re-chose stages
        writes = self.filtered(lambda l: l.access_level == 'write')
        res = True
        for lines, was_write in ((writes, True), (self - writes, False)):
            if lines:
                res = super(ProjectAccessLine, lines).write(self._normalize_vals(vals, was_write))
        self.env.registry.clear_cache()
        return res

    def unlink(self):
        res = super().unlink()
        self.env.registry.clear_cache()
        return res
