# pylint: disable=pointless-statement
{
    'name': 'Serichai Project MO',
    'summary': 'Manage project management for Serichai Group',
    'version': '1.0.0',
    'description': """Allows to manage project management for Serichai Group.""",
    'depends': ['project', 'mrp'],
    'data': [
        "views/mrp_production_views.xml",
        "views/project_task_views.xml"
    ],
    'installable': True,
    'author': 'Serichai Group',
    'license': 'AGPL-3',
}
