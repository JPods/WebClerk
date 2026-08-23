from django.core.management.base import BaseCommand
from apps.core.models import Contact
import sys
from datetime import datetime


class Command(BaseCommand):
    help = 'Import contacts from West Point SallyPort text data'

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

        end_loop = False
        final_c = []

        while not end_loop:
            p = working_text.find("West Point Association of Graduates - Home")
            if p < 0:
                end_loop = True
            else:
                working_text = working_text[p+10:]
                p_end = working_text.find("West Point Association of Graduates")
                if p_end > 0:
                    one_t = working_text[:p_end]
                    working_text = working_text[p_end:]
                else:
                    one_t = working_text
                    working_text = ""

                c = one_t.split("\n")
                contact = Contact()
                contact.metadata = contact.metadata or {}
                contact.metadata['SallyPort_c'] = c
                contact.metadata['customerID'] = f"SallyPort{Contact.objects.count() + 1}"
                temp_o = {}
                i = -1
                for label in c:
                    i += 1
                    if label == "Send message":
                        if i + 1 < len(c):
                            temp_o['name'] = c[i+1]
                            parse_c = temp_o['name'].split()
                            line_c = []
                            for str_item in parse_c:
                                test_t = str_item.strip()
                                if test_t not in ["Jr.", "Sr.", "II"]:
                                    line_c.append(test_t)
                            if line_c:
                                contact.name_first = line_c[0]
                                contact.name_last = line_c[-1]
                                contact.company = f"{contact.name_last}, {contact.name_first}"
                                contact.metadata['individual'] = True
                                contact.metadata['profile1'] = temp_o['name']
                                contact.comment = (contact.comment or "") + "\r\rFullName: " + c[i+1]

                    elif label == "Enter Location for Map":
                        if i + 1 < len(c):
                            temp_o['location'] = c[i+1]
                            line_c = temp_o['location'].split(";")
                            if len(line_c) > 1:
                                contact.metadata['city'] = line_c[0].strip()
                                contact.metadata['state'] = line_c[1].strip()
                            else:
                                temp_o['location'] = "leaflet"

                    elif label == "Affiliation":
                        if i + 1 < len(c):
                            temp_o['class'] = c[i+1]
                            contact.metadata['profile1'] = c[i+1]

                    elif label == "Cadet Company :":
                        if i + 1 < len(c):
                            temp_o['cadetCompany'] = c[i+1]
                            contact.metadata['profile2'] = c[i+1]

                    elif label == "Retired Branch :":
                        if i + 1 < len(c):
                            temp_o['branch'] = c[i+1]
                            contact.metadata['profile3'] = c[i+1]

                    elif label == "Title or Rank :":
                        if i + 1 < len(c):
                            temp_o['title'] = c[i+1]
                            contact.title = c[i+1]

                    elif label == "Name at Graduation :":
                        if i + 1 < len(c):
                            temp_o['nameAtGraduation'] = c[i+1]
                            contact.metadata['profile4'] = c[i+1]
                            contact.comment = (contact.comment or "") + "\r\rName at Graduation: " + c[i+1]
                            if not contact.name_first:
                                line_c = temp_o['nameAtGraduation'].split()
                                parse_c = line_c
                                line_c = []
                                for str_item in parse_c:
                                    test_t = str_item.strip()
                                    if test_t not in ["Jr.", "Sr.", "II"]:
                                        line_c.append(test_t)
                                if line_c:
                                    contact.name_first = line_c[0]
                                    contact.name_last = line_c[-1]
                                    contact.company = f"{contact.name_last}, {contact.name_first}"
                                    contact.metadata['individual'] = True

                    elif label == "Emails":
                        if i + 1 < len(c):
                            temp_o['emails'] = c[i+1]
                            contact.email = c[i+1]

                    elif label == "Experience":
                        if i + 1 < len(c):
                            temp_o['experience'] = c[i+1]
                            contact.comment = (contact.comment or "") + "\r\rExperience: " + c[i+1]

                    elif label == "Present":
                        if i + 1 < len(c):
                            temp_o['present'] = c[i+1]
                            contact.comment = (contact.comment or "") + "\r\rPresent: " + c[i+1]

                contact.metadata['need'] = group
                contact.metadata['prospect'] = group
                contact.metadata['adSource'] = f"SP_{group}"
                contact.dt_joined = datetime.now()
                if contact.comment:
                    contact.comment = contact.comment[3:]  # Remove leading \r\r?
                contact.update_keywords()
                contact.save()
                final_c.append(contact)
                self.stdout.write(f"Created contact: {contact}")

        self.stdout.write(f"Processed {len(final_c)} contacts.")