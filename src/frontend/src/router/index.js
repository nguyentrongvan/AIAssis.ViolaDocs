import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../store/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue')
  },
  {
    path: '/',
    component: () => import('../components/Layout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'Home',
        component: () => import('../views/Home.vue')
      },
      {
        path: 'upload',
        name: 'Upload',
        component: () => import('../views/Upload.vue')
      },
      {
        path: 'scan',
        name: 'Scan',
        component: () => import('../views/Scan.vue')
      },
      {
        path: 'search',
        name: 'Search',
        component: () => import('../views/Search.vue')
      },
      {
        path: 'documents',
        name: 'Documents',
        component: () => import('../views/Documents.vue')
      },
      {
        path: 'documents/:id',
        name: 'DocumentDetail',
        component: () => import('../views/DocumentDetail.vue')
      },
      {
        path: 'recycle-bin',
        name: 'RecycleBin',
        component: () => import('../views/RecycleBin.vue')
      },
      {
        path: 'tasks',
        name: 'Tasks',
        component: () => import('../views/Tasks.vue')
      },
      {
        path: 'chatbot',
        name: 'Chatbot',
        component: () => import('../views/Chatbot.vue')
      },
      {
        path: 'folders',
        name: 'Folders',
        component: () => import('../views/Folders.vue')
      },
      {
        path: 'folders/:id',
        name: 'FolderDetail',
        component: () => import('../views/Folders.vue')
      },
      {
        path: 'preferences',
        name: 'Preferences',
        component: () => import('../views/Preferences.vue')
      },
      {
        path: 'profile',
        name: 'Profile',
        component: () => import('../views/Profile.vue')
      },
      {
        path: 'admin/users',
        name: 'AdminUsers',
        component: () => import('../views/admin/Users.vue')
      },
      {
        path: 'admin/devices',
        name: 'AdminDevices',
        component: () => import('../views/admin/Devices.vue')
      },
      {
        path: 'admin/groups',
        name: 'AdminGroups',
        component: () => import('../views/admin/Groups.vue')
      },
      {
        path: 'admin/settings',
        name: 'AdminSettings',
        component: () => import('../views/admin/Settings.vue')
      },
      {
        path: 'admin/reports',
        name: 'AdminReports',
        component: () => import('../views/admin/Reports.vue')
      },
      {
        path: 'admin/roles',
        name: 'AdminRoles',
        component: () => import('../views/admin/Roles.vue')
      },
      {
        path: 'admin/system-config',
        name: 'AdminSystemConfig',
        component: () => import('../views/admin/SystemConfig.vue'),
        meta: { requiresMaintainer: true }
      },
      {
        path: 'admin/ai-jobs',
        name: 'AdminAIJobs',
        component: () => import('../views/admin/AIJobs.vue'),
        meta: { requiresAuth: true, requiresAdmin: true }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()
  const { usePreferencesStore } = await import('../store/preferences')
  const preferencesStore = usePreferencesStore()
  
  // Fetch user if we have token but no user data
  if (authStore.token && !authStore.user) {
    await authStore.fetchMe()
  }
  
  // Load and apply user preferences after authentication
  if (authStore.isAuthenticated && !preferencesStore.loaded) {
    await preferencesStore.fetchPreferences()
  }
  
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next('/login')
  } else if (to.meta.requiresMaintainer && !authStore.isMaintainer) {
    next('/')
  } else {
    next()
  }
})

export default router






