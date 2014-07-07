#!/usr/bin/env python
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
import unittest
import doctest
import trytond.tests.test_tryton
from trytond.tests.test_tryton import test_view, test_depends, doctest_dropdb
from trytond.tests.test_tryton import POOL, DB_NAME, USER, CONTEXT
from trytond.transaction import Transaction


class TestCase(unittest.TestCase):
    'Test module'

    def setUp(self):
        trytond.tests.test_tryton.install_module('stock_external')
        self.category = POOL.get('product.category')
        self.company = POOL.get('company.company')
        self.location = POOL.get('stock.location')
        self.shipment = POOL.get('stock.shipment.external')
        self.party = POOL.get('party.party')
        self.user = POOL.get('res.user')

    def test0005views(self):
        'Test views'
        test_view('stock_external')

    def test0006depends(self):
        'Test depends'
        test_depends()

    def test0010locations(self):
        'Test locations'
        with Transaction().start(DB_NAME, USER, context=CONTEXT):
            supplier, = self.location.search([('code', '=', 'SUP')])
            customer, = self.location.search([('code', '=', 'CUS')])
            storage, = self.location.search([('code', '=', 'STO')])
            company, = self.company.search([
                    ('rec_name', '=', 'Dunder Mifflin'),
                    ])
            self.user.write([self.user(USER)], {
                'main_company': company.id,
                'company': company.id,
                })
            party, = self.party.create([{
                        'name': 'Customer',
                        }])
            self.shipment.create([{
                        'company': company.id,
                        'party': party.id,
                        'from_location': supplier.id,
                        'to_location': storage.id,
                        }])
            for from_, to in [
                    (supplier, supplier),
                    (supplier, customer),
                    (storage, storage),
                    ]:
                self.assertRaises(Exception, self.shipment.create, [{
                            'company': company.id,
                            'party': party.id,
                            'from_location': from_.id,
                            'to_location': to.id,
                            }])


def suite():
    suite = trytond.tests.test_tryton.suite()
    from trytond.modules.company.tests import test_company
    for test in test_company.suite():
        if test not in suite:
            suite.addTest(test)
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestCase))
    suite.addTests(doctest.DocFileSuite(
            'scenario_stock_external_shipment.rst',
            setUp=doctest_dropdb, tearDown=doctest_dropdb, encoding='utf-8',
            optionflags=doctest.REPORT_ONLY_FIRST_FAILURE))
    return suite
