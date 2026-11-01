import PostCard from './PostCard.jsx';

export default function Feed({ posts, error, me, onChange, empty = 'لا توجد تغريدات بعد. كن أول من ينشر!' }) {
  if (error) return <div className="error">{error}</div>;
  if (!posts) return <div className="muted pad">جارٍ التحميل…</div>;
  if (posts.length === 0) return <div className="muted pad">{empty}</div>;
  return (
    <section aria-label="التغريدات">
      {posts.map((p) => <PostCard key={p.id} post={p} me={me} onChange={onChange} />)}
    </section>
  );
}
