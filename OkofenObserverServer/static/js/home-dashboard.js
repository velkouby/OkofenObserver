const chartsByPanel = {};

function cssVar(name, fallback = '') {
  const value = getComputedStyle(document.documentElement).getPropertyValue(name);
  return value ? value.trim() : fallback;
}

function setupTabs(group, onShow) {
  const toggles = Array.from(document.querySelectorAll(`.tab-toggle[data-tab-group="${group}"]`));
  const panels = Array.from(document.querySelectorAll(`.tab-panel[data-tab-group="${group}"]`));
  if (!toggles.length || !panels.length) {
    return;
  }

  const activate = (target) => {
    if (!target) {
      return;
    }
    toggles.forEach((btn) => {
      const isActive = btn.dataset.tabTarget === target;
      btn.classList.toggle('is-active', isActive);
      btn.setAttribute('aria-selected', isActive ? 'true' : 'false');
    });
    panels.forEach((panel) => {
      const isActive = panel.dataset.tabPanel === target;
      panel.classList.toggle('is-active', isActive);
    });
    if (typeof onShow === 'function') {
      onShow(target);
    }
  };

  toggles.forEach((btn) => {
    btn.addEventListener('click', () => activate(btn.dataset.tabTarget));
  });

  const initial = toggles.find((btn) => btn.classList.contains('is-active'))?.dataset.tabTarget
    || toggles[0]?.dataset.tabTarget;
  if (initial) {
    activate(initial);
  }
}

