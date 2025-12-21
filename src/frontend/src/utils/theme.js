/**
 * Theme utility functions for calculating and applying theme colors
 */

/**
 * Convert hex color to RGB
 */
export function hexToRgb(hex) {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex)
  return result
    ? {
        r: parseInt(result[1], 16),
        g: parseInt(result[2], 16),
        b: parseInt(result[3], 16)
      }
    : null
}

/**
 * Convert RGB to hex
 */
export function rgbToHex(r, g, b) {
  return '#' + [r, g, b].map(x => {
    const hex = x.toString(16)
    return hex.length === 1 ? '0' + hex : hex
  }).join('')
}

/**
 * Darken a color by a percentage
 */
export function darkenColor(hex, percent) {
  const rgb = hexToRgb(hex)
  if (!rgb) return hex
  
  const r = Math.max(0, Math.floor(rgb.r * (1 - percent)))
  const g = Math.max(0, Math.floor(rgb.g * (1 - percent)))
  const b = Math.max(0, Math.floor(rgb.b * (1 - percent)))
  
  return rgbToHex(r, g, b)
}

/**
 * Lighten a color by a percentage
 */
export function lightenColor(hex, percent) {
  const rgb = hexToRgb(hex)
  if (!rgb) return hex
  
  const r = Math.min(255, Math.floor(rgb.r + (255 - rgb.r) * percent))
  const g = Math.min(255, Math.floor(rgb.g + (255 - rgb.g) * percent))
  const b = Math.min(255, Math.floor(rgb.b + (255 - rgb.b) * percent))
  
  return rgbToHex(r, g, b)
}

/**
 * Calculate all theme colors from a primary color
 */
export function calculateThemeColors(primaryColor) {
  if (!primaryColor || !primaryColor.startsWith('#')) {
    return {}
  }
  
  const primaryDark = darkenColor(primaryColor, 0.2)
  const primaryLight = lightenColor(primaryColor, 0.3)
  
  // Generate gradient end (slightly different hue)
  const rgb = hexToRgb(primaryColor)
  if (!rgb) return {}
  
  const gradientEndR = Math.min(255, Math.floor(rgb.r * 1.1))
  const gradientEndG = Math.min(255, Math.floor(rgb.g * 0.95))
  const gradientEndB = Math.min(255, Math.floor(rgb.b * 1.15))
  const gradientEnd = rgbToHex(gradientEndR, gradientEndG, gradientEndB)
  
  // Calculate RGB values for gradient-ai (with opacity)
  const primaryRgba = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.25)`
  const primaryRgbaLight = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.1)`
  
  // Generate gradient-ai: cyan -> primary -> pink (for text)
  const gradientAi = `linear-gradient(135deg, #00D9FF 0%, ${primaryColor} 50%, #EC4899 100%)`
  
  // Generate gradient-ai-soft: soft version for backgrounds
  const gradientAiSoft = `linear-gradient(135deg, rgba(0, 217, 255, 0.1) 0%, ${primaryRgba} 50%, rgba(236, 72, 153, 0.1) 100%)`
  
  return {
    '--primary': primaryColor,
    '--primary-dark': primaryDark,
    '--primary-light': primaryLight,
    '--gradient-start': primaryColor,
    '--gradient-end': gradientEnd,
    '--gradient-primary': `linear-gradient(135deg, ${primaryColor} 0%, ${gradientEnd} 100%)`,
    '--gradient-cyan-purple': `linear-gradient(135deg, #00D9FF 0%, ${primaryColor} 100%)`,
    '--gradient-purple-pink': `linear-gradient(135deg, ${primaryColor} 0%, #EC4899 100%)`,
    '--gradient-ai': gradientAi,
    '--gradient-ai-soft': gradientAiSoft
  }
}

/**
 * Apply theme colors to document root
 */
export function applyThemeColors(themeColors) {
  const root = document.documentElement
  Object.keys(themeColors).forEach(key => {
    root.style.setProperty(key, themeColors[key])
  })
}

/**
 * Apply font size preference
 */
