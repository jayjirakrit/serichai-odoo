import logging

from odoo.fields import Command

_logger = logging.getLogger(__name__)

OLD = 'serichai_project_security'
MIGRATED_NAME = 'Production Planning (migrated)'
GROUP_XMLID = 'group_production_planning'
# Stage names of the old role's rule (serichai_project_security/security/ir_rule.xml)
STAGES = ['วางแผนการผลิต', 'กำลังผลิตสินค้า', 'เตรียมส่งสินค้า', 'เสร็จสิ้น']

# Core values of the menus the old module rewrote; the old module's uninstall does not revert
# them (FR-025), so the hook puts them back. menu_main_pm additionally keeps the restricted
# control group this module adds.
CORE_MENU_GROUPS = {
    'project.menu_main_pm': ['project.group_project_manager', 'project.group_project_user',
                             'serichai_project_access.serichai_project_access_group_restricted'],
    'project.menu_projects_group_stage': ['project.group_project_stages'],
    'project.menu_projects': [],
    'project.menu_project_report': [],
    'project.menu_project_management': [],
    'project.menu_project_management_all_tasks': [],
}


def post_init_hook(env):
    """Migrate serichai_project_security (spec 009 FR-023..FR-026). Idempotent: does nothing on
    a fresh install (old module absent) or when the migrated profile already exists."""
    old_group = env.ref(f'{OLD}.group_project_task_list_only', raise_if_not_found=False)
    Profile = env['project.access.profile'].with_context(active_test=False)
    if not old_group or Profile.search_count([('name', '=', MIGRATED_NAME)]):
        return
    group = _get_or_create_group(env)
    # sudo: ir.config_parameter is admin-only; reading the old module's pinned project id is harmless.
    pinned = int(env['ir.config_parameter'].sudo().get_param(
        f'{OLD}.expanded_access_project_id', 0) or 0)
    pinned = env['project.project'].browse(pinned).exists().id if pinned else False
    projects = env['project.project'].search(
        [('is_template', '=', False), ('id', '!=', pinned or 0)])
    stages = env['project.task.type'].search([('name', 'in', STAGES)])
    missing = set(STAGES) - set(stages.mapped('name'))
    if missing:
        _logger.warning("Migration: production stages not found: %s", ', '.join(sorted(missing)))
    hidden = []
    if 'project.task.property.access' in env:
        # sudo: migration reads the old module's configuration regardless of the installer.
        rules = env['project.task.property.access'].sudo().search([])
        hidden = sorted({r.property_string for r in rules if old_group not in r.group_ids})
    lines = []
    if projects:
        lines.append(Command.create({
            'project_ids': [Command.set(projects.ids)], 'access_level': 'read',
            'task_access': 'list', 'stage_ids': [Command.set(stages.ids)],
            'stages_exhausted': not stages, 'hidden_property_names': '\n'.join(hidden)}))
    if pinned:
        lines.append(Command.create({
            'project_ids': [Command.set([pinned])], 'access_level': 'write'}))
    Profile.create({'name': MIGRATED_NAME, 'group_ids': [Command.set(group.ids)],
                    'line_ids': lines})
    # sudo: moving users between groups needs user administration rights.
    users = env['res.users'].sudo().with_context(active_test=False).search(
        [('all_group_ids', 'in', old_group.id)])
    users.write({'group_ids': [Command.link(group.id)]})
    _restore_core_menu_groups(env)
    env.registry.clear_cache()
    _logger.info("Migration: %d user(s) moved to %s, %d project(s) granted read-only",
                 len(users), MIGRATED_NAME, len(projects))


def _get_or_create_group(env):
    group = env.ref(f'serichai_project_access.{GROUP_XMLID}', raise_if_not_found=False)
    if group:
        return group
    # sudo: creating a group needs administration rights; the migration may run as any installer.
    group = env['res.groups'].sudo().create({
        'name': 'Production Planning',
        'privilege_id': env.ref('project.res_groups_privilege_project').id,
        'implied_ids': [Command.link(env.ref('base.group_user').id)],
        'comment': 'Created by the migration from serichai_project_security.',
    })
    # sudo: ir.model.data is admin-only; registers the xmlid so the group is a normal module record.
    env['ir.model.data'].sudo().create({
        'module': 'serichai_project_access', 'name': GROUP_XMLID,
        'model': 'res.groups', 'res_id': group.id, 'noupdate': True})
    return group


def _restore_core_menu_groups(env):
    for menu_xmlid, group_xmlids in CORE_MENU_GROUPS.items():
        menu = env.ref(menu_xmlid, raise_if_not_found=False)
        if not menu:
            continue
        groups = env['res.groups'].browse()
        for xmlid in group_xmlids:
            groups |= env.ref(xmlid, raise_if_not_found=False) or groups.browse()
        # sudo: ir.ui.menu is only writable by administrators.
        menu.sudo().write({'group_ids': [Command.set(groups.ids)]})
