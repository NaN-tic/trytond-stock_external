# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import Workflow, ModelSQL, ModelView, fields
from trytond.pyson import Eval, If, In, Or, Not, Equal, Bool, Id
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction
from trytond.wizard import Wizard, StateTransition, StateView, Button
from trytond.i18n import gettext
from trytond.exceptions import UserWarning


__all__ = ['Configuration', 'ShipmentExternal', 'Move',
    'AssignShipmentExternalAssignFailed', 'AssignShipmentExternal',
    'ConfigurationSequence']


class Configuration(metaclass=PoolMeta):
    __name__ = 'stock.configuration'

    shipment_external_sequence = fields.MultiValue(
        fields.Many2One('ir.sequence',
            'External Shipment Sequence', required=True, 
            domain=[
                ('company', 'in',
                    [Eval('context', {}).get('company', -1), None]),
                ('code', '=', 'stock.shipment.external'),
                ]))

    @classmethod
    def multivalue_model(cls, field):
        pool = Pool()
        if field in ['shipment_external_sequence']:
            return pool.get('stock.configuration.sequence')
        return super(Configuration, cls).multivalue_model(field)

    @staticmethod
    def default_shipment_external_sequence(**pattern):
        pool = Pool()
        ModelData = pool.get('ir.model.data')
        return ModelData.get_id('stock_external', 'sequence_shipment_external')


class ConfigurationSequence(metaclass=PoolMeta):
    __name__ = 'stock.configuration.sequence'

    shipment_external_sequence = fields.Many2One('ir.sequence',
            'External Shipment Sequence', required=True,
            domain=[
                ('company', 'in',
                    [Eval('context', {}).get('company', -1), None]),
                ('code', '=', 'stock.shipment.external'),
                ])


