# Sprint 1: AI Intent Classification System

## Overview

Sprint 1 implements a basic AI-powered intent classification system that enhances your existing workflow detection with OpenAI GPT-4o-mini. This system provides more accurate workflow detection and optimal model selection while maintaining full backward compatibility.

## ✨ New Features

### 🤖 AI Intent Classification
- **Intelligent workflow detection** using OpenAI GPT-4o-mini
- **9 distinct workflow types** with specialized model mappings
- **Fallback to pattern matching** when AI is unavailable
- **Simple in-memory caching** for performance

### 🎯 Enhanced Model Selection
- **FLUX Kontext Apps integration** for specialized workflows
- **Video generation optimization** with Google Veo 3, LTX Video, Minimax
- **Cost-aware model selection** with user preferences
- **Quality vs speed preferences** (speed/balanced/quality)

### 📊 Comparison & Testing
- **Side-by-side comparison** of AI vs existing system
- **Performance metrics** tracking
- **A/B testing capability** for validation

## 🚀 Quick Start

### 1. Install Dependencies
The system uses existing dependencies - no additional packages needed for Sprint 1.

### 2. Environment Variables
Ensure your `.env` has the OpenAI API key:
```bash
OPENAI_API_KEY=your_openai_api_key_here
```

### 3. Start the Server
```bash
uvicorn app.main:app --reload
```

### 4. Test the Implementation
```bash
# Run the comprehensive test suite
python test_sprint1.py

# Or test individual components
python -c "
import asyncio
from app.services.intent_classifier import IntentClassifier

async def test():
    classifier = IntentClassifier()
    result = await classifier.classify_intent('change my hair to blonde')
    print(f'Workflow: {result.workflow_type}')
    print(f'Confidence: {result.confidence}')

asyncio.run(test())
"
```

## 📡 API Endpoints

### Enhanced Processing
```bash
POST /api/v1/enhanced/process
{
  "prompt": "change my hair to blonde with bangs",
  "working_image_url": "https://example.com/image.jpg",
  "user_preferences": {"quality": "balanced"},
  "use_ai_classification": true
}
```

### AI vs Existing Comparison
```bash
POST /api/v1/enhanced/compare
{
  "prompt": "create a video of sunset with music",
  "use_ai_classification": true
}
```

### Performance Metrics
```bash
GET /api/v1/enhanced/metrics
```

## 🎯 Workflow Types

| Workflow Type | Use Case | Primary Model |
|---------------|----------|---------------|
| `image_generation` | Create new images | `black-forest-labs/flux-1.1-pro` |
| `hair_styling` | Change hair color/style | `flux-kontext-apps/change-haircut` |
| `reference_styling` | Celebrity/event styling, virtual try-on | `flux-kontext-apps/multi-image-kontext-max` |
| `image_editing` | Modify existing images | `zsxkib/flux-kontext-pro` |
| `image_enhancement` | Improve image quality | `flux-kontext-apps/restore-image` |
| `style_transfer` | Apply artistic styles | `flux-kontext-apps/cartoonify` |
| `video_generation` | Premium video with audio | `google/veo-3` |
| `image_to_video` | Animate existing images | `lightricks/ltx-video` |
| `text_to_video` | Cost-effective video | `minimax/video-01` |

## 🧪 Testing Examples

### Hair Styling Detection
```bash
curl -X POST http://localhost:8000/api/v1/enhanced/process \
  -H "Content-Type: application/json" \
  -d '{"prompt": "change my hair to blonde with bangs"}'
```

Expected: `hair_styling` workflow with `flux-kontext-apps/change-haircut`

### Video Generation Detection
```bash
curl -X POST http://localhost:8000/api/v1/enhanced/process \
  -H "Content-Type: application/json" \
  -d '{"prompt": "create a cinematic video with orchestra music"}'
```

Expected: `video_generation` workflow with `google/veo-3`

### Virtual Try-on Detection
```bash
curl -X POST http://localhost:8000/api/v1/enhanced/process \
  -H "Content-Type: application/json" \
  -d '{"prompt": "put @sarah in this red dress"}'
```

Expected: `reference_styling` workflow with `flux-kontext-apps/multi-image-kontext-max`

## 📈 Performance Metrics

The system tracks:
- **Total classifications** processed
- **Cache hit rate** for performance optimization
- **Error rate** and fallback usage
- **Processing time** per classification
- **AI vs existing system** comparison results

## 🔄 Integration with Existing System

Sprint 1 maintains **full backward compatibility**:

- ✅ Existing frontend works unchanged
- ✅ Existing API endpoints remain functional
- ✅ Graceful fallback to existing system on errors
- ✅ Side-by-side comparison for validation

## 🐛 Troubleshooting

### Common Issues

1. **OpenAI API Key Missing**
   ```
   Error: OpenAI API key not found
   Solution: Set OPENAI_API_KEY in .env file
   ```

2. **Import Errors**
   ```
   Error: ModuleNotFoundError
   Solution: Ensure you're in the correct directory and dependencies are installed
   ```

3. **Authentication Errors**
   ```
   Error: 401 Unauthorized
   Solution: The test script uses placeholder auth - implement proper authentication
   ```

## 📋 Next Steps (Sprint 2)

1. **Enhanced Model Mappings** with virtual try-on support
2. **Web Search Integration** for celebrity/event styling
3. **Improved Workflow Detection** patterns
4. **Basic Video Workflow** support

## 🏗️ Architecture

```
Enhanced Workflow Service
├── Intent Classifier (AI-powered)
│   ├── GPT-4o-mini classification
│   ├── Pattern-based fallback
│   └── Simple in-memory cache
├── Model Selector
│   ├── FLUX Kontext Apps mapping
│   ├── Video model optimization
│   └── User preference handling
└── Reference Integration
    ├── Existing reference service
    ├── Working image handling
    └── Prompt enhancement
```

This Sprint 1 implementation provides immediate value through better workflow detection while laying the foundation for advanced features in future sprints. 