import { useState } from 'react'
import './App.css'

function App() {
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleDownload = async (type) => {
    if (!url.trim()) {
      setError('Please enter a valid YouTube URL.')
      return
    }

    setError('')
    setLoading(true)

    try {
      const endpoint = type === 'playlist' ? '/download/playlist' : '/download'
      const response = await fetch(
        `http://localhost:8000${endpoint}?url=${encodeURIComponent(url)}`
      )

      if (!response.ok) throw new Error('Failed to download. Check the URL.')

      const blob = await response.blob()

      // Extract filename from Content-Disposition header
      const contentDisposition = response.headers.get('Content-Disposition')
      let filename = 'download'
      if (contentDisposition) {
        const match = contentDisposition.match(/filename="(.+?)"/)
        if (match && match[1]) {
          filename = decodeURIComponent(match[1]) // Decode in case of special characters
        }
      }

      const fileType = type === 'playlist' ? 'zip' : 'mp3'
      filename = filename.endsWith(fileType)
        ? filename
        : `${filename}.${fileType}`

      // Trigger download
      const downloadLink = document.createElement('a')
      downloadLink.href = URL.createObjectURL(blob)
      downloadLink.download = filename
      document.body.appendChild(downloadLink)
      downloadLink.click()
      document.body.removeChild(downloadLink)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className='container'>
      <h2>YouTube MP3 Downloader</h2>
      <input
        type='text'
        placeholder='Enter YouTube URL'
        value={url}
        onChange={(e) => setUrl(e.target.value)}
      />
      <div className='buttons'>
        <button onClick={() => handleDownload('single')} disabled={loading}>
          Download MP3
        </button>
        <button onClick={() => handleDownload('playlist')} disabled={loading}>
          Download Playlist
        </button>
      </div>
      {error && <p className='error'>{error}</p>}
      {loading && <p>Downloading...</p>}
    </div>
  )
}

export default App
