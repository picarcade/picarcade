# Model Pricing Breakdown - PicArcade

*Last Updated: July 2025*

## Overview

This document provides a comprehensive breakdown of AI model costs used in the PicArcade platform. Our system uses **actual model routing logic** with specific models automatically selected for each use case through a sophisticated CSV-based decision matrix.

## Actual Model Usage by Use Case

### Image Generation Use Cases

| Use Case | Actual Model | Provider | Cost | Audio Support | Notes |
|----------|-------------|----------|------|---------------|-------|
| **NEW_IMAGE** | `black-forest-labs/flux-1.1-pro` | Replicate | $0.04/request | ❌ | Default high-quality image generation |
| **NEW_IMAGE_REF** | `runway_gen4_image` | Runway | $0.06/request | ❌ | With reference images or uploads |
| **EDIT_IMAGE** | `black-forest-labs/flux-kontext-max` | Replicate | $0.03/request | ❌ | Basic image editing (working image only) |
| **EDIT_IMAGE_REF** | `runway_gen4_image` | Runway | $0.06/request | ❌ | Face swaps, hair/clothing transfers |
| **EDIT_IMAGE_ADD_NEW** | `runway_gen4_image` | Runway | $0.06/request | ❌ | Adding people/objects to scenes |

### Video Generation Use Cases

| Use Case | Actual Model | Provider | Cost | Duration | Audio Support | Notes |
|----------|-------------|----------|------|----------|---------------|-------|
| **NEW_VIDEO** | `minimax/hailuo-02` | Replicate | $0.05/request | 6s | ❌ | Text-to-video (primary) |
| **NEW_VIDEO_WITH_AUDIO** | `google/veo-3-fast` | Replicate | $0.08/request | Variable | ✅ | Text-to-video with audio |
| **IMAGE_TO_VIDEO** | `gen4_turbo` | Runway | $0.50/request | 5s | ❌ | Image-to-video conversion (improved quality) |
| **IMAGE_TO_VIDEO_WITH_AUDIO** | `google/veo-3-fast` | Replicate | $0.08/request | Variable | ✅ | Image-to-video with audio |
| **EDIT_IMAGE_REF_TO_VIDEO** | `gen4_turbo` | Runway | $0.50/request | 5s | ❌ | Reference-based video (improved quality) |

### Special Routing Rules

| Condition | Override Model | Trigger | Cost Impact |
|-----------|----------------|---------|-------------|
| **Multi-Reference** | `runway_gen4_image` | 2+ reference images | +50% cost vs Flux |
| **Audio Detection** | `google/veo-3-fast` | Audio keywords detected | Most cost-effective audio option |
| **Image-to-Video** | `gen4_turbo` | Working image + video intent | 10x more expensive than text-to-video (50% cost reduction from Gen3A) |

## Actual Model Specifications

### Image Models in Production

#### FLUX 1.1 Pro (`black-forest-labs/flux-1.1-pro`)
- **Use Case**: NEW_IMAGE (standard image generation)
- **Provider**: Replicate
- **Cost**: $0.04 per request
- **Parameters**: aspect_ratio, output_format, output_quality, prompt_upsampling, safety_tolerance, seed
- **Quality Score**: 10/10
- **Speed Score**: 8/10

#### FLUX Kontext Max (`black-forest-labs/flux-kontext-max`)
- **Use Case**: EDIT_IMAGE (basic image editing)
- **Provider**: Replicate
- **Cost**: $0.03 per request (25% cheaper than FLUX 1.1 Pro)
- **Specialty**: Image editing and enhancement
- **Quality Score**: 8/10
- **Speed Score**: 7/10

#### Runway Gen4 Image (`runway_gen4_image`)
- **Use Cases**: NEW_IMAGE_REF, EDIT_IMAGE_REF, EDIT_IMAGE_ADD_NEW
- **Provider**: Runway
- **Cost**: $0.06 per request (50% more expensive than FLUX 1.1 Pro)
- **Specialty**: Reference-based generation, face swaps, multi-image workflows
- **Quality Score**: 9/10
- **Speed Score**: 6/10

### Video Models in Production

#### Minimax Hailuo-02 (`minimax/hailuo-02`)
- **Use Case**: NEW_VIDEO (text-to-video without audio)
- **Provider**: Replicate
- **Cost**: $0.05 per request (most cost-effective video option)
- **Duration**: 6 seconds default
- **Parameters**: prompt, prompt_optimizer, resolution (768p/1080p), duration (6s/10s)
- **Quality Score**: 8.8/10
- **Speed Score**: 10/10 (fastest)
- **Fallback**: `google/veo-3-fast`

#### Google VEO-3 Fast (`google/veo-3-fast`)
- **Use Cases**: NEW_VIDEO_WITH_AUDIO, IMAGE_TO_VIDEO_WITH_AUDIO
- **Provider**: Replicate
- **Cost**: $0.08 per request (60% more expensive than Minimax)
- **Audio Support**: ✅ (only audio-capable model in use)
- **Quality Score**: 8/10
- **Speed Score**: 9/10

