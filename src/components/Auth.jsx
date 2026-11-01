import { useState } from 'react';
import { supabase } from '../lib/supabase.js';
import Logo from './Logo.jsx';

export default function Auth() {
  const [mode, setMode] = useState('login');
  const [form, setForm] = useState({ name: '', email: '', password: '' });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    setError(''); setNotice('');
    if (mode === 'signup' && form.password.length < 8) {
      setError('كلمة المرور أقل من 8 أحرف.');
      return;
    }
    setBusy(true);
    try {
      if (mode === 'login') {
        const { error } = await supabase.auth.signInWithPassword({
          email: form.email, password: form.password,
        });
        if (error) throw error;
      } else {
        const { data, error } = await supabase.auth.signUp({
          email: form.email,
          password: form.password,
          options: { data: { name: form.name.trim() } },
        });
        if (error) throw error;
        if (!data.session) setNotice('تم إنشاء الحساب. افتح بريدك وأكّد الحساب ثم سجّل دخولك.');
      }
    } catch (err) {
      setError(translate(err.message));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth">
      <div className="auth-card">
        <Logo size={40} />
        <h1>{mode === 'login' ? 'مرحباً بعودتك' : 'انضم إلى Vox'}</h1>
        <p className="muted">{mode === 'login' ? 'سجّل دخولك للمتابعة.' : 'أنشئ حسابك في أقل من دقيقة.'}</p>

        <form onSubmit={submit} noValidate={false}>
          {mode === 'signup' && (
            <label>الاسم
              <input value={form.name} onChange={set('name')} autoComplete="name" required minLength={2} />
            </label>
          )}
          <label>البريد الإلكتروني
            <input type="email" dir="ltr" value={form.email} onChange={set('email')}
              autoComplete={mode === 'login' ? 'username' : 'email'} required />
          </label>
          <label>كلمة المرور
            <input type="password" dir="ltr" value={form.password} onChange={set('password')}
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'} required />
          </label>
          {error && <div className="error" role="alert">{error}</div>}
          {notice && <div className="notice" role="status">{notice}</div>}
          <button className="btn primary" disabled={busy}>
            {busy ? 'جارٍ المعالجة…' : mode === 'login' ? 'دخول' : 'إنشاء الحساب'}
          </button>
        </form>

        <p className="switch">
          {mode === 'login' ? 'ما عندك حساب؟ ' : 'عندك حساب؟ '}
          <button className="link" type="button"
            onClick={() => { setMode(mode === 'login' ? 'signup' : 'login'); setError(''); setNotice(''); }}>
            {mode === 'login' ? 'أنشئ حساباً' : 'سجّل دخولك'}
          </button>
        </p>
      </div>
    </div>
  );
}

function translate(msg = '') {
  if (/invalid login/i.test(msg)) return 'البريد أو كلمة المرور غير صحيحة.';
  if (/email address .* invalid/i.test(msg)) return 'البريد الإلكتروني غير صالح.';
  if (/already registered/i.test(msg)) return 'هذا البريد مسجّل مسبقاً.';
  if (/email not confirmed/i.test(msg)) return 'أكّد بريدك الإلكتروني أولاً.';
  if (/rate limit/i.test(msg)) return 'محاولات كثيرة. انتظر قليلاً ثم أعد المحاولة.';
  if (/password/i.test(msg)) return 'كلمة المرور ضعيفة أو غير صالحة.';
  return 'حدث خطأ. حاول مرة أخرى.';
}
