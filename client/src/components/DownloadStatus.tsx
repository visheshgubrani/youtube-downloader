import { useState, useEffect } from 'react'
import { FileMusic, Check, Download, AlertCircle } from 'lucide-react'

interface DownloadStatusProps {
  status: 'idle' | 'loading' | 'success' | 'error'
  filename?: string
  errorMessage?: string
}

export default function DownloadStatus({
  status,
  filename,
  errorMessage,
}: DownloadStatusProps) {
  const [visible, setVisible] = useState(false)

  // Show component when status changes to loading, success, or error
  useEffect(() => {
    if (status === 'loading' || status === 'success' || status === 'error') {
      setVisible(true)
    }

    // Hide the success or error message after 5 seconds
    if (status === 'success' || status === 'error') {
      const timer = setTimeout(() => {
        setVisible(false)
      }, 5000)

      return () => clearTimeout(timer)
    }
  }, [status])

  if (!visible) return null

  return (
    <div className='music-card mt-6'>
      {status === 'loading' && (
        <div className='flex items-center space-x-4'>
          <div className='rounded-full bg-music-primary/20 p-3'>
            <Download className='h-6 w-6 text-music-primary animate-pulse' />
          </div>
          <div>
            <h3 className='font-semibold text-white'>Downloading...</h3>
            <p className='text-sm text-gray-400'>
              Please wait while we process your request
            </p>
          </div>
        </div>
      )}

      {status === 'success' && filename && (
        <div className='flex items-center space-x-4'>
          <div className='rounded-full bg-green-500/20 p-3'>
            <Check className='h-6 w-6 text-green-500' />
          </div>
          <div>
            <h3 className='font-semibold text-white'>Download Complete</h3>
            <p className='text-sm text-gray-400'>
              Successfully downloaded{' '}
              <span className='text-music-primary'>{filename}</span>
            </p>
          </div>
        </div>
      )}

      {status === 'error' && (
        <div className='flex items-center space-x-4'>
          <div className='rounded-full bg-red-500/20 p-3'>
            <AlertCircle className='h-6 w-6 text-red-500' />
          </div>
          <div>
            <h3 className='font-semibold text-white'>Download Failed</h3>
            <p className='text-sm text-gray-400'>
              {errorMessage || 'Failed to download the file. Please try again.'}
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
