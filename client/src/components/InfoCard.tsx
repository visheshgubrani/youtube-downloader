
import { Youtube, FileMusic } from 'lucide-react';

export default function InfoCard() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-12">
      <div className="music-card">
        <div className="flex items-center space-x-4 mb-4">
          <div className="rounded-full bg-youtube/10 p-3">
            <Youtube className="h-6 w-6 text-youtube" />
          </div>
          <h3 className="font-semibold text-white">YouTube Videos</h3>
        </div>
        <p className="text-gray-400 text-sm">
          Paste any YouTube video URL and convert it to MP3 format. 
          Perfect for creating your offline music collection.
        </p>
      </div>
      
      <div className="music-card">
        <div className="flex items-center space-x-4 mb-4">
          <div className="rounded-full bg-music-accent/10 p-3">
            <FileMusic className="h-6 w-6 text-music-accent" />
          </div>
          <h3 className="font-semibold text-white">YouTube Playlists</h3>
        </div>
        <p className="text-gray-400 text-sm">
          Convert entire YouTube playlists and download them as a ZIP file
          containing all tracks, ready for your music library.
        </p>
      </div>
    </div>
  );
}
