<template>
  <div class="profile-page">
    <h1 class="page-header">{{ $t('profile.title') }}</h1>
    
    <div class="profile-content">
      <!-- Profile Information Section -->
      <div class="profile-section">
        <h2>{{ $t('profile.profileInformation') }}</h2>
        <p class="section-description">{{ $t('profile.profileInformationDescription') }}</p>
        
        <div class="profile-form">
          <!-- Avatar Upload -->
          <div class="form-group">
            <label>{{ $t('profile.avatar') }}</label>
            <AvatarUpload
              :avatar-url="profile.avatar_url"
              :user-id="authStore.user?.id"
              @uploaded="handleAvatarUploaded"
            />
          </div>
          
          <!-- Name -->
          <div class="form-group">
            <label for="name">{{ $t('profile.name') }} *</label>
            <input
              id="name"
              v-model="profileForm.name"
              type="text"
              required
              :placeholder="$t('profile.namePlaceholder')"
            />
          </div>
          
          <!-- Date of Birth -->
          <div class="form-group">
            <label for="date_of_birth">{{ $t('profile.dateOfBirth') }}</label>
            <input
              id="date_of_birth"
              v-model="profileForm.date_of_birth"
              type="date"
              :max="maxDate"
            />
          </div>
          
          <!-- Phone -->
          <div class="form-group">
            <label for="phone">{{ $t('profile.phone') }}</label>
            <input
              id="phone"
              v-model="profileForm.phone"
              type="tel"
              :placeholder="$t('profile.phonePlaceholder')"
            />
          </div>
          
          <!-- Address -->
          <div class="form-group">
            <label for="address">{{ $t('profile.address') }}</label>
            <textarea
              id="address"
              v-model="profileForm.address"
              rows="3"
              :placeholder="$t('profile.addressPlaceholder')"
            ></textarea>
          </div>
          
          <div class="form-actions">
            <button @click="saveProfile" class="btn-primary" :disabled="savingProfile">
              <Save v-if="!savingProfile" :size="16" />
              {{ savingProfile ? $t('profile.saving') : $t('profile.save') }}
            </button>
            <button @click="resetProfile" class="btn-secondary" :disabled="savingProfile">
              <RefreshCw :size="16" />
              {{ $t('profile.reset') }}
            </button>
          </div>
        </div>
      </div>
      
      <!-- Change Password Section -->
      <div class="profile-section">
        <h2>{{ $t('profile.changePassword') }}</h2>
        <p class="section-description">{{ $t('profile.changePasswordDescription') }}</p>
        
        <div class="password-form">
          <!-- Current Password -->
          <div class="form-group">
            <label for="current_password">{{ $t('profile.currentPassword') }} *</label>
            <input
              id="current_password"
              v-model="passwordForm.current_password"
              type="password"
              required
              :placeholder="$t('profile.currentPasswordPlaceholder')"
            />
          </div>
          
          <!-- New Password -->
          <div class="form-group">
            <label for="new_password">{{ $t('profile.newPassword') }} *</label>
            <input
              id="new_password"
              v-model="passwordForm.new_password"
              type="password"
              required
              @input="updatePasswordStrength"
              :placeholder="$t('profile.newPasswordPlaceholder')"
            />
            <!-- Password Strength Indicator -->
            <div v-if="passwordForm.new_password" class="password-strength">
              <div class="strength-bar">
                <div
                  class="strength-fill"
                  :class="`strength-${passwordStrength.strength}`"
                  :style="{ width: `${(passwordStrength.score / 5) * 100}%` }"
                ></div>
              </div>
              <div class="strength-label" :style="{ color: getStrengthColor(passwordStrength.strength) }">
                {{ $t(`profile.passwordStrength.${passwordStrength.strength}`) }}
              </div>
            </div>
          </div>
          
          <!-- Confirm Password -->
          <div class="form-group">
            <label for="confirm_password">{{ $t('profile.confirmPassword') }} *</label>
            <input
              id="confirm_password"
              v-model="passwordForm.confirm_password"
              type="password"
              required
              :placeholder="$t('profile.confirmPasswordPlaceholder')"
            />
            <p v-if="passwordForm.confirm_password && passwordForm.new_password !== passwordForm.confirm_password" class="error-text">
              {{ $t('profile.passwordsDoNotMatch') }}
            </p>
          </div>
          
          <!-- Password Requirements -->
          <div class="password-requirements">
            <h3>{{ $t('profile.passwordRequirements') }}</h3>
            <ul>
              <li
                v-for="requirement in passwordRequirements"
                :key="requirement"
                :class="{ met: isRequirementMet(requirement) }"
              >
                <Check v-if="isRequirementMet(requirement)" :size="16" class="check-icon" />
                <X v-else :size="16" class="x-icon" />
                <span v-html="requirement"></span>
              </li>
            </ul>
          </div>
          
          <div class="form-actions">
            <button @click="changePassword" class="btn-primary" :disabled="savingPassword || !isPasswordFormValid">
              <Lock :size="16" />
              {{ savingPassword ? $t('profile.changing') : $t('profile.changePassword') }}
            </button>
            <button @click="resetPasswordForm" class="btn-secondary" :disabled="savingPassword">
              <RefreshCw :size="16" />
              {{ $t('profile.reset') }}
            </button>
          </div>
        </div>
      </div>
      
      <!-- Account Information Section (Read-only) -->
      <div class="profile-section">
        <h2>{{ $t('profile.accountInformation') }}</h2>
        <p class="section-description">{{ $t('profile.accountInformationDescription') }}</p>
        
        <div class="account-info">
          <div class="info-item">
            <label>{{ $t('profile.email') }}</label>
            <span>{{ profile.email }}</span>
            <small>{{ $t('profile.emailCannotChange') }}</small>
          </div>
          <div class="info-item">
            <label>{{ $t('profile.role') }}</label>
            <span>{{ profile.role }}</span>
          </div>
          <div class="info-item">
            <label>{{ $t('profile.accountCreated') }}</label>
            <span>{{ formatDate(profile.created_at) }}</span>
          </div>
          <div class="info-item" v-if="profile.last_login_at">
            <label>{{ $t('profile.lastLogin') }}</label>
            <span>{{ formatDate(profile.last_login_at) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../store/auth'
import { usersAPI } from '../services/api'
import { checkPasswordStrength, validatePassword, getPasswordRequirements, getStrengthColor } from '../utils/password_strength'
import AvatarUpload from '../components/AvatarUpload.vue'
import { Save, RefreshCw, Lock, Check, X } from 'lucide-vue-next'

const { t } = useI18n()
const authStore = useAuthStore()

const profile = ref({
  id: null,
  name: '',
  email: '',
  date_of_birth: null,
  phone: '',
  address: '',
  avatar_url: null,
  role: '',
  created_at: null,
  last_login_at: null
})

const profileForm = ref({
  name: '',
  date_of_birth: '',
  phone: '',
  address: ''
})

const passwordForm = ref({
  current_password: '',
  new_password: '',
  confirm_password: ''
})

const savingProfile = ref(false)
const savingPassword = ref(false)
const passwordStrength = ref({ strength: 'weak', score: 0, feedback: [] })

// Special characters constant - kept outside i18n to avoid linked format parsing issues
const SPECIAL_CHARS = '!@#$%^&*()_+-=[]{}|;:,.<>?'

const passwordRequirements = computed(() => {
  return [
    t('profile.passwordRequirement.minLength'),
    t('profile.passwordRequirement.uppercase'),
    t('profile.passwordRequirement.lowercase'),
    t('profile.passwordRequirement.digit'),
    `${t('profile.passwordRequirement.special')} (${SPECIAL_CHARS})`
  ]
})

const maxDate = computed(() => {
  const today = new Date()
  today.setFullYear(today.getFullYear() - 13) // Minimum 13 years old
  return today.toISOString().split('T')[0]
})

const isPasswordFormValid = computed(() => {
  if (!passwordForm.value.current_password || !passwordForm.value.new_password || !passwordForm.value.confirm_password) {
    return false
  }
  const validation = validatePassword(passwordForm.value.new_password)
  return validation.isValid && passwordForm.value.new_password === passwordForm.value.confirm_password
})

onMounted(async () => {
  await loadProfile()
})

const loadProfile = async () => {
  try {
    const res = await usersAPI.profile.get()
    if (res.is_success && res.data) {
      profile.value = res.data
      profileForm.value = {
        name: res.data.name || '',
        date_of_birth: res.data.date_of_birth ? res.data.date_of_birth.split('T')[0] : '',
        phone: res.data.phone || '',
        address: res.data.address || ''
      }
    }
  } catch (e) {
    console.error('Failed to load profile', e)
    if (window.$toast) {
      window.$toast.show(t('profile.failedToLoadProfile'), 'error')
    }
  }
}

const handleAvatarUploaded = async (avatarUrl) => {
  profile.value.avatar_url = avatarUrl
  if (authStore.user) {
    authStore.user.avatar_url = avatarUrl
  }
  // Reload profile to get updated avatar URL
  await loadProfile()
  if (window.$toast) {
    window.$toast.show(t('profile.avatarUploaded'), 'success')
  }
}

const saveProfile = async () => {
  savingProfile.value = true
  try {
    await authStore.updateProfile(profileForm.value)
    if (window.$toast) {
      window.$toast.show(t('profile.profileUpdated'), 'success')
    }
  } catch (e) {
    console.error('Failed to save profile', e)
    if (window.$toast) {
      window.$toast.show(e.response?.data?.message || t('profile.failedToUpdateProfile'), 'error')
    }
  } finally {
    savingProfile.value = false
  }
}

const resetProfile = () => {
  profileForm.value = {
    name: profile.value.name || '',
    date_of_birth: profile.value.date_of_birth ? profile.value.date_of_birth.split('T')[0] : '',
    phone: profile.value.phone || '',
    address: profile.value.address || ''
  }
}

const updatePasswordStrength = () => {
  if (passwordForm.value.new_password) {
    passwordStrength.value = checkPasswordStrength(passwordForm.value.new_password)
  } else {
    passwordStrength.value = { strength: 'weak', score: 0, feedback: [] }
  }
}

const isRequirementMet = (requirement) => {
  const password = passwordForm.value.new_password
  if (!password) return false
  
  // Check based on requirement index (since we're using translation keys now)
  const requirements = passwordRequirements.value
  const index = requirements.indexOf(requirement)
  
  switch (index) {
    case 0: // minLength
      return password.length >= 12
    case 1: // uppercase
      return /[A-Z]/.test(password)
    case 2: // lowercase
      return /[a-z]/.test(password)
    case 3: // digit
      return /\d/.test(password)
    case 4: // special
      const specialPattern = /[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]/
      return specialPattern.test(password)
    default:
      return false
  }
}

const changePassword = async () => {
  savingPassword.value = true
  try {
    await authStore.changePassword(
      passwordForm.value.current_password,
      passwordForm.value.new_password,
      passwordForm.value.confirm_password
    )
    if (window.$toast) {
      window.$toast.show(t('profile.passwordChanged'), 'success')
    }
    resetPasswordForm()
  } catch (e) {
    console.error('Failed to change password', e)
    const errorMsg = e.response?.data?.message || e.response?.data?.errors?.join(', ') || t('profile.failedToChangePassword')
    if (window.$toast) {
      window.$toast.show(errorMsg, 'error')
    }
  } finally {
    savingPassword.value = false
  }
}

const resetPasswordForm = () => {
  passwordForm.value = {
    current_password: '',
    new_password: '',
    confirm_password: ''
  }
  passwordStrength.value = { strength: 'weak', score: 0, feedback: [] }
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleDateString()
}
</script>

<style scoped>
.profile-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--space-xl);
  animation: fadeIn var(--transition-base) var(--ease-out);
}

