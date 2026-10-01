# pylint: disable=pointless-statement
{
    'name': 'Serichai Project Security',
    'summary': 'Restrict a role to a read-only, filtered, list-only view of Project tasks',
    'version': '1.0.0',
    'category': 'Project',
    'description': """
Adds a restricted role ("Task List Viewer (Production Planning Only)") that can only see
project tasks in the Production Planning stage, in a list-only view with no Tags column and
no access to task forms. Projects / Reporting / Configuration menus are hidden for this role.

An administrator may pin one exception project (Settings > Project > "Task List Viewer Role"):
members of the restricted role may open the task form and edit existing tasks belonging to
that one project only. In that project the stage filter does not apply: its "Product
Development" menu opens a Kanban board with every stage of the project as a column (list and
form also available). Create/delete stay blocked everywhere, including in the pinned project.
    """,
    'depends': ['project'],
    'data': [
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'views/project_task_views.xml',
        'views/project_menus.xml',
        'views/project_task_property_access_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'author': 'Serichai Group',
    'license': 'AGPL-3',
}
