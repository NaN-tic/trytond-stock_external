=================================
Stock Shipment Externals Scenario
=================================

=============
General Setup
=============

Imports::

    >>> import datetime
    >>> from dateutil.relativedelta import relativedelta
    >>> from decimal import Decimal
    >>> from proteus import config, Model, Wizard
    >>> from trytond.tests.tools import activate_modules
    >>> from trytond.modules.company.tests.tools import create_company, \
    ...     get_company
    >>> today = datetime.date.today()
    >>> yesterday = today - relativedelta(days=1)

Create database::

    >>> config = config.set_trytond()
    >>> config.pool.test = True

Install stock Module::

    >>> config = activate_modules('stock_external')

Create company::

    >>> _ = create_company()
    >>> company = get_company()

Reload the context::

    >>> User = Model.get('res.user')
    >>> config._context = User.get_preferences(True, config.context)

Create customer::

    >>> Party = Model.get('party.party')
    >>> customer = Party(name='Customer')
    >>> customer.save()

Create category::

    >>> ProductCategory = Model.get('product.category')
    >>> category = ProductCategory(name='Category')
    >>> category.save()

Create product::

    >>> ProductUom = Model.get('product.uom')
    >>> ProductTemplate = Model.get('product.template')
    >>> Product = Model.get('product.product')
    >>> unit, = ProductUom.find([('name', '=', 'Unit')])
    >>> product = Product()
    >>> template = ProductTemplate()
    >>> template.name = 'Product'
    >>> template.category = category
    >>> template.default_uom = unit
    >>> template.type = 'goods'
    >>> template.list_price = Decimal('20')
    >>> template.cost_price = Decimal('8')
    >>> template.save()
    >>> product.template = template
    >>> product.save()

Get stock locations::

    >>> Location = Model.get('stock.location')
    >>> supplier_loc, = Location.find([('code', '=', 'SUP')])
    >>> customer_loc, = Location.find([('code', '=', 'CUS')])
    >>> storage_loc, = Location.find([('code', '=', 'STO')])

Recieve products from customer::

    >>> ShipmentExternal = Model.get('stock.shipment.external')
    >>> StockMove = Model.get('stock.move')
    >>> shipment = ShipmentExternal()
    >>> shipment.planned_date = yesterday
    >>> shipment.effective_date = yesterday
    >>> shipment.party = customer
    >>> shipment.from_location = customer_loc
    >>> shipment.to_location = storage_loc
    >>> shipment.company = company
    >>> move = StockMove()
    >>> shipment.moves.append(move)
    >>> move.product = product
    >>> move.uom =unit
    >>> move.quantity = 1
    >>> move.from_location = customer_loc
    >>> move.to_location = storage_loc
    >>> move.company = company
    >>> move.unit_price = Decimal('1')
    >>> shipment.save()
    >>> ShipmentExternal.wait([shipment.id], config.context)
    >>> ShipmentExternal.assign_try([shipment.id], config.context)
    True
    >>> move, = shipment.moves
    >>> move.state
    u'assigned'
    >>> ShipmentExternal.done([shipment.id], config.context)
    >>> shipment.reload()
    >>> shipment.state
    u'done'
    >>> move, = shipment.moves
    >>> move.state
    u'done'
    >>> config._context['locations'] = [storage_loc.id]
    >>> product.reload()


Try to send 2 products to customer::

    >>> shipment = ShipmentExternal()
    >>> shipment.planned_date = today
    >>> shipment.party = customer
    >>> shipment.from_location = storage_loc
    >>> shipment.to_location = customer_loc
    >>> shipment.company = company
    >>> move = StockMove()
    >>> shipment.moves.append(move)
    >>> move.product = product
    >>> move.uom =unit
    >>> move.quantity = 2
    >>> move.from_location = storage_loc
    >>> move.to_location = customer_loc
    >>> move.company = company
    >>> move.unit_price = Decimal('1')
    >>> shipment.save()
    >>> ShipmentExternal.wait([shipment.id], config.context)
    >>> ShipmentExternal.assign_try([shipment.id], config.context)
    False

Delete draft move and only available product::

    >>> for move in shipment.moves:
    ...     if move.state == 'draft':
    ...         break
    >>> shipment.moves.remove(move)
    >>> shipment.save()
    >>> ShipmentExternal.assign_try([shipment.id], config.context)
    True
    >>> move, = shipment.moves
    >>> move.state
    u'assigned'
    >>> ShipmentExternal.done([shipment.id], config.context)
    >>> shipment.reload()
    >>> shipment.state
    u'done'
    >>> move, = shipment.moves
    >>> move.state
    u'done'
    >>> config._context['locations'] = [storage_loc.id]
    >>> product.reload()
    >>> product.quantity == 0
    True
