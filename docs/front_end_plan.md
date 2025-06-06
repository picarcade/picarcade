# Pictures Frontend Implementation Guide

## Overview

This guide provides detailed instructions for implementing the Pictures frontend - a modern, responsive UI for AI-powered image and video generation with intelligent model routing.

## Tech Stack
- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Icons**: Lucide React
- **HTTP Client**: Axios
- **State Management**: React useState/useEffect

## Project Structure

```
frontend/
├── app/
│   ├── layout.tsx              # Root layout with global styles
│   ├── page.tsx                # Main application page
│   ├── globals.css             # Global CSS with Tailwind
│   ├── components/
│   │   ├── GenerationForm.tsx  # Main prompt input and controls
│   │   ├── GenerationResult.tsx # Display generation results
│   │   ├── GenerationHistory.tsx # History sidebar
│   │   └── LoadingSpinner.tsx  # Reusable loading component
│   ├── lib/
│   │   └── api.ts              # API client functions
│   └── types.ts                # TypeScript interfaces
├── next.config.js              # Next.js configuration
├── tailwind.config.js          # Tailwind configuration
└── package.json                # Dependencies
```

## Design System

### Brand Colors
```css
/* Primary Colors */
--primary: #9333EA        /* Purple */
--primary-light: #A855F7
--primary-dark: #7C3AED

/* Accent Colors */
--accent: #EC4899         /* Pink */
--accent-light: #F472B6
--accent-dark: #DB2777

/* Neutral Colors */
--gray-50: #F9FAFB
--gray-100: #F3F4F6
--gray-600: #4B5563
--gray-900: #111827
```

### Typography
- **Headers**: Inter font, bold weights
- **Body**: Inter font, regular/medium weights
- **Code/IDs**: Mono font for generation IDs

### Layout Principles
- **Grid-based**: 3-column layout (form, results, history)
- **Responsive**: Mobile-first design
- **Card-based**: White cards with shadows for content sections
- **Purple-pink gradient**: For branding and CTAs

## Core Components Implementation

### 1. Main Layout (`app/layout.tsx`)

```typescript
export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
        <div className="container mx-auto px-4 py-8">
          <header className="text-center mb-12">
            <div className="flex items-center justify-center gap-3 mb-4">
              <div className="w-12 h-12 bg-gradient-to-br from-purple-600 to-pink-600 rounded-xl flex items-center justify-center">
                <span className="text-white font-bold text-xl">P</span>
              </div>
              <h1 className="text-4xl font-bold text-gray-900">Pictures</h1>
            </div>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              Create stunning images and videos with AI-powered intelligent routing
            </p>
          </header>
          {children}
        </div>
      </body>
    </html>
  )
}
```

### 2. Main Page (`app/page.tsx`)

**Key Features:**
- State management for current generation
- Real-time updates between components
- Error handling and loading states

```typescript
'use client'

export default function Home() {
  const [currentGeneration, setCurrentGeneration] = useState<GenerationResponse | null>(null)
  const [isGenerating, setIsGenerating] = useState(false)
  const [refreshHistory, setRefreshHistory] = useState(0)

  const handleGenerationComplete = (result: GenerationResponse) => {
    setCurrentGeneration(result)
    setIsGenerating(false)
    setRefreshHistory(prev => prev + 1) // Trigger history refresh
  }

  const handleGenerationStart = () => {
    setIsGenerating(true)
    setCurrentGeneration(null)
  }

  return (
    <div className="grid lg:grid-cols-3 gap-8">
      {/* Generation Form - 2/3 width */}
      <div className="lg:col-span-2">
        <GenerationForm 
          onGenerationStart={handleGenerationStart}
          onGenerationComplete={handleGenerationComplete}
          isGenerating={isGenerating}
        />
        
        {/* Generation Result */}
        {(currentGeneration || isGenerating) && (
          <div className="mt-8">
            <GenerationResult 
              result={currentGeneration} 
              isGenerating={isGenerating}
            />
          </div>
        )}
      </div>

      {/* History Sidebar - 1/3 width */}
      <div className="lg:col-span-1">
        <GenerationHistory refreshTrigger={refreshHistory} />
      </div>
    </div>
  )
}
```

### 3. Generation Form (`app/components/GenerationForm.tsx`)

