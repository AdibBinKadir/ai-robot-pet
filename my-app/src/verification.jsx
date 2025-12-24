import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { supabase } from './dbconnect'
import RobotControl from './RobotControl'
import DatabaseTester from './DatabaseTester'
import photo from './assets/photo.svg'
import "./verification.css"
import './App.css'
import './index.css'

function Verification() {
  const navigate = useNavigate()
  const [user, setUser] = useState(null)
  const [selectedFiles, setSelectedFiles] = useState([])
  const [photocount, setPhotocount] = useState(0)
  const [uploading, setUploading] = useState(false)
  const [message, setMessage] = useState('')
  const fileInputRef = useRef(null)

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ?? null)
    })
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null)
    })
    return () => subscription.unsubscribe()
  }, [])

  const handleLogout = async () => {
    await supabase.auth.signOut()
    navigate('/login', { replace: true })
  }

  const handleFileChange = (e) => {
    setMessage('')
    const files = Array.from(e.target.files || [])
    const limited = files.slice(0, 3)
    setSelectedFiles(limited)
    setPhotocount(limited.length)

    // replace input filelist so extras are removed visually
    try {
      const dt = new DataTransfer()
      limited.forEach((f) => dt.items.add(f))
      if (fileInputRef.current) fileInputRef.current.files = dt.files
    } catch (err) {
      // fallback: input may remain with original FileList
    }
  }

  const handleUpload = async () => {
    if (selectedFiles.length === 0) {
      setMessage('Select up to 3 photos first.')
      return
    }
    setUploading(true)
    setMessage('')
    try {
      const form = new FormData()
      selectedFiles.forEach((f) => form.append('photos', f))

      // get session to include token / user id
      const { data: { session } } = await supabase.auth.getSession()
      const token = session?.access_token
      const userId = session?.user?.id

      const res = await fetch('http://localhost:5000/images', {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}`, 'x-user-id': userId } : { 'x-user-id': userId },
        body: form,
      })
      const body = await res.json()
      if (!res.ok) throw new Error(body.error || 'Upload failed')
      setMessage(`Uploaded ${body.uploaded.length} photo(s).`)
      navigate('/microphone', { replace: true })
      // clear input
      setSelectedFiles([])
      setPhotocount(0)
      if (fileInputRef.current) fileInputRef.current.value = ''
    } catch (err) {
      setMessage(err.message || 'Upload error')
    } finally {
      setUploading(false)
    }
  }

  return (
    <>
      <div className="body">
        <div className="header">
          <h2>Verification</h2>
          {user ? <p>Signed in as {user.email}</p> : <p>Not signed in</p>}
          <button onClick={handleLogout}>Log out</button>
        </div>

        <div className="upload-form">
          <p>Upload up to 3 images of yourself to enable facial recognition</p>

          <div className="photocount">Photos Selected: {photocount} / 3</div>
          <img src={photo} className="photo" alt="Upload Photos" />

          <div className="file-input">
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              multiple
              onChange={handleFileChange}
            />
          </div>

          <div className="upload-buttons">
            <button 
              className="primary-btn"
              onClick={handleUpload} 
              disabled={uploading || photocount === 0}
            >
              {uploading ? 'Uploading…' : 'Upload Photos'}
            </button>
            <button 
              className="secondary-btn"
              onClick={() => { 
                setSelectedFiles([]); 
                setPhotocount(0); 
                if (fileInputRef.current) fileInputRef.current.value = '' 
              }}
            >
              Clear Selection
            </button>
          </div>

          {message && <div className="upload-message">{message}</div>}
        </div>

        {/* Robot Control Section */}
        <div className="section-card">
          <h3>🤖 Robot Control</h3>
          <RobotControl />
        </div>

        {/* Database Testing Section */}
        <div className="section-card">
          <h3>🗄️ Database Testing</h3>
          <DatabaseTester />
        </div>
      </div>
    </>
  )
}

export default Verification
// ...existing code...