.page-header {
  margin-bottom: var(--space-2xl);
  font-size: 2rem;
  font-weight: 700;
  background: var(--gradient-primary);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.profile-content {
  display: flex;
  flex-direction: column;
  gap: var(--space-2xl);
}

.profile-section {
  background: var(--bg-white);
  padding: var(--space-xl);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
}

.profile-section h2 {
  font-size: 1.5rem;
  font-weight: 600;
  margin-bottom: var(--space-sm);
  color: var(--text-dark);
}

.section-description {
  color: var(--text-light);
  margin-bottom: var(--space-lg);
  font-size: 0.95rem;
}

.profile-form,
.password-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.form-group label {
  font-weight: 600;
  color: var(--text-dark);
  font-size: 0.95rem;
}

.form-group input,
.form-group textarea {
  padding: var(--space-md);
  border: 2px solid #ddd;
  border-radius: var(--radius-md);
  font-size: 1rem;
  transition: all var(--transition-base);
  font-family: inherit;
}

.form-group input:focus,
.form-group textarea:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(62, 47, 166, 0.1);
}

.form-group textarea {
  resize: vertical;
  min-height: 80px;
}

.password-strength {
  margin-top: var(--space-xs);
}

.strength-bar {
  width: 100%;
  height: 6px;
  background: var(--bg-light);
  border-radius: var(--radius-full);
  overflow: hidden;
  margin-bottom: var(--space-xs);
}

