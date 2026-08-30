"""
build_demo — Build commerce_demo from commerce_expert.

Usage:
    python manage.py build_demo              # dry-run, show what would change
    python manage.py build_demo --apply      # do it

Uses raw SQL to bypass model save chains and signals.
"""
import uuid
from django.core.management.base import BaseCommand
from django.db import connection


ORG_DATA = {
    'Oakdale Hardware & Supply': {
        'address1': '1420 S Harvard Ave', 'city': 'Tulsa', 'state': 'OK', 'zip': '74112',
        'phone': '(918) 555-0127', 'email': 'info@oakdalehardware.fake',
    },
    'ProBuild Contractors Inc': {
        'address1': '8901 E 46th St', 'city': 'Tulsa', 'state': 'OK', 'zip': '74145',
        'phone': '(918) 555-0302', 'email': 'office@probuildtulsa.fake',
    },
    'Mitchell Residence': {
        'address1': '3217 S Trenton Ave', 'city': 'Tulsa', 'state': 'OK', 'zip': '74105',
        'phone': '(918) 555-0188', 'email': 'pat@mitchell.fake',
    },
    'Acme Sporting Goods': {
        'address1': '2200 Hennepin Ave', 'city': 'Minneapolis', 'state': 'MN', 'zip': '55405',
        'phone': '(612) 555-0101', 'email': 'sales@acmesports.fake',
    },
    'Riverside Sports': {
        'address1': '2100 S Yale Ave', 'city': 'Tulsa', 'state': 'OK', 'zip': '74114',
        'phone': '(918) 555-1234', 'email': 'info@riversidesports.fake',
    },
    'Metro Baseball Academy': {
        'address1': '4500 NW 23rd St', 'city': 'Oklahoma City', 'state': 'OK', 'zip': '73107',
        'phone': '(405) 555-9876', 'email': 'front.desk@metrobaseball.fake',
    },
    'Eastside Little League': {
        'address1': '7700 E 11th St', 'city': 'Tulsa', 'state': 'OK', 'zip': '74112',
        'phone': '(918) 555-7890', 'email': 'league@eastsidell.fake',
    },
    'Diamond Pro Equipment': {
        'address1': '1800 Main St', 'city': 'Dallas', 'state': 'TX', 'zip': '75201',
        'phone': '(214) 555-3456', 'email': 'sales@diamondpro.fake',
    },
    'Stanley Tools': {
        'address1': '1000 Stanley Dr', 'city': 'New Britain', 'state': 'CT', 'zip': '06053',
        'phone': '(860) 555-0400', 'email': 'orders@stanleytools.fake',
    },
    'Behr Paint Co': {
        'address1': '3400 W Segerstrom Ave', 'city': 'Santa Ana', 'state': 'CA', 'zip': '92704',
        'phone': '(714) 555-0500', 'email': 'wholesale@behrpaint.fake',
    },
    'Southern Pine Lumber': {
        'address1': '2900 Cantrell Rd', 'city': 'Little Rock', 'state': 'AR', 'zip': '72202',
        'phone': '(501) 555-0600', 'email': 'sales@southernpine.fake',
    },
}

VENDOR_CONTACTS = {
    'Stanley Tools': ('qq-vendor-stanley', 'Mark Stanley', 'orders@stanleytools.fake'),
    'Behr Paint Co': ('qq-vendor-behr', 'Karen Behr', 'wholesale@behrpaint.fake'),
    'Southern Pine Lumber': ('qq-vendor-spl', 'Jim Sawyer', 'sales@southernpine.fake'),
    'Diamond Pro Equipment': ('qq-vendor-diamond', 'Lisa Wang', 'sales@diamondpro.fake'),
}


def _now_ms():
    from django.utils import timezone
    return int(timezone.now().timestamp() * 1000)


def _insert_address(cursor, ida, address1, city, state, zip_code):
    """Insert an Address row via raw SQL. Returns the new id."""
    full = f'{address1}\n{city}, {state} {zip_code}'
    now = _now_ms()
    cursor.execute("""
        INSERT INTO locations (uuid, ida, address1, city, state, zip, country, "full",
                               address_type, dt_created, dt_modified, version,
                               is_active, security_level, dt_approved, times_used,
                               dt_last_used, is_deleted, is_archived, is_locked,
                               health_rating, config, metadata, refs, prefs,
                               actions, comments, address2, address3, district,
                               postal_name, instructions, latitude, longitude)
        VALUES (%s, %s, %s, %s, %s, %s, 'US', %s, 'work', %s, %s, 1,
                true, 0, 0, 0, 0, false, false, false, 50,
                '{}'::jsonb, '{}'::jsonb, '{}'::jsonb, '{}'::jsonb,
                '{}'::jsonb, '{}'::jsonb, '', '', '', '', '', 0, 0)
        RETURNING id
    """, [str(uuid.uuid4()), ida, address1, city, state, zip_code, full, now, now])
    return cursor.fetchone()[0]


