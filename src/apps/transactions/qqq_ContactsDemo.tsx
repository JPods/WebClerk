/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import React, { useState } from "react";
import ContactPanel, { RefContact } from "./components/ContactPanel";

const initialContacts: RefContact[] = [
  {
    contact_id: 3,
    purpose: "sellto",
    attention: "Bill James",
    email: [{ id: 2, name: "home", value: "1@1.com" }],
    phone: [{ id: 2, name: "home", value: "123.334.1223" }],
    domain: [{ id: 2, name: "home", value: "www.shipto.com/this" }],
    full: "street 123\ncity, state\n 12345",
    address: [{ id: 3, full: "street 123\ncity, state\n 12345", name: "home" }],
  },
];

export default function ContactsDemo() {
  const [contacts, setContacts] = useState<RefContact[]>(initialContacts);

  return (
    <ContactPanel
      contacts={contacts}
      isEditing={true}
      onChange={setContacts}
    />
  );
}
