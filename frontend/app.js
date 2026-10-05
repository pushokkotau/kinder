const state = {
  screen: "login",
  authenticated: false,
  token: null,
  city: null,
  mode: null,
  swipes: 0,
  swipeLimit: 100,
  matchesBefore: 0,
  matchesAfter: 0,
  newMatches: 0
};

const recommendations = [
  { name: "Maria", age: 27, city: "New York", bio: "Love travelling, coffee and long walks." },
  { name: "Anna", age: 25, city: "London", bio: "Music, books and good conversations." },
  { name: "Elena", age: 29, city: "Barcelona", bio: "Beach, food and spontaneous adventures." }
];

let recommendationIndex = 0;

function render() {
  const app = document.querySelector("#app");

  app.innerHTML = `
    <div class="app">
      ${renderScreen()}
    </div>
  `;
}

function renderScreen() {
  switch (state.screen) {
    case "login": return loginScreen();
    case "city": return cityScreen();
    case "mode": return modeScreen();
    case "swipe": return swipeScreen();
    case "auto": return autoScreen();
    case "result": return resultScreen();
    case "matches": return matchesScreen();
    default: return "<p>Unknown screen</p>";
  }
}

function loginScreen() {
  return `
    <h1>Login</h1>
    <p class="muted">Test authorization</p>
    <form id="loginForm">
      <input id="token" placeholder="Enter token" required>
      <br><br>
      <button type="submit">Login</button>
    </form>
  `;
}

function cityScreen() {
  return `
    <h1>Choose city</h1>
    <p class="muted">Enter any city in the world.</p>
    <form id="cityForm">
      <input id="city" placeholder="New York" required>
      <br><br>
      <button type="submit">Continue</button>
    </form>
  `;
}

function modeScreen() {
  return `
    <h1>Choose mode</h1>
    <p>City: <strong>${state.city}</strong></p>
    <div class="actions">
      <button id="autoBtn">AutoSwipe</button>
      <button id="swipeBtn">Swipe</button>
    </div>
  `;
}

function swipeScreen() {
  const person = recommendations[recommendationIndex % recommendations.length];

  return `
    <h1>Swipe</h1>

    <p>
      City: <strong>${state.city}</strong>
      <button id="editCityBtn" type="button">Edit city</button>
    </p>

    <div class="card">
      <div class="photo">PHOTO</div>
      <h2>${person.name}, ${person.age}</h2>
      <p>${person.city}</p>
      <p>${person.bio}</p>
    </div>

    <p>Swipes: ${state.swipes} / ${state.swipeLimit}</p>

    <div class="actions">
      <button id="dislikeBtn">Dislike</button>
      <button id="likeBtn">Like</button>
    </div>
  `;
}

function cityEditScreen() {
  return `
    <h1>Edit city</h1>
    <p class="muted">Changing the city does not reset your swipe progress.</p>

    <form id="editCityForm">
      <input id="editCity" value="${state.city || ""}" placeholder="New York" required>
      <br><br>
      <div class="actions">
        <button type="button" id="cancelCityBtn">Cancel</button>
        <button type="submit">Save city</button>
      </div>
    </form>

    <p>Swipes: ${state.swipes} / ${state.swipeLimit}</p>
    <p>Matches: ${state.matchesAfter}</p>
  `;
}

function autoScreen() {
  return `
    <h1>AutoSwipe</h1>
    <p>City: <strong>${state.city}</strong></p>
    <p>Progress: ${state.swipes} / ${state.swipeLimit}</p>
    <button id="nextBatchBtn">Next batch</button>
    <button id="stopAutoBtn">Stop</button>
  `;
}

function resultScreen() {
  return `
    <h1>Done</h1>
    <p>New matches: <strong>+${state.newMatches}</strong></p>
    <p>Total matches: <strong>${state.matchesAfter}</strong></p>
    <button id="matchesBtn">Matches</button>
  `;
}

function matchesScreen() {
  return `
    <h1>Matches</h1>
    <p>Total matches: <strong>${state.matchesAfter}</strong></p>
    <button id="backBtn">Back to mode</button>
  `;
}

document.addEventListener("submit", (event) => {
  event.preventDefault();

  if (event.target.id === "loginForm") {
    state.token = document.querySelector("#token").value;
    state.authenticated = true;
    state.screen = "city";
    render();
  }

  if (event.target.id === "cityForm") {
    state.city = document.querySelector("#city").value.trim();
    state.screen = "mode";
    render();
  }

  if (event.target.id === "editCityForm") {
    const newCity = document.querySelector("#editCity").value.trim();

    if (!newCity) {
      return;
    }

    state.city = newCity;
    state.screen = "swipe";
    render();
  }
});

document.addEventListener("click", (event) => {
  if (event.target.id === "autoBtn") {
    state.mode = "auto";
    state.matchesBefore = state.matchesAfter;
    state.screen = "auto";
    render();
  }

  if (event.target.id === "swipeBtn") {
    state.mode = "swipe";
    state.matchesBefore = state.matchesAfter;
    state.screen = "swipe";
    render();
  }

  if (event.target.id === "editCityBtn") {
    state.screen = "editCity";
    render();
  }

  if (event.target.id === "cancelCityBtn") {
    state.screen = "swipe";
    render();
  }

  if (event.target.id === "likeBtn" || event.target.id === "dislikeBtn") {
    if (state.swipes >= state.swipeLimit) {
      finishSwiping();
      return;
    }

    state.swipes += 1;

    if (event.target.id === "likeBtn" && Math.random() > 0.6) {
      state.newMatches += 1;
      state.matchesAfter += 1;
    }

    recommendationIndex += 1;

    if (state.swipes >= state.swipeLimit) {
      finishSwiping();
    } else {
      render();
    }
  }

  if (event.target.id === "nextBatchBtn") {
    const remaining = state.swipeLimit - state.swipes;
    state.swipes += Math.min(10, remaining);

    if (state.swipes >= state.swipeLimit) {
      finishSwiping();
    } else {
      render();
    }
  }

  if (event.target.id === "stopAutoBtn") {
    finishSwiping();
  }

  if (event.target.id === "matchesBtn") {
    state.screen = "matches";
    render();
  }

  if (event.target.id === "backBtn") {
    state.screen = "mode";
    state.swipes = 0;
    state.newMatches = 0;
    render();
  }
});

function finishSwiping() {
  state.screen = "result";
  render();
}

render();
