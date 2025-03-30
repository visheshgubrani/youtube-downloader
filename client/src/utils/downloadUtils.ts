
/**
 * Extracts filename from Content-Disposition header
 */
export function extractFilenameFromHeader(disposition: string | null): string {
  if (!disposition) return "download";
  
  // Try to extract filename from the Content-Disposition header
  const filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
  const matches = filenameRegex.exec(disposition);
  if (matches && matches[1]) {
    let filename = matches[1].replace(/['"]/g, '');
    return filename;
  }
  
  // Default fallback filename
  return "download";
}

/**
 * Initiates file download from blob data
 */
export function downloadFile(blob: Blob, filename: string) {
  // Create a URL for the blob
  const url = window.URL.createObjectURL(blob);
  
  // Create a temporary anchor element
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', filename);
  
  // Append to the body
  document.body.appendChild(link);
  
  // Programmatically click the link to trigger the download
  link.click();
  
  // Clean up
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
}

/**
 * Handles API responses and downloads files
 */
export async function handleDownload(
  url: string, 
  isPlaylist: boolean,
  onStart: () => void,
  onSuccess: (filename: string) => void,
  onError: (error: string) => void
) {
  try {
    onStart();
    
    // Construct the API endpoint based on whether it's a playlist or not
    const endpoint = isPlaylist 
      ? `http://localhost:8000/download/playlist?url=${encodeURIComponent(url)}`
      : `http://localhost:8000/download?url=${encodeURIComponent(url)}`;
    
    // Fetch the file from the API
    const response = await fetch(endpoint);
    
    if (!response.ok) {
      let errorText = await response.text();
      throw new Error(errorText || `Server returned ${response.status}: ${response.statusText}`);
    }
    
    // Get the filename from the Content-Disposition header
    const contentDisposition = response.headers.get('content-disposition');
    let filename = extractFilenameFromHeader(contentDisposition);
    
    // If no filename was found, create one based on the type
    if (!filename || filename === 'download') {
      filename = isPlaylist ? 'youtube_playlist.zip' : 'youtube_audio.mp3';
    }
    
    // Get the file blob
    const blob = await response.blob();
    
    // Download the file
    downloadFile(blob, filename);
    
    // Call the success callback
    onSuccess(filename);
  } catch (error) {
    // Handle errors
    console.error('Download error:', error);
    onError(error instanceof Error ? error.message : 'An unknown error occurred');
  }
}
