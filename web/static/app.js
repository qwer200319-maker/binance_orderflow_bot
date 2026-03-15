console.info("Orderflow UI v21 loaded");
const UI_VERSION = "v21";
const DEFAULT_API_BASE = "https://binance-orderflow-bot-ms21.onrender.com";

const params = new URLSearchParams(window.location.search);
const apiParam = params.get("api");
const storedBase = window.localStorage.getItem("apiBase");
let API_BASE = apiParam || storedBase || DEFAULT_API_BASE || "";
API_BASE = API_BASE.replace(/\/$/, "");
if (apiParam) {
  window.localStorage.setItem("apiBase", API_BASE);
}

const els = {
  botStatus: document.getElementById("botStatus"),
  lastUpdate: document.getElementById("lastUpdate"),
  uiVersion: document.getElementById("uiVersion"),
  symbol: document.getElementById("symbol"),
  price: document.getElementById("price"),
  currentSignal: document.getElementById("currentSignal"),
  qualityScore: document.getElementById("qualityScore"),
  marketSymbol: document.getElementById("marketSymbol"),
  marketPrice: document.getElementById("marketPrice"),
  htfBias: document.getElementById("htfBias"),
  setupSignal: document.getElementById("setupSignal"),
  marketRegime: document.getElementById("marketRegime"),
  volatility: document.getElementById("volatility"),
  signalCurrent: document.getElementById("signalCurrent"),
  signalQuality: document.getElementById("signalQuality"),
  signalEntry: document.getElementById("signalEntry"),
  signalSL: document.getElementById("signalSL"),
  signalTP1: document.getElementById("signalTP1"),
  signalTP2: document.getElementById("signalTP2"),
  delta5s: document.getElementById("delta5s"),
  delta15s: document.getElementById("delta15s"),
  imbalance: document.getElementById("imbalance"),
  absorption: document.getElementById("absorption"),
  liquidations: document.getElementById("liquidations"),
  liquiditySweep: document.getElementById("liquiditySweep"),
  vwapContext: document.getElementById("vwapContext"),
  vwapValue: document.getElementById("vwapValue"),
  botRunning: document.getElementById("botRunning"),
  lastSignalTime: document.getElementById("lastSignalTime"),
  cooldownRemaining: document.getElementById("cooldownRemaining"),
  signalsList: document.getElementById("signalsList"),
  logsList: document.getElementById("logsList"),
  nextClose: document.getElementById("nextClose"),
  closeCountdown: document.getElementById("closeCountdown"),
  candleTabs: document.getElementById("candleTabs"),
  chartFullscreen: document.getElementById("chartFullscreen"),
  candlesChart: document.getElementById("candlesChart"),
  candleFallback: document.getElementById("candleFallback"),
  chartPanel: document.getElementById("chartPanel"),
};

const chartState = {
  points: [],
  overlays: {},
  ready: false,
};

function formatNumber(value, decimals = 2) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "--";
  }
  return Number(value).toLocaleString(undefined, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

function formatSigned(value, decimals = 2) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "--";
  }
  const sign = value > 0 ? "+" : "";
  return `${sign}${formatNumber(value, decimals)}`;
}

function formatTime(iso) {
  if (!iso) return "--";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "--";
  return date.toLocaleTimeString();
}

function formatDateTime(iso) {
  if (!iso) return "--";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "--";
  return date.toLocaleString();
}

