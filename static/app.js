/* Small progressive-enhancement helpers. Everything works without JS except the theme toggle and upload progress. */
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

  // Upload progress: any <form data-upload> with a chosen file is sent with XHR so the user sees a progress bar.
  document.addEventListener('submit', function (e) {
    var form = e.target;
    if (!form.matches('form[data-upload]')) return;
    var hasFile = Array.prototype.some.call(form.querySelectorAll('input[type=file]'), function (i) { return i.files.length; });
    if (!hasFile || form.dataset.sending) return; // no file: normal submit
    e.preventDefault();
    form.dataset.sending = '1';

    var box = document.createElement('div');
    box.className = 'upload-overlay';
    box.setAttribute('role', 'status');
    box.innerHTML = '<div class="upload-card"><div class="upload-title"><span class="spin"></span><strong>جارٍ الرفع…</strong><span class="upload-pct">0%</span></div>' +
      '<div class="progress"><span style="width:0%"></span></div><p class="muted small-txt upload-note">لا تغلق الصفحة حتى يكتمل الرفع.</p></div>';
    document.body.appendChild(box);
    var bar = box.querySelector('.progress span'), pct = box.querySelector('.upload-pct'), note = box.querySelector('.upload-note');
    function warn(ev) { ev.preventDefault(); ev.returnValue = ''; }
    window.addEventListener('beforeunload', warn);

    var xhr = new XMLHttpRequest();
    xhr.open((form.method || 'POST').toUpperCase(), form.action || location.href);
    xhr.upload.onprogress = function (p) {
      if (!p.lengthComputable) return;
      var v = Math.round(p.loaded / p.total * 100);
      bar.style.width = v + '%'; pct.textContent = v + '%';
      if (v >= 100) note.textContent = 'اكتمل الرفع، جارٍ المعالجة…';
    };
    function fail() {
      window.removeEventListener('beforeunload', warn);
      box.remove(); delete form.dataset.sending;
      alert('تعذّر الرفع. تحقّق من الاتصال وحاول مرة أخرى.');
    }
    xhr.onerror = fail;
    xhr.onload = function () {
      window.removeEventListener('beforeunload', warn);
      var landed = xhr.responseURL || location.href;
      var sameForm = landed.split('#')[0] === (form.action || location.href).split('#')[0];
      if (xhr.status >= 500) return fail();
      if (!sameForm) { location.href = landed; return; }
      document.open(); document.write(xhr.responseText); document.close(); // validation errors: show the re-rendered form
    };
    xhr.send(new FormData(form));
  });

  // Chat: reset the form after a successful htmx send, keep the newest message in view.
  document.addEventListener('htmx:afterRequest', function (e) {
    var f = e.detail.elt;
    if (f.matches && f.matches('form[data-reset-on-success]') && e.detail.successful) {
      f.reset();
      var t = f.querySelector('textarea');
      if (t) { t.style.height = ''; t.focus(); }
      var em = document.getElementById('chat-empty');
      if (em) em.remove();
    }
  });
  function toBottom() { if (document.getElementById('msgs')) window.scrollTo({ top: document.body.scrollHeight }); }
  document.addEventListener('htmx:afterSwap', function (e) {
    if (e.target && e.target.closest && e.target.closest('#msgs')) toBottom();
  });
  window.addEventListener('load', toBottom);

  // Enter sends, Shift+Enter makes a new line; the box grows with its text.
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.shiftKey && e.target.matches('.chat-form textarea')) {
      e.preventDefault();
      if (e.target.value.trim()) e.target.form.requestSubmit();
    }
  });
  document.addEventListener('input', function (e) {
    if (e.target.matches('.chat-form textarea')) {
      e.target.style.height = 'auto';
      e.target.style.height = Math.min(e.target.scrollHeight, 140) + 'px';
    }
  });

  // Mobile "more" sheet.
  var sheet = document.getElementById('more-sheet'), back = document.querySelector('.sheet-backdrop');
  function sheetOpen(open) {
    if (!sheet) return;
    sheet.hidden = !open; back.hidden = !open;
    var b = document.querySelector('[data-sheet-toggle]');
    if (b) b.setAttribute('aria-expanded', open);
  }
  document.addEventListener('click', function (e) {
    if (e.target.closest('[data-sheet-toggle]')) sheetOpen(sheet.hidden);
    else if (e.target.closest('[data-sheet-close]')) sheetOpen(false);
  });
})();
