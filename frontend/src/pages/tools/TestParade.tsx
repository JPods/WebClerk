/**
 * TestParade — test review parade.
 *
 * Same parade pattern as SettingParade and FormParade:
 * left list of tests grouped by area, right panel shows details,
 * toolbar with feedback buttons. Users see what each test verifies,
 * its result, and the recommended action.
 *
 * LastChecked: 2026-08-31 | WhereUsed: /test-parade | WhoCreated: Bill+Claude
 */
import { useEffect, useState } from "react";
import PageMeta from "@/components/common/PageMeta";
import apiClient from "../../api/axios";
import { getUI } from "@/utils/contactUI";
import "./TestParade.css";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface TestFeedback {
  choice: "understood" | "investigate" | "needs_fix" | "wont_fix";
  notes: string;
  reviewed_by?: string;
  reviewed_at?: string;
}

interface Recommendation {
  actor: "user" | "system" | "none" | "unknown";
  action: string;
}

interface ParadeTest {
  id: string;        // "file::name"
  file: string;
  name: string;
  description: string;
  area: string;
  status: "pass" | "fail" | "error" | "skip" | "unknown";
  message: string;
  recommendation: Recommendation;
  feedback: TestFeedback | null;
}

interface ParadeGroup {
  name: string;
  description: string;
  tests: ParadeTest[];
  count: number;
}

interface TierDef {
  name: string;
  marker: string;
  description: string;
  time_budget: string;
}

interface ParadeManifest {
  groups: ParadeGroup[];
  total_tests: number;
  reviewed_count: number;
  summary: Record<string, number>;
  last_run: string | null;
  tiers: TierDef[];
}

/* ------------------------------------------------------------------ */
/*  Status helpers                                                     */
/* ------------------------------------------------------------------ */

const STATUS_ICON: Record<string, string> = {
  pass: "✓",
  fail: "✗",
  error: "!",
  skip: "○",
  unknown: "?",
};

const STATUS_LABEL: Record<string, string> = {
  pass: "pass",
  fail: "fail",
  error: "error",
  skip: "skip",
  unknown: "not run",
};

const FEEDBACK_LABEL: Record<string, string> = {
  understood: "understood",
  investigate: "investigate",
  needs_fix: "needs fix",
  wont_fix: "won't fix",
};

const FEEDBACK_ICON: Record<string, string> = {
  understood: "✓",
  investigate: "?",
  needs_fix: "✎",
  wont_fix: "—",
};

/* ------------------------------------------------------------------ */
/*  Main Component                                                     */
/* ------------------------------------------------------------------ */