function updatePanel(state) {
  const symbol = state.symbol || "--";
  const price = state.price;

  if (els.symbol) els.symbol.textContent = symbol;
  if (els.price) els.price.textContent = formatNumber(price, 2);
  if (els.currentSignal) els.currentSignal.textContent = state.signal_current || "--";
  if (els.qualityScore) {
    els.qualityScore.textContent = state.quality_score
      ? `${state.quality_score} ${state.quality_grade || ""}`.trim()
      : "--";
  }

  if (els.marketSymbol) els.marketSymbol.textContent = symbol;
  if (els.marketPrice) els.marketPrice.textContent = formatNumber(price, 2);
  if (els.htfBias) els.htfBias.textContent = state.htf_bias || "--";
  if (els.setupSignal) els.setupSignal.textContent = state.setup_signal || "--";
  if (els.marketRegime) els.marketRegime.textContent = state.market_regime || "--";

  const volValue =
    state.volatility_value !== null && state.volatility_value !== undefined
      ? formatNumber(state.volatility_value, 4)
      : "--";
  if (els.volatility) {
    els.volatility.textContent = `${state.volatility_state || "--"} (${volValue})`;
  }

  if (els.signalCurrent) els.signalCurrent.textContent = state.signal_current || "--";
  if (els.signalQuality) {
    els.signalQuality.textContent = state.quality_score
      ? `${state.quality_score} ${state.quality_grade || ""}`.trim()
      : "--";
  }
  if (els.signalEntry) els.signalEntry.textContent = formatNumber(state.entry, 2);
  if (els.signalSL) els.signalSL.textContent = formatNumber(state.sl, 2);
  if (els.signalTP1) els.signalTP1.textContent = formatNumber(state.tp1, 2);
  if (els.signalTP2) els.signalTP2.textContent = formatNumber(state.tp2, 2);

  if (els.delta5s) els.delta5s.textContent = formatSigned(state.delta_5s, 2);
  if (els.delta15s) els.delta15s.textContent = formatSigned(state.delta_15s, 2);
  if (els.imbalance) els.imbalance.textContent = formatNumber(state.imbalance, 4);

  let absorption = "NONE";
  if (state.bullish_absorption) absorption = "BULLISH";
  if (state.bearish_absorption) absorption = "BEARISH";
  if (els.absorption) els.absorption.textContent = absorption;

  const liq = [];
  if (state.active_buy_liq_cluster) liq.push("ACTIVE BUY");
  if (state.active_sell_liq_cluster) liq.push("ACTIVE SELL");
  if (state.recent_buy_liq_cluster) liq.push("RECENT BUY");
  if (state.recent_sell_liq_cluster) liq.push("RECENT SELL");
  if (els.liquidations) els.liquidations.textContent = liq.length ? liq.join(" • ") : "NONE";

  let sweep = "NONE";
  if (state.bullish_sweep) sweep = "BULLISH";
  if (state.bearish_sweep) sweep = "BEARISH";
  if (els.liquiditySweep) els.liquiditySweep.textContent = sweep;

  const vwapFlags = [];
  if (state.vwap_reclaim) vwapFlags.push("RECLAIM");
  if (state.vwap_reject) vwapFlags.push("REJECT");
  const vwapContext = `${state.vwap_state || "--"}${
    vwapFlags.length ? ` (${vwapFlags.join(", ")})` : ""
  }`;
  if (els.vwapContext) els.vwapContext.textContent = vwapContext;
  if (els.vwapValue) els.vwapValue.textContent = formatNumber(state.vwap, 2);

  const running = Boolean(state.running);
  if (els.botRunning) els.botRunning.textContent = running ? "RUNNING" : "STOPPED";
  if (els.botStatus) {
    els.botStatus.textContent = running ? "RUNNING" : "STOPPED";
    els.botStatus.classList.toggle("warn", !running);
  }
  if (els.lastUpdate) els.lastUpdate.textContent = `Last update ${formatTime(state.ts)}`;
  if (els.lastSignalTime) els.lastSignalTime.textContent = formatDateTime(state.last_signal_time);

  const cooldownRemaining = state.cooldown_remaining || 0;
  if (els.cooldownRemaining) {
    if (cooldownRemaining > 0) {
      els.cooldownRemaining.textContent = `${Math.ceil(cooldownRemaining)}s remaining`;
    } else {
      els.cooldownRemaining.textContent = "Ready";
    }
  }

  updateLists(state);
}

