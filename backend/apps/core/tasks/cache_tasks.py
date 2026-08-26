"""
Cache-related tasks and async operations.
"""

import logging
from apps.core.constants.save_hooks import execute_save_hook
from apps.core.constants.model_registry import get_model

logger = logging.getLogger(__name__)


def execute_save_async_hooks(model_name: str, obj_id: int, data: dict = None):
    """
    Execute asynchronous save hooks for a model instance.

    Since Celery is not configured, this executes synchronously for now.
    In the future, this should be converted to a Celery task.

    Args:
        model_name: The model name (e.g., 'contact')
        obj_id: The ID of the saved instance
        data: The save payload data
    """
    try:
        logger.info(f"Executing async save hooks for {model_name} id={obj_id}")

        # Get the model class
        model = get_model(model_name)
        if not model:
            logger.error(f"Model not found for {model_name}")
            return

        # Get the instance
        try:
            instance = model.objects.get(id=obj_id)
        except model.DoesNotExist:
            logger.error(f"Instance not found: {model_name} id={obj_id}")
            return

        # Execute the async hooks synchronously
        result = execute_save_hook(model_name, 'save_async', instance, data)

        if result['success']:
            logger.info(f"Async save hooks executed successfully for {model_name} id={obj_id}")
        else:
            logger.error(f"Async save hooks failed for {model_name} id={obj_id}: {result['errors']}")

    except Exception as e:
        logger.error(f"Error executing async save hooks for {model_name} id={obj_id}: {e}", exc_info=True)