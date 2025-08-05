import React, { useState, useRef, useEffect } from 'react';
import { Search, Paperclip, Image, Loader2, X, History, Tag, User, LogOut, RotateCcw, Camera, Send, Settings } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { generateContent, uploadImage, getUserReferences } from '../lib/api';
import type { GenerationResponse, UploadResponse, HistoryItem, ReferenceImage } from '../types';
import GenerationHistory from './GenerationHistory';
import ReferencesPanel from './ReferencesPanel';
import TagImageModal from './TagImageModal';
import ImageMaximizeModal from './ImageMaximizeModal';
import ShareButton from './ShareButton';
import { AuthModal } from './AuthModal';
import { useAuth } from './AuthProvider';
import { getOrCreateUserId } from '../lib/userUtils';
import ReferenceInput from './ReferenceInput';
import XPIndicator from './XPIndicator';
import XPNotification from './XPNotification';

const PerplexityInterface = () => {
  const { user, loading, signOut } = useAuth();
  const router = useRouter();
  const [inputValue, setInputValue] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [result, setResult] = useState<GenerationResponse | null>(null);
  const [previousResult, setPreviousResult] = useState<GenerationResponse | null>(null); // Keep previous result while generating
  const [error, setError] = useState<string | null>(null);
  const [uploadedImages, setUploadedImages] = useState<UploadResponse[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null); // Track session for conversational editing
  const [currentWorkingVideo, setCurrentWorkingVideo] = useState<string | null>(null); // Track current working video for editing
  // Use authenticated Supabase user ID when available, fallback to localStorage for unauthenticated users
  const [userId] = useState(() => {
    if (user?.id) {
      return user.id; // Use Supabase authenticated user ID for cross-device sync
    }
    return getOrCreateUserId(); // Fallback for unauthenticated users
  });
  const [showHistory, setShowHistory] = useState(false);
  const [showReferences, setShowReferences] = useState(false);
  const [showTagModal, setShowTagModal] = useState(false);
  const [imageToTag, setImageToTag] = useState<string>('');
  const [historyRefreshTrigger, setHistoryRefreshTrigger] = useState(0);
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [showCamera, setShowCamera] = useState(false);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [showImageModal, setShowImageModal] = useState(false);
  const [imageToMaximize, setImageToMaximize] = useState<string>('');
  const [taggedImages, setTaggedImages] = useState<Set<string>>(new Set());
  const [imageTagMap, setImageTagMap] = useState<Map<string, string>>(new Map());
  const [currentXP, setCurrentXP] = useState<number>(0);
  const [currentWittyMessageIndex, setCurrentWittyMessageIndex] = useState<number>(0);
  const [currentWittyMessages, setCurrentWittyMessages] = useState<string[]>([]);

  // Helper function to check if URL is an image
  const isImageUrl = (url: string) => {
    return /\.(jpg|jpeg|png|gif|webp|svg)(\?|$)/i.test(url);
  };

  // Helper function to check if URL is a video
  const isVideoUrl = (url: string) => {
    return /\.(mp4|mov|avi|mkv|webm|m4v)(\?|$)/i.test(url);
  };


  const [xpNotification, setXpNotification] = useState<{
    show: boolean;
    amount: number;
    type: 'gain' | 'loss' | 'bonus' | 'refund';
    reason: string;
  }>({ show: false, amount: 0, type: 'loss', reason: '' });
  const fileInputRef = useRef<HTMLInputElement>(null);
  const userMenuRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // Load tagged images state from Supabase on component mount
  const loadTaggedImagesState = async () => {
    try {
      const references = await getUserReferences(userId);
      const taggedImageUrls = new Set(references.map(ref => ref.image_url));
      const imageToTagMap = new Map(references.map(ref => [ref.image_url, ref.tag]));
      
      setTaggedImages(taggedImageUrls);
      setImageTagMap(imageToTagMap);
      console.log(`[Sync] Loaded ${references.length} tagged images from database`);
    } catch (error) {
      console.error('Failed to load tagged images state:', error);
    }
  };

  // Load tagged images state when userId changes (including on mount)
  useEffect(() => {
    if (userId) {
      loadTaggedImagesState();
    }
  }, [userId]);

  // Load XP data
  useEffect(() => {
    loadXPData();
  }, []);

  // Cycle through witty messages during generation
  useEffect(() => {
    if (isGenerating) {
      // Use current witty messages for the current request
      const messages = currentWittyMessages;
      
      if (messages && messages.length > 0) {
        const interval = setInterval(() => {
          setCurrentWittyMessageIndex(prev => (prev + 1) % messages.length);
        }, 10000); // Change message every 10 seconds

        return () => clearInterval(interval);
      }
    } else {
      setCurrentWittyMessageIndex(0);
    }
  }, [isGenerating, currentWittyMessages]);

  const loadXPData = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      };

      const response = await fetch(`${baseUrl}/api/v1/subscriptions/current`, { headers });
      if (response.ok) {
        const data = await response.json();
        setCurrentXP(data.xp_balance || 0);
      }
    } catch (error) {
      console.error('Error loading XP data:', error);
    }
  };

  // Function to extract and resolve @ references from prompt
  const extractReferences = async (prompt: string): Promise<ReferenceImage[]> => {
    const mentionRegex = /@(\w+)/g;
    const mentions: string[] = [];
    let match;

    while ((match = mentionRegex.exec(prompt)) !== null) {
      mentions.push(match[1]);
    }

    if (mentions.length === 0) {
      return [];
    }

    try {
      // Get all user references
      const allReferences = await getUserReferences(userId);
      const referenceMap = new Map(allReferences.map(ref => [ref.tag, ref]));

      // Resolve mentions to reference images
      const referenceImages: ReferenceImage[] = [];
      for (const mention of mentions) {
        const reference = referenceMap.get(mention);
        if (reference) {
          referenceImages.push({
            uri: reference.image_url,
            tag: mention
          });
        }
      }

      return referenceImages;
    } catch (error) {
      console.error('Failed to resolve references:', error);
      return [];
    }
  };

  // Check camera availability on component mount
  useEffect(() => {
    const checkCameraSupport = () => {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        console.warn('Camera API not supported in this browser')
        return false
      }
      
      if (!window.isSecureContext) {
        console.warn('Camera requires HTTPS. Current URL:', window.location.href)
        return false
      }
      
      console.log('Camera API supported and secure context available')
      return true
    }
    
    checkCameraSupport()
  }, [])

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

    // Check XP cost before generation
    try {
      // Pre-generation setup
    } catch (error) {
      console.error('Error in generation:', error);
    }

    setIsGenerating(true);
    setError(null);
    
    // Keep current result visible while generating new one
    if (result) {
      setPreviousResult(result);
    }
    
    // Reset witty message index when starting new generation
    setCurrentWittyMessageIndex(0);
    
    // Generate witty messages for the current request immediately
    const wittyMessages = await generateWittyMessages(inputValue.trim());
    setCurrentWittyMessages(wittyMessages);

    try {
      console.log(`[DEBUG Frontend] About to generate with session_id: ${sessionId}`);
      
      // Extract reference images from @ mentions in the prompt
      const referenceImages = await extractReferences(inputValue.trim());
      console.log(`[DEBUG Frontend] Found ${referenceImages.length} reference images:`, referenceImages);
      
      const response = await generateContent({
        prompt: inputValue.trim(),
        user_id: userId,
        session_id: sessionId || undefined, // Send session ID for conversational continuity
        quality_priority: 'balanced',
        uploaded_images: uploadedImages.map(img => img.public_url),
        reference_images: referenceImages,
        current_working_video: currentWorkingVideo || undefined // Send working video for video editing
      });

      setResult(response);
      

      
      // Extract session ID from response metadata for future requests
      if (response.metadata?.session_id) {
        setSessionId(response.metadata.session_id);
        console.log('[Frontend] Session ID obtained:', response.metadata.session_id);
      }
      
      // Set working video if this was a video generation/edit
      if (response.success && response.output_url && isVideoUrl(response.output_url)) {
        setCurrentWorkingVideo(response.output_url);
        console.log('[Frontend] Working video set:', response.output_url);
      }
      
      // Clear uploaded images after successful generation (they're now part of the session)
      if (response.success && uploadedImages.length > 0) {
        setUploadedImages([]);
      }
      
      if (!response.success) {
        setError(response.error_message || 'Generation failed');
      } else {
        // Reload XP data from server to get actual balance after deduction (no popup)
        loadXPData();

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
      setCurrentWittyMessages([]); // Clear witty messages when generation completes
    }
  };

  const generateWittyMessages = async (prompt: string, promptType: string = "NEW_IMAGE") => {
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const token = localStorage.getItem('access_token');
      
      console.log('[DEBUG] Generating witty messages for:', prompt);
      
      const response = await fetch(`${baseUrl}/api/v1/generation/generate-witty-messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          user_prompt: prompt,
          prompt_type: promptType,
          context: {
            user_id: userId,
            session_id: sessionId,
            working_image: result?.output_url,
            working_video: currentWorkingVideo,
            uploaded_images: uploadedImages.map(img => img.public_url),
          }
        })
      });
      
      console.log('[DEBUG] Witty messages response status:', response.status);
      
      if (response.ok) {
        const data = await response.json();
        console.log('[DEBUG] Witty messages received:', data.witty_messages);
        return data.witty_messages || [];
      } else {
        console.error('[DEBUG] Witty messages API error:', response.status, response.statusText);
      }
    } catch (error) {
      console.error('Error generating witty messages:', error);
    }
    
    // Fallback messages
    return [
      "Creating something amazing for you",
      "This might take around 30 seconds, but it'll be worth the wait",
      "Your creative vision is coming to life",
      "Working some AI magic here",
      "Almost there! Your masterpiece is being crafted",
      "Just 30 seconds until your creation is ready",
      "The AI is putting the finishing touches on your request",
      "Something special is being generated just for you",
      "Your imagination is becoming reality",
      "The wait will be worth it - this is going to look incredible!"
    ];
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as React.FormEvent);
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
  };

  // Camera functions
  const startCamera = async () => {
    try {
      // Check if navigator.mediaDevices is available
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error('Camera API not supported in this browser')
      }

      // Check if we're in a secure context (HTTPS required for camera access)
      if (!window.isSecureContext) {
        throw new Error('Camera access requires HTTPS. Please use https:// or localhost')
      }

      console.log('Requesting camera access...')
      const mediaStream = await navigator.mediaDevices.getUserMedia({ 
        video: { 
          facingMode: 'user',
          width: { ideal: 640 },
          height: { ideal: 480 }
        } 
      })
      
      console.log('Camera access granted, setting up stream...')
      setStream(mediaStream)
      setShowCamera(true)
      
      // Wait a bit for the modal to render before setting video source
      setTimeout(() => {
        if (videoRef.current) {
          videoRef.current.srcObject = mediaStream
          videoRef.current.onloadedmetadata = () => {
            console.log('Video metadata loaded, camera ready')
          }
        }
      }, 100)
      
    } catch (error) {
      console.error('Failed to access camera:', error)
      
      let errorMessage = 'Failed to access camera. '
      
      if (error instanceof Error) {
        if (error.name === 'NotAllowedError') {
          errorMessage += 'Please allow camera access and try again.'
        } else if (error.name === 'NotFoundError') {
          errorMessage += 'No camera found on this device.'
        } else if (error.name === 'NotSupportedError') {
          errorMessage += 'Camera not supported in this browser.'
        } else if (error.name === 'NotReadableError') {
          errorMessage += 'Camera is already in use by another application.'
        } else if (error.message.includes('HTTPS')) {
          errorMessage += 'Camera access requires HTTPS. Please use https:// or localhost.'
        } else {
          errorMessage += 'Please ensure camera permissions are granted and try again.'
        }
      } else {
        errorMessage += 'Please ensure camera permissions are granted and try again.'
      }
      
      alert(errorMessage)
    }
  }

  const stopCamera = () => {
    if (stream) {
      stream.getTracks().forEach(track => track.stop())
      setStream(null)
    }
    setShowCamera(false)
  }

  const capturePhoto = async () => {
    if (!videoRef.current || !canvasRef.current) return

    const canvas = canvasRef.current
    const video = videoRef.current
    const context = canvas.getContext('2d')
    
    if (!context) return

    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    context.drawImage(video, 0, 0)

    // Convert canvas to blob
    canvas.toBlob(async (blob) => {
      if (!blob) return

      setIsUploading(true)
      try {
        const file = new File([blob], `selfie_${Date.now()}.jpg`, { type: 'image/jpeg' })
        const uploadResult = await uploadImage(file, `selfie_${Date.now()}`)
        
        // Add to uploaded images list (same as regular upload)
        setUploadedImages(prev => [...prev, uploadResult])
        stopCamera()
      } catch (error) {
        console.error('Failed to upload selfie:', error)
        setError(error instanceof Error ? error.message : 'Upload failed')
      } finally {
        setIsUploading(false)
      }
    }, 'image/jpeg', 0.8)
  }

  // Cleanup camera stream when component unmounts
  useEffect(() => {
    return () => {
      if (stream) {
        stream.getTracks().forEach(track => track.stop())
      }
    }
  }, [stream])

  const handleHistoryClick = () => {
    setShowHistory(true);
  };

  const handleReferencesClick = () => {
    setShowReferences(true);
  };

  const handleReferenceSelect = (tag: string) => {
    // Add the @tag to the input
    setInputValue(prev => {
      return prev + (prev ? ' ' : '') + tag;
    });
    setShowReferences(false);
  };

  const handleTagImage = (imageUrl: string) => {
    setImageToTag(imageUrl);
    setShowTagModal(true);
  };

  const handleImageTagged = (tag: string) => {
    // Mark the image as tagged and store the tag mapping locally for immediate UI update
    setTaggedImages(prev => new Set(prev).add(imageToTag));
    setImageTagMap(prev => new Map(prev).set(imageToTag, tag));
    console.log(`Image tagged as @${tag}`, 'Image URL:', imageToTag);
    
    // Refresh the tagged state from database to ensure sync across devices
    loadTaggedImagesState();
  };

  const handleImageMaximize = (imageUrl: string) => {
    setImageToMaximize(imageUrl);
    setShowImageModal(true);
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
      
      // **CRITICAL FIX**: Set this item as the working image/video in the session
      try {
        const sessionId = item.generation_id; // Use generation_id as session_id
        
        if (isVideoUrl(item.output_url)) {
          // Handle video selection
          console.log(`[DEBUG Frontend] Setting working video for session ${sessionId}: ${item.output_url}`);
          setCurrentWorkingVideo(item.output_url);
        } else {
          // Handle image selection
          console.log(`[DEBUG Frontend] About to set working image for session ${sessionId}: ${item.output_url}`);
          
          // Import the API function we'll need
          const { setWorkingImage } = await import('../lib/api');
          
          const result = await setWorkingImage(sessionId, item.output_url, userId);
          console.log(`[DEBUG Frontend] Successfully set working image:`, result);
        }
      } catch (error) {
        console.error('[DEBUG Frontend] Failed to set working image/video in session:', error);
        // Don't throw - continue with the selection even if working item setting fails
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
    setCurrentWorkingVideo(null); // Clear working video
    
    // Clear any active working images by clearing the session
    try {
      if (sessionId) {
        // Import the authenticated API client
        const { clearSession } = await import('../lib/api');
        await clearSession(sessionId);
        console.log('✅ Session cleared successfully');
      }
    } catch (error) {
      console.log('Note: Could not clear session (this is normal if no session exists):', error);
    }
    
    // Force refresh the page state
    setHistoryRefreshTrigger(prev => prev + 1);
  };



  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center p-4">
      <div className="w-full max-w-4xl">
        {/* Header with Logo and User Menu */}
        <div className="flex items-center justify-between mb-8">
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
          <div className="flex-1 flex justify-end items-center space-x-4">
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
                      onClick={() => {
                        router.push('/subscriptions');
                        setShowUserMenu(false);
                      }}
                      className="w-full flex items-center gap-2 p-3 text-left text-gray-300 hover:bg-gray-700 transition-colors"
                    >
                      <Settings className="w-4 h-4" />
                      Account
                    </button>
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

        {/* XP Progress Bar - Under logo, above prompt */}
        {user && (
          <div className="flex justify-center mb-6">
            <XPIndicator
              currentXP={currentXP}
              isGenerating={isGenerating}
            />
          </div>
        )}

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
            {/* Main Input Row */}
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
              <ReferenceInput
                value={inputValue}
                onChange={setInputValue}
                onKeyPress={handleKeyPress}
                placeholder="Let's make something amazing..."
                disabled={isGenerating}
                userId={userId}
                className="bg-transparent text-white placeholder-gray-400 text-lg outline-none disabled:opacity-50"
              />

              {/* Submit Button */}
              <button 
                type="submit"
                disabled={!inputValue.trim() || isGenerating}
                className="bg-cyan-500 hover:bg-cyan-600 disabled:bg-gray-600 disabled:cursor-not-allowed p-2 rounded-lg transition-colors flex-shrink-0"
              >
                {isGenerating ? (
                  <Loader2 className="w-4 h-4 text-white animate-spin" />
                ) : (
                  <Send className="w-4 h-4 text-white" />
                )}
              </button>
            </div>

            {/* Action Icons Row - Below Input */}
            <div className="flex items-center justify-center gap-2 mt-3 pt-3 border-t border-gray-700/30">
              <button 
                type="button"
                onClick={handleStartFresh}
                className="p-2 hover:bg-gray-700/50 rounded-lg transition-colors relative"
                disabled={isGenerating}
                title="Start fresh - Clear all images and start over"
              >
                <RotateCcw className="w-5 h-5 text-gray-400 hover:text-gray-300" />
              </button>
              
              <button 
                type="button"
                onClick={handleReferencesClick}
                className="p-2 hover:bg-gray-700/50 rounded-lg transition-colors relative"
                disabled={isGenerating}
                title="Manage references (@mentions)"
              >
                <Tag className="w-5 h-5 text-gray-400 hover:text-gray-300" />
              </button>
              
              <button 
                type="button"
                onClick={handleHistoryClick}
                className="p-2 hover:bg-gray-700/50 rounded-lg transition-colors relative"
                disabled={isGenerating}
                title="View generation history"
              >
                <History className="w-5 h-5 text-gray-400 hover:text-gray-300" />
              </button>
              
              <button 
                type="button"
                onClick={triggerImageUpload}
                className="p-2 hover:bg-gray-700/50 rounded-lg transition-colors relative"
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
                onClick={() => {
                  console.log('Camera button clicked')
                  startCamera()
                }}
                className="p-2 hover:bg-gray-700/50 rounded-lg transition-colors relative"
                disabled={isGenerating || isUploading || showCamera}
                title="Take selfie"
              >
                <Camera className="w-5 h-5 text-gray-400 hover:text-gray-300" />
              </button>
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
                        className={`text-white rounded-full p-1 ${
                          taggedImages.has(image.public_url)
                            ? 'bg-green-600 hover:bg-green-700'
                            : 'bg-gray-600 hover:bg-gray-700'
                        }`}
                        title={taggedImages.has(image.public_url) ? "Image tagged" : "Tag image"}
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
            <p className="text-gray-400 text-lg">
              {currentWittyMessages.length > 0 
                ? currentWittyMessages[currentWittyMessageIndex] 
                : "Creating something amazing..."}
            </p>

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
                    <p className="text-white text-lg">
                      {currentWittyMessages.length > 0 
                        ? currentWittyMessages[currentWittyMessageIndex] 
                        : "Generating new version..."}
                    </p>
                    <p className="text-gray-400 text-sm">Your current image will be replaced</p>
                  </div>
                </div>
              )}
              
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-white text-xl">
                  {isGenerating && previousResult ? "Current Creation" : "Your Creation"}
                </h3>
                
                {/* Show session info */}
                {sessionId && (result?.image_source_type || currentWorkingVideo) && (
                  <div className="text-xs text-gray-400 flex items-center gap-2">
                    {result?.image_source_type === 'working_image' && (
                      <span className="bg-blue-500/20 text-blue-300 px-2 py-1 rounded">
                        Editing Previous Result
                      </span>
                    )}
                    {result?.image_source_type === 'uploaded' && (
                      <span className="bg-green-500/20 text-green-300 px-2 py-1 rounded">
                        Editing Uploaded Image
                      </span>
                    )}
                    {currentWorkingVideo && (
                      <span className="bg-purple-500/20 text-purple-300 px-2 py-1 rounded">
                        Video Editing Enabled
                      </span>
                    )}
                  </div>
                )}
              </div>
              
              {/* Show current result or previous result while generating */}
              {(result?.success && result?.output_url) ? (
                result.output_url.includes('.mp4') || result.output_url.includes('video') || result.output_url.includes('mock-image-to-video') ? (
                  <div className="relative inline-block">
                    <video
                      src={result.output_url}
                      controls
                      className="max-w-full h-auto max-h-96 rounded-lg mx-auto shadow-lg"
                    >
                      Your browser does not support video playback.
                    </video>
                    {/* Share button overlay for video */}
                    <div className="absolute top-2 right-2">
                      <ShareButton 
                        url={result.output_url}
                        title="Check out this amazing AI-generated video!"
                        isVideo={true}
                        size="sm"
                      />
                    </div>
                  </div>
                ) : (
                  <div className="relative inline-block">
                    <img 
                      src={result.output_url} 
                      alt="Generated content"
                      className="max-w-full h-auto rounded-lg mx-auto shadow-lg cursor-pointer hover:opacity-90 transition-opacity"
                      onClick={() => result.output_url && handleImageMaximize(result.output_url)}
                      title="Click to maximize image"
                    />
                    {/* Action icons overlay */}
                    <div className="absolute top-2 right-2 flex gap-2">
                      <ShareButton 
                        url={result.output_url}
                        title="Check out this amazing AI-generated image!"
                        isVideo={false}
                        size="sm"
                      />
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          console.log('Tagged images:', taggedImages, 'Current URL:', result.output_url, 'Is tagged:', result.output_url ? taggedImages.has(result.output_url) : false);
                          if (result.output_url) {
                            handleTagImage(result.output_url);
                          }
                        }}
                        className={`p-2 text-white rounded-full transition-all opacity-75 hover:opacity-100 shadow-lg ${
                          taggedImages.has(result.output_url) 
                            ? 'bg-green-600 hover:bg-green-700' 
                            : 'bg-gray-600 hover:bg-gray-700'
                        }`}
                        title={taggedImages.has(result.output_url) ? "Image tagged" : "Tag this image"}
                      >
                        <Tag className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                )
              ) : (previousResult?.success && previousResult?.output_url) ? (
                previousResult.output_url.includes('.mp4') || previousResult.output_url.includes('video') || previousResult.output_url.includes('mock-image-to-video') ? (
                  <div className="relative inline-block">
                    <video
                      src={previousResult.output_url}
                      controls
                      className="max-w-full h-auto max-h-96 rounded-lg mx-auto shadow-lg opacity-75"
                    >
                      Your browser does not support video playback.
                    </video>
                    {/* Share button overlay for previous video */}
                    <div className="absolute top-2 right-2">
                      <ShareButton 
                        url={previousResult.output_url}
                        title="Check out this amazing AI-generated video!"
                        isVideo={true}
                        size="sm"
                      />
                    </div>
                  </div>
                ) : (
                  <div className="relative inline-block">
                    <img 
                      src={previousResult.output_url} 
                      alt="Previous generated content"
                      className="max-w-full h-auto rounded-lg mx-auto shadow-lg opacity-75 cursor-pointer hover:opacity-60 transition-opacity"
                      onClick={() => previousResult.output_url && handleImageMaximize(previousResult.output_url)}
                      title="Click to maximize image"
                    />
                    {/* Action icons overlay */}
                    <div className="absolute top-2 right-2 flex gap-2">
                      <ShareButton 
                        url={previousResult.output_url}
                        title="Check out this amazing AI-generated image!"
                        isVideo={false}
                        size="sm"
                      />
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          if (previousResult.output_url) {
                            handleTagImage(previousResult.output_url);
                          }
                        }}
                        className={`p-2 text-white rounded-full transition-all opacity-75 hover:opacity-100 shadow-lg ${
                          taggedImages.has(previousResult.output_url) 
                            ? 'bg-green-600 hover:bg-green-700' 
                            : 'bg-gray-600 hover:bg-gray-700'
                        }`}
                        title={taggedImages.has(previousResult.output_url) ? "Image tagged" : "Tag this image"}
                      >
                        <Tag className="w-4 h-4" />
                      </button>
                    </div>
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
                  taggedImages={taggedImages}
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
          initialTag={imageTagMap.get(imageToTag)}
        />

        {/* Authentication Modal */}
        <AuthModal
          isOpen={showAuthModal}
          onClose={() => setShowAuthModal(false)}
          defaultMode="signin"
        />

        {/* Camera Modal */}
        {showCamera && (
          <div className="fixed inset-0 bg-black/90 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-gray-800 rounded-2xl max-w-md w-full mx-4 p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-white">Take a Selfie</h3>
                <button
                  onClick={stopCamera}
                  className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
                >
                  <X className="w-5 h-5 text-gray-400" />
                </button>
              </div>
              
              <div className="space-y-4">
                <video
                  ref={videoRef}
                  autoPlay
                  playsInline
                  className="w-full h-64 bg-gray-900 rounded-lg object-cover"
                />
                
                <div className="flex gap-2">
                  <button
                    onClick={capturePhoto}
                    disabled={isUploading}
                    className="flex-1 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
                  >
                    {isUploading ? 'Processing...' : 'Capture Photo'}
                  </button>
                  <button
                    onClick={stopCamera}
                    className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Image Maximize Modal */}
        <ImageMaximizeModal
          isOpen={showImageModal}
          onClose={() => setShowImageModal(false)}
          imageUrl={imageToMaximize}
          altText="Maximized working image"
        />

        {/* XP Notification */}
        <XPNotification
          isVisible={xpNotification.show}
          amount={xpNotification.amount}
          type={xpNotification.type}
          reason={xpNotification.reason}
          onComplete={() => setXpNotification(prev => ({ ...prev, show: false }))}
        />

        {/* Hidden canvas for photo capture */}
        <canvas ref={canvasRef} className="hidden" />
      </div>
    </div>
  );
};

export default PerplexityInterface; 