import React, { useState, useRef, useEffect } from 'react';
import { Search, Paperclip, MapPin, Image, Smile, Mic, Loader2, X, History, Clock, Tag, User, LogOut, RotateCcw } from 'lucide-react';
import { generateContent, uploadImage } from '../lib/api';
import type { GenerationResponse, UploadResponse, HistoryItem } from '../types';
import GenerationHistory from './GenerationHistory';
import ReferencesPanel from './ReferencesPanel';
import TagImageModal from './TagImageModal';
import { AuthModal } from './AuthModal';
import { useAuth } from './AuthProvider';
import { getOrCreateUserId } from '../lib/userUtils';

const PerplexityInterface = () => {
  const { user, session, loading, signOut } = useAuth();
  const [inputValue, setInputValue] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [result, setResult] = useState<GenerationResponse | null>(null);
  const [previousResult, setPreviousResult] = useState<GenerationResponse | null>(null); // Keep previous result while generating
  const [error, setError] = useState<string | null>(null);
  const [uploadedImages, setUploadedImages] = useState<UploadResponse[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null); // Track session for conversational editing
  // Generate a persistent user ID that survives page refreshes
  const [userId] = useState(() => getOrCreateUserId());
  const [showHistory, setShowHistory] = useState(false);
  const [showReferences, setShowReferences] = useState(false);
  const [showTagModal, setShowTagModal] = useState(false);
  const [imageToTag, setImageToTag] = useState<string>('');
  const [historyRefreshTrigger, setHistoryRefreshTrigger] = useState(0);
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const userMenuRef = useRef<HTMLDivElement>(null);

  // Close user menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) {
        setShowUserMenu(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!inputValue.trim() || isGenerating) return;

    setIsGenerating(true);
    setError(null);
    
    // Keep current result visible while generating new one
    if (result) {
      setPreviousResult(result);
    }

    try {
      console.log(`[DEBUG Frontend] About to generate with session_id: ${sessionId}`);
      const response = await generateContent({
        prompt: inputValue.trim(),
        user_id: userId,
        session_id: sessionId || undefined, // Send session ID for conversational continuity
        quality_priority: 'balanced',
        uploaded_images: uploadedImages.map(img => img.public_url)
      });

      setResult(response);
      
      // Extract session ID from response metadata for future requests
      if (response.metadata?.session_id) {
        setSessionId(response.metadata.session_id);
        console.log('[Frontend] Session ID obtained:', response.metadata.session_id);
      }
      
      // Clear uploaded images after successful generation (they're now part of the session)
      if (response.success && uploadedImages.length > 0) {
        setUploadedImages([]);
      }
      
      if (!response.success) {
        setError(response.error_message || 'Generation failed');
      } else {
        // Clear input after successful generation
        setInputValue('');
        setPreviousResult(null); // Clear previous result since we have new one
        
        // Refresh history to show the new generation
        setHistoryRefreshTrigger(prev => prev + 1);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      // Restore previous result if new generation failed
      if (previousResult) {
        setResult(previousResult);
        setPreviousResult(null);
      }
    } finally {
      setIsGenerating(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as any);
    }
  };

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    setIsUploading(true);
    setError(null);

    try {
      const uploadPromises = Array.from(files).map(file => 
        uploadImage(file, 'user_' + Date.now())
      );
      
      const uploadResults = await Promise.all(uploadPromises);
      setUploadedImages(prev => [...prev, ...uploadResults]);
      
      // Add uploaded image URLs to prompt
      const imageUrls = uploadResults.map(result => result.public_url).join(', ');
      setInputValue(prev => 
        prev ? `${prev}\n\nUploaded images: ${imageUrls}` : `Use these images: ${imageUrls}`
      );
      
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Upload failed');
    } finally {
      setIsUploading(false);
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const triggerImageUpload = () => {
    fileInputRef.current?.click();
  };

  const removeUploadedImage = (index: number) => {
    setUploadedImages(prev => prev.filter((_, i) => i !== index));
    // Update input value to remove the removed image URL
    const remainingUrls = uploadedImages
      .filter((_, i) => i !== index)
      .map(img => img.public_url)
      .join(', ');
    
    if (remainingUrls) {
      setInputValue(prev => {
        const lines = prev.split('\n');
        const nonImageLines = lines.filter(line => !line.includes('images:'));
        return [...nonImageLines, `Use these images: ${remainingUrls}`].join('\n');
      });
    } else {
      setInputValue(prev => 
        prev.split('\n').filter(line => !line.includes('images:')).join('\n')
      );
    }
  };



  const handleHistoryClick = () => {
    setShowHistory(true);
  };

  const handleReferencesClick = () => {
    setShowReferences(true);
  };

  const handleReferenceSelect = (tag: string) => {
    // Add the @tag to the input
    setInputValue(prev => {
      const cursorPos = prev.length; // Add to end for now
      return prev + (prev ? ' ' : '') + tag;
    });
    setShowReferences(false);
  };

  const handleTagImage = (imageUrl: string) => {
    setImageToTag(imageUrl);
    setShowTagModal(true);
  };

  const handleImageTagged = (tag: string) => {
    // Optionally refresh references or show a success message
    console.log(`Image tagged as @${tag}`);
  };

  const selectFromHistory = async (item: HistoryItem) => {
    if (item.output_url && item.success === 'success') {
      // Replace the current active image/video with the selected one
      setResult({
        success: true,
        generation_id: item.generation_id,
        output_url: item.output_url,
        model_used: item.model_used,
        execution_time: item.execution_time,
        image_source_type: 'working_image'
      });
      
      // Clear previous result and uploaded images since we're starting with a new base
      setPreviousResult(null);
      setUploadedImages([]);
      setInputValue('');
      
      // Set or update session ID for this working image
      console.log(`[DEBUG Frontend] Setting session ID to: ${item.generation_id}`);
      setSessionId(item.generation_id);
      
      // **CRITICAL FIX**: Set this image as the working image in the session
      try {
        const sessionId = item.generation_id; // Use generation_id as session_id
        console.log(`[DEBUG Frontend] About to set working image for session ${sessionId}: ${item.output_url}`);
        
        // Import the API function we'll need
        const { setWorkingImage } = await import('../lib/api');
        
        const result = await setWorkingImage(sessionId, item.output_url, userId);
        console.log(`[DEBUG Frontend] Successfully set working image:`, result);
      } catch (error) {
        console.error('[DEBUG Frontend] Failed to set working image in session:', error);
        // Don't throw - continue with the selection even if working image setting fails
      }
      
      setShowHistory(false);
    }
  };

  const handleDeleteGeneration = async (generationId: string) => {
    try {
      // Call API to delete the generation (you might need to implement this endpoint)
      const response = await fetch(`/api/v1/generation/history/${generationId}`, {
        method: 'DELETE'
      });
      
      if (response.ok) {
        // Refresh history to remove the deleted item
        setHistoryRefreshTrigger(prev => prev + 1);
      } else {
        console.error('Failed to delete generation');
      }
    } catch (error) {
      console.error('Error deleting generation:', error);
    }
  };

  const handleStartFresh = async () => {
    if (isGenerating) return;
    
    // Clear all state
    setInputValue('');
    setUploadedImages([]);
    setResult(null);
    setPreviousResult(null);
    setError(null);
    setSessionId(null);
    
    // Clear any active working images by clearing the session
    try {
      if (sessionId) {
        // Call API to clear the session (you might need to implement this endpoint)
        const response = await fetch(`/api/v1/generation/session/${sessionId}`, {
          method: 'DELETE'
        });
      }
    } catch (error) {
      console.log('Note: Could not clear session (this is normal if no session exists)');
    }
    
    // Force refresh the page state
    setHistoryRefreshTrigger(prev => prev + 1);
  };



  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center p-4">
      <div className="w-full max-w-4xl">
        {/* Header with Logo and User Menu */}
        <div className="flex items-center justify-between mb-12">
          <div className="flex-1"></div>
          
          {/* Logo */}
          <div className="text-center">
            <img 
              src="/logo_with_text_white_trans.png" 
              alt="PicArcade" 
              className="h-32 mx-auto"
            />
          </div>
          
          {/* User Menu */}
          <div className="flex-1 flex justify-end">
            {loading ? (
              <div className="w-8 h-8 rounded-full bg-gray-700 animate-pulse"></div>
            ) : user ? (
              <div className="relative" ref={userMenuRef}>
                <button
                  onClick={() => setShowUserMenu(!showUserMenu)}
                  className="flex items-center gap-2 p-2 rounded-lg bg-gray-800/60 border border-gray-700/50 hover:bg-gray-700/60 transition-colors"
                >
                  <User className="w-5 h-5 text-gray-300" />
                  <span className="text-gray-300 text-sm hidden sm:block">
                    {user.email?.split('@')[0] || 'User'}
                  </span>
                </button>
                
                {showUserMenu && (
                  <div className="absolute right-0 top-full mt-2 w-48 bg-gray-800 border border-gray-700 rounded-lg shadow-xl z-50">
                    <div className="p-3 border-b border-gray-700">
                      <p className="text-white text-sm font-medium">{user.email}</p>
                      <p className="text-gray-400 text-xs">Signed in</p>
                    </div>
                    <button
                      onClick={async () => {
                        await signOut();
                        setShowUserMenu(false);
                      }}
                      className="w-full flex items-center gap-2 p-3 text-left text-gray-300 hover:bg-gray-700 transition-colors"
                    >
                      <LogOut className="w-4 h-4" />
                      Sign Out
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <button
                onClick={() => setShowAuthModal(true)}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
              >
                <User className="w-4 h-4" />
                Sign In
              </button>
            )}
          </div>
        </div>

        {/* Hidden File Input */}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          multiple
          onChange={handleImageUpload}
          className="hidden"
        />

        {/* Search Interface */}
        <form onSubmit={handleSubmit} className="relative mb-8">
          <div className={`bg-gray-800/60 backdrop-blur-sm border border-gray-700/50 rounded-2xl p-4 shadow-2xl ${isGenerating ? 'throb-outline' : ''}`}>
            <div className="flex items-center gap-3">
              {/* Search Icon */}
              <div className="flex-shrink-0">
                {isGenerating ? (
                  <Loader2 className="w-5 h-5 text-cyan-400 animate-spin" />
                ) : (
                  <Search className="w-5 h-5 text-gray-400" />
                )}
              </div>

              {/* Input Field */}
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Let's make something amazing..."
                disabled={isGenerating}
                className="flex-1 bg-transparent text-white placeholder-gray-400 text-lg outline-none disabled:opacity-50"
              />

              {/* Action Icons */}
              <div className="flex items-center gap-3 flex-shrink-0">
                <button 
                  type="button"
                  onClick={handleStartFresh}
                  className="p-1 hover:bg-gray-700/50 rounded-lg transition-colors relative"
                  disabled={isGenerating}
                  title="Start fresh - Clear all images and start over"
                >
                  <RotateCcw className="w-5 h-5 text-orange-400 hover:text-orange-300" />
                </button>
                
                <button 
                  type="button"
                  onClick={handleReferencesClick}
                  className="p-1 hover:bg-gray-700/50 rounded-lg transition-colors relative"
                  disabled={isGenerating}
                  title="Manage references (@mentions)"
                >
                  <Tag className="w-5 h-5 text-purple-400 hover:text-purple-300" />
                </button>
                
                <button 
                  type="button"
                  onClick={handleHistoryClick}
                  className="p-1 hover:bg-gray-700/50 rounded-lg transition-colors relative"
                  disabled={isGenerating}
                  title="View generation history"
                >
                  <History className="w-5 h-5 text-gray-400 hover:text-gray-300" />
                </button>
                
                <button 
                  type="button"
                  onClick={triggerImageUpload}
                  className="p-1 hover:bg-gray-700/50 rounded-lg transition-colors relative"
                  disabled={isGenerating || isUploading}
                  title="Upload images"
                >
                  {isUploading ? (
                    <Loader2 className="w-5 h-5 text-cyan-400 animate-spin" />
                  ) : (
                    <Paperclip className="w-5 h-5 text-gray-400 hover:text-gray-300" />
                  )}
                </button>
                
                {/* Submit Button */}
                <button 
                  type="submit"
                  disabled={!inputValue.trim() || isGenerating}
                  className="bg-cyan-500 hover:bg-cyan-600 disabled:bg-gray-600 disabled:cursor-not-allowed p-2 rounded-lg transition-colors"
                >
                  {isGenerating ? (
                    <Loader2 className="w-4 h-4 text-white animate-spin" />
                  ) : (
                    <div className="flex items-center gap-1">
                      <div className="w-1 h-3 bg-white rounded-full animate-pulse"></div>
                      <div className="w-1 h-4 bg-white rounded-full animate-pulse" style={{ animationDelay: '0.1s' }}></div>
                      <div className="w-1 h-2 bg-white rounded-full animate-pulse" style={{ animationDelay: '0.2s' }}></div>
                      <div className="w-1 h-4 bg-white rounded-full animate-pulse" style={{ animationDelay: '0.3s' }}></div>
                    </div>
                  )}
                </button>
              </div>
            </div>
          </div>
        </form>

        {/* Uploaded Images Display */}
        {uploadedImages.length > 0 && (
          <div className="mb-8">
            <div className="bg-gray-800/60 backdrop-blur-sm border border-gray-700/50 rounded-2xl p-4 shadow-2xl">
              <h3 className="text-white text-sm mb-3 flex items-center gap-2">
                <Image className="w-4 h-4" />
                Uploaded Images ({uploadedImages.length})
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {uploadedImages.map((image, index) => (
                  <div key={index} className="relative group">
                    <img
                      src={image.public_url}
                      alt={image.filename}
                      className="w-full h-24 object-cover rounded-lg border border-gray-600"
                    />
                    <div className="absolute -top-2 -right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button
                        onClick={() => handleTagImage(image.public_url)}
                        className="bg-purple-600 hover:bg-purple-700 text-white rounded-full p-1"
                        title="Tag image"
                      >
                        <Tag className="w-3 h-3" />
                      </button>
                      <button
                        onClick={() => removeUploadedImage(index)}
                        className="bg-red-500 hover:bg-red-600 text-white rounded-full p-1"
                        title="Remove image"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </div>
                    <div className="absolute bottom-1 left-1 right-1 bg-black/70 text-white text-xs p-1 rounded truncate">
                      {image.filename}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Status Messages */}
        {isGenerating && (
          <div className="text-center mb-8">
            <p className="text-gray-400 text-lg">Creating something amazing...</p>
          </div>
        )}

        {isUploading && (
          <div className="text-center mb-8">
            <p className="text-cyan-400 text-lg flex items-center justify-center gap-2">
              <Loader2 className="w-5 h-5 animate-spin" />
              Uploading images...
            </p>
          </div>
        )}

        {error && (
          <div className="text-center mb-8">
            <div className="bg-red-500/20 border border-red-500/50 rounded-lg p-4 text-red-300">
              {error}
            </div>
          </div>
        )}

        {/* Results */}
        {(result || previousResult) && (
          <div className="text-center">
            <div className="bg-gray-800/60 backdrop-blur-sm border border-gray-700/50 rounded-2xl p-6 shadow-2xl relative">
              {/* Show generating overlay if there's a previous result and we're generating */}
              {isGenerating && previousResult && (
                <div className="absolute inset-0 bg-gray-900/70 backdrop-blur-sm rounded-2xl flex items-center justify-center z-10">
                  <div className="text-center">
                    <Loader2 className="w-8 h-8 text-cyan-400 animate-spin mx-auto mb-3" />
                    <p className="text-white text-lg">Generating new version...</p>
                    <p className="text-gray-400 text-sm">Your current image will be replaced</p>
                  </div>
                </div>
              )}
              
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-white text-xl">
                  {isGenerating && previousResult ? "Current Creation" : "Your Creation"}
                </h3>
                
                {/* Show session info */}
                {sessionId && result?.image_source_type && (
                  <div className="text-xs text-gray-400 flex items-center gap-2">
                    {result.image_source_type === 'working_image' && (
                      <span className="bg-blue-500/20 text-blue-300 px-2 py-1 rounded">
                        Editing Previous Result
                      </span>
                    )}
                    {result.image_source_type === 'uploaded' && (
                      <span className="bg-green-500/20 text-green-300 px-2 py-1 rounded">
                        Editing Uploaded Image
                      </span>
                    )}
                  </div>
                )}
              </div>
              
              {/* Show current result or previous result while generating */}
              {(result?.success && result?.output_url) ? (
                result.output_url.includes('.mp4') || result.output_url.includes('video') || result.output_url.includes('mock-image-to-video') ? (
                  <video
                    src={result.output_url}
                    controls
                    className="max-w-full h-auto max-h-96 rounded-lg mx-auto shadow-lg"
                  >
                    Your browser does not support video playback.
                  </video>
                ) : (
                  <div className="relative inline-block">
                    <img 
                      src={result.output_url} 
                      alt="Generated content"
                      className="max-w-full h-auto rounded-lg mx-auto shadow-lg"
                    />
                    {/* Tag icon overlay */}
                    <button
                      onClick={() => result.output_url && handleTagImage(result.output_url)}
                      className="absolute top-2 right-2 p-2 bg-purple-600 text-white rounded-full hover:bg-purple-700 transition-all opacity-75 hover:opacity-100 shadow-lg"
                      title="Tag this image"
                    >
                      <Tag className="w-4 h-4" />
                    </button>
                  </div>
                )
              ) : (previousResult?.success && previousResult?.output_url) ? (
                previousResult.output_url.includes('.mp4') || previousResult.output_url.includes('video') || previousResult.output_url.includes('mock-image-to-video') ? (
                  <video
                    src={previousResult.output_url}
                    controls
                    className="max-w-full h-auto max-h-96 rounded-lg mx-auto shadow-lg opacity-75"
                  >
                    Your browser does not support video playback.
                  </video>
                ) : (
                  <div className="relative inline-block">
                    <img 
                      src={previousResult.output_url} 
                      alt="Previous generated content"
                      className="max-w-full h-auto rounded-lg mx-auto shadow-lg opacity-75"
                    />
                    {/* Tag icon overlay */}
                    <button
                      onClick={() => previousResult.output_url && handleTagImage(previousResult.output_url)}
                      className="absolute top-2 right-2 p-2 bg-purple-600 text-white rounded-full hover:bg-purple-700 transition-all opacity-75 hover:opacity-100 shadow-lg"
                      title="Tag this image"
                    >
                      <Tag className="w-4 h-4" />
                    </button>
                  </div>
                )
              ) : null}
              
              <div className="mt-4 text-sm text-gray-400">
                {result ? (
                  <>
                    <p>Model: {result.model_used}</p>
                    {result.execution_time && (
                      <p>Generated in {result.execution_time.toFixed(2)}s</p>
                    )}
                    {result.input_image_used && (
                      <p className="text-xs text-blue-400">
                        Edited from: {result.input_image_used.substring(0, 50)}...
                      </p>
                    )}
                  </>
                ) : previousResult ? (
                  <>
                    <p>Model: {previousResult.model_used}</p>
                    {previousResult.execution_time && (
                      <p>Generated in {previousResult.execution_time.toFixed(2)}s</p>
                    )}
                  </>
                ) : null}
              </div>
            </div>
          </div>
        )}

        {/* History Modal */}
        {showHistory && (
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-gray-800 rounded-2xl w-full max-w-4xl max-h-[80vh] flex flex-col">
              {/* Header */}
              <div className="flex items-center justify-between p-6 border-b border-gray-700">
                <h2 className="text-xl font-semibold text-white flex items-center gap-2">
                  <History className="w-6 h-6" />
                  Generation History
                </h2>
                <button
                  onClick={() => setShowHistory(false)}
                  className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
                >
                  <X className="w-5 h-5 text-gray-400" />
                </button>
              </div>

              {/* Content */}
              <div className="flex-1 overflow-auto p-6">
                <GenerationHistory
                  refreshTrigger={historyRefreshTrigger}
                  userId={userId}
                  onSelectImage={selectFromHistory}
                  onTagImage={handleTagImage}
                  onDeleteItem={handleDeleteGeneration}
                />
              </div>

              {/* Footer */}
              <div className="border-t border-gray-700 p-4">
                <div className="flex items-center justify-center">
                  <p className="text-gray-400 text-sm">
                    Click on any image to add it to your editing context
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* References Panel */}
        <ReferencesPanel
          isOpen={showReferences}
          onClose={() => setShowReferences(false)}
          userId={userId}
          onReferenceSelect={handleReferenceSelect}
        />

        {/* Tag Image Modal */}
        <TagImageModal
          isOpen={showTagModal}
          onClose={() => setShowTagModal(false)}
          imageUrl={imageToTag}
          userId={userId}
          onTagged={handleImageTagged}
        />

        {/* Authentication Modal */}
        <AuthModal
          isOpen={showAuthModal}
          onClose={() => setShowAuthModal(false)}
          defaultMode="signin"
        />
      </div>
    </div>
  );
};

export default PerplexityInterface; 