const goals = [
  { id: "focus", label: "Focus", mark: "F" },
  { id: "energy", label: "Energy", mark: "E" },
  { id: "stress", label: "Stress", mark: "S" },
  { id: "learning", label: "Learning", mark: "L" },
  { id: "wellbeing", label: "Wellbeing", mark: "W" },
];

let selectedGoal = "focus";
let currentHabit = null;
const apiBase = (window.MICRO_HABIT_API_URL || localStorage.getItem("MICRO_HABIT_API_URL") || "").replace(/\/$/, "");

const goalGrid = document.querySelector("#goalGrid");
const databaseStatus = document.querySelector("#databaseStatus");
const habitTitle = document.querySelector("#habitTitle");
const habitDescription = document.querySelector("#habitDescription");
const habitMeta = document.querySelector("#habitMeta");
const noteInput = document.querySelector("#noteInput");
const toast = document.querySelector("#toast");

function showToast(message) {
  toast.textContent = message;
  toast.classList.add("visible");
  window.setTimeout(() => toast.classList.remove("visible"), 2400);
}

async function api(path, options = {}) {
  const response = await fetch(`${apiBase}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Something went wrong.");
  }
  return data;
}

function renderGoals() {
  goalGrid.innerHTML = "";
  goals.forEach((goal) => {
    const button = document.createElement("button");
    button.className = `goal-button ${goal.id === selectedGoal ? "active" : ""}`;
    button.type = "button";
    button.innerHTML = `<span>${goal.label}</span><strong>${goal.mark}</strong>`;
    button.addEventListener("click", async () => {
      selectedGoal = goal.id;
      renderGoals();
      await loadTodayHabit();
    });
    goalGrid.appendChild(button);
  });
}

async function loadHealth() {
  try {
    const data = await api("/api/health");
    databaseStatus.textContent = `${data.database.toUpperCase()} connected`;
  } catch (error) {
    databaseStatus.textContent = "Offline";
  }
}

async function loadTodayHabit() {
  habitTitle.textContent = "Loading habit...";
  habitDescription.textContent = "";
  habitMeta.textContent = "-- min";
  const data = await api(`/api/habits/today?goal=${encodeURIComponent(selectedGoal)}`);
  currentHabit = data.habit;
  habitTitle.textContent = currentHabit.title;
  habitDescription.textContent = currentHabit.description;
  habitMeta.textContent = `${currentHabit.minutes} min · ${currentHabit.difficulty}`;
}

async function submitCheckin(status) {
  if (!currentHabit) return;
  const data = await api("/api/checkins", {
    method: "POST",
    body: JSON.stringify({
      habit_id: currentHabit.id,
      status,
      note: noteInput.value,
    }),
  });
  noteInput.value = "";
  renderProgress(data.progress);
  showToast(status === "completed" ? "Nice. Tiny win logged." : "Skipped today. Still useful data.");
}

async function loadProgress() {
  const data = await api("/api/progress");
  renderProgress(data);
}

function renderProgress(data) {
  document.querySelector("#streakValue").textContent = data.streak;
  document.querySelector("#rateValue").textContent = `${data.completion_rate}%`;
  document.querySelector("#totalValue").textContent = data.total;
  renderWeek(data.week);
  renderRecent(data.recent);
}

function renderWeek(week) {
  const chart = document.querySelector("#weekChart");
  chart.innerHTML = "";
  const max = Math.max(1, ...week.map((day) => day.completed + day.skipped));
  week.forEach((day) => {
    const total = day.completed + day.skipped;
    const height = 14 + Math.round((total / max) * 76);
    const item = document.createElement("div");
    item.className = "day-bar";
    item.innerHTML = `
      <div class="bar ${total ? "has-work" : ""}" style="height:${height}px"></div>
      <span>${day.label}</span>
    `;
    chart.appendChild(item);
  });
}

function renderRecent(recent) {
  const list = document.querySelector("#recentList");
  list.innerHTML = "";
  if (!recent.length) {
    list.innerHTML = `<p class="recent-meta">No check-ins yet. Complete your first tiny habit to start the log.</p>`;
    return;
  }

  recent.forEach((item) => {
    const row = document.createElement("div");
    row.className = "recent-item";
    row.innerHTML = `
      <span class="recent-dot ${item.status}"></span>
      <div>
        <p class="recent-title">${item.habit_title || item.goal}</p>
        <p class="recent-meta">${item.status} · ${item.checkin_date}</p>
      </div>
      <strong>${item.goal}</strong>
    `;
    list.appendChild(row);
  });
}

async function addCustomHabit(event) {
  event.preventDefault();
  const payload = {
    goal: document.querySelector("#customGoal").value,
    title: document.querySelector("#customTitle").value,
    description: document.querySelector("#customDescription").value,
    minutes: document.querySelector("#customMinutes").value,
    difficulty: "Custom",
  };
  await api("/api/habits", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  event.target.reset();
  document.querySelector("#customMinutes").value = 5;
  showToast("Custom habit saved.");
  if (payload.goal === selectedGoal) {
    await loadTodayHabit();
  }
}

document.querySelector("#completeButton").addEventListener("click", () => submitCheckin("completed"));
document.querySelector("#skipButton").addEventListener("click", () => submitCheckin("skipped"));
document.querySelector("#refreshButton").addEventListener("click", loadTodayHabit);
document.querySelector("#habitForm").addEventListener("submit", addCustomHabit);

async function init() {
  renderGoals();
  await Promise.all([loadHealth(), loadTodayHabit(), loadProgress()]);
}

init().catch((error) => showToast(error.message));
