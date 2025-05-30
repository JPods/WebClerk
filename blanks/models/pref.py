rom django.db import models

class Prefs(models.Model):
    CONTACT_BY_CHOICES = [
        ('email', 'Email'),
        ('phone', 'Phone'),
        ('sms', 'SMS'),
    ]
    
    TIME_OF_DAY_CHOICES = [
        ('morning', 'Morning'),
        ('afternoon', 'Afternoon'),
        ('evening', 'Evening'),
    ]
    
    DAY_OF_WEEK_CHOICES = [
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    ]
    
    contact_by = models.CharField(
        max_length=50,
        choices=CONTACT_BY_CHOICES,
        default='email',
        help_text="Preferred contact method"
    )
    time_of_day = models.CharField(
        max_length=50,
        choices=TIME_OF_DAY_CHOICES,
        default='morning',
        help_text="Preferred time of day, possibly controlled by a template"
    )
    day_of_week = models.CharField(
        max_length=50,
        choices=DAY_OF_WEEK_CHOICES,
        default='monday',
        help_text="Preferred day of the week, possibly controlled by a template"
    )

    class Meta:
        db_table = 'prefs'
        verbose_name = 'Preference'
        verbose_name_plural = 'Preferences'

    def __str__(self):
        return f"Prefs (Contact By: {self.contact_by}, Time: {self.time_of_day}, Day: {self.day_of_week})"