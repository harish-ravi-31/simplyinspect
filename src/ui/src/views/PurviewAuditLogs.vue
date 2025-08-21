<template>
  <v-container fluid class="fill-height">
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title>
            <v-icon left color="primary" class="mr-2">mdi-shield-search</v-icon>
            Microsoft Purview Audit Logs
          </v-card-title>
          
          <v-card-text>
            <!-- External Audit Logs Content -->
            <v-row>
              <v-col cols="12">
                <v-card outlined>
                  <v-card-title class="text-subtitle-1">
                    <v-icon left color="purple darken-2">mdi-shield-account</v-icon>
                    External Audit Log Collection
                  </v-card-title>
                  <v-card-text>
                    <p class="mb-4">
                      Configure and manage external audit log collection from Microsoft Purview and other sources.
                    </p>
                    
                    <!-- Source Configuration -->
                    <v-expansion-panels class="mb-4">
                      <v-expansion-panel>
                        <v-expansion-panel-header>
                          <div>
                            <v-icon left>mdi-microsoft</v-icon>
                            Microsoft Purview Configuration
                          </div>
                        </v-expansion-panel-header>
                        <v-expansion-panel-content>
                          <v-alert type="info" outlined class="mb-3">
                            Microsoft Purview provides unified data governance and compliance audit logs across Microsoft 365 services.
                          </v-alert>
                          
                          <v-alert v-if="!hasCredentials" type="warning" outlined class="mb-3">
                            <div class="d-flex align-center">
                              <v-icon left>mdi-alert</v-icon>
                              No Azure credentials configured. 
                              <v-btn
                                text
                                color="primary"
                                class="ml-2"
                                @click="$router.push('/settings')"
                              >
                                Configure in Settings
                              </v-btn>
                            </div>
                          </v-alert>
                          
                          <div v-if="hasCredentials">
                            <v-list dense>
                              <v-list-item>
                                <v-list-item-content>
                                  <v-list-item-title>Tenant ID</v-list-item-title>
                                  <v-list-item-subtitle>{{ purviewConfig.tenantId || 'Not configured' }}</v-list-item-subtitle>
                                </v-list-item-content>
                              </v-list-item>
                              <v-list-item>
                                <v-list-item-content>
                                  <v-list-item-title>Client ID</v-list-item-title>
                                  <v-list-item-subtitle>{{ purviewConfig.clientId || 'Not configured' }}</v-list-item-subtitle>
                                </v-list-item-content>
                              </v-list-item>
                              <v-list-item>
                                <v-list-item-content>
                                  <v-list-item-title>Client Secret</v-list-item-title>
                                  <v-list-item-subtitle>{{ purviewConfig.clientSecretMasked || 'Not configured' }}</v-list-item-subtitle>
                                </v-list-item-content>
                              </v-list-item>
                            </v-list>
                            
                            <v-select
                              v-model="purviewConfig.contentTypes"
                              label="Content Types"
                              :items="contentTypeOptions"
                              multiple
                              chips
                              small-chips
                              outlined
                              dense
                              class="mt-3"
                              hint="Select audit log types to collect"
                              persistent-hint
                            ></v-select>
                            
                            <v-row class="mt-3">
                              <v-col>
                                <v-btn color="primary" @click="testPurviewConnection">
                                  <v-icon left>mdi-connection</v-icon>
                                  Test Connection
                                </v-btn>
                              </v-col>
                              <v-col>
                                <v-btn 
                                  text
                                  color="primary"
                                  @click="$router.push('/settings')"
                                >
                                  <v-icon left>mdi-cog</v-icon>
                                  Manage Credentials
                                </v-btn>
                              </v-col>
                            </v-row>
                          </div>
                        </v-expansion-panel-content>
                      </v-expansion-panel>
                    </v-expansion-panels>
                    
                    <!-- Collection Status -->
                    <v-card outlined class="mb-4">
                      <v-card-title class="text-subtitle-2">
                        Collection Status
                      </v-card-title>
                      <v-card-text>
                        <v-simple-table>
                          <template v-slot:default>
                            <thead>
                              <tr>
                                <th>Source</th>
                                <th>Status</th>
                                <th>Last Sync</th>
                                <th>Records</th>
                                <th>Actions</th>
                              </tr>
                            </thead>
                            <tbody>
                              <tr v-for="source in auditSources" :key="source.id">
                                <td>{{ source.name }}</td>
                                <td>
                                  <v-chip
                                    :color="getStatusColor(source.status)"
                                    small
                                    dark
                                  >
                                    {{ source.status }}
                                  </v-chip>
                                </td>
                                <td>{{ formatDate(source.lastSync) }}</td>
                                <td>{{ source.recordCount || 0 }}</td>
                                <td>
                                  <v-btn
                                    icon
                                    small
                                    @click="syncSource(source)"
                                    :loading="source.syncing"
                                  >
                                    <v-icon>mdi-sync</v-icon>
                                  </v-btn>
                                  <v-btn
                                    icon
                                    small
                                    @click="viewSourceLogs(source)"
                                  >
                                    <v-icon>mdi-eye</v-icon>
                                  </v-btn>
                                </td>
                              </tr>
                            </tbody>
                          </template>
                        </v-simple-table>
                      </v-card-text>
                    </v-card>
                    
                    <!-- Manual Collection -->
                    <v-card outlined>
                      <v-card-title class="text-subtitle-2">
                        Manual Collection
                      </v-card-title>
                      <v-card-text>
                        <v-alert type="info" density="compact" class="mb-3">
                          <v-icon slot="prepend">mdi-information</v-icon>
                          Microsoft Purview API limits audit log collection to 24-hour periods at a time.
                        </v-alert>
                        <v-row align="center">
                          <v-col cols="12" md="6">
                            <div class="d-flex align-center">
                              <v-text-field
                                v-model="collectionDateRange"
                                label="Date Range (24-hour max)"
                                prepend-icon="mdi-calendar"
                                readonly
                                variant="outlined"
                                density="compact"
                                hint="Click to select a date range (max 24 hours)"
                                persistent-hint
                                @focus="openDatePicker"
                                @click:control="openDatePicker"
                                @click:prepend="openDatePicker"
                                style="cursor: pointer;"
                              ></v-text-field>
                              <v-btn
                                icon="mdi-calendar-edit"
                                variant="text"
                                @click="openDatePicker"
                                class="ml-2"
                              ></v-btn>
                            </div>
                            
                            <v-dialog
                              v-model="dateMenu"
                              max-width="400px"
                            >
                              <v-card>
                                <v-card-title>Select Date Range</v-card-title>
                                <v-card-text>
                                  <v-date-picker
                                    v-model="selectedDates"
                                    multiple="range"
                                    show-adjacent-months
                                  ></v-date-picker>
                                </v-card-text>
                                <v-card-actions>
                                  <v-spacer></v-spacer>
                                  <v-btn
                                    variant="text"
                                    @click="dateMenu = false"
                                  >
                                    Cancel
                                  </v-btn>
                                  <v-btn
                                    variant="text"
                                    color="primary"
                                    @click="confirmDateSelection"
                                  >
                                    OK
                                  </v-btn>
                                </v-card-actions>
                              </v-card>
                            </v-dialog>
                          </v-col>
                          <v-col cols="12" md="6">
                            <v-row>
                              <v-col>
                                <v-btn
                                  color="primary"
                                  @click="triggerManualCollection"
                                  :loading="isCollecting"
                                  :disabled="!selectedDates || selectedDates.length === 0"
                                >
                                  <v-icon left>mdi-download</v-icon>
                                  Collect Audit Logs
                                </v-btn>
                              </v-col>
                              <v-col>
                                <v-menu offset-y>
                                  <template v-slot:activator="{ props }">
                                    <v-btn
                                      text
                                      v-bind="props"
                                    >
                                      <v-icon left>mdi-calendar-clock</v-icon>
                                      Quick Select
                                    </v-btn>
                                  </template>
                                  <v-list>
                                    <v-list-item @click="setDateRange('today')">
                                      <v-list-item-title>Today</v-list-item-title>
                                    </v-list-item>
                                    <v-list-item @click="setDateRange('yesterday')">
                                      <v-list-item-title>Yesterday</v-list-item-title>
                                    </v-list-item>
                                    <v-list-item @click="setDateRange('last24hours')">
                                      <v-list-item-title>Last 24 Hours</v-list-item-title>
                                    </v-list-item>
                                    <v-divider></v-divider>
                                    <v-list-item disabled>
                                      <v-list-item-title class="text-caption">Note: Purview API limits to 24-hour periods</v-list-item-title>
                                    </v-list-item>
                                  </v-list>
                                </v-menu>
                              </v-col>
                            </v-row>
                          </v-col>
                        </v-row>
                      </v-card-text>
                    </v-card>
                  </v-card-text>
                </v-card>
              </v-col>
            </v-row>
            
            <!-- Recent Audit Logs -->
            <v-row class="mt-4">
              <v-col cols="12">
                <v-card outlined>
                  <v-card-title class="text-subtitle-1">
                    <v-icon left color="indigo darken-2">mdi-format-list-bulleted</v-icon>
                    Recent Audit Logs
                  </v-card-title>
                  <v-card-text>
                    <v-data-table
                      :headers="auditLogHeaders"
                      :items="recentAuditLogs"
                      :loading="loadingLogs"
                      class="elevation-1"
                      :items-per-page="10"
                    >
                      <template v-slot:item.CreationTime="{ item }">
                        {{ formatDate(item.CreationTime) }}
                      </template>
                      <template v-slot:item.actions="{ item }">
                        <v-btn icon small @click="viewLogDetails(item)">
                          <v-icon>mdi-eye</v-icon>
                        </v-btn>
                      </template>
                    </v-data-table>
                  </v-card-text>
                </v-card>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
    
    <!-- Log Details Dialog -->
    <v-dialog v-model="detailsDialog" max-width="800px">
      <v-card>
        <v-card-title>
          Audit Log Details
          <v-spacer></v-spacer>
          <v-btn icon @click="detailsDialog = false">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-card-title>
        <v-card-text>
          <pre>{{ JSON.stringify(selectedLog, null, 2) }}</pre>
        </v-card-text>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
