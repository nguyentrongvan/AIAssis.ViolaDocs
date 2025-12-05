<template>
  <div class="layout">
    <aside class="sidebar">
      <div class="logo-container">
        <img src="/logo.png" alt="ViolaDocs" class="logo-img" />
        <div class="logo-text">ViolaDocs</div>
      </div>
      <nav>
        <router-link to="/" class="nav-item">
          <span>📚 Library</span>
        </router-link>
        <router-link to="/upload" class="nav-item">
          <span>📤 Upload</span>
        </router-link>
        <router-link to="/scan" class="nav-item">
          <span>🖨️ Scan Inbox</span>
        </router-link>
        <router-link to="/search" class="nav-item">
          <span>🔍 Search</span>
        </router-link>
        <router-link to="/tasks" class="nav-item">
          <span>✅ Tasks</span>
        </router-link>
        <router-link to="/chatbot" class="nav-item">
          <span>💬 Chatbot</span>
        </router-link>
        <template v-if="authStore.isAdmin || authStore.isStaff">
          <div class="nav-divider">Admin</div>
          <router-link to="/admin/users" class="nav-item">
            <span>👥 Users</span>
          </router-link>
          <router-link to="/admin/devices" class="nav-item">
            <span>🖨️ Devices</span>
          </router-link>
          <router-link to="/admin/groups" class="nav-item">
            <span>📁 Groups</span>
          </router-link>
          <router-link to="/admin/settings" class="nav-item">
            <span>⚙️ Settings</span>
          </router-link>
          <router-link to="/admin/reports" class="nav-item">
            <span>📊 Reports</span>
          </router-link>
        </template>
      </nav>
      <div class="user-menu">
        <div class="user-info">
          <span>{{ authStore.user?.name || 'User' }}</span>
          <button @click="handleLogout" class="btn-link">Logout</button>
        </div>
      </div>
    </aside>
    <main class="main-content">
      <header class="topbar">
        <slot name="header"></slot>
      </header>
      <div class="content">
        <slot></slot>
      </div>
    </main>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '../store/auth'

const router = useRouter()
const authStore = useAuthStore()

const handleLogout = () => {
  authStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.layout {
  display: flex;
  min-height: 100vh;
  background: var(--bg-light);
}
.sidebar {
  width: 250px;
  background: var(--primary-dark);
  color: white;
  display: flex;
  flex-direction: column;
  padding: 1.5rem;
}
.logo-container {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 2rem;
  padding: 0.5rem;
  justify-content: center;
}
.logo-img {
  height: 40px;
  width: auto;
}
.logo-text {
  font-size: 1.5rem;
  font-weight: bold;
}
nav {
  flex: 1;
}
.nav-item {
  display: block;
  padding: 0.75rem 1rem;
  color: rgba(255,255,255,0.8);
  text-decoration: none;
  border-radius: 6px;
  margin-bottom: 0.5rem;
  transition: all 0.2s;
}
.nav-item:hover, .nav-item.router-link-active {
  background: rgba(255,255,255,0.1);
  color: white;
}
.nav-divider {
  margin-top: 1.5rem;
  margin-bottom: 0.5rem;
  padding: 0.5rem 1rem;
  font-size: 0.85rem;
  color: rgba(255,255,255,0.6);
  text-transform: uppercase;
}
.user-menu {
  margin-top: auto;
  padding-top: 1rem;
  border-top: 1px solid rgba(255,255,255,0.1);
}
.user-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.btn-link {
  background: none;
  border: none;
  color: rgba(255,255,255,0.8);
  cursor: pointer;
  text-decoration: underline;
  font-size: 0.9rem;
}
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
}
.topbar {
  background: white;
  padding: 1rem 2rem;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}
.content {
  flex: 1;
  padding: 2rem;
  overflow-y: auto;
}
</style>

