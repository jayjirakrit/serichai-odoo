from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ProjectTaskPropertyAccess(models.Model):
    _name = 'project.task.property.access'
    _description = 'Task Property Group Visibility Rule'

    property_string = fields.Char(
        string='Property Label', required=True,
        help="Must match the property's displayed label (the 'string' shown in the Properties widget) exactly.",
    )
    group_ids = fields.Many2many('res.groups', string='Visible To Groups', required=True)
    active = fields.Boolean(default=True)

    _property_string_uniq = models.Constraint(
        'unique(property_string)',
        'A visibility rule already exists for this property label.',
    )

    @api.constrains('group_ids')
    def _check_group_ids(self):
        for rule in self:
            if not rule.group_ids:
                raise ValidationError(self.env._('A visibility rule must permit at least one group.'))

    def _get_restricted_strings_for_user(self, user=None):
        """Return the set of property labels ('string') that ``user`` is not
        permitted to see, per the active rules on this model.

        Uses sudo() so this can be called regardless of the caller's own
        read access to this model - the caller only learns which labels to
        hide, never the rule contents (permitted groups) themselves.
        """
        user = user or self.env.user
        rules = self.sudo().search([])
        return {
            rule.property_string
            for rule in rules
            if not (rule.group_ids & user.group_ids)
        }
