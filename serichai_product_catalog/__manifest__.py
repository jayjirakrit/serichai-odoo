{
    'name': 'Serichai Product Catalog',
    'summary': 'Visual product catalog with specifications',
    'version': '19.0.1.2.0',
    'category': 'Inventory',
    'description': """
Catalog app on top of product.template: grid/list browsing, search by name,
reference or barcode, and a full-screen product page with the rich-text
Specification (the standard description field), technical data, and the
Sales and Purchase information.
    """,
    'depends': ['product', 'account', 'purchase'],
    'data': [
        'views/product_template_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'serichai_product_catalog/static/src/scss/catalog.scss',
        ],
    },
    'application': True,
    'installable': True,
    'author': 'Serichai Group',
    'license': 'AGPL-3',
}
