<template>
  <div class="layout">
    <aside class="sidebar">
      <div class="sidebar-gradient"></div>
      <div class="logo-container">
        <div class="logo-wrapper">
          <img src="/logo.png" alt="ViolaDocs" class="logo-img" />
        </div>
        <div class="logo-tagline">AI-Powered Document Intelligence</div>
      </div>
      <nav>
        <router-link to="/" :class="['nav-item', { 'router-link-active': isActiveRoute('/') }]" active-class="" exact-active-class="">
          <Library class="nav-icon" />
          <span>Library</span>
        </router-link>
        <router-link to="/documents" :class="['nav-item', { 'router-link-active': isActiveRoute('/documents') }]" active-class="" exact-active-class="">
          <FileText class="nav-icon" />
          <span>Documents</span>
        </router-link>
        <router-link to="/upload" :class="['nav-item', { 'router-link-active': isActiveRoute('/upload') }]" active-class="" exact-active-class="">
          <Upload class="nav-icon" />
          <span>Upload</span>
        </router-link>
        <router-link to="/scan" :class="['nav-item', { 'router-link-active': isActiveRoute('/scan') }]" active-class="" exact-active-class="">
          <Scan class="nav-icon" />
          <span>Scan Inbox</span>
        </router-link>
        <router-link to="/folders" :class="['nav-item', { 'router-link-active': isActiveRoute('/folders') }]" active-class="" exact-active-class="">
          <Folder class="nav-icon" />
          <span>Folders</span>
        </router-link>
        <router-link to="/search" :class="['nav-item', { 'router-link-active': isActiveRoute('/search') }]" active-class="" exact-active-class="">
          <Search class="nav-icon" />
          <span>Search</span>
        </router-link>
        <router-link to="/recycle-bin" :class="['nav-item', { 'router-link-active': isActiveRoute('/recycle-bin') }]" active-class="" exact-active-class="">
          <Trash2 class="nav-icon" />
          <span>Recycle Bin</span>
        </router-link>
        <router-link to="/tasks" :class="['nav-item', { 'router-link-active': isActiveRoute('/tasks') }]" active-class="" exact-active-class="">
          <CheckSquare class="nav-icon" />
          <span>Tasks</span>
        </router-link>
        <router-link to="/chatbot" :class="['nav-item', { 'router-link-active': isActiveRoute('/chatbot') }]" active-class="" exact-active-class="">
          <MessageSquare class="nav-icon" />
          <span>Chatbot</span>
        </router-link>
        <template v-if="authStore.isAdmin || authStore.isStaff">
          <div class="nav-divider">Admin</div>
          <router-link to="/admin/users" :class="['nav-item', { 'router-link-active': isActiveRoute('/admin/users') }]" active-class="" exact-active-class="">
            <Users class="nav-icon" />
            <span>Users</span>
          </router-link>
          <router-link to="/admin/devices" :class="['nav-item', { 'router-link-active': isActiveRoute('/admin/devices') }]" active-class="" exact-active-class="">
            <Printer class="nav-icon" />
            <span>Devices</span>
          </router-link>
          <router-link to="/admin/groups" :class="['nav-item', { 'router-link-active': isActiveRoute('/admin/groups') }]" active-class="" exact-active-class="">
            <Folder class="nav-icon" />
            <span>Groups</span>
          </router-link>
          <router-link to="/admin/settings" :class="['nav-item', { 'router-link-active': isActiveRoute('/admin/settings') }]" active-class="" exact-active-class="">
            <Settings class="nav-icon" />
            <span>Settings</span>
          </router-link>
          <router-link to="/admin/reports" :class="['nav-item', { 'router-link-active': isActiveRoute('/admin/reports') }]" active-class="" exact-active-class="">
            <BarChart3 class="nav-icon" />
            <span>Reports</span>
          </router-link>
          <router-link to="/admin/roles" :class="['nav-item', { 'router-link-active': isActiveRoute('/admin/roles') }]" active-class="" exact-active-class="">
            <Shield class="nav-icon" />
            <span>Roles</span>
          </router-link>
          <router-link to="/admin/ai-jobs" :class="['nav-item', { 'router-link-active': isActiveRoute('/admin/ai-jobs') }]" active-class="" exact-active-class="">
            <Activity class="nav-icon" />
            <span>AI Jobs</span>
          </router-link>
        </template>
        <template v-if="authStore.isMaintainer">
          <div class="nav-divider">Maintainer</div>
          <router-link to="/admin/system-config" :class="['nav-item', { 'router-link-active': isActiveRoute('/admin/system-config') }]" active-class="" exact-active-class="">
            <Settings class="nav-icon" />
            <span>System Config</span>
          </router-link>
        </template>
      </nav>
      <div class="user-menu">
        <div class="user-info">
          <div class="user-avatar">
            <User class="user-icon" />
          </div>
          <div class="user-details">
            <span class="user-name">{{ authStore.user?.name || 'User' }}</span>
            <span class="user-role">{{ authStore.user?.role || 'user' }}</span>
          </div>
          <button @click="handleLogout" class="btn-link">
            <LogOut class="logout-icon" />
            <span>Logout</span>
          </button>
        </div>
      </div>
    </aside>
    <main class="main-content">
      <div class="content-background"></div>
      <div class="content">
        <transition name="page" mode="out-in">
          <router-view />
        </transition>
      </div>
    </main>
  </div>
</template>

