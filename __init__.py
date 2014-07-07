# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from .shipment import *


def register():
    Pool.register(
        Configuration,
        ShipmentExternal,
        Move,
        AssignShipmentExternalAssignFailed,
        module='stock_external', type_='model')
    Pool.register(
        AssignShipmentExternal,
        module='stock_external', type_='wizard')
