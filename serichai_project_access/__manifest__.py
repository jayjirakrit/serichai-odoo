# pylint: disable=pointless-statement
{
    'name': 'Serichai Project Access',
    'summary': 'Configurable per-department access to projects, stages and task properties',
    'version': '1.1.0',
    'category': 'Project',
    'description': """
Project managers define "Project Access Groups": a department (one or more user groups)
and, per line, which projects its members can reach, read-only or read/write, optionally
limited to some stages and with some task properties hidden.
    """,
    'depends': ['project'],
    'data': [
        'security/serichai_project_access_groups.xml',
        'security/ir.model.access.csv',
        'security/project_project_security.xml',
        'security/project_task_security.xml',
        'views/project_access_profile_views.xml',
        'views/project_access_property_label_views.xml',
        'views/project_task_views.xml',
        'views/project_project_views.xml',
        'views/project_access_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'serichai_project_access/static/src/views/*.js',
        ],
        'web.assets_tests': [
            'serichai_project_access/static/tests/tours/*.js',
        ],
    },
    # 'post_init_hook': 'post_init_hook',
    'installable': True,
    'author': 'Serichai Group',
    'license': 'AGPL-3',
}
