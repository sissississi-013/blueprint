// P&ID Copilot review pane — renders the graph + live annotations over WebSocket.
// An overlay, not an editor: buttons stand in for "an engineer saved a revision."

const WS_URL = `ws://${location.host}/ws`;
let cy = null;
let lastFindings = [];
let activeFinding = null;

const {
  getReviewStatus,
  getPrimaryFinding,
  formatRevisionAction,
} = window.PaneModel;

const TYPE_SHAPE = {
  vessel: "round-rectangle", psv: "diamond", rupture_disc: "diamond",
  control_valve: "triangle", block_valve: "triangle", check_valve: "triangle",
  pump: "ellipse", compressor: "ellipse", instrument: "ellipse",
  flare: "vee", disposal: "vee", inlet: "tag", outlet: "tag",
};

function initCy() {
  cy = cytoscape({
    container: document.getElementById("cy"),
    style: [
      { selector: "node", style: {
        "label": "data(label)", "font-size": 13, "font-weight": 700, "color": "#f8fbff",
        "text-valign": "bottom", "text-margin-y": 7, "width": 52, "height": 52,
        "background-color": "#14213d", "border-width": 2, "border-color": "#74a0ff",
        "text-outline-color": "#05070d", "text-outline-width": 3 } },
      { selector: "node", style: { "shape": (e) => TYPE_SHAPE[e.data("type")] || "ellipse" } },
      { selector: "edge", style: {
        "width": 3, "line-color": "#53627f", "target-arrow-color": "#53627f",
        "target-arrow-shape": "triangle", "curve-style": "bezier" } },
      { selector: "edge[kind = 'signal'], edge[kind = 'instrument']",
        style: { "line-style": "dashed" } },
      { selector: "node.red", style: { "border-color": "#ff3b3b", "border-width": 7,
        "background-color": "#4c1111", "shadow-blur": 28, "shadow-color": "#ff3b3b",
        "shadow-opacity": 0.8 } },
      { selector: "node.amber", style: { "border-color": "#ffbd54", "border-width": 6,
        "background-color": "#3c2a10" } },
      { selector: "node.matched", style: { "border-color": "#74a0ff", "border-width": 6 } },
      { selector: "node.glow", style: { "border-color": "#52f29a", "border-width": 6,
        "background-color": "#0d3320", "shadow-blur": 22, "shadow-color": "#52f29a",
        "shadow-opacity": 0.65 } },
      { selector: ".ghost", style: { "border-style": "dashed", "line-style": "dashed",
        "opacity": 0.85, "border-color": "#c7d7ff", "line-color": "#c7d7ff",
        "background-color": "#172442", "width": 4, "target-arrow-color": "#c7d7ff" } },
    ],
    layout: { name: "cose", animate: false, padding: 90 },
    wheelSensitivity: 0.25,
  });
}

function renderGraph(g) {
  const els = [];
  for (const n of g.nodes) {
    els.push({ data: { id: n.id, label: n.tag || n.label || n.id, type: n.type } });
  }
  for (const e of g.edges) {
    els.push({ data: { id: e.id, source: e.source, target: e.target, kind: e.kind } });
  }
  cy.elements().remove();
  cy.add(els);
  cy.layout({ name: "cose", animate: false, padding: 90 }).run();
  setTimeout(() => cy.fit(undefined, 70), 80);
}

function applyAnnotations(msg) {
  lastFindings = msg.findings || [];
  activeFinding = getPrimaryFinding(lastFindings);
  cy.nodes().removeClass("red amber matched");
  cy.elements(".ghost").remove();

  renderStatus(msg);

  for (const f of lastFindings) {
    for (const id of f.node_ids) cy.getElementById(id).addClass(f.severity);
    for (const id of f.matched_subgraph || []) cy.getElementById(id).addClass("matched");
    for (const ge of f.ghost_edges || []) addGhost(ge);
  }
  if (lastFindings.length) cy.layout({ name: "cose", animate: false, padding: 90 }).run();
  setTimeout(() => cy.fit(undefined, 70), 80);

  renderPrimaryFinding(activeFinding);
  for (const r of msg.regressions || []) pushAlert("Saved: " + r);
}

