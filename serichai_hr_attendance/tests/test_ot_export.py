from odoo.tests import tagged
from odoo.tests.common import TransactionCase

NEW_FIELDS = ('normal_hours', 'overtime_150_hours', 'overtime_200_hours', 'day_type')


@tagged('post_install', '-at_install')
class TestOtExport(TransactionCase):
    """The export wizard's field picker (web/controllers/export.py Export.get_fields)
    lists every field returned by Model.fields_get() whose 'exportable' attribute is
    not explicitly False - readonly fields (which our compute+store fields are, by
    default) are only excluded when the user opts into "Import-Compatible Export"
    (import_compat=True), which is off by default in the export dialog. So the
    contract this test protects is: these fields must be present in fields_get()
    and must not be marked non-exportable.
    """

    def test_new_fields_are_present_and_exportable(self):
        fields = self.env['hr.attendance'].fields_get(
            attributes=['type', 'string', 'exportable', 'readonly']
        )
        for field_name in NEW_FIELDS:
            self.assertIn(field_name, fields, "%s must exist on hr.attendance" % field_name)
            self.assertTrue(
                fields[field_name].get('exportable', True),
                "%s must not be excluded from export (exportable=False)" % field_name,
            )

    def test_new_fields_survive_default_export_dialog_filter(self):
        # Mirrors web/controllers/export.py Export.get_fields()'s own filter, with
        # import_compat=False (the export dialog's default, non-import-compatible mode -
        # see isCompatible=false in export_data_dialog.js), under which readonly fields
        # are NOT excluded.
        fields = self.env['hr.attendance'].fields_get(
            attributes=['type', 'string', 'exportable', 'readonly']
        )
        import_compat = False
        exportable_field_names = {
            name for name, field in fields.items()
            if field.get('exportable', True)
            and not (import_compat and name != 'id' and field.get('readonly'))
        }
        for field_name in NEW_FIELDS:
            self.assertIn(field_name, exportable_field_names)