class ShipmentExternal(Workflow, ModelSQL, ModelView):
    "External Shipment"
    __name__ = 'stock.shipment.external'
    _rec_name = 'code'
    effective_date = fields.Date('Effective Date',
        states={
            'readonly': Eval('state').in_(['cancel', 'done']),
            },
        depends=['state'])
    planned_date = fields.Date('Planned Date',
        states={
            'readonly': Eval('state') != 'draft',
            },
        depends=['state'])
    company = fields.Many2One('company.company', 'Company', required=True,
        states={
            'readonly': Eval('state') != 'draft',
            },
        domain=[
            ('id', If(In('company', Eval('context', {})), '=', '!='),
                Eval('context', {}).get('company', -1)),
            ],
        depends=['state'])
    code = fields.Char("Code", size=None, select=True, readonly=True)
    party = fields.Many2One('party.party', 'Party', required=True,
        states={
            'readonly': Or(Not(Equal(Eval('state'), 'draft')),
                Bool(Eval('moves', [0]))),
            },
        depends=['state'])
    address = fields.Many2One('party.address', 'Contact Address',
        states={
            'readonly': Not(Equal(Eval('state'), 'draft')),
            }, domain=[('party', '=', Eval('party'))],
        depends=['state', 'party'])
    reference = fields.Char("Reference", size=None, select=True,
        states={
            'readonly': Eval('state') != 'draft',
            }, depends=['state'])
    from_location = fields.Many2One('stock.location', "From Location",
        required=True, states={
            'readonly': Or(Not(Equal(Eval('state'), 'draft')),
                Bool(Eval('moves', [0]))),
            },
        domain=[
            ('type', 'in', ['storage', 'customer', 'supplier']),
            ], depends=['state'])
    from_location_type = fields.Function(fields.Char('From Location Type'),
        'on_change_with_from_location_type')
    to_location = fields.Many2One('stock.location', "To Location",
        required=True, states={
            'readonly': Or(Not(Equal(Eval('state'), 'draft')),
                Bool(Eval('moves', [0]))),
            }, domain=[
                If((Eval('from_location_type', '') == 'storage'),
                    (('type', 'in', ['customer', 'supplier']),),
                    (('type', '=', 'storage'),)),
            ], depends=['from_location_type'])
    moves = fields.One2Many('stock.move', 'shipment', 'Moves',
        states={
            'readonly': ((Eval('state') != 'draft')
                | ~Eval('from_location') | ~Eval('to_location')),
            },
        domain=[
            ('from_location', '=', Eval('from_location')),
            ('to_location', '=', Eval('to_location')),
            ('company', '=', Eval('company')),
            ],
        depends=['state', 'from_location', 'to_location', 'planned_date',
            'company'])
    state = fields.Selection([
            ('draft', 'Draft'),
            ('cancel', 'Canceled'),
            ('assigned', 'Assigned'),
            ('waiting', 'Waiting'),
            ('done', 'Done'),
            ], 'State', readonly=True)

    @classmethod
    def __setup__(cls):
        super(ShipmentExternal, cls).__setup__()
        cls._order[0] = ('id', 'DESC')
        cls._transitions |= set((
                ('draft', 'waiting'),
                ('waiting', 'waiting'),
                ('waiting', 'assigned'),
                ('assigned', 'done'),
                ('waiting', 'draft'),
                ('assigned', 'waiting'),
                ('draft', 'cancel'),
                ('waiting', 'cancel'),
                ('assigned', 'cancel'),
                ('cancel', 'draft'),
                ))
        cls._buttons.update({
                'cancel': {
                    'invisible': Eval('state').in_(['cancel', 'done']),
                    'icon': 'tryton-cancel',
                    },
                'draft': {
                    'invisible': ~Eval('state').in_(['cancel', 'waiting']),
                    'icon': If(Eval('state') == 'cancel',
                        'tryton-undo',
                        'tryton-back'),
                    },
                'wait': {
                    'invisible': ~Eval('state').in_(['assigned', 'waiting',
                            'draft']),
                    'icon': If(Eval('state') == 'assigned',
                        'tryton-back',
                        If(Eval('state') == 'waiting',
                            'tryton-undo',
                            'tryton-forward')),
                    },
                'done': {
                    'invisible': Eval('state') != 'assigned',
                    'icon': 'tryton-ok',
                    },
                'assign_wizard': {
                    'invisible': Eval('state') != 'waiting',
                    'icon': 'tryton-forward',
                    'icon': 'tryton-forward',
                    },
                'assign_try': {},
                'assign_force': {},
                })

    @staticmethod
    def default_state():
        return 'draft'

    @staticmethod
    def default_company():
        return Transaction().context.get('company')

    @fields.depends('party')
    def on_change_party(self):
        self.address = None
        if self.party:
            self.address = self.party.address_get(type='delivery')

    @fields.depends('from_location')
    def on_change_with_from_location_type(self, name=None):
        return self.from_location.type if self.from_location else ''

    @classmethod
    def validate(cls, shipments):
        super(ShipmentExternal, cls).validate(shipments)
        for shipment in shipments:
            shipment.check_locations()

    def check_locations(self):
        Warning = Pool().get('res.user.warning')

        from_type = self.from_location.type
        to_type = self.to_location.type
        key = 'internal_shipments_%s' % self.id
        if (from_type == 'storage' and to_type == 'storage' and
                Warning.check(key)):
            raise UserWarning(key,
                gettext('stock_external.internal_shipments',
                    shipment=self.rec_name))
        key = 'same_from_to_type_%s' % self.id
        if from_type == to_type and Warning.check(key):
            raise UserWarning(key,
                gettext('stock_external.same_from_to_type',
                    shipment=self.rec_name))
        key = 'one_storage_required_%s' % self.id
        if (from_type != 'storage' and to_type != 'storage' and
                Warning.check(key)):
            raise UserWarning(key,
                gettext('stock_external.one_storage_required',
                    shipment=self.rec_name))

    @classmethod
    def create(cls, vlist):
        pool = Pool()
        Sequence = pool.get('ir.sequence')
        Config = pool.get('stock.configuration')

        vlist = [x.copy() for x in vlist]
        config = Config(1)
        for values in vlist:
            values['code'] = Sequence.get_id(
                config.shipment_external_sequence and
                config.shipment_external_sequence.id)
        return super(ShipmentExternal, cls).create(vlist)

    @classmethod
    def delete(cls, shipments):
        pool = Pool()
        Move = pool.get('stock.move')
        Warning = pool.get('res.user.warning')
        # Cancel before delete
        cls.cancel(shipments)
        for shipment in shipments:
            key = 'delete_cancel_%s' % shipment.id
            if shipment.state != 'cancel' and Warning.check(key):
                raise UserWarning(key, gettext(
                    'stock_external.delete_cancel', shipment=shipment.rec_name))
        Move.delete([m for s in shipments for m in s.moves])
        super(ShipmentExternal, cls).delete(shipments)

    @classmethod
    @ModelView.button
    @Workflow.transition('draft')
    def draft(cls, shipments):
        Move = Pool().get('stock.move')
        Move.draft([m for s in shipments for m in s.moves])

    @classmethod
    @ModelView.button
    @Workflow.transition('waiting')
    def wait(cls, shipments):
        Move = Pool().get('stock.move')
        # First reset state to draft to allow update from and to location
        Move.draft([m for s in shipments for m in s.moves])
        for shipment in shipments:
            Move.write([m for m in shipment.moves
                    if m.state != 'done'], {
                    'from_location': shipment.from_location.id,
                    'to_location': shipment.to_location.id,
                    'planned_date': shipment.planned_date,
                    })

    @classmethod
    @Workflow.transition('assigned')
    def assign(cls, shipments):
        pass

    @classmethod
    @ModelView.button
    @Workflow.transition('done')
    def done(cls, shipments):
        pool = Pool()
        Move = pool.get('stock.move')
        Date = pool.get('ir.date')
        Move.do([m for s in shipments for m in s.moves])
        cls.write([s for s in shipments if not s.effective_date], {
                'effective_date': Date.today(),
                })

    @classmethod
    @ModelView.button
    @Workflow.transition('cancel')
    def cancel(cls, shipments):
        Move = Pool().get('stock.move')
        Move.cancel([m for s in shipments for m in s.moves])

    @classmethod
    @ModelView.button_action(
        'stock_external.wizard_shipment_external_assign')
    def assign_wizard(cls, shipments):
        pass

    @classmethod
    @ModelView.button
    def assign_try(cls, shipments):
        Move = Pool().get('stock.move')
        to_assign = [s for s in shipments if s.from_location.type == 'storage']
        if not to_assign:
            Move.assign([m for s in shipments for m in s.moves])
            cls.assign(shipments)
            return True
        if Move.assign_try([m for s in to_assign
                    for m in s.moves]):
            cls.assign(shipments)
            return True
        else:
            return False

    @classmethod
    @ModelView.button
    def assign_force(cls, shipments):
        Move = Pool().get('stock.move')
        Move.assign([m for s in shipments for m in s.moves])
        cls.assign(shipments)


