import { Auth } from '@supabase/auth-ui-react';
import { ThemeSupa } from '@supabase/auth-ui-shared';
import { supabase } from './dbconnect';
import { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';

function Login() {
  const [session, setSession] = useState(null);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
    });

    return () => subscription.unsubscribe();
  }, []);

  // If user is already logged in, redirect to verification
  if (session) {
    return <Navigate to="/verification" replace />;
  }

  return (
    <div style={{ padding: '20px', maxWidth: '400px', margin: '0 auto' }}>
      <h2>Login to Robot Pet</h2>
      <Auth 
        supabaseClient={supabase} 
        appearance={{ theme: ThemeSupa }}
        providers={[]}
      />
      
      <div style={{ marginTop: '20px', fontSize: '12px', color: '#666' }}>
        <p><strong>Debug Info:</strong></p>
        <p>Supabase URL: {import.meta.env.VITE_SUPABASE_URL}</p>
        <p>Current URL: {window.location.href}</p>
        <p>Session: {session ? '✅ Active' : '❌ None'}</p>
      </div>
    </div>
  );
}

export default Login;