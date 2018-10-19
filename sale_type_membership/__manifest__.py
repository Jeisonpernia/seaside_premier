# -*- coding: utf-8 -*-
{
    'name': "Product Type Membership in Sales",
    'summary': """Sales Handling for Membership""",
    'description': """
        Sale module for including Membership as type of product:
            - Types of Membership. Inclusion of Exclusive types where only a number of people can avail
            - Month-based Payment Terms with monthly recurring breakdown of payment in Sales and Invoice
            - Miscellaneous and Interest rates entered by the User using a pop-up window
            - Computation for a VATable Interest Fee
            - Computation of Coupons included for the Miscellaneous Fee
    """,
    'author': "Earvin Clyde Gatdula - Agilis Enterprise Solutions, Inc.",
    'website': "http://www.agilis-solutions.com/",
    'category': 'Sale',
    'version': '0.1',

    'depends': [
        'sale_management', 'account_invoicing', 'sale_coupon'
        ],

    'data': [
        'wizards/interest_breakdown.xml',
        'wizards/miscellaneous_fee.xml',
        'views/sale_type_membership.xml',
        ],

    'demo': [

        ],
    "application": False,
    "installable": True,
}
