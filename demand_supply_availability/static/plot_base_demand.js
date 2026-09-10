let chart;   // all-materials chart
let chart2;  // concrete-constituents chart

/* ---------- colour + hatch helpers ---------- */

// Strip the _reused suffix to get the underlying material name
function baseName(label) {
  return String(label).replace(/_reused$/i, "").trim();
}

function isReused(label) {
  return /_reused$/i.test(String(label));
}

// One hue per distinct base material, so X and X_reused share a colour
function buildColorMap(labels) {
  const bases = [...new Set(labels.map(baseName))];
  const map = {};
  bases.forEach((b, i) => {
    map[b] = `hsl(${Math.round(i * 360 / bases.length)}, 70%, 60%)`;
  });
  return map;
}

// A 10x10 tile: solid colour with white 45-degree stripes
const patternCache = new Map();
function hatchPattern(color) {
  if (patternCache.has(color)) return patternCache.get(color);

  const size = 10;
  const tile = document.createElement("canvas");
  tile.width = tile.height = size;
  const g = tile.getContext("2d");

  g.fillStyle = color;
  g.fillRect(0, 0, size, size);

  g.strokeStyle = "rgba(255, 255, 255, 0.95)";
  g.lineWidth = 3;
  g.beginPath();
  g.moveTo(0, size);
  g.lineTo(size, 0);
  g.moveTo(-1, 1);          // corner fill, keeps tiling seamless
  g.lineTo(1, -1);
  g.moveTo(size - 1, size + 1);
  g.lineTo(size + 1, size - 1);
  g.stroke();

  const pattern = g.createPattern(tile, "repeat");
  patternCache.set(color, pattern);
  return pattern;
}

// Colourful segments; reused materials hatched in their base colour
function segmentColors(labels) {
  const map = buildColorMap(labels);
  return labels.map(label => {
    const color = map[baseName(label)];
    return isReused(label) ? hatchPattern(color) : color;
  });
}

// Initial black-and-white state; reused materials still hatched
function greyColors(labels) {
  const grey = "rgba(128, 128, 128, 0.8)";
  return labels.map(label => (isReused(label) ? hatchPattern(grey) : grey));
}

// Shared chart options
function chartOptions() {
  return {
    responsive: true,
    maintainAspectRatio: false,
    layout: { padding: { top: 0, right: 8, bottom: 8, left: 8 } },
    plugins: {
      legend: {
        display: true,
        position: "top",
        align: "start",
        labels: { font: { size: 10 }, boxWidth: 12, padding: 6 },
      },
      title: { display: false },
    },
  };
}


// Push new rows into an existing chart with colourful segments
function updateChart(c, rows) {
  if (!rows) return;
  const labels = rows.map(d => d.Material);
  c.data.labels = labels;
  c.data.datasets[0].data = rows.map(d => d["Baseline Demand (lbs)"]);
  c.data.datasets[0].backgroundColor = segmentColors(labels);
  c.data.datasets[0].borderColor = "#fff";
  c.data.datasets[0].borderWidth = 1;
  c.update();
}

/* ---------- initial render ---------- */

async function loadCharts() {
  const materials = await fetch("/static/processed_data/new_bldg_demand.json")
    .then(res => res.json())
    .catch(error => { console.error("Error loading materials data:", error); return []; });

  const concrete = await fetch("/static/processed_data/concrete_demand.json")
    .then(res => res.json())
    .catch(error => { console.error("Error loading concrete data:", error); return []; });

  const materialLabels = materials.map(d => d.Material);
  const materialValues = materials.map(d => d["Baseline Demand (lbs)"]);
  const concreteLabels = concrete.map(d => d.Material);
  const concreteValues = concrete.map(d => d["Baseline Demand (lbs)"]);

  const ctx1 = document.getElementById("materialsPie").getContext("2d");
  const ctx2 = document.getElementById("concretePie").getContext("2d");

  chart = new Chart(ctx1, {
    type: "pie",
    data: {
      labels: materialLabels,
      datasets: [{
        label: "Material Demand",
        data: materialValues,
        backgroundColor: greyColors(materialLabels),
        borderColor: "#fff",
        borderWidth: 1,
      }],
    },
    options: chartOptions(),
  });

  chart2 = new Chart(ctx2, {
    type: "pie",
    data: {
      labels: concreteLabels,
      datasets: [{
        label: "Concrete Constituents",
        data: concreteValues,
        backgroundColor: greyColors(concreteLabels),
        borderColor: "#fff",
        borderWidth: 1,
      }],
    },
    options: chartOptions(),
  });
}

/* ---------- form submission ---------- */

const form = document.querySelector("form");
form.addEventListener("submit", async (event) => {
  event.preventDefault();
  console.log("Form submitted via AJAX!");

  const formData = new FormData(form);

  const response = await fetch(form.action, {
    method: "POST",
    body: formData,
    headers: { "X-CSRFToken": formData.get("csrfmiddlewaretoken") },
  });

  if (!response.ok) {
    console.error("Error submitting form:", response.statusText);
    return;
  }

  console.log("Form submitted successfully! Fetching updated data...");

  // cache-buster so the browser doesn't hand back the previous submission
  const bust = "?t=" + Date.now();

  const updatedMaterials = await fetch("/static/processed_data/new_bldg_demand.json" + bust)
    .then(res => res.json())
    .catch(error => console.error("Error loading updated materials data:", error));
  console.log("Updated materials data:", updatedMaterials);
  updateChart(chart, updatedMaterials);
  console.log("All materials chart updated successfully!");

  const updatedConcrete = await fetch("/static/processed_data/concrete_demand.json" + bust)
    .then(res => res.json())
    .catch(error => console.error("Error loading updated concrete data:", error));
  console.log("Updated concrete data:", updatedConcrete);
  updateChart(chart2, updatedConcrete);
  console.log("Concrete chart updated successfully!");
});

loadCharts();
