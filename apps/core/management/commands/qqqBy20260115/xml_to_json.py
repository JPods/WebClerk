import xmltodict  # pip install xmltodict
import json

with open("/Users/williamjames/Documents/CommerceExpert/00WebClerk19/Project/Sources/catalog.xml", "r", encoding="utf-8") as f:
    xml_content = f.read()

data = xmltodict.parse(xml_content)
with open("/Users/williamjames/Documents/CommerceExpert/webclerk3_data/catalog.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
