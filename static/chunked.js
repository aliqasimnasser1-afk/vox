/* Chunked upload for the video splitter: big files are sent in 16 MB pieces so no host's request-size
   limit (e.g. a 413 "Request Entity Too Large") can block them. Runs before the generic upload handler. */
(function () {
  var form = document.getElementById('split-form');
  if (!form) return;

  function csrf() { return form.querySelector('[name=csrfmiddlewaretoken]').value; }

  function overlay() {
    var box = document.createElement('div');
    box.className = 'upload-overlay';
    box.setAttribute('role', 'status');
    box.innerHTML = '<div class="upload-card"><div class="upload-title"><span class="spin"></span><strong>جارٍ رفع الفيديو…</strong><span class="upload-pct">0%</span></div>' +
      '<div class="progress"><span style="width:0%"></span></div>' +
      '<p class="muted small-txt upload-note">لا تغلق الصفحة حتى يكتمل الرفع.</p>' +
      '<button type="button" class="btn ghost small upload-cancel">إلغاء</button></div>';
    document.body.appendChild(box);
    return {
      el: box,
      set: function (v) { box.querySelector('.progress span').style.width = v + '%'; box.querySelector('.upload-pct').textContent = v + '%'; },
      note: function (t) { box.querySelector('.upload-note').textContent = t; },
      cancel: box.querySelector('.upload-cancel'),
      close: function () { box.remove(); }
    };
  }

  function post(url, fd, onProgress, signal) {
    return new Promise(function (resolve, reject) {
      var xhr = new XMLHttpRequest();
      xhr.open('POST', url);
      xhr.setRequestHeader('X-CSRFToken', csrf());
      xhr.responseType = 'json';
      if (onProgress) xhr.upload.onprogress = function (e) { if (e.lengthComputable) onProgress(e.loaded); };
      xhr.onload = function () {
        var body = xhr.response || {};
        if (xhr.status >= 200 && xhr.status < 300) resolve(body);
        else reject(new Error(body.error || (xhr.status === 413 ? 'حجم الجزء أكبر مما يسمح به الخادم.' : 'خطأ في الرفع (' + xhr.status + ').')));
      };
      xhr.onerror = function () { reject(new Error('انقطع الاتصال.')); };
      xhr.onabort = function () { reject(new Error('أُلغي الرفع.')); };
      if (signal) signal.abort = function () { xhr.abort(); };
      xhr.send(fd);
    });
  }

  async function sendChunk(url, id, index, blob, onBytes, signal) {
    for (var attempt = 1; ; attempt++) {
      try {
        var fd = new FormData();
        fd.append('id', id); fd.append('index', index); fd.append('chunk', blob, 'chunk');
        return await post(url, fd, onBytes, signal);
      } catch (e) {
        if (signal.cancelled || attempt >= 3 || /ألغي|أُلغي/.test(e.message)) throw e;
        await new Promise(function (r) { setTimeout(r, 800 * attempt); });  // brief pause, then retry this chunk only
      }
    }
  }

  // capture phase: run before the generic XHR upload handler and take over for big files
  form.addEventListener('submit', async function (e) {
    var input = form.querySelector('input[type=file]');
    var file = input && input.files[0];
    if (!file || file.size < parseInt(form.dataset.chunkMin || '0', 10)) return; // small file: normal upload
    e.preventDefault();
    e.stopImmediatePropagation();
    if (form.dataset.sending) return;
    form.dataset.sending = '1';

    var ui = overlay(), signal = { cancelled: false, abort: null }, uploadId = null;
    function warn(ev) { ev.preventDefault(); ev.returnValue = ''; }
    window.addEventListener('beforeunload', warn);
    function done() { window.removeEventListener('beforeunload', warn); ui.close(); delete form.dataset.sending; }
    ui.cancel.addEventListener('click', function () { signal.cancelled = true; if (signal.abort) signal.abort(); });

    try {
      var init = new FormData();
      init.append('name', file.name); init.append('size', file.size);
      var meta = await post(form.dataset.chunkInit, init);
      uploadId = meta.id;
      var size = meta.chunk_size, total = meta.chunks, sent = 0;
      for (var i = 0; i < total; i++) {
        if (signal.cancelled) throw new Error('أُلغي الرفع.');
        var blob = file.slice(i * size, Math.min(file.size, (i + 1) * size));
        await sendChunk(form.dataset.chunkUrl, uploadId, i, blob, function (loaded) {
          ui.set(Math.min(99, Math.round((sent + loaded) / file.size * 100)));
        }, signal);
        sent += blob.size;
        ui.set(Math.min(99, Math.round(sent / file.size * 100)));
      }
      ui.set(100); ui.note('اكتمل الرفع، جارٍ تجميع الملف وبدء التقسيم…');
      var fin = new FormData(form);   // amount, unit, mode (+ csrf)
      fin.delete('video'); fin.set('id', uploadId);
      var res = await post(form.dataset.chunkFinish, fin);
      window.removeEventListener('beforeunload', warn);
      location.href = res.redirect;
    } catch (err) {
      if (uploadId) { var ab = new FormData(); ab.append('id', uploadId); post(form.dataset.chunkAbort, ab).catch(function () {}); }
      done();
      alert(err.message || 'تعذّر الرفع. حاول مرة أخرى.');
    }
  }, true);
})();
