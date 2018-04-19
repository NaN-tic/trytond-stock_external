# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import unittest
import doctest

import trytond.tests.test_tryton
from trytond.tests.test_tryton import ModuleTestCase, with_transaction
from trytond.tests.test_tryton import doctest_setup, doctest_teardown
from trytond.pool import Pool

from trytond.modules.company.tests import create_company, set_company


class TestCase(ModuleTestCase):
    'Stock External module'
    module = 'stock_external'

    @with_transaction()
    def test0010locations(self):
        'Test locations'
        pool = Pool()
        Location = pool.get('stock.location')
        Shipment = pool.get('stock.shipment.external')
        Party = pool.get('party.party')

        # Create Company
        party = Party(name='Party')
        party.save()
        company = create_company()
        with set_company(company):
            supplier, = Location.search([('code', '=', 'SUP')])
            customer, = Location.search([('code', '=', 'CUS')])
            storage, = Location.search([('code', '=', 'STO')])
            party, = Party.create([{
                        'name': 'Customer',
                        }])
            Shipment.create([{
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
                self.assertRaises(Exception, Shipment.create, [{
                            'company': company.id,
                            'party': party.id,
                            'from_location': from_.id,
                            'to_location': to.id,
                            }])


def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestCase))
    suite.addTests(doctest.DocFileSuite(
            'scenario_stock_external_shipment.rst',
            setUp=doctest_setup, tearDown=doctest_teardown, encoding='utf-8',
            optionflags=doctest.REPORT_ONLY_FIRST_FAILURE))
    return suite
