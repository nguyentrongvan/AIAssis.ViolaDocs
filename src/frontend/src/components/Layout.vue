<template>
  <div class="layout">
    <aside class="sidebar">
      <div class="logo-container">
        <img src="/logo.png" alt="ViolaDocs" class="logo-img" />
        <div class="logo-text">ViolaDocs</div>
      </div>
      <nav>
        <router-link to="/" class="nav-item">
          <Library class="nav-icon" />
          <span>Library</span>
        </router-link>
        <router-link to="/upload" class="nav-item">
          <Upload class="nav-icon" />
          <span>Upload</span>
        </router-link>
        <router-link to="/scan" class="nav-item">
          <Scan class="nav-icon" />
          <span>Scan Inbox</span>
        </router-link>
        <router-link to="/folders" class="nav-item">
          <Folder class="nav-icon" />
          <span>Folders</span>
        </router-link>
        <router-link to="/search" class="nav-item">
          <Search class="nav-icon" />
          <span>Search</span>
        </router-link>
        <router-link to="/tasks" class="nav-item">
          <CheckSquare class="nav-icon" />
          <span>Tasks</span>
        </router-link>
        <router-link to="/chatbot" class="nav-item">
          <MessageSquare class="nav-icon" />
          <span>Chatbot</span>
        </router-link>
        <template v-if="authStore.isAdmin || authStore.isStaff">
          <div class="nav-divider">Admin</div>
          <router-link to="/admin/users" class="nav-item">
            <Users class="nav-icon" />
            <span>Users</span>
          </router-link>
          <router-link to="/admin/devices" class="nav-item">
            <Printer class="nav-icon" />
            <span>Devices</span>
          </router-link>
          <router-link to="/admin/groups" class="nav-item">
            <Folder class="nav-icon" />
            <span>Groups</span>
          </router-link>
          <router-link to="/admin/settings" class="nav-item">
            <Settings class="nav-icon" />
            <span>Settings</span>
          </router-link>
          <router-link to="/admin/reports" class="nav-item">
            <BarChart3 class="nav-icon" />
            <span>Reports</span>
          </router-link>
          <router-link to="/admin/roles" class="nav-item">
            <Shield class="nav-icon" />
            <span>Roles</span>
          </router-link>
        </template>
        <template v-if="authStore.isMaintainer">
          <div class="nav-divider">Maintainer</div>
          <router-link to="/admin/system-config" class="nav-item">
            <Settings class="nav-icon" />
            <span>System Config</span>
          </router-link>
        </template>
      </nav>
      <div class="user-menu">
        <div class="user-info">
          <User class="user-icon" />
          <span>{{ authStore.user?.name || 'User' }}</span>
          <button @click="handleLogout" class="btn-link">
            <LogOut class="logout-icon" />
            <span>Logout</span>
          </button>
        </div>
      </div>
    </aside>
    <main class="main-content">
      <div class="content">
        <router-view />
      </div>
    </main>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../store/auth'
import {
  Library,
  Upload,
  Scan,
  Search,
  CheckSquare,
  MessageSquare,
  Users,
  Printer,
  Folder,
  Settings,
  BarChart3,
  User,
  LogOut,
  Shield
} from 'lucide-vue-next'

const router = useRouter()
const authStore = useAuthStore()

onMounted(async () => {
  // Ensure user data is loaded if we have a token
  if (authStore.token && !authStore.user) {
    await authStore.fetchMe()
  }
})

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
  min-width: 250px;
  background: var(--primary-dark);
  color: white;
  display: flex;
  flex-direction: column;
  padding: 1.5rem;
  overflow-x: hidden;
}
.logo-container {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 2rem;
  padding: 0.5rem;
  justify-content: center;
  flex-wrap: wrap;
}
.logo-img {
  height: 40px;
  width: auto;
  flex-shrink: 0;
}
.logo-text {
  font-size: 1.25rem;
  font-weight: bold;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
nav {
  flex: 1;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  color: rgba(255,255,255,0.8);
  text-decoration: none;
  border-radius: 6px;
  margin-bottom: 0.5rem;
  transition: all 0.2s;
}
.nav-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  stroke-width: 2;
}
.nav-item span {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.user-icon {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
  stroke-width: 2;
}
.user-info > span {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.btn-link {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: none;
  border: none;
  color: rgba(255,255,255,0.8);
  cursor: pointer;
  text-decoration: none;
  font-size: 0.9rem;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  transition: all 0.2s;
}
.btn-link:hover {
  background: rgba(255,255,255,0.1);
  color: white;
}
.logout-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  stroke-width: 2;
}
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
}
.content {
  flex: 1;
  padding: 2rem;
  overflow-y: auto;
}
</style>

