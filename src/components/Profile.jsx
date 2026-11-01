import { useEffect, useState } from 'react';
import { supabase } from '../lib/supabase.js';
import { usePosts } from '../lib/usePosts.js';
import Feed from './Feed.jsx';

export default function Profile({ username, me, onMeUpdated }) {
  const [profile, setProfile] = useState(undefined); // undefined = loading, null = not found
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState({ display_name: '', bio: '' });
  const [error, setError] = useState('');

  useEffect(() => {
    setProfile(undefined);
    supabase.from('profiles').select('*').eq('username', username).maybeSingle()
      .then(({ data }) => setProfile(data));
  }, [username]);

  const { posts, error: postsError, reload } = usePosts(profile?.id);

  if (profile === undefined) return <div className="muted pad">جارٍ التحميل…</div>;
  if (profile === null) return <div className="pad">لا يوجد مستخدم بهذا الاسم. <a href="#/">الرئيسية</a></div>;

  const mine = me?.id === profile.id;

  function startEdit() {
    setDraft({ display_name: profile.display_name, bio: profile.bio });
    setError('');
    setEditing(true);
  }

  async function save(e) {
    e.preventDefault();
    const display_name = draft.display_name.trim();
    if (display_name.length < 1) { setError('الاسم مطلوب.'); return; }
    const { data, error } = await supabase.from('profiles')
      .update({ display_name, bio: draft.bio.trim() }).eq('id', profile.id).select().single();
    if (error) { setError('تعذّر الحفظ.'); return; }
    setProfile(data); onMeUpdated?.(data); setEditing(false);
  }

  return (
    <>
      <section className="profile">
        <div className="avatar big" aria-hidden="true">{profile.display_name.slice(0, 1).toUpperCase()}</div>
        {editing ? (
          <form onSubmit={save} className="edit">
            <label>الاسم
              <input value={draft.display_name} maxLength={40}
                onChange={(e) => setDraft({ ...draft, display_name: e.target.value })} />
            </label>
            <label>النبذة
              <textarea rows={3} maxLength={160} value={draft.bio}
                onChange={(e) => setDraft({ ...draft, bio: e.target.value })} />
            </label>
            {error && <div className="error" role="alert">{error}</div>}
            <div className="row">
              <button className="btn primary">حفظ</button>
              <button type="button" className="btn ghost" onClick={() => setEditing(false)}>إلغاء</button>
            </div>
          </form>
        ) : (
          <>
            <h1>{profile.display_name}</h1>
            <div className="muted" dir="ltr">@{profile.username}</div>
            {profile.bio && <p>{profile.bio}</p>}
            {mine && <button className="btn ghost" onClick={startEdit}>تعديل الملف</button>}
          </>
        )}
      </section>
      <Feed posts={posts} error={postsError} me={me} onChange={reload} empty="لم ينشر شيئاً بعد." />
    </>
  );
}
