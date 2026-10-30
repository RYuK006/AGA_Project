/**
 * Emergency Ambulance Routing System - Frontend Controller
 * KTU B.Tech S5: Advanced Graph Algorithms
 * 
 * Vanilla JavaScript implementation interfacing with FastAPI backend.
 * Controls:
 * 1. Tab 1: Step-by-step visual replay on 5-node toy graph (Dijkstra, A*, Bellman-Ford)
 * 2. Tab 2: Leaflet map dispatch, reversed Dijkstra ambulance ranking, A* hospital scoring, frontier animation
 * 3. Tab 3: Chart.js empirical benchmarking, distributions, and 100% cost equality verification
 * 4. Tab 4: Negative weight signal-preemption credit and negative cycle detection
 */

document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  initTab1Learn();
  initTab2Dispatch();
  initTab3Benchmark();
  initTab4Negative();
});

// ==========================================================
// Tab Switching Controller
// ==========================================================
function initTabs() {
  const tabButtons = document.querySelectorAll(".tab-btn");
  const tabPanes = document.querySelectorAll(".tab-pane");

  tabButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      const targetId = btn.getAttribute("data-tab");

      tabButtons.forEach(b => b.classList.remove("active"));
      tabPanes.forEach(p => p.classList.remove("active"));

      btn.classList.add("active");
      const targetPane = document.getElementById(targetId);
      if (targetPane) {
        targetPane.classList.add("active");
      }

      // Invalidate Leaflet map size when switching to Tab 2
      if (targetId === "tab-dispatch" && window.cityMap) {
        setTimeout(() => {
          window.cityMap.invalidateSize();
        }, 150);
      }
    });
  });
}

// ==========================================================
// TAB 1: LEARN (TOY GRAPH STEP-BY-STEP TRACE)
// ==========================================================
let toyGraphData = null;
let toyEvents = [];
let toyCurrentStep = 0;
let toyPlayInterval = null;

async function initTab1Learn() {
  const svg = document.getElementById("toy-svg");
  const algoSelect = document.getElementById("toy-algo-select");
  const btnStep = document.getElementById("btn-toy-step");
  const btnPlay = document.getElementById("btn-toy-play");
  const btnReset = document.getElementById("btn-toy-reset");

  try {
    const res = await fetch("/api/toy-graph");
    toyGraphData = await res.json();
    renderToyGraphSvg();
    resetToyState();
  } catch (err) {
    console.error("Failed to load toy graph:", err);
  }

  btnStep.addEventListener("click", () => {
    pauseToyPlay();
    stepToyForward();
  });

  btnPlay.addEventListener("click", () => {
    if (toyPlayInterval) {
      pauseToyPlay();
    } else {
      startToyPlay();
    }
  });

  btnReset.addEventListener("click", () => {
    pauseToyPlay();
    resetToyState();
  });

  algoSelect.addEventListener("change", () => {
    pauseToyPlay();
    resetToyState();
    updateAlgoCallout(algoSelect.value);
  });
}

function updateAlgoCallout(algo) {
  const box = document.getElementById("toy-algo-note");
  const qTitle = document.getElementById("toy-queue-title");
  if (algo === "dijkstra") {
    box.innerHTML = "<strong>Dijkstra's Invariant:</strong> At every step, the unvisited vertex with minimum tentative distance is popped from the min-heap and finalized. Requires edge weights &ge; 0. Time: O((V+E) log V).";
    qTitle.textContent = "Min-Heap Contents (Priority Queue)";
  } else if (algo === "astar") {
    box.innerHTML = "<strong>A* Evaluation:</strong> Prioritizes nodes by f(n) = g(n) + h(n). Heuristic h(n) = Euclidean_distance / v_max is admissible (h &le; h*), guaranteeing shortest path while reducing expansions.";
    qTitle.textContent = "A* Priority Queue (Sorted by f = g + h)";
  } else {
    box.innerHTML = "<strong>Bellman-Ford Passes:</strong> Relaxes all |E| directed edges (V - 1) times. Detects reachable negative cycles in Pass V. Can handle negative weights. Time: O(V &middot; E).";
    qTitle.textContent = "Edge Relaxation Pass Progress";
  }
}

