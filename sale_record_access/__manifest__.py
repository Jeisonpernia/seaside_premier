# -*- coding: utf-8 -*-
{
    'name': "Record Accesses for Salespersonnel",
    'summary': """Accessing of records such as Customer details for Salespersonnel""",
    'description': """
        Sale module for Accessing of records for Salespersonnel:
            - Allow different Salespersonnel beside the original contact Salesperson to see a Customer
    """,
    'author': "Earvin Clyde Gatdula - Agilis Enterprise Solutions, Inc.",
    'website': "http://www.agilis-solutions.com/",
    'category': 'Sale',
    'version': '0.1',

    'depends': [
        'sale_management', 'account_invoicing', 'contacts'
        ],

    'data': [
        'views/sale_record_access.xml',
        ],

    'demo': [

        ],
    "application": False,
    "installable": True,
}
