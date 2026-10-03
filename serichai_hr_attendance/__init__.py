from . import models

BACKFILL_BATCH_SIZE = 1000


def post_init_hook(env):
    """Backfill day_type/normal_hours/overtime_150_hours/overtime_200_hours on
    hr.attendance records that already existed before this module was installed."""
    attendance_model = env['hr.attendance']
    all_ids = attendance_model.sudo().search([]).ids
    for offset in range(0, len(all_ids), BACKFILL_BATCH_SIZE):
        batch_ids = all_ids[offset:offset + BACKFILL_BATCH_SIZE]
        attendance_model.sudo().browse(batch_ids)._compute_ot_hours()
        env.flush_all()