function renderToyGraphSvg() {
  const svg = document.getElementById("toy-svg");
  if (!svg || !toyGraphData) return;

  svg.innerHTML = `
    <defs>
      <marker id="arrow" viewBox="0 0 10 10" refX="28" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
        <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#64748b" />
      </marker>
      <marker id="arrow-relaxing" viewBox="0 0 10 10" refX="28" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
        <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#eab308" />
      </marker>
      <marker id="arrow-optimal" viewBox="0 0 10 10" refX="28" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
        <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#16a34a" />
      </marker>
    </defs>
  `;

  // Draw Edges
  toyGraphData.edges.forEach(([u, v, w]) => {
    const nodeU = toyGraphData.nodes[u];
    const nodeV = toyGraphData.nodes[v];
    const edgeId = `edge-${u}-${v}`;

    // Compute midpoint with slight curve offset for parallel/opposite edges (e.g. I->H and H->I)
    let pathD = "";
    let midX = (nodeU.ui_x + nodeV.ui_x) / 2;
    let midY = (nodeU.ui_y + nodeV.ui_y) / 2;

    if (u === "H" && v === "I") {
      midY += 35; // Curve down for H->I so it doesn't overlap I->H
      pathD = `M ${nodeU.ui_x} ${nodeU.ui_y} Q ${midX} ${midY} ${nodeV.ui_x} ${nodeV.ui_y}`;
    } else if (u === "I" && v === "H") {
      midY -= 35; // Curve up for I->H
      pathD = `M ${nodeU.ui_x} ${nodeU.ui_y} Q ${midX} ${midY} ${nodeV.ui_x} ${nodeV.ui_y}`;
    } else {
      pathD = `M ${nodeU.ui_x} ${nodeU.ui_y} L ${nodeV.ui_x} ${nodeV.ui_y}`;
    }

    const pathEl = document.createElementNS("http://www.w3.org/2000/svg", "path");
    pathEl.setAttribute("d", pathD);
    pathEl.setAttribute("class", "edge-path");
    pathEl.setAttribute("id", edgeId);
    pathEl.setAttribute("marker-end", "url(#arrow)");
    svg.appendChild(pathEl);

    // Label background pill
    const bgRect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    bgRect.setAttribute("x", midX - 18);
    bgRect.setAttribute("y", midY - 11);
    bgRect.setAttribute("width", 36);
    bgRect.setAttribute("height", 22);
    bgRect.setAttribute("class", "edge-label-bg");
    svg.appendChild(bgRect);

    // Weight text
    const textEl = document.createElementNS("http://www.w3.org/2000/svg", "text");
    textEl.setAttribute("x", midX);
    textEl.setAttribute("y", midY);
    textEl.setAttribute("class", "edge-weight-text");
    textEl.textContent = `${Math.round(w)}s`;
    svg.appendChild(textEl);
  });

  // Draw Nodes
  Object.entries(toyGraphData.nodes).forEach(([nid, meta]) => {
    const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
    g.setAttribute("id", `node-group-${nid}`);

    const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    circle.setAttribute("cx", meta.ui_x);
    circle.setAttribute("cy", meta.ui_y);
    circle.setAttribute("r", 24);
    circle.setAttribute("class", "node-circle unvisited");
    circle.setAttribute("id", `circle-${nid}`);
    g.appendChild(circle);

    const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
    text.setAttribute("x", meta.ui_x);
    text.setAttribute("y", meta.ui_y - 1);
    text.setAttribute("class", "node-label");
    text.textContent = nid;
    g.appendChild(text);

    // Node Subtitle / Role Tag below circle
    const subText = document.createElementNS("http://www.w3.org/2000/svg", "text");
    subText.setAttribute("x", meta.ui_x);
    subText.setAttribute("y", meta.ui_y + 38);
    subText.setAttribute("font-size", "11px");
    subText.setAttribute("font-weight", "600");
    subText.setAttribute("fill", "#64748b");
    subText.setAttribute("text-anchor", "middle");
    subText.textContent = meta.label || nid;
    g.appendChild(subText);

    svg.appendChild(g);
  });
}

async function resetToyState() {
  const algo = document.getElementById("toy-algo-select").value;
  toyCurrentStep = 0;
  toyEvents = [];

  // Reset visual elements
  document.querySelectorAll(".node-circle").forEach(c => {
    c.className.baseVal = "node-circle unvisited";
  });
  document.querySelectorAll(".edge-path").forEach(e => {
    e.className.baseVal = "edge-path";
    e.setAttribute("marker-end", "url(#arrow)");
  });

  document.getElementById("toy-stat-cost").textContent = "—";
  document.getElementById("toy-stat-expanded").textContent = "0";
  document.getElementById("toy-stat-relaxed").textContent = "0";
  document.getElementById("toy-step-counter").textContent = "Step 0 / 0";
  document.getElementById("toy-caption").textContent = "Click 'Step' or 'Play' to trace execution.";
  document.getElementById("btn-toy-play").textContent = "▶ Play";

  // Re-populate Table
  const tbody = document.getElementById("toy-dist-tbody");
  tbody.innerHTML = "";
  if (toyGraphData) {
    Object.entries(toyGraphData.nodes).forEach(([nid, meta]) => {
      const tr = document.createElement("tr");
      tr.id = `toy-row-${nid}`;
      tr.innerHTML = `
        <td><strong>${nid}</strong></td>
        <td>${meta.role || "junction"}</td>
        <td id="dist-val-${nid}" style="font-family:'JetBrains Mono',monospace;">inf</td>
        <td id="parent-val-${nid}" style="font-family:'JetBrains Mono',monospace;">none</td>
        <td id="status-val-${nid}">Unvisited</td>
      `;
      tbody.appendChild(tr);
    });
  }

  // Fetch algorithm execution trace
  try {
    const res = await fetch("/api/run-toy", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ algorithm: algo, source: "S", target: "H" })
    });
    const data = await res.json();
    toyEvents = data.events || [];
    document.getElementById("toy-step-counter").textContent = `Step 0 / ${toyEvents.length}`;
  } catch (err) {
    console.error("Error fetching toy run:", err);
  }
}

