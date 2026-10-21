// Small HTML builders and the modal. Everything returns strings, so pages stay plain.
(function () {
  const { esc, $ } = U;

  const ICONS = {
    daily: "M6 2L4 6v14a2 2 0 002 2h12a2 2 0 002-2V6l-2-4z M4 6h16 M16 10a4 4 0 01-8 0",
    due: "M12 7v5l3 2 M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
    wholesale: "M3 7l9-4 9 4v10l-9 4-9-4z M3 7l9 4 9-4 M12 11v10",
    company: "M3 21h18 M5 21V7l7-4 7 4v14 M9 9h2 M13 9h2 M9 13h2 M13 13h2 M10 21v-4h4v4",
    closing: "M5 11h14v10H5z M8 11V7a4 4 0 018 0v4",
    report: "M4 20V10 M10 20V4 M16 20v-7 M22 20H2",
    settings: "M4 6h10 M18 6h2 M4 12h4 M12 12h8 M4 18h12 M20 18h0 M14 4v4 M8 10v4 M16 16v4",
    user: "M4 21c0-4.4 3.6-7 8-7s8 2.6 8 7 M16 8a4 4 0 11-8 0 4 4 0 018 0z",
    search: "M20 20l-3.5-3.5 M18 11a7 7 0 11-14 0 7 7 0 0114 0z",
    check: "M5 12l5 5 9-10",
  };
  const icon = (name, size) =>
    '<svg aria-hidden="true" width="' + (size || 20) + '" height="' + (size || 20) + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex:none"><path d="' + ICONS[name] + '"/></svg>';

  const UI = {
    icon,
    field(label, id, o) {
      o = o || {};
      return '<div class="field"><label for="' + id + '">' + esc(label) + '</label><input id="' + id + '" class="input" type="' + (o.type || "text") + '" value="' + esc(o.value || "") + '" ' + (o.attrs || "") + "></div>";
    },
    moneyField(label, id, value, attrs) {
      return '<div class="field"><label for="' + id + '">' + esc(label) + '</label><div class="input-money"><span aria-hidden="true" class="muted">\u09F3</span><input id="' + id + '" inputmode="decimal" value="' + esc(value || "") + '" ' + (attrs || "") + "></div></div>";
    },
    searchBox(label, id, placeholder, value, attrs) {
      return '<div class="field"><label for="' + id + '">' + esc(label) + '</label><div class="search-box"><input id="' + id + '" type="search" placeholder="' + esc(placeholder) + '" value="' + esc(value || "") + '" ' + (attrs || "") + ">" + icon("search") + "</div></div>";
    },
    select(label, id, options, value, attrs) {
      return '<div class="field"><label for="' + id + '">' + esc(label) + '</label><select id="' + id + '" class="input" ' + (attrs || "") + ">" +
        options.map((o) => '<option value="' + esc(o[0]) + '"' + (String(o[0]) === String(value) ? " selected" : "") + ">" + esc(o[1]) + "</option>").join("") + "</select></div>";
    },
    tabs(list, active, act, label) {
      return '<div class="tabs" role="tablist" aria-label="' + esc(label) + '">' +
        list.map((t) => '<button type="button" role="tab" class="tab" aria-selected="' + (t[0] === active) + '" data-act="' + act + '" data-key="' + t[0] + '">' + esc(t[1]) + "</button>").join("") + "</div>";
    },
    emptyRow: (cols) => '<tr><td class="empty" colspan="' + cols + '" role="status">No data found</td></tr>',
    sumRow(label, value, o) {
      o = o || {};
      return '<div class="sum-row"><span class="muted">' + esc(label) + '</span><b class="' + (o.neg ? "neg" : o.danger ? "due-text" : "") + '">' + (o.neg ? "\u2212 " : "") + U.money(value) + "</b></div>";
    },
    // an element whose text is set later with UI.say(id, msg)
    msg: (id, cls) => '<div id="' + id + '" role="alert" class="' + (cls || "error") + '"></div>',
    say(id, text) {
      const el = $("#" + id);
      if (el) el.textContent = text || "";
    },
    modal: {
      open(title, body, wide) {
        $("#modal-root").innerHTML =
          '<div class="backdrop"><div class="modal' + (wide ? " wide" : "") + '" role="dialog" aria-modal="true" aria-labelledby="m-title"><h2 id="m-title">' + esc(title) + "</h2>" + body + "</div></div>";
        const first = $("#modal-root input, #modal-root select");
        if (first) first.focus();
      },
      close() { $("#modal-root").innerHTML = ""; },
      isOpen: () => !!$("#modal-root .backdrop"),
    },
  };
  window.UI = UI;
})();
