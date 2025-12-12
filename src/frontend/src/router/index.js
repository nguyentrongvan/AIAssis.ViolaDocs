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
        path: 'documents/:id',
        name: 'DocumentDetail',
        component: () => import('../views/DocumentDetail.vue')
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
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next('/login')
  } else {
    next()
  }
})

export default router






