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
    """,
    'depends': ['project'],
    'data': [
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'views/project_task_views.xml',
        'views/project_menus.xml',
        'views/project_task_property_access_views.xml',
    ],
    'installable': True,
    'author': 'Serichai Group',
    'license': 'AGPL-3',
}
