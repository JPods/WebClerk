Summary Contact, Customer, (orgs) pages should display emails, addresses, domains, phones from the data in the .refs.links array. The display data is denormalized from the related records. Calls are made to the records only when someone is editing the data.  We should have Add, Edit and Delete buttons. Clicking Edit would change the display value into an input that can be edited.

in contact and org layouts we do not query for communication

We only display what is in .refs

NOT: email.address

DO:  refs.links.email=[{“id": 6, "name": "work", "address": "samirbiswas47@gmail.com”},{“id": 63, "name": “home”, "address": "samir@gmail.com"}]

refs.links.location=[{"id":223, "name": "home", address_full:"
3939 E 60th Pl
Tulsa, OK 74135
US"}]

This would show 2 email address.

Look at Google contacts for an example


{"tags": [], "links": {"item": [], "contact": []}, "keywords": ["656", "planned", "grt"], "categories": [], "depends_on": {}, "related_ids": []}

.refs.links["email": [{"id": 6, "name": "billing", "address": "billing@gmail.com"},{"id": 67, "name": "shipping", "address": "shipping@gmail.com"}], "phone": [{"id": 6, "name": "billing", "number": "1234billing"},{"id": 6, "name": "shipping", "number": "1234shipping"}],

Billing
123 Billing Street
Collect, MA 01212