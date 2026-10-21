(function () {
  // Role matrix (matches the backend): owner everything; manager all but Settings; cashier sales and dues.
  const ACCESS = {
    owner: ["daily", "due", "wholesale", "company", "closing", "report", "settings"],
    manager: ["daily", "due", "wholesale", "company", "closing", "report"],
    cashier: ["daily", "due", "wholesale"],
  };
  let profile = null;
  try { profile = JSON.parse(localStorage.getItem("profile")); } catch (e) {}

  window.Auth = {
    profile: () => profile,
    loggedIn: () => Boolean(profile && Api.token()),
    can: (area) => (ACCESS[profile && profile.role] || []).indexOf(area) >= 0,
    async login(name, password) {
      const d = await Api.call("/api/auth/login/", { method: "POST", body: { name, password } });
      Api.setToken(d.token);
      localStorage.setItem("profile", JSON.stringify(d.profile));
      profile = d.profile;
    },
    async logout() {
      try { await Api.call("/api/auth/logout/", { method: "POST" }); } catch (e) {}
      Auth.clear();
    },
    clear() { Api.setToken(null); localStorage.removeItem("profile"); profile = null; },
    async changePassword(body) {
      const d = await Api.call("/api/auth/change-password/", { method: "POST", body });
      Api.setToken(d.token); // the old token stops working after a change
    },
  };
  window.addEventListener("auth:expired", () => { Auth.clear(); location.replace((Auth.loginUrl && Auth.loginUrl()) || "/login/"); });
})();
