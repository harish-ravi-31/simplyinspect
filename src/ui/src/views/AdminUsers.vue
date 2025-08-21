<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <h1 class="text-h4 mb-4">User Management</h1>
      </v-col>
    </v-row>

    <!-- Summary Cards -->
    <v-row class="mb-4">
      <v-col cols="12" sm="6" md="3">
        <v-card color="orange">
          <v-card-text class="text-white">
            <div class="text-h4">{{ stats.pending_count || 0 }}</div>
            <div class="text-subtitle1">Pending Approval</div>
          </v-card-text>
        </v-card>
      </v-col>
      
      <v-col cols="12" sm="6" md="3">
        <v-card color="success">
          <v-card-text class="text-white">
            <div class="text-h4">{{ stats.active_count || 0 }}</div>
            <div class="text-subtitle1">Active Users</div>
          </v-card-text>
        </v-card>
      </v-col>
      
      <v-col cols="12" sm="6" md="3">
        <v-card color="primary">
          <v-card-text class="text-white">
            <div class="text-h4">{{ stats.total_count || 0 }}</div>
            <div class="text-subtitle1">Total Users</div>
          </v-card-text>
        </v-card>
      </v-col>
      
      <v-col cols="12" sm="6" md="3">
        <v-card color="info">
          <v-card-text class="text-white">
            <div class="text-h4">{{ adminCount }}</div>
            <div class="text-subtitle1">Administrators</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Action Buttons -->
    <v-row class="mb-4">
      <v-col cols="12">
        <v-btn
          color="primary"
          @click="showCreateUserDialog = true"
          prepend-icon="mdi-account-plus"
        >
          Add New User
        </v-btn>
        
      </v-col>
    </v-row>

    <!-- Filters and Search -->
    <v-card class="mb-4">
      <v-card-title>
        <v-icon left class="mr-2">mdi-filter-variant</v-icon>
        Filters
      </v-card-title>
      
      <v-card-text>
        <v-row>
          <v-col cols="12" md="3">
            <v-select
              v-model="filters.status"
              label="Status"
              :items="statusOptions"
              clearable
              variant="outlined"
              density="compact"
              @update:model-value="loadUsers"
            />
          </v-col>
          
          <v-col cols="12" md="3">
            <v-select
              v-model="filters.role"
              label="Role"
              :items="roleOptions"
              clearable
              variant="outlined"
              density="compact"
              @update:model-value="loadUsers"
            />
          </v-col>
          
          <v-col cols="12" md="6">
            <v-text-field
              v-model="filters.search"
              label="Search users..."
              variant="outlined"
              density="compact"
              prepend-inner-icon="mdi-magnify"
              clearable
              @keyup.enter="loadUsers"
              @click:clear="clearSearch"
            />
          </v-col>
        </v-row>
        
        <v-row>
          <v-col cols="auto">
            <v-btn
              color="primary"
              variant="flat"
              @click="loadUsers"
              :loading="loading"
            >
              <v-icon left class="mr-2">mdi-magnify</v-icon>
              Search
            </v-btn>
          </v-col>
          
          <v-col cols="auto">
            <v-btn
              variant="outlined"
              @click="clearFilters"
            >
              <v-icon left class="mr-2">mdi-filter-remove</v-icon>
              Clear Filters
            </v-btn>
          </v-col>
          
          <v-spacer />
          
          <v-col cols="auto">
            <v-btn
              color="success"
              variant="flat"
              @click="loadPendingUsers"
            >
              <v-icon left class="mr-2">mdi-account-clock</v-icon>
              Show Pending ({{ stats.pending_count || 0 }})
            </v-btn>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- Users Table -->
    <v-card>
      <v-card-title>
        <v-icon left class="mr-2">mdi-account-group</v-icon>
        Users
        <v-spacer />
        <v-btn
          icon="mdi-refresh"
          variant="text"
          @click="loadUsers"
          :loading="loading"
        />
      </v-card-title>

      <v-data-table-server
        v-model:items-per-page="itemsPerPage"
        :headers="headers"
        :items="users"
        :items-length="totalItems"
        :loading="loading"
        :search="filters.search"
        @update:options="loadUsers"
        class="elevation-0"
      >
        <!-- User Info Column -->
        <template v-slot:item.user_info="{ item }">
          <div>
            <div class="text-subtitle-2">{{ item.full_name }}</div>
            <div class="text-body-2 text-grey">{{ item.email }}</div>
            <div class="text-caption text-grey">@{{ item.username }}</div>
          </div>
        </template>

        <!-- Status Column -->
        <template v-slot:item.status="{ item }">
          <v-chip
            :color="getStatusColor(item)"
            variant="flat"
            size="small"
          >
            {{ getStatusText(item) }}
          </v-chip>
        </template>

        <!-- Role Column -->
        <template v-slot:item.role="{ item }">
          <v-chip
            :color="item.role === 'administrator' ? 'purple' : 'blue'"
            variant="outlined"
            size="small"
          >
            {{ item.role }}
          </v-chip>
        </template>

        <!-- Organization Column -->
        <template v-slot:item.organization="{ item }">
          <div v-if="item.company">
            <div class="text-body-2">{{ item.company }}</div>
            <div v-if="item.department" class="text-caption text-grey">{{ item.department }}</div>
          </div>
          <div v-else class="text-grey text-body-2">Not specified</div>
        </template>

        <!-- Dates Column -->
        <template v-slot:item.dates="{ item }">
          <div>
            <div class="text-caption">
              <strong>Registered:</strong> {{ formatDate(item.created_at) }}
            </div>
            <div v-if="item.approved_at" class="text-caption">
              <strong>Approved:</strong> {{ formatDate(item.approved_at) }}
            </div>
            <div v-if="item.last_login" class="text-caption">
              <strong>Last Login:</strong> {{ formatDate(item.last_login) }}
            </div>
          </div>
        </template>

        <!-- Actions Column -->
        <template v-slot:item.actions="{ item }">
          <div class="d-flex gap-1">
            <!-- Approve/Reject buttons for pending users -->
            <template v-if="!item.is_approved && !item.approved_by">
              <v-btn
                icon="mdi-check"
                variant="text"
                color="success"
                size="small"
                @click="openApprovalDialog(item, true)"
                :loading="actionLoading[item.id]"
              />
              <v-btn
                icon="mdi-close"
                variant="text"
                color="error"
                size="small"
                @click="openApprovalDialog(item, false)"
                :loading="actionLoading[item.id]"
              />
            </template>

            <!-- Role change for approved users -->
            <v-btn
              v-if="item.is_approved"
              icon="mdi-account-cog"
              variant="text"
              color="primary"
              size="small"
              @click="openRoleDialog(item)"
              :disabled="item.id === auth.user.value?.id"
            />

            <!-- More actions menu -->
            <v-menu>
              <template v-slot:activator="{ props }">
                <v-btn
                  icon="mdi-dots-vertical"
                  variant="text"
                  size="small"
                  v-bind="props"
                />
              </template>

              <v-list density="compact">
                <v-list-item
                  @click="viewUserDetails(item)"
                  prepend-icon="mdi-account-details"
                >
                  View Details
                </v-list-item>
                
                <v-list-item
                  v-if="item.role === 'reviewer'"
                  @click="openLibraryAssignmentDialog(item)"
                  prepend-icon="mdi-folder-network"
                >
                  Assign Libraries
                </v-list-item>

                <v-list-item
                  v-if="item.is_active && item.id !== auth.user.value?.id"
                  @click="deactivateUser(item)"
                  prepend-icon="mdi-account-off"
                  class="text-error"
                >
                  Deactivate User
                </v-list-item>
              </v-list>
            </v-menu>
          </div>
        </template>

        <!-- No data -->
        <template v-slot:no-data>
          <div class="text-center py-4">
            <v-icon size="48" color="grey" class="mb-2">mdi-account-group</v-icon>
            <div class="text-h6">No users found</div>
            <div class="text-body-2">Try adjusting your search criteria</div>
          </div>
        </template>
      </v-data-table-server>
    </v-card>

    <!-- Approval Dialog -->
    <v-dialog v-model="approvalDialog.show" max-width="500">
      <v-card>
        <v-card-title>
          <v-icon :left="true" :color="approvalDialog.approve ? 'success' : 'error'" class="mr-2">
            {{ approvalDialog.approve ? 'mdi-check-circle' : 'mdi-close-circle' }}
          </v-icon>
          {{ approvalDialog.approve ? 'Approve User' : 'Reject User' }}
        </v-card-title>

        <v-card-text v-if="approvalDialog.user">
          <p class="mb-3">
            {{ approvalDialog.approve ? 'Approve' : 'Reject' }} registration for:
          </p>
          
          <div class="bg-grey-lighten-4 pa-3 rounded mb-3">
            <div class="text-subtitle-1 font-weight-bold">{{ approvalDialog.user.full_name }}</div>
            <div class="text-body-2">{{ approvalDialog.user.email }}</div>
            <div class="text-body-2">{{ approvalDialog.user.company }}</div>
            <div v-if="approvalDialog.user.department" class="text-body-2">
              {{ approvalDialog.user.department }}
            </div>
          </div>

          <v-textarea
            v-if="!approvalDialog.approve"
            v-model="approvalDialog.rejectionReason"
            label="Rejection Reason"
            placeholder="Please provide a reason for rejecting this user..."
            variant="outlined"
            rows="3"
            :rules="[v => !!v || 'Rejection reason is required']"
          />

          <div v-if="approvalDialog.approve" class="text-body-2 text-success">
            The user will receive a notification and can start using SimplyInspect immediately.
          </div>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn
            variant="text"
            @click="approvalDialog.show = false"
          >
            Cancel
          </v-btn>
          <v-btn
            :color="approvalDialog.approve ? 'success' : 'error'"
            variant="flat"
            @click="processApproval"
            :loading="approvalDialog.processing"
          >
            {{ approvalDialog.approve ? 'Approve' : 'Reject' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Role Change Dialog -->
    <v-dialog v-model="roleDialog.show" max-width="400">
      <v-card>
        <v-card-title>
          <v-icon left class="mr-2">mdi-account-cog</v-icon>
          Change User Role
        </v-card-title>

        <v-card-text v-if="roleDialog.user">
          <p class="mb-3">Change role for <strong>{{ roleDialog.user.full_name }}</strong>:</p>
          
          <v-radio-group v-model="roleDialog.newRole" :rules="[v => !!v || 'Please select a role']">
            <v-radio
              value="reviewer"
              label="Reviewer"
              color="blue"
            >
              <template v-slot:label>
                <div>
                  <div class="font-weight-bold">Reviewer</div>
                  <div class="text-caption text-grey">Can view and analyze data</div>
                </div>
              </template>
            </v-radio>
            
            <v-radio
              value="administrator"
              label="Administrator"
              color="purple"
            >
              <template v-slot:label>
                <div>
                  <div class="font-weight-bold">Administrator</div>
                  <div class="text-caption text-grey">Full access including user management</div>
                </div>
              </template>
            </v-radio>
          </v-radio-group>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn
            variant="text"
            @click="roleDialog.show = false"
          >
            Cancel
          </v-btn>
          <v-btn
            color="primary"
            variant="flat"
            @click="processRoleChange"
            :loading="roleDialog.processing"
            :disabled="!roleDialog.newRole"
          >
            Update Role
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Create User Dialog -->
    <v-dialog v-model="showCreateUserDialog" max-width="600">
      <v-card>
        <v-card-title class="text-h5 primary">
          <span class="text-white">Create New User</span>
        </v-card-title>
        
        <v-card-text class="pt-6">
          <v-form ref="createUserForm" v-model="createUserFormValid">
            <v-text-field
              v-model="newUser.email"
              label="Email Address"
              type="email"
              variant="outlined"
              density="compact"
              :rules="[rules.required, rules.email]"
              prepend-inner-icon="mdi-email"
              class="mb-3"
            />
            
            <v-text-field
              v-model="newUser.username"
              label="Username"
              variant="outlined"
              density="compact"
              :rules="[rules.required, rules.username]"
              prepend-inner-icon="mdi-account"
              class="mb-3"
            />
            
            <v-text-field
              v-model="newUser.full_name"
              label="Full Name"
              variant="outlined"
              density="compact"
              :rules="[rules.required]"
              prepend-inner-icon="mdi-account-circle"
              class="mb-3"
            />
            
            <v-text-field
              v-model="newUser.password"
              label="Password"
              :type="showPassword ? 'text' : 'password'"
              variant="outlined"
              density="compact"
              :rules="[rules.required, rules.password]"
              prepend-inner-icon="mdi-lock"
              :append-inner-icon="showPassword ? 'mdi-eye-off' : 'mdi-eye'"
              @click:append-inner="showPassword = !showPassword"
              class="mb-3"
            />
            
            <v-text-field
              v-model="newUser.department"
              label="Department (Optional)"
              variant="outlined"
              density="compact"
              prepend-inner-icon="mdi-office-building"
              class="mb-3"
            />
            
            <v-text-field
              v-model="newUser.company"
              label="Company (Optional)"
              variant="outlined"
              density="compact"
              prepend-inner-icon="mdi-domain"
              class="mb-3"
            />
            
            <v-text-field
              v-model="newUser.phone"
              label="Phone (Optional)"
              variant="outlined"
              density="compact"
              prepend-inner-icon="mdi-phone"
              class="mb-3"
            />
            
            <v-select
              v-model="newUser.role"
              label="Role"
              :items="['reviewer', 'administrator']"
              variant="outlined"
              density="compact"
              prepend-inner-icon="mdi-shield-account"
              class="mb-3"
            />
            
            <v-alert
              v-if="createUserError"
              type="error"
              density="compact"
              class="mb-3"
            >
              {{ createUserError }}
            </v-alert>
          </v-form>
        </v-card-text>
        
        <v-card-actions>
          <v-spacer />
          <v-btn
            @click="closeCreateUserDialog"
            :disabled="createUserLoading"
          >
            Cancel
          </v-btn>
          <v-btn
            color="primary"
            @click="createUser"
            :loading="createUserLoading"
            :disabled="!createUserFormValid"
          >
            Create User
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    
    <!-- Library Assignment Dialog -->
    <v-dialog v-model="libraryDialog.show" max-width="800">
      <v-card>
        <v-card-title>
          <v-icon left class="mr-2">mdi-folder-network</v-icon>
          Assign SharePoint Libraries
        </v-card-title>
        
        <v-card-subtitle v-if="libraryDialog.user">
          Assigning libraries to: {{ libraryDialog.user.full_name }} ({{ libraryDialog.user.email }})
        </v-card-subtitle>
        
        <v-card-text>
          <v-alert type="info" density="compact" class="mb-4">
            Select the SharePoint libraries that this reviewer should have access to.
          </v-alert>
          
          <v-text-field
            v-model="librarySearch"
            label="Search libraries"
            prepend-inner-icon="mdi-magnify"
            variant="outlined"
            density="compact"
            clearable
            class="mb-3"
          />
          
          <v-list 
            v-if="availableLibraries.length > 0"
            density="compact" 
            class="library-list"
            max-height="400"
            style="overflow-y: auto;"
          >
            <template v-for="site in groupedLibraries" :key="site.site_id">
              <v-list-subheader>{{ site.site_name }}</v-list-subheader>
              <v-list-item
                v-for="library in site.libraries"
                :key="library.library_id"
              >
                <template v-slot:prepend>
                  <v-checkbox
                    v-model="selectedLibraries"
                    :value="library.library_id"
                    hide-details
                    density="compact"
                  />
                </template>
                <v-list-item-title>{{ library.library_name }}</v-list-item-title>
                <v-list-item-subtitle>{{ library.library_url }}</v-list-item-subtitle>
              </v-list-item>
            </template>
          </v-list>
          
          <v-alert v-else type="warning" density="compact">
            No SharePoint sites found. Please ensure SharePoint data has been imported.
          </v-alert>
          
          <div class="mt-3">
            <v-chip
              v-for="count in [selectedLibraries.length]"
              :key="count"
              color="primary"
              variant="outlined"
            >
              {{ count }} {{ count === 1 ? 'library' : 'libraries' }} selected
            </v-chip>
          </div>
        </v-card-text>
        
        <v-card-actions>
          <v-spacer />
          <v-btn
            variant="text"
            @click="libraryDialog.show = false"
          >
            Cancel
          </v-btn>
          <v-btn
            color="primary"
            variant="flat"
            @click="saveLibraryAssignments"
            :loading="libraryDialog.saving"
          >
            Save Assignments
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    
    <!-- Snackbar for notifications -->
    <v-snackbar
      v-model="snackbar.show"
      :color="snackbar.color"
      timeout="3000"
    >
      {{ snackbar.message }}
    </v-snackbar>
  </v-container>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useAuth } from '../composables/useAuth'
import axios from 'axios'

const auth = useAuth()

// Ensure axios has the auth token
if (auth.token.value) {
  axios.defaults.headers.common['Authorization'] = `Bearer ${auth.token.value}`
}

// Data
const loading = ref(false)
const users = ref([])
const totalItems = ref(0)
const itemsPerPage = ref(25)
const actionLoading = reactive({})

const stats = reactive({
  total_count: 0,
  pending_count: 0,
  active_count: 0
})

const filters = reactive({
  status: null,
  role: null,
  search: ''
})

const approvalDialog = reactive({
  show: false,
  user: null,
  approve: true,
  rejectionReason: '',
  processing: false
})

const roleDialog = reactive({
  show: false,
  user: null,
  newRole: '',
  processing: false
})

// Create User Dialog
const showCreateUserDialog = ref(false)
const createUserFormValid = ref(false)
const createUserLoading = ref(false)
const createUserError = ref('')
const showPassword = ref(false)
const createUserForm = ref(null)

// Library Assignment Dialog
const libraryDialog = reactive({
  show: false,
  user: null,
  saving: false
})
const availableLibraries = ref([])
const selectedLibraries = ref([])
const librarySearch = ref('')

// Snackbar for notifications
const snackbar = ref({
  show: false,
  message: '',
  color: 'success'
})

const newUser = reactive({
  email: '',
  username: '',
  full_name: '',
  password: '',
  department: '',
  company: '',
  phone: '',
  role: 'reviewer'
})

// Validation Rules
const rules = {
  required: v => !!v || 'This field is required',
  email: v => /.+@.+\..+/.test(v) || 'Email must be valid',
  username: v => /^[a-zA-Z0-9_-]{3,}$/.test(v) || 'Username must be at least 3 characters and contain only letters, numbers, hyphens, and underscores',
  password: v => {
    if (!v) return 'Password is required'
    if (v.length < 8) return 'Password must be at least 8 characters'
    if (!/[A-Z]/.test(v)) return 'Password must contain at least one uppercase letter'
    if (!/[a-z]/.test(v)) return 'Password must contain at least one lowercase letter'
    if (!/[0-9]/.test(v)) return 'Password must contain at least one number'
    if (!/[!@#$%^&*]/.test(v)) return 'Password must contain at least one special character'
    return true
  }
}

// Options
const statusOptions = [
  { title: 'Pending Approval', value: 'pending' },
  { title: 'Approved', value: 'approved' },
  { title: 'Rejected', value: 'rejected' }
]

const roleOptions = [
  { title: 'Administrator', value: 'administrator' },
  { title: 'Reviewer', value: 'reviewer' }
]

// Table headers
const headers = [
  { title: 'User', key: 'user_info', sortable: false },
  { title: 'Status', key: 'status', sortable: false },
  { title: 'Role', key: 'role', sortable: true },
  { title: 'Organization', key: 'organization', sortable: false },
  { title: 'Dates', key: 'dates', sortable: false },
  { title: 'Actions', key: 'actions', sortable: false, width: '120px' }
]

// Computed
const adminCount = computed(() => {
  return users.value.filter(u => u.role === 'administrator').length
})

const groupedLibraries = computed(() => {
  const filtered = availableLibraries.value.filter(lib => {
    if (!librarySearch.value) return true
    const search = librarySearch.value.toLowerCase()
    return lib.library_name.toLowerCase().includes(search) ||
           lib.site_name.toLowerCase().includes(search)
  })
  
  // Group by site
  const grouped = {}
  filtered.forEach(lib => {
    if (!grouped[lib.site_id]) {
      grouped[lib.site_id] = {
        site_id: lib.site_id,
        site_name: lib.site_name,
        libraries: []
      }
    }
    grouped[lib.site_id].libraries.push(lib)
  })
  
  return Object.values(grouped)
})

// Methods
const loadUsers = async (options = {}) => {
  loading.value = true

  try {
    const params = new URLSearchParams()
    
    // Add filters
    if (filters.status) params.append('status_filter', filters.status)
    if (filters.role) params.append('role_filter', filters.role)
    if (filters.search) params.append('search', filters.search)
    
    // Add pagination (if provided by data table)
    if (options.itemsPerPage) {
      params.append('limit', options.itemsPerPage)
      params.append('offset', ((options.page || 1) - 1) * options.itemsPerPage)
    } else {
      params.append('limit', itemsPerPage.value)
      params.append('offset', 0)
    }

    const response = await axios.get(`/api/v1/admin/users?${params.toString()}`)
    
    users.value = response.data.users
    totalItems.value = response.data.total_count
    
    // Update stats
    stats.total_count = response.data.total_count
    stats.pending_count = response.data.pending_count
    stats.active_count = response.data.active_count

  } catch (error) {
    console.error('Failed to load users:', error)
  } finally {
    loading.value = false
  }
}

const loadPendingUsers = () => {
  filters.status = 'pending'
  loadUsers()
}

const clearFilters = () => {
  filters.status = null
  filters.role = null
  filters.search = ''
  loadUsers()
}

const clearSearch = () => {
  filters.search = ''
  loadUsers()
}

const openApprovalDialog = (user, approve) => {
  approvalDialog.user = user
  approvalDialog.approve = approve
  approvalDialog.rejectionReason = ''
  approvalDialog.show = true
}

const processApproval = async () => {
  if (!approvalDialog.approve && !approvalDialog.rejectionReason.trim()) {
    return
  }

  approvalDialog.processing = true
  actionLoading[approvalDialog.user.id] = true

  try {
    const payload = {
      approve: approvalDialog.approve,
      rejection_reason: approvalDialog.approve ? null : approvalDialog.rejectionReason.trim()
    }

    await axios.put(`/api/v1/admin/users/${approvalDialog.user.id}/approve`, payload)
    
    approvalDialog.show = false
    await loadUsers() // Reload to see updated status

  } catch (error) {
    console.error('Failed to process user approval:', error)
  } finally {
    approvalDialog.processing = false
    delete actionLoading[approvalDialog.user.id]
  }
}

const openRoleDialog = (user) => {
  roleDialog.user = user
  roleDialog.newRole = user.role
  roleDialog.show = true
}

const processRoleChange = async () => {
  if (roleDialog.newRole === roleDialog.user.role) {
    roleDialog.show = false
    return
  }

  roleDialog.processing = true

  try {
    await axios.put(`/api/v1/admin/users/${roleDialog.user.id}/role`, {
      role: roleDialog.newRole
    })
    
    roleDialog.show = false
    await loadUsers() // Reload to see updated role

  } catch (error) {
    console.error('Failed to update user role:', error)
  } finally {
    roleDialog.processing = false
  }
}

const deactivateUser = async (user) => {
  if (!confirm(`Are you sure you want to deactivate ${user.full_name}?`)) {
    return
  }

  actionLoading[user.id] = true

  try {
    await axios.delete(`/api/v1/admin/users/${user.id}`)
    await loadUsers() // Reload to see updated status

  } catch (error) {
    console.error('Failed to deactivate user:', error)
  } finally {
    delete actionLoading[user.id]
  }
}

const viewUserDetails = (user) => {
  // This could open a detailed view dialog or navigate to a user detail page
  console.log('View user details:', user)
}

// Library Assignment Methods
const openLibraryAssignmentDialog = async (user) => {
  libraryDialog.user = user
  libraryDialog.show = true
  selectedLibraries.value = []
  
  // Load available SharePoint sites directly from permissions data
  try {
    const response = await axios.get('/api/v1/sharepoint-simple/assignable-sites')
    availableLibraries.value = response.data.libraries || []
    
    // Load current assignments for this user
    const assignmentsResponse = await axios.get(`/api/v1/library-assignments/users/${user.id}/libraries`)
    const currentAssignments = assignmentsResponse.data.assignments || []
    selectedLibraries.value = currentAssignments
      .filter(a => a.is_active)
      .map(a => a.sp_library_id)  // Use the SharePoint library ID, not the internal ID
  } catch (error) {
    console.error('Failed to load libraries:', error)
    snackbar.value = {
      show: true,
      message: 'Failed to load SharePoint sites',
      color: 'error'
    }
  }
}


const saveLibraryAssignments = async () => {
  libraryDialog.saving = true
  
  try {
    // Debug: log what we're sending
    console.log('Saving assignments:', {
      user_id: libraryDialog.user.id,
      library_ids: selectedLibraries.value,
      permissions: {
        can_view: true,
        can_export: false,
        can_analyze: true
      }
    })
    
    await axios.post('/api/v1/library-assignments/assign', {
      user_id: libraryDialog.user.id,
      library_ids: selectedLibraries.value,
      permissions: {
        can_view: true,
        can_export: false,
        can_analyze: true
      }
    })
    
    snackbar.value = {
      show: true,
      message: `Libraries assigned to ${libraryDialog.user.full_name}`,
      color: 'success'
    }
    
    libraryDialog.show = false
  } catch (error) {
    console.error('Failed to save library assignments:', error)
    snackbar.value = {
      show: true,
      message: 'Failed to save library assignments',
      color: 'error'
    }
  } finally {
    libraryDialog.saving = false
  }
}

// Create User Methods
const createUser = async () => {
  // Validate form
  const { valid } = await createUserForm.value.validate()
  if (!valid) return

  createUserLoading.value = true
  createUserError.value = ''

  try {
    // First create the user
    const createResponse = await axios.post('/api/v1/admin/users/create', {
      email: newUser.email,
      username: newUser.username,
      full_name: newUser.full_name,
      password: newUser.password,
      department: newUser.department || null,
      company: newUser.company || null,
      phone: newUser.phone || null
    })

    // If role is administrator, update it (since default is reviewer)
    if (newUser.role === 'administrator' && createResponse.data.user_id) {
      await axios.put(`/api/v1/admin/users/${createResponse.data.user_id}/role`, {
        role: 'administrator'
      })
    }

    // Close dialog and reload users
    closeCreateUserDialog()
    await loadUsers()

    // Show success message (you might want to add a snackbar component for this)
    console.log('User created successfully:', createResponse.data)

  } catch (error) {
    console.error('Failed to create user:', error)
    
    if (error.response?.data?.detail) {
      const detail = error.response.data.detail
      
      if (typeof detail === 'string') {
        createUserError.value = detail
      } else if (detail.errors) {
        // Password validation errors
        createUserError.value = detail.errors.join('. ')
      } else if (detail.message) {
        createUserError.value = detail.message
      }
    } else {
      createUserError.value = 'Failed to create user. Please try again.'
    }
  } finally {
    createUserLoading.value = false
  }
}

const closeCreateUserDialog = () => {
  showCreateUserDialog.value = false
  createUserError.value = ''
  
  // Reset form
  newUser.email = ''
  newUser.username = ''
  newUser.full_name = ''
  newUser.password = ''
  newUser.department = ''
  newUser.company = ''
  newUser.phone = ''
  newUser.role = 'reviewer'
  
  // Reset form validation
  if (createUserForm.value) {
    createUserForm.value.resetValidation()
  }
}

const getStatusColor = (user) => {
  if (!user.is_approved && !user.approved_by) return 'orange'
  if (user.is_approved && user.is_active) return 'success'
  if (!user.is_approved && user.approved_by) return 'error'
  if (!user.is_active) return 'grey'
  return 'grey'
}

const getStatusText = (user) => {
  if (!user.is_approved && !user.approved_by) return 'Pending'
  if (user.is_approved && user.is_active) return 'Active'
  if (!user.is_approved && user.approved_by) return 'Rejected'
  if (!user.is_active) return 'Inactive'
  return 'Unknown'
}

const formatDate = (dateString) => {
  if (!dateString) return 'Never'
  return new Date(dateString).toLocaleDateString()
}

// Lifecycle
onMounted(() => {
  loadUsers()
})
</script>

<style scoped>
.gap-1 {
  gap: 4px;
}
</style>