import { ref, reactive, onMounted, computed, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import apiClient from '../services/api'

const router = useRouter()
const emit = defineEmits(['show-message'])

// Purview Configuration
const purviewConfig = reactive({
  tenantId: '',
  clientId: '',
  clientSecretMasked: '',
  contentTypes: ['Audit.AzureActiveDirectory', 'Audit.SharePoint', 'Audit.Exchange']
})

const hasCredentials = ref(false)

// Content Type Options
const contentTypeOptions = [
  'Audit.AzureActiveDirectory',
  'Audit.SharePoint',
  'Audit.Exchange',
  'Audit.General',
  'DLP.All'
]

// Audit Sources
const auditSources = ref([])

// Recent Logs
const recentAuditLogs = ref([])
const loadingLogs = ref(false)

// Table Headers
const auditLogHeaders = [
  { text: 'Time', value: 'CreationTime' },
  { text: 'Operation', value: 'Operation' },
  { text: 'User', value: 'UserId' },
  { text: 'Workload', value: 'Workload' },
  { text: 'Result', value: 'ResultStatus' },
  { text: 'Actions', value: 'actions', sortable: false }
]

// UI State
const dateMenu = ref(false)
const selectedDates = ref([])
const collectionDateRange = ref('')
const isCollecting = ref(false)
const detailsDialog = ref(false)
const selectedLog = ref(null)

// Methods
const openDatePicker = () => {
  console.log('Opening date picker - clicked')
  console.log('Current dateMenu value:', dateMenu.value)
  dateMenu.value = true
  console.log('New dateMenu value:', dateMenu.value)
  // Force update
  nextTick(() => {
    console.log('After nextTick dateMenu value:', dateMenu.value)
  })
}

const confirmDateSelection = () => {
  console.log('Confirming date selection:', selectedDates.value)
  updateDateRange()
  dateMenu.value = false
}

const updateDateRange = () => {
  console.log('Updating date range:', selectedDates.value)
  if (selectedDates.value && selectedDates.value.length >= 2) {
    // Sort dates to ensure correct order
    const sortedDates = [...selectedDates.value].sort()
    selectedDates.value = [sortedDates[0], sortedDates[sortedDates.length - 1]]
    collectionDateRange.value = `${sortedDates[0]} to ${sortedDates[sortedDates.length - 1]}`
  } else if (selectedDates.value && selectedDates.value.length === 1) {
    // Single date selected, use it for both start and end
    collectionDateRange.value = `${selectedDates.value[0]} to ${selectedDates.value[0]}`
  }
}

const setDateRange = (preset) => {
  const today = new Date()
  const formatDate = (date) => {
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
  }
  
  let startDate, endDate
  
  switch(preset) {
    case 'today':
      startDate = endDate = formatDate(today)
      break
    case 'yesterday':
      const yesterday = new Date(today)
      yesterday.setDate(yesterday.getDate() - 1)
      startDate = endDate = formatDate(yesterday)
      break
    case 'last24hours':
      // Last 24 hours means yesterday to today
      const yesterday24 = new Date(today)
      yesterday24.setDate(yesterday24.getDate() - 1)
      startDate = formatDate(yesterday24)
      endDate = formatDate(today)
      break
    case 'last7days':
      const week = new Date(today)
      week.setDate(week.getDate() - 6)
      startDate = formatDate(week)
      endDate = formatDate(today)
      break
    case 'last30days':
      const month = new Date(today)
      month.setDate(month.getDate() - 29)
      startDate = formatDate(month)
      endDate = formatDate(today)
      break
    case 'thisMonth':
      const firstDay = new Date(today.getFullYear(), today.getMonth(), 1)
      startDate = formatDate(firstDay)
      endDate = formatDate(today)
      break
    case 'lastMonth':
      const lastMonthEnd = new Date(today.getFullYear(), today.getMonth(), 0)
      const lastMonthStart = new Date(today.getFullYear(), today.getMonth() - 1, 1)
      startDate = formatDate(lastMonthStart)
      endDate = formatDate(lastMonthEnd)
      break
  }
  
  selectedDates.value = [startDate, endDate]
  collectionDateRange.value = `${startDate} to ${endDate}`
}

const loadPurviewConfig = async () => {
  try {
    const response = await axios.get('/api/v1/configuration/azure')
    console.log('Purview config response:', response.data)
    if (response.data) {
      purviewConfig.tenantId = response.data.tenant_id
      purviewConfig.clientId = response.data.client_id
      purviewConfig.clientSecretMasked = response.data.client_secret_masked
      
      // Check if credentials are configured
      hasCredentials.value = !!(
        response.data.tenant_id && 
        response.data.client_id && 
        response.data.client_secret_configured
      )
      console.log('hasCredentials:', hasCredentials.value)
    }
  } catch (error) {
    console.error('Failed to load Purview config:', error)
    hasCredentials.value = false
  }
}

const loadAuditSources = async () => {
  try {
    const response = await apiClient.get('/external-audit-logs/sources')
    auditSources.value = response.data.sources || []
  } catch (error) {
    console.error('Failed to load audit sources:', error)
    // Set default source if API fails
    auditSources.value = [{
      id: 1,
      name: 'Microsoft Purview',
      status: 'configured',
      lastSync: null,
      recordCount: 0
    }]
  }
}

const loadRecentLogs = async () => {
  loadingLogs.value = true
  try {
    const response = await apiClient.get('/external-audit-logs/recent', {
      params: { limit: 100 }
    })
    recentAuditLogs.value = response.data.logs || []
    
    // Set default date range based on whether logs exist
    if (recentAuditLogs.value.length > 0) {
      // If logs exist, default to last 24 hours
      setDateRange('last24hours')
    } else {
      // If no logs, default to last 7 days
      setDateRange('last7days')
    }
  } catch (error) {
    console.error('Failed to load recent logs:', error)
    recentAuditLogs.value = []
    // Default to last 7 days if error
    setDateRange('last7days')
  } finally {
    loadingLogs.value = false
  }
}

const testPurviewConnection = async () => {
  try {
    const response = await axios.post('/api/v1/configuration/test')
    if (response.data.status === 'success') {
      emit('show-message', {
        message: 'Connection successful!',
        color: 'success'
      })
    } else {
      emit('show-message', {
        message: response.data.message || 'Connection failed',
        color: 'error'
      })
    }
  } catch (error) {
    emit('show-message', {
      message: 'Failed to test connection',
      color: 'error'
    })
  }
}

const syncSource = async (source) => {
  source.syncing = true
  try {
    await apiClient.post(`/external-audit-logs/sync/${source.id}`)
    emit('show-message', {
      message: `Sync started for ${source.name}`,
      color: 'info'
    })
    // Reload sources after sync
    setTimeout(() => loadAuditSources(), 2000)
  } catch (error) {
    emit('show-message', {
      message: `Failed to sync ${source.name}`,
      color: 'error'
    })
  } finally {
    source.syncing = false
  }
}

const triggerManualCollection = async () => {
  if (!selectedDates.value || selectedDates.value.length === 0) {
    emit('show-message', {
      message: 'Please select a date range',
      color: 'warning'
    })
    return
  }
  
  // Get the selected dates
  const dates = selectedDates.value.length === 1 
    ? [selectedDates.value[0], selectedDates.value[0]]
    : selectedDates.value
  
  // Check if date range is within 24 hours (Purview API limitation)
  const startDate = new Date(dates[0])
  const endDate = new Date(dates[dates.length - 1])
  const diffInHours = Math.abs(endDate - startDate) / (1000 * 60 * 60)
  
  if (diffInHours > 24) {
    emit('show-message', {
      message: 'Date range cannot exceed 24 hours due to Purview API limitations. Please select a shorter range.',
      color: 'warning'
    })
    return
  }
  
  isCollecting.value = true
  try {
    await apiClient.post('/external-audit-logs/collect', {
      start_date: dates[0],
      end_date: dates[dates.length - 1]
    })
    
    emit('show-message', {
      message: 'Collection started successfully',
      color: 'success'
    })
    
    // Reload logs after collection
    setTimeout(() => loadRecentLogs(), 3000)
  } catch (error) {
    emit('show-message', {
      message: 'Failed to start collection',
      color: 'error'
    })
  } finally {
    isCollecting.value = false
  }
}

const viewSourceLogs = (source) => {
  // Navigate to filtered log view
  router.push({
    path: '/purview',
    query: { source: source.id }
  })
}

const viewLogDetails = (log) => {
  selectedLog.value = log
  detailsDialog.value = true
}

const formatDate = (date) => {
  if (!date) return 'Never'
  return new Date(date).toLocaleString()
}

const getStatusColor = (status) => {
  const colors = {
    active: 'success',
    configured: 'info',
    error: 'error',
    inactive: 'grey'
  }
  return colors[status] || 'grey'
}

// Initialize
onMounted(() => {
  loadAuditSources()
  loadPurviewConfig()
  // Load recent logs will set the appropriate date range
  loadRecentLogs()
})
</script>

<style scoped>
.v-expansion-panel-content__wrap {
  padding: 16px;
}

pre {
  background-color: #f5f5f5;
  padding: 12px;
  border-radius: 4px;
  overflow-x: auto;
}
</style>