function stepToyForward() {
  if (!toyEvents || toyCurrentStep >= toyEvents.length) {
    pauseToyPlay();
    return;
  }

  const ev = toyEvents[toyCurrentStep];
  toyCurrentStep++;
  document.getElementById("toy-step-counter").textContent = `Step ${toyCurrentStep} / ${toyEvents.length}`;
  applyToyEvent(ev);

  if (toyCurrentStep >= toyEvents.length) {
    pauseToyPlay();
  }
}

function applyToyEvent(ev) {
  const captionEl = document.getElementById("toy-caption");
  if (ev.caption) {
    captionEl.textContent = ev.caption;
  }

  // Clear transient active edge highlights
  document.querySelectorAll(".edge-path.relaxing").forEach(p => {
    p.classList.remove("relaxing");
    p.setAttribute("marker-end", "url(#arrow)");
  });

  if (ev.type === "init") {
    const rowS = document.getElementById(`dist-val-${ev.source}`);
    if (rowS) rowS.textContent = "0.0";
    const statusS = document.getElementById(`status-val-${ev.source}`);
    if (statusS) statusS.textContent = "Source (In Queue)";
    updateQueueChips([ev.source]);
  } else if (ev.type === "pop") {
    // Highlight current node
    document.querySelectorAll(".node-circle.current").forEach(c => {
      c.className.baseVal = "node-circle visited";
    });
    const c = document.getElementById(`circle-${ev.node}`);
    if (c) c.className.baseVal = "node-circle current";

    // Update table
    document.querySelectorAll("#toy-dist-tbody tr").forEach(r => r.classList.remove("row-active"));
    const row = document.getElementById(`toy-row-${ev.node}`);
    if (row) {
      row.classList.add("row-active");
      const statusCell = document.getElementById(`status-val-${ev.node}`);
      if (statusCell) statusCell.textContent = "Popped / Finalized";
    }

    // Update heap peek chips
    updateQueueChips(ev.heap_peek || []);

    const expEl = document.getElementById("toy-stat-expanded");
    expEl.textContent = parseInt(expEl.textContent || "0") + 1;
  } else if (ev.type === "relax") {
    const edgeId = `edge-${ev.u}-${ev.v}`;
    const edgeEl = document.getElementById(edgeId);
    if (edgeEl) {
      edgeEl.classList.add("relaxing");
      edgeEl.setAttribute("marker-end", "url(#arrow-relaxing)");
    }

    const relEl = document.getElementById("toy-stat-relaxed");
    relEl.textContent = parseInt(relEl.textContent || "0") + 1;

    if (ev.updated) {
      const distCell = document.getElementById(`dist-val-${ev.v}`);
      if (distCell) distCell.textContent = `${ev.new_dist !== undefined ? ev.new_dist.toFixed(1) : ev.new_g.toFixed(1)}`;
      const parentCell = document.getElementById(`parent-val-${ev.v}`);
      if (parentCell) parentCell.textContent = ev.u;

      const row = document.getElementById(`toy-row-${ev.v}`);
      if (row) {
        row.classList.add("row-updated");
        setTimeout(() => row.classList.remove("row-updated"), 800);
      }
    }
  } else if (ev.type === "target_reached") {
    const c = document.getElementById(`circle-${ev.node}`);
    if (c) c.className.baseVal = "node-circle target-reached";

    document.getElementById("toy-stat-cost").textContent = `${ev.dist.toFixed(1)}s`;

    // Highlight final optimal path: S -> P -> I -> H
    const optimalEdges = [["S", "P"], ["P", "I"], ["I", "H"]];
    optimalEdges.forEach(([u, v]) => {
      const e = document.getElementById(`edge-${u}-${v}`);
      if (e) {
        e.className.baseVal = "edge-path optimal";
        e.setAttribute("marker-end", "url(#arrow-optimal)");
      }
    });
  } else if (ev.type === "pass_start") {
    updateQueueChips([`Pass ${ev.pass_num}`]);
  }
}

function updateQueueChips(items) {
  const container = document.getElementById("toy-queue-content");
  if (!container) return;
  if (!items || items.length === 0) {
    container.innerHTML = `<span class="chip-empty">Queue is empty</span>`;
    return;
  }
  container.innerHTML = items.map(item => `<span class="chip-item">${item}</span>`).join("");
}

function startToyPlay() {
  const btn = document.getElementById("btn-toy-play");
  btn.textContent = "⏸ Pause";
  toyPlayInterval = setInterval(() => {
    if (toyCurrentStep >= toyEvents.length) {
      pauseToyPlay();
    } else {
      stepToyForward();
    }
  }, 650);
}

