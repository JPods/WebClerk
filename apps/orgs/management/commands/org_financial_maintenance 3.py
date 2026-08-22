from django.core.management.base import BaseCommand

from apps.orgs.services.financial_maintenance import (
    populate_existing_org_financials,
    recent_transaction_activity,
    process_org_financial_pending,
    scrub_org_financials,
    write_daily_alice_observation,
)


class Command(BaseCommand):
    help = "Permanent org financial maintenance command (populate, scrub, process_pending, daily)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--mode",
            choices=["populate", "scrub", "process_pending", "daily"],
            default="scrub",
            help="Maintenance mode to run.",
        )
        parser.add_argument("--org-id", type=int, help="Run against one org by primary key.")
        parser.add_argument("--org-type", type=str, help="Filter org type (customer, vendor, rep, employee, manufacturer).")
        parser.add_argument("--dry-run", action="store_true", help="Compute results but do not persist updates.")
        parser.add_argument(
            "--ignore-locks",
            action="store_true",
            help="Bypass lock checks for populate/scrub operations.",
        )
        parser.add_argument(
            "--no-queue-locked",
            action="store_true",
            help="Do not queue pending tasks for locked orgs (count as skipped_locked).",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=500,
            help="Batch size limit for --mode process_pending.",
        )
        parser.add_argument(
            "--activity-hours",
            type=int,
            default=24,
            help="Recent transaction activity window (hours) for --mode daily.",
        )
        parser.add_argument(
            "--no-alice-log",
            action="store_true",
            help="Skip writing alice_log health_check observation for --mode daily.",
        )

    def handle(self, *args, **options):
        mode = options["mode"]
        org_id = options.get("org_id")
        org_type = options.get("org_type")
        dry_run = bool(options.get("dry_run"))
        lock_aware = not bool(options.get("ignore_locks"))
        queue_if_locked = not bool(options.get("no_queue_locked"))
        limit = int(options.get("limit") or 500)
        activity_hours = int(options.get("activity_hours") or 24)
        write_alice_log = not bool(options.get("no_alice_log"))

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - no updates will be saved"))

        if mode == "populate":
            summary = populate_existing_org_financials(
                org_id=org_id,
                org_type=org_type,
                dry_run=dry_run,
                lock_aware=lock_aware,
                queue_if_locked=queue_if_locked,
            )
        elif mode == "scrub":
            summary = scrub_org_financials(
                org_id=org_id,
                org_type=org_type,
                dry_run=dry_run,
                lock_aware=lock_aware,
                queue_if_locked=queue_if_locked,
            )
        elif mode == "process_pending":
            summary = process_org_financial_pending(limit=limit, dry_run=dry_run)
        else:
            scrub_summary = scrub_org_financials(
                org_id=org_id,
                org_type=org_type,
                dry_run=dry_run,
                lock_aware=lock_aware,
                queue_if_locked=queue_if_locked,
            )
            pending_summary = process_org_financial_pending(limit=limit, dry_run=dry_run)
            activity_summary = recent_transaction_activity(hours=activity_hours)

            alice_log = {"created": False, "setting_id": None}
            if write_alice_log:
                alice_log = write_daily_alice_observation(
                    scrub_summary=scrub_summary,
                    pending_summary=pending_summary,
                    transaction_activity=activity_summary,
                    dry_run=dry_run,
                )

            summary = {
                "mode": "daily",
                "scrub": scrub_summary,
                "pending": pending_summary,
                "transaction_activity": activity_summary,
                "alice_observation": alice_log,
            }

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"org_financial_maintenance mode={mode}"))
        self._print_summary_with_badges(mode=mode, summary=summary)

    def _activity_badge(self, total_activity: int) -> str:
        if total_activity >= 200:
            return "ACTIVITY[VERY_HIGH]"
        if total_activity >= 75:
            return "ACTIVITY[HIGH]"
        if total_activity >= 20:
            return "ACTIVITY[MEDIUM]"
        return "ACTIVITY[LOW]"

    def _status_badge(self, issue_count: int) -> str:
        if issue_count >= 25:
            return "STATUS[CRITICAL]"
        if issue_count >= 10:
            return "STATUS[ATTENTION]"
        if issue_count > 0:
            return "STATUS[WATCH]"
        return "STATUS[OK]"

    def _print_summary_with_badges(self, *, mode: str, summary: dict):
        if mode == "daily":
            scrub = summary.get("scrub", {}) or {}
            pending = summary.get("pending", {}) or {}
            activity = summary.get("transaction_activity", {}) or {}
            alice_obs = summary.get("alice_observation", {}) or {}

            activity_total = int(activity.get("total", 0) or 0)
            issue_count = (
                int(scrub.get("queued_locked", 0) or 0)
                + int(scrub.get("skipped_locked", 0) or 0)
                + int(scrub.get("errors", 0) or 0)
                + int(pending.get("errors", 0) or 0)
                + int(pending.get("missing_org", 0) or 0)
            )

            activity_badge = self._activity_badge(activity_total)
            status_badge = self._status_badge(issue_count)
            self.stdout.write(f"  {activity_badge} {status_badge}")

            self.stdout.write(
                "  quick: "
                f"receivables_aged={scrub.get('receivables_aged', 0)} "
                f"updated={scrub.get('updated', 0)} "
                f"queued_locked={scrub.get('queued_locked', 0)} "
                f"pending_processed={pending.get('processed_pending', 0)} "
                f"tx_last_{activity.get('window_hours', 24)}h={activity_total}"
            )
            if alice_obs.get("created"):
                self.stdout.write(f"  alice_log: created setting_id={alice_obs.get('setting_id')}")
            else:
                self.stdout.write("  alice_log: not written")

            # Keep full detail available but below the badges/quick line.
            self.stdout.write(f"  scrub: {scrub}")
            self.stdout.write(f"  pending: {pending}")
            self.stdout.write(f"  transaction_activity: {activity}")
            return

        # Non-daily modes: compact status line plus full key/value dump.
        issue_count = int(summary.get("errors", 0) or 0) + int(summary.get("queued_locked", 0) or 0)
        activity_total = int(summary.get("updated", 0) or 0)
        self.stdout.write(f"  {self._activity_badge(activity_total)} {self._status_badge(issue_count)}")
        for key, value in summary.items():
            self.stdout.write(f"  {key}: {value}")
