import React, { useState, useRef } from 'react';
import { Search, Paperclip, MapPin, Image, Smile, Mic, Loader2, X } from 'lucide-react';
import { generateContent, uploadImage } from '../lib/api';
import type { GenerationResponse, UploadResponse } from '../types';

const PerplexityInterface = () => {
  const [inputValue, setInputValue] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [result, setResult] = useState<GenerationResponse | null>(null);
  const [previousResult, setPreviousResult] = useState<GenerationResponse | null>(null); // Keep previous result while generating
  const [error, setError] = useState<string | null>(null);
  const [uploadedImages, setUploadedImages] = useState<UploadResponse[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null); // Track session for conversational editing
  const [userId] = useState('user_' + Date.now()); // Generate persistent user ID
  const fileInputRef = useRef<HTMLInputElement>(null);

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

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center p-4">
      <div className="w-full max-w-4xl">
        {/* Logo */}
        <div className="text-center mb-12">
          <img 
            src="/logo_with_text_white_trans.png" 
            alt="PicArcade" 
            className="h-32 mx-auto"
          />
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
          <div className="bg-gray-800/60 backdrop-blur-sm border border-gray-700/50 rounded-2xl p-4 shadow-2xl">
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
                
                <button 
                  type="button"
                  className="p-1 hover:bg-gray-700/50 rounded-lg transition-colors"
                  disabled={isGenerating}
                >
                  <MapPin className="w-5 h-5 text-gray-400 hover:text-gray-300" />
                </button>
                
                <button 
                  type="button"
                  className="p-1 hover:bg-gray-700/50 rounded-lg transition-colors"
                  disabled={isGenerating}
                >
                  <Image className="w-5 h-5 text-gray-400 hover:text-gray-300" />
                </button>
                
                <button 
                  type="button"
                  className="p-1 hover:bg-gray-700/50 rounded-lg transition-colors"
                  disabled={isGenerating}
                >
                  <Smile className="w-5 h-5 text-gray-400 hover:text-gray-300" />
                </button>
                
                <button 
                  type="button"
                  className="p-1 hover:bg-gray-700/50 rounded-lg transition-colors"
                  disabled={isGenerating}
                >
                  <Paperclip className="w-5 h-5 text-gray-400 hover:text-gray-300" />
                </button>
                
                <button 
                  type="button"
                  className="p-1 hover:bg-gray-700/50 rounded-lg transition-colors"
                  disabled={isGenerating}
                >
                  <Mic className="w-5 h-5 text-gray-400 hover:text-gray-300" />
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
                    <button
                      onClick={() => removeUploadedImage(index)}
                      className="absolute -top-2 -right-2 bg-red-500 hover:bg-red-600 text-white rounded-full p-1 opacity-0 group-hover:opacity-100 transition-opacity"
                      title="Remove image"
                    >
                      <X className="w-3 h-3" />
                    </button>
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
                <img 
                  src={result.output_url} 
                  alt="Generated content"
                  className="max-w-full h-auto rounded-lg mx-auto shadow-lg"
                />
              ) : (previousResult?.success && previousResult?.output_url) ? (
                <img 
                  src={previousResult.output_url} 
                  alt="Previous generated content"
                  className="max-w-full h-auto rounded-lg mx-auto shadow-lg opacity-75"
                />
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
      </div>
    </div>
  );
};

export default PerplexityInterface; 