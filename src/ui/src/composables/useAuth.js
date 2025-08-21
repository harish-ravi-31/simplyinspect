import { ref, computed } from 'vue'
import axios from 'axios'
import { apiClient } from '../services/api'

// Global auth state
const user = ref(null)
const token = ref(null)
const refreshToken = ref(null)
const tokenExpiry = ref(null)
const isAuthenticated = ref(false)
const isLoading = ref(false)
let refreshTimer = null

export function useAuth() {
  
  // Computed properties
  const isAdmin = computed(() => user.value?.role === 'administrator')
  const isReviewer = computed(() => user.value?.role === 'reviewer')
  const hasRole = (role) => user.value?.role === role

  // Parse JWT token to get expiry
  const parseJwt = (token) => {
    try {
      const base64Url = token.split('.')[1]
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
      const jsonPayload = decodeURIComponent(atob(base64).split('').map((c) => {
        return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)
      }).join(''))
      return JSON.parse(jsonPayload)
    } catch (error) {
      console.error('Error parsing JWT:', error)
      return null
    }
  }

  // Check if token is expired or about to expire
  const isTokenExpiring = (expiryTime, bufferMinutes = 5) => {
    if (!expiryTime) return true
    const now = Date.now() / 1000
    const buffer = bufferMinutes * 60
    return expiryTime - now <= buffer
  }

  // Schedule automatic token refresh
  const scheduleTokenRefresh = () => {
    // Clear any existing timer
    if (refreshTimer) {
      clearTimeout(refreshTimer)
    }

    if (!tokenExpiry.value || !refreshToken.value) return

    const now = Date.now() / 1000
    const timeUntilExpiry = tokenExpiry.value - now
    // Refresh 5 minutes before expiry
    const refreshIn = Math.max(0, (timeUntilExpiry - 300) * 1000)

    if (refreshIn > 0) {
      console.log(`Scheduling token refresh in ${refreshIn / 1000} seconds`)
      refreshTimer = setTimeout(async () => {
        await refreshAccessToken()
      }, refreshIn)
    }
  }

  // Refresh access token using refresh token
  const refreshAccessToken = async () => {
    const storedRefreshToken = refreshToken.value || 
      localStorage.getItem('refresh_token') || 
      sessionStorage.getItem('refresh_token')

    if (!storedRefreshToken) {
      console.log('No refresh token available')
      clearAuth()
      return false
    }

    try {
      console.log('Refreshing access token...')
      const response = await axios.post('/api/v1/auth/refresh', {
        refresh_token: storedRefreshToken
      })

      const { access_token, expires_in } = response.data
      
      // Update token and expiry
      token.value = access_token
      const newExpiry = Date.now() / 1000 + expires_in
      tokenExpiry.value = newExpiry

      // Update storage
      const storage = localStorage.getItem('auth_token') ? localStorage : sessionStorage
      storage.setItem('auth_token', access_token)
      storage.setItem('token_expiry', newExpiry.toString())

      // Update axios headers
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`
      apiClient.defaults.headers.common['Authorization'] = `Bearer ${access_token}`

      // Schedule next refresh
      scheduleTokenRefresh()

      console.log('Token refreshed successfully')
      return true
    } catch (error) {
      console.error('Token refresh failed:', error)
      clearAuth()
      return false
    }
  }

  // Initialize auth state from storage
  const initializeAuth = () => {
    const storedToken = localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token')
    const storedRefresh = localStorage.getItem('refresh_token') || sessionStorage.getItem('refresh_token')
    const storedUser = localStorage.getItem('user_info')
    const storedExpiry = localStorage.getItem('token_expiry') || sessionStorage.getItem('token_expiry')

    if (storedToken && storedUser) {
      try {
        token.value = storedToken
        refreshToken.value = storedRefresh
        user.value = JSON.parse(storedUser)
        
        // Parse token to get expiry if not stored
        if (storedExpiry) {
          tokenExpiry.value = parseFloat(storedExpiry)
        } else {
          const tokenData = parseJwt(storedToken)
          if (tokenData?.exp) {
            tokenExpiry.value = tokenData.exp
          }
        }

        // Check if token is expired
        if (tokenExpiry.value && isTokenExpiring(tokenExpiry.value, 0)) {
          console.log('Token expired on initialization, attempting refresh...')
          if (storedRefresh) {
            refreshAccessToken()
          } else {
            clearAuth()
            return
          }
        } else {
          isAuthenticated.value = true
          
          // Also ensure userRole is in localStorage for components that need it
          if (user.value?.role) {
            localStorage.setItem('userRole', user.value.role)
          }
          
          // Set axios default header for both axios and apiClient
          axios.defaults.headers.common['Authorization'] = `Bearer ${storedToken}`
          apiClient.defaults.headers.common['Authorization'] = `Bearer ${storedToken}`
          
          // Schedule token refresh if we have expiry info
          if (tokenExpiry.value && refreshToken.value) {
            scheduleTokenRefresh()
          }
        }
      } catch (error) {
        console.error('Failed to initialize auth from storage:', error)
        clearAuth()
      }
    }
  }

  // Validate current token
  const validateToken = async () => {
    if (!token.value) return false

    try {
      const response = await axios.get('/api/v1/auth/me')
      
      // Update user info from server
      user.value = response.data
      localStorage.setItem('user_info', JSON.stringify(response.data))
      
      return true
    } catch (error) {
      console.error('Token validation failed:', error)
      // Only clear auth on 401 errors, not on network errors
      if (error.response && error.response.status === 401) {
        clearAuth()
      }
      return false
    }
  }

  // Login function
  const login = async (credentials, rememberMe = false) => {
    isLoading.value = true
    
    try {
      const response = await axios.post('/api/v1/auth/login', {
        email: credentials.email.toLowerCase().trim(),
        password: credentials.password
      })

      const { tokens, user: userData } = response.data
      const { access_token, refresh_token: refresh_tok, expires_in } = tokens

      // Store token and user info
      token.value = access_token
      refreshToken.value = refresh_tok
      user.value = userData
      isAuthenticated.value = true

      // Calculate and store expiry
      const expiry = Date.now() / 1000 + (expires_in || 1800) // Default 30 min if not provided
      tokenExpiry.value = expiry

      // Persist to storage
      const storage = rememberMe ? localStorage : sessionStorage
      storage.setItem('auth_token', access_token)
      storage.setItem('refresh_token', refresh_tok)
      storage.setItem('token_expiry', expiry.toString())
      localStorage.setItem('user_info', JSON.stringify(userData))
      
      // Also store userRole separately for components that need it
      if (userData?.role) {
        localStorage.setItem('userRole', userData.role)
      }

      // Set up axios defaults for both axios and apiClient
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`
      apiClient.defaults.headers.common['Authorization'] = `Bearer ${access_token}`

      // Schedule automatic token refresh
      scheduleTokenRefresh()

      return { success: true }

    } catch (error) {
      console.error('Login failed:', error)
      
      let message = 'Login failed. Please try again.'
      
      if (error.response?.status === 401) {
        const errorDetail = error.response.data?.detail || ''
        
        if (errorDetail.includes('not approved')) {
          message = 'Your account is pending approval. Please contact an administrator.'
        } else if (errorDetail.includes('inactive')) {
          message = 'Your account has been deactivated. Please contact an administrator.'
        } else if (errorDetail.includes('not found')) {
          message = 'No account found with this email address.'
        } else {
          message = 'Invalid email or password.'
        }
      } else if (error.response?.status >= 500) {
        message = 'Server error. Please try again later.'
      }
      
      // Normalize validation errors to an array to avoid UI forEach type errors
      const detail = error.response?.data?.detail
      const validationErrors = Array.isArray(detail) ? detail : []
      return { 
        success: false, 
        error: message,
        validationErrors
      }
      
    } finally {
      isLoading.value = false
    }
  }

  // Logout function
  const logout = async () => {
    isLoading.value = true

    try {
      // Call logout endpoint to invalidate server session
      if (token.value) {
        await axios.post('/api/v1/auth/logout')
      }
    } catch (error) {
      console.error('Logout request failed:', error)
      // Continue with local logout even if server request fails
    } finally {
      clearAuth()
      isLoading.value = false
    }
  }

  // Clear authentication state
  const clearAuth = () => {
    token.value = null
    refreshToken.value = null
    tokenExpiry.value = null
    user.value = null
    isAuthenticated.value = false
    
    // Clear refresh timer
    if (refreshTimer) {
      clearTimeout(refreshTimer)
      refreshTimer = null
    }
    
    // Clear storage
    localStorage.removeItem('auth_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('token_expiry')
    localStorage.removeItem('user_info')
    localStorage.removeItem('userRole')
    sessionStorage.removeItem('auth_token')
    sessionStorage.removeItem('refresh_token')
    sessionStorage.removeItem('token_expiry')
    
    // Clear axios default header for both axios and apiClient
    delete axios.defaults.headers.common['Authorization']
    delete apiClient.defaults.headers.common['Authorization']
  }

  // Register function
  const register = async (registrationData) => {
    isLoading.value = true
    
    try {
      const payload = {
        ...registrationData,
        email: registrationData.email.toLowerCase().trim(),
        username: registrationData.username.toLowerCase().trim()
      }

      await axios.post('/api/v1/auth/register', payload)
      
      return { success: true }

    } catch (error) {
      console.error('Registration failed:', error)
      
      let message = 'Registration failed. Please try again.'
      let fieldErrors = {}
      
      if (error.response?.status === 409) {
        const errorDetail = error.response.data?.detail || ''
        
        if (errorDetail.includes('email')) {
          fieldErrors.email = ['An account with this email address already exists']
        } else if (errorDetail.includes('username')) {
          fieldErrors.username = ['This username is already taken']
        } else {
          message = 'An account with these details already exists.'
        }
      } else if (error.response?.status === 422) {
        // Validation errors
        const validationErrors = error.response.data?.detail || []
        validationErrors.forEach(err => {
          if (err.loc && err.loc[1]) {
            const field = err.loc[1]
            if (!fieldErrors[field]) fieldErrors[field] = []
            fieldErrors[field].push(err.msg)
          }
        })
        
        if (!validationErrors.length) {
          message = 'Please check your input and try again.'
        }
      } else if (error.response?.status >= 500) {
        message = 'Server error. Please try again later.'
      } else {
        message = error.response?.data?.detail || message
      }
      
      return { 
        success: false, 
        error: message,
        fieldErrors
      }
      
    } finally {
      isLoading.value = false
    }
  }

  // Change password function
  const changePassword = async (currentPassword, newPassword) => {
    isLoading.value = true
    
    try {
      await axios.put('/api/v1/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword
      })
      
      return { success: true }

    } catch (error) {
      console.error('Password change failed:', error)
      
      let message = 'Failed to change password. Please try again.'
      
      if (error.response?.status === 400) {
        message = error.response.data?.detail || 'Current password is incorrect.'
      } else if (error.response?.status === 422) {
        message = 'Password does not meet requirements.'
      } else if (error.response?.status >= 500) {
        message = 'Server error. Please try again later.'
      }
      
      return { 
        success: false, 
        error: message 
      }
      
    } finally {
      isLoading.value = false
    }
  }

  // Refresh user profile
  const refreshProfile = async () => {
    if (!isAuthenticated.value) return false
    
    try {
      const response = await axios.get('/api/v1/auth/me')
      user.value = response.data
      localStorage.setItem('user_info', JSON.stringify(response.data))
      return true
    } catch (error) {
      console.error('Failed to refresh profile:', error)
      return false
    }
  }

  // Setup axios interceptors for automatic token handling
  const setupAxiosInterceptors = () => {
    // Request interceptor to add token
    axios.interceptors.request.use(
      (config) => {
        const currentToken = token.value || 
          localStorage.getItem('auth_token') || 
          sessionStorage.getItem('auth_token')
        
        if (currentToken) {
          config.headers.Authorization = `Bearer ${currentToken}`
        }
        
        return config
      },
      (error) => Promise.reject(error)
    )

    // Response interceptor to handle 401 errors with automatic retry
    axios.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config
        
        if (error.response?.status === 401 && isAuthenticated.value && !originalRequest._retry) {
          console.log('Token expired, attempting to refresh...')
          originalRequest._retry = true
          
          // Try to refresh the token
          const refreshed = await refreshAccessToken()
          
          if (refreshed) {
            // Retry the original request with new token
            originalRequest.headers.Authorization = `Bearer ${token.value}`
            return axios(originalRequest)
          } else {
            // Refresh failed, clear auth and redirect
            clearAuth()
            if (window.location.pathname !== '/login') {
              window.location.href = '/login'
            }
          }
        }
        return Promise.reject(error)
      }
    )
  }

  return {
    // State
    user: computed(() => user.value),
    token: computed(() => token.value),
    isAuthenticated: computed(() => isAuthenticated.value),
    isLoading: computed(() => isLoading.value),
    isAdmin,
    isReviewer,
    
    // Methods
    initializeAuth,
    validateToken,
    login,
    logout,
    register,
    changePassword,
    refreshProfile,
    hasRole,
    setupAxiosInterceptors,
    clearAuth
  }
}