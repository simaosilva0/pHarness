"""The theme button of the page: light, solarized light, dark and nord dark. The choice is kept in this browser; with
none, the page follows the system. Colors are the page's variables, so the
whole page changes, the diagram too."""

KEY = "pharness-theme"

# In the head, so the page never flashes the wrong theme.
THEME_RESTORE = """
try {
  var saved = localStorage.getItem("%s");
  if (["light", "solarized", "dark", "nord"].indexOf(saved) >= 0) document.documentElement.setAttribute("data-theme", saved);
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
  var themes = ["light", "solarized", "dark", "nord"];
  var names = { light: "Light", solarized: "Solarized", dark: "Dark", nord: "Nord" };
  function next() { return themes[(themes.indexOf(current()) + 1) %% themes.length]; }
  function label() {
    button.textContent = names[current()] + " theme";
  }
  button.addEventListener("click", function () {
    var chosen = next();
    root.setAttribute("data-theme", chosen);
    try { localStorage.setItem("%s", chosen); } catch (e) { /* not kept */ }
    label();
  });
  label();
})();
""" % KEY
