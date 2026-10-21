// Company Payment: Details, Bill Amount and Company List tabs, with Add Company, Pay and View modals.
Pages.company = (function () {
  const { $, esc, num, money, dmy, time12 } = U;
  const TABS = [["details", "Company Payment Details"], ["bill", "Bill Amount"], ["list", "Company List"]];
  const st = { tab: "details", q: "", shown: [], all: [], summary: null, notice: "", bill: "", paid: "", companyId: "" };

  const loadShown = async () => { st.shown = Api.rows(await Api.call("/api/companies/?search=" + encodeURIComponent(st.q.trim()) + "&page_size=500")); };
  async function load() {
    const r = await Promise.all([loadShown(), Api.call("/api/companies/?page_size=500"), Api.call("/api/companies/summary/")]);
    st.all = Api.rows(r[1]); st.summary = r[2];
  }
  const refresh = async () => { await load(); App.refresh(); };

  const rowsHtml = () => st.shown.length ? st.shown.map((c) =>
    '<tr><td class="strong">' + esc(c.name) + "</td><td>" + money(c.bill_total) + "</td><td>" + money(c.paid_total) + '</td><td class="strong ' + (num(c.due) > 0 ? "due-text" : "ok") + '">' + money(c.due) + "</td>" +
    '<td><div class="actions"><button class="btn btn-small" data-act="co.view" data-id="' + c.id + '">View</button><button class="btn btn-small btn-primary" data-act="co.pay" data-id="' + c.id + '"' + (num(c.due) <= 0 ? " disabled" : "") + ">Pay</button></div></td></tr>").join("") : UI.emptyRow(5);

  const dueAmt = () => Math.max(num(st.bill) - num(st.paid), 0);

  function tabBody() {
    if (st.tab === "details") {
      return '<div class="row" style="align-items:flex-end;justify-content:space-between"><div style="flex:1 1 320px">' + UI.searchBox("Search", "co-q", "Search By company", st.q, 'data-in="co.search"') + "</div>" +
        '<div class="stat warn"><small>Total due remaining</small><b>' + money(st.summary && st.summary.total_due) + "</b></div></div>" +
        '<section class="card" aria-label="Company payment details"><h2>Company Payment details</h2><div class="table-wrap"><table class="table"><thead><tr><th>Company Name</th><th>Bill Amount</th><th>Paid Amount</th><th>Due</th><th>Action</th></tr></thead><tbody id="co-body">' + rowsHtml() + "</tbody></table></div></section>";
    }
    if (st.tab === "bill") {
      return '<section class="card stack" aria-label="Bill amount" style="max-width:560px"><h2 style="margin:0">Bill Amount</h2>' +
        UI.select("Company Name", "co-company", [["", "Select company"]].concat(st.all.map((c) => [c.id, c.name])), st.companyId, 'data-ch="co.select"') +
        UI.moneyField("Bill Amount", "co-bill", st.bill, 'data-in="co.bill"') + UI.moneyField("Paid Amount", "co-paid", st.paid, 'data-in="co.paid"') +
        '<div class="field"><span style="font-weight:600">Due Amount</span><div class="readonly" id="co-due">' + money(dueAmt()) + "</div></div>" + UI.msg("co-err") +
        '<div class="modal-actions"><button class="btn btn-primary" data-act="co.bill.save">Save</button></div></section>';
    }
    return '<section class="card" aria-label="Company list"><h2>Company List</h2><div class="table-wrap"><table class="table"><thead><tr><th>Company Name</th><th>Due</th></tr></thead><tbody>' +
      (st.all.length ? st.all.map((c) => '<tr><td class="strong">' + esc(c.name) + '</td><td class="' + (num(c.due) > 0 ? "due-text" : "") + '">' + money(c.due) + "</td></tr>").join("") : UI.emptyRow(2)) + "</tbody></table></div></section>";
  }

  function html() {
    return '<div class="page-head"><h1>Company Payment</h1><div class="row"><button class="btn btn-outline" data-act="co.add">Add Company</button><button class="btn btn-primary" data-act="co.tab" data-key="bill">Bill Amount</button></div></div>' +
      UI.tabs(TABS, st.tab, "co.tab", "Company payment") + '<div role="status" class="ok">' + esc(st.notice) + "</div>" + tabBody();
  }

  const byId = (id) => st.all.filter((c) => c.id === Number(id))[0];
  A["co.tab"] = (el) => { st.tab = el.dataset.key; App.refresh(); };
  I["co.search"] = U.debounce(async (el) => { st.q = el.value; await loadShown(); const b = $("#co-body"); if (b) b.innerHTML = rowsHtml(); }, 250);
  I["co.bill"] = (el) => { st.bill = el.value; $("#co-due").textContent = money(dueAmt()); };
  I["co.paid"] = (el) => { st.paid = el.value; $("#co-due").textContent = money(dueAmt()); };
  C["co.select"] = (el) => { st.companyId = el.value; };

  A["co.bill.save"] = async () => {
    if (!st.companyId) return UI.say("co-err", "Select a company.");
    if (num(st.bill) <= 0) return UI.say("co-err", "Enter the bill amount.");
    try {
      await Api.call("/api/company-entries/", { method: "POST", body: { company: Number(st.companyId), bill_amount: num(st.bill), paid_amount: num(st.paid) } });
      st.notice = "Saved bill."; st.tab = "details"; st.bill = ""; st.paid = ""; st.companyId = ""; await refresh();
    } catch (e) { UI.say("co-err", e.message); }
  };

  A["co.add"] = () => {
    UI.modal.open("Add Company", UI.field("Company Name", "co-name") + UI.msg("m-err") +
      '<div class="modal-actions"><button class="btn" data-act="modal.close">Cancel</button><button class="btn btn-primary" data-act="co.add.save">Save</button></div>');
  };
  A["co.add.save"] = async () => {
    const name = $("#co-name").value.trim();
    if (!name) return UI.say("m-err", "Enter the company name.");
    try { const c = await Api.call("/api/companies/", { method: "POST", body: { name } }); UI.modal.close(); st.tab = "list"; st.notice = "Added company " + c.name + "."; await refresh(); }
    catch (e) { UI.say("m-err", e.message); }
  };

  A["co.pay"] = (el) => {
    const c = byId(el.dataset.id) || st.shown.filter((x) => x.id === Number(el.dataset.id))[0];
    UI.modal.open("Pay company", "<div>Company Name: <b>" + esc(c.name) + '</b></div><div class="row" style="justify-content:space-between;padding:10px 14px;background:var(--danger-soft);border-radius:10px"><span>Due Amount</span><b class="due-text">' + money(c.due) + "</b></div>" +
      UI.moneyField("Paid Amount", "co-pay-amt", "") + UI.msg("m-err") +
      '<div class="modal-actions"><button class="btn" data-act="modal.close">Cancel</button><button class="btn btn-primary" data-act="co.pay.save" data-id="' + c.id + '">Save</button></div>');
  };
  A["co.pay.save"] = async (el) => {
    const c = byId(el.dataset.id), amount = num($("#co-pay-amt").value);
    try { await Api.call("/api/companies/" + c.id + "/pay/", { method: "POST", body: { amount } }); UI.modal.close(); st.notice = "Paid " + money(amount) + " to " + c.name + "."; await refresh(); }
    catch (e) { UI.say("m-err", e.message); }
  };

  A["co.view"] = async (el) => {
    const c = byId(el.dataset.id);
    try {
      const d = await Api.call("/api/companies/" + c.id + "/history/");
      UI.modal.open("Company payment history", '<div class="row" style="justify-content:space-between"><span>Company Name: <b>' + esc(c.name) + "</b></span><span>Remaining Due: <b class=\"due-text\">" + money(d.remaining_due) + "</b></span></div>" +
        '<div class="table-wrap"><table class="table"><thead><tr><th>Date</th><th>Bill Amount</th><th>Paid Amount</th><th>Remaining</th></tr></thead><tbody>' +
        (d.rows.length ? d.rows.map((r) => "<tr><td>" + dmy(r.date) + ' <span class="muted">' + time12(r.date) + "</span></td><td>" + money(r.bill_amount) + "</td><td>" + money(r.paid_amount) + '</td><td class="strong">' + money(r.remaining) + "</td></tr>").join("") : UI.emptyRow(4)) +
        '</tbody></table></div><div class="modal-actions"><button class="btn btn-primary" data-act="modal.close">Close</button></div>', true);
    } catch (e) { st.notice = e.message; App.refresh(); }
  };

  return { load, html };
})();
