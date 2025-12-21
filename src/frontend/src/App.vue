<template>
  <router-view />
  <Toast />
</template>

<script setup>
import { onMounted } from 'vue'
import { useAuthStore } from './store/auth'
import { usePreferencesStore } from './store/preferences'
import Toast from './components/Toast.vue'

const authStore = useAuthStore()
const preferencesStore = usePreferencesStore()

onMounted(async () => {
  // Fetch user if we have a token but no user data
  if (authStore.token && !authStore.user) {
    await authStore.fetchMe()
  }
  
  // Load and apply preferences if authenticated
  if (authStore.isAuthenticated && !preferencesStore.loaded) {
    await preferencesStore.fetchPreferences()
  }
})
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  color: #333;
  overflow-x: hidden;
}
html {
  overflow-x: hidden;
}
</style>

