import { supabase } from '../lib/supabase.js';
import Logo from './Logo.jsx';

export default function Header({ me }) {
  return (
    <header className="header">
      <a href="#/" className="brand" aria-label="الرئيسية">
        <Logo size={32} /> <span>Vox</span>
      </a>
      <nav>
        {me && <a href={`#/u/${me.username}`} className="navlink">@{me.username}</a>}
        <button className="btn ghost" onClick={() => supabase.auth.signOut()}>خروج</button>
      </nav>
    </header>
  );
}
