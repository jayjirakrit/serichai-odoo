import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";

/**
 * Task list of restricted project-access users: only tasks with `access_task_detail` open
 * their form. Other rows show a notice, and the form pager is limited to openable rows. The
 * server refuses direct form loads of the other tasks too (project.task.web_read).
 */
export class AccessTaskListController extends ListController {
    setup() {
        super.setup();
        this.notification = useService("notification");
    }

    async openRecord(record, { force, newWindow } = { force: false }) {
        if (!record.data.access_task_detail) {
            this.notification.add(_t("You are not allowed to open this task."), {
                type: "warning",
            });
            return;
        }
        const activeIds = this.model.root.records
            .filter((datapoint) => datapoint.data.access_task_detail)
            .map((datapoint) => datapoint.resId);
        this.props.selectRecord(record.resId, { activeIds, force, newWindow });
    }
}

registry.category("views").add("serichai_access_task_list", {
    ...listView,
    Controller: AccessTaskListController,
});
