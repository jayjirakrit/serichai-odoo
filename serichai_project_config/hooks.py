from odoo.tools.sql import column_exists, create_column


# (xml_id, model, domain) of the records shipped in data/project_contract_template.xml.
# An existing record created by hand is adopted instead of duplicated.
ADOPTED_RECORDS = [
    ('project_serichai_contract', 'project.project', [('name', '=', 'Serichai Contract')]),
    ('project_stage_upcoming_bid', 'project.task.type', [('name', '=', 'กำลังจะประมูล')]),
    ('task_template_contract', 'project.task',
     [('name', '=', 'Template Contract'), ('is_template', '=', True)]),
]


def _adopt_existing_records(env):
    """Give hand-made records the XML ids the data file uses, so install does not duplicate them."""
    for xml_id, model, domain in ADOPTED_RECORDS:
        if env['ir.model.data'].search_count(
                [('module', '=', 'serichai_project_config'), ('name', '=', xml_id)]):
            continue
        record = env[model].with_context(active_test=False).search(domain, limit=1, order='id')
        if record:
            env['ir.model.data'].create({
                'module': 'serichai_project_config',
                'name': xml_id,
                'model': model,
                'res_id': record.id,
                'noupdate': True,
            })


def pre_init_hook(env):
    """Create the column first so the ORM does not compute every task in one go."""
    _adopt_existing_records(env)
    if not column_exists(env.cr, 'project_task', 'is_high_value'):
        create_column(env.cr, 'project_task', 'is_high_value', 'boolean')


def post_init_hook(env):
    env['project.task']._recompute_high_value()
