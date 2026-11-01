import { useState } from 'react';
import { supabase } from '../lib/supabase.js';

const MAX = 280;

export default function Composer({ me, onPosted }) {
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const left = MAX - text.length;
  const empty = text.trim().length === 0;

  async function post(e) {
    e.preventDefault();
    if (empty || left < 0 || !me) return;
    setBusy(true); setError('');
    const { error } = await supabase.from('posts').insert({ content: text.trim(), user_id: me.id });
    setBusy(false);
    if (error) { setError('تعذّر النشر. حاول مرة أخرى.'); return; }
    setText('');
    onPosted?.();
  }

  return (
    <form className="composer" onSubmit={post}>
      <label className="sr" htmlFor="composer-text">اكتب تغريدة</label>
      <textarea id="composer-text" value={text} onChange={(e) => setText(e.target.value)}
        placeholder="وش الجديد؟" rows={3} />
      {error && <div className="error" role="alert">{error}</div>}
      <div className="composer-bar">
        <span className={left < 0 ? 'count over' : left < 20 ? 'count warn' : 'count'}
          aria-live="polite">{left}</span>
        <button className="btn primary" disabled={busy || empty || left < 0 || !me}>نشر</button>
      </div>
    </form>
  );
}
