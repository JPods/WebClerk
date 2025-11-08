# Save Hooks Reference

## Overview

Save hooks provide a flexible system for executing custom Python scripts before and after model saves. These hooks are defined in Setting records and allow administrators to add custom business logic without code deployments.

## Design Philosophy

Save hooks enable **local customization without code changes**, following enterprise software best practices:

### Separation of Concerns
- **Core business logic** stays in version-controlled code
- **Local customizations** reside in database settings
- **Clear ownership** between framework and implementation teams

### Deployment Flexibility
- **Core application** can be updated without affecting local rules
- **Local hooks** persist through application upgrades
- **No merge conflicts** between core and custom logic

### Multi-Tenant Support
- **Organization-specific** validation and business rules
- **Industry-specific** compliance requirements
- **Regulatory adaptations** without code modifications

### Enterprise Patterns
This approach mirrors successful patterns in major platforms:
- **Salesforce**: Validation rules and Apex triggers
- **NetSuite**: Custom scripts and workflows
- **SAP**: Enhancement points and user exits
- **WordPress**: Hooks and filters system

### Real-World Use Cases
- **Healthcare**: HIPAA compliance validation
- **Finance**: Regulatory reporting triggers
- **Manufacturing**: Quality control checks
- **Retail**: Inventory integration logic
- **Professional Services**: Custom approval workflows

## Setting Record Structure

Save hooks are stored as Setting records with the following structure:

```json
{
    "purpose": "save_pre_post",
    "model_name": "contact",
    "name": "contact_validation",
    "data": {
        "save_pre": "Python script to execute before save",
        "save_post": "Python script to execute after save"
    },
    "is_active": true
}
```

### Fields

- **`purpose`**: Must be `"save_pre_post"`
- **`model_name`**: The model this hook applies to (e.g., `"contact"`, `"proposal"`)
- **`name`**: Unique identifier for this hook (e.g., `"validation"`, `"audit"`)
- **`data.save_pre`**: Python script executed before save (optional)
- **`data.save_post`**: Python script executed after save (optional)
- **`is_active`**: Enable/disable the hook

## Usage Examples

### Creating a Save Hook

```python
from apps.core.models.setting import Setting

# Create a contact validation hook
Setting.objects.create(
    purpose='save_pre_post',
    model_name='contact',
    name='contact_validation',
    data={
        'save_pre': '''
# Validate contact data
if not instance.email or '@' not in instance.email:
    raise ValueError("Invalid email address")

if instance.phone and not instance.phone.startswith('+'):
    instance.phone = f"+1{instance.phone}"
''',
        'save_post': '''
# Log successful save
print(f"Contact {instance.email} saved successfully")
'''
    },
    is_active=True
)
```

### Getting Hooks

```python
from apps.core.constants.save_hooks import get_save_hooks

# Get all hooks for a model
hooks = get_save_hooks('contact')
print(hooks)  # {'contact_validation': {'save_pre': '...', 'save_post': '...'}}
```

### Executing Hooks

```python
from apps.core.constants.save_hooks import execute_save_hook

# Execute pre-save hooks
result = execute_save_hook('contact', 'save_pre', contact_instance, {'user_id': 123})
if not result['success']:
    print("Hook execution failed:", result['errors'])
```

## Hook Execution Context

When hooks execute, they have access to:

- **`instance`**: The model instance being saved
- **`data`**: Additional context data passed to the execution
- **`model_name`**: The model name (e.g., 'contact')
- **`hook_name`**: The hook identifier (e.g., 'validation')
- **`hook_type`**: Either 'save_pre' or 'save_post'

### Example Hook Script

```python
# Pre-save validation
if instance.status == 'active' and not instance.verified_at:
    raise ValueError("Active records must be verified")

# Set derived fields
instance.full_name = f"{instance.first_name} {instance.last_name}".strip()

# Log the change
print(f"Processing {model_name} {instance.id} for {data.get('user_id', 'system')}")
```

## Integration with Save Process

Hooks are automatically executed during the normal save process. No code changes are required in model save methods.

### Pre-Save Hooks
- Execute before the instance is saved to the database
- Can modify the instance or raise exceptions to prevent save
- Useful for validation, data transformation, and business rules

