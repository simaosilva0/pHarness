"""The light and dark switch of the page. The choice is kept in this browser; with
none, the page follows the system. Colors are the page's variables, so the
whole page changes, the diagram too."""

KEY = "pharness-theme"

# In the head, so the page never flashes the wrong theme.
THEME_RESTORE = """
try {
  var saved = localStorage.getItem("%s");
  if (saved === "light" || saved === "dark") document.documentElement.setAttribute("data-theme", saved);
} catch (e) { /* no memory here: follow the system */ }
""" % KEY

THEME_BUTTON = """
(function () {
  var root = document.documentElement;
  var button = document.getElementById("theme");
  if (!button) return;
  function current() {
    return root.getAttribute("data-theme") ||
      (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  }
  function label() {
    button.textContent = current() === "dark" ? "Light mode" : "Dark mode";
  }
  button.addEventListener("click", function () {
    var next = current() === "dark" ? "light" : "dark";
    root.setAttribute("data-theme", next);
    try { localStorage.setItem("%s", next); } catch (e) { /* not kept */ }
    label();
  });
  label();
})();
""" % KEY
