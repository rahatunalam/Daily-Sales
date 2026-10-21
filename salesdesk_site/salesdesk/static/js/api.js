// Small fetch wrapper for the Django API. Errors carry the server's {detail} message.
(function () {
  const token = () => localStorage.getItem("token");

  async function call(path, opts) {
    const { method = "GET", body } = opts || {};
    if (window.CONFIG.DEMO) return window.mockApi(path, { method, body });
    const headers = { "Content-Type": "application/json" };
    if (token()) headers.Authorization = "Token " + token();
    let res;
    try {
      res = await fetch((window.CONFIG.API_URL || "") + path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
    } catch (e) {
      throw new Error("Cannot reach the server. Check that the backend is running.");
    }
    if (res.status === 401 && token()) window.dispatchEvent(new Event("auth:expired"));
    const data = res.status === 204 ? null : await res.json().catch(() => null);
    if (!res.ok) {
      const fallback = res.status >= 500
        ? "The server returned an error (" + res.status + "). Check that the backend is running and the database is migrated."
        : "Request failed (" + res.status + ").";
      const err = new Error((data && data.detail) || fallback);
      err.status = res.status;
      throw err;
    }
    return data;
  }

  // Lists may be paginated ({results}); most screens just want the rows.
  const rows = (d) => (Array.isArray(d) ? d : (d && d.results) || []);

  window.Api = { call, rows, token, setToken: (t) => (t ? localStorage.setItem("token", t) : localStorage.removeItem("token")) };
})();
