# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from . import shipment


def register():
    Pool.register(
        shipment.Configuration,
        shipment.ConfigurationSequence,
        shipment.ShipmentExternal,
        shipment.Move,
        shipment.AssignShipmentExternalAssignFailed,
        module='stock_external', type_='model')
    Pool.register(
        shipment.AssignShipmentExternal,
        module='stock_external', type_='wizard')
