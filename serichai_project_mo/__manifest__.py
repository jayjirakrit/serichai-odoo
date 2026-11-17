# pylint: disable=pointless-statement
{
    'name': 'Serichai Project MO',
    'summary': 'Manage project management for Serichai Group',
    'version': '1.1.1',
    'description': """Allows to manage project management for Serichai Group.""",
    'depends': ['project', 'mrp', 'project_mrp', 'mail'],
    'data': [
        "security/ir.model.access.csv",
        "data/project_project_data.xml",
        "views/mrp_production_views.xml",
        "views/project_task_views.xml",
        "views/project_project_views.xml",
        "wizard/project_task_create_mo_views.xml",
        "report/project_task_report_views.xml",
        "report/project_task_report_templates.xml"
    ],
    'assets': {
        'web.assets_backend': [
            'serichai_project_mo/static/src/js/many2many_tags_open.js',
        ],
    },
    'installable': True,
    'author': 'Serichai Group',
    'license': 'AGPL-3',
}
