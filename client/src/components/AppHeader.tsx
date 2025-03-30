
import { FileMusic } from 'lucide-react';

export default function AppHeader() {
  return (
    <header className="mb-8 text-center">
      <div className="flex items-center justify-center gap-2 mb-2">
        <FileMusic className="h-8 w-8 text-music-primary" />
        <h1 className="text-3xl md:text-4xl font-bold bg-clip-text text-transparent bg-music-gradient">
          MP3ify Magic
        </h1>
      </div>
      <p className="text-gray-400 max-w-md mx-auto">
        Convert YouTube videos to high-quality MP3 files with just a few clicks
      </p>
    </header>
  );
}
