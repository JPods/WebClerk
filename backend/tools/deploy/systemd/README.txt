# systemd unit files for WebClerk3 production
#
# Three units:
#   webclerk3-gunicorn.service  — Django/gunicorn worker
#   webclerk3-celery.service    — Celery worker
#   webclerk3-celerybeat.service — Celery Beat scheduler
#
# Install all three:
#   sudo cp tools/deploy/systemd/*.service /etc/systemd/system/
#   sudo systemctl daemon-reload
#   sudo systemctl enable webclerk3-gunicorn webclerk3-celery webclerk3-celerybeat
#   sudo systemctl start  webclerk3-gunicorn webclerk3-celery webclerk3-celerybeat
#
# Useful commands:
#   sudo systemctl status webclerk3-gunicorn
#   sudo journalctl -u webclerk3-gunicorn -f     # follow logs
#   sudo systemctl restart webclerk3-gunicorn

# ── Adjust these two before installing ───────────────────────────────
#   User=         OS user that owns the repo (not root)
#   WorkingDirectory / ExecStart paths to match your server layout
# ─────────────────────────────────────────────────────────────────────
