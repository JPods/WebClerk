/**
 * PendingHealthBadge — warns when unprocessed pending records are stale (> 3 min).
 *
 * Polls /wcapi/_system_info/ every 60 seconds. Shows a red badge with count
 * and oldest age. Click navigates to the DataBrowser pending list filtered
 * to unprocessed records.
 */
import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router";

const POLL_INTERVAL = 60_000; // 60 seconds

interface PendingHealth {
  count: number;
  stale: boolean;
  oldest_age_seconds: number;
}

const formatAge = (seconds: number): string => {
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  return `${Math.round(seconds / 3600)}h`;
};

export const PendingHealthBadge: React.FC = () => {
  const [health, setHealth] = useState<PendingHealth | null>(null);
  const navigate = useNavigate();

  const fetchHealth = useCallback(async () => {
    try {
      const res = await fetch("/wcapi/_system_info/");
      if (!res.ok) return;
      const data = await res.json();
      if (data.pending) {
        setHealth(data.pending);
      }
    } catch {
      // silent — don't block UI for health check failures
    }
  }, []);

  useEffect(() => {
    fetchHealth();
    const timer = setInterval(fetchHealth, POLL_INTERVAL);
    return () => clearInterval(timer);
  }, [fetchHealth]);

  if (!health || !health.stale) return null;

  return (
    <button
      type="button"
      onClick={() => navigate("/pending?dt_processed=0")}
      className="inline-flex items-center gap-1.5 rounded border border-rose-300 bg-rose-50 px-2 py-0.5 text-[11px] font-semibold text-rose-700 transition hover:bg-rose-100 dark:border-rose-700 dark:bg-rose-900/30 dark:text-rose-300 dark:hover:bg-rose-900/50"
      title={`${health.count} pending record(s) unprocessed, oldest ${formatAge(health.oldest_age_seconds)} — click to view`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-rose-500 animate-pulse" />
      {health.count} pending · {formatAge(health.oldest_age_seconds)}
    </button>
  );
};

export default PendingHealthBadge;
