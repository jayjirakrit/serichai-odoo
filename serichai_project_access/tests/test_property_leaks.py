import json

from odoo.exceptions import AccessError
from odoo.tests import tagged

from .common import AccessCase

# What the web client sends for the restricted All Tasks list / kanban / form (spec 009):
# the properties field plus the project co-record with its properties definition.
SPEC = {
    'name': {},
    'task_properties': {},
    'project_id': {'fields': {'display_name': {}, 'task_properties_definition': {}}},
}
LABEL = 'Secret Cost'
THAI = 'ต้นทุน ลับ'


@tagged('post_install', '-at_install')
class TestPropertyLeaks(AccessCase):
    """Part A of the user report: a hidden property must not leak, neither its values nor its
    label/definition, through any RPC a restricted user can reach."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        definition = [
            {'name': 'prop_a', 'string': 'Public', 'type': 'char'},
            {'name': 'prop_b', 'string': LABEL, 'type': 'char'},
            {'name': 'prop_c', 'string': THAI, 'type': 'char'},
        ]
        (cls.p_read | cls.p_write).task_properties_definition = definition
        for task in (cls.t_read1, cls.t_read2, cls.t_write):
            task.task_properties = {'prop_a': 'visible', 'prop_b': '4242', 'prop_c': '9191'}
        cls.line_read.hidden_property_names = '  secret   COST \n %s' % THAI

    def _assert_clean(self, data):
        dump = json.dumps(data, ensure_ascii=False)
        for leak in ('prop_b', 'prop_c', LABEL, THAI, '4242', '9191'):
            self.assertNotIn(leak, dump)
        self.assertIn('Public', dump)

    def test_web_search_read_list(self):
        res = self.as_user().web_search_read([('project_id', '=', self.p_read.id)], SPEC)
        self.assertEqual(len(res['records']), 2)
        self._assert_clean(res)

    def test_web_read_form(self):
        self._assert_clean(self.t_read1.with_user(self.user).web_read(SPEC))

    def test_project_definition_direct(self):
        project = self.p_read.with_user(self.user)
        self._assert_clean(project.read(['task_properties_definition']))
        self._assert_clean(project.web_read({'task_properties_definition': {}}))
        self._assert_clean(self.env['project.project'].with_user(self.user).web_search_read(
            [('id', '=', self.p_read.id)], {'task_properties_definition': {}}))

    def test_write_project_and_unrestricted_keep_all(self):
        full = self.p_write.with_user(self.user).read(['task_properties_definition'])
        self.assertEqual({d['string'] for d in full[0]['task_properties_definition']},
                         {'Public', LABEL, THAI})
        admin = self.env.ref('base.user_admin')
        full = self.p_read.with_user(admin).read(['task_properties_definition'])
        self.assertEqual(len(full[0]['task_properties_definition']), 3)

    def test_merged_departments_intersection(self):
        group2 = self.env['res.groups'].create({'name': 'PA G2 leaks'})
        profile2 = self.env['project.access.profile'].create(
            {'name': 'PA D2 leaks', 'group_ids': [(6, 0, group2.ids)]})
        self.env['project.access.line'].create({
            'profile_id': profile2.id, 'project_ids': [(6, 0, self.p_read.ids)]})
        self.user.group_ids = [(4, group2.id)]
        labels = {d['string'] for d in self.p_read.with_user(self.user).read(
            ['task_properties_definition'])[0]['task_properties_definition']}
        self.assertEqual(labels, {'Public', LABEL, THAI})

    def test_label_matching_space_case_thai(self):
        # trimming, inner whitespace and case are ignored; Thai is matched as typed
        grants = self.user._get_project_access()
        self.assertEqual(len(grants[self.p_read.id].hidden), 2)
        res = self.t_read1.with_user(self.user).read(['task_properties'])
        self.assertEqual({p['string'] for p in res[0]['task_properties']}, {'Public'})

    def test_group_by_and_search_on_hidden_property(self):
        Task = self.as_user()
        with self.assertRaises(AccessError):
            Task.web_read_group([], ['task_properties.prop_b'], ['__count'])
        with self.assertRaises(AccessError):
            Task.search([('task_properties.prop_b', '=', '4242')])
        with self.assertRaises(AccessError):
            Task.search_count([('task_properties.prop_c', 'ilike', '9')])
        with self.assertRaises(AccessError):
            Task.search([], order='task_properties.prop_b')
        # a visible property still works
        self.assertEqual(Task.search_count([('task_properties.prop_a', '=', 'visible')]), 3)
        Task.web_read_group([], ['task_properties.prop_a'], ['__count'])
        # the unrestricted user is not affected
        admin_task = self.env['project.task'].with_user(self.env.ref('base.user_admin'))
        self.assertTrue(admin_task.search_count([('task_properties.prop_b', '=', '4242')]))

    def test_get_property_definition(self):
        Task = self.as_user()
        self.assertEqual(Task.get_property_definition('task_properties.prop_b'), {})
        self.assertEqual(Task.get_property_definition('task_properties.prop_a')['string'], 'Public')

    def test_export_hidden_property(self):
        self.user.group_ids = [(4, self.env.ref('base.group_allow_export').id)]
        with self.assertRaises(AccessError):
            self.t_read1.with_user(self.user).export_data(['name', 'task_properties'])
        self.assertTrue(self.t_read1.with_user(self.user).export_data(['name']))
