"""The wc-flush signal: bump its dt_changed so every open browser tab reloads its cached
Settings, bootstrap data and panel definitions (the frontend polls get_bootstrap_dt)."""
import time


def flush_frontend() -> dict:
    """Bump wc-flush, creating it on a fresh database (Setting audit S-8)."""
    from apps.core.models.setting import Setting
    now_ms = int(time.time() * 1000)
    flush = Setting.objects.filter(ida='wc-flush').first()
    created = flush is None
    if not created:
        flush.config = {'dt_changed': now_ms}
        flush.dt_modified = now_ms
        flush.save(update_fields=['config', 'dt_modified'])
    else:
        flush = Setting.authorized_create(
            ida='wc-flush', name='Frontend Flush Signal', purpose='wc:system',
            explanation='Timestamp bumped to trigger frontend cache reload',
            config={'dt_changed': now_ms}, dt_modified=now_ms)
    return {'created': created, 'dt_changed': now_ms}
