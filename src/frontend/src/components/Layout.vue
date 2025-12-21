<template>
  <div class="layout">
    <aside class="sidebar">
      <div class="sidebar-gradient"></div>
      <div class="logo-container">
        <div class="logo-wrapper">
          <img src="/logo.png" alt="ViolaDocs" class="logo-img" />
        </div>
        <div class="logo-tagline">{{ $t('common.tagline') }}</div>
      </div>
      <LanguageSelector />
      <div class="tour-guide-container">
        <button @click="handleRestartTour" class="tour-guide-btn-top" :title="$t('common.restartTour')">
          <HelpCircle class="tour-icon-top" />
          <span>{{ $t('common.tourGuide') }}</span>
        </button>
      </div>
      <nav>
        <router-link to="/" :class="['nav-item', { 'router-link-active': isActiveRoute('/') }]" active-class="" exact-active-class="">
          <Library class="nav-icon" />
          <span>{{ $t('nav.library') }}</span>
        </router-link>
        <router-link to="/documents" :class="['nav-item', { 'router-link-active': isActiveRoute('/documents') }]" active-class="" exact-active-class="">
          <FileText class="nav-icon" />
          <span>{{ $t('nav.documents') }}</span>
        </router-link>
        <router-link v-if="authStore.hasPermission('upload')" to="/upload" :class="['nav-item', { 'router-link-active': isActiveRoute('/upload') }]" active-class="" exact-active-class="">
          <Upload class="nav-icon" />
          <span>{{ $t('nav.upload') }}</span>
        </router-link>
        <router-link v-if="authStore.hasPermission('scan')" to="/scan" :class="['nav-item', { 'router-link-active': isActiveRoute('/scan') }]" active-class="" exact-active-class="">
          <Scan class="nav-icon" />
          <span>{{ $t('nav.scanInbox') }}</span>
        </router-link>
        <router-link v-if="authStore.hasPermission('folder')" to="/folders" :class="['nav-item', { 'router-link-active': isActiveRoute('/folders') }]" active-class="" exact-active-class="">
          <Folder class="nav-icon" />
          <span>{{ $t('nav.folders') }}</span>
        </router-link>
        <router-link v-if="authStore.hasPermission('search')" to="/search" :class="['nav-item', { 'router-link-active': isActiveRoute('/search') }]" active-class="" exact-active-class="">
          <Search class="nav-icon" />
          <span>{{ $t('nav.search') }}</span>
        </router-link>
        <router-link v-if="authStore.hasPermission('delete')" to="/recycle-bin" :class="['nav-item', { 'router-link-active': isActiveRoute('/recycle-bin') }]" active-class="" exact-active-class="">
          <Trash2 class="nav-icon" />
          <span>{{ $t('nav.recycleBin') }}</span>
        </router-link>
        <router-link to="/tasks" :class="['nav-item', { 'router-link-active': isActiveRoute('/tasks') }]" active-class="" exact-active-class="">
          <CheckSquare class="nav-icon" />
          <span>{{ $t('nav.tasks') }}</span>
        </router-link>
        <router-link v-if="authStore.hasPermission('chat')" to="/chatbot" :class="['nav-item', { 'router-link-active': isActiveRoute('/chatbot') }]" active-class="" exact-active-class="">
          <MessageSquare class="nav-icon" />
          <span>{{ $t('nav.chatbot') }}</span>
        </router-link>
        <template v-if="authStore.isAdmin || authStore.isStaff || authStore.hasPermission('user') || authStore.hasPermission('settings') || authStore.hasPermission('reports')">
          <div class="nav-divider">{{ $t('nav.admin') }}</div>
          <router-link v-if="authStore.isAdmin || authStore.isStaff || authStore.hasPermission('user')" to="/admin/users" :class="['nav-item', { 'router-link-active': isActiveRoute('/admin/users') }]" active-class="" exact-active-class="">
            <Users class="nav-icon" />
            <span>{{ $t('nav.users') }}</span>
          </router-link>
          <router-link v-if="authStore.isAdmin || authStore.isStaff" to="/admin/devices" :class="['nav-item', { 'router-link-active': isActiveRoute('/admin/devices') }]" active-class="" exact-active-class="">
            <Printer class="nav-icon" />
            <span>{{ $t('nav.devices') }}</span>
          </router-link>
          <router-link v-if="authStore.isAdmin || authStore.isStaff" to="/admin/groups" :class="['nav-item', { 'router-link-active': isActiveRoute('/admin/groups') }]" active-class="" exact-active-class="">
            <Folder class="nav-icon" />
            <span>{{ $t('nav.groups') }}</span>
          </router-link>
          <router-link v-if="authStore.isAdmin || authStore.isStaff || authStore.hasPermission('settings')" to="/admin/settings" :class="['nav-item', { 'router-link-active': isActiveRoute('/admin/settings') }]" active-class="" exact-active-class="">
            <Settings class="nav-icon" />
            <span>{{ $t('nav.settings') }}</span>
          </router-link>
          <router-link v-if="authStore.isAdmin || authStore.isStaff || authStore.hasPermission('reports')" to="/admin/reports" :class="['nav-item', { 'router-link-active': isActiveRoute('/admin/reports') }]" active-class="" exact-active-class="">
            <BarChart3 class="nav-icon" />
            <span>{{ $t('nav.reports') }}</span>
          </router-link>
          <router-link v-if="authStore.isAdmin || authStore.isStaff" to="/admin/roles" :class="['nav-item', { 'router-link-active': isActiveRoute('/admin/roles') }]" active-class="" exact-active-class="">
            <Shield class="nav-icon" />
            <span>{{ $t('nav.roles') }}</span>
          </router-link>
          <router-link v-if="authStore.isAdmin || authStore.isStaff" to="/admin/ai-jobs" :class="['nav-item', { 'router-link-active': isActiveRoute('/admin/ai-jobs') }]" active-class="" exact-active-class="">
            <Activity class="nav-icon" />
            <span>{{ $t('nav.aiJobs') }}</span>
          </router-link>
        </template>
        <template v-if="authStore.isMaintainer">
          <div class="nav-divider">{{ $t('nav.maintainer') }}</div>
          <router-link to="/admin/system-config" :class="['nav-item', { 'router-link-active': isActiveRoute('/admin/system-config') }]" active-class="" exact-active-class="">
            <Settings class="nav-icon" />
            <span>{{ $t('nav.systemConfig') }}</span>
          </router-link>
        </template>
      </nav>
      <div class="user-menu">
        <div class="user-info">
          <div class="user-info-top">
            <div :class="['user-avatar', getUserRoleColor]">
              <User class="user-icon" />
            </div>
            <div class="user-details">
              <span class="user-name">{{ authStore.user?.name || $t('common.user') }}</span>
              <span class="user-role">{{ authStore.user?.role || 'user' }}</span>
            </div>
          </div>
          <div class="user-info-actions">
            <router-link to="/profile" class="btn-link profile-btn">
              <User class="profile-icon" />
              <span>{{ $t('profile.title') }}</span>
            </router-link>
            <router-link to="/preferences" class="btn-link preferences-btn">
              <Settings class="preferences-icon" />
              <span>{{ $t('preferences.title') }}</span>
            </router-link>
            <button @click="handleLogout" class="btn-link logout-btn">
              <LogOut class="logout-icon" />
              <span>{{ $t('common.logout') }}</span>
            </button>
          </div>
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
      <Footer />
    </main>
    <OnboardingTour ref="onboardingTourRef" />
  </div>