function initCharts() {
  if (typeof Chart === 'undefined') {
    return;
  }

  const dataNode = document.getElementById('chart-data');
  if (!dataNode) {
    return;
  }

  let chartData = {};
  try {
    chartData = JSON.parse(dataNode.textContent || '{}');
  } catch (error) {
    console.error('Failed to parse chart data', error); // eslint-disable-line no-console
    return;
  }

  const labels = chartData.labels || [];
  const emptyState = document.querySelector('.chart-empty');
  if (!labels.length) {
    if (emptyState) {
      emptyState.hidden = false;
    }
    return;
  }
  if (emptyState) {
    emptyState.hidden = true;
  }

  Chart.defaults.font.family = 'Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
  Chart.defaults.color = cssVar('--muted-text', '#475569');

  const colors = {
    brand: cssVar('--brand', '#2b8cf3'),
    accent: cssVar('--accent', '#f37f2b'),
    success: cssVar('--success', '#1cc48f'),
    purple: '#7c3aed',
    pink: '#f43f5e',
    teal: '#14b8a6',
    slate: '#475569',
  };

  const toNumericArray = (values = [], transform) => (
    values.map((value) => {
      if (value === null || typeof value === 'undefined') {
        return null;
      }
      const num = Number(value);
      return typeof transform === 'function' ? transform(num) : num;
    })
  );

  const boilerHoursCanvas = document.getElementById('chart-boiler-hours');
  const pelletsCanvas = document.getElementById('chart-pellets');
  const heatingCanvas = document.getElementById('chart-heating');
  const ecsCanvas = document.getElementById('chart-ecs');

  const chaudiereCharts = [];

  if (boilerHoursCanvas) {
    const dataset = toNumericArray(chartData.chaudiere?.boiler_hours, (v) => Number(v.toFixed(2)));
    chaudiereCharts.push(new Chart(boilerHoursCanvas, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: 'Durée allumage (h)',
          data: dataset,
          backgroundColor: colors.brand,
          borderRadius: 8,
          borderSkipped: false,
        }],
      },
      options: {
        responsive: true,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (ctx) => `${ctx.formattedValue} h`,
            },
          },
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: { callback: (value) => `${value} h` },
            grid: { color: 'rgba(148, 163, 184, 0.25)' },
          },
          x: {
            grid: { display: false },
          },
        },
      },
    }));
  }

  if (pelletsCanvas) {
    const dataset = toNumericArray(chartData.chaudiere?.pellet_consumed, (v) => Number(v.toFixed(2)));
    chaudiereCharts.push(new Chart(pelletsCanvas, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: 'Pellets (kg)',
          data: dataset,
          backgroundColor: colors.accent,
          borderRadius: 8,
          borderSkipped: false,
        }],
      },
      options: {
        responsive: true,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (ctx) => `${ctx.formattedValue} kg`,
            },
          },
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: { callback: (value) => `${value} kg` },
            grid: { color: 'rgba(148, 163, 184, 0.25)' },
          },
          x: {
            grid: { display: false },
          },
        },
      },
    }));
  }

  if (chaudiereCharts.length) {
    chartsByPanel['chart-chaudiere'] = chaudiereCharts;
  }

  if (heatingCanvas) {
    const heatingConfigs = [
      { key: 'temp_ext_moy', label: 'T° extérieure', color: colors.brand },
      { key: 'temp_ext_nuit', label: 'T° extérieure nuit', color: colors.slate, borderDash: [6, 4] },
      { key: 'temp_chaudiere_moy', label: 'T° chaudière', color: colors.accent },
      { key: 'temp_depart_moy', label: 'T° départ', color: colors.success },
      { key: 'temp_ambiante_moy', label: 'T° ambiante', color: colors.purple },
      { key: 'temp_ambiante_nuit', label: 'T° ambiante nuit', color: colors.pink, borderDash: [4, 4] },
    ];

    const datasets = heatingConfigs.map((cfg) => ({
      label: cfg.label,
      data: toNumericArray(chartData.chauffage?.[cfg.key]),
      borderColor: cfg.color,
      backgroundColor: cfg.color,
      spanGaps: true,
      tension: 0.3,
      borderWidth: 2,
      fill: false,
      ...(cfg.borderDash ? { borderDash: cfg.borderDash } : {}),
    }));

    const heatingChart = new Chart(heatingCanvas, {
      type: 'line',
      data: { labels, datasets },
      options: {
        responsive: true,
        plugins: {
          legend: {
            position: 'top',
            labels: { usePointStyle: true },
          },
        },
        scales: {
          y: {
            title: { display: true, text: '°C' },
            grid: { color: 'rgba(148, 163, 184, 0.25)' },
          },
          x: {
            grid: { display: false },
          },
        },
      },
    });

    chartsByPanel['chart-chauffage'] = [heatingChart];
  }

  if (ecsCanvas) {
    const ecsConfigs = [
      { key: 'temp_ecs_chauffe_moy', label: 'T° ECS en chauffe', color: colors.teal },
      { key: 'temp_ecs_global_moy', label: 'T° ECS moyenne', color: colors.brand },
    ];

    const datasets = ecsConfigs.map((cfg) => ({
      label: cfg.label,
      data: toNumericArray(chartData.ecs?.[cfg.key]),
      borderColor: cfg.color,
      backgroundColor: cfg.color,
      spanGaps: true,
      tension: 0.3,
      borderWidth: 2,
      fill: false,
    }));

    const ecsChart = new Chart(ecsCanvas, {
      type: 'line',
      data: { labels, datasets },
      options: {
        responsive: true,
        plugins: {
          legend: {
            position: 'top',
            labels: { usePointStyle: true },
          },
        },
        scales: {
          y: {
            title: { display: true, text: '°C' },
            grid: { color: 'rgba(148, 163, 184, 0.25)' },
          },
          x: {
            grid: { display: false },
          },
        },
      },
    });

    chartsByPanel['chart-ecs'] = [ecsChart];
  }
}

document.addEventListener('DOMContentLoaded', () => {
  setupTabs('summary');
  setupTabs('charts', (panelId) => {
    const chartList = chartsByPanel[panelId];
    if (chartList) {
      chartList.forEach((chart) => {
        if (chart && typeof chart.resize === 'function') {
          chart.resize();
        }
      });
    }
  });
  initCharts();
});
