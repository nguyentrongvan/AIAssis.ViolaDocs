<template>
  <router-view />
  <Toast />
</template>

<script setup>
import { onMounted } from 'vue'
import { useAuthStore } from './store/auth'
import Toast from './components/Toast.vue'

const authStore = useAuthStore()

onMounted(async () => {
  // Fetch user if we have a token but no user data
  if (authStore.token && !authStore.user) {
    await authStore.fetchMe()
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