function updateLists(state) {
  if (state.signals && els.signalsList) {
    els.signalsList.innerHTML = state.signals
      .slice()
      .reverse()
      .map((sig) => {
        const when = formatTime(sig.ts);
        return `<div class="list-item"><strong>${sig.side || "?"}</strong> • ${when} • Entry ${formatNumber(
          sig.entry,
          2
        )} • SL ${formatNumber(sig.sl, 2)}</div>`;
      })
      .join("");
  }

  if (state.logs && els.logsList) {
    els.logsList.innerHTML = state.logs
      .slice()
      .reverse()
      .map((log) => {
        const when = formatTime(log.ts);
        return `<div class="list-item"><strong>${log.level}</strong> • ${when}<br />${log.message}</div>`;
      })
      .join("");
  }
}

const candleState = {
  tf: "1m",
  tfMs: 60 * 1000,
  timerId: null,
};

let candleChart;
let candleSeries;

function tfToMs(tf) {
  switch (tf) {
    case "1m":
      return 60 * 1000;
    case "15m":
      return 15 * 60 * 1000;
    case "1h":
      return 60 * 60 * 1000;
    case "4h":
      return 4 * 60 * 60 * 1000;
    case "1d":
      return 24 * 60 * 60 * 1000;
    default:
      return 60 * 1000;
  }
}

function formatCountdown(ms) {
  const total = Math.max(0, Math.floor(ms / 1000));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  const pad = (v) => String(v).padStart(2, "0");
  if (h > 0) return `${pad(h)}:${pad(m)}:${pad(s)}`;
  return `${pad(m)}:${pad(s)}`;
}

function updateCandleTimer() {
  if (!els.nextClose || !els.closeCountdown) return;
  const now = Date.now();
  const tfMs = candleState.tfMs;
  const next = Math.ceil(now / tfMs) * tfMs;
  const diff = next - now;
  els.nextClose.textContent = new Date(next).toLocaleTimeString();
  els.closeCountdown.textContent = formatCountdown(diff);
}

function setCandleFallback(message) {
  if (!els.candleFallback) return;
  if (message) {
    els.candleFallback.textContent = message;
    els.candleFallback.style.display = "flex";
  } else {
    els.candleFallback.style.display = "none";
  }
}

function initCandlesChart() {
  if (!els.candlesChart) return;
  if (!window.LightweightCharts) {
    setCandleFallback("Chart library failed to load.");
    return;
  }
  candleChart = LightweightCharts.createChart(els.candlesChart, {
    layout: {
      background: { color: "#f7f9fc" },
      textColor: "#0f1722",
      fontFamily: "Sora",
    },
    grid: {
      vertLines: { color: "rgba(15, 23, 34, 0.06)" },
      horzLines: { color: "rgba(15, 23, 34, 0.06)" },
    },
    timeScale: {
      timeVisible: true,
      secondsVisible: false,
    },
    rightPriceScale: {
      borderColor: "rgba(15, 23, 34, 0.2)" ,
    },
  });
  candleSeries = candleChart.addCandlestickSeries({
    upColor: "#1f8a5b",
    downColor: "#c14a4a",
    borderVisible: false,
    wickUpColor: "#1f8a5b",
    wickDownColor: "#c14a4a",
  });
  resizeCandleChart();
}

function resizeCandleChart() {
  if (!candleChart || !els.candlesChart) return;
  const { width, height } = els.candlesChart.getBoundingClientRect();
  candleChart.resize(width, height);
}

async function fetchCandles() {
  if (!candleSeries) return;
  try {
    setCandleFallback("Loading candles…");
    const res = await fetch(
      `${API_BASE}/api/candles?interval=${candleState.tf}&limit=200`
    );
    if (!res.ok) {
      throw new Error(`candles ${res.status}`);
    }
    const data = await res.json();
    if (data.candles && data.candles.length) {
      candleSeries.setData(data.candles);
      setCandleFallback("");
    } else {
      setCandleFallback("No candle data yet.");
    }
  } catch (err) {
    console.warn("candles fetch failed", err);
    setCandleFallback("Candle API unavailable.");
  }
}

