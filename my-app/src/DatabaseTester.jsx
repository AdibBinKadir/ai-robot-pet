import { useState, useEffect } from 'react'
import { supabase } from './dbconnect'

function DatabaseTester() {
  const [tables, setTables] = useState({
    photos: [],
    user_profiles: []
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [user, setUser] = useState(null)

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ?? null)
      if (session?.user) {
        loadAllData()
      }
    })
  }, [])

  const loadAllData = async () => {
    setLoading(true)
    setError('')
    
    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) {
        setError('Not authenticated')
        return
      }

      console.log('🔍 Loading data from Supabase tables...')

      // Load photos
      try {
        const { data: photosData, error: photosError } = await supabase
          .from('photos')
          .select('*')
          .eq('user_id', session.user.id)
          .order('upload_time', { ascending: false })
          .limit(10)

        if (photosError) throw photosError
        setTables(prev => ({ ...prev, photos: photosData || [] }))
        console.log('✅ Photos loaded:', photosData?.length || 0)
      } catch (err) {
        console.log('⚠️ Photos table error:', err.message)
      }



      // Load user profiles
      try {
        const { data: profilesData, error: profilesError } = await supabase
          .from('user_profiles')
          .select('*')
          .eq('user_id', session.user.id)

        if (profilesError) throw profilesError
        setTables(prev => ({ ...prev, user_profiles: profilesData || [] }))
        console.log('✅ User profiles loaded:', profilesData?.length || 0)
      } catch (err) {
        console.log('⚠️ User profiles table error:', err.message)
      }



    } catch (error) {
      console.error('❌ Database loading error:', error)
      setError(error.message)
    } finally {
      setLoading(false)
    }
  }

  const testDirectInsert = async () => {
    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) {
        alert('Please login first')
        return
      }

      // Test inserting a user profile update
      const testProfile = {
        user_id: session.user.id,
        display_name: 'Test User',
        robot_name: 'Test Robot Pet',
        total_commands: 1
      }

      const { data, error } = await supabase
        .from('user_profiles')
        .upsert(testProfile)
        .select()

      if (error) throw error

      console.log('✅ Profile upsert successful:', data)
      alert('✅ User profile test successful!')
      loadAllData() // Reload to show new data
    } catch (error) {
      console.error('❌ Direct insert failed:', error)
      alert(`❌ Direct insert failed: ${error.message}`)
    }
  }

  const clearUserData = async () => {
    if (!confirm('Are you sure you want to clear all your data? This cannot be undone.')) {
      return
    }

    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) return

      // Clear user photos only
      await supabase.from('photos').delete().eq('user_id', session.user.id)

      alert('✅ Your photo data cleared')
      loadAllData()
    } catch (error) {
      alert(`❌ Clear failed: ${error.message}`)
    }
  }

  if (!user) {
    return (
      <div style={{ padding: '20px', border: '1px solid #ddd', borderRadius: '8px', margin: '20px 0' }}>
        <h3>🗄️ Database Tester</h3>
        <p>Please login to test database functionality</p>
      </div>
    )
  }

  return (
    <div style={{ padding: '20px', border: '1px solid #ddd', borderRadius: '8px', margin: '20px 0' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h3>🗄️ Database Tester</h3>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button 
            onClick={loadAllData}
            disabled={loading}
            style={{ padding: '8px 16px', backgroundColor: '#007bff', color: 'white', border: 'none', borderRadius: '4px' }}
          >
            {loading ? 'Loading...' : '🔄 Refresh All'}
          </button>
          <button 
            onClick={testDirectInsert}
            style={{ padding: '8px 16px', backgroundColor: '#28a745', color: 'white', border: 'none', borderRadius: '4px' }}
          >
            🧪 Test Insert
          </button>
          <button 
            onClick={clearUserData}
            style={{ padding: '8px 16px', backgroundColor: '#dc3545', color: 'white', border: 'none', borderRadius: '4px' }}
          >
            🗑️ Clear Data
          </button>
        </div>
      </div>

      {error && (
        <div style={{ padding: '10px', backgroundColor: '#f8d7da', border: '1px solid #f5c6cb', borderRadius: '4px', marginBottom: '20px', color: '#721c24' }}>
          ❌ Error: {error}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
        
        {/* Photos Table */}
        <div>
          <h4>📸 Photos ({tables.photos.length})</h4>
          <div style={{ maxHeight: '200px', overflowY: 'auto', fontSize: '12px', backgroundColor: '#f8f9fa', padding: '10px', borderRadius: '4px' }}>
            {tables.photos.length > 0 ? (
              tables.photos.map((photo, idx) => (
                <div key={photo.id || idx} style={{ marginBottom: '8px', paddingBottom: '8px', borderBottom: '1px solid #ddd' }}>
                  <div><strong>ID:</strong> {photo.id}</div>
                  <div><strong>Filename:</strong> {photo.filename}</div>
                  <div><strong>URL:</strong> <a href={photo.url} target="_blank" rel="noopener noreferrer">View</a></div>
                  <div><strong>Size:</strong> {photo.file_size ? `${photo.file_size} bytes` : 'N/A'}</div>
                  <div><strong>Uploaded:</strong> {new Date(photo.upload_time).toLocaleString()}</div>
                </div>
              ))
            ) : (
              <p style={{ color: '#6c757d' }}>No photos uploaded yet</p>
            )}
          </div>
        </div>



        {/* User Profiles Table */}
        <div>
          <h4>👤 User Profile ({tables.user_profiles.length})</h4>
          <div style={{ maxHeight: '200px', overflowY: 'auto', fontSize: '12px', backgroundColor: '#f8f9fa', padding: '10px', borderRadius: '4px' }}>
            {tables.user_profiles.length > 0 ? (
              tables.user_profiles.map((profile, idx) => (
                <div key={profile.id || idx} style={{ marginBottom: '8px', paddingBottom: '8px', borderBottom: '1px solid #ddd' }}>
                  <div><strong>Display Name:</strong> {profile.display_name || 'N/A'}</div>
                  <div><strong>Robot Name:</strong> {profile.robot_name}</div>
                  <div><strong>Total Commands:</strong> {profile.total_commands}</div>
                  <div><strong>Created:</strong> {new Date(profile.created_at).toLocaleString()}</div>
                </div>
              ))
            ) : (
              <p style={{ color: '#6c757d' }}>No profile created yet</p>
            )}
          </div>
        </div>


      </div>

      {/* Database Connection Info */}
      <div style={{ marginTop: '20px', padding: '15px', backgroundColor: '#e9ecef', borderRadius: '4px' }}>
        <h4>📊 Database Connection Info</h4>
        <div style={{ fontSize: '12px' }}>
          <p><strong>Supabase URL:</strong> https://proavqhzzoljnoeomddd.supabase.co</p>
          <p><strong>User ID:</strong> {user.id}</p>
          <p><strong>User Email:</strong> {user.email}</p>
          <p><strong>Tables:</strong> photos, user_profiles</p>
          <p><strong>Status:</strong> <span style={{ color: 'green' }}>✅ Connected</span></p>
        </div>
      </div>
    </div>
  )
}

export default DatabaseTester