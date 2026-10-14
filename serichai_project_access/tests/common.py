from odoo.tests.common import TransactionCase
from odoo.tests import new_test_user


class AccessCase(TransactionCase):
    """Shared fixture: projects Read/Write/None, stages S1/S2/S3, one restricted user."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Project = cls.env['project.project']
        cls.p_read, cls.p_write, cls.p_none = Project.create(
            [{'name': 'PA Read'}, {'name': 'PA Write'}, {'name': 'PA None'}])
        cls.s1, cls.s2, cls.s3 = cls.env['project.task.type'].create(
            [{'name': 'PA S1'}, {'name': 'PA S2'}, {'name': 'PA S3'}])
        cls.group = cls.env['res.groups'].create({'name': 'PA Dept Group'})
        cls.profile = cls.env['project.access.profile'].create({
            'name': 'PA Dept', 'group_ids': [(6, 0, cls.group.ids)]})
        cls.line_read = cls.env['project.access.line'].create({
            'profile_id': cls.profile.id, 'project_ids': [(6, 0, cls.p_read.ids)],
            'access_level': 'read', 'task_access': 'list'})
        cls.line_write = cls.env['project.access.line'].create({
            'profile_id': cls.profile.id, 'project_ids': [(6, 0, cls.p_write.ids)],
            'access_level': 'write'})
        cls.user = new_test_user(cls.env, login='pa_enf_user', groups='base.group_user')
        cls.user.group_ids = [(4, cls.group.id)]
        Task = cls.env['project.task']
        cls.t_read1 = Task.create({'name': 'R1', 'project_id': cls.p_read.id, 'stage_id': cls.s1.id})
        cls.t_read2 = Task.create({'name': 'R2', 'project_id': cls.p_read.id, 'stage_id': cls.s2.id})
        cls.t_write = Task.create({'name': 'W1', 'project_id': cls.p_write.id, 'stage_id': cls.s3.id})
        cls.t_none = Task.create({'name': 'N1', 'project_id': cls.p_none.id, 'stage_id': cls.s1.id})
        cls.tasks = cls.t_read1 | cls.t_read2 | cls.t_write | cls.t_none

    def as_user(self, user=None):
        return self.env['project.task'].with_user(user or self.user)
