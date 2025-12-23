<template>
  <div class="preferences-page">
    <h1 class="page-header">{{ $t('preferences.title') }}</h1>
    
    <div class="preferences-content">
      <!-- Primary Color Section -->
      <div class="preference-section">
        <h2>{{ $t('preferences.primaryColor') }}</h2>
        <p class="section-description">{{ $t('preferences.primaryColorDescription') }}</p>
        
        <div class="color-picker-group">
          <div class="color-picker-wrapper">
            <input
              type="color"
              v-model="localPreferences.primary_color"
              @input="onColorChange"
              class="color-picker"
            />
            <input
              type="text"
              v-model="localPreferences.primary_color"
              @input="onColorTextChange"
              class="color-input"
              placeholder="#3E2FA6"
              pattern="^#[0-9A-Fa-f]{6}$"
            />
          </div>
          
          <!-- Preset Colors -->
          <div class="preset-colors">
            <div
              v-for="preset in presetColors"
              :key="preset.value"
              class="preset-color"
              :class="{ active: localPreferences.primary_color === preset.value }"
              :style="{ backgroundColor: preset.value }"
              @click="selectPresetColor(preset.value)"
              :title="preset.name"
            ></div>
          </div>
        </div>
        
        <!-- Preview -->
        <div class="preview-section">
          <h3>{{ $t('preferences.preview') }}</h3>
          <div class="preview-card" :style="previewStyle">
            <button class="btn-primary">{{ $t('preferences.previewButton') }}</button>
            <button class="btn-secondary">{{ $t('preferences.previewButtonSecondary') }}</button>
            <div class="preview-gradient">{{ $t('preferences.previewGradient') }}</div>
          </div>
        </div>
      </div>
      
      <!-- Font Size Section -->
      <div class="preference-section">
        <h2>{{ $t('preferences.fontSize') }}</h2>
        <p class="section-description">{{ $t('preferences.fontSizeDescription') }}</p>
        
        <div class="option-group">
          <label
            v-for="size in fontSizes"
            :key="size.value"
            class="option-label"
            :class="{ active: localPreferences.font_size === size.value }"
          >
            <input
              type="radio"
              :value="size.value"
              v-model="localPreferences.font_size"
              @change="onPreferenceChange"
            />
            <span>{{ size.label }}</span>
          </label>
        </div>
      </div>
      
      <!-- Border Radius Section -->
      <div class="preference-section">
        <h2>{{ $t('preferences.borderRadius') }}</h2>
        <p class="section-description">{{ $t('preferences.borderRadiusDescription') }}</p>
        
        <div class="option-group">
          <label
            v-for="radius in borderRadii"
            :key="radius.value"
            class="option-label"
            :class="{ active: localPreferences.border_radius === radius.value }"
          >
            <input
              type="radio"
              :value="radius.value"
              v-model="localPreferences.border_radius"
              @change="onPreferenceChange"
            />
            <span>{{ radius.label }}</span>
            <div class="radius-preview" :class="`radius-${radius.value}`"></div>
          </label>
        </div>
      </div>
      
      <!-- Animation Speed Section -->
      <div class="preference-section">
        <h2>{{ $t('preferences.animationSpeed') }}</h2>
        <p class="section-description">{{ $t('preferences.animationSpeedDescription') }}</p>
        
        <div class="option-group">
          <label
            v-for="speed in animationSpeeds"
            :key="speed.value"
            class="option-label"
            :class="{ active: localPreferences.animation_speed === speed.value }"
          >
            <input
              type="radio"
              :value="speed.value"
              v-model="localPreferences.animation_speed"
              @change="onPreferenceChange"
            />
            <span>{{ speed.label }}</span>
          </label>
        </div>
      </div>
      
      <!-- Compact Mode Section -->
      <div class="preference-section">
        <h2>{{ $t('preferences.compactMode') }}</h2>
        <p class="section-description">{{ $t('preferences.compactModeDescription') }}</p>
        
        <label class="toggle-label">
          <input
            type="checkbox"
            v-model="localPreferences.compact_mode"
            @change="onPreferenceChange"
            class="toggle-checkbox"
          />
          <span class="toggle-switch" :class="{ active: localPreferences.compact_mode }"></span>
          <span class="toggle-text">{{ $t('preferences.enableCompactMode') }}</span>
        </label>
      </div>
      
      <!-- Actions -->
      <div class="preference-actions">
        <button @click="savePreferences" class="btn-primary" :disabled="saving">
          <Save v-if="!saving" :size="16" />
          {{ saving ? $t('preferences.saving') : $t('preferences.save') }}
        </button>
        <button @click="resetPreferences" class="btn-secondary">
          <RefreshCw :size="16" />
          {{ $t('preferences.reset') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePreferencesStore } from '../store/preferences'
import { applyPreferences, calculateThemeColors } from '../utils/theme'
import { Save, RefreshCw } from 'lucide-vue-next'

const { t } = useI18n()
const preferencesStore = usePreferencesStore()

const saving = ref(false)
const localPreferences = ref({
  primary_color: null,
  font_size: 'medium',
  border_radius: 'medium',
  animation_speed: 'normal',
  compact_mode: false
})

const presetColors = [
  { name: 'Default Purple', value: '#3E2FA6' },
  { name: 'Blue', value: '#2563EB' },
  { name: 'Green', value: '#10B981' },
  { name: 'Red', value: '#EF4444' },
  { name: 'Orange', value: '#F59E0B' },
  { name: 'Pink', value: '#EC4899' },
  { name: 'Teal', value: '#14B8A6' },
  { name: 'Indigo', value: '#6366F1' }
]

const fontSizes = computed(() => [
  { value: 'small', label: t('preferences.fontSizeSmall') },
  { value: 'medium', label: t('preferences.fontSizeMedium') },
  { value: 'large', label: t('preferences.fontSizeLarge') }
])

const borderRadii = computed(() => [
  { value: 'small', label: t('preferences.borderRadiusSmall') },
  { value: 'medium', label: t('preferences.borderRadiusMedium') },
  { value: 'large', label: t('preferences.borderRadiusLarge') }
])

const animationSpeeds = computed(() => [
  { value: 'fast', label: t('preferences.animationSpeedFast') },
  { value: 'normal', label: t('preferences.animationSpeedNormal') },
  { value: 'slow', label: t('preferences.animationSpeedSlow') }
])

const previewStyle = computed(() => {
  if (!localPreferences.value.primary_color) return {}
  const themeColors = calculateThemeColors(localPreferences.value.primary_color)
  return themeColors
})

onMounted(async () => {
  await preferencesStore.fetchPreferences()
  localPreferences.value = { ...preferencesStore.preferences }
  // Apply current preferences for preview
  applyPreferences(localPreferences.value)
})

const onColorChange = () => {
  if (localPreferences.value.primary_color) {
    applyPreferences(localPreferences.value)
  }
}

const onColorTextChange = (e) => {
  const value = e.target.value
  if (/^#[0-9A-Fa-f]{6}$/.test(value)) {
    localPreferences.value.primary_color = value
    applyPreferences(localPreferences.value)
  }
}

const selectPresetColor = (color) => {
  localPreferences.value.primary_color = color
  applyPreferences(localPreferences.value)
}

const onPreferenceChange = () => {
  applyPreferences(localPreferences.value)
}

const savePreferences = async () => {
  saving.value = true
  try {
    await preferencesStore.updatePreferences(localPreferences.value)
    if (window.$toast) {
      window.$toast.show(t('preferences.savedSuccessfully'), 'success')
    }
  } catch (e) {
    console.error('Failed to save preferences', e)
    if (window.$toast) {
      window.$toast.show(t('preferences.failedToSave'), 'error')
    }
  } finally {
    saving.value = false
  }
}

const resetPreferences = () => {
  localPreferences.value = {
    primary_color: null,
    font_size: 'medium',
    border_radius: 'medium',
    animation_speed: 'normal',
    compact_mode: false
  }
  preferencesStore.resetTheme()
  // Reload default theme
  setTimeout(() => {
    applyPreferences(localPreferences.value)
  }, 100)
}
</script>

<style scoped>
.preferences-page {
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

.preferences-content {
  display: flex;
  flex-direction: column;
  gap: var(--space-2xl);
}

.preference-section {
  background: var(--bg-white);
  padding: var(--space-xl);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
}

.preference-section h2 {
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

.color-picker-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
  margin-bottom: var(--space-xl);
}

.color-picker-wrapper {
  display: flex;
  gap: var(--space-md);
  align-items: center;
}

.color-picker {
  width: 80px;
  height: 80px;
  border: 2px solid var(--primary);
  border-radius: var(--radius-md);
  cursor: pointer;
  background: none;
}

.color-input {
  flex: 1;
  padding: var(--space-md);
  border: 2px solid #ddd;
  border-radius: var(--radius-md);
  font-size: 1rem;
  font-family: var(--font-mono);
}

.preset-colors {
  display: flex;
  gap: var(--space-md);
  flex-wrap: wrap;
}

.preset-color {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-md);
  cursor: pointer;
  border: 3px solid transparent;
  transition: all var(--transition-base);
  box-shadow: var(--shadow-sm);
}

.preset-color:hover {
  transform: scale(1.1);
  box-shadow: var(--shadow-md);
}

.preset-color.active {
  border-color: var(--primary);
  box-shadow: var(--shadow-lg);
  transform: scale(1.15);
}

.preview-section {
  margin-top: var(--space-xl);
  padding-top: var(--space-xl);
  border-top: 1px solid #eee;
}

.preview-section h3 {
  font-size: 1.1rem;
  font-weight: 600;
  margin-bottom: var(--space-md);
  color: var(--text-dark);
}

.preview-card {
  padding: var(--space-xl);
  background: var(--bg-light);
  border-radius: var(--radius-lg);
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
  align-items: flex-start;
}

.preview-gradient {
  padding: var(--space-md) var(--space-lg);
  background: var(--gradient-primary);
  color: white;
  border-radius: var(--radius-md);
  font-weight: 600;
  width: 100%;
  text-align: center;
}

.option-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.option-label {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-md);
  border: 2px solid #ddd;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-base);
}

