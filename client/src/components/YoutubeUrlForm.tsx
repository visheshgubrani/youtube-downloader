import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Checkbox } from '@/components/ui/checkbox'
import { useToast } from '@/hooks/use-toast'
import { handleDownload } from '@/utils/downloadUtils'
import { Youtube, Download, FileMusic } from 'lucide-react'

interface YoutubeUrlFormProps {
  onDownloadStart: () => void
  onDownloadComplete: (filename: string) => void
  onDownloadError: (error: string) => void
}

export default function YoutubeUrlForm({
  onDownloadStart,
  onDownloadComplete,
  onDownloadError,
}: YoutubeUrlFormProps) {
  const [url, setUrl] = useState('')
  const [isPlaylist, setIsPlaylist] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const { toast } = useToast()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    // Simple validation
    if (!url) {
      toast({
        title: 'URL Required',
        description: 'Please enter a YouTube URL',
        variant: 'destructive',
      })
      return
    }

    // Simple URL validation
    if (!url.includes('youtube.com') && !url.includes('youtu.be')) {
      toast({
        title: 'Invalid URL',
        description: 'Please enter a valid YouTube URL',
        variant: 'destructive',
      })
      return
    }

    setIsLoading(true)

    await handleDownload(
      url,
      isPlaylist,
      // On start
      () => {
        onDownloadStart()
      },
      // On success
      (filename) => {
        setIsLoading(false)
        onDownloadComplete(filename)
        toast({
          title: 'Download Complete',
          description: `Successfully downloaded ${filename}`,
        })
      },
      // On error
      (errorMessage) => {
        setIsLoading(false)
        onDownloadError(errorMessage)
        toast({
          title: 'Download Failed',
          description: errorMessage,
          variant: 'destructive',
        })
      }
    )
  }

  return (
    <form onSubmit={handleSubmit} className='space-y-6'>
      <div className='space-y-2'>
        <label
          htmlFor='youtube-url'
          className='block text-sm font-medium text-gray-300'
        >
          YouTube URL
        </label>
        <div className='relative'>
          <div className='absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none'>
            {/* <Youtube className='h-5 w-5 text-gray-400' /> */}
          </div>
          <Input
            id='youtube-url'
            type='url'
            placeholder='https://www.youtube.com/watch?v=...'
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            className='music-input pl-12 pr-4'
            disabled={isLoading}
          />
        </div>
        <p className='text-xs text-gray-400'>
          Enter a YouTube video or playlist URL
        </p>
      </div>

      <div className='flex items-center space-x-2'>
        <Checkbox
          id='playlist'
          checked={isPlaylist}
          onCheckedChange={(checked) => setIsPlaylist(checked === true)}
          disabled={isLoading}
        />
        <label
          htmlFor='playlist'
          className='text-sm font-medium text-gray-300 leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70'
        >
          This is a playlist
        </label>
      </div>

      <Button
        type='submit'
        className='music-button w-full flex items-center justify-center gap-2'
        disabled={isLoading}
      >
        {isLoading ? (
          <>
            <div className='animate-spin h-5 w-5 border-2 border-gray-300 rounded-full border-t-transparent' />
            <span>Processing...</span>
          </>
        ) : (
          <>
            {isPlaylist ? (
              <Download className='h-5 w-5' />
            ) : (
              <FileMusic className='h-5 w-5' />
            )}
            <span>Convert & Download</span>
          </>
        )}
      </Button>
    </form>
  )
}
