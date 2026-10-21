// Modals shared by several pages.
(function () {
  const { $, num } = U;

  window.Modals = {
    addCustomer(o) {
      o = o || {};
      const initial = o.initial || "";
      const digits = initial.replace(/\D/g, "");
      const looksPhone = digits.length >= 6 && digits.length >= initial.length - 3;
      UI.modal.open("Add Customer",
        UI.field("Customer Name", "ac-name", { value: looksPhone ? "" : initial }) +
        UI.field("Phone number", "ac-phone", { type: "tel", value: looksPhone ? initial : "" }) +
        UI.msg("m-err") +
        '<div class="modal-actions"><button class="btn" data-act="modal.close">Close</button><button class="btn btn-primary" data-act="ac.save">Add</button></div>');
      A["ac.save"] = async () => {
        const name = $("#ac-name").value.trim();
        if (!name) return UI.say("m-err", "Enter the customer name.");
        try {
          const c = await Api.call("/api/customers/", { method: "POST", body: { name, phone: $("#ac-phone").value.trim(), ledger: o.ledger } });
          o.onAdded(c);
        } catch (e) { UI.say("m-err", e.message); }
      };
    },

    changePassword(onDone) {
      UI.modal.open("Change password",
        UI.field("Current password", "pw-cur", { type: "password", attrs: 'autocomplete="current-password"' }) +
        UI.field("New Password", "pw-new", { type: "password", attrs: 'autocomplete="new-password"' }) +
        UI.field("Confirm password", "pw-conf", { type: "password", attrs: 'autocomplete="new-password"' }) +
        UI.msg("m-err") +
        '<div class="modal-actions"><button class="btn" data-act="modal.close">Cancel</button><button class="btn btn-primary" data-act="pw.save">Save</button></div>');
      A["pw.save"] = async () => {
        const f = { current_password: $("#pw-cur").value, new_password: $("#pw-new").value, confirm_password: $("#pw-conf").value };
        if (!f.current_password || !f.new_password || !f.confirm_password) return UI.say("m-err", "Fill in all three fields.");
        try { await Auth.changePassword(f); UI.modal.close(); onDone(); }
        catch (e) { UI.say("m-err", e.message); }
      };
    },
  };
  A["modal.close"] = () => UI.modal.close();
})();
