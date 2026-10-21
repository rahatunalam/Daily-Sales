// Settings: Add MFS, Add User and Money Setting tabs (owner only).
Pages.settings = (function () {
  const { $, esc, money } = U;
  const TABS = [["mfs", "Add MFS"], ["user", "Add User"], ["money", "Money Setting"]];
  const ROLES = [["owner", "Owner"], ["manager", "Manager"], ["cashier", "Cashier"]];
  const st = { tab: "mfs", mfs: [], users: [], dens: [], mfsEdit: null, userEdit: null };

  async function load() {
    const r = await Promise.all([Api.call("/api/mfs-accounts/"), Api.call("/api/users/?page_size=200"), Api.call("/api/denominations/")]);
    st.mfs = Api.rows(r[0]); st.users = Api.rows(r[1]); st.dens = Api.rows(r[2]);
  }
  const refresh = async () => { await load(); App.refresh(); };
  const btns = (save, editing, cancel) => '<button class="btn btn-primary" data-act="' + save + '">' + (editing ? "Update" : "Save") + "</button>" + (editing ? '<button class="btn" data-act="' + cancel + '">Cancel</button>' : "");

  function mfsTab() {
    const e = st.mfs.filter((m) => m.id === st.mfsEdit)[0] || { name: "", account: "" };
    return '<section class="card stack"><div class="row" style="align-items:flex-end">' + UI.field("MFS Name", "st-mfs-name", { value: e.name }) + UI.field("MFS Account", "st-mfs-acc", { value: e.account }) +
      btns("st.mfs.save", st.mfsEdit, "st.mfs.cancel") + "</div>" + UI.msg("st-err") +
      '<div class="table-wrap"><table class="table"><thead><tr><th>Name</th><th>Account</th><th>Action</th></tr></thead><tbody>' +
      (st.mfs.length ? st.mfs.map((m) => '<tr><td class="strong">' + esc(m.name) + "</td><td>" + esc(m.account) + '</td><td><button class="btn btn-small" data-act="st.mfs.edit" data-id="' + m.id + '">Edit</button></td></tr>').join("") : UI.emptyRow(3)) + "</tbody></table></div></section>";
  }

  function userTab() {
    const e = st.users.filter((u) => u.id === st.userEdit)[0] || { name: "", role: "cashier", designation: "" };
    return '<section class="card stack"><div class="row" style="align-items:flex-end">' + UI.field("Name", "st-u-name", { value: e.name }) + UI.select("Role", "st-u-role", ROLES, e.role) +
      UI.field("Designation", "st-u-desig", { value: e.designation, attrs: 'placeholder="e.g. Sales Man"' }) +
      UI.field(st.userEdit ? "New password (optional)" : "Password", "st-u-pass", { type: "password", attrs: 'autocomplete="new-password"' }) + btns("st.user.save", st.userEdit, "st.user.cancel") + "</div>" + UI.msg("st-err") +
      '<div class="table-wrap"><table class="table"><thead><tr><th>Role</th><th>Name</th><th>Designation</th><th>Status</th><th>Action</th></tr></thead><tbody>' +
      (st.users.length ? st.users.map((u) => "<tr><td>" + esc((ROLES.filter((r) => r[0] === u.role)[0] || [])[1]) + '</td><td class="strong">' + esc(u.name) + "</td><td>" + esc(u.designation) + '</td><td><span class="pill' + (u.is_active ? "" : " due") + '">' + (u.is_active ? "Active" : "Inactive") +
        '</span></td><td><div class="actions"><button class="btn btn-small" data-act="st.user.edit" data-id="' + u.id + '">Edit</button><button class="btn btn-small" data-act="st.user.toggle" data-id="' + u.id + '">' + (u.is_active ? "Deactivate" : "Activate") + "</button></div></td></tr>").join("") : UI.emptyRow(5)) + "</tbody></table></div></section>";
  }

  function moneyTab() {
    return '<section class="card stack" style="max-width:520px"><div class="row" style="align-items:flex-end">' + UI.field("Notes / Coins", "st-den", { attrs: 'inputmode="decimal"' }) + '<button class="btn btn-primary" data-act="st.den.add">Add</button></div>' + UI.msg("st-err") +
      '<table class="table"><thead><tr><th>Notes / Coins</th><th>Action</th></tr></thead><tbody>' +
      (st.dens.length ? st.dens.map((d) => '<tr><td class="strong">' + money(d.value) + '</td><td><button class="btn btn-small" style="color:var(--danger)" data-act="st.den.del" data-id="' + d.id + '">Delete</button></td></tr>').join("") : UI.emptyRow(2)) + "</tbody></table></section>";
  }

  function html() {
    return '<div class="page-head"><h1>Settings</h1></div>' + UI.tabs(TABS, st.tab, "st.tab", "Settings") + (st.tab === "mfs" ? mfsTab() : st.tab === "user" ? userTab() : moneyTab());
  }
  const run = async (fn) => { try { await fn(); await refresh(); } catch (e) { UI.say("st-err", e.message); } };

  A["st.tab"] = (el) => { st.tab = el.dataset.key; st.mfsEdit = null; st.userEdit = null; App.refresh(); };
  A["st.mfs.edit"] = (el) => { st.mfsEdit = Number(el.dataset.id); App.refresh(); };
  A["st.mfs.cancel"] = () => { st.mfsEdit = null; App.refresh(); };
  A["st.mfs.save"] = () => {
    const name = $("#st-mfs-name").value.trim();
    if (!name) return UI.say("st-err", "Enter the MFS name.");
    run(async () => { await Api.call(st.mfsEdit ? "/api/mfs-accounts/" + st.mfsEdit + "/" : "/api/mfs-accounts/", { method: st.mfsEdit ? "PATCH" : "POST", body: { name, account: $("#st-mfs-acc").value.trim() } }); st.mfsEdit = null; });
  };

  A["st.user.edit"] = (el) => { st.userEdit = Number(el.dataset.id); App.refresh(); };
  A["st.user.cancel"] = () => { st.userEdit = null; App.refresh(); };
  A["st.user.save"] = () => {
    const body = { name: $("#st-u-name").value.trim(), role: $("#st-u-role").value, designation: $("#st-u-desig").value.trim(), password: $("#st-u-pass").value };
    if (!body.name) return UI.say("st-err", "Enter the name.");
    if (!st.userEdit && !body.password) return UI.say("st-err", "Enter a password.");
    run(async () => { await Api.call(st.userEdit ? "/api/users/" + st.userEdit + "/" : "/api/users/", { method: st.userEdit ? "PATCH" : "POST", body }); st.userEdit = null; });
  };
  A["st.user.toggle"] = (el) => run(() => Api.call("/api/users/" + el.dataset.id + "/toggle-active/", { method: "POST" }));

  A["st.den.add"] = () => run(() => Api.call("/api/denominations/", { method: "POST", body: { value: $("#st-den").value.replace(/[^0-9.]/g, "") } }));
  A["st.den.del"] = (el) => run(() => Api.call("/api/denominations/" + el.dataset.id + "/", { method: "DELETE" }));

  return { load, html };
})();
