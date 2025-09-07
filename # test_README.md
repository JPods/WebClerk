# test_README.md
import unittest
import os

README_PATH = os.path.join(os.path.dirname(__file__), "README.md")

class TestReadmeContent(unittest.TestCase):
  def setUp(self):
    with open(README_PATH, "r", encoding="utf-8") as f:
      self.content = f.read()

  def test_runserver_command_present(self):
    self.assertIn("python manage.py runserver", self.content)

  def test_makemigrations_command_present(self):
    self.assertIn("python manage.py makemigrations", self.content)

  def test_migrate_command_present(self):
    self.assertIn("python manage.py migrate", self.content)

  def test_createsuperuser_command_present(self):
    self.assertIn("python manage.py createsuperuser", self.content)

  def test_load_default_access_command_present(self):
    self.assertIn("python manage.py load_default_access", self.content)

  def test_universal_api_examples_present(self):
    self.assertIn("/wcapi/manage/?model_name=contact", self.content)
    self.assertIn("/wcapi/manage/?model_name=contact&id=123", self.content)
    self.assertIn("/wcapi/manage/?model_name=email&contact_id=123", self.content)
    self.assertIn("/wcapi/manage/?model_name=action&mode=create", self.content)
    self.assertIn("/wcapi/get/?model_name=contact&id=123", self.content)

  def test_navigation_structure_present(self):
    self.assertIn("🏠 **Home**", self.content)
    self.assertIn("**Contact**", self.content)
    self.assertIn("**Action**", self.content)
    self.assertIn("**Communication**", self.content)
    self.assertIn("**Admin**", self.content)
    self.assertIn("🤚 **Logout**", self.content)

  def test_key_features_present(self):
    self.assertIn("✅ **Universal API**", self.content)
    self.assertIn("✅ **Contact-Centric**", self.content)
    self.assertIn("✅ **Relationship Management**", self.content)
    self.assertIn("✅ **Bootstrap 5 UI**", self.content)

  def test_github_workflow_present(self):
    self.assertIn("git pull origin dev", self.content)
    self.assertIn("git add .", self.content)
    self.assertIn("git commit -m", self.content)
    self.assertIn("git push", self.content)
    self.assertIn("Pull requests tab", self.content)

if __name__ == "__main__":
  unittest.main()