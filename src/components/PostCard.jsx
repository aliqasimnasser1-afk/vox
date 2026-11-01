import { supabase } from '../lib/supabase.js';

function ago(iso) {
  const s = Math.max(1, Math.floor((Date.now() - new Date(iso)) / 1000));
  if (s < 60) return 'الآن';
  const m = Math.floor(s / 60); if (m < 60) return `${m} د`;
  const h = Math.floor(m / 60); if (h < 24) return `${h} س`;
  const d = Math.floor(h / 24); if (d < 30) return `${d} ي`;
  return new Date(iso).toLocaleDateString('ar');
}

export default function PostCard({ post, me, onChange }) {
  const likes = post.likes ?? [];
  const liked = !!me && likes.some((l) => l.user_id === me.id);
  const mine = !!me && post.user_id === me.id;
  const author = post.profiles;

  async function toggleLike() {
    if (!me) return;
    const q = liked
      ? supabase.from('likes').delete().eq('post_id', post.id).eq('user_id', me.id)
      : supabase.from('likes').insert({ post_id: post.id, user_id: me.id });
    const { error } = await q;
    if (!error) onChange?.();
  }

  async function remove() {
    if (!window.confirm('حذف هذه التغريدة؟')) return;
    const { error } = await supabase.from('posts').delete().eq('id', post.id);
    if (!error) onChange?.();
  }

  return (
    <article className="post">
      <div className="avatar" aria-hidden="true">{(author?.display_name || '?').slice(0, 1).toUpperCase()}</div>
      <div className="post-body">
        <div className="post-head">
          <a href={`#/u/${author?.username}`} className="name">{author?.display_name}</a>
          <span className="muted handle" dir="ltr">@{author?.username}</span>
          <span className="muted">· {ago(post.created_at)}</span>
        </div>
        <p className="content">{post.content}</p>
        <div className="actions">
          <button className={liked ? 'act liked' : 'act'} onClick={toggleLike}
            aria-pressed={liked} aria-label={liked ? 'إلغاء الإعجاب' : 'إعجاب'}>
            <svg viewBox="0 0 24 24" width="18" height="18" fill={liked ? 'currentColor' : 'none'}
              stroke="currentColor" strokeWidth="2" strokeLinejoin="round">
              <path d="M12 21s-7-4.4-9.3-8.6C1 9 2.8 5 6.5 5c2 0 3.5 1.1 5.5 3.2C14 6.1 15.5 5 17.5 5 21.2 5 23 9 21.3 12.4 19 16.6 12 21 12 21z" />
            </svg>
            <span>{likes.length}</span>
          </button>
          {mine && <button className="act danger" onClick={remove}>حذف</button>}
        </div>
      </div>
    </article>
  );
}
