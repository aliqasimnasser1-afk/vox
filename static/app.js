/* Small progressive-enhancement helpers. Everything works without JS except the theme toggle. */
(function () {
  var root = document.documentElement;

  // Theme toggle: system -> explicit light/dark, remembered in localStorage.
  document.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-theme-toggle]');
    if (!btn) return;
    var dark = root.dataset.theme
      ? root.dataset.theme === 'dark'
      : window.matchMedia('(prefers-color-scheme: dark)').matches;
    var next = dark ? 'light' : 'dark';
    root.dataset.theme = next;
    try { localStorage.setItem('vox-theme', next); } catch (err) {}
  });

  // Toasts: close button and auto-dismiss.
  function dismiss(t) { t.classList.add('out'); setTimeout(function () { t.remove(); }, 250); }
  document.addEventListener('click', function (e) {
    var x = e.target.closest('.toast-x');
    if (x) dismiss(x.closest('.toast'));
  });
  document.querySelectorAll('.toast').forEach(function (t) { setTimeout(function () { dismiss(t); }, 4500); });

  // Password show/hide.
  document.addEventListener('click', function (e) {
    var b = e.target.closest('[data-toggle-password]');
    if (!b) return;
    var input = document.getElementById(b.dataset.togglePassword);
    var show = input.type === 'password';
    input.type = show ? 'text' : 'password';
    b.setAttribute('aria-pressed', show);
    b.classList.toggle('on', show);
  });

  // Drag-and-drop file picker.
  document.querySelectorAll('.dropzone').forEach(function (zone) {
    var input = zone.querySelector('input[type=file]');
    var label = zone.querySelector('[data-file-name]');
    function show() {
      if (input.files.length) {
        var f = input.files[0];
        label.textContent = f.name + ' · ' + (f.size / 1048576).toFixed(1) + ' MB';
        zone.classList.add('has-file');
      }
    }
    input.addEventListener('change', show);
    ['dragenter', 'dragover'].forEach(function (ev) {
      zone.addEventListener(ev, function (e) { e.preventDefault(); zone.classList.add('drag'); });
    });
    ['dragleave', 'drop'].forEach(function (ev) {
      zone.addEventListener(ev, function () { zone.classList.remove('drag'); });
    });
    zone.addEventListener('drop', function (e) {
      e.preventDefault();
      if (e.dataTransfer.files.length) { input.files = e.dataTransfer.files; show(); }
    });
  });
})();
