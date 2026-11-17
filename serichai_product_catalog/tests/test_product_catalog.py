import os
import re
import time
import unittest

from lxml import etree
from PIL import Image

from odoo.tools.image import image_to_base64
from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, tagged
from odoo.tools import file_open
from odoo.tools.safe_eval import safe_eval

CATALOG = 'serichai_product_catalog'


@tagged('post_install', '-at_install')
class TestProductCatalog(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Users = cls.env['res.users'].with_context(no_reset_password=True)
        cls.plain_user = Users.create({
            'name': 'Catalog Plain', 'login': 'catalog_plain',
            'group_ids': [(6, 0, [cls.env.ref('base.group_user').id])],
        })
        cls.purchase_user = Users.create({
            'name': 'Catalog Purchase', 'login': 'catalog_purchase',
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('purchase.group_purchase_user').id])],
        })
        cls.manager_user = Users.create({
            'name': 'Catalog Manager', 'login': 'catalog_manager',
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('product.group_product_manager').id])],
        })
        cls.product = cls.env['product.template'].create({
            'name': 'Catalog Widget Alpha',
            'default_code': 'CAT-REF-001',
            'barcode': '9990001112223',
        })
        cls.bare_product = cls.env['product.template'].create({
            'name': 'Catalog Bare Product', 'list_price': 0.0,
        })

    # -- helpers ---------------------------------------------------------
    def _view(self, user, xmlid, view_type):
        view = self.env.ref(f'{CATALOG}.{xmlid}')
        res = self.env['product.template'].with_user(user).get_view(
            view_id=view.id, view_type=view_type)
        return res['arch']

    def _search_domain(self, term):
        arch = self._view(self.plain_user, 'product_catalog_view_search',
                          'search')
        node = etree.fromstring(arch).xpath("//field[@name='name']")[0]
        return safe_eval(node.get('filter_domain'), {'self': term})

    def _form_arch(self, user):
        return self._view(user, 'product_catalog_view_form', 'form')

    # -- US1 -------------------------------------------------------------
    def test_search_by_name_reference_barcode(self):
        Product = self.env['product.template'].with_user(self.plain_user)
        for term in ('widget alpha', 'cat-ref-001', '9990001112223'):
            found = Product.search(self._search_domain(term))
            self.assertIn(self.product, found, term)
        self.product.active = False
        found = Product.search(self._search_domain('widget alpha'))
        self.assertNotIn(self.product, found)

    def test_action_views_load_for_internal_user(self):
        action = self.env.ref(f'{CATALOG}.product_catalog_action')
        modes = {v.view_mode: v.view_id for v in action.view_ids}
        self.assertEqual(set(modes), {'kanban', 'list', 'form'})
        self.assertEqual(action.search_view_id,
                         self.env.ref(f'{CATALOG}.product_catalog_view_search'))
        menu = self.env.ref(f'{CATALOG}.product_catalog_menu')
        self.assertIn(self.env.ref('base.group_user'), menu.group_ids)
        for xmlid, vtype in (('product_catalog_view_kanban', 'kanban'),
                             ('product_catalog_view_list', 'list'),
                             ('product_catalog_view_form', 'form')):
            arch = self._view(self.plain_user, xmlid, vtype)
            self.assertNotIn('standard_price', arch)
            self.assertNotIn('seller_ids', arch)

    def test_bare_product_renders(self):
        spec = {'name': {}, 'default_code': {}, 'list_price': {},
                'image_1024': {}, 'description': {}}
        res = self.bare_product.with_user(self.plain_user).web_read(spec)
        self.assertEqual(res[0]['name'], 'Catalog Bare Product')

    # -- US2 -------------------------------------------------------------
    def test_form_view_has_spec_first_tab(self):
        arch = etree.fromstring(self._form_arch(self.plain_user))
        pages = arch.xpath('//notebook/page')
        self.assertEqual(pages[0].get('name'), 'specification')

    def test_open_standard_form_returns_record_action(self):
        action = self.product.action_open_standard_form()
        self.assertEqual(action['res_id'], self.product.id)
        self.assertEqual(action['res_model'], 'product.template')
        self.assertEqual(action['view_mode'], 'form')
        with self.assertRaises(ValueError):
            (self.product | self.bare_product).action_open_standard_form()

    # -- US3 -------------------------------------------------------------
    def test_manager_can_write_description(self):
        self.product.with_user(self.manager_user).write(
            {'description': '<p>Spec</p>'})
        self.assertEqual(self.product.description, '<p>Spec</p>')

    def test_plain_user_cannot_write_description(self):
        with self.assertRaises(AccessError):
            self.product.with_user(self.plain_user).write(
                {'description': '<p>x</p>'})

    def test_get_view_description_editable_per_role(self):
        def desc_nodes(user):
            arch = etree.fromstring(self._form_arch(user))
            return arch.xpath("//field[@name='description']")
        plain = desc_nodes(self.plain_user)
        self.assertEqual(len(plain), 1)
        self.assertIn(plain[0].get('readonly'), ('1', 'True', 'true'))
        manager = desc_nodes(self.manager_user)
        self.assertEqual(len(manager), 1)
        self.assertNotIn(manager[0].get('readonly'), ('1', 'True', 'true'))

    def test_manager_can_update_photo_plain_user_cannot(self):
        photo = image_to_base64(Image.new('RGB', (4, 4), 'red'), 'PNG')
        self.product.with_user(self.manager_user).write({'image_1920': photo})
        self.assertTrue(self.product.image_1920)
        with self.assertRaises(AccessError):
            self.product.with_user(self.plain_user).write(
                {'image_1920': photo})

    def test_get_view_photo_editable_per_role(self):
        manager = etree.fromstring(self._form_arch(self.manager_user))
        nodes = manager.xpath("//field[@name='image_1920']")
        self.assertEqual(len(nodes), 1)
        self.assertNotIn(nodes[0].get('readonly'), ('1', 'True', 'true'))
        plain = etree.fromstring(self._form_arch(self.plain_user))
        self.assertFalse(plain.xpath("//field[@name='image_1920']"))
        node = plain.xpath("//field[@name='image_1024']")[0]
        self.assertIn(node.get('readonly'), ('1', 'True', 'true'))

    # -- US4 -------------------------------------------------------------
    def test_purchase_page_stripped_for_plain_user(self):
        # View-level hiding only. KNOWN RESIDUAL: the fields are still
        # readable by an internal user through direct RPC (e.g. read()
        # on standard_price); this is not data protection (decided).
        arch = self._form_arch(self.plain_user)
        tree = etree.fromstring(arch)
        self.assertFalse(tree.xpath("//page[@name='purchase']"))
        for name in ('standard_price', 'seller_ids', 'supplier_taxes_id'):
            self.assertNotIn(f'name="{name}"', arch)
        for vtype, xmlid in (('kanban', 'product_catalog_view_kanban'),
                             ('list', 'product_catalog_view_list')):
            other = self._view(self.plain_user, xmlid, vtype)
            self.assertNotIn('standard_price', other)

    def test_purchase_page_present_for_purchase_user(self):
        arch = self._form_arch(self.purchase_user)
        tree = etree.fromstring(arch)
        self.assertTrue(tree.xpath("//page[@name='purchase']"))
        for name in ('standard_price', 'seller_ids', 'supplier_taxes_id'):
            self.assertIn(f'name="{name}"', arch)

    def test_list_export_disabled(self):
        arch = etree.fromstring(
            self._view(self.plain_user, 'product_catalog_view_list', 'list'))
        self.assertEqual(arch.get('export_xlsx'), '0')

    # -- US5 -------------------------------------------------------------
    def test_scss_has_no_hardcoded_colors(self):
        with file_open(f'{CATALOG}/static/src/scss/catalog.scss') as f:
            text = f.read()
        text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
        text = re.sub(r'//[^\n]*', '', text)
        self.assertFalse(re.findall(r'#[0-9a-fA-F]{3,8}\b', text))
        self.assertFalse(re.findall(r'\bhsla?\(', text))
        self.assertFalse(re.findall(r'\brgba?\(\s*\d', text))
        self.assertNotIn('.text-primary', text)
        # This Odoo build has no `bs-` prefix: `--bs-*` variables are undefined.
        self.assertNotIn('--bs-', text)

    # -- US6: computed fields, views, confidentiality --------------------
    def _taxed_product(self):
        Tax = self.env['account.tax']
        sale_tax = Tax.create({
            'name': 'Catalog VAT 7 sale', 'amount': 7.0,
            'amount_type': 'percent', 'type_tax_use': 'sale'})
        purchase_tax = Tax.create({
            'name': 'Catalog VAT 7 purchase', 'amount': 7.0,
            'amount_type': 'percent', 'type_tax_use': 'purchase'})
        return self.env['product.template'].create({
            'name': 'Catalog Taxed Product',
            'list_price': 150.0,
            'standard_price': 100.0,
            'taxes_id': [(6, 0, sale_tax.ids)],
            'supplier_taxes_id': [(6, 0, purchase_tax.ids)],
        })

    def test_cost_fields_denied_for_plain_user(self):
        product = self.product.with_user(self.plain_user)
        for name in ('catalog_margin', 'catalog_cost_incl_tax'):
            with self.assertRaises(AccessError, msg=name):
                product.read([name])

    def test_computed_values_for_purchase_user(self):
        product = self._taxed_product().with_user(self.purchase_user)
        data = product.read(
            ['catalog_margin', 'catalog_cost_incl_tax',
             'catalog_price_incl_tax'])[0]
        self.assertAlmostEqual(data['catalog_margin'], 50.0)
        self.assertAlmostEqual(data['catalog_cost_incl_tax'], 107.0)
        self.assertAlmostEqual(data['catalog_price_incl_tax'], 160.5)

    def test_price_incl_tax_without_tax(self):
        product = self.env['product.template'].create({
            'name': 'Catalog No Tax', 'list_price': 80.0, 'taxes_id': False})
        data = product.with_user(self.plain_user).read(
            ['catalog_price_incl_tax'])[0]
        self.assertAlmostEqual(data['catalog_price_incl_tax'], 80.0)

    def test_price_incl_tax_with_tax_plain_user(self):
        product = self._taxed_product().with_user(self.plain_user)
        data = product.read(['catalog_price_incl_tax'])[0]
        self.assertAlmostEqual(data['catalog_price_incl_tax'], 160.5)

    def test_cost_nodes_per_role(self):
        names = ('standard_price', 'catalog_margin', 'catalog_cost_incl_tax',
                 'seller_ids')
        plain = self._form_arch(self.plain_user)
        for name in names:
            self.assertNotIn(f'name="{name}"', plain, name)
        purchase = self._form_arch(self.purchase_user)
        for name in names:
            self.assertIn(f'name="{name}"', purchase, name)
        for user in (self.plain_user, self.purchase_user):
            for xmlid, vtype in (('product_catalog_view_kanban', 'kanban'),
                                 ('product_catalog_view_list', 'list')):
                arch = self._view(user, xmlid, vtype)
                for name in names:
                    self.assertNotIn(name, arch, f'{xmlid} {name}')

    def test_web_read_form_spec_has_no_cost_for_plain_user(self):
        product = self._taxed_product().with_user(self.plain_user)
        spec = {'name': {}, 'list_price': {}, 'catalog_price_incl_tax': {},
                'description': {}, 'image_1024': {}}
        res = product.web_read(spec)[0]
        self.assertNotIn('standard_price', res)
        self.assertNotIn('catalog_margin', res)
        self.assertNotIn('catalog_cost_incl_tax', res)
        with self.assertRaises(AccessError):
            product.web_read({'catalog_margin': {}})

    def test_bare_product_reads_catalog_fields(self):
        bare = self.bare_product.with_user(self.purchase_user)
        data = bare.read(['catalog_price_incl_tax', 'catalog_margin',
                          'catalog_cost_incl_tax', 'default_code',
                          'categ_id', 'image_1024'])[0]
        self.assertEqual(data['catalog_price_incl_tax'], 0.0)
        self.assertFalse(data['default_code'])

    # -- FR-017 ----------------------------------------------------------
    def test_standard_product_views_untouched(self):
        IMD = self.env['ir.model.data']
        Views = self.env['ir.ui.view']
        own_views = Views.browse(
            IMD.search([('module', '=', CATALOG),
                        ('model', '=', 'ir.ui.view')]).mapped('res_id'))
        self.assertTrue(own_views)
        # Every own view is primary: none modifies a stock view.
        for view in own_views:
            self.assertFalse(view.inherit_id, view.name)
            self.assertEqual(view.mode, 'primary', view.name)
        # No stock view inherits from a catalog view.
        self.assertFalse(Views.search([
            ('inherit_id', 'in', own_views.ids),
            ('id', 'not in', own_views.ids)]))
        # The standard Products action keeps its own menus and does not
        # use any catalog view.
        std_action = self.env.ref('product.product_template_action')
        self.assertFalse(std_action.view_id & own_views)
        self.assertFalse(std_action.view_ids.view_id & own_views)
        self.assertNotIn(std_action.search_view_id, own_views)
        menu = self.env.ref(f'{CATALOG}.product_catalog_menu')
        self.assertEqual(
            menu.action,
            self.env.ref(f'{CATALOG}.product_catalog_action'))
        self.assertNotEqual(menu.action, std_action)

    def test_catalog_is_browse_only(self):
        for xmlid, vtype in (('product_catalog_view_kanban', 'kanban'),
                             ('product_catalog_view_list', 'list')):
            root = etree.fromstring(self._view(self.manager_user, xmlid, vtype))
            self.assertEqual(root.get('create'), '0', xmlid)
            self.assertEqual(root.get('delete'), '0', xmlid)
        form = etree.fromstring(self._form_arch(self.plain_user))
        self.assertEqual(form.get('delete'), '0')
        self.assertEqual(form.get('create'), '0')
        # Non-managers get no editable control: every field is readonly.
        editable = [
            f.get('name') for f in form.xpath('//field[not(@invisible)]')
            if f.get('readonly') not in ('1', 'True', 'true')
            and not f.get('name').endswith('_uom_name')
            and f.get('widget') != 'many2many_tags'
            and not f.xpath('ancestor::list|ancestor::kanban')]
        self.assertEqual(editable, [])

    # -- SC-008 (opt-in: CATALOG_PERF=1, not part of the default gate) ---
    @unittest.skipUnless(os.environ.get('CATALOG_PERF'),
                         'set CATALOG_PERF=1 to run the 5,000-product timing')
    def test_perf_5000_products(self):
        Tmpl = self.env['product.template']
        Categ = self.env['product.category']
        parent = Categ.create({'name': 'Perf Parent'})
        child = Categ.create({'name': 'Perf Child', 'parent_id': parent.id})
        Tmpl.create([{
            'categ_id': (child if i % 2 else parent).id,
            'name': f'Perf Item {i:05d}',
            'default_code': f'PERF-{i:05d}',
            'barcode': f'88{i:011d}',
        } for i in range(5000)])
        self.env.flush_all()
        Product = Tmpl.with_user(self.plain_user)
        timings = {}
        for label, term in (('name', 'item 04321'), ('reference', 'perf-04321'),
                            ('barcode', '8800000004321')):
            t0 = time.perf_counter()
            found = Product.search(self._search_domain(term))
            timings[label] = time.perf_counter() - t0
            self.assertTrue(found, label)
            self.assertLess(timings[label], 2.0, label)
        spec = {'name': {}, 'default_code': {}, 'list_price': {},
                'image_512': {}}
        # SC-010: category change and search each under 1 second (server side)
        cases = {
            'categ_child_of': [('categ_id', 'child_of', parent.id)],
            'search_name': self._search_domain('item 04321'),
            'search_reference': self._search_domain('perf-04321'),
            'search_barcode': self._search_domain('8800000004321'),
        }
        for label, domain in cases.items():
            t0 = time.perf_counter()
            res = Product.web_search_read(domain, spec, limit=80)
            timings[label + '_wsr'] = time.perf_counter() - t0
            self.assertTrue(res['records'], label)
            self.assertLess(timings[label + '_wsr'], 1.0, label)
        t0 = time.perf_counter()
        page = Product.search([], limit=80)
        page.web_read(spec)
        timings['kanban_page_80'] = time.perf_counter() - t0
        self.assertEqual(len(page), 80)
        self.assertLess(timings['kanban_page_80'], 3.0)
        print('CATALOG_PERF timings (s):', timings)
