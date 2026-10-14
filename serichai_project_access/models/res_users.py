from collections import namedtuple

from odoo import models, tools

from ._utils import norm_label

Grant = namedtuple('Grant', 'write detail stage_ids hidden')
# stage_ids: frozenset of allowed ids, None = all stages; hidden: normalised labels


def _norm(names):
    return frozenset(norm_label(n) for n in (names or '').splitlines() if n.strip())


class ResUsers(models.Model):
    _inherit = 'res.users'

    @tools.ormcache('self.id', 'self._get_group_ids()')
    def _get_project_access(self):
        """{project_id: Grant}, or None when the user is not restricted (FR-017)."""
        self.ensure_one()
        group_ids = set(self._get_group_ids())
        xmlid = self.env['ir.model.data']._xmlid_to_res_id
        if (xmlid('serichai_project_access.serichai_project_access_group_restricted',
                  raise_if_not_found=False) not in group_ids
                or xmlid('project.group_project_user') in group_ids):
            return None
        # sudo: users cannot read profiles; only the merged result leaves this method.
        lines = self.env['project.access.line'].sudo().search([
            ('profile_id.active', '=', True),
            ('profile_id.group_ids', 'in', list(group_ids))])
        grants = {}
        for line in lines:
            write = line.access_level == 'write'
            all_stages = write or not (line.stage_ids or line.stages_exhausted)
            new = Grant(write, write or line.task_access == 'detail',
                        None if all_stages else frozenset(line.stage_ids.ids),
                        frozenset() if write else _norm(line.hidden_property_names))
            for project in line.project_ids.filtered('active'):
                grants[project.id] = self._merge_grant(grants.get(project.id), new)
        return grants

    @staticmethod
    def _merge_grant(old, new):  # FR-018
        if old is None:
            return new
        stages = None if None in (old.stage_ids, new.stage_ids) else old.stage_ids | new.stage_ids
        return Grant(old.write or new.write, old.detail or new.detail, stages,
                     old.hidden & new.hidden)