def _insert_phone(cursor, ida, number):
    """Insert a Phone row via raw SQL. Returns the new id."""
    now = _now_ms()
    cursor.execute("""
        INSERT INTO phones (uuid, ida, number, name, country_code, format,
                            attention, opt_out,
                            dt_created, dt_modified, version,
                            is_active, security_level, dt_approved, times_used,
                            dt_last_used, is_deleted, is_archived, is_locked,
                            health_rating, config, metadata, refs, prefs,
                            actions, comments)
        VALUES (%s, %s, %s, 'Office', '', '', '', false,
                %s, %s, 1,
                true, 0, 0, 0, 0, false, false, false, 50,
                '{}'::jsonb, '{}'::jsonb, '{}'::jsonb, '{}'::jsonb,
                '{}'::jsonb, '{}'::jsonb)
        RETURNING id
    """, [str(uuid.uuid4()), ida, number, now, now])
    return cursor.fetchone()[0]


def _insert_contact(cursor, ida, attention, email, company):
    """Insert a Contact row via raw SQL. Returns the new id."""
    now = _now_ms()
    cursor.execute("""
        INSERT INTO contacts (uuid, ida, attention, email, company,
                              dt_created, dt_modified, version,
                              is_active, security_level, dt_approved, times_used,
                              dt_last_used, is_deleted, is_archived, is_locked,
                              health_rating, config, metadata, refs, prefs,
                              actions, comments,
                              is_superuser, is_staff, password,
                              name_first, name_last, name_middle,
                              name_prefix, name_suffix,
                              title, department, role,
                              source_name, dt_joined)
        VALUES (%s, %s, %s, %s, %s,
                %s, %s, 1,
                true, 0, 0, 0, 0, false, false, false, 50,
                '{}'::jsonb, '{}'::jsonb, '{}'::jsonb, '{}'::jsonb,
                '{}'::jsonb, '{}'::jsonb,
                false, false, '',
                '', '', '',
                '', '',
                '', '', '',
                '', NOW())
        RETURNING id
    """, [str(uuid.uuid4()), ida, attention, email, company, now, now])
    return cursor.fetchone()[0]


