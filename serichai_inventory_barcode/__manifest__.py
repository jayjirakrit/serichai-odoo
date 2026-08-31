# pylint: disable=pointless-statement
{
    'name': 'Serichai Inventory Barcode',
    'summary': 'Barcode scanning for inventory management',
    'version': '1.0.0',
    'description': """Allows barcode scanning for inventory management in Serichai Group.""",
    'depends': ['stock', 'barcodes'],
    'data': [
        'views/stock_picking_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'serichai_inventory_barcode/static/src/js/barcode_scan_widget.js',
        ],
    },
    'installable': True,
    'author': 'Serichai Group',
    'license': 'AGPL-3',
}
