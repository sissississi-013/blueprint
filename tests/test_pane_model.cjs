const assert = require("node:assert/strict");
const test = require("node:test");

const {
  getReviewStatus,
  getPrimaryFinding,
  formatRevisionAction,
} = require("../web/pane-model.cjs");

test("summarizes a clean graph as a safe visual state", () => {
  const status = getReviewStatus({ issues: 0, passing: 12, checks_run: 12, revision: 4 });

  assert.deepEqual(status, {
    tone: "safe",
    label: "Safe",
    headline: "All checks passing",
    detail: "12 of 12 checks clear · revision 4",
  });
});

test("summarizes active findings as an issue visual state", () => {
  const status = getReviewStatus({ issues: 2, passing: 10, checks_run: 12, revision: 5 });

  assert.deepEqual(status, {
    tone: "issue",
    label: "Issue found",
    headline: "2 issues need review",
    detail: "10 of 12 checks clear · revision 5",
  });
});

test("selects the most important finding and formats its primary action", () => {
  const finding = getPrimaryFinding([
    { rule_id: "R3", severity: "amber", message: "Fail position missing" },
    {
      rule_id: "R1",
      severity: "red",
      message: "V-101 has no relief path",
      fix: { summary: "add PSV-101 and route to flare" },
    },
  ]);

  assert.equal(finding.rule_id, "R1");
  assert.equal(formatRevisionAction("delete_psv_101"), "Remove relief valve");
});
