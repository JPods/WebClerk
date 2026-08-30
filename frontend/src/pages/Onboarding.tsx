/**
 * Onboarding — Registration + Subscription for new WebClerk installations.
 *
 * Three steps:
 *   1. Who are you? (name, email, company)
 *   2. What do you need? (industry, goals, pain points)
 *   3. Choose your plan (community, starter, professional, enterprise)
 *
 * On submit: POST to webclerk.com/wcapi/register-installation/
 * Receives Athena token, stores it in local Connection record.
 */
import { useState } from "react";
import axios from "axios";

const WCHQ_URL = "https://webclerk.com";

// Pricing: $14 per 5 staff users. Alice counts is_staff.
const PRICE_PER_5 = 14;

interface FormData {
  name_first: string;
  name_last: string;
  email: string;
  company: string;
  industry: string;
  website: string;
  goals: string[];
  pain_points: string[];
  subscribed: boolean;
  donation_amount: number;
}

const GOAL_OPTIONS = [
  "Replace spreadsheets",
  "Manage inventory",
  "Track sales pipeline",
  "Invoice customers",
  "Purchase management",
  "Team task management",
  "Customer portal",
  "Multi-location operations",
];

const PAIN_OPTIONS = [
  "Data scattered across tools",
  "No inventory visibility",
  "Manual invoicing",
  "Can't track what's owed",
  "Team coordination",
  "Reporting is painful",
  "Current software too expensive",
  "Outgrew current system",
];

