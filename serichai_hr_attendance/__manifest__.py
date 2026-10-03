{
    'name': 'Serichai HR Attendance',
    'summary': 'Multi-rate overtime (Normal / 1.5x / 2x) for Attendances, via configurable rules',
    'version': '1.0.0',
    'category': 'Human Resources/Attendances',
    'description': """
Splits attendance hours into Normal / OT 1.5x / OT 2x pay categories by
employee wage type and day type, using rules editable from Attendances >
Overtime Rules — no code changes needed.
    """,
    'depends': ['hr_attendance'],
    'data': [
        'security/ir.model.access.csv',
        'security/hr_attendance_ot_rule_security.xml',
        'data/hr_attendance_ot_rule_data.xml',
        'views/hr_employee_views.xml',
        'views/hr_attendance_ot_rule_views.xml',
        'views/hr_attendance_views.xml',
    ],
    'installable': True,
    'application': False,
    'author': 'Serichai Group',
    'license': 'AGPL-3',
    'post_init_hook': 'post_init_hook',
}
