from __future__ import annotations

from common.refs.contact_refs import normalize_refs_for_save, normalize_refs_for_response


def test_normalize_refs_for_save_moves_contact_under_links():
    refs = {
        "links": {
            "contact": [
                {
                    "purpose": "billto",
                    "contact": {"id": 3, "attention": "Bill James"},
                    "address": [
                        {
                            "id": 3,
                            "name": "home",
                            "address1": "street 123",
                            "city": "City",
                            "state": "State",
                            "zip": "12345",
                        }
                    ],
                    "email": [{"id": 2, "name": "home", "address": "1@1.com"}],
                    "phone": [{"id": 2, "name": "home", "number": "123.334.1223"}],
                    "domain": [{"id": 2, "name": "home", "path": "www.shipto.com/this"}],
                }
            ]
        }
    }

    normalized = normalize_refs_for_save(refs)
    contacts = normalized["links"]["contact"]
    assert isinstance(contacts, list)
    assert contacts[0]["purpose"] == "billto"

    contact_payload = contacts[0]["contact"]
    assert contact_payload["id"] == 3
    assert contact_payload["attention"] == "Bill James"

    email = contact_payload["email"][0]
    assert email["value"] == "1@1.com"

    phone = contact_payload["phone"][0]
    assert phone["value"] == "123.334.1223"

    domain = contact_payload["domain"][0]
    assert domain["value"] == "www.shipto.com/this"

    address = contact_payload["address"][0]
    assert "full" in address
    assert "street 123" in address["full"]


def test_normalize_refs_for_response_enriches_contact_comm_fields():
    refs = {
        "links": {
            "contact": [
                {
                    "purpose": "shipto",
                    "contact": {
                        "id": 9,
                        "attention": "Bill James",
                        "address": [
                            {
                                "id": 3,
                                "address1": "street 123",
                                "city": "City",
                                "state": "State",
                                "zip": "12345",
                            }
                        ],
                        "email": [{"id": 2, "address": "1@1.com"}],
                        "phone": [{"id": 2, "number": "123.334.1223"}],
                        "domain": [{"id": 2, "path": "www.shipto.com/this"}],
                    },
                }
            ]
        }
    }

    normalized = normalize_refs_for_response(refs)
    contact_entry = normalized["links"]["contact"][0]
    contact_payload = contact_entry["contact"]

    assert contact_entry["purpose"] == "shipto"
    assert contact_payload["id"] == 9

    assert contact_payload["email"][0]["value"] == "1@1.com"
    assert contact_payload["phone"][0]["value"] == "123.334.1223"
    assert contact_payload["domain"][0]["value"] == "www.shipto.com/this"

    assert "full" in contact_payload["address"][0]
    assert "street 123" in contact_payload["address"][0]["full"]