.strength-fill {
  height: 100%;
  transition: width var(--transition-base);
  border-radius: var(--radius-full);
}

.strength-fill.strength-weak {
  background: #ef4444;
}

.strength-fill.strength-medium {
  background: #f59e0b;
}

.strength-fill.strength-strong {
  background: #10b981;
}

.strength-label {
  font-size: 0.875rem;
  font-weight: 600;
  text-transform: capitalize;
}

.password-requirements {
  background: var(--bg-light);
  padding: var(--space-md);
  border-radius: var(--radius-md);
  margin-top: var(--space-md);
}

.password-requirements h3 {
  font-size: 1rem;
  font-weight: 600;
  margin-bottom: var(--space-sm);
  color: var(--text-dark);
}

.password-requirements ul {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}

.password-requirements li {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  font-size: 0.875rem;
  color: var(--text-medium);
}

.password-requirements li.met {
  color: var(--success);
}

.check-icon {
  color: var(--success);
  flex-shrink: 0;
}

.x-icon {
  color: var(--text-light);
  flex-shrink: 0;
}

.error-text {
  color: var(--error);
  font-size: 0.875rem;
  margin-top: var(--space-xs);
}

.form-actions {
  display: flex;
  gap: var(--space-md);
  margin-top: var(--space-md);
}

.btn-primary,
.btn-secondary {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.account-info {
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
  padding-bottom: var(--space-md);
  border-bottom: 1px solid #eee;
}

.info-item:last-child {
  border-bottom: none;
}

.info-item label {
  font-weight: 600;
  color: var(--text-medium);
  font-size: 0.875rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.info-item span {
  color: var(--text-dark);
  font-size: 1rem;
}

.info-item small {
  color: var(--text-light);
  font-size: 0.8rem;
  font-style: italic;
}

@media (max-width: 768px) {
  .profile-page {
    padding: var(--space-md);
  }
  
  .form-actions {
    flex-direction: column;
  }
  
  .btn-primary,
  .btn-secondary {
    width: 100%;
    justify-content: center;
  }
}
</style>

