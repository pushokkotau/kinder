const API_BASE = window.KINDER_API_BASE || "http://localhost:8000/api/v1";
const state = { token: localStorage.getItem("kinder_session_token"), city: "", selectedCity: "", recommendations: [], index: 0, photoIndex: 0, beforeMatches: 0 };

const $ = (id) => document.getElementById(id);
function toast(message) { $("toast").textContent = message; $("toast").classList.add("show"); clearTimeout(toast.timer); toast.timer = setTimeout(() => $("toast").classList.remove("show"), 1600); }

async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  const response = await fetch(API_BASE + path, { ...options, headers });
  let data = {};
  try { data = await response.json(); } catch (_) {}
  if (response.status === 401) { logout(false); throw new Error("Сессия истекла. Войдите снова."); }
  if (!response.ok) throw new Error(data.detail || `API error: ${response.status}`);
  return data;
}

function requireAuth() {
  if (!state.token) {
    $("profileName").textContent = "Нужна авторизация";
    $("profileMeta").textContent = "Перед подключением frontend нужен Tinder token.";
    $("profileBio").textContent = "Откройте API-авторизацию или установите session token в localStorage.";
    $("profileCard").classList.remove("hidden");
    $("emptyState").classList.add("hidden");
    return false;
  }
  return true;
}

async function loadProfile() {
  const profile = await api("/profile");
  state.city = profile.city || "Город не определен";
  $("cityName").textContent = state.city;
}

async function loadMatches() {
  const data = await api("/matches/count");
  $("matchesCount").textContent = data.count;
  return data.count;
}

async function loadRecommendations() {
  const data = await api("/recommendations");
  state.recommendations = data.recommendations || [];
  state.index = 0;
  $("autoSwipeButton").classList.remove("hidden");
  render();
}

function render() {
  const profile = state.recommendations[state.index];
  if (!profile) {
    $("profileCard").classList.add("hidden");
    $("actions").classList.add("hidden");
    $("emptyState").classList.remove("hidden");
    $("autoSwipeButton").classList.add("hidden");
    $("status").textContent = "Подборка завершена";
    return;
  }
  $("emptyState").classList.add("hidden");
  $("profileCard").classList.remove("hidden");
  $("actions").classList.remove("hidden");
  state.photoIndex = 0;
  $("profilePhoto").classList.remove("photo-placeholder");
  $("profilePhoto").src = profile.photos?.[0]?.url || profile.photos?.[0] || "";
  $("profilePhoto").onerror = () => { $("profilePhoto").removeAttribute("src"); $("profilePhoto").classList.add("photo-placeholder"); };
  $("profileName").textContent = profile.name || "Без имени";
  $("profileAge").textContent = "";
  $("profileMeta").textContent = state.city;
  $("profileBio").textContent = "";
  $("status").textContent = "Новая рекомендация";
  $("matchesCount").textContent = $("matchesCount").textContent || "0";
  $("photoDots").innerHTML = (profile.photos || []).map((_, i) => `<i class="${i === 0 ? "active" : ""}" data-photo-index="${i}"></i>`).join("");
  document.querySelectorAll("#photoDots i").forEach(dot => dot.addEventListener("click", () => showPhoto(Number(dot.dataset.photoIndex))));
}

function showPhoto(index) {
  const profile = state.recommendations[state.index];
  const photos = profile?.photos || [];
  if (!photos.length) return;
  state.photoIndex = Math.max(0, Math.min(index, photos.length - 1));
  const photo = photos[state.photoIndex];
  $("profilePhoto").classList.remove("photo-placeholder");
  $("profilePhoto").src = photo?.url || photo || "";
  $("profilePhoto").onerror = () => { $("profilePhoto").removeAttribute("src"); $("profilePhoto").classList.add("photo-placeholder"); };
  document.querySelectorAll("#photoDots i").forEach((dot, i) => dot.classList.toggle("active", i === state.photoIndex));
}

function changePhoto(direction) {
  const photos = state.recommendations[state.index]?.photos || [];
  if (photos.length < 2) return;
  showPhoto((state.photoIndex + direction + photos.length) % photos.length);
}

async function swipe(action) {
  const profile = state.recommendations[state.index];
  if (!profile) return;
  try {
    await api(`/swipes/${action}/${encodeURIComponent(profile.id)}`, { method: "POST" });
    state.index += 1;
    if (action === "like") toast("♥ Лайк отправлен"); else toast("× Пропущено");
    render();
    if (!state.recommendations[state.index]) await finishManualSwiping();
  } catch (error) { toast(error.message); }
}

async function finishManualSwiping() {
  try {
    const afterMatches = await loadMatches();
    const newMatches = Math.max(0, afterMatches - state.beforeMatches);
    $("status").textContent = "Свайпинг завершён";
    $("emptyState").querySelector("h2").textContent = "Свайпинг завершён ♥";
    $("swipeResultText").textContent = `Новых матчей: +${newMatches} · Всего матчей: ${afterMatches}`;
  } catch (error) {
    toast(error.message);
  }
}

async function applyCity() {
  const city = $("customCity").value.trim() || state.selectedCity;
  if (!city) return;
  try {
    await api("/location", { method: "POST", body: JSON.stringify({ city }) });
    state.city = city;
    state.selectedCity = city;
    state.recommendations = [];
    state.index = 0;
    $("cityName").textContent = city;
    $("cityDialog").close();
    $("emptyState").classList.add("hidden");
    $("profileCard").classList.remove("hidden");
    $("actions").classList.remove("hidden");
    state.beforeMatches = await loadMatches();
    toast(`Ищем анкеты в городе «${city}»`);
    await loadRecommendations();
  } catch (error) { toast(error.message); }
}