.option-label:hover {
  border-color: var(--primary);
  background: var(--bg-light);
}

.option-label.active {
  border-color: var(--primary);
  background: var(--primary-light);
  color: white;
}

.option-label input[type="radio"] {
  margin: 0;
  cursor: pointer;
}

.radius-preview {
  width: 40px;
  height: 40px;
  background: var(--primary);
  margin-left: auto;
}

.radius-preview.radius-small {
  border-radius: 4px;
}

.radius-preview.radius-medium {
  border-radius: 12px;
}

.radius-preview.radius-large {
  border-radius: 24px;
}

.toggle-label {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  cursor: pointer;
}

.toggle-checkbox {
  display: none;
}

.toggle-switch {
  position: relative;
  width: 48px;
  height: 24px;
  background: #ddd;
  border-radius: 12px;
  transition: all var(--transition-base);
  flex-shrink: 0;
}

.toggle-switch.active {
  background: var(--primary);
}

.toggle-switch::after {
  content: '';
  position: absolute;
  width: 20px;
  height: 20px;
  background: white;
  border-radius: 50%;
  top: 2px;
  left: 2px;
  transition: all var(--transition-base);
  box-shadow: var(--shadow-sm);
}

.toggle-switch.active::after {
  left: 26px;
}

.preference-actions {
  display: flex;
  gap: var(--space-md);
  justify-content: flex-end;
  padding-top: var(--space-xl);
  border-top: 1px solid #eee;
}

.btn-primary,
.btn-secondary {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

@media (max-width: 768px) {
  .preferences-page {
    padding: var(--space-md);
  }
  
  .color-picker-wrapper {
    flex-direction: column;
  }
  
  .preference-actions {
    flex-direction: column;
  }
  
  .btn-primary,
  .btn-secondary {
    width: 100%;
    justify-content: center;
  }
}
</style>