function addGhost(ge) {
  let target = ge.target;
  if (ge.implied_node) {
    const n = ge.implied_node;
    if (cy.getElementById(n.id).empty()) {
      cy.add({ group: "nodes", data: { id: n.id, label: n.label || n.tag, type: n.type },
        classes: "ghost" });
    }
    target = n.id;
  }
  if (ge.source && target) {
    cy.add({ group: "edges", classes: "ghost",
      data: { id: "ghost-" + ge.source + "-" + target, source: ge.source, target } });
  }
}

function renderStatus(msg) {
  const status = getReviewStatus(msg);
  const card = document.getElementById("status-card");
  card.className = `status-card ${status.tone}`;
  document.getElementById("status-label").textContent = status.label;
  document.getElementById("status-headline").textContent = status.headline;
  document.getElementById("status-detail").textContent = status.detail;
  document.getElementById("scoreline").textContent = `checks clear: ${msg.passing}/${msg.checks_run}`;
}

function renderPrimaryFinding(finding) {
  const title = document.getElementById("primary-title");
  const message = document.getElementById("primary-message");
  const fixButton = document.getElementById("primary-fix");
  const whyButton = document.getElementById("why-btn");
  const explanation = document.getElementById("explanation");

  explanation.textContent = "";

  if (!finding) {
    title.textContent = "Graph is clear";
    message.textContent = "No safety or compliance issue is active in this revision.";
    fixButton.hidden = true;
    whyButton.hidden = true;
    return;
  }

  title.textContent = finding.rule_id + " " + finding.severity.toUpperCase();
  message.textContent = finding.message;
  fixButton.hidden = !finding.fix;
  fixButton.textContent = finding.fix ? "Accept fix: " + finding.fix.summary : "Accept fix";
  whyButton.hidden = false;
}

function pushAlert(text) {
  const ul = document.getElementById("alerts");
  const li = document.createElement("li");
  li.textContent = text;
  ul.prepend(li);
}

let ws;
function connect() {
  ws = new WebSocket(WS_URL);
  ws.onopen = () => {
    const connection = document.getElementById("connection");
    connection.textContent = "Live";
    connection.classList.add("live");
  };
  ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.type === "graph") renderGraph(msg.graph);
    else if (msg.type === "annotations") {
      applyAnnotations(msg);
      if (msg.issues > 0) pushAlert(`Revision ${msg.revision}: ${msg.issues} issue(s) flagged.`);
      else pushAlert(`Revision ${msg.revision}: all checks passing.`);
    } else if (msg.type === "highlight") {
      cy.nodes().removeClass("glow");
      for (const id of msg.node_ids || []) {
        const byTag = cy.nodes().filter((n) => n.data("label") === id);
        (cy.getElementById(id).empty() ? byTag : cy.getElementById(id)).addClass("glow");
      }
      if (msg.answer) pushAlert("Answer: " + msg.answer);
    } else if (msg.type === "explanation") {
      if (activeFinding && activeFinding.rule_id === msg.rule_id) {
        document.getElementById("explanation").textContent = msg.text;
      }
    }
  };
  ws.onclose = () => {
    const connection = document.getElementById("connection");
    connection.textContent = "Reconnecting";
    connection.classList.remove("live");
    setTimeout(connect, 1000);
  };
}

function send(obj) { ws && ws.readyState === 1 && ws.send(JSON.stringify(obj)); }

document.querySelectorAll(".controls button").forEach((b) => {
  b.textContent = formatRevisionAction(b.dataset.rev);
  b.onclick = () => send({ type: "apply_revision", name: b.dataset.rev });
});

document.getElementById("primary-fix").onclick = () => {
  if (!activeFinding || !activeFinding.fix) return;
  send({ type: "accept_fix", rule_id: activeFinding.rule_id, node_ids: activeFinding.node_ids });
};

document.getElementById("why-btn").onclick = () => {
  if (!activeFinding) return;
  send({ type: "why", rule_id: activeFinding.rule_id });
};

window.addEventListener("load", () => { initCy(); connect(); });
