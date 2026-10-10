from odoo import models


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    def _load_menus_blacklist(self):
        res = super()._load_menus_blacklist()
        all_tasks = self.env.ref('serichai_project_access.menu_task_all_access', raise_if_not_found=False)
        project = self.env.ref('serichai_project_access.menu_project_access', raise_if_not_found=False)
        own = (all_tasks or self.env['ir.ui.menu']) | (project or self.env['ir.ui.menu'])
        root = self.env.ref('project.menu_main_pm', raise_if_not_found=False)
        if self.env.user._get_project_access() is None:
            # Unrestricted users (incl. Project users who are also in a department) keep the
            # standard Project menus only.
            return res + own.ids
        if not root:
            return res
        # sudo: the whole Project menu tree must be listed to blacklist it, whatever the
        # user's own menu visibility; only ids leave this method.
        others = self.sudo().with_context(active_test=False).search(
            [('id', 'child_of', root.id)]) - root - own
        return res + others.ids
