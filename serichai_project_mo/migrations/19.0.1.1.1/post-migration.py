from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Run the install-time project setup on an upgrade.

    Odoo skips `<function>` tags in noupdate data files on `-u`, so
    `data/project_project_data.xml` only does this on a fresh install. A `post-` script runs
    right after the module data is loaded, so the default mail template record already exists.
    Both calls are idempotent (a second run changes nothing).
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    Project = env['project.project']
    # the new columns are filled before the template record exists: NULL template, flag False
    Project._set_default_mo_done_mail_template()
    # projects already complete must not be notified retroactively by a later MO change
    Project._mark_completed_projects_as_notified()