#### Runway Gen4 Turbo (`gen4_turbo`)
- **Use Cases**: IMAGE_TO_VIDEO, EDIT_IMAGE_REF_TO_VIDEO
- **Provider**: Runway
- **Cost**: $0.50 per request (5s), $1.00 per request (10s) - 50% cost reduction vs Gen3A
- **Duration**: 5-10 seconds
- **Specialty**: Image-to-video conversion with enhanced character consistency and physics simulation
- **Quality Score**: 10/10
- **Speed Score**: 8/10

## Decision Matrix Logic

### Image Generation Decision Tree

```
No Images → NEW_IMAGE → FLUX 1.1 Pro ($0.04)
Working Image Only → EDIT_IMAGE → FLUX Kontext Max ($0.03)
With References/Uploads → NEW_IMAGE_REF/EDIT_IMAGE_REF → Runway Gen4 ($0.06)
```

### Video Generation Decision Tree

```
Text-to-Video:
  └── Audio Required? 
      ├── Yes → VEO-3 Fast ($0.08)
      └── No → Minimax Hailuo-02 ($0.05)

Image-to-Video:
  └── Audio Required?
      ├── Yes → VEO-3 Fast ($0.08)
      └── No → Runway Gen4 Turbo ($0.50)
```

## Real Cost Analysis

### Cost Per Use Case (Production Data)

| Scenario | Model Selection | Cost | Cost vs Cheapest |
|----------|-----------------|------|------------------|
| "Create a cat" | FLUX 1.1 Pro | $0.04 | Base |
| "Edit this image" | FLUX Kontext Max | $0.03 | -25% |
| "Use @reference style" | Runway Gen4 | $0.06 | +50% |
| "Make a video" | Minimax Hailuo-02 | $0.05 | +25% |
| "Video with music" | VEO-3 Fast | $0.08 | +100% |
| "Animate this image" | Runway Gen3A | $0.95 | +2275% |

### Monthly Cost Estimates

| Usage Level | Use Case Mix | Monthly Cost |
|-------------|--------------|--------------|
| **Light** (100 requests) | 70% images, 30% videos | $4-7 |
| **Medium** (1,000 requests) | 60% images, 40% videos | $40-70 |
| **Heavy** (10,000 requests) | 50% images, 50% videos | $400-700 |
| **Enterprise** (100,000 requests) | Custom mix | $4,000-70,000 |

## Provider Analysis

### Replicate Usage (67% of models)
- **Models**: FLUX 1.1 Pro, FLUX Kontext Max, Minimax Hailuo-02, VEO-3 Fast
- **Strengths**: Cost-effective, reliable, variety
- **Cost Range**: $0.03 - $0.08 per request
- **Best For**: Standard generation, cost optimization

### Runway Usage (33% of models)
- **Models**: Runway Gen4 Image, Gen4 Turbo
- **Strengths**: Highest quality, reference handling, enhanced physics simulation
- **Cost Range**: $0.06 - $1.00 per request
- **Best For**: Professional results, complex workflows

## Fallback & Override Logic

### Automatic Fallbacks (Production)
1. **Minimax Hailuo-02 fails** → VEO-3 Fast (for text-to-video)
2. **2+ references detected** → Force Runway Gen4 Image
3. **Audio keywords detected** → Force VEO-3 Fast

### Cost Impact of Fallbacks
- **Minimax → VEO-3**: +60% cost increase
- **Multi-reference override**: +50% cost increase
- **Audio override**: Varies based on original model

## Optimization Strategies

### Cost Optimization Tips
1. **Use FLUX Kontext Max** for simple edits (-25% vs FLUX 1.1 Pro)
2. **Avoid image-to-video** unless necessary (19x more expensive)
3. **Use Minimax for text-to-video** without audio (cheapest video option)
4. **Batch similar requests** to avoid reference overrides

### Quality Optimization
1. **Use Runway models** for professional results (+50% cost, +quality)
2. **Include audio** for immersive video content (+60% cost)
3. **Use references** for consistent styling (+50% cost, +accuracy)

## 2025 Market Context

### Competitive Positioning
- **Minimax Hailuo-02**: Most cost-effective video at $0.05/request
- **VEO-3 Fast**: Only audio-capable model in production use
- **Runway Gen3A**: Premium image-to-video despite high cost
- **FLUX models**: Balanced quality/cost for image generation

### Industry Trends
- **Video costs 10-20x higher** than image generation
- **Audio capability** commands premium pricing
- **Reference-based models** cost 50% more but deliver higher accuracy
- **Speed vs Quality** trade-offs clearly reflected in pricing

---

*This analysis is based on actual model routing logic found in `config/model_routing.yaml`, `app/services/simplified_flow_service.py`, and production generation endpoints as of July 2025.*

*Cost estimates reflect internal configuration pricing and may not include provider markup or volume discounts.* 