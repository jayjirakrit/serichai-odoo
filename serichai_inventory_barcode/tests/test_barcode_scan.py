from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

TEST_BARCODE_UNTRACKED = 'BC-TEST-UNTRACKED-001'
TEST_BARCODE_TRACKED = 'BC-TEST-TRACKED-001'


@tagged('post_install', '-at_install')
class TestBarcodeScan(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.product_untracked = cls.env['product.product'].create({
            'name': 'Test Untracked Product (serichai_inventory_barcode)',
            'type': 'consu',
            'is_storable': True,
            'tracking': 'none',
            'barcode': TEST_BARCODE_UNTRACKED,
        })
        cls.product_tracked = cls.env['product.product'].create({
            'name': 'Test Lot-Tracked Product (serichai_inventory_barcode)',
            'type': 'consu',
            'is_storable': True,
            'tracking': 'lot',
            'barcode': TEST_BARCODE_TRACKED,
        })

        cls.picking_type = cls.env.ref('stock.picking_type_in')

    def setUp(self):
        super().setUp()
        # Fresh picking per test so scan-count assertions never leak between tests.
        self.picking = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type.id,
        })

    def _move_lines_for(self, product):
        return self.picking.move_line_ids.filtered(lambda l: l.product_id == product)

    def test_scan_creates_new_line(self):
        # US1 / contract #1: first scan of an untracked product with no existing
        # open line creates exactly one move line at quantity 1, picked.
        result = self.picking.action_scan_barcode(TEST_BARCODE_UNTRACKED)

        lines = self._move_lines_for(self.product_untracked)
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines.quantity, 1)
        self.assertTrue(lines.picked)
        self.assertEqual(lines.location_id, self.picking.location_id)
        self.assertEqual(lines.location_dest_id, self.picking.location_dest_id)
        self.assertEqual(result, {'product_name': self.product_untracked.display_name})

    def test_scan_increments_existing_line(self):
        # US2 / contract #2: a second scan of the same product increments the
        # existing line instead of creating a duplicate.
        self.picking.action_scan_barcode(TEST_BARCODE_UNTRACKED)
        self.picking.action_scan_barcode(TEST_BARCODE_UNTRACKED)

        lines = self._move_lines_for(self.product_untracked)
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines.quantity, 2)

    def test_scan_unrecognized_barcode_raises(self):
        # US3 / contract #3: an unrecognized barcode raises and changes nothing.
        move_count_before = len(self.picking.move_ids)
        move_line_count_before = len(self.picking.move_line_ids)

        with self.assertRaises(UserError):
            self.picking.action_scan_barcode('does-not-exist')

        self.assertEqual(len(self.picking.move_ids), move_count_before)
        self.assertEqual(len(self.picking.move_line_ids), move_line_count_before)

    def test_scan_tracked_product_blocked(self):
        # US4 / contract #4: a lot/serial tracked product is blocked from
        # auto-add/increment.
        with self.assertRaises(UserError):
            self.picking.action_scan_barcode(TEST_BARCODE_TRACKED)

        self.assertFalse(self._move_lines_for(self.product_tracked))

    def test_scan_blocked_on_closed_transfer(self):
        # FR-007 / contract #5: scanning on a done or cancelled transfer must
        # raise and must not touch any move or move line.
        for state in ('done', 'cancel'):
            with self.subTest(state=state):
                picking = self.env['stock.picking'].create({
                    'picking_type_id': self.picking_type.id,
                })
                picking.state = state
                move_count_before = len(picking.move_ids)
                move_line_count_before = len(picking.move_line_ids)

                with self.assertRaises(UserError):
                    picking.action_scan_barcode(TEST_BARCODE_UNTRACKED)

                self.assertEqual(len(picking.move_ids), move_count_before)
                self.assertEqual(len(picking.move_line_ids), move_line_count_before)
