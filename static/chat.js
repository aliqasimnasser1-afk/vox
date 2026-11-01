/* Chat extras: emoji picker, stickers, image attachment preview and error toasts. */
(function () {
  var form = document.getElementById('chat-form');
  if (!form) return;

  var EMOJI = {
    'وجوه': '😀 😃 😄 😁 😆 😅 😂 🤣 🥲 ☺️ 😊 😇 🙂 🙃 😉 😌 😍 🥰 😘 😗 😙 😚 😋 😛 😝 😜 🤪 🤨 🧐 🤓 😎 🥸 🤩 🥳 😏 😒 😞 😔 😟 😕 🙁 ☹️ 😣 😖 😫 😩 🥺 😢 😭 😤 😠 😡 🤬 🤯 😳 🥵 🥶 😱 😨 😰 😥 😓 🤗 🤔 🤭 🤫 😶 😐 😑 😬 🙄 😯 😦 😧 😮 😲 🥱 😴 🤤 😪 😵 🤐 🥴 🤢 🤮 🤧 😷 🤒 🤕',
    'إيماءات': '👍 👎 👌 🤌 🤏 ✌️ 🤞 🤟 🤘 🤙 👈 👉 👆 👇 ☝️ ✋ 🤚 🖐️ 🖖 👋 🤝 🙏 ✍️ 💪 👏 🙌 🫶 👐 🤲 🫡',
    'قلوب': '❤️ 🧡 💛 💚 💙 💜 🖤 🤍 🤎 💔 ❣️ 💕 💞 💓 💗 💖 💘 💝 💟 ✨ ⭐ 🌟 💫 🔥 💥 💯 ✅ ❌ ⚡ 🎉 🎊',
    'طبيعة': '🐶 🐱 🐭 🐹 🐰 🦊 🐻 🐼 🐨 🐯 🦁 🐮 🐷 🐸 🐵 🙈 🙉 🙊 🐔 🐧 🐦 🦆 🦅 🦉 🐺 🐴 🦄 🐝 🦋 🐢 🐍 🐙 🐬 🐳 🦈 🌹 🌸 🌼 🌻 🌴 🌵 🍀 🌙 ☀️ ⛅ 🌈 ❄️',
    'طعام': '🍎 🍌 🍉 🍇 🍓 🍒 🍑 🥭 🍍 🥥 🥑 🍅 🌶️ 🥕 🌽 🥔 🍞 🧀 🍕 🍔 🌭 🍟 🍗 🥩 🍣 🍜 🍰 🎂 🍩 🍪 🍫 🍿 ☕ 🍵 🥤',
    'أنشطة': '⚽ 🏀 🏈 🎾 🎮 🎯 🎲 🎵 🎶 🎤 🎧 🎬 📷 💻 📱 ⌚ 💡 📚 ✏️ 🎁 🏆 🥇 🚗 ✈️ 🚀 🏠'
  };
  var STICKERS = {
    'مشاعر': '😂 🥹 😍 😎 🤩 😭 😡 🥳 🤯 😴 🤗 🙄 😱 🥺 😏 🤔',
    'حب': '❤️ 💖 💘 💝 🌹 😘 🥰 💌 💋 💐 🫶 😻',
    'احتفال': '🎉 🎊 🏆 🔥 💯 👏 🙌 🎁 🥇 🚀 ✨ 🎂',
    'ردود': '👍 👎 👌 🙏 💪 🤝 ✌️ 🫡 👋 🤞 ✅ ❌',
    'حيوانات': '🐱 🐶 🦁 🐼 🦊 🐸 🐧 🦄 🐻 🐰 🐯 🐵'
  };

  var picker = document.getElementById('picker'), body = document.getElementById('picker-body');
  var text = document.getElementById('body'), emojiBtn = document.getElementById('emoji-btn');
  var tab = 'emoji', cat = null;

  function recents() { try { return JSON.parse(localStorage.getItem('vox-emoji-recent') || '[]'); } catch (e) { return []; } }
  function remember(e) {
    var r = recents().filter(function (x) { return x !== e; }); r.unshift(e);
    try { localStorage.setItem('vox-emoji-recent', JSON.stringify(r.slice(0, 24))); } catch (err) {}
  }
  function btn(cls, label, onclick) {
    var b = document.createElement('button'); b.type = 'button'; b.className = cls; b.textContent = label; b.onclick = onclick; return b;
  }

  function insert(e) {
    var s = text.selectionStart == null ? text.value.length : text.selectionStart, en = text.selectionEnd == null ? s : text.selectionEnd;
    text.value = text.value.slice(0, s) + e + text.value.slice(en);
    text.focus(); text.selectionStart = text.selectionEnd = s + e.length;
    text.dispatchEvent(new Event('input', { bubbles: true }));
    remember(e);
  }

  function sendSticker(s) {
    var empty = document.getElementById('chat-empty'); if (empty) empty.remove();
    htmx.ajax('POST', form.dataset.stickerUrl, { target: '#poller', swap: 'beforebegin', values: { sticker: s } });
    setOpen(false);
  }

  function render() {
    body.innerHTML = '';
    var packs = tab === 'emoji' ? EMOJI : STICKERS;
    var names = Object.keys(packs);
    if (!cat || names.indexOf(cat) < 0) cat = names[0];
    var chips = document.createElement('div'); chips.className = 'pack-chips';
    var rec = tab === 'emoji' ? recents() : [];
    if (rec.length) { chips.appendChild(btn('pack' + (cat === '*' ? ' on' : ''), 'الأخيرة', function () { cat = '*'; render(); })); }
    names.forEach(function (n) { chips.appendChild(btn('pack' + (n === cat ? ' on' : ''), n, function () { cat = n; render(); })); });
    body.appendChild(chips);
    var grid = document.createElement('div'); grid.className = 'pgrid ' + tab;
    var list = cat === '*' ? rec : packs[cat].split(' ');
    list.forEach(function (e) {
      grid.appendChild(btn('pitem', e, function () { tab === 'emoji' ? insert(e) : sendSticker(e); }));
    });
    body.appendChild(grid);
  }

  function setOpen(open) {
    picker.hidden = !open; emojiBtn.setAttribute('aria-expanded', open); emojiBtn.classList.toggle('on', open);
    if (open) render();
  }
  emojiBtn.addEventListener('click', function () { setOpen(picker.hidden); });
  document.querySelectorAll('[data-ptab]').forEach(function (b) {
    b.addEventListener('click', function () {
      tab = b.dataset.ptab; cat = null;
      document.querySelectorAll('[data-ptab]').forEach(function (x) { x.classList.toggle('on', x === b); });
      render();
    });
  });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !picker.hidden) setOpen(false); });
  document.addEventListener('click', function (e) {
    if (!picker.hidden && !e.target.closest('#picker') && !e.target.closest('#emoji-btn')) setOpen(false);
  });

  // Image attachment preview
  var file = document.getElementById('chat-image'), prev = document.getElementById('attach-preview');
  var img = document.getElementById('attach-img'), nm = document.getElementById('attach-name');
  function clearFile() { file.value = ''; prev.hidden = true; img.removeAttribute('src'); }
  file.addEventListener('change', function () {
    if (!file.files.length) return clearFile();
    var f = file.files[0];
    img.src = URL.createObjectURL(f); nm.textContent = f.name + ' · ' + (f.size / 1048576).toFixed(1) + ' MB';
    prev.hidden = false; text.focus();
  });
  document.getElementById('attach-x').addEventListener('click', clearFile);
  document.addEventListener('htmx:afterRequest', function (e) { if (e.detail.elt === form && e.detail.xhr.status === 200) clearFile(); });

  // Small toast for server-side chat errors (sent through the HX-Trigger header).
  document.body.addEventListener('chat-error', function (e) {
    var wrap = document.querySelector('.toasts');
    if (!wrap) { wrap = document.createElement('div'); wrap.className = 'toasts'; document.body.appendChild(wrap); }
    var t = document.createElement('div'); t.className = 'toast error'; t.setAttribute('role', 'status');
    t.innerHTML = '<span class="toast-ico"></span><span></span>';
    t.children[1].textContent = (e.detail && e.detail.value) || 'تعذّر الإرسال.';
    wrap.appendChild(t); setTimeout(function () { t.remove(); }, 4500);
  });
})();
