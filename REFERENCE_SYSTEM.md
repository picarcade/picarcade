# @ Reference System

## Overview

The @ reference system allows users to mention tagged images in their prompts by typing `@` followed by the tag name. This enables users to reference previously tagged images in their generation requests.

## Features

### 1. Auto-complete Dropdown
- When users type `@` in the prompt input, a dropdown appears with available references
- Users can type to filter the references by tag name
- Keyboard navigation with arrow keys, Enter to select, Escape to close
- Click to select a reference

### 2. Visual Indicators
- Valid references show a purple indicator with count in the input field
- References in the dropdown show thumbnail previews
- Invalid @ mentions (references that don't exist) are handled gracefully

### 3. Integration with Generation
- @ references are automatically resolved to their corresponding images
- Reference images are sent to the backend as part of the generation request
- The prompt maintains the @ mentions for context

## Implementation Details

### Components
- `ReferenceInput`: Main input component that handles @ mention detection and dropdown
- `ReferenceDropdown`: Dropdown component showing available references with thumbnails
- Modified `PerplexityInterface`: Integrates the new input and processes references

### Workflow
1. User types `@` in the prompt input
2. System detects the @ symbol and shows dropdown with all available references
3. User can continue typing to filter references or select from the dropdown
4. Selected reference is inserted as `@tagname` in the prompt
5. When generating, the system:
   - Parses @ mentions from the prompt
   - Resolves them to reference images
   - Includes both the prompt and reference images in the generation request

### API Integration
- Uses existing `getUserReferences()` API to fetch available references
- Sends `reference_images` array in generation requests
- Each reference includes the image URI and tag name

## Usage Examples

### Basic Usage
```
Generate a portrait like @hero but in a forest setting
```

### Multiple References
```
Create a scene with @castle in the background and @dragon flying overhead
```

### Filtering References
- Type `@h` to see all references starting with 'h'
- Type `@hero` to find exact matches

### Keyboard Shortcuts
- `↑/↓` - Navigate dropdown options
- `Enter` - Select highlighted option
- `Escape` - Close dropdown
- Continue typing after `@` to filter results

## Technical Notes

### Performance
- References are loaded once when the dropdown opens
- Filtering is done client-side for responsiveness
- Dropdown position is calculated dynamically

### Validation
- Only existing references are resolved for generation
- Invalid @ mentions are ignored during generation
- Visual feedback shows valid vs invalid references

### Browser Compatibility
- Works in all modern browsers
- Handles touch interactions for mobile devices
- Keyboard navigation is fully accessible

## Future Enhancements

Potential improvements could include:
1. Category-based reference organization
2. Recent references prioritization
3. Inline preview of referenced images
4. Batch reference operations
5. Reference search across tag names and descriptions