// Day Closing: count cash by note and coin; the day closes only when the count matches the closing balance.
Pages.closing = (function () {
  const { $, num, money, esc } = U;
  const st = { data: null, qty: {}, msg: "", msgType: "" };

  async function load() {
    st.data = await Api.call("/api/day-closing/");
    st.qty = {};
    st.data.counts.forEach((c) => { st.qty[c.value] = c.quantity ? String(c.quantity) : ""; });
    st.msg = ""; st.msgType = "";
  }
  const lines = () => st.data.counts.map((c) => ({ value: c.value, quantity: parseInt(st.qty[c.value] || "0", 10) || 0 }));
  const total = () => lines().reduce((a, l) => a + num(l.value) * l.quantity, 0);
  const diff = () => Math.round((total() - num(st.data.closing_balance)) * 100) / 100;

  function diffHtml() {
    if (st.data.closed || total() <= 0) return "";
    return diff() === 0 ? '<div role="status" class="ok">Cash matches.</div>' : '<div role="status" class="error">' + (diff() > 0 ? "Over" : "Short") + " by " + money(Math.abs(diff())) + "</div>";
  }

  function html() {
    const d = st.data;
    return '<div class="page-head"><h1>Day Closing</h1></div><div class="row" style="align-items:flex-start;gap:24px"><div class="stat"><small>Opening Balance</small><b>' + money(d.opening_balance) +
      '</b></div><div class="stat"><small>Closing Balance</small><b>' + money(d.closing_balance) + "</b></div></div>" +
      '<p class="muted" style="max-width:640px">Closing = Opening + Cash + MFS + Card + Due received + Whole Sale received \u2212 Refund \u2212 Company payments. Credit sales (Due and Whole Sale) are not cash, so they are not counted until paid.</p>' +
      '<section class="card" aria-label="Count cash"><h2>Count cash by note and coin</h2><div class="table-wrap"><table class="table"><thead><tr><th>Note / Coin</th><th>Quantity</th><th>Total</th></tr></thead><tbody>' +
      lines().map((l, i) => '<tr><td class="strong">' + money(l.value) + '</td><td><input class="input" style="width:120px" inputmode="numeric" aria-label="Quantity of ' + l.value + '" data-in="dc.qty" data-v="' + l.value + '" data-i="' + i + '"' +
        (d.closed ? " disabled" : "") + ' value="' + esc(st.qty[l.value] || "") + '"></td><td id="dc-row-' + i + '">' + money(num(l.value) * l.quantity) + "</td></tr>").join("") +
      '</tbody></table></div><div class="sum-total" style="margin-top:12px"><span>Day End total</span><span id="dc-total">' + money(d.closed ? d.counted_total : total()) + '</span></div>' +
      '<div id="dc-diff" style="margin-top:8px">' + diffHtml() + '</div><div class="row" style="margin-top:16px"><button class="btn btn-primary" data-act="dc.close"' + (d.closed ? " disabled" : "") + ">Close day</button>" +
      (d.closed ? '<span class="ok">This day is closed.</span>' : "") + '</div><div id="dc-msg" role="status" class="' + st.msgType + '" style="margin-top:8px">' + esc(st.msg) + "</div></section>";
  }

  I["dc.qty"] = (el) => {
    el.value = el.value.replace(/\D/g, ""); st.qty[el.dataset.v] = el.value; st.msg = "";
    const l = lines()[Number(el.dataset.i)];
    $("#dc-row-" + el.dataset.i).textContent = money(num(l.value) * l.quantity);
    $("#dc-total").textContent = money(total());
    $("#dc-diff").innerHTML = diffHtml(); $("#dc-msg").textContent = "";
  };
  A["dc.close"] = async () => {
    try {
      await Api.call("/api/day-closing/", { method: "POST", body: { counts: lines() } });
      await load(); st.msg = "Day closed. Today's totals are locked in the report."; st.msgType = "ok"; App.refresh();
    } catch (e) { st.msg = e.message; st.msgType = "error"; $("#dc-msg").className = "error"; $("#dc-msg").textContent = e.message; }
  };

  return { load, html };
})();
