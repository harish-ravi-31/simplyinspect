<template>
  <v-container class="fill-height d-flex align-center justify-center">
    <v-card
      class="elevation-12 mx-auto"
      max-width="500"
      width="100%"
    >
      <v-toolbar color="primary" dark flat>
        <v-toolbar-title class="text-h5 font-weight-bold">
          <v-icon left class="mr-2">mdi-account-plus</v-icon>
          Create Account
        </v-toolbar-title>
      </v-toolbar>

      <v-card-subtitle class="text-center pt-4 pb-2">
        <v-icon size="48" color="primary" class="mb-2">mdi-shield-search</v-icon>
        <div class="text-h6">SimplyInspect</div>
        <div class="text-body-2">SharePoint & Purview Inspector</div>
      </v-card-subtitle>

      <v-card-text>
        <!-- Success message after registration -->
        <v-alert
          v-if="registrationSuccess"
          type="success"
          class="mb-4"
          prominent
        >
          <div class="text-h6 mb-2">Registration Successful!</div>
          <p class="mb-2">
            Your account has been created and is pending approval by an administrator.
          </p>
          <p class="text-body-2">
            You will receive a notification once your account is approved. This usually takes 1-2 business days.
          </p>
          
          <v-btn
            variant="text"
            color="white"
            @click="$router.push('/login')"
            class="mt-2"
          >
            <v-icon left class="mr-2">mdi-login</v-icon>
            Go to Sign In
          </v-btn>
        </v-alert>

        <!-- Registration form -->
        <v-form 
          v-else
          ref="form" 
          v-model="valid" 
          @submit.prevent="handleRegistration"
        >
          <!-- Personal Information -->
          <div class="text-h6 mb-3">Personal Information</div>
          
          <v-text-field
            v-model="registrationData.full_name"
            label="Full Name"
            variant="outlined"
            :rules="[rules.required, rules.minLength(2)]"
            :error-messages="fieldErrors.full_name"
            prepend-inner-icon="mdi-account"
            class="mb-3"
            @input="clearFieldError('full_name')"
          />

          <v-text-field
            v-model="registrationData.email"
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
            v-model="registrationData.username"
            label="Username"
            variant="outlined"
            :rules="[rules.required, rules.minLength(3), rules.username]"
            :error-messages="fieldErrors.username"
            prepend-inner-icon="mdi-account-circle"
            class="mb-3"
            hint="3-50 characters, letters, numbers, underscore and dash only"
            persistent-hint
            @input="clearFieldError('username')"
          />

          <!-- Organization Information -->
          <div class="text-h6 mb-3 mt-4">Organization</div>
          
          <v-text-field
            v-model="registrationData.company"
            label="Company"
            variant="outlined"
            :rules="[rules.required]"
            :error-messages="fieldErrors.company"
            prepend-inner-icon="mdi-domain"
            class="mb-3"
            @input="clearFieldError('company')"
          />

          <v-text-field
            v-model="registrationData.department"
            label="Department"
            variant="outlined"
            prepend-inner-icon="mdi-office-building"
            class="mb-3"
            hint="Optional"
            persistent-hint
          />

          <v-text-field
            v-model="registrationData.phone"
            label="Phone Number"
            variant="outlined"
            prepend-inner-icon="mdi-phone"
            class="mb-3"
            hint="Optional"
            persistent-hint
          />

          <!-- Password -->
          <div class="text-h6 mb-3 mt-4">Security</div>
          
          <v-text-field
            v-model="registrationData.password"
            label="Password"
            :type="showPassword ? 'text' : 'password'"
            variant="outlined"
            :rules="[rules.required, rules.password]"
            :error-messages="fieldErrors.password"
            prepend-inner-icon="mdi-lock"
            :append-inner-icon="showPassword ? 'mdi-eye' : 'mdi-eye-off'"
            @click:append-inner="showPassword = !showPassword"
            class="mb-3"
            hint="At least 8 characters with uppercase, lowercase, number, and special character"
            persistent-hint
            @input="clearFieldError('password')"
          />

          <v-text-field
            v-model="passwordConfirm"
            label="Confirm Password"
            :type="showConfirmPassword ? 'text' : 'password'"
            variant="outlined"
            :rules="[rules.required, rules.passwordMatch]"
            prepend-inner-icon="mdi-lock-check"
            :append-inner-icon="showConfirmPassword ? 'mdi-eye' : 'mdi-eye-off'"
            @click:append-inner="showConfirmPassword = !showConfirmPassword"
            class="mb-3"
          />

          <!-- Terms Agreement -->
          <v-checkbox
            v-model="agreeToTerms"
            color="primary"
            class="mb-3"
            :rules="[rules.mustAgree]"
          >
            <template v-slot:label>
              <span class="text-body-2">
                I agree to the Terms of Service and acknowledge that my account will be reviewed before activation
              </span>
            </template>
          </v-checkbox>

          <!-- Error Message -->
          <v-alert
            v-if="registrationError"
            type="error"
            class="mb-3"
            closable
            @click:close="registrationError = null"
          >
            {{ registrationError }}
          </v-alert>

          <!-- Submit Button -->
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
            <v-icon left class="mr-2">mdi-account-plus</v-icon>
            Create Account
          </v-btn>
        </v-form>
      </v-card-text>

      <v-divider v-if="!registrationSuccess" />

      <v-card-actions v-if="!registrationSuccess" class="justify-center pa-4">
        <div class="text-center">
          <p class="text-body-2 mb-2">Already have an account?</p>
          <v-btn
            variant="text"
            color="primary"
            @click="$router.push('/login')"
          >
            Sign In
          </v-btn>
        </div>
      </v-card-actions>
    </v-card>
  </v-container>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '../composables/useAuth'

