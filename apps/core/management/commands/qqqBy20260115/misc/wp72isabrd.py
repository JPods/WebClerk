from django.core.management.base import BaseCommand
from apps.core.models import Contact
import sys
from datetime import datetime


class Command(BaseCommand):
    help = 'Import contact from iSabrd text data'

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str, help='File containing the text data')
        parser.add_argument('--group', type=str, help='iSabrd group name')

    def handle(self, *args, **options):
        group = options.get('group')
        if not group:
            group = input("Define iSabrdGroup for this import: ")
        if not group:
            self.stdout.write("No group specified, exiting.")
            return

        # Get text
        if options.get('file'):
            with open(options['file'], 'r') as f:
                working_text = f.read()
        else:
            working_text = sys.stdin.read()

        # Parse
        p = working_text.find("Personal Information")
        if p == -1:
            self.stdout.write("No 'Personal Information' found in text.")
            return

        contact = Contact()
        contact.metadata = contact.metadata or {}
        contact.metadata['iSabrd'] = {}
        working_text = working_text[p-1:]

        # Find Industry
        p = working_text.find("Industry")
        if p != -1:
            vt_fix = working_text[:p-1]
            working_text = working_text[p:]
            p = working_text.find("Occupation")
            if p != -1:
                vt_industry = working_text[:p-1]
                working_text = working_text[p:]
                vt_industry = vt_industry.replace("\n", "").replace("\t", "").replace(":", ":\t")
                working_text = vt_fix + vt_industry + "\n" + working_text

        a_text1 = working_text.split("\n")
        working_text = working_text.replace("\n", "\r")
        vt_catagory = ""
        a_ob_working = []

        for line in a_text1:
            a_text2 = line.split("\t")
            ob_line = {}
            if len(a_text2) == 0:
                continue
            if a_text2[0] == "@publicly@":
                a_text2[0] = "Ticker:"
            elif a_text2[0] == "@num of em@":
                a_text2[0] = "EmployeeCount:"
            elif a_text2[0] == "@Org. Name@":
                a_text2[0] = "Company:"
            elif a_text2[0] == "Actively seeking@":
                a_text2[0] = "SeekingEmployment:"
            elif a_text2[0] == "State/Prov@":
                a_text2[0] = "State"
            elif a_text2[0] == "@Preference@":
                a_text2[0] = "ContactPreference"

            if len(a_text2) == 1:
                if a_text2[0] == "@Personal Information@":
                    vt_cat_change = "Personal"
                elif a_text2[0] == "@Contact Information@":
                    vt_cat_change = "Contact"
                elif a_text2[0] == "@Employment Information@":
                    vt_cat_change = "Employment"
                elif a_text2[0] == "@Previous Employment@":
                    vt_cat_change = "Previous"
                elif a_text2[0] == "@Graduate Schools@":
                    vt_cat_change = "Graduate"
                elif a_text2[0] == "@Extended Bio@":
                    vt_cat_change = "Extended"
                    vt_value = ""
                    for i in range(len(a_text1)):
                        vt_value += a_text1[i] + "\r"
                    contact.metadata['iSabrd'][vt_cat_change] = vt_value
                    break  # drop out

                if vt_cat_change != vt_catagory:
                    if a_ob_working:
                        contact.metadata['iSabrd'][vt_catagory] = a_ob_working
                        a_ob_working = []
                    vt_catagory = vt_cat_change
                else:
                    if ":" in a_text2[0]:
                        a_text2[0] = a_text2[0].replace(":", "").strip()
                        ob_line[a_text2[0]] = ""
                        a_ob_working.append(ob_line)
            elif len(a_text2) > 1:
                a_text2[0] = a_text2[0].replace(":", "").replace(" ", "").replace("/", "").replace("#", "")
                if a_text2[0] == "State@":
                    vt_value = a_text2[1]
                    p_zip = vt_value.find("Postal")
                    if p_zip != -1:
                        vi_zip = vt_value[p_zip+13:].replace(":", "").strip()
                        ob_line["Zip"] = vi_zip
                        a_ob_working.append(ob_line)
                        ob_line = {}
                        vi_state = vt_value[:p_zip-1].replace(":", "").strip()
                        ob_line["State"] = vi_state
                        a_ob_working.append(ob_line)
                    else:
                        vt_value = a_text2[1].replace(":", "").strip()
                        ob_line[a_text2[0]] = vt_value
                        a_ob_working.append(ob_line)
                else:
                    vt_value = a_text2[1].replace(":", "").strip()
                    ob_line[a_text2[0]] = vt_value
                    a_ob_working.append(ob_line)

        # After loop
        if a_ob_working:
            contact.metadata['iSabrd'][vt_catagory] = a_ob_working

        # Set fields
        name_graduation = self.find_in_array_parse_from(a_text1, "Graduation Name :", ":")
        contact.metadata['customerID'] = f"iSabrd{Contact.objects.count() + 1}"
        o_name = self.parse_name(name_graduation)
        contact.name_first = o_name['nameFirst']
        contact.name_last = o_name['nameLast']
        contact.company = f"{contact.name_last}, {contact.name_first}"
        contact.dt_joined = datetime.now()
        contact.metadata['adSource'] = "iSabrd"
        contact.metadata['action'] = "New"
        contact.metadata['actionDate'] = datetime.now()
        contact.metadata['salesNameID'] = "Bill.James"
        contact.metadata['address1'] = self.find_in_array_parse_from(a_text1, "Address :", ":")
        contact.metadata['city'] = self.find_in_array_parse_from(a_text1, "City :", ":")
        state = self.find_in_array_parse_from(a_text1, "State/Prov :", ":")
        p_zip = state.find("Postal Code :")
        if p_zip != -1:
            contact.metadata['state'] = state[:p_zip-1].strip()
            contact.metadata['zip'] = state[p_zip+13:].strip()
        contact.metadata['country'] = self.find_in_array_parse_from(a_text1, "Country :", ":")
        contact.metadata['need'] = group
        contact.metadata['phoneCell'] = self.find_in_array_parse_from(a_text1, "Phone # :", ":")
        contact.email = self.find_in_array_parse_from(a_text1, "E-mail :", ":")
        contact.metadata['profile3'] = self.find_in_array_parse_from(a_text1, "Gender :", ":")
        contact.metadata['domain'] = self.find_in_array_parse_from(a_text1, "Web Site :", ":")
        p_ind = self.find_index_in_array(a_text1, "Industry@")
        if p_ind != -1 and p_ind + 1 < len(a_text1):
            contact.metadata['profile4'] = a_text1[p_ind + 1]
        contact.metadata['profile5'] = self.find_in_array_parse_from(a_text1, "Occupation :", ":")
        contact.metadata['phone'] = self.find_in_array_parse_from(a_text1, "Phone # :", ":")
        seeking = self.find_in_array_parse_from(a_text1, "Actively seeking employment :", ":")
        contact.metadata['sector'] = self.find_in_array_parse_from(a_text1, "Org.", ":")
        contact.metadata['repID'] = self.find_in_array_parse_from(a_text1, "Preference :", ":")

        contact.comment = str(datetime.now()) + "\r" + working_text.replace("\t", " ")

        # Keywords
        contact.update_keywords()
        contact.save()
        self.stdout.write(f"Created contact: {contact}")

    def find_in_array_parse_from(self, array, start_with, delimiter):
        for line in array:
            if line.startswith(start_with):
                parts = line.split(delimiter, 1)
                if len(parts) > 1:
                    return parts[1].strip()
        return ""

    def find_index_in_array(self, array, start_with):
        for i, line in enumerate(array):
            if start_with in line:
                return i
        return -1

    def parse_name(self, full_name):
        parts = full_name.strip().split()
        if len(parts) >= 2:
            return {'nameFirst': parts[0], 'nameLast': ' '.join(parts[1:])}
        return {'nameFirst': full_name, 'nameLast': ''}