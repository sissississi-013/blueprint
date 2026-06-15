(function (root, factory) {
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (root) root.PaneModel = api;
})(typeof window !== "undefined" ? window : globalThis, function () {
  const REVISION_ACTIONS = {
    delete_psv_101: "Remove relief valve",
    strip_fail_position: "Clear fail position",
    duplicate_tag: "Duplicate tag",
    delete_level_instrument: "Remove level instrument",
  };

  function pluralize(count, singular, plural) {
    return count === 1 ? singular : plural;
  }

  function getReviewStatus(report) {
    const issues = Number(report && report.issues) || 0;
    const passing = Number(report && report.passing) || 0;
    const checksRun = Number(report && report.checks_run) || 0;
    const revision = report && report.revision != null ? report.revision : "-";

    if (issues === 0) {
      return {
        tone: "safe",
        label: "Safe",
        headline: "All checks passing",
        detail: `${passing} of ${checksRun} checks clear · revision ${revision}`,
      };
    }

    return {
      tone: "issue",
      label: "Issue found",
      headline: `${issues} ${pluralize(issues, "issue", "issues")} need review`,
      detail: `${passing} of ${checksRun} checks clear · revision ${revision}`,
    };
  }

  function getPrimaryFinding(findings) {
    const list = Array.isArray(findings) ? findings : [];
    return list.find((finding) => finding.severity === "red") || list[0] || null;
  }

  function formatRevisionAction(name) {
    return REVISION_ACTIONS[name] || name;
  }

  return { getReviewStatus, getPrimaryFinding, formatRevisionAction };
});
