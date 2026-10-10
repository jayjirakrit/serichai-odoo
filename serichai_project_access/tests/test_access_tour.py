from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestAccessTour(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        group = cls.env['res.groups'].create({'name': 'PA Tour Group'})
        profile = cls.env['project.access.profile'].create(
            {'name': 'PA Tour', 'group_ids': [(6, 0, group.ids)]})
        list_project, detail_project = cls.env['project.project'].create(
            [{'name': 'PA Tour List', 'privacy_visibility': 'employees'},
             {'name': 'PA Tour Detail', 'privacy_visibility': 'employees'}])
        Line = cls.env['project.access.line']
        Line.create({'profile_id': profile.id, 'project_ids': [(6, 0, list_project.ids)],
                     'access_level': 'read', 'task_access': 'list'})
        Line.create({'profile_id': profile.id, 'project_ids': [(6, 0, detail_project.ids)],
                     'access_level': 'read', 'task_access': 'detail'})
        Task = cls.env['project.task']
        Task.create([
            {'name': 'Tour Detail A', 'project_id': detail_project.id, 'sequence': 1},
            {'name': 'Tour ListOnly', 'project_id': list_project.id, 'sequence': 2},
            {'name': 'Tour Detail B', 'project_id': detail_project.id, 'sequence': 3},
        ])
        cls.env['res.users'].create({
            'name': 'PA Tour User', 'login': 'pa_tour_user', 'password': 'pa_tour_user',
            'group_ids': [(6, 0, [cls.env.ref('base.group_user').id, group.id])]})

    def test_list_tour(self):
        self.start_tour('/odoo', 'serichai_access_task_list_tour', login='pa_tour_user')

    def test_kanban_tour(self):
        self.start_tour('/odoo', 'serichai_access_task_kanban_tour', login='pa_tour_user')
