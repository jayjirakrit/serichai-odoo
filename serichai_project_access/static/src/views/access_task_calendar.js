import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { projectTaskCalendarView } from "@project/views/project_task_calendar/project_task_calendar_view";
import { ProjectTaskCalendarController } from "@project/views/project_task_calendar/project_task_calendar_controller";

/** Calendar counterpart of AccessTaskListController: only openable tasks show their form. */
export class AccessTaskCalendarController extends ProjectTaskCalendarController {
    setup() {
        super.setup();
        this.notification = useService("notification");
    }

    async editRecord(record, context = {}) {
        if (record.id && !record.rawRecord?.access_task_detail) {
            this.notification.add(_t("You are not allowed to open this task."), {
                type: "warning",
            });
            return;
        }
        return super.editRecord(record, context);
    }
}

registry.category("views").add("serichai_access_task_calendar", {
    ...projectTaskCalendarView,
    Controller: AccessTaskCalendarController,
});
