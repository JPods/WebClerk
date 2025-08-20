from django import template

register = template.Library()

@register.filter
def get_field(obj, field_name):
    try:
        return getattr(obj, field_name)
    except AttributeError:
        return ''