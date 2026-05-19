const goals = [
  { id: "focus", label: "Focus", mark: "F" },
  { id: "energy", label: "Energy", mark: "E" },
  { id: "stress", label: "Stress", mark: "S" },
  { id: "learning", label: "Learning", mark: "L" },
  { id: "wellbeing", label: "Wellbeing", mark: "W" },
];

let selectedGoal = "focus";
let selectedLibraryGoal = "all";
let currentHabit = null;
let calendarDate = new Date();
const apiBase = (window.MICRO_HABIT_API_URL || localStorage.getItem("MICRO_HABIT_API_URL") || "").replace(/\/$/, "");

const goalGrid = document.querySelector("#goalGrid");
const databaseStatus = document.querySelector("#databaseStatus");
const habitTitle = document.querySelector("#habitTitle");
const habitDescription = document.querySelector("#habitDescription");
const habitMeta = document.querySelector("#habitMeta");
const noteInput = document.querySelector("#noteInput");
const toast = document.querySelector("#toast");
const completeButton = document.querySelector("#completeButton");
const skipButton = document.querySelector("#skipButton");
const refreshButton = document.querySelector("#refreshButton");

function showToast(message) {
  toast.textContent = message;
  toast.classList.add("visible");
  window.setTimeout(() => toast.classList.remove("visible"), 2800);
}

function setBusy(isBusy) {
  completeButton.disabled = isBusy;
  skipButton.disabled = isBusy;
  refreshButton.disabled = isBusy;
}

async function api(path, options = {}) {
  const response = await fetch(`${apiBase}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const text = await response.text();
  let data = {};

  try {
    data = text ? JSON.parse(text) : {};
  } catch (error) {
    data = { error: text || "The server returned an invalid response." };
  }

  if (!response.ok) {
    throw new Error(data.error || `Request failed with status ${response.status}.`);
  }
  return data;
}

function renderGoals() {
  goalGrid.innerHTML = "";
  goals.forEach((goal) => {
    const button = document.createElement("button");
    button.className = `goal-button ${goal.id === selectedGoal ? "active" : ""}`;
    button.type = "button";
    button.textContent = goal.label;
    button.addEventListener("click", async () => {
      selectedGoal = goal.id;
      renderGoals();
      await loadTodayHabit();
    });
    goalGrid.appendChild(button);
  });
}

function renderLibraryTabs() {
  const tabs = document.querySelector("#libraryTabs");
  tabs.innerHTML = "";
  [{ id: "all", label: "All" }, ...goals].forEach((goal) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `tab-button ${selectedLibraryGoal === goal.id ? "active" : ""}`;
    button.textContent = goal.label;
    button.addEventListener("click", async () => {
      selectedLibraryGoal = goal.id;
      renderLibraryTabs();
      await loadHabitLibrary();
    });
    tabs.appendChild(button);
  });
}

async function loadHealth() {
  try {
    const data = await api("/api/health");
    databaseStatus.textContent = `${data.database.toUpperCase()} connected`;
  } catch (error) {
    databaseStatus.textContent = "Backend offline";
    showToast(error.message);
  }
}

async function loadTodayHabit() {
  setBusy(true);
  habitTitle.textContent = "Loading habit...";
  habitDescription.textContent = "Getting a realistic action for your current goal.";
  habitMeta.textContent = "-- min";

  try {
    const data = await api(`/api/habits/today?goal=${encodeURIComponent(selectedGoal)}`);
    currentHabit = data.habit;
    habitTitle.textContent = currentHabit.title;
    habitDescription.textContent = currentHabit.description;
    habitMeta.textContent = `${currentHabit.minutes} min - ${currentHabit.difficulty}`;
  } catch (error) {
    currentHabit = null;
    habitTitle.textContent = "Could not load habit";
    habitDescription.textContent = error.message;
    habitMeta.textContent = "Check API";
    showToast(error.message);
  } finally {
    setBusy(false);
  }
}

async function submitCheckin(status) {
  if (!currentHabit) {
    showToast("Load a habit first.");
    return;
  }

  setBusy(true);
  try {
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
    await Promise.all([loadCalendar(), loadHabitLibrary()]);
    showToast(status === "completed" ? "Tiny win logged." : "Skip logged. Keep the signal honest.");
  } catch (error) {
    showToast(error.message);
  } finally {
    setBusy(false);
  }
}

async function loadProgress() {
  try {
    const data = await api("/api/progress");
    renderProgress(data);
  } catch (error) {
    showToast(error.message);
  }
}

function renderProgress(data) {
  document.querySelector("#streakValue").textContent = data.streak;
  document.querySelector("#rateValue").textContent = `${data.completion_rate}%`;
  document.querySelector("#totalValue").textContent = data.total;
  renderWeek(data.week || []);
  renderRecent(data.recent || []);
  renderGoalBreakdown(data.goal_totals || []);
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

function renderGoalBreakdown(goalTotals) {
  const container = document.querySelector("#goalBreakdown");
  if (!goalTotals.length) {
    container.innerHTML = `<p class="recent-meta">No goal data yet.</p>`;
    return;
  }

  const max = Math.max(1, ...goalTotals.map((item) => Number(item.total)));
  container.innerHTML = goalTotals
    .map((item) => {
      const width = Math.max(8, Math.round((Number(item.completed) / max) * 100));
      return `
        <div class="goal-meter">
          <span>${item.goal}</span>
          <div><i style="width:${width}%"></i></div>
          <strong>${item.completed}/${item.total}</strong>
        </div>
      `;
    })
    .join("");
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
        <p class="recent-meta">${item.status} - ${item.checkin_date}</p>
      </div>
      <strong>${item.goal}</strong>
    `;
    list.appendChild(row);
  });
}