### Post-Save Hooks
- Execute after the instance is successfully saved
- Cannot prevent the save but can perform side effects
- Useful for notifications, logging, and triggering external processes

## Management Commands

### List Save Hooks

```bash
# List all save hooks
python manage.py manage_save_hooks --list

# List hooks for specific model
python manage.py manage_save_hooks --list --model contact
```

### Invalidate Cache

```bash
# Clear save hooks cache (useful after manual DB changes)
python manage.py manage_save_hooks --invalidate-cache
```

## Security Considerations

### Script Safety
- Hooks execute with restricted builtins (no `import`, `open`, etc.)
- Dangerous operations are blocked by the execution environment
- Scripts should be reviewed by administrators before deployment

### Validation
```python
from apps.core.constants.save_hooks import validate_save_hook_script

result = validate_save_hook_script(script_content)
if not result['valid']:
    print("Script validation failed:", result['issues'])
```

## Caching

Save hooks are cached in Redis for performance:

- **Cache Key**: `save_hooks:{model_name}`
- **TTL**: 1 hour
- **Invalidation**: Automatic on Setting changes

## Related Systems

### Mandatory Constants
For application constants, see: [`readmes/mandatory-constants.md`](mandatory-constants.md)

Mandatory constants provide default configuration values for the application.

### Cache Service
For caching implementation, see: [`readmes/cache-service.md`](cache-service.md)

The centralized cache service provides Redis-backed caching for all application data.

## Best Practices

### Development
1. **Keep scripts simple** - Complex logic belongs in proper Python modules
2. **Use validation** - Always validate scripts before deployment
3. **Handle errors gracefully** - Scripts should not crash the save process
4. **Log important actions** - Use print() for debugging and monitoring
5. **Test thoroughly** - Test hooks in development before production deployment

### Enterprise Usage
1. **Document business rules** - Maintain clear documentation of custom logic
2. **Version control scripts** - Keep scripts in external version control
3. **Review security implications** - Audit scripts for data exposure risks
4. **Monitor performance** - Track execution times and failure rates
5. **Plan for upgrades** - Consider core application changes that might affect hooks

### Deployment Strategy
1. **Staging first** - Test hooks in staging environment before production
2. **Gradual rollout** - Enable hooks for subsets of data initially
3. **Monitoring alerts** - Set up alerts for hook failures or performance issues
4. **Rollback plan** - Have procedures to disable hooks if issues arise
5. **Change management** - Document hook changes in change management system

## Error Handling

Hook execution failures are logged but don't prevent saves:

```python
# Hook errors are collected and logged
result = execute_save_hook('contact', 'save_pre', instance)
if result['errors']:
    # Errors are logged but save continues
    logger.warning(f"Hook errors: {result['errors']}")
```

## Examples

### Email Validation Hook
```python
Setting.objects.create(
    purpose='save_pre_post',
    model_name='contact',
    name='email_validation',
    data={
        'save_pre': '''
import re
if instance.email and not re.match(r'^[^@]+@[^@]+\\.[^@]+$', instance.email):
    raise ValueError("Invalid email format")
'''
    }
)
```

### Audit Trail Hook
```python
Setting.objects.create(
    purpose='save_pre_post',
    model_name='contact',
    name='audit_trail',
    data={
        'save_post': '''
# Log changes to external system
audit_log = {
    'model': model_name,
    'id': instance.id,
    'action': 'updated',
    'user': data.get('user_id', 'system'),
    'timestamp': instance.dt_modified
}
print(f"AUDIT: {audit_log}")
'''
    }
)
```

## Troubleshooting

### Hook Not Executing
1. Check if Setting record is `is_active=True`
2. Verify `purpose='save_pre_post'` and correct `model_name`
3. Clear cache: `python manage.py manage_save_hooks --invalidate-cache`

### Script Errors
1. Check application logs for error details
2. Validate script syntax with `validate_save_hook_script()`
3. Test script in isolation before deployment

### Performance Issues
1. Keep scripts lightweight - avoid database queries
2. Use caching for expensive operations
3. Monitor execution times in logs