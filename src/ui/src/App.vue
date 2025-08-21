<template>
  <v-app>
    <!-- Navigation Drawer - only show when authenticated -->
    <v-navigation-drawer v-if="auth.isAuthenticated.value" v-model="drawer" app>
      <v-list>
        <v-list-item>
          <v-list-item-content>
            <v-list-item-title class="text-h6">
              SimplyInspect
            </v-list-item-title>
            <v-list-item-subtitle>
              SharePoint & Purview Inspector
            </v-list-item-subtitle>
          </v-list-item-content>
        </v-list-item>
      </v-list>

      <v-divider></v-divider>

      <v-list nav dense>
        <v-list-item
          v-for="item in filteredNavigationItems"
          :key="item.title"
          :to="item.to"
          :prepend-icon="item.icon"
          :title="item.title"
        />
      </v-list>

      <!-- User Info Section -->
      <template v-slot:append v-if="auth.user.value">
        <v-divider></v-divider>
        <v-list density="compact">
          <v-list-item>
            <v-list-item-content>
              <v-list-item-title class="text-body-2 font-weight-bold">
                {{ auth.user.value.full_name }}
              </v-list-item-title>
              <v-list-item-subtitle class="text-caption">
                {{ auth.user.value.role }}
              </v-list-item-subtitle>
            </v-list-item-content>
          </v-list-item>
        </v-list>
      </template>
    </v-navigation-drawer>

    <!-- App Bar -->
    <v-app-bar app>
      <v-app-bar-nav-icon 
        v-if="auth.isAuthenticated.value" 
        @click="drawer = !drawer"
      />
      
      <v-toolbar-title>{{ pageTitle }}</v-toolbar-title>

      <v-spacer />

      <!-- User Menu (when authenticated) -->
      <div v-if="auth.isAuthenticated.value">
        <v-menu>
          <template v-slot:activator="{ props }">
            <v-btn
              icon="mdi-account-circle"
              v-bind="props"
            />
          </template>

          <v-list>
            <v-list-item>
              <v-list-item-content>
                <v-list-item-title>{{ auth.user.value?.full_name }}</v-list-item-title>
                <v-list-item-subtitle>{{ auth.user.value?.email }}</v-list-item-subtitle>
              </v-list-item-content>
            </v-list-item>

            <v-divider />

            <v-list-item @click="handleLogout">
              <template v-slot:prepend>
                <v-icon>mdi-logout</v-icon>
              </template>
              <v-list-item-title>Sign Out</v-list-item-title>
            </v-list-item>
          </v-list>
        </v-menu>
      </div>

      <!-- Login Button (when not authenticated) -->
      <div v-else>
        <v-btn
          variant="text"
          @click="$router.push('/login')"
          prepend-icon="mdi-login"
        >
          Sign In
        </v-btn>
      </div>
    </v-app-bar>

    <!-- Main Content -->
    <v-main>
      <!-- Show loading overlay when auth is loading -->
      <v-overlay v-if="auth.isLoading.value" class="d-flex align-center justify-center">
        <v-progress-circular indeterminate size="64" />
      </v-overlay>

      <v-container v-else :fluid="shouldBeFluid" class="pa-0">
        <router-view />
      </v-container>
    </v-main>

    <!-- Logout confirmation dialog -->
    <v-dialog v-model="showLogoutDialog" max-width="400">
      <v-card>
        <v-card-title>
          <v-icon left class="mr-2">mdi-logout</v-icon>
          Sign Out
        </v-card-title>
        
        <v-card-text>
          Are you sure you want to sign out?
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn 
            variant="text" 
            @click="showLogoutDialog = false"
          >
            Cancel
          </v-btn>
          <v-btn 
            color="primary" 
            variant="flat" 
            @click="confirmLogout"
            :loading="loggingOut"
          >
            Sign Out
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-app>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuth } from './composables/useAuth'

const drawer = ref(true)
const route = useRoute()
const router = useRouter()
const auth = useAuth()

// Logout dialog state
const showLogoutDialog = ref(false)
const loggingOut = ref(false)

const navigationItems = [
  { title: 'SharePoint Permissions', to: '/sharepoint', icon: 'mdi-folder-network', requiresAuth: true },
  { title: 'Permission Baselines', to: '/baselines', icon: 'mdi-shield-check', requiresAuth: true },
  { title: 'Purview Audit Logs', to: '/purview', icon: 'mdi-shield-search', requiresAuth: true },
  { title: 'Settings', to: '/settings', icon: 'mdi-cog', requiresAdmin: true },
  { title: 'Admin Panel', to: '/admin', icon: 'mdi-shield-account', requiresAdmin: true },
]

// Filter navigation items based on user permissions
const filteredNavigationItems = computed(() => {
  return navigationItems.filter(item => {
    if (item.requiresAdmin) {
      return auth.isAdmin.value
    }
    if (item.requiresAuth) {
      return auth.isAuthenticated.value
    }
    return true
  })
})

const pageTitle = computed(() => {
  const titles = {
    '/login': 'Sign In',
    '/register': 'Create Account',
    '/sharepoint': 'SharePoint Permissions Analysis',
    '/baselines': 'Permission Baselines',
    '/purview': 'Microsoft Purview Audit Logs',
    '/settings': 'Settings',
    '/admin': 'Admin Panel',
    '/admin/users': 'User Management',
  }
  return titles[route.path] || 'SimplyInspect'
})

// Determine if container should be fluid (full width with no padding)
const shouldBeFluid = computed(() => {
  // Make SharePoint page fluid for better space usage
  const fluidRoutes = ['/sharepoint', '/baselines', '/purview']
  return !auth.isAuthenticated.value || fluidRoutes.includes(route.path)
})

// Logout handlers
const handleLogout = () => {
  showLogoutDialog.value = true
}

const confirmLogout = async () => {
  loggingOut.value = true
  
  try {
    await auth.logout()
    showLogoutDialog.value = false
    router.push('/login')
  } catch (error) {
    console.error('Logout failed:', error)
  } finally {
    loggingOut.value = false
  }
}
</script>