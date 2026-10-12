const rows = document.getElementById("bonus-rows");
const statusEl = document.getElementById("status");
const countEl = document.getElementById("record-count");
const updatedEl = document.getElementById("updated");

function textCell(value) {
  const td = document.createElement("td");
  td.textContent = value === null || value === undefined || value === "" ? "Not found" : String(value);
  return td;
}

function renderRecord(record) {
  const tr = document.createElement("tr");
  const casinoCell = textCell(record.casino);
  if (record.needs_review) {
    const badge = document.createElement("span");
    badge.className = "review";
    badge.textContent = "Review required";
    casinoCell.append(document.createElement("br"), badge);
  }
  tr.append(casinoCell);
  tr.append(textCell(record.welcome_bonus));
  const wagering = record.wagering_text ||
    (record.wagering_requirement !== null && record.wagering_requirement !== undefined
      ? `${record.wagering_requirement}×` : "Not found");
  tr.append(textCell(wagering));
  let deposit = "Not found";
  if (record.minimum_deposit_amount !== null && record.minimum_deposit_amount !== undefined) {
    deposit = `${record.currency || ""} ${record.minimum_deposit_amount}`.trim();
  }
  tr.append(textCell(deposit));
  const sourceCell = document.createElement("td");
  const link = document.createElement("a");
  link.href = record.source_url;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  link.textContent = "View source";
  sourceCell.append(link);
  tr.append(sourceCell);
  return tr;
}

async function loadData() {
  try {
    const response = await fetch("./bonuses.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`Could not load bonuses.json (HTTP ${response.status})`);
    const data = await response.json();
    const records = Array.isArray(data.records) ? data.records : [];
    rows.replaceChildren(...records.map(renderRecord));
    countEl.textContent = `${records.length} record${records.length === 1 ? "" : "s"}`;
    statusEl.textContent = records.length ? "" : "No collected records yet. Run the scraper and refresh this page.";
    updatedEl.textContent = data.collected_at
      ? `Collected: ${new Date(data.collected_at).toLocaleString()}`
      : "Collection timestamp unavailable";
  } catch (error) {
    countEl.textContent = "Unavailable";
    statusEl.textContent = `${error.message}. If opening this file directly, use a local web server instead.`;
  }
}
loadData();
