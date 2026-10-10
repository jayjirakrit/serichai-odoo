from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Command


class ProjectAccessProfile(models.Model):
    _name = 'project.access.profile'
    _description = 'Project Access Group'
    _order = 'name, id'

    name = fields.Char(string='Department', required=True)
    active = fields.Boolean(default=True)
    group_ids = fields.Many2many(
        'res.groups', 'project_access_profile_group_rel', 'profile_id', 'group_id',
        string='Groups', required=True)
    line_ids = fields.One2many('project.access.line', 'profile_id', string='Access Lines', copy=True)
    user_ids = fields.Many2many('res.users', string='Users', compute='_compute_user_ids')
    project_ids = fields.Many2many('project.project', string='Projects',
                                   compute='_compute_project_ids')

    @api.depends('group_ids')
    def _compute_user_ids(self):
        for profile in self:
            # sudo: project managers cannot read all groups' members; shown read-only.
            profile.user_ids = profile.group_ids.sudo().all_user_ids

    @api.depends('line_ids.project_ids')
    def _compute_project_ids(self):
        for profile in self:
            profile.project_ids = profile.line_ids.project_ids

    @api.model
    def _forbidden_groups(self):
        refs = ['base.group_user', 'base.group_portal', 'base.group_public',
                'base.group_system', 'project.group_project_user',
                'project.group_project_manager']
        groups = self.env['res.groups']
        for ref in refs:
            groups |= self.env.ref(ref, raise_if_not_found=False) or groups.browse()
        return groups

    @api.constrains('group_ids')
    def _check_group_ids(self):
        forbidden = self._forbidden_groups()
        # base.group_user is implied by nearly every internal group (including the control
        # group), so only a group *being* it is rejected; the others are rejected transitively.
        base_user = self.env.ref('base.group_user', raise_if_not_found=False) or forbidden.browse()
        for profile in self:
            groups = profile.group_ids
            if groups & forbidden or groups.all_implied_ids & (forbidden - base_user):
                raise ValidationError(self.env._("This group cannot define a department."))

    @api.model
    def _sync_restricted_group(self, affected):
        """Link/unlink the control group on ``affected`` department groups only (the groups of
        the created, changed or deleted profiles); groups linked by other means are untouched."""
        # sudo: project managers cannot write res.groups; only the control group is linked to or
        # unlinked from implied_ids of the affected department groups, nothing else is touched.
        restricted = self.env.ref('serichai_project_access.serichai_project_access_group_restricted')
        wanted = self.sudo().search([]).group_ids  # active profiles only
        affected = affected.sudo() - restricted
        (affected & wanted).filtered(lambda g: restricted not in g.implied_ids).write(
            {'implied_ids': [Command.link(restricted.id)]})
        (affected - wanted).filtered(lambda g: restricted in g.implied_ids).write(
            {'implied_ids': [Command.unlink(restricted.id)]})

    def _after_change(self, previous_groups):
        self._sync_restricted_group(previous_groups | self.exists().with_context(active_test=False).group_ids)
        self.env.registry.clear_cache()

    @api.model_create_multi
    def create(self, vals_list):
        profiles = super().create(vals_list)
        profiles._after_change(self.env['res.groups'])
        return profiles

    def write(self, vals):
        sync = 'group_ids' in vals or 'active' in vals
        previous = self.with_context(active_test=False).group_ids if sync else self.env['res.groups']
        res = super().write(vals)
        if sync:
            self._after_change(previous)
        return res

    def unlink(self):
        previous = self.with_context(active_test=False).group_ids
        res = super().unlink()
        self._after_change(previous)
        return res
