<template>
  <div class="login-container">
    <div class="particles-background"></div>
    <div class="login-card glass-strong">
      <div class="logo-container">
        <div class="logo-wrapper">
          <img src="/logo.png" alt="ViolaDocs" class="logo-img" />
          <h1 class="logo-text gradient-text">ViolaDocs</h1>
        </div>
        <p class="tagline">AI-Powered Document Intelligence</p>
      </div>
      <form @submit.prevent="handleLogin">
        <div class="form-group">
          <label>Email</label>
          <input v-model="email" type="email" required />
        </div>
        <div class="form-group">
          <label>Password</label>
          <input v-model="password" type="password" required />
        </div>
        <button type="submit" :disabled="loading" class="btn-primary">
          {{ loading ? 'Logging in...' : 'Login' }}
        </button>
        <p v-if="error" class="error">{{ error }}</p>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../store/auth'

const router = useRouter()
const authStore = useAuthStore()

const email = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

const handleLogin = async () => {
  error.value = ''
  loading.value = true
  try {
    await authStore.login(email.value, password.value)
    router.push('/')
  } catch (e) {
    error.value = e.message || 'Login failed'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--gradient-ai);
  position: relative;
  overflow: hidden;
}

.particles-background {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: var(--gradient-ai-soft);
  opacity: 0.5;
  z-index: 0;
  animation: shimmer 8s ease-in-out infinite;
}

.particles-background::before,
.particles-background::after {
  content: '';
  position: absolute;
  width: 300px;
  height: 300px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(0, 217, 255, 0.4) 0%, transparent 70%);
  animation: float 6s ease-in-out infinite;
}

.particles-background::before {
  top: 10%;
  left: 10%;
  animation-delay: 0s;
}

.particles-background::after {
  bottom: 10%;
  right: 10%;
  animation-delay: 3s;
}

.login-card {
  padding: var(--space-3xl);
  border-radius: var(--radius-2xl);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15), 0 0 40px rgba(108, 92, 231, 0.2);
  width: 100%;
  max-width: 450px;
  box-sizing: border-box;
  overflow: hidden;
  position: relative;
  z-index: 1;
  background: #FFFFFF;
  border: 1px solid rgba(255, 255, 255, 0.3);
  animation: fadeInUp var(--transition-slow) var(--ease-out);
}

.login-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: var(--gradient-ai);
  z-index: 1;
}
.logo-container {
  margin-bottom: var(--space-xl);
  text-align: center;
}

.logo-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-md);
  margin-bottom: var(--space-md);
  flex-wrap: wrap;
}

.logo-img {
  height: 64px;
  width: auto;
  flex-shrink: 0;
  border-radius: var(--radius-xl);
  filter: drop-shadow(0 0 20px rgba(0, 217, 255, 0.4));
  animation: float 3s var(--ease-in-out) infinite;
}

.logo-text {
  text-align: center;
  margin: 0;
  font-size: 2rem;
  font-weight: 800;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  letter-spacing: -0.02em;
}

.tagline {
  text-align: center;
  color: var(--text-medium);
  font-size: 1rem;
  margin: 0 0 var(--space-xl) 0;
  font-weight: 500;
  letter-spacing: 0.05em;
}
.form-group {
  margin-bottom: 1rem;
}
.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  color: #333;
}
.form-group input {
  width: 100%;
  padding: var(--space-lg);
  border: 2px solid rgba(0, 0, 0, 0.1);
  border-radius: var(--radius-lg);
  font-size: 1rem;
  box-sizing: border-box;
  background: var(--bg-white);
  transition: all var(--transition-base);
  box-shadow: var(--shadow-sm);
}

.form-group input:focus {
  outline: none;
  border-color: var(--ai-cyan);
  box-shadow: var(--shadow-md), 0 0 0 3px rgba(0, 217, 255, 0.1);
}
.error {
  color: var(--error);
  margin-top: 1rem;
  text-align: center;
}
</style>