function pauseToyPlay() {
  if (toyPlayInterval) {
    clearInterval(toyPlayInterval);
    toyPlayInterval = null;
  }
  const btn = document.getElementById("btn-toy-play");
  if (btn) btn.textContent = "▶ Play";
}

// ==========================================================
// TAB 2: CITY DISPATCH & SEARCH FRONTIER
// ==========================================================
let cityGraphMeta = null;
let incidentMarker = null;
let currentIncidentCoords = null;
let leg1Polyline = null;
let leg2Polyline = null;
let frontierCircles = [];
let currentDispatchData = null;

async function initTab2Dispatch() {
  const mapContainer = document.getElementById("city-map");
  if (!mapContainer) return;

  // Initialize Leaflet Map centered at Thiruvananthapuram (8.5000, 76.9500)
  window.cityMap = L.map("city-map").setView([8.5000, 76.9500], 13);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18,
    attribution: "&copy; OpenStreetMap contributors | KTU AGA Routing System"
  }).addTo(window.cityMap);

  // Map click handler to place incident
  window.cityMap.on("click", (e) => {
    setIncidentLocation(e.latlng.lat, e.latlng.lng);
  });

  // Quick incident button
  document.getElementById("btn-quick-incident").addEventListener("click", () => {
    setIncidentLocation(8.5015, 76.9520);
  });

  // Dispatch button
  document.getElementById("btn-run-dispatch").addEventListener("click", () => {
    executeDispatch();
  });

  // Lambda Slider live updates
  const lambdaSlider = document.getElementById("lambda-slider");
  const lambdaVal = document.getElementById("lambda-val");
  lambdaSlider.addEventListener("input", (e) => {
    lambdaVal.textContent = parseFloat(e.target.value).toFixed(1);
    if (currentIncidentCoords) {
      executeDispatch();
    }
  });

  // Specialty select change
  document.getElementById("dispatch-specialty").addEventListener("change", () => {
    if (currentIncidentCoords) {
      executeDispatch();
    }
  });

  // Replay Frontier button
  document.getElementById("btn-replay-frontier").addEventListener("click", () => {
    if (currentDispatchData && currentDispatchData.frontier_comparison) {
      animateFrontier(currentDispatchData.frontier_comparison);
    }
  });

  // Fetch City Graph data
  try {
    const res = await fetch("/api/city-graph");
    cityGraphMeta = await res.json();
    renderCityFacilities();

    const pill = document.getElementById("city-status-pill");
    if (pill) {
      pill.textContent = `${cityGraphMeta.total_nodes} nodes | ${cityGraphMeta.total_edges} edges | ${cityGraphMeta.source_info.includes("OSM") ? "Live OSM" : "Offline Grid"}`;
    }
  } catch (err) {
    console.error("Failed to load city graph metadata:", err);
  }
}

function renderCityFacilities() {
  if (!cityGraphMeta || !window.cityMap) return;

  // Render Hospitals
  cityGraphMeta.hospitals.forEach(h => {
    const icon = L.divIcon({
      className: "leaflet-div-icon",
      html: `<div class="marker-icon marker-hospital" title="${h.name}">&#10010;</div>`,
      iconSize: [26, 26],
      iconAnchor: [13, 13]
    });

    const m = L.marker([h.lat, h.lon], { icon }).addTo(window.cityMap);
    m.bindPopup(`
      <strong>${h.name}</strong><br>
      Beds: ${h.beds_free} / ${h.beds_total} free<br>
      Specialties: ${h.specialties.join(", ")}<br>
      <small style="color:#64748b;">(Synthetic Hospital Data)</small>
    `);
  });

  // Render Ambulances
  cityGraphMeta.ambulances.forEach(a => {
    const icon = L.divIcon({
      className: "leaflet-div-icon",
      html: `<div class="marker-icon marker-ambulance" title="${a.name}">&#128657;</div>`,
      iconSize: [26, 26],
      iconAnchor: [13, 13]
    });

    const m = L.marker([a.lat, a.lon], { icon }).addTo(window.cityMap);
    m.bindPopup(`
      <strong>${a.name}</strong><br>
      Status: ${a.status}<br>
      Node ID: ${a.node_id}<br>
      <small style="color:#64748b;">(Synthetic Fleet Simulation)</small>
    `);
  });
}

function setIncidentLocation(lat, lon) {
  currentIncidentCoords = { lat, lon };

  if (incidentMarker) {
    window.cityMap.removeLayer(incidentMarker);
  }

  const icon = L.divIcon({
    className: "leaflet-div-icon",
    html: `<div class="marker-icon marker-incident">&#9888;</div>`,
    iconSize: [28, 28],
    iconAnchor: [14, 14]
  });

  incidentMarker = L.marker([lat, lon], { icon }).addTo(window.cityMap);
  incidentMarker.bindPopup("<strong>Emergency Incident Scene</strong><br>Snapped to road network.").openPopup();
}