</template>

<script setup>
import { onMounted, computed, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../store/auth'
import LanguageSelector from './LanguageSelector.vue'
import Footer from './Footer.vue'
import OnboardingTour from './OnboardingTour.vue'
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
  Trash2,
  HelpCircle
} from 'lucide-vue-next'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const onboardingTourRef = ref(null)

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

const handleRestartTour = () => {
  if (onboardingTourRef.value && onboardingTourRef.value.restartTour) {
    onboardingTourRef.value.restartTour()
  }
}

const getUserRoleColor = computed(() => {
  const role = authStore.user?.role?.toLowerCase() || 'user'
  
  switch (role) {
    case 'admin':
      return 'avatar-admin'
    case 'staff':
      return 'avatar-staff'
    case 'maintainer':
      return 'avatar-maintainer'
    case 'user':
    default:
      return 'avatar-user'
  }
})
</script>

<style scoped>
.layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
  background: var(--bg-light);
  position: relative;
}

.sidebar {
  width: 280px;
  min-width: 280px;
  height: 100vh;
  position: relative;
  color: white;
  display: flex;
  flex-direction: column;
  padding: var(--space-lg);
  overflow-x: hidden;
  overflow-y: auto;
  z-index: 10;
  scrollbar-width: thin;
  scrollbar-color: transparent transparent;
  transition: scrollbar-color 0.3s ease;
  background: var(--gradient-primary);
  background-attachment: local;
}

