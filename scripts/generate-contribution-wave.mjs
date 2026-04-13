import { mkdirSync, writeFileSync } from "node:fs";

const username = process.env.GITHUB_USERNAME || "sayedio";
const token = process.env.GITHUB_TOKEN || "";

const today = new Date();
const totalColumns = 53;
const totalRows = 7;
const cell = 12;
const gap = 4;
const chartWidth = totalColumns * (cell + gap) - gap;
const chartHeight = totalRows * (cell + gap) - gap;

const margin = {
  top: 56,
  right: 48,
  bottom: 34,
  left: 76,
};

const width = margin.left + chartWidth + margin.right;
const height = margin.top + chartHeight + margin.bottom;

function toDateKey(date) {
  return date.toISOString().slice(0, 10);
}

function startOfDay(date) {
  const d = new Date(date);
  d.setHours(0, 0, 0, 0);
  return d;
}

function startOnSunday(date) {
  const d = startOfDay(date);
  const day = d.getDay();
  d.setDate(d.getDate() - day);
  return d;
}

const startDate = startOnSunday(
  new Date(
    today.getFullYear(),
    today.getMonth(),
    today.getDate() - (totalColumns * 7 - 1),
  ),
);
const endDate = startOfDay(today);

async function fetchEvents() {
  const counts = new Map();
  const headers = {
    Accept: "application/vnd.github+json",
    "User-Agent": "contribution-wave-generator",
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  let page = 1;
  while (page <= 10) {
    const url = `https://api.github.com/users/${username}/events/public?per_page=100&page=${page}`;
    const res = await fetch(url, { headers });
    if (!res.ok) {
      break;
    }

    const events = await res.json();
    if (!Array.isArray(events) || events.length === 0) {
      break;
    }

    for (const ev of events) {
      const created = new Date(ev.created_at);
      if (created < startDate) {
        continue;
      }
      const key = toDateKey(created);
      counts.set(key, (counts.get(key) || 0) + 1);
    }

    page += 1;
  }

  return counts;
}

function levelFromCount(count) {
  if (count === 0) return 0;
  if (count <= 2) return 1;
  if (count <= 5) return 2;
  if (count <= 9) return 3;
  return 4;
}

function formatDate(date) {
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

(async () => {
  const counts = await fetchEvents();

  const dayLabels = ["Sun", "Tue", "Thu"];
  const dayRows = [0, 2, 4];

  const monthMarks = [];
  let prevMonth = -1;
  for (let col = 0; col < totalColumns; col += 1) {
    const d = new Date(startDate);
    d.setDate(startDate.getDate() + col * 7);
    const month = d.getMonth();
    if (month !== prevMonth) {
      monthMarks.push({
        col,
        label: d.toLocaleDateString("en-US", { month: "short" }),
      });
      prevMonth = month;
    }
  }

  const rects = [];
  let maxCount = 0;

  for (let col = 0; col < totalColumns; col += 1) {
    for (let row = 0; row < totalRows; row += 1) {
      const d = new Date(startDate);
      d.setDate(startDate.getDate() + col * 7 + row);
      const key = toDateKey(d);
      const count = counts.get(key) || 0;
      maxCount = Math.max(maxCount, count);

      const level = levelFromCount(count);
      const x = margin.left + col * (cell + gap);
      const y = margin.top + row * (cell + gap);
      const delay = ((col * 0.06 + row * 0.03) % 3.2).toFixed(2);

      rects.push(
        `<rect class="c l${level}" x="${x}" y="${y}" width="${cell}" height="${cell}" rx="3" data-date="${key}" data-count="${count}" style="animation-delay:${delay}s">` +
          `<title>${formatDate(d)}: ${count} contribution${count === 1 ? "" : "s"}</title></rect>`,
      );
    }
  }

  const subtitle = `Last ${totalColumns * 7} days · Peak ${maxCount} contributions/day`;

  const svg = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}" width="100%" role="img" aria-label="Animated contribution wave for ${username}">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#050a17"/>
      <stop offset="50%" stop-color="#0a1530"/>
      <stop offset="100%" stop-color="#071022"/>
    </linearGradient>
    <radialGradient id="auraLeft" cx="25%" cy="45%" r="55%">
      <stop offset="0%" stop-color="#1d4ed8" stop-opacity="0.26"/>
      <stop offset="100%" stop-color="#1d4ed8" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="auraRight" cx="78%" cy="54%" r="45%">
      <stop offset="0%" stop-color="#0ea5e9" stop-opacity="0.18"/>
      <stop offset="100%" stop-color="#0ea5e9" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="sweep" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#ffffff" stop-opacity="0"/>
      <stop offset="50%" stop-color="#93c5fd" stop-opacity="0.25"/>
      <stop offset="100%" stop-color="#ffffff" stop-opacity="0"/>
    </linearGradient>
    <style>
      .title { font: 700 20px 'Segoe UI', Arial, sans-serif; fill: #dbeafe; letter-spacing: 0.4px; }
      .subtitle { font: 400 12px 'Segoe UI', Arial, sans-serif; fill: #93c5fd; }
      .axis { font: 400 10px 'Segoe UI', Arial, sans-serif; fill: #64748b; }
      .c { stroke: rgba(148, 163, 184, 0.14); stroke-width: 1; transform-origin: center; animation: pulse 3.6s ease-in-out infinite; }
      .l0 { fill: #0b1224; }
      .l1 { fill: #1e3a8a; }
      .l2 { fill: #2563eb; }
      .l3 { fill: #3b82f6; }
      .l4 { fill: #60a5fa; }
      .sweep { animation: glide 7s linear infinite; }
      .aura { animation: breathe 6s ease-in-out infinite; }
      @keyframes pulse { 0%, 100% { filter: brightness(1); } 50% { filter: brightness(1.22); } }
      @keyframes glide { 0% { transform: translateX(-140px); opacity: 0; } 10% { opacity: 1; } 90% { opacity: 1; } 100% { transform: translateX(${width + 140}px); opacity: 0; } }
      @keyframes breathe { 0%, 100% { opacity: 0.55; } 50% { opacity: 0.85; } }
    </style>
    <clipPath id="gridClip"><rect x="${margin.left}" y="${margin.top}" width="${chartWidth}" height="${chartHeight}" rx="10"/></clipPath>
  </defs>

  <rect width="${width}" height="${height}" rx="18" fill="url(#bg)"/>
  <rect width="${width}" height="${height}" rx="18" fill="url(#auraLeft)" class="aura"/>
  <rect width="${width}" height="${height}" rx="18" fill="url(#auraRight)" class="aura"/>

  <text x="${margin.left}" y="30" class="title">Contribution Aurora Wave</text>
  <text x="${margin.left}" y="48" class="subtitle">${subtitle}</text>

  ${dayRows.map((r, i) => `<text x="${margin.left - 12}" y="${margin.top + r * (cell + gap) + 10}" text-anchor="end" class="axis">${dayLabels[i]}</text>`).join("\n  ")}
  ${monthMarks.map((m) => `<text x="${margin.left + m.col * (cell + gap)}" y="${height - 10}" class="axis">${m.label}</text>`).join("\n  ")}

  <g>${rects.join("")}</g>

  <g clip-path="url(#gridClip)">
    <rect class="sweep" x="0" y="${margin.top - 8}" width="120" height="${chartHeight + 16}" fill="url(#sweep)"/>
  </g>
</svg>
`;

  mkdirSync("dist", { recursive: true });
  writeFileSync("dist/contribution-wave.svg", svg, "utf8");
})();
