def migrate(cr, version):
    """Spec 009 bug B: turn the existing text values of ``hidden_property_names`` (one label per
    line) into the tags of ``hidden_property_label_ids``. The text column stays the source read by
    the resolver; it is rewritten from the tags (same labels, normalised spacing)."""
    from odoo import SUPERUSER_ID, api
    env = api.Environment(cr, SUPERUSER_ID, {})
    Line = env['project.access.line'].with_context(active_test=False)
    Label = env['project.access.property.label']
    cr.execute("SELECT id, hidden_property_names FROM project_access_line "
               "WHERE hidden_property_names IS NOT NULL AND hidden_property_names <> ''")
    for line_id, text in cr.fetchall():
        labels = Label._get_or_create((text or '').splitlines())
        if labels:
            Line.browse(line_id).hidden_property_label_ids = labels
    env.registry.clear_cache()