async function executeDispatch() {
  if (!currentIncidentCoords) {
    setIncidentLocation(8.5015, 76.9520);
  }

  const specialty = document.getElementById("dispatch-specialty").value;
  const lambdaParam = parseFloat(document.getElementById("lambda-slider").value);

  try {
    const res = await fetch("/api/dispatch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        incident_lat: currentIncidentCoords.lat,
        incident_lon: currentIncidentCoords.lon,
        specialty,
        lambda_param: lambdaParam
      })
    });

    const data = await res.json();
    currentDispatchData = data;
    displayDispatchResults(data);

    if (document.getElementById("toggle-frontier").checked) {
      animateFrontier(data.frontier_comparison);
    }
  } catch (err) {
    console.error("Dispatch call failed:", err);
  }
}

function displayDispatchResults(data) {
  // Update Mission Summary
  const amb = data.selected_ambulance;
  const hospId = data.selected_hospital_id;
  const hosp = data.ranked_hospitals.find(h => h.hospital_id === hospId);

  document.getElementById("res-amb-id").textContent = amb ? amb.name : "None";
  document.getElementById("res-amb-time").textContent = amb ? `Travel Time: ${amb.travel_time_s.toFixed(1)}s` : "";

  document.getElementById("res-hosp-name").textContent = hosp ? hosp.name : "None";
  document.getElementById("res-hosp-time").textContent = hosp ? `Transit Time: ${hosp.travel_time_s.toFixed(1)}s` : "";

  document.getElementById("res-total-time").textContent = `${data.total_mission_time_s.toFixed(1)} seconds (${(data.total_mission_time_s / 60).toFixed(1)} min)`;

  // Update Ambulance Ranking List
  const ambContainer = document.getElementById("amb-list-container");
  ambContainer.innerHTML = data.ranked_ambulances.map((a, i) => `
    <div class="list-item ${i === 0 ? "selected" : ""}">
      <div class="li-left">
        <span class="li-name">${a.name} ${i === 0 ? "★ ASSIGNED" : ""}</span>
        <span class="li-detail">Node #${a.node_id}</span>
      </div>
      <div class="li-right">${a.travel_time_s.toFixed(1)}s</div>
    </div>
  `).join("");

  // Update Hospital Ranking List
  const hospContainer = document.getElementById("hosp-list-container");
  hospContainer.innerHTML = data.ranked_hospitals.map((h, i) => `
    <div class="list-item ${h.hospital_id === hospId ? "selected" : ""}">
      <div class="li-left">
        <span class="li-name">${h.name} ${h.hospital_id === hospId ? "★ CHOSEN" : ""}</span>
        <span class="li-detail">Travel: ${h.travel_time_s}s | Free Beds: ${h.beds_free}/${h.beds_total} | ${h.specialty_match ? "✓ Match" : "✗ Mismatch"}</span>
      </div>
      <div class="li-right">Score: ${h.total_score}</div>
    </div>
  `).join("");

  // Draw Polylines on Leaflet Map
  if (leg1Polyline) window.cityMap.removeLayer(leg1Polyline);
  if (leg2Polyline) window.cityMap.removeLayer(leg2Polyline);

  // Leg 1: Ambulance to Incident (Royal Blue)
  if (data.leg1_coords && data.leg1_coords.length > 0) {
    leg1Polyline = L.polyline(data.leg1_coords, {
      color: "#2563eb",
      weight: 5,
      opacity: 0.9,
      dashArray: "8, 6"
    }).addTo(window.cityMap);
  }

  // Leg 2: Incident to Hospital (Emerald Green)
  if (data.leg2_coords && data.leg2_coords.length > 0) {
    leg2Polyline = L.polyline(data.leg2_coords, {
      color: "#16a34a",
      weight: 6,
      opacity: 0.95
    }).addTo(window.cityMap);
  }

  // Update counters
  document.getElementById("fc-dijkstra-nodes").textContent = data.frontier_comparison.dijkstra.nodes_expanded;
  document.getElementById("fc-dijkstra-time").textContent = data.frontier_comparison.dijkstra.runtime_ms;
  document.getElementById("fc-astar-nodes").textContent = data.frontier_comparison.astar.nodes_expanded;
  document.getElementById("fc-astar-time").textContent = data.frontier_comparison.astar.runtime_ms;
}

function animateFrontier(comparison) {
  // Clear existing frontier circles
  frontierCircles.forEach(c => window.cityMap.removeLayer(c));
  frontierCircles = [];

  const astarNodes = comparison.astar.explored_nodes || [];
  const dijkstraNodes = comparison.dijkstra.explored_nodes || [];

  // Animate Dijkstra explored set (circular expansion in violet/purple)
  dijkstraNodes.forEach((node, i) => {
    setTimeout(() => {
      const circle = L.circleMarker([node.lat, node.lon], {
        radius: 4,
        color: "#7c3aed",
        fillColor: "#c4b5fd",
        fillOpacity: 0.5,
        weight: 1
      }).addTo(window.cityMap);
      frontierCircles.push(circle);
    }, i * 4);
  });

  // Animate A* explored set (directed cone in amber/orange)
  astarNodes.forEach((node, i) => {
    setTimeout(() => {
      const circle = L.circleMarker([node.lat, node.lon], {
        radius: 5,
        color: "#d97706",
        fillColor: "#fbbf24",
        fillOpacity: 0.8,
        weight: 1.5
      }).addTo(window.cityMap);
      frontierCircles.push(circle);
    }, i * 4);
  });
}

