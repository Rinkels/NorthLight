// Small progressive enhancements. Dependency-free.
document.querySelectorAll(".range-value").forEach(function (s) {
  var i = document.getElementById(s.dataset.for);
  if (i) i.addEventListener("input", function () { s.textContent = i.value; });
});
document.addEventListener("click", function (ev) {
  var btn = ev.target.closest("[data-sample-target]");
  if (!btn) return;
  var nl = document.getElementById(btn.dataset.sampleTarget);
  var why = document.getElementById(btn.dataset.sampleWhyTarget);
  if (nl) { nl.value = btn.dataset.sampleNl; nl.dispatchEvent(new Event("input", { bubbles: true })); }
  if (why) { why.value = btn.dataset.sampleWhy; why.dispatchEvent(new Event("input", { bubbles: true })); }
  var details = btn.closest("details");
  if (details) details.open = false;
  if (nl) nl.focus();
});
