from common.base_serializers import RoleAwareModelSerializer


class StatementLineSerializer(RoleAwareModelSerializer):
    """Serializer for StatementLine — bank/card statement import staging."""

    class Meta:
        from apps.transactions.models.statement_line import StatementLine as SLModel
        model = SLModel
        fields = [
            'id', 'uuid', 'ida',
            'dt_transaction', 'description', 'amount', 'raw_text',
            'source', 'statement_date', 'batch_id',
            'classification', 'category', 'merchant', 'ledger',
            'contact_id', 'vendor_id',
            'promoted', 'payment_id',
            'dt_created', 'dt_modified', 'version',
            'is_active', 'refs', 'metadata', 'prefs', 'comments',
        ]
        read_only_fields = ['id', 'uuid', 'dt_created', 'dt_modified', 'version']
