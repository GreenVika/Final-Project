let chart;
let currentDays = 30;

async function postJSON(url, data) {
  const res = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
async function getJSON(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

function renderEntries(entries) {
  const list = document.getElementById("entriesList");
  if (!entries.length) {
    list.innerHTML = `<p class="muted">No entries in this range.</p>`;
    return;
  }
  list.innerHTML = entries.slice().reverse().slice(0, 5).map(e => {
    const ts = new Date(e.created_at);
    const emo = e.top_label.replace(/\b\w/g, c => c.toUpperCase());
    return `
    <div class="entry">
      <div><strong>${ts.toDateString()}</strong> – <span class="tiny">Top: ${emo} (${e.top_score}%)</span></div>
      <div class="tiny">${e.text.replace(/</g,"&lt;").slice(0, 220)}${e.text.length > 220 ? "..." : ""}</div>
    </div>`;
  }).join("");
}

function renderInsights(ins) {
  const container = document.getElementById("insights");
  container.innerHTML = ins.summary.map(s => `<p>${s}</p>`).join("") || "<p class='muted'>No insights yet.</p>";
}

function buildDatasets(labels, series) {
  const dates = series.map(s => s.date);
  return labels.map(label => ({
    label: label,
    data: series.map(s => s[label] ?? null),
    spanGaps: true,
  }));
}

function renderChart(stats) {
  const ctx = document.getElementById("moodChart").getContext("2d");
  if (chart) chart.destroy();

  const labels = stats.series.map(s => s.date);
  const datasets = buildDatasets(stats.labels, stats.series);

  chart = new Chart(ctx, {
    type: "line",
    data: { labels, datasets },
    options: {
      responsive: true,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { position: "bottom" },
        tooltip: { callbacks: { label: (ctx) => `${ctx.dataset.label}: ${ctx.formattedValue}` } }
      },
      scales: {
        y: { title: { display: true, text: "Emotion (avg %)" }, min: 0, max: 100 },
        x: { title: { display: true, text: "Date" } }
      }
    }
  });
}

async function refreshAll() {
  document.getElementById("rangeLabel").innerText = currentDays;
  const [stats, entries, ins] = await Promise.all([
    getJSON(`/api/stats?days=${currentDays}`),
    getJSON(`/api/entries?days=${currentDays}`),
    getJSON(`/api/insights`),
  ]);
  renderChart(stats);
  renderEntries(entries);
  renderInsights(ins);
}

document.addEventListener("DOMContentLoaded", () => {
  const saveBtn = document.getElementById("saveBtn");
  const entryText = document.getElementById("entryText");
  const saveStatus = document.getElementById("saveStatus");

  saveBtn.addEventListener("click", async () => {
    const text = entryText.value.trim();
    if (!text) return;
    saveBtn.disabled = true;
    saveStatus.textContent = "Analyzing...";
    try {
      await postJSON("/api/entries", { text });
      entryText.value = "";
      saveStatus.textContent = "Saved ✓";
      await refreshAll();
    } catch (e) {
      console.error(e);
      saveStatus.textContent = "Error saving entry.";
    } finally {
      setTimeout(() => (saveStatus.textContent = ""), 2000);
      saveBtn.disabled = false;
    }
  });

  document.querySelectorAll("button.pill").forEach(btn => {
    btn.addEventListener("click", () => {
      currentDays = parseInt(btn.dataset.days, 10);
      refreshAll().catch(console.error);
    });
  });

  refreshAll().catch(console.error);
});
