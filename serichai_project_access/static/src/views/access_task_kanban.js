import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanController } from "@web/views/kanban/kanban_controller";

/** Kanban counterpart of AccessTaskListController: same notice and pager limits. */
export class AccessTaskKanbanController extends KanbanController {
    setup() {
        super.setup();
        this.notification = useService("notification");
    }

    async openRecord(record, { newWindow } = {}) {
        if (!record.data.access_task_detail) {
            this.notification.add(_t("You are not allowed to open this task."), {
                type: "warning",
            });
            return;
        }
        const activeIds = this.model.root.records
            .filter((datapoint) => datapoint.data.access_task_detail)
            .map((datapoint) => datapoint.resId);
        this.props.selectRecord(record.resId, { activeIds, newWindow });
    }
}

registry.category("views").add("serichai_access_task_kanban", {
    ...kanbanView,
    Controller: AccessTaskKanbanController,
});
