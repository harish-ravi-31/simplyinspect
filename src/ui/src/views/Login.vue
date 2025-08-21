<template>
  <v-container class="fill-height d-flex align-center justify-center">
    <v-card
      class="elevation-12 mx-auto"
      max-width="400"
      width="100%"
    >
      <v-toolbar color="primary" dark flat>
        <v-toolbar-title class="text-h5 font-weight-bold">
          <v-icon left class="mr-2">mdi-login</v-icon>
          Sign In
        </v-toolbar-title>
      </v-toolbar>

      <v-card-subtitle class="text-center pt-4 pb-2">
        <v-icon size="48" color="primary" class="mb-2">mdi-shield-search</v-icon>
        <div class="text-h6">SimplyInspect</div>
        <div class="text-body-2">SharePoint & Purview Inspector</div>
      </v-card-subtitle>

      <v-card-text>
        <v-form ref="form" v-model="valid" @submit.prevent="handleLogin">
          <v-text-field
            v-model="credentials.email"
            label="Email Address"
            type="email"
            variant="outlined"
            :rules="[rules.required, rules.email]"
            :error-messages="fieldErrors.email"
            prepend-inner-icon="mdi-email"
            class="mb-3"
            @input="clearFieldError('email')"
          />

          <v-text-field
            v-model="credentials.password"
            label="Password"
            :type="showPassword ? 'text' : 'password'"
            variant="outlined"
            :rules="[rules.required]"
            :error-messages="fieldErrors.password"
            prepend-inner-icon="mdi-lock"
            :append-inner-icon="showPassword ? 'mdi-eye' : 'mdi-eye-off'"
            @click:append-inner="showPassword = !showPassword"
            class="mb-3"
            @input="clearFieldError('password')"
          />

          <v-checkbox
            v-model="rememberMe"
            label="Remember me"
            color="primary"
            hide-details
            class="mb-3"
          />

          <v-alert
            v-if="loginError"
            type="error"
            class="mb-3"
            closable
            @click:close="loginError = null"
          >
            {{ loginError }}
          </v-alert>

          <v-btn
            type="submit"
            color="primary"
            variant="flat"
            size="large"
            :loading="auth.isLoading.value"
            :disabled="!valid"
            block
            class="mb-3"
          >
            <v-icon left class="mr-2">mdi-login</v-icon>
            Sign In
          </v-btn>
        </v-form>
      </v-card-text>

      <v-divider />

      <v-card-actions class="justify-center pa-4">
        <div class="text-center">
          <p class="text-body-2 mb-2">Don't have an account?</p>
          <v-btn
            variant="text"
            color="primary"
            @click="$router.push('/register')"
          >
            Create Account
          </v-btn>
        </div>
      </v-card-actions>
    </v-card>
  </v-container>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuth } from '../composables/useAuth'

const router = useRouter()
const route = useRoute()
const auth = useAuth()

// Form data
const valid = ref(false)
const showPassword = ref(false)
const rememberMe = ref(false)
const loginError = ref(null)

const credentials = reactive({
  email: '',
  password: ''
})

const fieldErrors = reactive({
  email: [],
  password: []
})

// Validation rules
const rules = {
  required: value => !!value || 'Required',
  email: value => {
    const pattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    return pattern.test(value) || 'Invalid email address'
  }
}

// Methods
const clearFieldError = (field) => {
  fieldErrors[field] = []
  loginError.value = null
}

const handleLogin = async () => {
  if (!valid.value) return

  loginError.value = null
  fieldErrors.email = []
  fieldErrors.password = []

  const result = await auth.login(credentials, rememberMe.value)

  if (result.success) {
    // Redirect to the page they were trying to access or home
    const redirect = route.query.redirect || '/'
    router.push(redirect)
  } else {
    // Handle login errors
    if (result.validationErrors) {
      // Handle field-specific validation errors
      result.validationErrors.forEach(err => {
        if (err.loc && err.loc[1]) {
          const field = err.loc[1]
          if (fieldErrors[field]) {
            fieldErrors[field].push(err.msg)
          }
        }
      })
    } else {
      loginError.value = result.error
    }
  }
}

// Check if user is already logged in
onMounted(() => {
  if (auth.isAuthenticated.value) {
    // User is already logged in, redirect to home
    const redirect = route.query.redirect || '/'
    router.push(redirect)
  }
})
</script>

<style scoped>
.fill-height {
  min-height: 100vh;
  background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
}

.v-card {
  border-radius: 16px;
  overflow: hidden;
}

.v-toolbar {
  border-radius: 0;
}
</style>