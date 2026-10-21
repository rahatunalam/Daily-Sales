(function () {
  const pad = (n) => String(n).padStart(2, "0");
  const U = {
    $: (s, r) => (r || document).querySelector(s),
    $$: (s, r) => Array.from((r || document).querySelectorAll(s)),
    esc: (v) => String(v == null ? "" : v).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])),
    num: (v) => Number(String(v == null ? "" : v).replace(/[^0-9.\-]/g, "")) || 0,
    money: (v) => "\u09F3 " + Number(v || 0).toLocaleString("en-IN", { maximumFractionDigits: 2 }),
    todayISO() {
      const d = new Date();
      return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate());
    },
    // 20/10/26
    dmy(v) {
      const d = new Date(String(v).length === 10 ? v + "T00:00:00" : v);
      return pad(d.getDate()) + "/" + pad(d.getMonth() + 1) + "/" + String(d.getFullYear()).slice(2);
    },
    // 11:00 AM
    time12(v) {
      const d = new Date(v);
      return pad(d.getHours() % 12 || 12) + ":" + pad(d.getMinutes()) + " " + (d.getHours() >= 12 ? "PM" : "AM");
    },
    methodLabel: (m) => ({ CASH: "Cash", MFS: "MFS", CARD: "Card", DUE: "Due", DUE_RECEIVED: "Due received", REFUND: "Refund", WHOLESALE: "Whole Sale", WHOLESALE_RECEIVED: "Whole Sale received" }[m] || m),
    debounce(fn, ms) {
      let t;
      return function () {
        const a = arguments;
        clearTimeout(t);
        t = setTimeout(() => fn.apply(null, a), ms || 250);
      };
    },
  };
  window.U = U;
  window.A = {}; // click actions:  <button data-act="name">
  window.I = {}; // input actions:  <input data-in="name">
  window.C = {}; // change actions: <select data-ch="name">
  window.Pages = {};
})();
