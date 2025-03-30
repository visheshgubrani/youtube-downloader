import { useState } from 'react'
import AppHeader from '@/components/AppHeader'
import YoutubeUrlForm from '@/components/YoutubeUrlForm'
import DownloadStatus from '@/components/DownloadStatus'
import InfoCard from '@/components/InfoCard'
import AppFooter from '@/components/AppFooter'

const Index = () => {
  const [downloadStatus, setDownloadStatus] = useState<
    'idle' | 'loading' | 'success' | 'error'
  >('idle')
  const [downloadedFilename, setDownloadedFilename] = useState<
    string | undefined
  >()
  const [errorMessage, setErrorMessage] = useState<string>()

  const handleDownloadStart = () => {
    setDownloadStatus('loading')
    setErrorMessage(undefined)
  }

  const handleDownloadComplete = (filename: string) => {
    setDownloadedFilename(filename)
    setDownloadStatus('success')
  }

  const handleDownloadError = (error: string) => {
    setDownloadStatus('error')
    setErrorMessage(error)
  }

  return (
    <div className='min-h-screen bg-music-dark py-12 px-4'>
      <div className='max-w-md mx-auto'>
        <AppHeader />

        <div className='music-card'>
          <YoutubeUrlForm
            onDownloadStart={handleDownloadStart}
            onDownloadComplete={handleDownloadComplete}
            onDownloadError={handleDownloadError}
          />
        </div>

        <DownloadStatus
          status={downloadStatus}
          filename={downloadedFilename}
          errorMessage={errorMessage}
        />

        <InfoCard />

        <AppFooter />
      </div>
    </div>
  )
}

export default Index
