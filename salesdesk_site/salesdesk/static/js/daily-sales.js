// Daily Sales: opening balance, new entry, Due Receive, summary and today's transactions.
Pages.daily = (function () {
  const { $, esc, num, money, dmy, time12, methodLabel } = U;
  const METHODS = [["CASH", "Cash"], ["MFS", "MFS"], ["CARD", "Card"], ["REFUND", "Refund"], ["DUE", "Due"], ["WHOLESALE", "Whole Sale"]];
  const st = { summary: null, txs: [], opening: null, wallets: [], method: "CASH", walletId: null, amount: "", paid: "", ob: "", obSaved: false,
    obErr: "", notice: "", error: "", dueOpen: false, dueErr: "", dueAmount: "" };

  const entryPicker = Picker.make("entry", { label: () => "Search customer by name or phone number" + (st.method === "REFUND" ? " (optional)" : "") });
  const duePicker = Picker.make("due", {
    label: "Search customer by name or phone number", hasDue: true,
    onChange: (c) => { st.dueAmount = c ? String(c.remaining) : ""; st.dueErr = ""; renderDue(); },
  });

  async function reload() {
    const today = U.todayISO();
    const r = await Promise.all([
      Api.call("/api/daily-summary/?date=" + today),
      Api.call("/api/transactions/?date=" + today + "&page_size=200"),
      Api.call("/api/opening-balance/?date=" + today),
    ]);
    st.summary = r[0]; st.txs = Api.rows(r[1]); st.opening = r[2];
  }
  async function load() { await reload(); st.wallets = Api.rows(await Api.call("/api/mfs-accounts/")); }

  const isWs = () => st.method === "WHOLESALE";
  const needsCustomer = () => ["REFUND", "DUE", "WHOLESALE"].indexOf(st.method) >= 0;
  const wsDue = () => Math.max(num(st.amount) - num(st.paid), 0);
  const walletId = () => st.walletId || (st.wallets[0] && st.wallets[0].id);

  function entryInner() {
    let h = '<h2 style="margin:0">New entry</h2><div class="row" role="group" aria-label="Payment method">' +
      METHODS.map((m) => '<button class="chip" aria-pressed="' + (st.method === m[0]) + '" data-act="ds.method" data-k="' + m[0] + '">' + m[1] + "</button>").join("") + "</div>";
    if (st.method === "MFS") {
      h += '<div class="row" role="group" aria-label="Mobile wallet"><b>Wallet</b>' +
        st.wallets.map((w) => '<button class="chip" aria-pressed="' + (walletId() === w.id) + '" data-act="ds.wallet" data-id="' + w.id + '">' + esc(w.name) + "</button>").join("") + "</div>";
    }
    if (needsCustomer()) h += entryPicker.html();
    h += '<div class="row" style="align-items:flex-end">' + UI.moneyField(isWs() ? "Bill Amount" : "Amount", "ds-amount", st.amount, 'data-in="ds.amount"');
    if (isWs()) {
      h += UI.moneyField("Paid Amount", "ds-paid", st.paid, 'data-in="ds.paid"') +
        '<div class="field"><span style="font-weight:600">Due amount</span><div class="readonly" id="ds-due-amt">' + money(wsDue()) + "</div></div>";
    }
    h += '<button class="btn btn-primary" data-act="ds.save">Save</button></div>';
    h += '<div id="ds-err" role="alert" class="error">' + esc(st.error) + "</div>";
    h += '<div id="ds-notice" role="status" class="ok">' + esc(st.notice) + "</div>";
    h += '<div class="stack" style="border-top:1px solid var(--line-soft);padding-top:20px;align-items:flex-start"><b>Collect an old due</b>' +
      '<button class="btn btn-due" aria-expanded="' + st.dueOpen + '" data-act="ds.due.toggle">Due Receive</button><div id="ds-due" style="align-self:stretch">' + dueInner() + "</div></div>";
    return h;
  }

  function dueInner() {
    if (!st.dueOpen) return "";
    return '<div class="stack box" style="background:#fdf6f0;border-color:#e7b9a0">' + duePicker.html() +
      (duePicker.sel ? '<div class="row" style="align-items:flex-end">' + UI.moneyField("Receive amount", "ds-due-amount", st.dueAmount, 'data-in="ds.due.amount"') + '<button class="btn btn-primary" data-act="ds.due.save">Save</button></div>' : "") +
      '<div role="alert" class="error">' + esc(st.dueErr) + "</div></div>";
  }
  const renderEntry = () => { const el = $("#ds-entry"); if (el) el.innerHTML = entryInner(); };
  const renderDue = () => { const el = $("#ds-due"); if (el) el.innerHTML = dueInner(); };

  function summaryHtml() {
    const s = st.summary;
    if (!s) return "";
    return "<h2>Daily Sales</h2>" + s.rows.map((r) => UI.sumRow(r.label, r.amount, { danger: r.label === "Due", neg: r.label === "Refund" })).join("") +
      '<div class="sum-total"><span>Total sales with due</span><span>' + money(s.total_sales_with_due) + "</span></div>" +
      '<div class="sum-total"><span>Total sales without due</span><span>' + money(s.total_sales_without_due) + "</span></div>";
  }

  function txRows() {
    if (!st.txs.length) return UI.emptyRow(4);
    return st.txs.map((t) => {
      const cls = t.method === "DUE" ? "due" : t.method === "DUE_RECEIVED" || t.method === "WHOLESALE_RECEIVED" ? "recv" : t.method === "WHOLESALE" ? "ws" : t.method === "REFUND" ? "refund" : "";
      return "<tr><td>" + dmy(t.occurred_at) + ' <span class="muted">' + time12(t.occurred_at) + "</span></td><td>" + esc(t.customer_name || "\u2014") + "</td>" +
        '<td class="strong' + (t.method === "REFUND" ? " neg" : "") + '">' + (t.method === "REFUND" ? "\u2212 " : "") + money(t.amount) + "</td>" +
        '<td><span class="pill ' + cls + '">' + esc(t.method === "MFS" ? t.wallet_name : methodLabel(t.method)) + "</span></td></tr>";
    }).join("");
  }

  function html() {
    const ph = st.opening ? money(st.opening.amount) : "\u09F3 0";
    return '<div class="page-head"><h1>Daily Sales</h1><div class="row"><label for="ds-ob" style="font-weight:600">Opening Balance</label>' +
      '<input id="ds-ob" class="input" style="width:140px" inputmode="decimal" placeholder="' + esc(ph) + '" value="' + esc(st.ob) + '" data-in="ds.ob">' +
      '<button class="btn btn-primary btn-small" aria-label="Confirm opening balance" data-act="ds.ob.save">' + UI.icon("check") + "</button>" +
      (st.obSaved ? '<span class="ok">Set</span>' : "") + "</div></div>" + '<div role="alert" class="error">' + esc(st.obErr) + "</div>" +
      '<div class="grid-2"><section class="card grow2 stack" id="ds-entry" aria-label="New entry">' + entryInner() + "</section>" +
      '<aside class="card grow1" aria-label="Today\'s summary">' + summaryHtml() + "</aside></div>" +
      '<section class="card" aria-label="Transactions"><h2>Transactions</h2><div class="table-wrap"><table class="table"><thead><tr><th>Date</th><th>Customer name</th><th>Amount</th><th>Payment method</th></tr></thead><tbody>' +
      txRows() + "</tbody></table></div></section>";
  }

  async function refreshData() { await reload(); App.refresh(); }

  A["ds.method"] = (el) => { st.method = el.dataset.k; st.paid = ""; st.error = ""; renderEntry(); };
  A["ds.wallet"] = (el) => { st.walletId = Number(el.dataset.id); renderEntry(); };
  I["ds.amount"] = (el) => { st.amount = el.value; st.error = ""; const d = $("#ds-due-amt"); if (d) d.textContent = money(wsDue()); };
  I["ds.paid"] = (el) => { st.paid = el.value; st.error = ""; const d = $("#ds-due-amt"); if (d) d.textContent = money(wsDue()); };
  I["ds.ob"] = (el) => { st.ob = el.value; st.obSaved = false; };
  I["ds.due.amount"] = (el) => { st.dueAmount = el.value; };

  A["ds.ob.save"] = async () => {
    try { await Api.call("/api/opening-balance/", { method: "PUT", body: { amount: num(st.ob) } }); st.obSaved = true; st.obErr = ""; await refreshData(); }
    catch (e) { st.obErr = e.message; App.refresh(); }
  };

  A["ds.save"] = async () => {
    st.notice = "";
    const m = st.method, c = entryPicker.sel;
    const fail = (msg) => { st.error = msg; renderEntry(); };
    if (num(st.amount) <= 0) return fail("Enter an amount first.");
    if (m === "DUE" && !c) return fail("Search and pick the customer for a due sale.");
    if (m === "WHOLESALE" && !c) return fail("Search and pick the customer for a whole sale.");
    if (m === "WHOLESALE" && num(st.paid) > num(st.amount)) return fail("Paid amount cannot be more than the bill amount.");
    if (m === "MFS" && !walletId()) return fail("Add a wallet in Settings first.");
    try {
      await Api.call("/api/transactions/", { method: "POST", body: Object.assign({ method: m, amount: num(st.amount), wallet: m === "MFS" ? walletId() : null, customer: needsCustomer() && c ? c.id : null },
        m === "WHOLESALE" ? { paid_amount: num(st.paid) } : {}) });
      st.notice = m === "WHOLESALE"
        ? "Saved whole sale " + money(st.amount) + ": paid " + money(st.paid || 0) + ", due " + money(wsDue()) + "."
        : "Saved " + money(st.amount) + " as " + methodLabel(m) + ".";
      st.amount = ""; st.paid = ""; st.error = ""; entryPicker.reset();
      await refreshData();
    } catch (e) { fail(e.message); }
  };

  A["ds.due.toggle"] = () => { st.dueOpen = !st.dueOpen; renderDue(); const b = $("[data-act='ds.due.toggle']"); if (b) b.setAttribute("aria-expanded", st.dueOpen); };
  A["ds.due.save"] = async () => {
    const c = duePicker.sel;
    if (!c) { st.dueErr = "Search and pick a customer first."; return renderDue(); }
    try {
      await Api.call("/api/customers/" + c.id + "/receive/", { method: "POST", body: { amount: num(st.dueAmount) } });
      st.notice = "Received " + money(st.dueAmount) + " from " + c.name + ".";
      st.dueOpen = false; st.dueAmount = ""; st.dueErr = ""; duePicker.reset();
      await refreshData();
    } catch (e) { st.dueErr = e.message; renderDue(); }
  };

  return { load, html };
})();
