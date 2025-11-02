import os
from celery import Celery
import threading
import logging

try:
	from kombu import Connection as KombuConnection
except Exception:
	KombuConnection = None

try:
	import redis as _redis_client  # type: ignore
	_REDIS_CLIENT_AVAILABLE = hasattr(_redis_client, 'Redis')
	if not _REDIS_CLIENT_AVAILABLE:
		raise AttributeError('redis client missing Redis attribute')
except Exception as exc:
	_REDIS_IMPORT_ERROR = exc
	_REDIS_CLIENT_AVAILABLE = False
else:
	_REDIS_IMPORT_ERROR = None

# 3 terminals named celery, redis, python
# % redis-server
# % celery -A webclerk3_api worker -l info

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webclerk3_api.settings')

app = Celery('webclerk3_api')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Pre-warm broker connection in a background thread to reduce first-request latency
def _prewarm_broker():
	logger = logging.getLogger(__name__)
	try:
		broker_url = app.conf.get('broker_url') or app.conf.get('CELERY_BROKER_URL') or os.environ.get('CELERY_BROKER_URL')
		if not broker_url:
			logger.debug('No broker URL configured; skipping prewarm')
			return
		if KombuConnection is None:
			logger.debug('kombu not available; cannot prewarm broker connection')
			return
		if broker_url.startswith(('redis://', 'rediss://')) and not _REDIS_CLIENT_AVAILABLE:
			logger.warning('Skipping broker pre-warm: redis client missing (install "redis" package). Details: %s', _REDIS_IMPORT_ERROR)
			return
		logger.info('Pre-warming broker connection to %s', broker_url)
		try:
			with KombuConnection(broker_url) as conn:
				# perform a lightweight connect/open
				conn.connect()
				conn.release()
		except Exception as e:
			logger.warning('Broker pre-warm failed: %s', e)
	except Exception:
		logger.exception('Unexpected error during broker prewarm')

try:
	t = threading.Thread(target=_prewarm_broker, name='broker-prewarm', daemon=True)
	t.start()
except Exception:
	logging.getLogger(__name__).exception('Failed to start broker prewarm thread')