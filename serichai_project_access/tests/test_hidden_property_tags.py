import importlib.util
import os

from psycopg2 import IntegrityError

from odoo.exceptions import AccessError
from odoo.tests import new_test_user, tagged
from odoo.tools import mute_logger

from .common import AccessCase


@tagged('post_install', '-at_install')
class TestHiddenPropertyTags(AccessCase):
    """Part B of the user report: hidden properties are chosen as tags; the text field the
    resolver reads stays in sync both ways."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Label = cls.env['project.access.property.label']
        cls.p_read.task_properties_definition = [
            {'name': 'prop_a', 'string': 'Public', 'type': 'char'},
            {'name': 'prop_b', 'string': 'Secret Cost', 'type': 'char'}]

    def test_tags_drive_text_and_resolver(self):
        labels = self.Label.create([{'name': 'Secret Cost'}, {'name': 'ต้นทุน'}])
        self.line_read.hidden_property_label_ids = labels
        self.assertEqual(set(self.line_read.hidden_property_names.splitlines()),
                         {'Secret Cost', 'ต้นทุน'})
        self.assertEqual(self.user._get_project_access()[self.p_read.id].hidden,
                         frozenset({'secret cost', 'ต้นทุน'}))
        self.line_read.hidden_property_label_ids = labels[:1]
        self.assertEqual(self.user._get_project_access()[self.p_read.id].hidden,
                         frozenset({'secret cost'}))

    def test_text_fills_tags_reusing_labels(self):
        existing = self.Label.create({'name': 'Secret Cost'})
        self.line_read.hidden_property_names = ' secret   COST \n\nNew One\nnew one'
        self.assertEqual(len(self.line_read.hidden_property_label_ids), 2)
        self.assertIn(existing, self.line_read.hidden_property_label_ids)
        self.assertEqual(self.Label.search_count([('name_norm', '=', 'new one')]), 1)

    def test_name_create_reuses_and_unique(self):
        label = self.Label.create({'name': 'Cost'})
        self.assertEqual(self.Label.name_create('  COST ')[0], label.id)
        with self.assertRaises(IntegrityError), mute_logger('odoo.sql_db'), self.cr.savepoint():
            self.Label.create({'name': 'cost'})

    def test_rename_label_refreshes_resolver(self):
        label = self.Label.create({'name': 'Old'})
        self.line_read.hidden_property_label_ids = label
        self.assertEqual(self.user._get_project_access()[self.p_read.id].hidden, frozenset({'old'}))
        label.name = 'New'
        self.assertEqual(self.line_read.hidden_property_names, 'New')
        self.assertEqual(self.user._get_project_access()[self.p_read.id].hidden, frozenset({'new'}))

    def test_write_line_clears_tags(self):
        self.line_read.hidden_property_label_ids = self.Label.create({'name': 'X'})
        self.line_read.access_level = 'write'
        self.assertFalse(self.line_read.hidden_property_label_ids)
        self.assertFalse(self.line_read.hidden_property_names)
        line = self.env['project.access.line'].create({
            'profile_id': self.profile.id, 'project_ids': [(6, 0, self.p_none.ids)],
            'access_level': 'write', 'hidden_property_label_ids': [(0, 0, {'name': 'Y'})],
            'hidden_property_names': 'Z'})
        self.assertFalse(line.hidden_property_label_ids or line.hidden_property_names)

    def test_warning_and_suggestions_use_tags(self):
        self.line_read.hidden_property_label_ids = self.Label.create(
            [{'name': 'Secret  cost'}, {'name': 'Missing'}])
        self.assertIn("'missing'", self.line_read.warning_message)
        self.assertNotIn("'secret cost'", self.line_read.warning_message)
        self.assertEqual(self.line_read.available_property_labels, 'Public, Secret Cost')

    def test_manager_acl(self):
        manager = new_test_user(self.env, login='pa_tag_mgr', groups='project.group_project_manager')
        label = self.Label.with_user(manager).create({'name': 'Mgr'})
        label.write({'name': 'Mgr2'})
        label.unlink()
        with self.assertRaises(AccessError):
            self.Label.with_user(self.user).create({'name': 'Nope'})

    def test_migration_text_to_tags(self):
        path = os.path.join(os.path.dirname(__file__), '..', 'migrations', '1.1.0', 'post-migration.py')
        spec = importlib.util.spec_from_file_location('pa_post_migration', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # state of a database installed before the tags existed: text only, no tags
        self.line_read.hidden_property_label_ids = False
        self.env.flush_all()
        self.cr.execute("UPDATE project_access_line SET hidden_property_names = %s WHERE id = %s",
                        [' Secret Cost \n\nต้นทุน', self.line_read.id])
        self.env.invalidate_all()
        module.migrate(self.cr, '1.0.0')
        self.env.invalidate_all()
        self.assertEqual(set(self.line_read.hidden_property_label_ids.mapped('name')),
                         {'Secret Cost', 'ต้นทุน'})
        self.assertEqual(self.user._get_project_access()[self.p_read.id].hidden,
                         frozenset({'secret cost', 'ต้นทุน'}))

    def test_delete_label_updates_lines_text_and_resolver(self):
        keep, gone = self.Label.create([{'name': 'Secret Cost'}, {'name': 'Gone'}])
        self.line_read.hidden_property_label_ids = keep | gone
        self.assertEqual(gone.line_count, 1)
        self.assertEqual(self.user._get_project_access()[self.p_read.id].hidden,
                         frozenset({'secret cost', 'gone'}))
        gone.unlink()
        self.assertEqual(self.line_read.hidden_property_label_ids, keep)
        self.assertEqual(self.line_read.hidden_property_names, 'Secret Cost')
        self.assertEqual(self.user._get_project_access()[self.p_read.id].hidden,
                         frozenset({'secret cost'}))
        keep.unlink()
        self.assertFalse(self.line_read.hidden_property_names)
        self.assertFalse(self.user._get_project_access()[self.p_read.id].hidden)

    def test_unused_label_line_count_and_rename(self):
        used, unused = self.Label.create([{'name': 'Used'}, {'name': 'Unused'}])
        self.line_read.hidden_property_label_ids = used
        self.assertEqual((used | unused).mapped('line_count'), [1, 0])
        used.name = '  Renamed   Used '
        self.assertEqual(self.line_read.hidden_property_names, 'Renamed Used')
        self.assertEqual(self.user._get_project_access()[self.p_read.id].hidden,
                         frozenset({'renamed used'}))

    def test_label_management_refused_to_non_managers(self):
        label = self.Label.create({'name': 'Keep'})
        self.line_read.hidden_property_label_ids = label
        for op in (lambda l: l.write({'name': 'Hack'}), lambda l: l.unlink()):
            with self.assertRaises(AccessError):
                op(label.with_user(self.user))
        self.assertEqual(self.line_read.hidden_property_names, 'Keep')

    def test_label_menu_only_for_managers(self):
        manager = new_test_user(self.env, login='pa_lbl_mgr', groups='project.group_project_manager')
        officer = new_test_user(self.env, login='pa_lbl_pu', groups='project.group_project_user')
        xmlid = 'serichai_project_access.project_access_property_label_menu'
        menu = self.env.ref(xmlid)

        def visible(user):
            data = self.env['ir.ui.menu'].with_user(user).with_context(lang='en_US').load_menus(False)
            return xmlid in {m.get('xmlid') for m in data.values()}
        self.assertTrue(visible(manager))
        self.assertFalse(visible(officer))
        self.assertFalse(visible(self.user))
        self.assertEqual(menu.action.res_model, 'project.access.property.label')
