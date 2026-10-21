// Shell (top bar, side menu, profile menu) and page start-up. Every feature page calls App.start("<area>").
(function () {
  const { $, esc } = U;
  const PAGES = {"daily": "/daily-sales/", "due": "/due/", "wholesale": "/whole-sale/", "company": "/company-payment/", "closing": "/day-closing/", "report": "/report/", "settings": "/settings/"};
  const LABELS = { daily: "Daily Sales", due: "Due", wholesale: "Whole Sale", company: "Company Payment", closing: "Day Closing", report: "Report", settings: "Settings" };
  const ORDER = ["daily", "due", "wholesale", "company", "closing", "report", "settings"];
  const S = { menu: false, notice: "", current: null };
  // every feature page sits one folder below the site root: features/<name>/<name>.html
  const LOGIN = "/login/";

  Auth.loginUrl = () => LOGIN;

  function topRight() {
    const p = Auth.profile();
    return (S.notice ? '<span role="status" class="notice">' + esc(S.notice) + "</span>" : "") +
      '<button class="avatar" aria-label="Profile" aria-haspopup="menu" aria-expanded="' + S.menu + '" data-act="app.menu">' + UI.icon("user", 22) + "</button>" +
      (S.menu
        ? '<div class="menu" role="menu" aria-label="Profile"><div><small>Name</small><strong>' + esc(p.name) + "</strong></div>" +
          "<div><small>Designation</small><b>" + esc(p.designation) + "</b></div>" +
          '<button class="btn btn-outline btn-small" role="menuitem" data-act="app.password">Change password</button>' +
          '<button class="btn btn-small" role="menuitem" style="color:var(--danger);border-color:#e7b9a0" data-act="app.logout">Logout</button></div>'
        : "");
  }
  const renderTop = () => { const el = $("#top-right"); if (el) el.innerHTML = topRight(); };

  function shell(area) {
    $("#app").innerHTML =
      '<div class="shell"><header class="topbar"><div class="brand">Sales Desk</div><div class="topbar-right" id="top-right">' + topRight() + "</div></header>" +
      '<div class="body"><nav class="sidebar" aria-label="Main">' +
      ORDER.filter((k) => Auth.can(k)).map((k) => '<a class="nav-link' + (k === area ? " active" : "") + '" href="' + PAGES[k] + '"' + (k === area ? ' aria-current="page"' : "") + ">" + UI.icon(k) + "<span>" + LABELS[k] + "</span></a>").join("") +
      '</nav><main class="main" id="view"></main></div></div>';
  }

  async function start(area) {
    if (!Auth.loggedIn()) { location.replace(LOGIN); return; }
    if (!Auth.can(area)) { location.replace(PAGES.daily); return; }
    document.title = LABELS[area] + " \u00B7 Sales Desk";
    shell(area);
    const page = Pages[area];
    S.current = page;
    $("#view").innerHTML = '<p class="muted">Loading\u2026</p>';
    try { await page.load(); } catch (e) { $("#view").innerHTML = '<div role="alert" class="error">' + esc(e.message) + "</div>"; return; }
    refresh();
  }
  function refresh() { if (S.current) { $("#view").innerHTML = S.current.html(); if (S.current.after) S.current.after(); } }

  window.App = { start, refresh, renderTop, notice: (m) => { S.notice = m; renderTop(); } };

  A["app.menu"] = () => { S.menu = !S.menu; S.notice = ""; renderTop(); };
  A["app.logout"] = async () => { await Auth.logout(); location.href = LOGIN; };
  A["app.password"] = () => { S.menu = false; renderTop(); Modals.changePassword(() => App.notice("Password changed.")); };
  A["modal.close"] = () => UI.modal.close();

  document.addEventListener("click", (e) => {
    const el = e.target.closest("[data-act]");
    if (el && A[el.dataset.act]) { e.preventDefault(); A[el.dataset.act](el, e); }
  });
  document.addEventListener("input", (e) => { const el = e.target.closest("[data-in]"); if (el && I[el.dataset.in]) I[el.dataset.in](el, e); });
  document.addEventListener("change", (e) => { const el = e.target.closest("[data-ch]"); if (el && C[el.dataset.ch]) C[el.dataset.ch](el, e); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && UI.modal.isOpen()) UI.modal.close(); });
})();