class Command(BaseCommand):
    help = 'Build demo database: fill denorm, create missing contacts, qq-prefix IDAs'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true',
                            help='Actually apply changes (default is dry-run)')

    def handle(self, *args, **options):
        apply = options['apply']
        if not apply:
            self.stdout.write(self.style.WARNING('DRY RUN — use --apply to commit\n'))

        cursor = connection.cursor()

        try:
            if apply:
                cursor.execute('BEGIN')

            self._fill_org_data(cursor, apply)
            self._create_vendor_contacts(cursor, apply)
            self._fix_purchases(cursor, apply)
            self._fix_workorders(cursor, apply)
            self._denorm_ship_to(cursor, apply)
            self._qq_prefix_idas(cursor, apply)
            self._delete_placeholders(cursor, apply)
            self._create_jpods_llc(cursor, apply)

            if apply:
                cursor.execute('COMMIT')
                self.stdout.write(self.style.SUCCESS('\nAll changes applied'))
            else:
                self.stdout.write(self.style.WARNING('\nDRY RUN complete — nothing saved'))
        except Exception as e:
            if apply:
                cursor.execute('ROLLBACK')
            raise

    def _fill_org_data(self, cursor, apply):
        """Create Address/Phone records and link to orgs."""
        self.stdout.write('\n=== Filling org data ===')
        cursor.execute(
            'SELECT id, display_name, address_id, phone_id, email FROM orgs_orgbase'
        )
        for org_id, display_name, address_id, phone_id, email in cursor.fetchall():
            data = ORG_DATA.get(display_name)
            if not data:
                continue

            if not address_id:
                full = f'{data["address1"]}\n{data["city"]}, {data["state"]} {data["zip"]}'
                self.stdout.write(f'  {display_name}: address → {full}')
                if apply:
                    addr_id = _insert_address(
                        cursor, f'qq-addr-{org_id}',
                        data['address1'], data['city'], data['state'], data['zip'],
                    )
                    cursor.execute(
                        'UPDATE orgs_orgbase SET address_id = %s WHERE id = %s',
                        [addr_id, org_id],
                    )

            if not phone_id:
                self.stdout.write(f'  {display_name}: phone → {data["phone"]}')
                if apply:
                    ph_id = _insert_phone(cursor, f'qq-phone-{org_id}', data['phone'])
                    cursor.execute(
                        'UPDATE orgs_orgbase SET phone_id = %s WHERE id = %s',
                        [ph_id, org_id],
                    )

            if not email or email == 'None':
                self.stdout.write(f'  {display_name}: email → {data["email"]}')
                if apply:
                    cursor.execute(
                        'UPDATE orgs_orgbase SET email = %s WHERE id = %s',
                        [data['email'], org_id],
                    )

    def _create_vendor_contacts(self, cursor, apply):
        """Create contacts for vendors without one."""
        self.stdout.write('\n=== Creating vendor contacts ===')
        cursor.execute(
            "SELECT id, display_name, contact_id FROM orgs_orgbase WHERE org_type = 'vendor'"
        )
        for org_id, display_name, contact_id in cursor.fetchall():
            if contact_id:
                continue
            vc = VENDOR_CONTACTS.get(display_name)
            if not vc:
                continue
            ida, attention, email = vc
            self.stdout.write(f'  CREATE contact for {display_name}: {attention}')
            if apply:
                c_id = _insert_contact(cursor, ida, attention, email, display_name)
                cursor.execute(
                    'UPDATE orgs_orgbase SET contact_id = %s, attention = %s WHERE id = %s',
                    [c_id, attention, org_id],
                )

    def _fix_purchases(self, cursor, apply):
        """Fix contact/attention on purchases."""
        self.stdout.write('\n=== Fixing purchases ===')
        cursor.execute("""
            SELECT p.id, p.ida, p.vendor_id, p.contact_id, p.attention,
                   o.contact_id AS org_contact_id, o.attention AS org_attention, o.display_name
            FROM purchases p
            JOIN orgs_orgbase o ON o.id = p.vendor_id
            WHERE p.contact_id IS NULL AND p.vendor_id IS NOT NULL
        """)
        for p_id, p_ida, vendor_id, p_contact, p_att, org_contact, org_att, org_name in cursor.fetchall():
            if org_contact:
                self.stdout.write(f'  {p_ida}: assign contact from {org_name}')
                if apply:
                    new_att = org_att if org_att and org_att != 'None' else org_name
                    cursor.execute(
                        'UPDATE purchases SET contact_id = %s, attention = %s WHERE id = %s',
                        [org_contact, new_att, p_id],
                    )

    def _fix_workorders(self, cursor, apply):
        """Fix customer/contact on work orders."""
        self.stdout.write('\n=== Fixing work orders ===')
        cursor.execute("""
            SELECT id, ida, customer_id, contact_id FROM work_orders
            WHERE customer_id IS NULL OR contact_id IS NULL
        """)
        rows = cursor.fetchall()
        if not rows:
            return

        # Get a default customer
        cursor.execute("""
            SELECT id, display_name, contact_id FROM orgs_orgbase
            WHERE org_type = 'customer' AND contact_id IS NOT NULL
              AND ida NOT LIKE 'zz%%' AND display_name != '__TEST__'
            LIMIT 1
        """)
        default = cursor.fetchone()
        if not default:
            return

        for wo_id, wo_ida, cust_id, contact_id in rows:
            updates = {}
            if not cust_id:
                updates['customer_id'] = default[0]
                self.stdout.write(f'  {wo_ida}: assign customer {default[1]}')
            if not contact_id:
                updates['contact_id'] = default[2]
                self.stdout.write(f'  {wo_ida}: assign contact from {default[1]}')
            if updates and apply:
                sets = ', '.join(f'{k} = %s' for k in updates)
                cursor.execute(
                    f'UPDATE work_orders SET {sets} WHERE id = %s',
                    list(updates.values()) + [wo_id],
                )

    def _denorm_ship_to(self, cursor, apply):
        """Populate shipping.ship_to on all transactions."""
        self.stdout.write('\n=== Denormalizing ship_to ===')

        # Build org cache with address/phone data
        cursor.execute("""
            SELECT o.id, o.display_name, o.attention,
                   a.address1, a.city, a.state, a.zip, a."full",
                   p.number AS phone
            FROM orgs_orgbase o
            LEFT JOIN locations a ON a.id = o.address_id
            LEFT JOIN phones p ON p.id = o.phone_id
            WHERE o.address_id IS NOT NULL
        """)
        org_cache = {}
        for row in cursor.fetchall():
            org_id, name, att, addr1, city, state, zipcode, full_addr, phone = row
            lines = (full_addr or '').split('\n', 1)
            org_cache[org_id] = {
                'company': name or '',
                'attention': att or '',
                'phone': phone or '',
                'address1': lines[0] if lines else '',
                'city_state_zip': lines[1] if len(lines) > 1 else '',
            }

        tx_tables = [
            ('orders', 'customer_id'),
            ('invoices', 'customer_id'),
            ('proposals', 'customer_id'),
            ('work_orders', 'customer_id'),
            ('purchases', 'vendor_id'),
        ]
        import json
        for table, org_field in tx_tables:
            cursor.execute(f'SELECT id, ida, {org_field}, contact_id, shipping FROM {table}')
            for row_id, ida, org_id, contact_id, shipping in cursor.fetchall():
                if not org_id or org_id not in org_cache:
                    continue

                ship_to = dict(org_cache[org_id])  # copy

                # Use transaction's contact attention if available
                if contact_id:
                    cursor.execute(
                        'SELECT attention FROM contacts WHERE id = %s', [contact_id]
                    )
                    crow = cursor.fetchone()
                    if crow and crow[0] and crow[0] != 'None':
                        ship_to['attention'] = crow[0]

                shipping_dict = shipping if isinstance(shipping, dict) else {}
                old_ship_to = shipping_dict.get('ship_to', {})
                if old_ship_to == ship_to:
                    continue

                self.stdout.write(
                    f'  {table} {ida}: ship_to → {ship_to["company"]}, {ship_to["address1"]}'
                )
                if apply:
                    shipping_dict['ship_to'] = ship_to
                    cursor.execute(
                        f'UPDATE {table} SET shipping = %s::jsonb WHERE id = %s',
                        [json.dumps(shipping_dict), row_id],
                    )

    def _qq_prefix_idas(self, cursor, apply):
        """Prefix non-qq IDAs with qq."""
        self.stdout.write('\n=== Prefixing IDAs with qq ===')

        tables = [
            ('orgs_orgbase', 'Org'),
            ('products_item', 'Item'),
            ('orders', 'Order'),
            ('invoices', 'Invoice'),
            ('proposals', 'Proposal'),
            ('purchases', 'Purchase'),
            ('work_orders', 'WorkOrder'),
        ]
        for table, label in tables:
            cursor.execute(f"""
                SELECT id, ida FROM {table}
                WHERE ida IS NOT NULL
                  AND ida NOT LIKE 'qq%%'
                  AND ida NOT LIKE 'SYS-%%'
                  AND ida NOT LIKE 'jpods-%%'
                  AND ida NOT LIKE 'zz%%'
            """)
            for row_id, ida in cursor.fetchall():
                new_ida = f'qq-{ida}'
                self.stdout.write(f'  {label} {ida} → {new_ida}')
                if apply:
                    cursor.execute(
                        f'UPDATE {table} SET ida = %s WHERE id = %s',
                        [new_ida, row_id],
                    )

    def _delete_placeholders(self, cursor, apply):
        """Remove zz-fake-* and __TEST__ records."""
        self.stdout.write('\n=== Deleting placeholders ===')
        # Delete zz transactions first (before orgs, to avoid FK issues)
        tx_tables = ['work_orders', 'purchases', 'invoices', 'orders']
        for table in tx_tables:
            cursor.execute(f"SELECT count(*) FROM {table} WHERE ida LIKE 'zz%%'")
            ct = cursor.fetchone()[0]
            if ct:
                self.stdout.write(f'  DELETE {ct} from {table} with zz prefix')
                if apply:
                    cursor.execute(f"DELETE FROM {table} WHERE ida LIKE 'zz%%'")

        # Delete zz orgs — clear contact FK refs first
        cursor.execute("SELECT id FROM orgs_orgbase WHERE ida LIKE 'zz%%'")
        zz_ids = [r[0] for r in cursor.fetchall()]
        if zz_ids:
            self.stdout.write(f'  DELETE {len(zz_ids)} orgs with zz prefix')
            if apply:
                for oid in zz_ids:
                    cursor.execute("UPDATE contacts SET customer_id = NULL WHERE customer_id = %s", [oid])
                cursor.execute("DELETE FROM orgs_orgbase WHERE ida LIKE 'zz%%'")

        cursor.execute("SELECT id FROM orgs_orgbase WHERE display_name = '__TEST__'")
        test_ids = [r[0] for r in cursor.fetchall()]
        if test_ids:
            self.stdout.write(f'  DELETE {len(test_ids)} __TEST__ org(s)')
            if apply:
                for tid in test_ids:
                    cursor.execute("UPDATE contacts SET customer_id = NULL WHERE customer_id = %s", [tid])
                    cursor.execute("DELETE FROM orgs_orgbase WHERE id = %s", [tid])

    def _create_jpods_llc(self, cursor, apply):
        """Create JPods LLC as primary_organization."""
        self.stdout.write('\n=== JPods LLC — primary organization ===')
        cursor.execute("SELECT id FROM orgs_orgbase WHERE ida = 'jpods-llc'")
        row = cursor.fetchone()
        if row:
            org_id = row[0]
            self.stdout.write(f'  JPods LLC already exists (id={org_id})')
        else:
            self.stdout.write('  CREATE JPods LLC')
            if apply:
                addr_id = _insert_address(
                    cursor, 'jpods-addr', '3939 E 60th Pl', 'Tulsa', 'OK', '74135',
                )
                ph_id = _insert_phone(cursor, 'jpods-phone', '+1 (612) 414-4211')
                now = _now_ms()
                cursor.execute("""
                    INSERT INTO orgs_orgbase (uuid, ida, display_name, org_type, attention,
                                              email, address_id, phone_id,
                                              dt_created, dt_modified, version,
                                              is_active, security_level, dt_approved,
                                              times_used, dt_last_used,
                                              is_deleted, is_archived, is_locked,
                                              health_rating, type, price_level, terms,
                                              tax_exempt_code,
                                              config, metadata, refs, prefs,
                                              actions, comments, stats,
                                              relationship_stats, contacts, addresses,
                                              domains, phones, emails, docs,
                                              connections, relations, financial,
                                              metrics, gl_accounts)
                    VALUES (%s, 'jpods-llc', 'JPods LLC', 'customer', 'Bill James',
                            'bill.james@jpods.com', %s, %s,
                            %s, %s, 1,
                            true, 0, 0, 0, 0,
                            false, false, false,
                            50, '', '', '',
                            '',
                            '{}'::jsonb, '{}'::jsonb, '{}'::jsonb, '{}'::jsonb,
                            '{}'::jsonb, '{}'::jsonb, '{}'::jsonb,
                            '{}'::jsonb, '[]'::jsonb, '[]'::jsonb,
                            '[]'::jsonb, '[]'::jsonb, '[]'::jsonb, '[]'::jsonb,
                            '[]'::jsonb, '[]'::jsonb, '{}'::jsonb,
                            '{}'::jsonb, '{}'::jsonb)
                    RETURNING id
                """, [str(uuid.uuid4()), addr_id, ph_id, now, now])
                org_id = cursor.fetchone()[0]
                self.stdout.write(f'    → id={org_id}')
            else:
                org_id = None

        if apply and org_id:
            import json
            data_json = json.dumps({
                'id': org_id, 'model_name': 'customer',
                'company': 'JPods LLC', 'ida': 'jpods-llc',
            })
            cursor.execute("""
                UPDATE settings SET config = %s::jsonb, is_active = true
                WHERE purpose = 'db_defaults' AND name = 'primary_organization'
            """, [data_json])
            if cursor.rowcount == 0:
                now = _now_ms()
                cursor.execute("""
                    INSERT INTO settings (uuid, ida, purpose, name,
                                          is_active, dt_created, dt_modified, version,
                                          security_level, dt_approved, times_used,
                                          dt_last_used, is_deleted, is_archived,
                                          is_locked, health_rating,
                                          config, metadata, refs, prefs,
                                          actions, comments,
                                          contact_id, org_id, scope,
                                          explanation, paths)
                    VALUES (%s, '', 'db_defaults', 'primary_organization',
                            true, %s, %s, 1,
                            0, 0, 0, 0, false, false, false, 50,
                            %s::jsonb, '{}'::jsonb, '{}'::jsonb, '{}'::jsonb,
                            '{}'::jsonb, '{}'::jsonb,
                            0, 0, '',
                            '', '{}'::jsonb)
                """, [str(uuid.uuid4()), now, now, data_json])
            self.stdout.write('  primary_organization Setting updated')
