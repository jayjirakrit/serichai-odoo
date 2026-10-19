from odoo.tools.sql import column_exists, create_column


def pre_init_hook(env):
    """Create the column first so the ORM does not compute every task in one go."""
    if not column_exists(env.cr, 'project_task', 'is_high_value'):
        create_column(env.cr, 'project_task', 'is_high_value', 'boolean')


def post_init_hook(env):
    env['project.task']._recompute_high_value()