<script setup>
import { onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
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
  Shield,
  Activity,
  FileText,
  Trash2
} from 'lucide-vue-next'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const isActiveRoute = (path) => {
  const currentPath = route.path
  
  // Special handling for root path - only match exact "/" or empty
  if (path === '/') {
    return currentPath === '/' || currentPath === ''
  }
  
  // If we're on root path, don't match any other paths
  if (currentPath === '/' || currentPath === '') {
    return false
  }
  
  // For other paths, match exact or sub-paths (e.g., /documents matches /documents/123)
  return currentPath === path || currentPath.startsWith(path + '/')
}

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
  position: relative;
}

.sidebar {
  width: 280px;
  min-width: 280px;
  position: relative;
  color: white;
  display: flex;
  flex-direction: column;
  padding: var(--space-lg);
  overflow-x: hidden;
  z-index: 10;
}

.sidebar::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: var(--gradient-primary);
  z-index: -1;
}

.sidebar-gradient {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: var(--gradient-ai-soft);
  opacity: 0.3;
  z-index: -1;
  animation: shimmer 3s ease-in-out infinite;
}
.logo-container {
  margin-bottom: var(--space-xl);
  padding: var(--space-md);
}

.logo-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
}

.logo-img {
  height: 48px;
  width: auto;
  flex-shrink: 0;
}

.logo-tagline {
  font-size: 0.75rem;
  text-align: center;
  color: rgba(255, 255, 255, 0.7);
  font-weight: 500;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  margin-top: var(--space-sm);
}
nav {
  flex: 1;
  position: relative;
  z-index: 1;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-md) var(--space-lg);
  color: rgba(255, 255, 255, 0.85);
  text-decoration: none;
  border-radius: var(--radius-lg);
  margin-bottom: var(--space-sm);
  transition: all var(--transition-base);
  position: relative;
  overflow: hidden;
  font-weight: 500;
}

.nav-item::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: var(--ai-cyan);
  transform: scaleY(0);
  transition: transform var(--transition-base);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
}

.nav-item:hover::before,
.nav-item.router-link-active::before {
  transform: scaleY(1);
}

.nav-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  stroke-width: 2;
  transition: all var(--transition-base);
}

.nav-item span {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: all var(--transition-base);
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.1);
  color: white;
  transform: translateX(4px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.nav-item:hover .nav-icon {
  transform: scale(1.1);
  color: var(--ai-cyan);
}

.nav-item.router-link-active {
  background: rgba(255, 255, 255, 0.15);
  color: white;
  box-shadow: 0 4px 12px rgba(0, 217, 255, 0.2), inset 0 0 20px rgba(0, 217, 255, 0.1);
}

.nav-item.router-link-active .nav-icon {
  color: var(--ai-cyan);
  filter: drop-shadow(0 0 4px rgba(0, 217, 255, 0.6));
}
.nav-divider {
  margin-top: var(--space-xl);
  margin-bottom: var(--space-md);
  padding: var(--space-sm) var(--space-lg);
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.5);
  text-transform: uppercase;
  font-weight: 600;
  letter-spacing: 0.1em;
  position: relative;
}

.nav-divider::after {
  content: '';
  position: absolute;
  left: var(--space-lg);
  right: var(--space-lg);
  bottom: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
}

.user-menu {
  margin-top: auto;
  padding-top: var(--space-lg);
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  position: relative;
  z-index: 1;
}

.user-info {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-md);
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.05);
  transition: all var(--transition-base);
}

.user-info:hover {
  background: rgba(255, 255, 255, 0.1);
}

.user-avatar {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-full);
  background: var(--gradient-cyan-purple);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: var(--shadow-glow-cyan);
  flex-shrink: 0;
}

.user-icon {
  width: 20px;
  height: 20px;
  stroke-width: 2.5;
  color: white;
}

.user-details {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.user-name {
  font-weight: 600;
  font-size: 0.9rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-role {
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.6);
  text-transform: capitalize;
}
.btn-link {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  background: none;
  border: none;
  color: rgba(255, 255, 255, 0.8);
  cursor: pointer;
  text-decoration: none;
  font-size: 0.85rem;
  padding: var(--space-sm) var(--space-md);
  border-radius: var(--radius-md);
  transition: all var(--transition-base);
  font-weight: 500;
}

.btn-link:hover {
  background: rgba(255, 255, 255, 0.15);
  color: white;
  transform: translateX(2px);
}

.logout-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  stroke-width: 2;
  transition: transform var(--transition-base);
}

.btn-link:hover .logout-icon {
  transform: translateX(2px);
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
}

.content-background {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: var(--gradient-ai-soft);
  opacity: 0.3;
  z-index: 0;
  pointer-events: none;
}

.content {
  flex: 1;
  padding: var(--space-xl);
  overflow-y: auto;
  position: relative;
  z-index: 1;
}

/* Page Transition */
.page-enter-active {
  transition: all var(--transition-base) var(--ease-out);
}

.page-leave-active {
  transition: all var(--transition-fast) var(--ease-in);
}

.page-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.page-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

/* Responsive */
@media (max-width: 768px) {
  .sidebar {
    width: 70px;
    min-width: 70px;
    padding: var(--space-md);
  }
  
  .logo-tagline,
  .nav-item span,
  .user-name,
  .user-role,
  .btn-link span {
    display: none;
  }
  
  .logo-wrapper {
    justify-content: center;
  }
  
  .nav-item {
    justify-content: center;
    padding: var(--space-md);
  }
  
  .user-info {
    justify-content: center;
  }
}
</style>

