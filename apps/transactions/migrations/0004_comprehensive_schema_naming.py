# Comprehensive schema naming compliance migration
# Renames all remaining datetime and ID fields to follow dt_ and id_ conventions

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0003_rename_id_fields'),
    ]

    operations = [
        # Payment model datetime field renames (already done in code, adding to migration)
        migrations.RenameField(
            model_name='payment',
            old_name='payment_date',
            new_name='dt_payment',
        ),
        migrations.RenameField(
            model_name='payment',
            old_name='processed_at',
            new_name='dt_processed',
        ),
        migrations.RenameField(
            model_name='payment',
            old_name='reconciliation_date',
            new_name='dt_reconciliation',
        ),

        # Payment model ID field renames (already done in code, adding to migration)
        migrations.RenameField(
            model_name='payment',
            old_name='gateway_transaction_id',
            new_name='id_gateway_transaction',
        ),
        migrations.RenameField(
            model_name='payment',
            old_name='gateway_payment_intent_id',
            new_name='id_gateway_payment_intent',
        ),

        # Bill of Materials datetime field renames
        migrations.RenameField(
            model_name='billofmaterial',
            old_name='effective_from',
            new_name='dt_effective_from',
        ),
        migrations.RenameField(
            model_name='billofmaterial',
            old_name='effective_to',
            new_name='dt_effective_to',
        ),

        # Inventory Reservation datetime field renames
        migrations.RenameField(
            model_name='inventoryreservation',
            old_name='expires_at',
            new_name='dt_expires',
        ),
        migrations.RenameField(
            model_name='inventoryreservation',
            old_name='committed_at',
            new_name='dt_committed',
        ),
        migrations.RenameField(
            model_name='inventoryreservation',
            old_name='released_at',
            new_name='dt_released',
        ),

        # Soft Delete datetime field renames
        migrations.RenameField(
            model_name='softdeleteledger',
            old_name='purge_at',
            new_name='dt_purge',
        ),
        migrations.RenameField(
            model_name='softdeleteledger',
            old_name='created_at',
            new_name='dt_created',
        ),

        # Project ID field renames
        migrations.RenameField(
            model_name='project',
            old_name='contact_id',
            new_name='id_contact',
        ),

        # Bundle ID field renames (sync app)
        migrations.RenameField(
            model_name='bundle',
            old_name='connection_id',
            new_name='id_connection',
        ),

        # Note: Line models (InvoiceLine, SalesOrderLine, etc.) correctly use 'parent_id'
        # which is Django's automatic field for ForeignKey database columns.
        # These do not need renaming as they follow Django conventions.

        # Ledger ID field renames (accounts app)
        migrations.RenameField(
            model_name='ledger',
            old_name='parent_id',
            new_name='id_parent',
        ),

        # Tax Jurisdiction ID field renames (accounts app)
        migrations.RenameField(
            model_name='taxjurisdiction',
            old_name='service_id',
            new_name='id_service',
        ),

        # Tag ID field renames (docs app)
        migrations.RenameField(
            model_name='tag',
            old_name='record_id',
            new_name='id_record',
        ),

        # Linkage Index ID field renames (docs app)
        migrations.RenameField(
            model_name='linkageindex',
            old_name='record_id',
            new_name='id_record',
        ),

        # Report ID field renames (core app)
        migrations.RenameField(
            model_name='report',
            old_name='record_id',
            new_name='id_record',
        ),

        # Pending ID field renames (core app)
        migrations.RenameField(
            model_name='pending',
            old_name='record_id',
            new_name='id_record',
        ),

        # Audit ID field renames (core app)
        migrations.RenameField(
            model_name='audit',
            old_name='record_id',
            new_name='id_record',
        ),
        migrations.RenameField(
            model_name='audit',
            old_name='session_id',
            new_name='id_session',
        ),

        # Notification ID field renames (core app)
        migrations.RenameField(
            model_name='notification',
            old_name='record_id',
            new_name='id_record',
        ),

        # Action ID field renames (core app)
        migrations.RenameField(
            model_name='action',
            old_name='project_id',
            new_name='id_project',
        ),

        # Item ID field renames (products app)
        migrations.RenameField(
            model_name='item',
            old_name='specification_id',
            new_name='id_specification',
        ),

        # Processor Runs ID field renames (products app)
        migrations.RenameField(
            model_name='processorrun',
            old_name='stack_id',
            new_name='id_stack',
        ),

        # Item Xref ID field renames (products app)
        migrations.RenameField(
            model_name='itemxref',
            old_name='source_id',
            new_name='id_source',
        ),

        # Inventory Layer ID field renames (products app)
        migrations.RenameField(
            model_name='inventorylayer',
            old_name='source_doc_id',
            new_name='id_source_doc',
        ),
    ]