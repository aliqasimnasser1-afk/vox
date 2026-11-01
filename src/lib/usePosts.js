import { useCallback, useEffect, useRef, useState } from 'react';
import { supabase } from './supabase.js';

const SELECT = 'id, content, created_at, user_id, profiles(username, display_name), likes(user_id)';

// Loads the latest posts (optionally only one author's) and refreshes on realtime changes.
export function usePosts(authorId) {
  const [posts, setPosts] = useState(null);
  const [error, setError] = useState('');
  const timer = useRef();

  const load = useCallback(async () => {
    let q = supabase.from('posts').select(SELECT).order('created_at', { ascending: false }).limit(50);
    if (authorId) q = q.eq('user_id', authorId);
    const { data, error } = await q;
    if (error) setError('تعذّر تحميل التغريدات.');
    else { setError(''); setPosts(data); }
  }, [authorId]);

  useEffect(() => {
    setPosts(null);
    load();
    const refresh = () => { clearTimeout(timer.current); timer.current = setTimeout(load, 250); };
    const ch = supabase.channel(`posts-${authorId || 'all'}-${Math.random().toString(36).slice(2)}`)
      .on('postgres_changes', { event: '*', schema: 'public', table: 'posts' }, refresh)
      .on('postgres_changes', { event: '*', schema: 'public', table: 'likes' }, refresh)
      .subscribe();
    return () => { clearTimeout(timer.current); supabase.removeChannel(ch); };
  }, [load, authorId]);

  return { posts, error, reload: load };
}
