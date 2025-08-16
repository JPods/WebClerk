#Tip: You can call load_keyword_requirements() in your 
# AppConfig’s ready() method and cache the result.

from core.models.setting import Setting

def load_keyword_requirements():
    # Load all active keyword requirements once at startup
    requirements = {}
    for setting in Setting.objects.filter(purpose="keywords_from", is_active=True):
        requirements[setting.table_name] = setting.data
    return requirements

KEYWORD_REQUIREMENTS = load_keyword_requirements()