const TestParade: React.FC = () => {
  const active = getUI<string>("theme.active", "dark");
  const baseFontSize = getUI<number>(`theme.${active}.font.size`, 13);

  const [manifest, setManifest] = useState<ParadeManifest | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTest, setSelectedTest] = useState<ParadeTest | null>(null);
  const [feedbackMap, setFeedbackMap] = useState<Record<string, TestFeedback>>({});
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [running, setRunning] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>("all");

  // Load manifest
  useEffect(() => {
    loadManifest();
  }, []);

  const loadManifest = () => {
    setLoading(true);
    apiClient
      .get("/wcapi/_test_parade_manifest/")
      .then((res) => {
        const data: ParadeManifest = res.data?.data ?? res.data;
        setManifest(data);
        // Build feedback map
        const initial: Record<string, TestFeedback> = {};
        for (const g of data.groups) {
          for (const t of g.tests) {
            if (t.feedback) initial[t.id] = t.feedback;
          }
        }
        setFeedbackMap(initial);
      })
      .catch((err) => {
        setError(err?.response?.data?.detail ?? "Failed to load test manifest");
      })
      .finally(() => setLoading(false));
  };

  // Run tests
  const handleRunTests = (marker?: string) => {
    setRunning(true);
    const params = marker ? `?marker=${marker}` : "";
    apiClient
      .get(`/wcapi/_test_parade_run/${params}`)
      .then(() => {
        // Reload manifest to get fresh results
        loadManifest();
      })
      .catch((err) => {
        console.error("Test run failed:", err);
      })
      .finally(() => setRunning(false));
  };

  // Select a test
  const handleSelect = (t: ParadeTest) => {
    setSelectedTest(t);
    setNotes(feedbackMap[t.id]?.notes ?? "");
  };

  // Save feedback
  const handleFeedback = async (choice: TestFeedback["choice"]) => {
    if (!selectedTest) return;
    setSaving(true);
    try {
      await apiClient.post("/wcapi/_test_parade_feedback/", {
        test_id: selectedTest.id,
        feedback: choice,
        notes,
      });
      setFeedbackMap((prev) => ({
        ...prev,
        [selectedTest.id]: { choice, notes },
      }));
    } catch (err) {
      console.error("Feedback save failed:", err);
    } finally {
      setSaving(false);
    }
  };

  // Filter tests
  const filteredGroups = manifest?.groups
    .map((g) => ({
      ...g,
      tests:
        statusFilter === "all"
          ? g.tests
          : g.tests.filter((t) => t.status === statusFilter),
    }))
    .filter((g) => g.tests.length > 0);

  const currentFeedback = selectedTest
    ? feedbackMap[selectedTest.id]
    : null;

  if (loading) {
    return (
      <div className="tp-empty" style={{ height: "100vh" }}>
        <p className="big">loading tests...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="tp-empty" style={{ height: "100vh" }}>
        <p className="big">{error}</p>
      </div>
    );
  }

  const summary = manifest?.summary ?? {};

  return (
    <>
      <PageMeta title="Test Parade" description="Automated test review" />

      <div
        className="tp-container"
        style={{ "--tp-fs": `${baseFontSize}px` } as React.CSSProperties}
      >
        {/* Header */}
        <div className="tp-header">
          <h1>test parade</h1>
          <div className="tp-header-stats">
            {manifest && (
              <>
                <span className="tp-stat">
                  {manifest.total_tests} tests
                </span>
                <span className="tp-stat tp-stat-pass">
                  {STATUS_ICON.pass} {summary.pass ?? 0}
                </span>
                <span className="tp-stat tp-stat-fail">
                  {STATUS_ICON.fail} {summary.fail ?? 0}
                </span>
                <span className="tp-stat tp-stat-error">
                  {STATUS_ICON.error} {summary.error ?? 0}
                </span>
                <span className="tp-stat tp-stat-skip">
                  {STATUS_ICON.skip} {summary.skip ?? 0}
                </span>
                <span className="tp-stat">
                  {Object.keys(feedbackMap).length} reviewed
                </span>
              </>
            )}
            <button
              className="tp-run-btn"
              onClick={() => handleRunTests()}
              disabled={running}
            >
              {running ? "running..." : "run all tests"}
            </button>
          </div>
        </div>

        {/* Filter bar */}
        <div className="tp-filter-bar">
          {["all", "pass", "fail", "error", "skip", "unknown"].map((s) => (
            <button
              key={s}
              className={`tp-filter-btn${statusFilter === s ? " active" : ""}`}
              onClick={() => setStatusFilter(s)}
            >
              {s === "all" ? "all" : `${STATUS_ICON[s]} ${s}`}
            </button>
          ))}
          {manifest?.tiers.map((tier) => (
            <button
              key={tier.marker}
              className="tp-filter-btn"
              onClick={() => handleRunTests(tier.marker)}
              disabled={running}
              title={`${tier.description} (${tier.time_budget})`}
            >
              run {tier.name.toLowerCase()}
            </button>
          ))}
        </div>

        <div className="tp-main">
          {/* Left panel — test list */}
          <div className="tp-left">
            {filteredGroups?.map((group) => (
              <div key={group.name}>
                <div className="tp-group-header">
                  <h2 className="tp-group-title">
                    {group.name} ({group.tests.length})
                  </h2>
                  <p className="tp-group-desc">{group.description}</p>
                </div>
                {group.tests.map((t) => {
                  const fb = feedbackMap[t.id];
                  const isSelected = selectedTest?.id === t.id;
                  return (
                    <button
                      key={t.id}
                      onClick={() => handleSelect(t)}
                      className={`tp-item${isSelected ? " selected" : ""}`}
                    >
                      <div className="tp-item-row">
                        <span className={`tp-item-status ${t.status}`}>
                          {STATUS_ICON[t.status]} {STATUS_LABEL[t.status]}
                        </span>
                        <span className="tp-item-name">{t.description || t.name}</span>
                        {fb && (
                          <span
                            className={`tp-item-badge ${fb.choice}`}
                            title={FEEDBACK_LABEL[fb.choice]}
                          >
                            {FEEDBACK_ICON[fb.choice]}
                          </span>
                        )}
                      </div>
                      <div className="tp-item-file">{t.file}</div>
                    </button>
                  );
                })}
              </div>
            ))}
          </div>

          {/* Right panel — detail */}
          <div className="tp-right">
            {/* Toolbar */}
            {selectedTest && (
              <div className="tp-toolbar">
                <span className="tp-toolbar-name">
                  {selectedTest.description || selectedTest.name}
                </span>
                <div className="tp-toolbar-divider" />
                {(
                  ["understood", "investigate", "needs_fix", "wont_fix"] as const
                ).map((choice) => (
                  <button
                    key={choice}
                    onClick={() => handleFeedback(choice)}
                    disabled={saving}
                    className={`tp-fb-btn ${choice}${
                      currentFeedback?.choice === choice ? " active" : ""
                    }`}
                  >
                    {FEEDBACK_LABEL[choice]}
                  </button>
                ))}
                <div className="tp-toolbar-divider" />
                <input
                  type="text"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="notes..."
                  className="tp-notes-input"
                />
              </div>
            )}

            {/* Preview */}
            <div className="tp-preview">
              {selectedTest ? (
                <div className="tp-preview-content">
                  {/* Status */}
                  <div className="tp-detail-section">
                    <p className="tp-detail-label">status</p>
                    <p className="tp-detail-value">
                      <span className={`tp-item-status ${selectedTest.status}`}>
                        {STATUS_ICON[selectedTest.status]}{" "}
                        {STATUS_LABEL[selectedTest.status]}
                      </span>
                    </p>
                  </div>

                  {/* File & test name */}
                  <div className="tp-detail-section">
                    <p className="tp-detail-label">test</p>
                    <p className="tp-detail-value mono">
                      {selectedTest.file}::{selectedTest.name}
                    </p>
                  </div>

                  {/* Area */}
                  <div className="tp-detail-section">
                    <p className="tp-detail-label">area</p>
                    <p className="tp-detail-value">{selectedTest.area}</p>
                  </div>

                  {/* Error message */}
                  {selectedTest.message && (
                    <div className="tp-detail-section">
                      <p className="tp-detail-label">message</p>
                      <p className="tp-detail-value mono">
                        {selectedTest.message}
                      </p>
                    </div>
                  )}

                  {/* Recommendation */}
                  <div
                    className={`tp-recommendation ${selectedTest.recommendation.actor}`}
                  >
                    <p className="tp-rec-actor">
                      {selectedTest.recommendation.actor === "user"
                        ? "user action"
                        : selectedTest.recommendation.actor === "system"
                        ? "system action"
                        : "no action needed"}
                    </p>
                    <p className="tp-rec-action">
                      {selectedTest.recommendation.action}
                    </p>
                  </div>

                  {/* Feedback history */}
                  {currentFeedback && (
                    <div className="tp-detail-section">
                      <p className="tp-detail-label">your feedback</p>
                      <p className="tp-detail-value">
                        {FEEDBACK_LABEL[currentFeedback.choice]}
                        {currentFeedback.notes
                          ? ` — ${currentFeedback.notes}`
                          : ""}
                      </p>
                    </div>
                  )}
                </div>
              ) : (
                <div className="tp-empty">
                  <div>
                    <p className="big">select a test to review</p>
                    <p className="small">
                      click any test in the left panel to see details and
                      recommendations
                    </p>
                    {manifest?.last_run && (
                      <p className="small">
                        last run:{" "}
                        {new Date(manifest.last_run).toLocaleString()}
                      </p>
                    )}
                    {!manifest?.last_run && (
                      <p className="small">
                        no test results yet — click "run all tests" to start
                      </p>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default TestParade;
