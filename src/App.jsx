import { useEffect, useState } from 'react';
import { supabase } from './lib/supabase.js';
import { useHashRoute } from './lib/useHashRoute.js';
import Auth from './components/Auth.jsx';
import Header from './components/Header.jsx';
import Home from './components/Home.jsx';
import Profile from './components/Profile.jsx';

export default function App() {
  const [session, setSession] = useState(undefined); // undefined = loading
  const [me, setMe] = useState(null);
  const route = useHashRoute();

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => setSession(data.session));
    const { data: sub } = supabase.auth.onAuthStateChange((_e, s) => setSession(s));
    return () => sub.subscription.unsubscribe();
  }, []);

  const userId = session?.user?.id;
  useEffect(() => {
    if (!userId) { setMe(null); return; }
    supabase.from('profiles').select('*').eq('id', userId).single()
      .then(({ data }) => setMe(data));
  }, [userId]);

  if (session === undefined) return <div className="center muted">جارٍ التحميل…</div>;
  if (!session) return <Auth />;

  const username = route.startsWith('/u/') ? decodeURIComponent(route.slice(3)) : null;

  return (
    <div className="app">
      <Header me={me} />
      <main className="column">
        {username
          ? <Profile username={username} me={me} onMeUpdated={setMe} />
          : <Home me={me} />}
      </main>
    </div>
  );
}
