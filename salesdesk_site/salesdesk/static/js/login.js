// Login feature: name + password. Already signed in? Go straight to Daily Sales.
(function () {
  const { $ } = U;
  if (Auth.loggedIn()) { location.replace("/daily-sales/"); return; }

  $("#app").innerHTML =
    '<div class="login-page"><form class="login-card" id="login-form"><div class="brand-name">Sales Desk</div><h1>Log in</h1>' +
    UI.field("Name", "lg-name", { attrs: 'autocomplete="username"' }) +
    UI.field("Password", "lg-pass", { type: "password", attrs: 'autocomplete="current-password"' }) +
    UI.msg("lg-err") + '<button class="btn btn-primary" type="submit">Log in</button>' +
    (window.CONFIG.DEMO
      ? '<p class="muted" style="font-size:14px">Design demo. Users: OWNER / owner1234, SUMI / 1234 (manager), RAHAT / 1234 (cashier).</p>' +
        '<button type="button" class="btn btn-small" id="reset-demo" style="align-self:flex-start">Reset demo data</button>'
      : "") + "</form></div>";

  $("#login-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const name = $("#lg-name").value.trim(), pass = $("#lg-pass").value;
    if (!name || !pass) return UI.say("lg-err", "Enter your name and password.");
    try { await Auth.login(name, pass); location.href = "/daily-sales/"; }
    catch (err) { UI.say("lg-err", err.message); }
  });
  const reset = $("#reset-demo");
  if (reset) reset.addEventListener("click", () => { window.resetDemo(); Auth.clear(); reset.textContent = "Demo data reset"; });
})();