class AssignShipmentExternalAssignFailed(ModelView):
    'Assign Shipment External'
    __name__ = 'stock.shipment.external.assign.failed'
    moves = fields.Many2Many('stock.move', None, None, 'Moves',
        readonly=True)

    @staticmethod
    def default_moves():
        ShipmentExternal = Pool().get('stock.shipment.external')
        shipment_id = Transaction().context.get('active_id')
        if not shipment_id:
            return []
        shipment = ShipmentExternal(shipment_id)
        return [x.id for x in shipment.moves if x.state == 'draft']


class AssignShipmentExternal(Wizard):
    'Assign Shipment External'
    __name__ = 'stock.shipment.external.assign'
    start = StateTransition()
    failed = StateView('stock.shipment.external.assign.failed',
        'stock_external.shipment_external_assign_failed_view_form',
        [
            Button('Force Assign', 'force', 'tryton-forward',
                states={
                    'invisible': ~Id('stock',
                        'group_stock_force_assignment').in_(
                        Eval('context', {}).get('groups', [])),
                    }),
            Button('Ok', 'end', 'tryton-ok', True),
            ])
    force = StateTransition()

    def transition_start(self):
        pool = Pool()
        Shipment = pool.get('stock.shipment.external')

        if Shipment.assign_try([Shipment(Transaction().context['active_id'])]):
            return 'end'
        else:
            return 'failed'

    def transition_force(self):
        Shipment = Pool().get('stock.shipment.external')

        Shipment.assign_force([Shipment(Transaction().context['active_id'])])
        return 'end'


class Move(metaclass=PoolMeta):
    __name__ = 'stock.move'

    @classmethod
    def _get_shipment(cls):
        models = super(Move, cls)._get_shipment()
        models.append('stock.shipment.external')
        return models

    @classmethod
    def check_origin(cls, moves, types=None):
        'Do not check moves related to an external shipment'
        pool = Pool()
        ExternalShipment = pool.get('stock.shipment.external')
        moves_to_check = []
        for move in moves:
            if move.shipment and isinstance(move.shipment, ExternalShipment):
                continue
            moves_to_check.append(move)
        super(Move, cls).check_origin(moves_to_check, types)