async function loadCalendar() {
  try {
    const year = calendarDate.getFullYear();
    const month = calendarDate.getMonth() + 1;
    const data = await api(`/api/calendar?year=${year}&month=${month}`);
    renderCalendar(data);
  } catch (error) {
    showToast(error.message);
  }
}

function renderCalendar(data) {
  document.querySelector("#calendarTitle").textContent = data.month_label;
  const grid = document.querySelector("#calendarGrid");
  grid.innerHTML = "";

  data.days.forEach((day) => {
    const cell = document.createElement("div");
    const total = (day.completed || 0) + (day.skipped || 0);
    cell.className = `calendar-day ${day.outside ? "outside" : ""} ${day.today ? "today" : ""} ${total ? "active" : ""}`;
    cell.innerHTML = `
      <strong>${day.day}</strong>
      ${total ? `<span>${day.completed || 0} done</span><small>${day.skipped || 0} skipped</small>` : ""}
    `;
    grid.appendChild(cell);
  });
}

async function loadHabitLibrary() {
  try {
    const query = selectedLibraryGoal === "all" ? "" : `?goal=${encodeURIComponent(selectedLibraryGoal)}`;
    const data = await api(`/api/habits${query}`);
    renderHabitLibrary(data.habits || []);
  } catch (error) {
    showToast(error.message);
  }
}

function renderHabitLibrary(habits) {
  document.querySelector("#habitCount").textContent = `${habits.length} habits`;
  const library = document.querySelector("#habitLibrary");
  if (!habits.length) {
    library.innerHTML = `<p class="recent-meta">No habits found for this goal.</p>`;
    return;
  }

  library.innerHTML = habits
    .slice(0, 6)
    .map(
      (habit) => `
        <article class="habit-card">
          <div>
            <strong>${habit.title}</strong>
            <p>${habit.description}</p>
          </div>
          <span>${habit.goal} - ${habit.minutes} min</span>
        </article>
      `,
    )
    .join("");
}

async function addCustomHabit(event) {
  event.preventDefault();
  const payload = {
    goal: document.querySelector("#customGoal").value,
    title: document.querySelector("#customTitle").value.trim(),
    description: document.querySelector("#customDescription").value.trim(),
    minutes: document.querySelector("#customMinutes").value,
    difficulty: "Custom",
  };

  if (!payload.title || !payload.description) {
    showToast("Add a title and description first.");
    return;
  }

  try {
    await api("/api/habits", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    event.target.reset();
    document.querySelector("#customMinutes").value = 5;
    showToast("Custom habit saved.");
    await Promise.all([loadHabitLibrary(), payload.goal === selectedGoal ? loadTodayHabit() : Promise.resolve()]);
  } catch (error) {
    showToast(error.message);
  }
}

completeButton.addEventListener("click", () => submitCheckin("completed"));
skipButton.addEventListener("click", () => submitCheckin("skipped"));
refreshButton.addEventListener("click", loadTodayHabit);
document.querySelector("#habitForm").addEventListener("submit", addCustomHabit);
document.querySelector("#prevMonthButton").addEventListener("click", async () => {
  calendarDate = new Date(calendarDate.getFullYear(), calendarDate.getMonth() - 1, 1);
  await loadCalendar();
});
document.querySelector("#nextMonthButton").addEventListener("click", async () => {
  calendarDate = new Date(calendarDate.getFullYear(), calendarDate.getMonth() + 1, 1);
  await loadCalendar();
});

async function init() {
  renderGoals();
  renderLibraryTabs();
  await Promise.all([loadHealth(), loadTodayHabit(), loadProgress(), loadCalendar(), loadHabitLibrary()]);
}

init().catch((error) => showToast(error.message));