function setActiveTimeframe(tf) {
  if (!els.candleTabs) return;
  els.candleTabs.querySelectorAll(".tab").forEach((btn) => {
    const isActive = btn.getAttribute("data-tf") === tf;
    btn.classList.toggle("active", isActive);
  });
}

function setTimeframe(tf) {
  candleState.tf = tf;
  candleState.tfMs = tfToMs(tf);
  setActiveTimeframe(tf);
  updateCandleTimer();
  fetchCandles();
}

function initCandleTimer() {
  if (!els.candleTabs) return;
  els.candleTabs.querySelectorAll(".tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      const tf = btn.getAttribute("data-tf") || "1m";
      setTimeframe(tf);
    });
  });
  if (candleState.timerId) clearInterval(candleState.timerId);
  candleState.timerId = setInterval(updateCandleTimer, 1000);
  setTimeframe(candleState.tf);
}

function toggleChartFullscreen() {
  if (!els.chartPanel) return;
  if (!document.fullscreenElement) {
    if (els.chartPanel.requestFullscreen) {
      els.chartPanel.requestFullscreen();
    }
  } else if (document.exitFullscreen) {
    document.exitFullscreen();
  }
}

function initChartFullscreen() {
  if (!els.chartFullscreen || !els.chartPanel) return;
  const btn = els.chartFullscreen;
  btn.addEventListener("click", () => {
    toggleChartFullscreen();
  });
  document.addEventListener("fullscreenchange", () => {
    const isFull = Boolean(document.fullscreenElement);
    btn.textContent = isFull ? "ចេញពីពេញអេក្រង់" : "ពេញអេក្រង់";
    setTimeout(resizeCandleChart, 100);
  });
}

function initCandlesView() {
  window.__setTF = setTimeframe;
  window.__toggleFull = toggleChartFullscreen;
  if (els.uiVersion) els.uiVersion.textContent = `UI ${UI_VERSION}`;
  initCandlesChart();
  initCandleTimer();
  initChartFullscreen();
  fetchCandles();
}

function updateChartFromState(state) {
  const price = state.price;
  if (!price) return;
  const ts = Date.parse(state.ts) / 1000;
  if (!Number.isNaN(ts)) {
    const last = chartState.points[chartState.points.length - 1];
    if (!last || ts > last.ts) {
      chartState.points.push({ ts, price, vwap: state.vwap || 0 });
      if (chartState.points.length > 600) {
        chartState.points.shift();
      }
    } else if (last) {
      last.price = price;
    }
  }
  chartState.overlays = {
    vwap: state.vwap,
    swing_high_1h: state.swing_high_1h,
    swing_low_1h: state.swing_low_1h,
    swing_high_15m: state.swing_high_15m,
    swing_low_15m: state.swing_low_15m,
    entry: state.entry,
    sl: state.sl,
    tp1: state.tp1,
    tp2: state.tp2,
  };
  drawChart();
}

function resizeCanvas(canvas, ctx) {
  const { width, height } = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  canvas.width = width * dpr;
  canvas.height = height * dpr;
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.scale(dpr, dpr);
}

