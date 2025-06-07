export interface GenerationRequest {
  prompt: string
  user_id: string
  session_id?: string  // Session ID for conversational continuity
  quality_priority: 'speed' | 'balanced' | 'quality'
  uploaded_images?: string[]  // Array of image URLs
  current_working_image?: string  // Current working image URL
  additional_params?: Record<string, any>
}

export interface GenerationResponse {
  success: boolean
  generation_id: string
  output_url?: string
  model_used?: string
  execution_time?: number
  error_message?: string
  input_image_used?: string  // URL of input image that was edited
  image_source_type?: string  // "uploaded", "working_image", or null
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

export interface GenerationFormProps {
  onGenerationStart: () => void;
  onGenerationComplete: (result: GenerationResponse) => void;
  isGenerating: boolean;
}

export interface GenerationResultProps {
  result: GenerationResponse | null;
  isGenerating: boolean;
}

export interface GenerationHistoryProps {
  refreshTrigger: number;
  userId: string;
  onSelectImage?: (item: HistoryItem) => void;
}

export interface UploadResponse {
  success: boolean
  file_path: string
  public_url: string
  filename: string
  content_type: string
  message: string
} 