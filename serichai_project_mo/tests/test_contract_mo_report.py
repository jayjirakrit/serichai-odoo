import re

from odoo.tests import tagged
from odoo.tests.common import TransactionCase

REPORT_XMLID = 'serichai_project_mo.report_contract_mo'
BLANK_ROW_COUNT = 15


@tagged('post_install', '-at_install')
class TestContractMoReport(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        uom_unit = cls.env.ref('uom.product_uom_unit')
        cls.product_m = cls.env['product.product'].create({
            'name': 'Test Shirt [Size: M]',
            'type': 'consu',
            'uom_id': uom_unit.id,
        })
        cls.product_l = cls.env['product.product'].create({
            'name': 'Test Shirt [Size: L]',
            'type': 'consu',
            'uom_id': uom_unit.id,
        })
        cls.project = cls.env['project.project'].create({'name': 'Test Project'})

    def _create_mo(self, product, qty):
        return self.env['mrp.production'].create({
            'product_id': product.id,
            'product_qty': qty,
        })

    def _render(self, task):
        html, _report_type = self.env['ir.actions.report']._render_qweb_html(
            REPORT_XMLID, task.ids
        )
        return html.decode() if isinstance(html, bytes) else html

    def test_render_with_data(self):
        """US1: a task with linked MOs and a description prints every content
        section, correctly populated (spec FR-004/005/009, SC-002)."""
        task = self.env['project.task'].create({
            'name': 'Test Job For Print',
            'project_id': self.project.id,
            'description': '<p>Handle with extra care</p>',
        })
        mo1 = self._create_mo(self.product_m, 2)
        mo2 = self._create_mo(self.product_l, 3)
        task.mrp_production_ids = [(6, 0, [mo1.id, mo2.id])]

        html = self._render(task)

        self.assertIn('Test Job For Print', html)
        self.assertIn(self.product_m.display_name, html)
        self.assertIn(self.product_l.display_name, html)
        self.assertIn(mo1.name, html, 'the Manufacturing Order column must show each linked MO reference')
        self.assertIn(mo2.name, html, 'the Manufacturing Order column must show each linked MO reference')
        self.assertIn('Handle with extra care', html)

    def test_render_task_properties(self):
        """US1: only the fixed contract-field properties (matched by label)
        still defined on the task's project print as label + value; a
        property whose definition is gone, or that isn't one of the report's
        contract fields, is skipped (spec FR-011/FR-012)."""
        project = self.env['project.project'].create({
            'name': 'Contract Project',
            'task_properties_definition': [
                {'name': 'contract_no', 'string': 'เลขที่สัญญา', 'type': 'char'},
                {'name': 'qty', 'string': 'จำนวน', 'type': 'integer'},
                {'name': 'sign_date', 'string': 'วันที่ลงนาม', 'type': 'date'},
                {'name': 'lead_time', 'string': 'ระยะส่ง', 'type': 'char'},
                {'name': 'notes', 'string': 'หมายเหตุพิเศษ', 'type': 'char'},
            ],
        })
        task = self.env['project.task'].create({
            'name': 'Property Task',
            'project_id': project.id,
            'task_properties': {
                'contract_no': 'CT-2026-001',
                'qty': 5,
                'sign_date': '2026-09-01',
                'notes': 'Not a contract field',
            },
        })

        html = self._render(task)

        self.assertIn('เลขที่สัญญา', html)
        self.assertIn('CT-2026-001', html)
        self.assertIn('จำนวน', html)
        self.assertIn('วันที่ลงนาม', html)
        self.assertIn(
            'ระยะส่ง', html,
            'a defined property with no value must still print its label, like the blank paper form',
        )
        self.assertNotIn(
            'หมายเหตุพิเศษ', html,
            'a defined property that is not one of the report contract fields must be skipped',
        )
        self.assertNotIn('Not a contract field', html)

        # drop a property from the project's definition: the value stays stored
        # on the task but no longer exists, so the report must skip it
        project.task_properties_definition = [
            {'name': 'contract_no', 'string': 'เลขที่สัญญา', 'type': 'char'},
        ]
        html = self._render(task)

        self.assertIn('CT-2026-001', html)
        self.assertNotIn('จำนวน', html, 'a property that no longer exists must be skipped')
        self.assertNotIn('วันที่ลงนาม', html, 'a property that no longer exists must be skipped')

    def test_report_action_binding(self):
        """US2: the report must be bound to project.task via binding_model_id/
        binding_type so it auto-appears in the Print dropdown (spec FR-002, SC-003)."""
        action = self.env.ref('serichai_project_mo.action_report_contract_mo')
        self.assertEqual(action.model, 'project.task')
        self.assertEqual(action.binding_model_id.model, 'project.task')
        self.assertEqual(action.binding_type, 'report')

        bindings = self.env['ir.actions.report'].get_bindings('project.task')
        binding_ids = [b['id'] for b in bindings.get('report', [])]
        self.assertIn(action.id, binding_ids, 'Contract MO must appear in the Print dropdown bindings')

    def test_render_empty_task(self):
        """US3: a bare task (no MOs, no project, no description, no assignees)
        must still render cleanly (spec FR-008/009, SC-004)."""
        task = self.env['project.task'].create({'name': 'Bare Task'})

        html = self._render(task)

        self.assertIn('Bare Task', html)
        self.assertNotIn(self.project.name, html)
        blank_cells = len(re.findall(r'<td>(?:\xa0|&#160;|&nbsp;)</td>', html))
        self.assertEqual(
            blank_cells, BLANK_ROW_COUNT * 3,
            'the item table must still be ruled with the full grid of blank rows',
        )

    def test_render_overflow_mos(self):
        """US3: more linked MOs than the template's blank-row constant must all
        still appear as rows, with no data loss (spec FR-007, SC-005)."""
        task = self.env['project.task'].create({'name': 'Overflow Task'})
        mos = self.env['mrp.production']
        for _i in range(BLANK_ROW_COUNT + 3):
            mos |= self._create_mo(self.product_m, 1)
        task.mrp_production_ids = [(6, 0, mos.ids)]

        html = self._render(task)

        for mo in mos:
            self.assertIn(mo.name, html, 'every linked MO must appear as a row, even past the padded grid size')
