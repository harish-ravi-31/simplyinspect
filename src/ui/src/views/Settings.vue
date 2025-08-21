<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <h1 class="text-h4 mb-4">Settings</h1>
      </v-col>
    </v-row>

    <v-row>
      <v-col cols="12" md="8">
        <v-card>
          <v-card-title>
            <v-icon left class="mr-2">mdi-microsoft-azure</v-icon>
            Azure Configuration
          </v-card-title>
          
          <v-card-subtitle>
            Configure Azure AD credentials for SharePoint and Purview access
          </v-card-subtitle>

          <v-card-text>
            <v-form ref="form" v-model="valid">
              <v-text-field
                v-model="config.tenant_id"
                label="Tenant ID"
                hint="Your Azure AD Tenant ID (GUID)"
                persistent-hint
                :rules="[rules.required, rules.guid]"
                variant="outlined"
                class="mb-3"
              />

              <v-text-field
                v-model="config.client_id"
                label="Client ID (Application ID)"
                hint="The Application (Client) ID from Azure AD"
                persistent-hint
                :rules="[rules.required, rules.guid]"
                variant="outlined"
                class="mb-3"
              />

              <v-text-field
                v-model="config.client_secret"
                :label="secretLabel"
                :hint="secretHint"
                persistent-hint
                :rules="secretRules"
                :type="showSecret ? 'text' : 'password'"
                variant="outlined"
                class="mb-3"
                :append-inner-icon="showSecret ? 'mdi-eye' : 'mdi-eye-off'"
                @click:append-inner="showSecret = !showSecret"
              />

            </v-form>

            <v-alert
              v-if="testResult"
              :type="testResult.status === 'success' ? 'success' : 'error'"
              class="mb-3"
              closable
              @click:close="testResult = null"
            >
              {{ testResult.message }}
            </v-alert>

            <v-alert
              v-if="saveResult"
              :type="saveResult.status === 'success' ? 'success' : 'error'"
              class="mb-3"
              closable
              @click:close="saveResult = null"
            >
              {{ saveResult.message }}
            </v-alert>
          </v-card-text>

          <v-card-actions>
            <v-spacer />
            <v-btn
              color="primary"
              variant="outlined"
              @click="testConfiguration"
              :loading="testing"
              :disabled="!valid || saving"
            >
              <v-icon left class="mr-2">mdi-connection</v-icon>
              Test Connection
            </v-btn>
            <v-btn
              color="primary"
              variant="flat"
              @click="saveConfiguration"
              :loading="saving"
              :disabled="!valid || testing"
            >
              <v-icon left class="mr-2">mdi-content-save</v-icon>
              Save Configuration
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>

      <v-col cols="12" md="4">
        <v-card>
          <v-card-title>
            <v-icon left class="mr-2">mdi-information-outline</v-icon>
            Configuration Help
          </v-card-title>
          
          <v-card-text>
            <h4 class="text-h6 mb-2">Required Permissions</h4>
            <v-list dense>
              <v-list-item>
                <v-list-item-content>
                  <v-list-item-title>Sites.Read.All</v-list-item-title>
                  <v-list-item-subtitle>SharePoint site access</v-list-item-subtitle>
                </v-list-item-content>
              </v-list-item>
              <v-list-item>
                <v-list-item-content>
                  <v-list-item-title>Group.Read.All</v-list-item-title>
                  <v-list-item-subtitle>Group membership reading</v-list-item-subtitle>
                </v-list-item-content>
              </v-list-item>
              <v-list-item>
                <v-list-item-content>
                  <v-list-item-title>AuditLog.Read.All</v-list-item-title>
                  <v-list-item-subtitle>Purview audit logs</v-list-item-subtitle>
                </v-list-item-content>
              </v-list-item>
            </v-list>

            <h4 class="text-h6 mb-2 mt-4">Where to Find Values</h4>
            <p class="text-body-2 mb-2">
              <strong>Tenant ID:</strong> Azure Portal → Azure Active Directory → Overview
            </p>
            <p class="text-body-2 mb-2">
              <strong>Client ID:</strong> Azure Portal → App Registrations → Your App → Overview
            </p>
            <p class="text-body-2 mb-2">
              <strong>Client Secret:</strong> Azure Portal → App Registrations → Your App → Certificates & Secrets
            </p>
            
            <v-alert type="info" density="compact" class="mt-3">
              Client secrets expire and need to be renewed periodically
            </v-alert>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-row class="mt-4">
      <v-col cols="12">
        <v-card>
          <v-card-title>
            <v-icon left class="mr-2">mdi-shield-check</v-icon>
            Configuration Status
          </v-card-title>
          
          <v-card-text>
            <v-list>
              <v-list-item>
                <template v-slot:prepend>
                  <v-icon :color="originalConfig.tenant_id ? 'success' : 'error'">
                    {{ originalConfig.tenant_id ? 'mdi-check-circle' : 'mdi-close-circle' }}
                  </v-icon>
                </template>
                <v-list-item-content>
                  <v-list-item-title>Tenant ID</v-list-item-title>
                  <v-list-item-subtitle>
                    {{ originalConfig.tenant_id || 'Not configured' }}
                  </v-list-item-subtitle>
                </v-list-item-content>
              </v-list-item>

              <v-list-item>
                <template v-slot:prepend>
                  <v-icon :color="originalConfig.client_id ? 'success' : 'error'">
                    {{ originalConfig.client_id ? 'mdi-check-circle' : 'mdi-close-circle' }}
                  </v-icon>
                </template>
                <v-list-item-content>
                  <v-list-item-title>Client ID</v-list-item-title>
                  <v-list-item-subtitle>
                    {{ originalConfig.client_id || 'Not configured' }}
                  </v-list-item-subtitle>
                </v-list-item-content>
              </v-list-item>

              <v-list-item>
                <template v-slot:prepend>
                  <v-icon :color="originalConfig.client_secret_configured ? 'success' : 'error'">
                    {{ originalConfig.client_secret_configured ? 'mdi-check-circle' : 'mdi-close-circle' }}
                  </v-icon>
                </template>
                <v-list-item-content>
                  <v-list-item-title>Client Secret</v-list-item-title>
                  <v-list-item-subtitle>
                    {{ originalConfig.client_secret_masked || 'Not configured' }}
                  </v-list-item-subtitle>
                </v-list-item-content>
              </v-list-item>

            </v-list>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'