function drawChart() {
  const canvas = document.getElementById("priceChart");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  resizeCanvas(canvas, ctx);

  const { width, height } = canvas.getBoundingClientRect();
  ctx.clearRect(0, 0, width, height);

  if (!chartState.points.length) {
    ctx.fillStyle = "rgba(15, 23, 34, 0.55)";
    ctx.font = "14px Sora";
    ctx.fillText("Waiting for data…", 16, 24);
    return;
  }

  const padding = 24;
  const prices = chartState.points.map((p) => p.price);
  let min = Math.min(...prices);
  let max = Math.max(...prices);
  if (min === max) {
    min -= 1;
    max += 1;
  }
  const range = max - min;
  min -= range * 0.08;
  max += range * 0.08;

  const scaleX = (idx) =>
    padding +
    (idx / (chartState.points.length - 1 || 1)) * (width - padding * 2);
  const scaleY = (price) =>
    padding + ((max - price) / (max - min)) * (height - padding * 2);

  ctx.strokeStyle = "rgba(12, 124, 136, 0.75)";
  ctx.lineWidth = 2;
  ctx.beginPath();
  chartState.points.forEach((point, idx) => {
    const x = scaleX(idx);
    const y = scaleY(point.price);
    if (idx === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();

  const drawLevel = (value, color, label) => {
    if (value === null || value === undefined || Number.isNaN(value) || value <= 0) return;
    const y = scaleY(value);
    ctx.strokeStyle = color;
    ctx.lineWidth = 1;
    ctx.setLineDash([6, 4]);
    ctx.beginPath();
    ctx.moveTo(padding, y);
    ctx.lineTo(width - padding, y);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = color;
    ctx.font = "12px JetBrains Mono";
    ctx.fillText(`${label} ${formatNumber(value, 2)}`, padding + 6, y - 6);
  };

  const overlays = chartState.overlays || {};
  drawLevel(overlays.vwap, "rgba(47, 110, 164, 0.85)", "VWAP");
  drawLevel(overlays.swing_high_1h, "rgba(227, 154, 23, 0.85)", "1H High");
  drawLevel(overlays.swing_low_1h, "rgba(227, 154, 23, 0.85)", "1H Low");
  drawLevel(overlays.swing_high_15m, "rgba(12, 124, 136, 0.85)", "15m High");
  drawLevel(overlays.swing_low_15m, "rgba(12, 124, 136, 0.85)", "15m Low");
  drawLevel(overlays.entry, "rgba(15, 23, 34, 0.85)", "Entry");
  drawLevel(overlays.sl, "rgba(193, 74, 74, 0.9)", "SL");
  drawLevel(overlays.tp1, "rgba(31, 138, 91, 0.9)", "TP1");
  drawLevel(overlays.tp2, "rgba(31, 138, 91, 0.9)", "TP2");
}

async function fetchChart() {
  try {
    const res = await fetch(`${API_BASE}/api/chart`);
    const data = await res.json();
    chartState.points = data.points || [];
    chartState.overlays = data.overlays || {};
    drawChart();
  } catch (err) {
    console.warn("chart fetch failed", err);
  }
}

async function pollState() {
  try {
    const res = await fetch(`${API_BASE}/api/state`);
    const state = await res.json();
    updatePanel(state);
    updateChartFromState(state);
  } catch (err) {
    console.warn("state poll failed", err);
  }
}

function connectStream() {
  const es = new EventSource(`${API_BASE}/api/stream`);
  es.onmessage = (event) => {
    const state = JSON.parse(event.data);
    updatePanel(state);
    updateChartFromState(state);
  };
  es.onerror = () => {
    es.close();
    setInterval(pollState, 2000);
  };
}

function initExpanders() {
  document.querySelectorAll("[data-toggle=\"expand\"]").forEach((btn) => {
    const targetSel = btn.getAttribute("data-target");
    const target = targetSel ? document.querySelector(targetSel) : null;
    if (!target) return;
    btn.addEventListener("click", () => {
      const expanded = target.classList.toggle("expanded");
      btn.setAttribute("aria-expanded", expanded ? "true" : "false");
      btn.textContent = expanded ? "ពង្រួម" : "ពង្រីក";
    });
  });
}

window.addEventListener("resize", () => {
  drawChart();
  resizeCandleChart();
});

fetchChart();
pollState();
connectStream();
initExpanders();
initCandlesView();

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch((err) => {
      console.warn("service worker registration failed", err);
    });
  });
}
