document.addEventListener("DOMContentLoaded", () => {
  const metricsConfig = JSON.parse(
    document.getElementById("metrics-config").textContent
  );

  const chartCanvas = document.getElementById("data-chart");
  const datasetSelector = document.getElementById("dataset-selector");
  const statusIndicator = document.getElementById("status-indicator");
  const dataRangeEl = document.getElementById("data-range");
  const sampleCountEl = document.getElementById("sample-count");
  const lastUpdateEl = document.getElementById("last-update");
  const emptyState = document.getElementById("empty-state");
  const refreshButton = document.getElementById("refresh-button");
  const startInput = document.getElementById("start-date");
  const endInput = document.getElementById("end-date");
  const quickButtons = document.querySelectorAll(".quick-range button");

  let currentData = [];
  let currentUrl = null;

  const colors = Object.fromEntries(
    Object.values(metricsConfig).map((metric, idx) => [
      metric.key,
      metric.color || generateColor(idx),
    ])
  );

  function generateColor(index) {
    const palette = [
      "#2b8cf3",
      "#f37f2b",
      "#7c3aed",
      "#1cc48f",
      "#f22e63",
      "#10b981",
      "#f59e0b",
      "#6366f1",
      "#9333ea",
      "#14b8a6",
    ];
    return palette[index % palette.length];
  }

  function formatDate(date) {
    return luxon.DateTime.fromISO(date, { zone: "utc" }).toFormat("dd LLL yyyy HH:mm");
  }

  function setStatus(online, message) {
    const dot = statusIndicator.querySelector(".dot");
    dot.classList.toggle("online", online);
    dot.classList.toggle("offline", !online);
    statusIndicator.querySelector("span").textContent = message;
  }

  function buildDatasetSelector() {
    datasetSelector.innerHTML = "";
    Object.values(metricsConfig).forEach((metric) => {
      const option = document.createElement("label");
      option.className = "dataset-option";

      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.value = metric.key;
      checkbox.checked = metric.default;

      checkbox.addEventListener("change", () => {
        if (getSelectedKeys().length === 0) {
          checkbox.checked = true; // always keep at least one dataset
          return;
        }
        updateChart();
      });

      const colorBadge = document.createElement("span");
      colorBadge.className = "dataset-color";
      colorBadge.style.backgroundColor = colors[metric.key];

      const label = document.createElement("span");
      label.textContent = metric.label;

      option.appendChild(checkbox);
      option.appendChild(colorBadge);
      option.appendChild(label);

      datasetSelector.appendChild(option);
    });
  }

  function getSelectedKeys() {
    return Array.from(datasetSelector.querySelectorAll("input[type=checkbox]:checked")).map(
      (input) => input.value
    );
  }

  const chart = new Chart(chartCanvas, {
    type: "line",
    data: {
      labels: [],
      datasets: [],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: "nearest",
        intersect: false,
      },
      scales: {
        x: {
          type: "time",
          time: {
            tooltipFormat: "dd LLL yyyy HH:mm",
            displayFormats: {
              hour: "HH:mm",
              day: "dd LLL",
            },
          },
          ticks: {
            color: "#5f6475",
          },
        },
        y: {
          ticks: {
            color: "#5f6475",
          },
          grid: {
            color: "rgba(95, 100, 117, 0.15)",
          },
        },
      },
      plugins: {
        legend: {
          labels: {
            usePointStyle: true,
          },
        },
        tooltip: {
          callbacks: {
            label: (context) => {
              const label = context.dataset.label || "";
              const value = context.parsed.y ?? "";
              return `${label}: ${value}`;
            },
          },
        },
      },
    },
  });

  function updateChart() {
    if (!currentData.length) {
      chart.data.labels = [];
      chart.data.datasets = [];
      chart.update();
      emptyState.hidden = false;
      return;
    }

    const selectedKeys = getSelectedKeys();
    emptyState.hidden = selectedKeys.length > 0;

    const labels = currentData.map((row) => luxon.DateTime.fromISO(row.datetime));

    chart.data.labels = labels;
    chart.data.datasets = selectedKeys.map((key) => ({
      label: metricsConfig[key].label,
      data: currentData.map((row) => row[key]),
      borderColor: colors[key],
      backgroundColor: colors[key],
      borderWidth: 2,
      tension: 0.25,
      spanGaps: true,
      pointRadius: 0,
      hoverRadius: 3,
    }));

    chart.update();
  }

  async function fetchData(url, rangeLabel) {
    try {
      setStatus(false, "Chargement des données…");
      refreshButton.disabled = true;

      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`Erreur ${response.status}`);
      }
      const payload = await response.json();

      currentData = payload.data || [];
      currentUrl = url;

      if (currentData.length === 0) {
        emptyState.hidden = false;
        dataRangeEl.textContent = rangeLabel || "Aucune période";
        sampleCountEl.textContent = "0 échantillon";
        lastUpdateEl.textContent = "";
        setStatus(true, "Aucune donnée sur cette période");
        updateChart();
        return;
      }

      const firstDate = currentData[0].datetime;
      const lastDate = currentData[currentData.length - 1].datetime;

      dataRangeEl.textContent = `Période : ${formatDate(firstDate)} → ${formatDate(lastDate)}`;
      sampleCountEl.textContent = `${currentData.length} échantillon${
        currentData.length > 1 ? "s" : ""
      }`;
      lastUpdateEl.textContent = `Dernière mise à jour : ${new Date().toLocaleString()}`;

      emptyState.hidden = true;
      setStatus(true, "Données chargées");

      updateChart();
    } catch (error) {
      console.error(error);
      setStatus(false, "Impossible de récupérer les données");
    } finally {
      refreshButton.disabled = false;
    }
  }

  function buildUrl() {
    const start = startInput.value;
    const end = endInput.value;

    if (start && end) {
      return `/data/range/${start}/${end}/json/`;
    }

    return currentUrl || "/data/lastdays/2/json/";
  }

  refreshButton.addEventListener("click", () => {
    const start = startInput.value;
    const end = endInput.value;

    if (start && end && start > end) {
      setStatus(false, "La date de début doit précéder la date de fin");
      return;
    }

    const url = buildUrl();
    fetchData(url);
  });

  quickButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const days = btn.getAttribute("data-days");
      startInput.value = "";
      endInput.value = "";
      fetchData(`/data/lastdays/${days}/json/`, `Derniers ${days} jours`);
    });
  });

  function setDefaultDates() {
    const today = luxon.DateTime.local();
    const yesterday = today.minus({ days: 1 });
    endInput.value = today.toISODate();
    startInput.value = yesterday.toISODate();
  }

  buildDatasetSelector();
  setDefaultDates();
  fetchData("/data/lastdays/2/json/", "Derniers 2 jours");
});