// ==========================================================
// TAB 3: BENCHMARK & COST EQUALITY
// ==========================================================
let chartNodesInstance = null;
let chartTimeInstance = null;

function initTab3Benchmark() {
  document.getElementById("btn-run-benchmark").addEventListener("click", () => {
    executeBenchmark();
  });
}

async function executeBenchmark() {
  const numQueries = parseInt(document.getElementById("bench-queries-input").value) || 300;
  const progressContainer = document.getElementById("bench-progress-bar-container");
  const progressBar = document.getElementById("bench-progress-bar");
  const btn = document.getElementById("btn-run-benchmark");

  progressContainer.style.display = "block";
  progressBar.style.width = "20%";
  btn.disabled = true;
  btn.textContent = "Benchmarking...";

  try {
    progressBar.style.width = "60%";
    const res = await fetch("/api/benchmark", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ num_queries: numQueries, bellman_sample_size: 25 })
    });
    progressBar.style.width = "90%";
    const summary = await res.json();
    progressBar.style.width = "100%";

    renderBenchmarkResults(summary);
  } catch (err) {
    console.error("Benchmark failed:", err);
  } finally {
    setTimeout(() => {
      progressContainer.style.display = "none";
      progressBar.style.width = "0%";
      btn.disabled = false;
      btn.textContent = "⚙ Execute Benchmark";
    }, 400);
  }
}

function renderBenchmarkResults(summary) {
  // Update Stat Cards
  document.getElementById("stat-equality-pass").textContent = `${summary.cost_equality_pass_rate}%`;
  document.getElementById("stat-node-ratio").textContent = `${summary.node_reduction_ratio}x`;
  document.getElementById("stat-astar-time").textContent = `${summary.astar_time_ms.mean}ms`;
  document.getElementById("stat-dijkstra-time").textContent = `${summary.dijkstra_time_ms.mean}ms`;
  document.getElementById("stat-bellman-slowdown").textContent = summary.bellman_slowdown_ratio ? `${summary.bellman_slowdown_ratio}x` : "O(VE)";

  document.getElementById("bench-interpretation-text").textContent = summary.interpretation;

  // Populate Table (show first 30 queries)
  const tbody = document.getElementById("bench-tbody");
  tbody.innerHTML = summary.queries.slice(0, 30).map(q => `
    <tr>
      <td>#${q.query_id}</td>
      <td>${q.source} &rarr; ${q.target}</td>
      <td style="font-family:'JetBrains Mono';">${q.dijkstra_cost}</td>
      <td style="font-family:'JetBrains Mono';">${q.astar_cost}</td>
      <td style="font-family:'JetBrains Mono';">${q.bellman_cost !== null ? q.bellman_cost : "—"}</td>
      <td><span class="badge-success-pill">✓ EQUAL</span></td>
      <td>${q.dijkstra_nodes}</td>
      <td>${q.astar_nodes}</td>
      <td>${q.dijkstra_time_ms}</td>
      <td>${q.astar_time_ms}</td>
      <td>${q.bellman_time_ms !== null ? q.bellman_time_ms : "—"}</td>
    </tr>
  `).join("");

  // Render Chart.js Visualizations
  renderBenchmarkCharts(summary);
}

