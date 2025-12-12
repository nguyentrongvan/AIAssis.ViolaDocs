/**
 * Animation utility functions for Vue components
 */

/**
 * Stagger animation for list items
 * @param {number} index - Item index
 * @param {number} delay - Base delay in ms
 * @returns {string} CSS animation delay
 */
export const staggerDelay = (index, delay = 100) => {
  return `${index * delay}ms`
}

/**
 * Fade in animation
 * @param {number} duration - Animation duration in ms
 * @returns {object} CSS transition object
 */
export const fadeIn = (duration = 300) => ({
  transition: `opacity ${duration}ms ease-out`,
  opacity: 1
})

/**
 * Fade out animation
 * @param {number} duration - Animation duration in ms
 * @returns {object} CSS transition object
 */
export const fadeOut = (duration = 300) => ({
  transition: `opacity ${duration}ms ease-in`,
  opacity: 0
})

/**
 * Slide in from right
 * @param {number} duration - Animation duration in ms
 * @param {number} distance - Slide distance in px
 * @returns {object} CSS transition object
 */
export const slideInRight = (duration = 300, distance = 20) => ({
  transition: `transform ${duration}ms ease-out, opacity ${duration}ms ease-out`,
  transform: 'translateX(0)',
  opacity: 1
})

/**
 * Slide in from left
 * @param {number} duration - Animation duration in ms
 * @param {number} distance - Slide distance in px
 * @returns {object} CSS transition object
 */
export const slideInLeft = (duration = 300, distance = 20) => ({
  transition: `transform ${duration}ms ease-out, opacity ${duration}ms ease-out`,
  transform: 'translateX(0)',
  opacity: 1
})

/**
 * Slide in from top
 * @param {number} duration - Animation duration in ms
 * @param {number} distance - Slide distance in px
 * @returns {object} CSS transition object
 */
export const slideInUp = (duration = 300, distance = 20) => ({
  transition: `transform ${duration}ms ease-out, opacity ${duration}ms ease-out`,
  transform: 'translateY(0)',
  opacity: 1
})

/**
 * Slide in from bottom
 * @param {number} duration - Animation duration in ms
 * @param {number} distance - Slide distance in px
 * @returns {object} CSS transition object
 */
export const slideInDown = (duration = 300, distance = 20) => ({
  transition: `transform ${duration}ms ease-out, opacity ${duration}ms ease-out`,
  transform: 'translateY(0)',
  opacity: 1
})

/**
 * Scale in animation
 * @param {number} duration - Animation duration in ms
 * @param {number} scale - Scale factor (0-1)
 * @returns {object} CSS transition object
 */
export const scaleIn = (duration = 300, scale = 1) => ({
  transition: `transform ${duration}ms ease-out, opacity ${duration}ms ease-out`,
  transform: `scale(${scale})`,
  opacity: 1
})

/**
 * Scale out animation
 * @param {number} duration - Animation duration in ms
 * @returns {object} CSS transition object
 */
export const scaleOut = (duration = 300) => ({
  transition: `transform ${duration}ms ease-in, opacity ${duration}ms ease-in`,
  transform: 'scale(0.9)',
  opacity: 0
})

/**
 * Rotate animation
 * @param {number} duration - Animation duration in ms
 * @param {number} degrees - Rotation degrees
 * @returns {object} CSS transition object
 */
export const rotate = (duration = 300, degrees = 360) => ({
  transition: `transform ${duration}ms ease-in-out`,
  transform: `rotate(${degrees}deg)`
})

/**
 * Pulse animation
 * @param {number} duration - Animation duration in ms
 * @returns {object} CSS animation object
 */
export const pulse = (duration = 2000) => ({
  animation: `pulse ${duration}ms ease-in-out infinite`
})

/**
 * Glow pulse animation
 * @param {number} duration - Animation duration in ms
 * @returns {object} CSS animation object
 */
export const glowPulse = (duration = 2000) => ({
  animation: `glow-pulse ${duration}ms ease-in-out infinite`
})

/**
 * Shimmer animation
 * @param {number} duration - Animation duration in ms
 * @returns {object} CSS animation object
 */
export const shimmer = (duration = 3000) => ({
  animation: `shimmer ${duration}ms ease-in-out infinite`
})

/**
 * Float animation
 * @param {number} duration - Animation duration in ms
 * @returns {object} CSS animation object
 */
export const float = (duration = 3000) => ({
  animation: `float ${duration}ms ease-in-out infinite`
})

/**
 * Get CSS transition string
 * @param {string} property - CSS property
 * @param {number} duration - Duration in ms
 * @param {string} easing - Easing function
 * @returns {string} CSS transition string
 */
export const getTransition = (property = 'all', duration = 300, easing = 'ease-out') => {
  return `${property} ${duration}ms ${easing}`
}

/**
 * Create stagger animation for Vue transition-group
 * @param {number} baseDelay - Base delay in ms
 * @returns {Function} Function that returns delay for each item
 */
export const createStagger = (baseDelay = 100) => {
  return (index) => staggerDelay(index, baseDelay)
}

/**
 * Combine multiple animations
 * @param {...object} animations - Animation objects to combine
 * @returns {object} Combined animation object
 */
export const combineAnimations = (...animations) => {
  return Object.assign({}, ...animations)
}

