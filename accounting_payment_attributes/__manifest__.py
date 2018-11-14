# -*- coding: utf-8 -*-
{
    'name': "Accounting Additional Payment Details",
    'summary': """Additional Details for Journals of Type:Bank during Payment""",
    'description': """
        Accounting module for additional details in Payment:
            - Cheque details in Payment Forms(Accounting and Invoicing) and Journal Entries.
            - Receipt details present in Payment Forms(Accounting and Invoicing) and Journal Entries.
            - Additional state 'Cleared' which is only present when the 'Cleared' button is pressed. Only applicable to Customer Payment involving Cheques.
    """,
    'author': "Earvin Clyde Gatdula - Agilis Enterprise Solutions, Inc.",
    'website': "http://www.agilis-solutions.com/",
    'category': 'Accounting',
    'version': '0.1',

    'depends': [
        'contacts', 'account_accountant', 'sale_management',
        ],

    'data': [
        'views/accounting_payment_attributes.xml',
    ],

    'demo': [

    ],
    "application": False,
    "installable": True,
}
