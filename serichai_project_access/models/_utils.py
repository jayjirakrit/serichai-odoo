import re
import unicodedata

from odoo.fields import Domain


def norm_label(label):
    """Comparable form of a task property label: Unicode NFKC (Thai vowels typed in a different
    order of composition match), inner whitespace collapsed, trimmed, case-folded."""
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', label or '')).strip().casefold()


def search_bool(operator, value, domain):
    """Turn "<boolean search field> <operator> <value>" into ``domain`` or its negation.

    Odoo 19 normalises boolean conditions to ``in`` / ``not in`` over a set of booleans before
    calling a search method; ``=`` / ``!=`` are accepted too for direct callers."""
    if operator in ('=', '!='):
        value, operator = [value], ('in' if operator == '=' else 'not in')
    if operator not in ('in', 'not in'):
        return NotImplemented
    want_true, want_false = True in value, False in value
    if operator == 'not in':
        want_true, want_false = not want_true, not want_false
    domain = Domain(domain)
    if want_true and want_false:
        return Domain.TRUE
    if want_true:
        return domain
    if want_false:
        return ~domain
    return Domain.FALSE