// Data
const valid = ref(false)
const saving = ref(false)
const testing = ref(false)
const showSecret = ref(false)
const testResult = ref(null)
const saveResult = ref(null)

const config = ref({
  tenant_id: '',
  client_id: '',
  client_secret: ''
})

const originalConfig = ref({
  tenant_id: '',
  client_id: '',
  client_secret_configured: false,
  client_secret_masked: ''
})

// Computed
const secretLabel = computed(() => {
  if (originalConfig.value.client_secret_configured && !config.value.client_secret) {
    return 'Client Secret (leave blank to keep existing)'
  }
  return 'Client Secret'
})

const secretHint = computed(() => {
  if (originalConfig.value.client_secret_configured && !config.value.client_secret) {
    return `Current secret is configured: ${originalConfig.value.client_secret_masked}`
  }
  return 'The client secret from your Azure AD application'
})

const secretRules = computed(() => {
  if (originalConfig.value.client_secret_configured) {
    // Secret already exists, so new value is optional
    return []
  }
  // No secret exists, so it's required
  return [rules.required]
})

// Validation rules
const rules = {
  required: value => !!value || 'Required',
  guid: value => {
    const guidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
    return guidPattern.test(value) || 'Must be a valid GUID'
  },
  url: value => {
    try {
      new URL(value)
      return true
    } catch {
      return 'Must be a valid URL'
    }
  }
}

// Methods
const loadConfiguration = async () => {
  try {
    const response = await axios.get('/api/v1/configuration/azure')
    originalConfig.value = response.data
    
    // Set form values
    config.value = {
      tenant_id: response.data.tenant_id,
      client_id: response.data.client_id,
      client_secret: '' // Always start with empty secret
    }
  } catch (error) {
    console.error('Failed to load configuration:', error)
  }
}

const saveConfiguration = async () => {
  saving.value = true
  saveResult.value = null
  
  try {
    const response = await axios.put('/api/v1/configuration/azure', config.value)
    saveResult.value = response.data
    
    // Reload configuration to update the display
    await loadConfiguration()
  } catch (error) {
    console.error('Failed to save configuration:', error)
    saveResult.value = {
      status: 'error',
      message: error.response?.data?.detail || 'Failed to save configuration'
    }
  } finally {
    saving.value = false
  }
}

const testConfiguration = async () => {
  testing.value = true
  testResult.value = null
  
  // Save first if there are unsaved changes
  if (hasUnsavedChanges()) {
    await saveConfiguration()
  }
  
  try {
    const response = await axios.post('/api/v1/configuration/test')
    testResult.value = response.data
  } catch (error) {
    console.error('Failed to test configuration:', error)
    testResult.value = {
      status: 'error',
      message: error.response?.data?.detail || 'Failed to test configuration'
    }
  } finally {
    testing.value = false
  }
}

const hasUnsavedChanges = () => {
  return config.value.tenant_id !== originalConfig.value.tenant_id ||
         config.value.client_id !== originalConfig.value.client_id ||
         (config.value.client_secret && config.value.client_secret !== '')
}

// Lifecycle
onMounted(() => {
  loadConfiguration()
})
</script>