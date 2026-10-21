// Report: one row per day, with a Details modal (Sales and Due, Company Payment details).
Pages.report = (function () {
  const { $, esc, money, dmy, todayISO } = U;
  const st = { preset: "today", from: todayISO(), to: todayISO(), data: null };
  const query = () => (st.preset ? "preset=" + st.preset : "from=" + st.from + "&to=" + st.to);

  async function load() { st.data = await Api.call("/api/reports/daily/?" + query()); }
  const refresh = async () => { await load(); App.refresh(); };

  function html() {
    const rows = st.data.rows;
    return '<div class="page-head"><h1>Report</h1></div><div class="row" style="justify-content:space-between;align-items:flex-end"><div class="row">' +
      [["today", "Today"], ["yesterday", "Yesterday"], ["last7", "Last 7 days"]].map((p) => '<button class="chip" aria-pressed="' + (st.preset === p[0]) + '" data-act="rp.preset" data-k="' + p[0] + '">' + p[1] + "</button>").join("") + "</div>" +
      '<div class="row"><div class="field" style="flex:none"><label for="rp-from">From</label><input id="rp-from" class="input" type="date" value="' + st.from + '" data-ch="rp.range"></div>' +
      '<div class="field" style="flex:none"><label for="rp-to">To</label><input id="rp-to" class="input" type="date" value="' + st.to + '" data-ch="rp.range"></div></div></div>' +
      '<section class="card" aria-label="Daily report"><div class="table-wrap"><table class="table"><thead><tr><th>Date / Day</th><th>Opening balance</th><th>Sales received</th><th>Due receive</th><th>Whole Sale received</th><th>Refund</th><th>Company paid</th><th>Closing balance</th><th>Credit given</th><th>Action</th></tr></thead><tbody>' +
      (rows.length ? rows.map((r, i) => '<tr><td class="strong">' + dmy(r.date) + " \u00B7 " + r.day + "</td><td>" + money(r.opening_balance) + "</td><td>" + money(r.sales_received) + "</td><td>" + money(r.due_receive) + "</td><td>" + money(r.whole_sale_received) +
        "</td><td>" + money(r.refund) + "</td><td>" + money(r.company_paid) + '</td><td class="strong">' + money(r.closing_balance) + '</td><td class="due-text">' + money(r.due) + '</td><td><button class="btn btn-small" data-act="rp.details" data-i="' + i + '">Details</button></td></tr>').join("") : UI.emptyRow(10)) +
      '</tbody></table></div><p class="muted-p">Closing balance = Opening balance + Sales received (Cash, MFS, Card) + Due receive + Whole Sale received \u2212 Refund \u2212 Company paid. Credit given (Due and Whole Sale sold on credit) is not cash, so it is not in the closing balance.</p></section>';
  }

  A["rp.preset"] = (el) => { st.preset = el.dataset.k; refresh(); };
  C["rp.range"] = () => { st.from = $("#rp-from").value; st.to = $("#rp-to").value; st.preset = ""; refresh(); };

  A["rp.details"] = async (el) => {
    const r = st.data.rows[Number(el.dataset.i)];
    try {
      const d = await Api.call("/api/reports/daily/details/?date=" + r.date);
      const sd = d.sales_and_due;
      UI.modal.open("Report", '<div style="font-size:18px">Date: <b>' + dmy(r.date) + " \u00B7 " + r.day + "</b></div>" +
        '<section class="box" aria-label="Sales and Due"><h3 style="font-size:16px;margin-bottom:4px">Sales and Due</h3><b>Daily Sales</b>' +
        sd.rows.map((x) => UI.sumRow(x.label, x.amount, { danger: x.label === "Due", neg: x.label === "Refund" })).join("") +
        '<div class="sum-total"><span>Total sales with due</span><span>' + money(sd.total_sales_with_due) + '</span></div><div class="sum-total"><span>Total sales without due</span><span>' + money(sd.total_sales_without_due) + "</span></div></section>" +
        '<section class="box" aria-label="Company Payment details"><h3 style="font-size:16px;margin-bottom:8px">Company Payment details</h3><table class="table"><thead><tr><th>Company Name</th><th>Paid Amount</th></tr></thead><tbody>' +
        (d.company_payments.length ? d.company_payments.map((c) => '<tr><td class="strong">' + esc(c.company_name) + "</td><td>" + money(c.paid_amount) + "</td></tr>").join("") : UI.emptyRow(2)) +
        '</tbody></table></section><div class="modal-actions"><button class="btn btn-primary" data-act="modal.close">Close</button></div>', true);
    } catch (e) { alert(e.message); }
  };

  return { load, html };
})();
