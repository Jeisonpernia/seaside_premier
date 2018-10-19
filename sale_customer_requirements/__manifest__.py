# -*- coding: utf-8 -*-
{
    'name': "Checklist for Customer's Requirements in Sales",
    'summary': """Checklist in Sales for Requirements that the Customer needs to provide""",
    'description': """
        Sale module for creating a Checklist of Requirements to be supplemented by the Customer:
            - Option for "Enable Checklist" in the Quotation Form
            - Checklist appears when enabled in the Quotation Form. Create items based on the Requirements
            - 100% of the Checklist is required to Confirm Sale
    """,
    'author': "Earvin Clyde Gatdula - Agilis Enterprise Solutions, Inc.",
    'website': "http://www.agilis-solutions.com/",
    'category': 'Sale',
    'version': '0.1',

    'depends': [
        'sale_management', 'account_invoicing'
        ],

    'data': [
        'views/sale_customer_requirements.xml',
        ],

    'demo': [

        ],
    "application": False,
    "installable": True,
}
