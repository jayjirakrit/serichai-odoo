from odoo import models
from odoo.exceptions import AccessError

# Fields the restricted role may change on a Manufacturing Order.
RESTRICTED_WRITABLE_FIELDS = {'project_task_ids'}


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    def write(self, vals):
        """The restricted role needs write access on mrp.production only to link the order to
        project tasks (field added by serichai_project_mo). Enforce that server-side, since the
        ACL itself is per model, not per field."""
        user = self.env.user
        if (
            not self.env.su
            and user.has_group('serichai_project_security.group_project_task_list_only')
            and not user.has_group('mrp.group_mrp_user')
            and set(vals) - RESTRICTED_WRITABLE_FIELDS
        ):
            raise AccessError(self.env._(
                "You may only assign project tasks on a Manufacturing Order."
            ))
        return super().write(vals)