const Onboarding: React.FC = () => {
  const [step, setStep] = useState(1);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<{ token?: string; error?: string } | null>(null);
  const [form, setForm] = useState<FormData>({
    name_first: "",
    name_last: "",
    email: "",
    company: "",
    industry: "",
    website: "",
    goals: [],
    pain_points: [],
    subscribed: false,
    donation_amount: 0,
  });

  const update = (field: keyof FormData, value: string | number | boolean | string[]) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const toggleList = (field: "goals" | "pain_points", item: string) => {
    setForm((prev) => {
      const list = prev[field];
      return {
        ...prev,
        [field]: list.includes(item) ? list.filter((i) => i !== item) : [...list, item],
      };
    });
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      // Generate installation ID
      const installation_id = crypto.randomUUID();

      const payload = {
        installation_id,
        contact: {
          name_first: form.name_first,
          name_last: form.name_last,
          email: form.email,
        },
        company: {
          name: form.company,
          industry: form.industry,
          website: form.website,
        },
        onboarding: {
          goals: form.goals,
          pain_points: form.pain_points,
        },
        subscribed: form.subscribed,
        staff_count: 0,  // Alice will count on first run
      };

      // Register with WCHQ
      const resp = await axios.post(`${WCHQ_URL}/wcapi/register-installation/`, payload);

      // Store the Athena token locally
      const token = resp.data.token;
      await axios.post("/wcapi/save/", {
        model_name: "setting",
        data: {
          name: "WCHQ Connection",
          purpose: "wchq_connection",
          scope: "system",
          config: {
            athena_token: token,
            installation_id,
            subscribed: form.subscribed,
            dt_registered: resp.data.dt_registered,
          },
        },
      });

      // Store subscription
      await axios.post("/wcapi/save/", {
        model_name: "setting",
        data: {
          name: "Subscription",
          purpose: "wc:subscription",
          scope: "system",
          config: {
            subscribed: form.subscribed,
            dt_started: resp.data.dt_registered,
          },
        },
      });

      setResult({ token: token.slice(0, 12) + "..." });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Registration failed";
      setResult({ error: msg });
    } finally {
      setSubmitting(false);
    }
  };

  if (result) {
    return (
      <div className="max-w-xl mx-auto mt-16 p-8 bg-white rounded-lg shadow">
        {result.error ? (
          <>
            <h2 className="text-xl font-semibold text-red-600 mb-4">Registration Failed</h2>
            <p className="text-gray-700">{result.error}</p>
            <button
              className="mt-6 px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              onClick={() => setResult(null)}
            >
              Try Again
            </button>
          </>
        ) : (
          <>
            <h2 className="text-xl font-semibold text-green-600 mb-4">Welcome to WebClerk</h2>
            <p className="text-gray-700 mb-2">
              Your installation is registered. Athena token: <code className="bg-gray-100 px-2 py-1 rounded">{result.token}</code>
            </p>
            <p className="text-gray-500 text-sm mb-6">
              This token connects your installation to WebClerk HQ for settings sync, Alice AI, and support.
            </p>
            <a
              href="/dashboard"
              className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 inline-block"
            >
              Go to Dashboard
            </a>
          </>
        )}
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto mt-12 p-8">
      <h1 className="text-2xl font-bold mb-2">Set Up WebClerk</h1>
      <p className="text-gray-500 mb-8">Step {step} of 3</p>

      {/* Progress bar */}
      <div className="flex gap-2 mb-8">
        {[1, 2, 3].map((s) => (
          <div
            key={s}
            className={`h-1.5 flex-1 rounded ${s <= step ? "bg-blue-600" : "bg-gray-200"}`}
          />
        ))}
      </div>

      {/* Step 1: Identity */}
      {step === 1 && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold">Who are you?</h2>
          <div className="grid grid-cols-2 gap-4">
            <input
              className="border rounded px-3 py-2"
              placeholder="First name"
              value={form.name_first}
              onChange={(e) => update("name_first", e.target.value)}
            />
            <input
              className="border rounded px-3 py-2"
              placeholder="Last name"
              value={form.name_last}
              onChange={(e) => update("name_last", e.target.value)}
            />
          </div>
          <input
            className="border rounded px-3 py-2 w-full"
            placeholder="Email"
            type="email"
            value={form.email}
            onChange={(e) => update("email", e.target.value)}
          />
          <input
            className="border rounded px-3 py-2 w-full"
            placeholder="Company name"
            value={form.company}
            onChange={(e) => update("company", e.target.value)}
          />
          <div className="grid grid-cols-2 gap-4">
            <input
              className="border rounded px-3 py-2"
              placeholder="Industry"
              value={form.industry}
              onChange={(e) => update("industry", e.target.value)}
            />
            <input
              className="border rounded px-3 py-2"
              placeholder="Website (optional)"
              value={form.website}
              onChange={(e) => update("website", e.target.value)}
            />
          </div>
          <button
            className="mt-4 px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            disabled={!form.email || !form.name_first}
            onClick={() => setStep(2)}
          >
            Next
          </button>
        </div>
      )}

      {/* Step 2: Goals */}
      {step === 2 && (
        <div className="space-y-6">
          <div>
            <h2 className="text-lg font-semibold mb-3">What are your goals?</h2>
            <div className="grid grid-cols-2 gap-2">
              {GOAL_OPTIONS.map((g) => (
                <button
                  key={g}
                  className={`text-left px-3 py-2 border rounded text-sm ${
                    form.goals.includes(g) ? "bg-blue-50 border-blue-400" : "hover:bg-gray-50"
                  }`}
                  onClick={() => toggleList("goals", g)}
                >
                  {form.goals.includes(g) ? "* " : ""}{g}
                </button>
              ))}
            </div>
          </div>
          <div>
            <h2 className="text-lg font-semibold mb-3">What pain points are you solving?</h2>
            <div className="grid grid-cols-2 gap-2">
              {PAIN_OPTIONS.map((p) => (
                <button
                  key={p}
                  className={`text-left px-3 py-2 border rounded text-sm ${
                    form.pain_points.includes(p) ? "bg-blue-50 border-blue-400" : "hover:bg-gray-50"
                  }`}
                  onClick={() => toggleList("pain_points", p)}
                >
                  {form.pain_points.includes(p) ? "* " : ""}{p}
                </button>
              ))}
            </div>
          </div>
          <div className="flex gap-3">
            <button className="px-6 py-2 border rounded hover:bg-gray-50" onClick={() => setStep(1)}>
              Back
            </button>
            <button
              className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              onClick={() => setStep(3)}
            >
              Next
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Subscribe */}
      {step === 3 && (
        <div className="space-y-6">
          <h2 className="text-lg font-semibold">Alice AI + Support</h2>
          <p className="text-gray-500 text-sm">
            WebClerk is free and open source. Always. The subscription adds Alice cloud AI
            and a direct support channel — priced by how many people use it.
          </p>

          {/* Two options */}
          <div className="grid grid-cols-2 gap-4">
            <button
              className={`text-left p-6 border rounded-lg ${
                !form.subscribed ? "border-blue-500 bg-blue-50 ring-2 ring-blue-200" : "hover:bg-gray-50"
              }`}
              onClick={() => update("subscribed", false)}
            >
              <div className="font-semibold text-lg">Community</div>
              <div className="text-blue-600 font-bold text-xl mt-1">Free</div>
              <ul className="mt-3 text-sm text-gray-600 space-y-1">
                <li>- All WebClerk features</li>
                <li>- Alice pattern detection</li>
                <li>- Settings sync from WCHQ</li>
                <li>- Run your own Ollama for AI</li>
              </ul>
            </button>
            <button
              className={`text-left p-6 border rounded-lg ${
                form.subscribed ? "border-blue-500 bg-blue-50 ring-2 ring-blue-200" : "hover:bg-gray-50"
              }`}
              onClick={() => update("subscribed", true)}
            >
              <div className="font-semibold text-lg">Subscribe</div>
              <div className="text-blue-600 font-bold text-xl mt-1">${PRICE_PER_5}/mo per 5 users</div>
              <ul className="mt-3 text-sm text-gray-600 space-y-1">
                <li>- Everything in Community</li>
                <li>- Alice cloud AI (no Ollama needed)</li>
                <li>- Direct support channel</li>
                <li>- Alice counts your staff — price adjusts automatically</li>
              </ul>
            </button>
          </div>

          {form.subscribed && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-sm text-gray-700">
              Alice will count your active staff users and report monthly. A company with 12 staff users
              pays ${Math.ceil(12 / 5) * PRICE_PER_5}/mo. Price adjusts as your team grows or shrinks.
              No contracts. Cancel anytime.
            </div>
          )}

          {/* Donation */}
          <div className="flex items-center gap-3">
            <label className="text-sm text-gray-600">Support WebClerk with a donation:</label>
            <select
              className="border rounded px-3 py-1.5"
              value={form.donation_amount}
              onChange={(e) => update("donation_amount", parseInt(e.target.value))}
            >
              <option value={0}>No thanks</option>
              <option value={10}>$10</option>
              <option value={25}>$25</option>
              <option value={50}>$50</option>
              <option value={100}>$100</option>
            </select>
          </div>

          <div className="flex gap-3 pt-4">
            <button className="px-6 py-2 border rounded hover:bg-gray-50" onClick={() => setStep(2)}>
              Back
            </button>
            <button
              className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
              disabled={submitting}
              onClick={handleSubmit}
            >
              {submitting ? "Registering..." : "Complete Setup"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default Onboarding;
