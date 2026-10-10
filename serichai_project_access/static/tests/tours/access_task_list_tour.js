import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add("serichai_access_task_list_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps("project.menu_main_pm", "Open the Project app"),
        {
            content: "Open All Tasks from the menu",
            trigger: 'a[data-menu-xmlid="serichai_project_access.menu_task_all_access"]',
            run: "click",
        },
        {
            content: "Non-openable row is greyed out",
            trigger: ".o_list_view .o_data_row.text-muted:contains('Tour ListOnly')",
        },
        {
            content: "Openable rows are not greyed out",
            trigger: ".o_list_view .o_data_row:not(.text-muted):contains('Tour Detail A')",
        },
        {
            content: "Click the list-only row",
            trigger: ".o_data_row:contains('Tour ListOnly') .o_data_cell[name='name']",
            run: "click",
        },
        {
            content: "A warning is shown",
            trigger: ".o_notification.border-warning:contains('not allowed')",
        },
        {
            content: "The list is still displayed (no navigation)",
            trigger: ".o_list_view:not(:has(.o_form_view))",
        },
        {
            content: "Open the first openable task",
            trigger: ".o_data_row:contains('Tour Detail A') .o_data_cell[name='name']",
            run: "click",
        },
        {
            content: "The form opens and the pager only counts openable rows",
            trigger: ".o_form_view .o_pager_counter .o_pager_limit:contains('2')",
        },
        {
            content: "Next skips the list-only task",
            trigger: ".o_form_view .o_pager_next",
            run: "click",
        },
        {
            content: "The second openable task is displayed",
            trigger: ".o_form_view .o_field_widget[name='name'] input:value('Tour Detail B')",
        },
    ],
});
registry.category("web_tour.tours").add("serichai_access_task_kanban_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps("project.menu_main_pm", "Open the Project app"),
        {
            content: "Open Project from the menu",
            trigger: 'a[data-menu-xmlid="serichai_project_access.menu_project_access"]',
            run: "click",
        },
        {
            content: "Only the granted projects are listed",
            trigger: ".o_kanban_record:contains('PA Tour List')",
        },
        {
            content: "Open the project with the list-only task",
            trigger: ".o_kanban_record:contains('PA Tour List')",
            run: "click",
        },
        {
            content: "Click the list-only card",
            trigger: ".o_kanban_record:contains('Tour ListOnly')",
            run: "click",
        },
        {
            content: "A warning is shown",
            trigger: ".o_notification.border-warning:contains('not allowed')",
        },
        {
            content: "Still on the kanban",
            trigger: ".o_kanban_view:not(:has(.o_form_view))",
        },
    ],
});
