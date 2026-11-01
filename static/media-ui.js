/* Styled confirm dialog (replaces window.confirm) and media lightbox (images, videos, avatars). */
(function () {
  // ───────── Confirm dialog ─────────
  var cdlg = document.getElementById('confirm-dialog');
  var cTitle = document.getElementById('cf-title'), cText = document.getElementById('cf-text'), cOk = document.getElementById('cf-ok');
  var cIcon = cdlg && cdlg.querySelector('.dlg-ico');

  function ask(opts) {
    return new Promise(function (resolve) {
      if (!cdlg || !cdlg.showModal) { resolve(window.confirm(opts.text || opts.title || '')); return; }
      cTitle.textContent = opts.title || 'هل أنت متأكد؟';
      cText.textContent = opts.text || '';
      cOk.textContent = opts.ok || 'نعم، احذف';
      var tone = opts.tone || 'danger';
      cOk.className = 'btn ' + (tone === 'danger' ? 'danger' : 'primary');
      cIcon.className = 'dlg-ico ' + tone;
      cdlg.returnValue = '';
      function done() { cdlg.removeEventListener('close', done); resolve(cdlg.returnValue === 'ok'); }
      cdlg.addEventListener('close', done);
      cdlg.showModal();
    });
  }
  function optsFrom(el, fallbackText) {
    var d = el.dataset;
    return { title: d.confirmTitle, text: d.confirmText || fallbackText, ok: d.confirmOk, tone: d.confirmTone };
  }

  // htmx buttons with hx-confirm
  document.addEventListener('htmx:confirm', function (e) {
    if (!e.detail.question) return;
    e.preventDefault();
    ask(optsFrom(e.detail.elt, e.detail.question)).then(function (ok) { if (ok) e.detail.issueRequest(true); });
  });

  // plain forms with data-confirm (capture phase so it runs before other submit handlers)
  document.addEventListener('submit', function (e) {
    var form = e.target;
    if (!form.matches || !form.matches('form[data-confirm]') || form.dataset.confirmed) return;
    e.preventDefault();
    e.stopImmediatePropagation();
    ask(optsFrom(form, form.dataset.confirm)).then(function (ok) {
      if (ok) { form.dataset.confirmed = '1'; form.requestSubmit(); }
    });
  }, true);

  // close dialogs when clicking the dimmed backdrop
  if (cdlg) cdlg.addEventListener('click', function (e) { if (e.target === cdlg) cdlg.close('cancel'); });

  // ───────── Lightbox ─────────
  var lb = document.getElementById('lightbox');
  if (!lb) return;
  var stage = lb.querySelector('.lb-stage'), caption = lb.querySelector('.lb-caption');
  var counter = lb.querySelector('.lb-count'), dl = lb.querySelector('.lb-download');
  var prevBtn = lb.querySelector('.lb-prev'), nextBtn = lb.querySelector('.lb-next');
  var items = [], idx = 0;

  function srcOf(el) { return el.dataset.src || el.getAttribute('href') || el.currentSrc || el.src; }

  function show(i) {
    idx = (i + items.length) % items.length;
    var el = items[idx], kind = el.dataset.lightbox, src = srcOf(el), node;
    stage.innerHTML = '';
    lb.classList.remove('zoomed');
    if (kind === 'video') {
      node = document.createElement('video');
      node.controls = true; node.autoplay = true; node.playsInline = true; node.src = src;
    } else {
      node = document.createElement('img');
      node.alt = ''; node.src = src; node.draggable = false;
      node.addEventListener('click', function (e) { e.stopPropagation(); lb.classList.toggle('zoomed'); });
    }
    stage.appendChild(node);

    var post = el.closest('.post');
    caption.innerHTML = '';
    if (post) {
      var who = post.querySelector('.name'), handle = post.querySelector('.handle'), text = post.querySelector('.content');
      var h = document.createElement('div'); h.className = 'lb-who';
      if (who) { var s = document.createElement('strong'); s.textContent = who.textContent; h.appendChild(s); }
      if (handle) { var m = document.createElement('span'); m.textContent = handle.textContent; m.dir = 'ltr'; h.appendChild(m); }
      caption.appendChild(h);
      if (text) { var p = document.createElement('p'); p.textContent = text.textContent; caption.appendChild(p); }
    }
    counter.textContent = items.length > 1 ? (idx + 1) + ' / ' + items.length : '';
    prevBtn.hidden = nextBtn.hidden = items.length < 2;
    dl.href = src;
    dl.setAttribute('download', src.split('/').pop().split('?')[0] || 'media');
    lb.dataset.kind = kind;
  }

  function open(el) {
    items = Array.prototype.slice.call(document.querySelectorAll('[data-lightbox]'));
    var i = items.indexOf(el);
    if (i < 0) return;
    // pause any inline video that is playing behind the lightbox
    document.querySelectorAll('video').forEach(function (v) { if (!lb.contains(v)) v.pause(); });
    show(i);
    if (!lb.open) lb.showModal();
    document.documentElement.classList.add('no-scroll');
  }

  document.addEventListener('click', function (e) {
    var el = e.target.closest('[data-lightbox]');
    if (!el || lb.contains(el)) return;
    e.preventDefault();
    open(el);
  });
  // avatars on profile pages
  document.addEventListener('click', function (e) {
    var img = e.target.closest('img.avatar.xl');
    if (!img || img.dataset.lightbox) return;
    img.dataset.lightbox = 'image';
    img.dataset.src = img.src;
    open(img);
  });

  // In RTL "next" is on the left.
  prevBtn.addEventListener('click', function (e) { e.stopPropagation(); show(idx - 1); });
  nextBtn.addEventListener('click', function (e) { e.stopPropagation(); show(idx + 1); });
  lb.querySelector('.lb-close').addEventListener('click', function () { lb.close(); });
  lb.addEventListener('click', function (e) {
    if (e.target === lb || e.target === stage) lb.close();
  });
  lb.addEventListener('close', function () {
    stage.innerHTML = ''; // stops video playback
    document.documentElement.classList.remove('no-scroll');
  });
  lb.addEventListener('keydown', function (e) {
    if (items.length < 2) return;
    var rtl = getComputedStyle(document.documentElement).direction === 'rtl';
    if (e.key === 'ArrowLeft') { e.preventDefault(); show(idx + (rtl ? 1 : -1)); }
    if (e.key === 'ArrowRight') { e.preventDefault(); show(idx + (rtl ? -1 : 1)); }
  });
  var tx = null;
  lb.addEventListener('touchstart', function (e) { tx = e.touches[0].clientX; }, { passive: true });
  lb.addEventListener('touchend', function (e) {
    if (tx === null || items.length < 2) return;
    var dx = e.changedTouches[0].clientX - tx; tx = null;
    if (Math.abs(dx) < 60 || lb.classList.contains('zoomed')) return;
    show(idx + (dx < 0 ? 1 : -1)); // swipe left = next (RTL)
  }, { passive: true });
})();
