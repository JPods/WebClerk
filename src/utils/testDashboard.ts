/**
 * Dashboard Endpoint Tester
 *
 * Run this in the browser console to test the dashboard endpoint
 */

window.testDashboardEndpoint = async function () {
  console.log("🔍 Testing dashboard endpoint...\n");

  const apiUrl = "http://localhost:8000";
  const endpoint = "/wcapi/get/?model_name=dashboard";
  const url = apiUrl + endpoint;

  console.log(`📍 URL: ${url}\n`);

  try {
    // Test 1: Simple fetch
    console.log("Test 1: Simple GET request...");
    const res1 = await fetch(url);
    console.log(`  Status: ${res1.status} ${res1.statusText}`);
    console.log(`  Headers:`, {
      "content-type": res1.headers.get("content-type"),
      "access-control-allow-origin": res1.headers.get(
        "access-control-allow-origin",
      ),
    });

    const data1 = await res1.json();
    console.log(`  ✅ Response OK:`, data1);

    // Test 2: With credentials
    console.log("\nTest 2: GET request with credentials...");
    const res2 = await fetch(url, {
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
      },
    });
    console.log(`  Status: ${res2.status} ${res2.statusText}`);
    const data2 = await res2.json();
    console.log(`  ✅ Response OK:`, data2);

    // Test 3: With Authorization header
    console.log("\nTest 3: GET request with Authorization header...");
    const { getAccessToken } = await import("../api/axios");
    const token = getAccessToken();
    console.log(`  Token found: ${token ? "✅ Yes" : "❌ No"}`);

    if (token) {
      const res3 = await fetch(url, {
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
      });
      console.log(`  Status: ${res3.status} ${res3.statusText}`);
      const data3 = await res3.json();
      console.log(`  ✅ Response OK:`, data3);
    } else {
      console.log(`  ⚠️ Skipped (no token - not logged in)`);
    }

    // Test 4: Axios (if available)
    if (window.axios) {
      console.log("\nTest 4: Using Axios...");
      try {
        const res4 = await window.axios.get(url);
        console.log(`  Status: ${res4.status} ${res4.statusText}`);
        console.log(`  ✅ Response OK:`, res4.data);
      } catch (err) {
        console.error(`  ❌ Error:`, {
          code: err.code,
          message: err.message,
          status: err.response?.status,
          data: err.response?.data,
        });
      }
    }
  } catch (err) {
    console.error("❌ Test failed:", err.message);
    console.error(err);
  }

  console.log("\n✅ Dashboard endpoint tests complete!");
};

// Auto-run when script loads
console.log("📦 Dashboard Endpoint Tester loaded");
console.log("   Run: window.testDashboardEndpoint()\n");

// Also export for use in components
if (typeof window !== "undefined") {
  window.testDashboardEndpoint();
}