export function applyFontSize(fontSize) {
  const root = document.documentElement
  const body = document.body
  const sizes = {
    small: '13px',
    medium: '16px',
    large: '18px'
  }
  const size = sizes[fontSize] || sizes.medium
  root.style.setProperty('--font-size-base', size)
  body.style.fontSize = size
}

/**
 * Apply border radius preference
 */
export function applyBorderRadius(borderRadius) {
  const root = document.documentElement
  const radiusMap = {
    small: {
      '--radius-sm': '4px',
      '--radius-md': '8px',
      '--radius-lg': '12px',
      '--radius-xl': '16px',
      '--radius-2xl': '20px'
    },
    medium: {
      '--radius-sm': '6px',
      '--radius-md': '12px',
      '--radius-lg': '16px',
      '--radius-xl': '20px',
      '--radius-2xl': '28px'
    },
    large: {
      '--radius-sm': '8px',
      '--radius-md': '16px',
      '--radius-lg': '24px',
      '--radius-xl': '32px',
      '--radius-2xl': '40px'
    }
  }
  
  const radii = radiusMap[borderRadius] || radiusMap.medium
  Object.keys(radii).forEach(key => {
    root.style.setProperty(key, radii[key])
  })
}

/**
 * Apply animation speed preference
 */
export function applyAnimationSpeed(animationSpeed) {
  const root = document.documentElement
  const speeds = {
    fast: {
      '--transition-fast': '100ms cubic-bezier(0.4, 0, 0.2, 1)',
      '--transition-base': '200ms cubic-bezier(0.4, 0, 0.2, 1)',
      '--transition-slow': '300ms cubic-bezier(0.4, 0, 0.2, 1)'
    },
    normal: {
      '--transition-fast': '150ms cubic-bezier(0.4, 0, 0.2, 1)',
      '--transition-base': '300ms cubic-bezier(0.4, 0, 0.2, 1)',
      '--transition-slow': '500ms cubic-bezier(0.4, 0, 0.2, 1)'
    },
    slow: {
      '--transition-fast': '200ms cubic-bezier(0.4, 0, 0.2, 1)',
      '--transition-base': '400ms cubic-bezier(0.4, 0, 0.2, 1)',
      '--transition-slow': '600ms cubic-bezier(0.4, 0, 0.2, 1)'
    }
  }
  
  const speedVars = speeds[animationSpeed] || speeds.normal
  Object.keys(speedVars).forEach(key => {
    root.style.setProperty(key, speedVars[key])
  })
}

/**
 * Apply compact mode
 */
export function applyCompactMode(compactMode) {
  const root = document.documentElement
  if (compactMode) {
    root.style.setProperty('--space-xs', '0.125rem')
    root.style.setProperty('--space-sm', '0.25rem')
    root.style.setProperty('--space-md', '0.5rem')
    root.style.setProperty('--space-lg', '0.75rem')
    root.style.setProperty('--space-xl', '1rem')
    root.style.setProperty('--space-2xl', '1.5rem')
    root.style.setProperty('--space-3xl', '2rem')
  } else {
    // Reset to defaults from theme.css
    root.style.setProperty('--space-xs', '0.25rem')
    root.style.setProperty('--space-sm', '0.5rem')
    root.style.setProperty('--space-md', '1rem')
    root.style.setProperty('--space-lg', '1.5rem')
    root.style.setProperty('--space-xl', '2rem')
    root.style.setProperty('--space-2xl', '3rem')
    root.style.setProperty('--space-3xl', '4rem')
  }
}

/**
 * Apply all preferences
 */
export function applyPreferences(preferences) {
  if (!preferences) return
  
  if (preferences.primary_color) {
    const themeColors = calculateThemeColors(preferences.primary_color)
    applyThemeColors(themeColors)
  }
  
  if (preferences.font_size) {
    applyFontSize(preferences.font_size)
  }
  
  if (preferences.border_radius) {
    applyBorderRadius(preferences.border_radius)
  }
  
  if (preferences.animation_speed) {
    applyAnimationSpeed(preferences.animation_speed)
  }
  
  if (preferences.compact_mode !== undefined) {
    applyCompactMode(preferences.compact_mode)
  }
}

