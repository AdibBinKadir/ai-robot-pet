
import { useState, useEffect } from 'react'
import { BrowserRouter, Route, Routes, Navigate } from 'react-router-dom'
import { supabase } from './dbconnect'
import Login from './login'
import Verification from './verification'
import './App.css'


function App() {
  const [session, setSession] = useState(null)

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session)
    })
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session)
    })
    return () => subscription.unsubscribe()
  }, [])

  return (
    <BrowserRouter>
      <Routes>
        {/* Public Route */}
        <Route path="/login" element={<Login />} />

        {/* After login the user should go to verification */}
        <Route
          path="/verification"
          element={session ? <Verification /> : <Navigate to="/login" replace />}
        />

        {/* Default route */}
        <Route
          path="/"
          element={session ? <Navigate to="/verification" replace /> : <Navigate to="/login" replace />}
        />
      </Routes>
    </BrowserRouter>
  )
}

export default App
