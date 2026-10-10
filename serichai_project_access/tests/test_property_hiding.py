from unittest.mock import patch

from odoo.tests import tagged

from ..models.res_users import Grant, ResUsers

from .common import AccessCase


@tagged('post_install', '-at_install')
class TestPropertyHiding(AccessCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        definition = [
            {'name': 'prop_a', 'string': 'Public', 'type': 'char'},
            {'name': 'prop_b', 'string': 'Secret Cost', 'type': 'char'},
        ]
        (cls.p_read | cls.p_write).task_properties_definition = definition
        for task in (cls.t_read1, cls.t_write):
            task.task_properties = {'prop_a': 'visible', 'prop_b': '42'}
        cls.line_read.hidden_property_names = '  secret cost \n'

    def _names(self, task, user):
        return {p['string'] for p in task.with_user(user).read(['task_properties'])[0]['task_properties']}

    def test_hidden_for_read(self):
        self.assertEqual(self._names(self.t_read1, self.user), {'Public'})

    def test_web_read_hidden(self):
        vals = self.t_read1.with_user(self.user).web_read({'task_properties': {}})[0]
        self.assertEqual({p['string'] for p in vals['task_properties']}, {'Public'})

    def test_present_for_write_and_unrestricted(self):
        self.assertEqual(self._names(self.t_write, self.user), {'Public', 'Secret Cost'})
        self.assertEqual(self._names(self.t_read1, self.env.ref('base.user_admin')),
                         {'Public', 'Secret Cost'})

    def test_other_department_intersection(self):
        group2 = self.env['res.groups'].create({'name': 'PA G2'})
        profile2 = self.env['project.access.profile'].create(
            {'name': 'PA D2', 'group_ids': [(6, 0, group2.ids)]})
        self.env['project.access.line'].create({
            'profile_id': profile2.id, 'project_ids': [(6, 0, self.p_read.ids)],
            'hidden_property_names': 'Other'})
        self.user.group_ids = [(4, group2.id)]
        self.assertEqual(self._names(self.t_read1, self.user), {'Public', 'Secret Cost'})

    def test_stored_value_survives_write(self):
        # A Read grant never allows writing (the rules refuse it), so exercise the defensive
        # merge with a grant that is writable and still hides a property (research D7).
        grant = Grant(True, True, None, frozenset({'secret cost'}))
        with patch.object(ResUsers, '_get_project_access',
                          lambda self: {p.id: grant for p in self.env['project.project'].sudo().search([])}):
            self.t_read1.with_user(self.user).write(
                {'task_properties': [{'name': 'prop_a', 'string': 'Public', 'type': 'char',
                                      'value': 'changed'}]})
        props = self.t_read1.sudo().task_properties
        self.assertEqual(props['prop_a'], 'changed')
        self.assertEqual(props['prop_b'], '42')
