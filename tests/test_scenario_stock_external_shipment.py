import datetime
import unittest
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from proteus import Model
from trytond.modules.company.tests.tools import create_company, get_company
from trytond.tests.test_tryton import drop_db
from trytond.tests.tools import activate_modules


class Test(unittest.TestCase):

    def setUp(self):
        drop_db()
        super().setUp()

    def tearDown(self):
        drop_db()
        super().tearDown()

    def test(self):

        today = datetime.date.today()
        yesterday = today - relativedelta(days=1)

        # Activate module
        config = activate_modules('stock_external')

        # Create company
        _ = create_company()
        company = get_company()

        # Reload the context
        User = Model.get('res.user')
        config._context = User.get_preferences(True, config.context)

        # Create customer
        Party = Model.get('party.party')
        customer = Party(name='Customer')
        customer.save()

        # Create product
        ProductUom = Model.get('product.uom')
        ProductTemplate = Model.get('product.template')
        Product = Model.get('product.product')
        unit, = ProductUom.find([('name', '=', 'Unit')])
        product = Product()
        template = ProductTemplate()
        template.name = 'Product'
        template.default_uom = unit
        template.type = 'goods'
        template.list_price = Decimal('20')
        template.save()
        product.template = template
        product.save()

        # Get stock locations
        Location = Model.get('stock.location')
        customer_loc, = Location.find([('code', '=', 'CUS')])
        storage_loc, = Location.find([('code', '=', 'STO')])

        # Recieve products from customer
        ShipmentExternal = Model.get('stock.shipment.external')
        StockMove = Model.get('stock.move')
        shipment = ShipmentExternal()
        shipment.planned_date = yesterday
        shipment.effective_date = yesterday
        shipment.party = customer
        shipment.from_location = customer_loc
        shipment.to_location = storage_loc
        shipment.company = company
        move = StockMove()
        shipment.moves.append(move)
        move.product = product
        move.unit = unit
        move.quantity = 1
        move.from_location = customer_loc
        move.to_location = storage_loc
        move.company = company
        shipment.save()
        ShipmentExternal.wait([shipment.id], config.context)
        ShipmentExternal.assign_try([shipment.id], config.context)
        move, = shipment.moves
        self.assertEqual(move.state, 'assigned')

        ShipmentExternal.done([shipment.id], config.context)
        shipment.reload()
        self.assertEqual(shipment.state, 'done')

        move, = shipment.moves
        self.assertEqual(move.state, 'done')

        config._context['locations'] = [storage_loc.id]
        product.reload()

        # Try to send 2 products to customer
        shipment = ShipmentExternal()
        shipment.planned_date = today
        shipment.party = customer
        shipment.from_location = storage_loc
        shipment.to_location = customer_loc
        shipment.company = company
        move = StockMove()
        shipment.moves.append(move)
        move.product = product
        move.unit = unit
        move.quantity = 2
        move.from_location = storage_loc
        move.to_location = customer_loc
        move.company = company
        shipment.save()
        ShipmentExternal.wait([shipment.id], config.context)
        ShipmentExternal.assign_try([shipment.id], config.context)

        # Delete draft move and only available product
        for move in shipment.moves:
            if move.state == 'draft':
                break

        shipment.moves.remove(move)
        shipment.save()
        ShipmentExternal.assign_try([shipment.id], config.context)
        move, = shipment.moves
        self.assertEqual(move.state, 'assigned')

        ShipmentExternal.done([shipment.id], config.context)
        shipment.reload()
        self.assertEqual(shipment.state, 'done')

        move, = shipment.moves
        self.assertEqual(move.state, 'done')

        config._context['locations'] = [storage_loc.id]
        product.reload()
        self.assertEqual(product.quantity, 0)
