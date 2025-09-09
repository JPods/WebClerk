from django.db import migrations


class Migration(migrations.Migration):
	# Merge stub resolving prior conflicting 0002 variants; now a no-op
	dependencies = [
		('accounts', '0002_initial'),
		('accounts', '0002_exchangetransaction_remove_exchange_connection_id_and_more'),
	]

	operations = []

