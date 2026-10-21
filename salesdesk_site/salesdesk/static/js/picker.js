// One search box for name or phone. Pick a result, or add a new customer when nothing matches.
(function () {
  const { esc, money, num } = U;
  const all = {};

  function make(id, o) {
    const p = { id, sel: null, q: "", results: [], error: "", adding: false };
    all[id] = p;
    const label = () => (typeof o.label === "function" ? o.label() : o.label);

    p.html = () => '<div id="pk-' + id + '" class="stack">' + inner() + "</div>";
    p.render = () => { const el = U.$("#pk-" + id); if (el) el.innerHTML = inner(); };
    p.reset = () => { p.sel = null; p.q = ""; p.results = []; p.error = ""; };

    function inner() {
      if (p.sel) {
        return '<div class="selected"><div><b>' + esc(p.sel.name) + '</b><div class="muted">' + esc(p.sel.phone) + "</div></div>" +
          '<div class="row">' + (o.hasDue ? '<b class="due-text">' + money(p.sel.remaining) + " due</b>" : "") +
          '<button type="button" class="btn btn-small" data-act="pk.change" data-pk="' + id + '">Change</button></div></div>';
      }
      let h = UI.searchBox(label(), "pks-" + id, "Type a name or phone number", p.q, 'data-in="pk.search" data-pk="' + id + '"');
      if (p.error) h += '<div role="alert" class="error">' + esc(p.error) + "</div>";
      p.results.forEach((c, i) => {
        h += '<button type="button" class="pick" data-act="pk.pick" data-pk="' + id + '" data-i="' + i + '"><span><b>' + esc(c.name) + '</b> <span class="muted">' + esc(c.phone) + "</span></span>" +
          (o.hasDue ? '<b class="due-text">' + money(c.remaining) + " due</b>" : "") + "</button>";
      });
      if (p.q.trim() && !p.results.length) {
        h += '<div class="row"><span class="muted">' + (o.hasDue ? "No customer with a due matches." : "No saved customer matches.") + "</span>" +
          (o.hasDue ? "" : '<button type="button" class="btn btn-small btn-outline" data-act="pk.add" data-pk="' + id + '">Add \u201C' + esc(p.q.trim()) + "\u201D as new customer</button>") + "</div>";
      }
      return h;
    }

    p.search = U.debounce(async () => {
      const q = p.q.trim();
      if (!q) { p.results = []; return p.renderKeepFocus(); }
      try {
        p.results = Api.rows(await Api.call("/api/customers/?search=" + encodeURIComponent(q) + (o.hasDue ? "&has_due=true" : "") + "&page_size=20"));
        p.error = "";
      } catch (e) { p.error = e.message; }
      p.renderKeepFocus();
    }, 250);

    // re-render the results but keep the caret in the search box
    p.renderKeepFocus = () => {
      const box = U.$("#pks-" + id);
      const pos = box ? box.selectionStart : 0;
      p.render();
      const nb = U.$("#pks-" + id);
      if (nb && document.activeElement !== nb && box) { nb.focus(); try { nb.setSelectionRange(pos, pos); } catch (e) {} }
    };
    p.choose = (c) => { p.sel = c; p.q = ""; p.results = []; p.render(); if (o.onChange) o.onChange(c); };
    p.clear = () => { p.sel = null; p.render(); if (o.onChange) o.onChange(null); };
    return p;
  }

  A["pk.pick"] = (el) => { const p = all[el.dataset.pk]; p.choose(p.results[Number(el.dataset.i)]); };
  A["pk.change"] = (el) => all[el.dataset.pk].clear();
  A["pk.add"] = (el) => {
    const p = all[el.dataset.pk];
    Modals.addCustomer({ initial: p.q.trim(), onAdded: (c) => { UI.modal.close(); p.choose(c); } });
  };
  I["pk.search"] = (el) => { const p = all[el.dataset.pk]; p.q = el.value; p.search(); };

  window.Picker = { make };
})();