const router = useRouter()
const auth = useAuth()

// Form data
const valid = ref(false)
const registrationSuccess = ref(false)
const showPassword = ref(false)
const showConfirmPassword = ref(false)
const agreeToTerms = ref(false)
const registrationError = ref(null)
const passwordConfirm = ref('')

const registrationData = reactive({
  full_name: '',
  email: '',
  username: '',
  password: '',
  company: '',
  department: '',
  phone: ''
})

const fieldErrors = reactive({
  full_name: [],
  email: [],
  username: [],
  password: [],
  company: []
})

// Validation rules
const rules = {
  required: value => !!value || 'Required',
  minLength: min => value => (value && value.length >= min) || `Minimum ${min} characters required`,
  email: value => {
    const pattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    return pattern.test(value) || 'Invalid email address'
  },
  username: value => {
    const pattern = /^[a-zA-Z0-9_-]{3,50}$/
    return pattern.test(value) || 'Username must be 3-50 characters, letters, numbers, underscore and dash only'
  },
  password: value => {
    if (!value) return 'Password is required'
    if (value.length < 8) return 'Password must be at least 8 characters'
    if (!/(?=.*[a-z])/.test(value)) return 'Password must contain at least one lowercase letter'
    if (!/(?=.*[A-Z])/.test(value)) return 'Password must contain at least one uppercase letter'
    if (!/(?=.*\d)/.test(value)) return 'Password must contain at least one number'
    if (!/(?=.*[!@#$%^&*(),.?":{}|<>])/.test(value)) return 'Password must contain at least one special character'
    return true
  },
  passwordMatch: value => (value === registrationData.password) || 'Passwords do not match',
  mustAgree: value => value === true || 'You must agree to the terms'
}

// Methods
const clearFieldError = (field) => {
  fieldErrors[field] = []
  registrationError.value = null
}

const handleRegistration = async () => {
  if (!valid.value) return

  registrationError.value = null
  
  // Clear field errors
  Object.keys(fieldErrors).forEach(key => {
    fieldErrors[key] = []
  })

  const result = await auth.register(registrationData)

  if (result.success) {
    registrationSuccess.value = true
  } else {
    // Handle registration errors
    if (result.fieldErrors) {
      Object.keys(result.fieldErrors).forEach(field => {
        if (fieldErrors[field]) {
          fieldErrors[field] = result.fieldErrors[field]
        }
      })
    } else {
      registrationError.value = result.error
    }
  }
}
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