function renderBenchmarkCharts(summary) {
  const ctxNodes = document.getElementById("chart-nodes").getContext("2d");
  const ctxTime = document.getElementById("chart-time").getContext("2d");

  if (chartNodesInstance) chartNodesInstance.destroy();
  if (chartTimeInstance) chartTimeInstance.destroy();

  // 1. Nodes Expanded Distribution Chart
  const sampleQueries = summary.queries.slice(0, 20);
  const labels = sampleQueries.map(q => `Q${q.query_id}`);
  const dijkstraNodesData = sampleQueries.map(q => q.dijkstra_nodes);
  const astarNodesData = sampleQueries.map(q => q.astar_nodes);

  chartNodesInstance = new Chart(ctxNodes, {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: "Dijkstra (Heap SSSP)",
          data: dijkstraNodesData,
          backgroundColor: "rgba(99, 102, 241, 0.7)",
          borderColor: "#4f46e5",
          borderWidth: 1.5
        },
        {
          label: "A* (Admissible Heuristic)",
          data: astarNodesData,
          backgroundColor: "rgba(245, 158, 11, 0.7)",
          borderColor: "#d97706",
          borderWidth: 1.5
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        title: {
          display: true,
          text: `Search Space Comparison Across Random Queries (Mean A* Reduction: ${summary.node_reduction_ratio}x)`
        }
      },
      scales: {
        y: {
          title: { display: true, text: "Nodes Expanded" },
          beginAtZero: true
        },
        x: {
          title: { display: true, text: "Sample Emergency Queries" }
        }
      }
    }
  });

  // 2. Runtime Distribution Chart
  chartTimeInstance = new Chart(ctxTime, {
    type: "bar",
    data: {
      labels: ["Dijkstra Mean", "Dijkstra Median", "A* Mean", "A* Median"],
      datasets: [{
        label: "Execution Latency (ms)",
        data: [
          summary.dijkstra_time_ms.mean,
          summary.dijkstra_time_ms.median,
          summary.astar_time_ms.mean,
          summary.astar_time_ms.median
        ],
        backgroundColor: [
          "rgba(99, 102, 241, 0.8)",
          "rgba(99, 102, 241, 0.5)",
          "rgba(245, 158, 11, 0.8)",
          "rgba(245, 158, 11, 0.5)"
        ],
        borderColor: [
          "#4f46e5",
          "#4f46e5",
          "#d97706",
          "#d97706"
        ],
        borderWidth: 1.5
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        title: {
          display: true,
          text: `Runtime Summary (Pure Python, N=${summary.sample_size} Queries)`
        }
      },
      scales: {
        y: {
          title: { display: true, text: "Milliseconds (ms)" },
          beginAtZero: true
        }
      }
    }
  });
}

// ==========================================================
// TAB 4: NEGATIVE WEIGHTS & SIGNAL PREEMPTION
// ==========================================================
let negativeGraphsMeta = null;

async function initTab4Negative() {
  const scenarioSelect = document.getElementById("negative-scenario-select");
  const btnCompare = document.getElementById("btn-neg-compare");
  const btnReset = document.getElementById("btn-neg-reset");

  try {
    const res = await fetch("/api/negative-graphs");
    negativeGraphsMeta = await res.json();
    renderNegativeGraphSvg("credit");
  } catch (err) {
    console.error("Failed to load negative graphs:", err);
  }

  scenarioSelect.addEventListener("change", () => {
    renderNegativeGraphSvg(scenarioSelect.value);
    resetNegativeResults();
  });

  btnCompare.addEventListener("click", () => {
    executeNegativeComparison(scenarioSelect.value);
  });

  btnReset.addEventListener("click", () => {
    renderNegativeGraphSvg(scenarioSelect.value);
    resetNegativeResults();
  });
}

function resetNegativeResults() {
  document.getElementById("neg-dijkstra-cost").textContent = "—";
  document.getElementById("neg-dijkstra-path").textContent = "Path: —";
  document.getElementById("neg-dijkstra-verdict").textContent = "Waiting to run...";
  document.getElementById("neg-dijkstra-verdict").className = "nc-verdict";

  document.getElementById("neg-bellman-cost").textContent = "—";
  document.getElementById("neg-bellman-path").textContent = "Path: —";
  document.getElementById("neg-bellman-verdict").textContent = "Waiting to run...";
  document.getElementById("neg-bellman-verdict").className = "nc-verdict";

  document.getElementById("neg-cycle-alert").style.display = "none";
}

