import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";

/**
 * "All Tasks" list of the Task List Viewer role: only tasks of the expanded-access project
 * (Settings > Project) can be opened. Other rows show a notice instead, and the form pager is
 * limited to openable rows. The server refuses direct form loads of other tasks as well (see
 * project.task.web_read).
 */
export class RestrictedTaskListController extends ListController {
    setup() {
        super.setup();
        this.notification = useService("notification");
    }

    async openRecord(record, { force, newWindow } = { force: false }) {
        if (!record.data.is_expanded_access_task) {
            this.notification.add(
                _t("You can only open tasks of the project allowed for your role."),
                { type: "warning" }
            );
            return;
        }
        const activeIds = this.model.root.records
            .filter((datapoint) => datapoint.data.is_expanded_access_task)
            .map((datapoint) => datapoint.resId);
        this.props.selectRecord(record.resId, { activeIds, force, newWindow });
    }
}

registry.category("views").add("serichai_restricted_task_list", {
    ...listView,
    Controller: RestrictedTaskListController,
});