.sidebar:hover {
  scrollbar-color: rgba(255, 255, 255, 0.2) transparent;
}

.sidebar::-webkit-scrollbar {
  width: 6px;
}

.sidebar::-webkit-scrollbar-track {
  background: transparent;
}

.sidebar::-webkit-scrollbar-thumb {
  background: transparent;
  border-radius: var(--radius-full);
  transition: background 0.3s ease;
}

.sidebar:hover::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
}

.sidebar::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.35);
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
  pointer-events: none;
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
  border-radius: var(--radius-lg);
  overflow: hidden;
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
  flex-direction: column;
  gap: var(--space-sm);
  padding: var(--space-md);
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.05);
  transition: all var(--transition-base);
  width: 100%;
  box-sizing: border-box;
}

.user-info-top {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  width: 100%;
}

.user-info-actions {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
  width: 100%;
}

.user-info:hover {
  background: rgba(255, 255, 255, 0.1);
}

.user-avatar {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all var(--transition-base);
}

/* Admin - Red/Purple gradient */
.avatar-admin {
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 50%, #991b1b 100%);
  box-shadow: 0 0 15px rgba(239, 68, 68, 0.4);
}

.avatar-admin:hover {
  box-shadow: 0 0 20px rgba(239, 68, 68, 0.6);
  transform: scale(1.05);
}

/* Staff - Blue/Cyan gradient */
.avatar-staff {
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 50%, #1d4ed8 100%);
  box-shadow: 0 0 15px rgba(59, 130, 246, 0.4);
}

.avatar-staff:hover {
  box-shadow: 0 0 20px rgba(59, 130, 246, 0.6);
  transform: scale(1.05);
}

/* Maintainer - Gold/Yellow gradient */
.avatar-maintainer {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 50%, #b45309 100%);
  box-shadow: 0 0 15px rgba(245, 158, 11, 0.4);
}

.avatar-maintainer:hover {
  box-shadow: 0 0 20px rgba(245, 158, 11, 0.6);
  transform: scale(1.05);
}

/* User - Default Cyan/Purple gradient */
.avatar-user {
  background: var(--gradient-cyan-purple);
  box-shadow: var(--shadow-glow-cyan);
}

.avatar-user:hover {
  box-shadow: var(--shadow-glow-cyan);
  transform: scale(1.05);
}

.user-icon {
  width: 20px;
  height: 20px;
  stroke-width: 2.5;
  color: white;
}

.user-details {
  flex: 1;
  min-width: 0; /* Allow flex item to shrink below content size */
  display: flex;
  flex-direction: column;
  gap: 2px;
  overflow: hidden;
}

.user-name {
  font-weight: 600;
  font-size: 0.9rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
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
  flex-shrink: 0; /* Prevent button from shrinking */
  white-space: nowrap; /* Prevent text wrapping */
}

.preferences-btn,
.logout-btn {
  width: 100%;
  justify-content: flex-start;
  padding: var(--space-sm) var(--space-md);
  border-radius: var(--radius-md);
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

.tour-guide-container {
  padding: var(--space-md);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.tour-guide-btn-top {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-sm);
  width: 100%;
  background: rgba(0, 217, 255, 0.1);
  border: 1px solid rgba(0, 217, 255, 0.3);
  color: rgba(255, 255, 255, 0.9);
  cursor: pointer;
  font-size: 0.85rem;
  padding: var(--space-sm) var(--space-md);
  border-radius: var(--radius-md);
  transition: all var(--transition-base);
  font-weight: 500;
  font-family: var(--font-sans);
}

.tour-guide-btn-top:hover {
  background: rgba(0, 217, 255, 0.2);
  color: #00D9FF;
  box-shadow: 0 0 15px rgba(0, 217, 255, 0.4);
  border-color: rgba(0, 217, 255, 0.5);
  transform: translateY(-1px);
}

.tour-guide-btn-top:active {
  transform: translateY(0);
}

.tour-icon-top {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
  stroke-width: 2;
  transition: transform var(--transition-base);
}

.tour-guide-btn-top:hover .tour-icon-top {
  transform: scale(1.15) rotate(10deg);
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
  min-height: 0;
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
  min-height: 0;
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

