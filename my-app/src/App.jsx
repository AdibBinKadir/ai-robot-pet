import { BrowserRouter as Router, Route, Routes, Navigate } from 'react-router-dom';
import { Auth } from '@supabase/auth-ui-react';
import { ThemeSupa } from '@supabase/auth-ui-shared';
import { supabase } from './dbconnect';
import { useEffect, useState } from 'react';
import Login from './login';
import Verification from './verification';

function App() {
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

  return (
    <Router>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/verification"
          element={
            session ? <Verification session={session} /> : <Navigate to="/login" />
          }
        />
        <Route
          path="/"
          element={
            session ? <Navigate to="/verification" /> : <Navigate to="/login" />
          }
        />
        <Route
          path="/microphone"
          element={
            session ? <Navigate to="/microphone" /> : <Navigate to="/login" />
          }
        />
        <Route
          path="*"
          element={<Navigate to={session ? "/verification" : "/login"} />}
        />
      </Routes>
    </Router>
  );
}

export default App;