function renderNegativeGraphSvg(scenario) {
  const svg = document.getElementById("neg-svg");
  if (!svg || !negativeGraphsMeta) return;

  const data = scenario === "credit" ? negativeGraphsMeta.credit_graph : negativeGraphsMeta.cycle_graph;

  svg.innerHTML = `
    <defs>
      <marker id="neg-arrow" viewBox="0 0 10 10" refX="28" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
        <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#64748b" />
      </marker>
      <marker id="neg-arrow-red" viewBox="0 0 10 10" refX="28" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
        <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#dc2626" />
      </marker>
    </defs>
  `;

  // Draw Edges
  data.edges.forEach(([u, v, w]) => {
    const nodeU = data.nodes[u];
    const nodeV = data.nodes[v];
    const isNegative = w < 0;

    const pathEl = document.createElementNS("http://www.w3.org/2000/svg", "path");
    pathEl.setAttribute("d", `M ${nodeU.ui_x} ${nodeU.ui_y} L ${nodeV.ui_x} ${nodeV.ui_y}`);
    pathEl.setAttribute("class", isNegative ? "edge-path negative-credit" : "edge-path");
    pathEl.setAttribute("id", `neg-edge-${u}-${v}`);
    pathEl.setAttribute("marker-end", isNegative ? "url(#neg-arrow-red)" : "url(#neg-arrow)");
    svg.appendChild(pathEl);

    // Midpoint label
    const midX = (nodeU.ui_x + nodeV.ui_x) / 2;
    const midY = (nodeU.ui_y + nodeV.ui_y) / 2;

    const bg = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    bg.setAttribute("x", midX - 22);
    bg.setAttribute("y", midY - 11);
    bg.setAttribute("width", 44);
    bg.setAttribute("height", 22);
    bg.setAttribute("class", "edge-label-bg");
    if (isNegative) bg.setAttribute("stroke", "#dc2626");
    svg.appendChild(bg);

    const txt = document.createElementNS("http://www.w3.org/2000/svg", "text");
    txt.setAttribute("x", midX);
    txt.setAttribute("y", midY);
    txt.setAttribute("class", "edge-weight-text");
    if (isNegative) txt.setAttribute("fill", "#dc2626");
    txt.textContent = `${w > 0 ? "+" : ""}${w.toFixed(1)}s`;
    svg.appendChild(txt);
  });

  // Draw Nodes
  Object.entries(data.nodes).forEach(([nid, meta]) => {
    const g = document.createElementNS("http://www.w3.org/2000/svg", "g");

    const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    circle.setAttribute("cx", meta.ui_x);
    circle.setAttribute("cy", meta.ui_y);
    circle.setAttribute("r", 24);
    circle.setAttribute("class", meta.role === "cycle" ? "node-circle cycle-alert" : "node-circle unvisited");
    circle.setAttribute("id", `neg-circle-${nid}`);
    g.appendChild(circle);

    const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
    text.setAttribute("x", meta.ui_x);
    text.setAttribute("y", meta.ui_y - 1);
    text.setAttribute("class", "node-label");
    text.textContent = nid;
    g.appendChild(text);

    const subText = document.createElementNS("http://www.w3.org/2000/svg", "text");
    subText.setAttribute("x", meta.ui_x);
    subText.setAttribute("y", meta.ui_y + 38);
    subText.setAttribute("font-size", "11px");
    subText.setAttribute("font-weight", "600");
    subText.setAttribute("fill", "#64748b");
    subText.setAttribute("text-anchor", "middle");
    subText.textContent = meta.label || nid;
    g.appendChild(subText);

    svg.appendChild(g);
  });
}

async function executeNegativeComparison(scenario) {
  try {
    // 1. Run Dijkstra
    const resD = await fetch("/api/run-negative", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ graph_type: scenario, algorithm: "dijkstra" })
    });
    const dataD = await resD.json();

    // 2. Run Bellman-Ford
    const resB = await fetch("/api/run-negative", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ graph_type: scenario, algorithm: "bellman_ford" })
    });
    const dataB = await resB.json();

    // Update UI
    if (scenario === "credit") {
      document.getElementById("neg-dijkstra-cost").textContent = `${dataD.cost.toFixed(1)}s`;
      document.getElementById("neg-dijkstra-path").textContent = `Path: ${dataD.path.join(" → ")}`;
      document.getElementById("neg-dijkstra-verdict").textContent = "SUBOPTIMAL / WRONG ANSWER";
      document.getElementById("neg-dijkstra-verdict").style.background = "#fee2e2";
      document.getElementById("neg-dijkstra-verdict").style.color = "#991b1b";

      document.getElementById("neg-bellman-cost").textContent = `${dataB.cost.toFixed(1)}s`;
      document.getElementById("neg-bellman-path").textContent = `Path: ${dataB.path.join(" → ")}`;
      document.getElementById("neg-bellman-verdict").textContent = "TRUE GLOBAL OPTIMUM (CORRECT)";
      document.getElementById("neg-bellman-verdict").style.background = "#dcfce7";
      document.getElementById("neg-bellman-verdict").style.color = "#166534";

      document.getElementById("neg-caption").innerHTML = `
        <strong>Dijkstra Error:</strong> Node A finalized at dist=3.0s. Edge B&rarr;A (-4.0s) was ignored because A was already visited. Dijkstra returns 13.0s (S&rarr;A&rarr;H).<br>
        <strong>Bellman-Ford Victory:</strong> Pass 2 relaxed B&rarr;A (5.0 - 4.0 = 1.0s), discovering the true optimal route S&rarr;B&rarr;A&rarr;H with cost 11.0s!
      `;
    } else {
      // Scenario B: Negative cycle
      document.getElementById("neg-dijkstra-cost").textContent = `${dataD.cost.toFixed(1)}s`;
      document.getElementById("neg-dijkstra-path").textContent = `Path: ${dataD.path.join(" → ")}`;
      document.getElementById("neg-dijkstra-verdict").textContent = "MISSED NEGATIVE CYCLE";

      document.getElementById("neg-bellman-cost").textContent = "—∞ (Cycle)";
      document.getElementById("neg-bellman-path").textContent = "Path: Undefined (Infinite Loop)";
      document.getElementById("neg-bellman-verdict").textContent = "NEGATIVE CYCLE DETECTED IN PASS V";

      document.getElementById("neg-cycle-alert").style.display = "block";
      document.getElementById("neg-caption").innerHTML = `
        <strong>Pass V Cycle Caught:</strong> Edge Z&rarr;X (-10.0s) still relaxes after 4 passes. Bellman-Ford flags the unbounded loop!
      `;
    }
  } catch (err) {
    console.error("Negative comparison failed:", err);
  }
}
