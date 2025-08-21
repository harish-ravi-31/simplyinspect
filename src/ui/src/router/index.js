import { createRouter, createWebHistory } from 'vue-router'
import { useAuth } from '../composables/useAuth'
import SharePointColumns from '../views/SharePointColumns.vue'
import PurviewAuditLogs from '../views/PurviewAuditLogs.vue'
import Settings from '../views/Settings.vue'
import Login from '../views/Login.vue'
import Register from '../views/Register.vue'
import AdminUsers from '../views/AdminUsers.vue'
import PermissionBaselines from '../views/PermissionBaselines.vue'

const routes = [
  // Authentication routes (public)
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { requiresGuest: true }
  },
  {
    path: '/register',
    name: 'Register',
    component: Register,
    meta: { requiresGuest: true }
  },
  
  // Protected routes
  {
    path: '/',
    redirect: '/sharepoint',
    meta: { requiresAuth: true }
  },
  {
    path: '/sharepoint',
    name: 'SharePoint',
    component: SharePointColumns,
    meta: { requiresAuth: true }
  },
  {
    path: '/purview',
    name: 'Purview',
    component: PurviewAuditLogs,
    meta: { requiresAuth: true }
  },
  {
    path: '/baselines',
    name: 'Baselines',
    component: PermissionBaselines,
    meta: { requiresAuth: true }
  },
  {
    path: '/settings',
    name: 'Settings',
    component: Settings,
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  
  // Admin routes
  {
    path: '/admin',
    redirect: '/admin/users',
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/admin/users',
    name: 'AdminUsers',
    component: AdminUsers,
    meta: { requiresAuth: true, requiresAdmin: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Route guards
router.beforeEach((to, from, next) => {
  const auth = useAuth()
  
  // Check if route requires authentication
  if (to.meta.requiresAuth) {
    if (!auth.isAuthenticated.value) {
      // Not logged in, redirect to login
      return next({ name: 'Login', query: { redirect: to.fullPath } })
    }
    
    // Check admin requirement
    if (to.meta.requiresAdmin && !auth.isAdmin.value) {
      console.warn(`Access denied: User ${auth.user.value?.email} tried to access admin route ${to.path}`)
      return next({ name: 'SharePoint' }) // Redirect to default page
    }
  }
  
  // Check if route requires guest (user not logged in)
  if (to.meta.requiresGuest && auth.isAuthenticated.value) {
    // Already logged in, redirect to home
    return next('/')
  }
  
  next()
})

export default router