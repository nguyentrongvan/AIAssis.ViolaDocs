/**
 * Password strength validation and checking utility
 */

const MIN_LENGTH = 12
const SPECIAL_CHARS = '!@#$%^&*()_+-=[]{}|;:,.<>?'

/**
 * Check password strength
 * @param {string} password - Password to check
 * @returns {Object} - { strength: 'weak'|'medium'|'strong', score: number, feedback: string[] }
 */
export function checkPasswordStrength(password) {
  if (!password) {
    return {
      strength: 'weak',
      score: 0,
      feedback: []
    }
  }

  let score = 0
  const feedback = []

  // Length check
  if (password.length < MIN_LENGTH) {
    feedback.push(`At least ${MIN_LENGTH} characters`)
  } else {
    score += 1
    if (password.length >= 16) {
      score += 1
    }
  }

  // Uppercase check
  if (!/[A-Z]/.test(password)) {
    feedback.push('At least one uppercase letter (A-Z)')
  } else {
    score += 1
  }

  // Lowercase check
  if (!/[a-z]/.test(password)) {
    feedback.push('At least one lowercase letter (a-z)')
  } else {
    score += 1
  }

  // Digit check
  if (!/\d/.test(password)) {
    feedback.push('At least one digit (0-9)')
  } else {
    score += 1
  }

  // Special character check
  const specialPattern = new RegExp(`[${SPECIAL_CHARS.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}]`)
  if (!specialPattern.test(password)) {
    feedback.push(`At least one special character (${SPECIAL_CHARS})`)
  } else {
    score += 1
  }

  // Determine strength
  let strength = 'weak'
  if (score >= 5 && password.length >= MIN_LENGTH) {
    strength = 'strong'
  } else if (score >= 3 && password.length >= MIN_LENGTH) {
    strength = 'medium'
  }

  return {
    strength,
    score,
    feedback
  }
}

/**
 * Validate password against requirements
 * @param {string} password - Password to validate
 * @returns {Object} - { isValid: boolean, errors: string[] }
 */
export function validatePassword(password) {
  const errors = []

  if (!password) {
    errors.push('Password is required')
    return { isValid: false, errors }
  }

  if (password.length < MIN_LENGTH) {
    errors.push(`Password must be at least ${MIN_LENGTH} characters long`)
  }

  if (!/[A-Z]/.test(password)) {
    errors.push('Password must contain at least one uppercase letter (A-Z)')
  }

  if (!/[a-z]/.test(password)) {
    errors.push('Password must contain at least one lowercase letter (a-z)')
  }

  if (!/\d/.test(password)) {
    errors.push('Password must contain at least one digit (0-9)')
  }

  const specialPattern = new RegExp(`[${SPECIAL_CHARS.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}]`)
  if (!specialPattern.test(password)) {
    errors.push(`Password must contain at least one special character (${SPECIAL_CHARS})`)
  }

  return {
    isValid: errors.length === 0,
    errors
  }
}

/**
 * Get password requirements list
 * @returns {string[]} - List of requirement strings
 */
export function getPasswordRequirements() {
  return [
    `At least ${MIN_LENGTH} characters`,
    'At least one uppercase letter (A-Z)',
    'At least one lowercase letter (a-z)',
    'At least one digit (0-9)',
    `At least one special character (${SPECIAL_CHARS})`
  ]
}

/**
 * Get strength color for UI
 * @param {string} strength - 'weak'|'medium'|'strong'
 * @returns {string} - Color class or hex
 */
export function getStrengthColor(strength) {
  switch (strength) {
    case 'strong':
      return '#10b981' // green
    case 'medium':
      return '#f59e0b' // orange
    case 'weak':
      return '#ef4444' // red
    default:
      return '#6b7280' // gray
  }
}



