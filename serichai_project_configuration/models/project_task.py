import logging
import math
import re

from odoo import api, fields, models
from odoo.exceptions import AccessError

_logger = logging.getLogger(__name__)

PROJECT_VALUE_LABEL = 'มูลค่าโครงการ'
THRESHOLD_PARAM = 'serichai_project_configuration.high_budget_threshold'
DEFAULT_THRESHOLD = 50_000_000.0
_AMOUNT_RE = re.compile(r'[-+]?\d+(\.\d+)?')


def parse_amount(prop_type, raw):
    """Amount held by one property value; 0.0 for non-amount types or unreadable text."""
    if prop_type in ('integer', 'float', 'monetary') and not isinstance(raw, bool):
        value = float(raw or 0)
    elif prop_type in ('char', 'text') and isinstance(raw, str):
        text = re.sub(r'[\s,]', '', raw)
        value = float(text) if _AMOUNT_RE.fullmatch(text) else 0.0
    else:
        return 0.0  # empty, relational, selection, tags, date...
    return value if math.isfinite(value) else 0.0


def is_value_property(prop):
    return (prop.get('string') or '').strip() == PROJECT_VALUE_LABEL


class ProjectTask(models.Model):
    _inherit = 'project.task'

    is_high_value = fields.Boolean(string='High Value', compute='_compute_is_high_value', store=True, readonly=True, help="Project value above the high-value threshold (Settings > Project).")
    project_value = fields.Float(string='Project Value', compute='_compute_project_value')

    @api.depends('task_properties', 'project_id')
    def _compute_is_high_value(self):
        # Stored field: the ORM evaluates it as superuser, so every user gets the same flag.
        threshold = self._get_high_value_threshold()
        for task in self:
            value = 0.0
            try:
                prop = next(filter(is_value_property, task.project_id.task_properties_definition or []), None)
                if prop:
                    value = parse_amount(prop.get('type'), task.task_properties.get(prop['name']))
            except (ValueError, TypeError, KeyError, AttributeError):
                _logger.debug("Unreadable project value on task %s, using 0", task.id, exc_info=True)
            task.is_high_value = value > threshold

    @api.depends_context('uid')
    @api.depends('task_properties', 'project_id')
    def _compute_project_value(self):
        # Goes through read() (not field access) so that any module which hides task properties
        # in the dicts read() returns also zeroes the amount, without this module naming it.
        values = dict.fromkeys(self.ids, 0.0)
        saved = self.filtered(lambda t: isinstance(t.id, int))
        try:
            rows = saved.read(['task_properties']) if saved else []
        except AccessError:  # a task this user may not read: show 0, never fail the list
            rows = []
        for row in rows:
            try:
                prop = next(filter(is_value_property, row['task_properties'] or []), None)
                if prop:
                    values[row['id']] = parse_amount(prop.get('type'), prop.get('value'))
            except (ValueError, TypeError, KeyError, AttributeError):
                _logger.debug("Unreadable project value on task %s", row.get('id'), exc_info=True)
        # assigned last: read() may invalidate cache entries set earlier in this method
        for task in self:
            task.project_value = values.get(task.id, 0.0)

    @api.model
    def _get_high_value_threshold(self):
        # sudo: ir.config_parameter is admin-only; only a number leaves this method.
        raw = self.env['ir.config_parameter'].sudo().get_param(THRESHOLD_PARAM)
        try:
            value = float(raw) if raw else DEFAULT_THRESHOLD  # unset; "0.0" is a real value
        except (TypeError, ValueError):
            return DEFAULT_THRESHOLD
        return value if math.isfinite(value) and value >= 0 else DEFAULT_THRESHOLD

    @api.model
    def _recompute_high_value(self, batch_size=1000):
        """Re-evaluate every task, archived included, in portions."""
        # sudo: an admin-triggered maintenance pass over all tasks, whatever record rules say.
        tasks = self.sudo().with_context(active_test=False)
        ids = tasks.search([], order='id').ids
        for start in range(0, len(ids), batch_size):
            batch = tasks.browse(ids[start:start + batch_size])
            self.env.add_to_compute(self._fields['is_high_value'], batch)
            batch.flush_recordset(['is_high_value'])
            batch.invalidate_recordset()
