import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useBus, useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { Component, xml } from "@odoo/owl";

export class StockPickingBarcodeScanner extends Component {
    static template = xml``;
    static props = { ...standardWidgetProps };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        const barcode = useService("barcode");
        useBus(barcode.bus, "barcode_scanned", (ev) => this.onBarcodeScanned(ev));
    }

    async onBarcodeScanned(ev) {
        const resId = this.props.record.resId;
        if (!resId) {
            return;
        }
        const { barcode } = ev.detail;
        try {
            const result = await this.orm.call("stock.picking", "action_scan_barcode", [[resId]], { barcode });
            await this.props.record.load();
            this.notification.add(_t("Added %s", result.product_name), { type: "success" });
        } catch (error) {
            this.notification.add(error.data ? error.data.message : error.message, { type: "danger" });
        }
    }
}

registry.category("view_widgets").add("stock_picking_barcode_scanner", { component: StockPickingBarcodeScanner });
