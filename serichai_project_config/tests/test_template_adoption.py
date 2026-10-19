from odoo.tests import TransactionCase, tagged

from ..hooks import _adopt_existing_records


@tagged('post_install', '-at_install')
class TestTemplateAdoption(TransactionCase):

    def test_existing_records_are_adopted(self):
        """A hand-made project/stage/template gets the shipped XML ids; nothing is duplicated."""
        data = self.env['ir.model.data']
        data.search([('module', '=', 'serichai_project_config'),
                     ('name', 'in', ['project_serichai_contract', 'project_stage_upcoming_bid',
                                     'task_template_contract'])]).unlink()
        project = self.env['project.project'].search(
            [('name', '=', 'Serichai Contract')], limit=1)
        self.assertTrue(project)
        _adopt_existing_records(self.env)
        self.assertEqual(self.env.ref('serichai_project_config.project_serichai_contract'), project)
        self.assertTrue(self.env.ref('serichai_project_config.task_template_contract').is_template)
        # idempotent
        _adopt_existing_records(self.env)
        self.assertEqual(self.env['project.project'].search_count([('name', '=', 'Serichai Contract')]), 1)
