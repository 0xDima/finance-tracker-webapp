(function () {
  function readJsonTag(id, fallback) {
    try {
      const el = document.getElementById(id);
      if (!el) return fallback;
      const raw = (el.textContent || "").trim();
      if (!raw) return fallback;
      return JSON.parse(raw);
    } catch {
      return fallback;
    }
  }

  const monthRange = readJsonTag('month-range-data', { start_date: null, end_date: null });
  const rawData = readJsonTag('spending-by-category-data', []);

  function normLabel(s) {
    return String(s || '').trim().replace(/\s+/g, ' ');
  }

  const totals = {};
  for (const item of rawData) {
    if (!item) continue;
    const label = normLabel(item.label);
    const value = Number(item.value);
    if (!label) continue;
    if (!Number.isFinite(value) || value < 0) continue;
    totals[label] = (totals[label] || 0) + value;
  }

  const labels = Object.keys(totals).sort((a, b) => (totals[b] || 0) - (totals[a] || 0));
  const values = labels.map(l => totals[l] || 0);

  const colors = [
    "#9bbcff", "#b6f0d2", "#ffd6a5", "#f1b5ff",
    "#ff9ea6", "#a6fff4", "#ffe98a", "#c7d2ff",
    "#d0ffb6", "#ffb7e0", "#cbd5e1", "#fca5a5"
  ];

  function goToTransactions(category) {
    const start = monthRange?.start_date;
    const end = monthRange?.end_date;

    const url = new URL('/transactions', window.location.origin);
    if (category) url.searchParams.set('category', category);
    if (start) url.searchParams.set('start_date', start);
    if (end) url.searchParams.set('end_date', end);

    window.location.href = url.toString();
  }

  function renderLegend() {
    const legend = document.getElementById('categoryLegend');
    if (!legend) return;
    legend.innerHTML = '';

    if (labels.length === 0) {
      const row = document.createElement('div');
      row.className = 'legendItem';
      row.innerHTML = `
        <div class="legendLeft">
          <span class="swatch" style="background: rgba(255,255,255,.18)"></span>
          <span class="legendName">No expenses found</span>
        </div>
        <span class="legendValue">0.00</span>
      `;
      legend.appendChild(row);
      return;
    }

    labels.forEach((name, i) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'legendBtn';
      btn.setAttribute('data-category', name);
      btn.setAttribute('aria-label', `Open monthly transactions for ${name}`);

      const left = document.createElement('div');
      left.className = 'legendLeft';

      const swatch = document.createElement('span');
      swatch.className = 'swatch';
      swatch.style.background = colors[i % colors.length];

      const label = document.createElement('span');
      label.className = 'legendName';
      label.textContent = name;

      left.append(swatch, label);

      const value = document.createElement('span');
      value.className = 'legendValue';
      value.textContent = values[i].toFixed(2);

      btn.append(left, value);
      btn.addEventListener('click', () => goToTransactions(name));

      legend.appendChild(btn);
    });
  }

  function buildChart() {
    const canvas = document.getElementById('spendingByCategoryChart');
    if (!canvas || typeof Chart === 'undefined') return;

    const existing = Chart.getChart(canvas);
    if (existing) existing.destroy();

    if (labels.length === 0) return;

    new Chart(canvas.getContext('2d'), {
      type: 'doughnut',
      data: {
        labels,
        datasets: [{
          data: values,
          backgroundColor: labels.map((_, i) => colors[i % colors.length]),
          borderWidth: 0,
          hoverOffset: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '72%',
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label(ctx) {
                const v = Number(ctx.parsed);
                return `${ctx.label}: ${Number.isFinite(v) ? v.toFixed(2) : "0.00"} €`;
              }
            }
          }
        }
      }
    });
  }

  function fadeIn() {
    const nodes = document.querySelectorAll('.card, .topbar');
    nodes.forEach((n, idx) => {
      n.classList.add('fade-in');
      n.style.animationDelay = Math.min(idx * 40, 220) + 'ms';
    });
  }

  renderLegend();
  buildChart();
  fadeIn();

  let rAF = null;
  window.addEventListener('resize', () => {
    if (rAF) cancelAnimationFrame(rAF);
    rAF = requestAnimationFrame(buildChart);
  });
})();