function initCities() {
  const cities = ["Амстердам", "Москва", "Нью-Йорк", "Лондон", "Берлин", "Париж"];
  $("cityOptions").innerHTML = cities.map(city => `<button type="button" class="city-option ${city === state.city ? "selected" : ""}" data-city="${city}">${city}</button>`).join("");
  document.querySelectorAll(".city-option").forEach(button => button.addEventListener("click", () => {
    state.selectedCity = button.dataset.city;
    document.querySelectorAll(".city-option").forEach(item => item.classList.remove("selected"));
    button.classList.add("selected");
    $("customCity").value = "";
  }));
}

async function authenticateToken(token) {
  const data = await api("/auth/token", { method: "POST", body: JSON.stringify({ token }) });
  state.token = data.session_token;
  localStorage.setItem("kinder_session_token", state.token);
}
async function requestPhone(phone) {
  const data = await api("/auth/phone", { method: "POST", body: JSON.stringify({ phone }) });
  state.phone = phone;
  state.token = data.session_token;
  localStorage.setItem("kinder_session_token", state.token);
}
async function verifyPhone(code) {
  const data = await api("/auth/phone/verify", { method: "POST", body: JSON.stringify({ phone: state.phone, code }) });
  state.token = data.session_token;
  localStorage.setItem("kinder_session_token", state.token);
}
function logout(showToast = true) {
  state.token = "";
  localStorage.removeItem("kinder_session_token");
  $("appScreen").classList.add("hidden");
  $("authScreen").classList.remove("hidden");
  $("authChoice").classList.remove("hidden");
  ["tokenForm", "phoneForm", "codeForm"].forEach(id => $(id).classList.add("hidden"));
  if (showToast) toast("Вы вышли из аккаунта");
}

async function runAutoSwipe() {
  $("autoSwipeButton").disabled = true;
  $("autoSwipeButton").textContent = "Свайпинг…";
  $("status").textContent = "Запускаем AutoSwipe…";
  try {
    const result = await api("/autoswipe", { method: "POST" });
    $("profileCard").classList.add("hidden");
    $("emptyState").classList.remove("hidden");
    $("actions").classList.add("hidden");
    $("autoSwipeButton").classList.add("hidden");
    $("emptyState").querySelector("h2").textContent = "AutoSwipe завершён ♥";
    $("swipeResultText").textContent = `Свайпов: ${result.swipes} · Лайков: ${result.likes} · Дизлайков: ${result.dislikes} · Новых матчей: +${result.new_matches} · Всего: ${result.matches_after}`;
    $("status").textContent = "Готово";
  } catch (error) {
    toast(error.message);
  }
}

function openCityDialog() {
  state.selectedCity = "";
  $("customCity").value = "";
  initCities();
  $("cityDialog").showModal();
}

function showApp() {
  $("authScreen").classList.add("hidden");
  $("appScreen").classList.remove("hidden");
}
function showAuthForm(id) {
  ["tokenForm", "phoneForm", "codeForm"].forEach(form => $(form).classList.add("hidden"));
  $(id).classList.remove("hidden");
  $("authChoice").classList.add("hidden");
}
$("tokenAuthButton").addEventListener("click", () => showAuthForm("tokenForm"));
$("phoneAuthButton").addEventListener("click", () => showAuthForm("phoneForm"));
$("logoutButton").addEventListener("click", () => logout());
$("tokenForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  try { await authenticateToken($("tokenInput").value.trim()); await init(); }
  catch (error) { toast(error.message); }
});
$("phoneForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  try { await requestPhone($("phoneInput").value.trim()); showAuthForm("codeForm"); }
  catch (error) { toast(error.message); }
});
$("codeForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  try { await verifyPhone($("codeInput").value.trim()); await init(); }
  catch (error) { toast(error.message); }
});
async function init() {
  if (!state.token) return;
  try {
    showApp();
    await loadProfile();
    $("status").textContent = "Выбери город";
    $("profileCard").classList.add("hidden");
    $("emptyState").classList.add("hidden");
    openCityDialog();
  } catch (error) {
    logout(false);
    toast(error.message);
  }
}

$("likeButton").addEventListener("click", () => swipe("like"));
$("dislikeButton").addEventListener("click", () => swipe("dislike"));
$("profilePhoto").addEventListener("click", (event) => {
  const rect = $("profilePhoto").getBoundingClientRect();
  changePhoto(event.clientX < rect.left + rect.width / 2 ? -1 : 1);
});
document.addEventListener("keydown", (event) => {
  if (event.key === "ArrowLeft") swipe("dislike");
  if (event.key === "ArrowRight") swipe("like");
});
$("profilePhoto").addEventListener("click", (event) => {
  const rect = $("profilePhoto").getBoundingClientRect();
  const photos = state.recommendations[state.index]?.photos || [];
  if (photos.length < 2) return;
  const direction = event.clientX < rect.left + rect.width / 2 ? -1 : 1;
  showPhoto((state.photoIndex + direction + photos.length) % photos.length);
});
$("cityButton").addEventListener("click", openCityDialog);
$("changeCityButton").addEventListener("click", openCityDialog);
$("autoSwipeButton").addEventListener("click", runAutoSwipe);
$("applyCityButton").addEventListener("click", (event) => { event.preventDefault(); applyCity(); });
init();