**Key Features:**
- Large textarea for prompts
- Quality priority buttons with icons
- Real-time character count
- Smart placeholder text
- Loading states with spinner

```typescript
export default function GenerationForm({ 
  onGenerationStart, 
  onGenerationComplete, 
  isGenerating 
}: GenerationFormProps) {
  const [prompt, setPrompt] = useState('')
  const [qualityPriority, setQualityPriority] = useState<'speed' | 'balanced' | 'quality'>('balanced')
  const [userId] = useState(() => `user_${Math.random().toString(36).substr(2, 9)}`)

  const qualityOptions = [
    { 
      value: 'speed', 
      label: 'Speed', 
      icon: Zap, 
      description: 'Fast generation, good quality',
      time: '~15s'
    },
    { 
      value: 'balanced', 
      label: 'Balanced', 
      icon: Gauge, 
      description: 'Optimal speed/quality balance',
      time: '~30s'
    },
    { 
      value: 'quality', 
      label: 'Quality', 
      icon: Crown, 
      description: 'Best quality, slower generation',
      time: '~60s'
    }
  ] as const

  return (
    <div className="bg-white rounded-xl shadow-lg p-6">
      <h2 className="text-2xl font-semibold text-gray-900 mb-6 flex items-center gap-2">
        <Wand2 className="w-6 h-6 text-purple-600" />
        Create Content
      </h2>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Prompt Input */}
        <div>
          <label htmlFor="prompt" className="block text-sm font-medium text-gray-700 mb-2">
            Describe what you want to create
          </label>
          <textarea
            id="prompt"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="A beautiful sunset over mountains, cinematic quality..."
            className="w-full h-32 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none"
            disabled={isGenerating}
          />
          <div className="mt-2 flex justify-between text-sm text-gray-500">
            <span>Be specific for better results</span>
            <span>{prompt.length}/500</span>
          </div>
        </div>

        {/* Quality Priority */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-3">
            Quality Priority
          </label>
          <div className="grid grid-cols-3 gap-3">
            {qualityOptions.map(({ value, label, icon: Icon, description, time }) => (
              <button
                key={value}
                type="button"
                onClick={() => setQualityPriority(value)}
                className={`p-4 border-2 rounded-lg transition-all ${
                  qualityPriority === value
                    ? 'border-purple-500 bg-purple-50 text-purple-700'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
                disabled={isGenerating}
              >
                <Icon className="w-6 h-6 mx-auto mb-2" />
                <div className="text-sm font-medium">{label}</div>
                <div className="text-xs text-gray-500 mt-1">{description}</div>
                <div className="text-xs text-purple-600 mt-1">{time}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={!prompt.trim() || isGenerating}
          className="w-full bg-gradient-to-r from-purple-600 to-pink-600 text-white py-3 px-6 rounded-lg font-medium transition-all hover:from-purple-700 hover:to-pink-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {isGenerating ? (
            <>
              <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Generating...
            </>
          ) : (
            <>
              <Wand2 className="w-5 h-5" />
              Generate Content
            </>
          )}
        </button>
      </form>
    </div>
  )
}
```

### 4. Generation Result (`app/components/GenerationResult.tsx`)

**Key Features:**
- Loading state with animated placeholder
- Image/video display with proper sizing
- Action buttons (view full size, copy URL, save)
- Metadata display (model used, time, etc.)
- Error state handling

```typescript
export default function GenerationResult({ result, isGenerating }: GenerationResultProps) {
  const [imageLoaded, setImageLoaded] = useState(false)

  if (isGenerating) {
    return (
      <div className="bg-white rounded-xl shadow-lg p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-8 h-8 border-2 border-purple-600 border-t-transparent rounded-full animate-spin" />
          <h3 className="text-xl font-semibold text-gray-900">Generating Content...</h3>
        </div>
        
        {/* Animated Placeholder */}
        <div className="space-y-3">
          <div className="h-4 bg-gray-200 rounded animate-pulse" />
          <div className="h-4 bg-gray-200 rounded animate-pulse w-3/4" />
          <div className="h-64 bg-gray-200 rounded animate-pulse" />
        </div>
        
        <div className="mt-4 text-sm text-gray-600">
          ✨ AI is creating your content with intelligent model selection...
        </div>
      </div>
    )
  }

  if (!result) return null

  return (
    <div className="bg-white rounded-xl shadow-lg p-6">
      <div className="flex items-center gap-3 mb-4">
        {result.success ? (
          <CheckCircle className="w-8 h-8 text-green-600" />
        ) : (
          <XCircle className="w-8 h-8 text-red-600" />
        )}
        <h3 className="text-xl font-semibold text-gray-900">
          {result.success ? 'Generation Complete!' : 'Generation Failed'}
        </h3>
      </div>

      {result.success && result.output_url ? (
        <div className="space-y-4">
          {/* Generated Content */}
          <div className="relative bg-gray-100 rounded-lg overflow-hidden">
            {result.output_url.includes('.mp4') || result.output_url.includes('video') ? (
              <video
                src={result.output_url}
                controls
                className="w-full h-auto max-h-96 object-contain"
              >
                Your browser does not support video playback.
              </video>
            ) : (
              <div className="relative">
                <Image
                  src={result.output_url}
                  alt="Generated content"
                  width={800}
                  height={600}
                  className="w-full h-auto max-h-96 object-contain"
                  onLoad={() => setImageLoaded(true)}
                />
                {!imageLoaded && (
                  <div className="absolute inset-0 bg-gray-200 animate-pulse flex items-center justify-center">
                    <Eye className="w-8 h-8 text-gray-400" />
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <div className="flex gap-2">
            <button
              onClick={() => window.open(result.output_url, '_blank')}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <Eye className="w-4 h-4" />
              View Full Size
            </button>
            <button
              onClick={() => navigator.clipboard.writeText(result.output_url!)}
              className="flex items-center gap-2 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
            >
              <Copy className="w-4 h-4" />
              Copy URL
            </button>
            <button
              onClick={() => {/* Future: Save to references */}}
              className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
            >
              <Save className="w-4 h-4" />
              Save
            </button>
          </div>

          {/* Metadata */}
          <div className="bg-gray-50 rounded-lg p-4 space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">Model Used:</span>
              <span className="font-medium">{result.model_used}</span>
            </div>
            {result.execution_time && (
              <div className="flex justify-between">
                <span className="text-gray-600">Generation Time:</span>
                <span className="font-medium flex items-center gap-1">
                  <Clock className="w-4 h-4" />
                  {result.execution_time.toFixed(1)}s
                </span>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-gray-600">Generation ID:</span>
              <span className="font-mono text-xs">{result.generation_id}</span>
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">
            {result.error_message || 'An unknown error occurred during generation.'}
          </p>
        </div>
      )}
    </div>
  )
}
```

### 5. History Sidebar (`app/components/GenerationHistory.tsx`)

**Key Features:**
- Real-time history updates
- Clickable history items
- Success/failure indicators
- Model badges
- Time stamps ("2m ago")

```typescript
export default function GenerationHistory({ refreshTrigger }: GenerationHistoryProps) {
  const [history, setHistory] = useState<HistoryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [userId] = useState(() => `user_${Math.random().toString(36).substr(2, 9)}`)

  const formatTimeAgo = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000)

    if (diffInSeconds < 60) return 'Just now'
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`
    if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`
    return `${Math.floor(diffInSeconds / 86400)}d ago`
  }

  return (
    <div className="bg-white rounded-xl shadow-lg p-6">
      <h3 className="text-xl font-semibold text-gray-900 mb-4 flex items-center gap-2">
        <History className="w-5 h-5 text-gray-600" />
        Recent Generations
      </h3>

      {loading ? (
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="animate-pulse">
              <div className="h-4 bg-gray-200 rounded w-3/4 mb-2" />
              <div className="h-3 bg-gray-200 rounded w-1/2" />
            </div>
          ))}
        </div>
      ) : history.length === 0 ? (
        <div className="text-center py-8">
          <Wand2 className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-500">No generations yet</p>
          <p className="text-sm text-gray-400">Your history will appear here</p>
        </div>
      ) : (
        <div className="space-y-3 max-h-96 overflow-y-auto">
          {history.map((item) => (
            <div
              key={item.generation_id}
              className="border border-gray-200 rounded-lg p-3 hover:bg-gray-50 transition-colors cursor-pointer"
              onClick={() => item.output_url && window.open(item.output_url, '_blank')}
            >
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0 mt-1">
                  {item.success === 'success' ? (
                    <CheckCircle className="w-4 h-4 text-green-600" />
                  ) : (
                    <XCircle className="w-4 h-4 text-red-600" />
                  )}
                </div>
                
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-900 line-clamp-2 mb-1">
                    {item.prompt}
                  </p>
                  
                  <div className="flex items-center gap-2 text-xs text-gray-500">
                    <span className="bg-gray-100 px-2 py-1 rounded">
                      {item.model_used?.replace(/_/g, ' ')}
                    </span>
                    
                    {item.execution_time && (
                      <div className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {(item.execution_time / 1000).toFixed(1)}s
                      </div>
                    )}
                    
                    <span>{formatTimeAgo(item.created_at)}</span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
```

## API Integration (`app/lib/api.ts`)

```typescript
const API_BASE_URL = process.env.NODE_ENV === 'production' 
  ? 'https://your-api-domain.com' 
  : 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000, // 5 minutes for generation requests
})

export const generateContent = async (request: GenerationRequest): Promise<GenerationResponse> => {
  try {
    const response = await api.post('/api/v1/generation/generate', request)
    return response.data
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(error.response?.data?.detail || error.message)
    }
    throw error
  }
}

export const getUserHistory = async (userId: string, limit: number = 20): Promise<HistoryItem[]> => {
  try {
    const response = await api.get(`/api/v1/generation/history/${userId}?limit=${limit}`)
    return response.data
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(error.response?.data?.detail || error.message)
    }
    throw error
  }
}
```

## TypeScript Interfaces (`app/types.ts`)

```typescript
export interface GenerationRequest {
  prompt: string
  user_id: string
  quality_priority: 'speed' | 'balanced' | 'quality'
  additional_params?: Record<string, any>
}

export interface GenerationResponse {
  success: boolean
  generation_id: string
  output_url?: string
  model_used?: string
  execution_time?: number
  error_message?: string
  metadata?: Record<string, any>
}

export interface HistoryItem {
  generation_id: string
  prompt: string
  model_used: string
  success: string
  output_url?: string
  created_at: string
  execution_time?: number
}
```

## Configuration Files

### `next.config.js`
```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    domains: ['replicate.delivery', 'runway.com', 'localhost'],
  },
}

module.exports = nextConfig
```

### `tailwind.config.js`
```javascript
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#faf5ff',
          500: '#9333ea',
          600: '#7c3aed',
          700: '#6d28d9',
        },
        accent: {
          500: '#ec4899',
          600: '#db2777',
        }
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
    },
  },
  plugins: [],
}
```

## Implementation Checklist

### Phase 1: Basic Structure
- [ ] Set up Next.js project with TypeScript
- [ ] Install dependencies (axios, lucide-react, etc.)
- [ ] Create basic layout with Pictures branding
- [ ] Implement GenerationForm component
- [ ] Add API client functions

### Phase 2: Core Features
- [ ] Implement GenerationResult component
- [ ] Add GenerationHistory sidebar
- [ ] Connect all components with state management
- [ ] Add loading states and error handling
- [ ] Test full generation flow

### Phase 3: Polish & UX
- [ ] Add responsive design for mobile
- [ ] Implement proper image/video display
- [ ] Add copy-to-clipboard functionality
- [ ] Enhance loading animations
- [ ] Add keyboard shortcuts (Enter to submit)

### Phase 4: Advanced Features
- [ ] Add generation queue for multiple requests
- [ ] Implement save/favorite functionality
- [ ] Add generation sharing features
- [ ] Create settings panel
- [ ] Add analytics tracking

## Testing Strategy

1. **Component Testing**: Test each component in isolation
2. **Integration Testing**: Test API connections and data flow
3. **User Journey Testing**: Complete generation workflow
4. **Responsive Testing**: Mobile and desktop layouts
5. **Error Handling**: Network failures, API errors, validation

## Performance Considerations

- **Image Optimization**: Use Next.js Image component
- **Lazy Loading**: Load history items progressively
- **Request Debouncing**: Prevent duplicate API calls
- **Caching**: Cache API responses where appropriate
- **Bundle Size**: Tree-shake unused dependencies

This comprehensive guide provides everything needed to build a beautiful, functional frontend for Pictures that showcases the intelligent model routing and provides an excellent user experience.