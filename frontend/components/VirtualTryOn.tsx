import React, { useState } from 'react';
import { Upload, Link2, User, ShoppingBag, Loader2, AlertCircle, CheckCircle } from 'lucide-react';

interface VirtualTryOnProps {
  onSubmit: (prompt: string) => void;
  isGenerating: boolean;
  availableReferences: Array<{ tag: string; image_url: string }>;
}

export const VirtualTryOn: React.FC<VirtualTryOnProps> = ({
  onSubmit,
  isGenerating,
  availableReferences
}) => {
  const [selectedReference, setSelectedReference] = useState<string>('');
  const [clothingUrl, setClothingUrl] = useState<string>('');
  const [isUrlValid, setIsUrlValid] = useState<boolean | null>(null);
  const [urlError, setUrlError] = useState<string>('');

  // Validate URL in real-time
  const validateUrl = (url: string) => {
    if (!url) {
      setIsUrlValid(null);
      setUrlError('');
      return;
    }

    try {
      new URL(url);
      
      // Check if it looks like an image URL
      const imageExtensions = ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp'];
             const imageDomains = [
         'imgur.com', 'unsplash.com', 'shopify.com', 'amazon.com',
         'zara.com', 'adidas.com', 'nike.com', 'cdn.', 'images.',
         'myer.com.au', 'davidjones.com', 'theiconic.com.au',
         'hm.com', 'uniqlo.com', 'gap.com', 'asos.com', 'target.com'
       ];
      
             const urlLower = url.toLowerCase();
       const hasImageExtension = imageExtensions.some(ext => urlLower.includes(ext));
       const hasImageDomain = imageDomains.some(domain => urlLower.includes(domain));
       
       // Also check for e-commerce patterns
       const ecommercePatterns = ['/product/', '/p/', '/item/', 'shop', 'store'];
       const hasEcommercePattern = ecommercePatterns.some(pattern => urlLower.includes(pattern));
       
       if (hasImageExtension || hasImageDomain || hasEcommercePattern) {
         setIsUrlValid(true);
         setUrlError('');
       } else {
         setIsUrlValid(false);
         setUrlError('URL should be from a clothing website or direct image link');
       }
    } catch {
      setIsUrlValid(false);
      setUrlError('Please enter a valid URL starting with http:// or https://');
    }
  };

  const handleUrlChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const url = e.target.value;
    setClothingUrl(url);
    validateUrl(url);
  };

  const handleSubmit = () => {
    if (!selectedReference) {
      alert('Please select a reference person');
      return;
    }
    
    if (!clothingUrl) {
      alert('Please enter a clothing URL');
      return;
    }

    if (isUrlValid === false) {
      alert('Please enter a valid image URL');
      return;
    }

    // Create the virtual try-on prompt
    const prompt = `Put @${selectedReference} in this outfit: ${clothingUrl}`;
    onSubmit(prompt);
  };

  const getQuickPrompts = () => [
    `Put @${selectedReference} in this dress`,
    `Show @${selectedReference} wearing this shirt`,
    `@${selectedReference} try on this outfit`,
    `Make @${selectedReference} wear this jacket`
  ];

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
      <div className="flex items-center gap-2 mb-4">
        <ShoppingBag className="h-5 w-5 text-purple-600" />
        <h3 className="text-lg font-semibold text-gray-900">Virtual Try-On</h3>
      </div>
      
      <div className="space-y-4">
        {/* Reference Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            <User className="inline h-4 w-4 mr-1" />
            Choose Reference Person
          </label>
          {availableReferences.length > 0 ? (
            <div className="grid grid-cols-2 gap-2">
              {availableReferences.map((ref) => (
                <button
                  key={ref.tag}
                  onClick={() => setSelectedReference(ref.tag)}
                  className={`flex items-center gap-2 p-2 rounded-lg border-2 transition-colors ${
                    selectedReference === ref.tag
                      ? 'border-purple-500 bg-purple-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <img
                    src={ref.image_url}
                    alt={`@${ref.tag}`}
                    className="w-8 h-8 rounded-full object-cover"
                  />
                  <span className="text-sm font-medium">@{ref.tag}</span>
                </button>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              <User className="h-12 w-12 mx-auto mb-2 text-gray-300" />
              <p>No reference people available.</p>
              <p className="text-sm">Create some @references first!</p>
            </div>
          )}
        </div>

        {/* Clothing URL Input */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            <Link2 className="inline h-4 w-4 mr-1" />
            Clothing Image URL
          </label>
          <div className="relative">
            <input
              type="url"
              value={clothingUrl}
              onChange={handleUrlChange}
              placeholder="https://example.com/dress.jpg"
              className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500 pr-10 ${
                isUrlValid === false ? 'border-red-300' : 
                isUrlValid === true ? 'border-green-300' : 'border-gray-300'
              }`}
            />
            {isUrlValid === true && (
              <CheckCircle className="absolute right-3 top-2.5 h-5 w-5 text-green-500" />
            )}
            {isUrlValid === false && (
              <AlertCircle className="absolute right-3 top-2.5 h-5 w-5 text-red-500" />
            )}
          </div>
          {urlError && (
            <p className="mt-1 text-sm text-red-600">{urlError}</p>
          )}
                     <p className="mt-1 text-xs text-gray-500">
             Paste a product page URL or direct image link from clothing websites
           </p>
        </div>

        {/* Quick Prompt Suggestions */}
        {selectedReference && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Quick Prompts
            </label>
            <div className="grid grid-cols-2 gap-2">
              {getQuickPrompts().map((prompt, index) => (
                <button
                  key={index}
                  onClick={() => {
                    if (clothingUrl) {
                      onSubmit(`${prompt}: ${clothingUrl}`);
                    } else {
                      alert('Please enter a clothing URL first');
                    }
                  }}
                  className="text-left p-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Submit Button */}
        <button
          onClick={handleSubmit}
          disabled={isGenerating || !selectedReference || !clothingUrl || isUrlValid === false}
          className={`w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
            isGenerating || !selectedReference || !clothingUrl || isUrlValid === false
              ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
              : 'bg-purple-600 text-white hover:bg-purple-700'
          }`}
        >
          {isGenerating ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Generating Try-On...
            </>
          ) : (
            <>
              <ShoppingBag className="h-4 w-4" />
              Try On Outfit
            </>
          )}
        </button>
      </div>

      {/* Example URLs */}
      <div className="mt-6 pt-4 border-t border-gray-100">
        <h4 className="text-sm font-medium text-gray-700 mb-2">Example URLs:</h4>
                 <div className="space-y-1 text-xs text-gray-500">
           <p>• Australian stores: myer.com.au, davidjones.com, theiconic.com.au</p>
           <p>• Global brands: zara.com, h&m.com, uniqlo.com, gap.com</p>
           <p>• Shopping sites: amazon.com, asos.com, target.com</p>
           <p>• Direct image links ending in .jpg, .png, .webp</p>
         </div>
      </div>
    </div>
  );
}; 