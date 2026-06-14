// P&ID Copilot review pane — renders the graph + live annotations over WebSocket.
// An overlay, not an editor: buttons stand in for "an engineer saved a revision."

const WS_URL = `ws://${location.host}/ws`;
let cy = null;
let lastFindings = [];

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
        "label": "data(label)", "font-size": 10, "color": "#e6edf3",
        "text-valign": "bottom", "text-margin-y": 4, "width": 34, "height": 34,
        "background-color": "#30363d", "border-width": 2, "border-color": "#484f58",
        "shape": "ele => ele" } },
      { selector: "node", style: { "shape": (e) => TYPE_SHAPE[e.data("type")] || "ellipse" } },
      { selector: "edge", style: {
        "width": 2, "line-color": "#484f58", "target-arrow-color": "#484f58",
        "target-arrow-shape": "triangle", "curve-style": "bezier" } },
      { selector: "edge[kind = 'signal'], edge[kind = 'instrument']",
        style: { "line-style": "dashed" } },
      { selector: "node.red", style: { "border-color": "#f85149", "border-width": 4,
        "background-color": "#3d1d1d" } },
      { selector: "node.amber", style: { "border-color": "#d29922", "border-width": 4 } },
      { selector: "node.matched", style: { "border-color": "#58a6ff", "border-width": 4 } },
      { selector: "node.glow", style: { "border-color": "#3fb950", "border-width": 4,
        "background-color": "#13321c" } },
      { selector: ".ghost", style: { "border-style": "dashed", "line-style": "dashed",
        "opacity": 0.7, "border-color": "#8b949e", "line-color": "#8b949e",
        "background-color": "#21262d" } },
    ],
    layout: { name: "cose", animate: false },
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
  cy.layout({ name: "cose", animate: false }).run();
}

function applyAnnotations(msg) {
  lastFindings = msg.findings || [];
  cy.nodes().removeClass("red amber matched");
  cy.elements(".ghost").remove();

  document.getElementById("passing").textContent = msg.passing;
  document.getElementById("checks").textContent = msg.checks_run;
  document.getElementById("issues").textContent = msg.issues;
  document.getElementById("rev").textContent = msg.revision;

  for (const f of lastFindings) {
    for (const id of f.node_ids) cy.getElementById(id).addClass(f.severity);
    for (const id of f.matched_subgraph || []) cy.getElementById(id).addClass("matched");
    for (const ge of f.ghost_edges || []) addGhost(ge);
  }
  renderFindings(lastFindings);
  for (const r of msg.regressions || []) pushAlert("⏱ " + r);
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

function renderFindings(findings) {
  const ul = document.getElementById("findings");
  ul.innerHTML = "";
  for (const f of findings) {
    const li = document.createElement("li");
    li.className = f.severity;
    li.innerHTML = `<div><b>${f.rule_id}</b> ${f.message}</div>
      <div class="ref">${f.standard_ref}</div>`;
    if (f.fix) {
      const fix = document.createElement("div");
      fix.className = "fix";
      const btn = document.createElement("button");
      btn.textContent = "Accept fix: " + f.fix.summary;
      btn.onclick = () => send({ type: "accept_fix", rule_id: f.rule_id, node_ids: f.node_ids });
      fix.appendChild(btn);
      li.appendChild(fix);
    }
    const why = document.createElement("button");
    why.className = "why"; why.textContent = "Why?";
    why.onclick = () => send({ type: "why", rule_id: f.rule_id });
    li.appendChild(why);
    const expl = document.createElement("div");
    expl.className = "expl"; expl.id = "expl-" + f.rule_id;
    li.appendChild(expl);
    ul.appendChild(li);
  }
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
  ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.type === "graph") renderGraph(msg.graph);
    else if (msg.type === "annotations") {
      applyAnnotations(msg);
      if (msg.issues > 0) pushAlert(`Rev ${msg.revision}: ${msg.issues} issue(s) flagged.`);
    } else if (msg.type === "highlight") {
      cy.nodes().removeClass("glow");
      for (const id of msg.node_ids || []) {
        const byTag = cy.nodes().filter((n) => n.data("label") === id);
        (cy.getElementById(id).empty() ? byTag : cy.getElementById(id)).addClass("glow");
      }
      if (msg.answer) pushAlert("Q: " + msg.answer);
    } else if (msg.type === "explanation") {
      const el = document.getElementById("expl-" + msg.rule_id);
      if (el) el.textContent = msg.text;
    }
  };
  ws.onclose = () => setTimeout(connect, 1000);
}

function send(obj) { ws && ws.readyState === 1 && ws.send(JSON.stringify(obj)); }

document.querySelectorAll(".controls button").forEach((b) => {
  b.onclick = () => send({ type: "apply_revision", name: b.dataset.rev });
});

window.addEventListener("load", () => { initCy(); connect(); });
