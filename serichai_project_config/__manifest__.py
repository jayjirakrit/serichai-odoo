{
    'name': 'Serichai Project Configuration',
    'summary': 'High-value tasks first: sort task lists and boards by project value',
    'version': '1.0.0',
    'category': 'Project',
    'description': """
Task lists and boards show starred tasks first, then tasks whose "มูลค่าโครงการ" property is above
a configurable threshold, then by deadline. Adds a Project Value column and a High Value filter.
    """,
    'depends': ['project', 'product'],
    'data': [
        'data/project_contract_template.xml',
        'views/project_task_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'pre_init_hook': 'pre_init_hook',
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'author': 'Serichai Group',
    'license': 'AGPL-3',
}
