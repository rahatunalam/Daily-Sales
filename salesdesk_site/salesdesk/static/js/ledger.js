// Shared by the Due and Whole Sale features: customers, what they owe, View history and Pay.
(function () {
  const { $, esc, num, money, dmy, time12 } = U;
  const LABELS = {
    due: { title: "Due", cardReceived: "Due received", cardRemaining: "Total due remaining", sale: "Due amount", received: "Due received", due: "Remaining",
      history: "Due history", histSale: "Due amount", histPaid: "Due paid", histDue: "Remaining" },
    wholesale: { title: "Whole Sale", cardReceived: "Received", cardRemaining: "Total due", sale: "Sale Amount", received: "Received Amount", due: "Due",
      history: "Whole Sale history", histSale: "Sale amount", histPaid: "Received", histDue: "Due" },
  };
  const all = {};

  function make(ledger) {
    const L = LABELS[ledger];
    const st = { list: [], cards: null, q: "", notice: "", error: "" };
    all[ledger] = st;
    st.ledger = ledger;

    st.reloadList = async () => {
      st.list = Api.rows(await Api.call("/api/customers/?scope=ledger&ledger=" + ledger + "&search=" + encodeURIComponent(st.q.trim()) + "&page_size=500"));
    };
    st.reloadCards = async () => { st.cards = await Api.call("/api/customers/due-summary/?ledger=" + ledger); };
    st.load = async () => { await Promise.all([st.reloadList(), st.reloadCards()]); };

    st.rowsHtml = () => st.list.length ? st.list.map((c) => {
      const rem = num(c.remaining);
      return "<tr><td><b>" + esc(c.name) + '</b><div class="muted">' + esc(c.phone) + "</div></td><td>" + money(c.due_total) + "</td><td>" + money(c.received_total) + "</td>" +
        '<td class="strong' + (rem > 0 ? " due-text" : "") + '">' + money(c.remaining) + "</td>" +
        '<td><div class="actions"><button class="btn btn-small" data-act="led.view" data-led="' + ledger + '" data-id="' + c.id + '">View</button>' +
        '<button class="btn btn-small btn-primary" data-act="led.pay" data-led="' + ledger + '" data-id="' + c.id + '"' + (rem <= 0 ? " disabled" : "") + ">Pay</button></div></td></tr>";
    }).join("") : UI.emptyRow(5);

    st.html = () =>
      '<div class="page-head"><h1>' + L.title + '</h1><button class="btn btn-primary" data-act="led.add" data-led="' + ledger + '">Add Customer</button></div>' +
      '<div class="row" style="align-items:flex-end"><div style="flex:1 1 320px">' + UI.searchBox("Search by name / phone", "led-q-" + ledger, "Type a name or phone number", st.q, 'data-in="led.search" data-led="' + ledger + '"') + "</div>" +
      '<div class="stat"><small>' + L.cardReceived + "</small><b>" + money(st.cards && st.cards.total_received) + "</b></div>" +
      '<div class="stat warn"><small>' + L.cardRemaining + "</small><b>" + money(st.cards && st.cards.total_remaining) + "</b></div></div>" +
      '<div id="led-notice" role="status" class="ok">' + esc(st.notice) + "</div>" +
      '<section class="card"><div class="table-wrap"><table class="table"><thead><tr><th>Customer / Phone</th><th>' + L.sale + "</th><th>" + L.received + "</th><th>" + L.due +
      '</th><th>Action</th></tr></thead><tbody id="led-body-' + ledger + '">' + st.rowsHtml() + "</tbody></table></div></section>";

    st.refresh = async () => { await st.load(); App.refresh(); };
    return st;
  }

  window.Ledger = { make };
  const L = (el) => all[el.dataset.led];
  const customer = (st, id) => st.list.filter((c) => c.id === Number(id))[0];

  I["led.search"] = U.debounce(async (el) => {
    const st = L(el); st.q = el.value;
    await st.reloadList();
    const body = $("#led-body-" + st.ledger);
    if (body) body.innerHTML = st.rowsHtml();
  }, 250);

  A["led.add"] = (el) => {
    const st = L(el);
    Modals.addCustomer({ ledger: st.ledger, onAdded: async (c) => { UI.modal.close(); st.notice = "Added customer " + c.name + "."; await st.refresh(); } });
  };

  A["led.view"] = async (el) => {
    const st = L(el), lb = LABELS[st.ledger], c = customer(st, el.dataset.id);
    try {
      const d = await Api.call("/api/customers/" + c.id + "/history/?ledger=" + st.ledger);
      UI.modal.open(lb.history,
        '<div class="row" style="justify-content:space-between"><span>Customer name: <b>' + esc(c.name) + "</b></span><span>Mobile: <b>" + esc(c.phone) + "</b></span></div>" +
        '<div class="table-wrap"><table class="table"><thead><tr><th>Date</th><th>' + lb.histSale + "</th><th>" + lb.histPaid + "</th><th>" + lb.histDue + "</th></tr></thead><tbody>" +
        (d.rows.length ? d.rows.map((r) => "<tr><td>" + dmy(r.date) + ' <span class="muted">' + time12(r.date) + "</span></td><td>" + money(r.due) + "</td><td>" + money(r.paid) + '</td><td class="strong">' + money(r.remaining) + "</td></tr>").join("") : UI.emptyRow(4)) +
        '</tbody></table></div><div class="modal-actions"><button class="btn btn-primary" data-act="modal.close">Close</button></div>', true);
    } catch (e) { st.error = e.message; }
  };

  A["led.pay"] = (el) => {
    const st = L(el), c = customer(st, el.dataset.id);
    UI.modal.open("Receive payment",
      "<div>Customer name: <b>" + esc(c.name) + '</b></div><div class="row" style="justify-content:space-between;padding:10px 14px;background:var(--danger-soft);border-radius:10px"><span>Remaining due</span><b class="due-text">' + money(c.remaining) + "</b></div>" +
      UI.moneyField("Amount receive", "led-pay-amt", String(c.remaining)) + UI.msg("m-err") +
      '<div class="modal-actions"><button class="btn" data-act="modal.close">Cancel</button><button class="btn btn-primary" data-act="led.pay.save" data-led="' + st.ledger + '" data-id="' + c.id + '">Pay</button></div>');
  };
  A["led.pay.save"] = async (el) => {
    const st = L(el), c = customer(st, el.dataset.id), amount = num($("#led-pay-amt").value);
    try {
      await Api.call("/api/customers/" + c.id + "/receive/", { method: "POST", body: { amount, ledger: st.ledger } });
      UI.modal.close(); st.notice = "Received " + money(amount) + " from " + c.name + "."; await st.refresh();
    } catch (e) { UI.say("m-err", e.message); }
  };
})();
