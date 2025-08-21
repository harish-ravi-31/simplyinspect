<template>
  <v-container fluid>
    <!-- Page Header -->
    <v-row>
      <v-col cols="12">
        <v-card flat>
          <v-card-title class="text-h4">
            <v-icon large class="mr-2">mdi-shield-check</v-icon>
            Permission Baselines
          </v-card-title>
          <v-card-subtitle>
            Manage permission baselines and monitor changes
          </v-card-subtitle>
        </v-card>
      </v-col>
    </v-row>

    <!-- Action Buttons -->
    <v-row class="mt-4">
      <v-col cols="12">
        <v-btn
          color="primary"
          @click="showCreateDialog = true"
          :disabled="userRole !== 'administrator'"
        >
          <v-icon left>mdi-plus</v-icon>
          Create Baseline
        </v-btn>
        
        <v-btn
          color="secondary"
          @click="detectChanges"
          class="ml-2"
          :loading="detectingChanges"
          :disabled="userRole !== 'administrator'"
        >
          <v-icon left>mdi-magnify</v-icon>
          Detect Changes
        </v-btn>
        
        <v-btn
          color="info"
          @click="showRecentChanges = !showRecentChanges"
          class="ml-2"
        >
          <v-icon left>mdi-history</v-icon>
          Recent Changes
          <v-badge
            v-if="unreviewedCount > 0"
            :content="unreviewedCount"
            color="error"
            class="ml-2"
          />
        </v-btn>
        
        <v-btn
          @click="showNotificationSettings = true"
          class="ml-2"
          :disabled="userRole !== 'administrator'"
        >
          <v-icon left>mdi-email-outline</v-icon>
          Notification Settings
        </v-btn>
      </v-col>
    </v-row>

    <!-- Baselines List -->
    <v-row class="mt-4">
      <v-col cols="12">
        <v-card>
          <v-card-title>
            Active Baselines
            <v-spacer></v-spacer>
            <v-text-field
              v-model="search"
              append-icon="mdi-magnify"
              label="Search"
              single-line
              hide-details
              density="compact"
              style="max-width: 300px"
            ></v-text-field>
          </v-card-title>
          
          <v-data-table
            :headers="baselineHeaders"
            :items="filteredBaselines"
            :search="search"
            :loading="loading"
            class="elevation-0"
          >
            <template v-slot:item.is_active="{ item }">
              <v-chip
                :color="item.is_active ? 'success' : 'default'"
                size="small"
              >
                {{ item.is_active ? 'Active' : 'Inactive' }}
              </v-chip>
            </template>
            
            <template v-slot:item.created_at="{ item }">
              {{ formatDate(item.created_at) }}
            </template>
            
            <template v-slot:item.actions="{ item }">
              <v-btn
                icon="mdi-compare"
                size="small"
                @click="compareBaseline(item)"
                title="Compare with current"
              />
              
              <v-btn
                v-if="!item.is_active && userRole === 'administrator'"
                icon="mdi-check"
                size="small"
                @click="activateBaseline(item)"
                title="Activate"
                class="ml-1"
                color="success"
              />
              
              <v-btn
                v-if="item.is_active && userRole === 'administrator'"
                icon="mdi-pause"
                size="small"
                @click="deactivateBaseline(item)"
                title="Deactivate"
                class="ml-1"
                color="warning"
              />
              
              <v-btn
                v-if="userRole === 'administrator'"
                icon="mdi-delete"
                size="small"
                @click="deleteBaseline(item)"
                title="Delete"
                class="ml-1"
                color="error"
              />
            </template>
          </v-data-table>
        </v-card>
      </v-col>
    </v-row>

    <!-- Recent Changes Panel -->
    <v-expand-transition>
      <v-row v-if="showRecentChanges" class="mt-4">
        <v-col cols="12">
          <v-card>
            <v-card-title>
              Recent Permission Changes
              <v-spacer></v-spacer>
              <v-btn
                text
                @click="loadRecentChanges"
                :loading="loadingChanges"
              >
                <v-icon>mdi-refresh</v-icon>
              </v-btn>
            </v-card-title>
            
            <v-card-text>
              <v-data-table
                :headers="changesHeaders"
                :items="recentChanges"
                :loading="loadingChanges"
                dense
              >
                <template v-slot:item.change_type="{ item }">
                  <v-chip
                    :color="getChangeTypeColor(item.change_type)"
                    size="small"
                  >
                    {{ item.change_type }}
                  </v-chip>
                </template>
                
                <template v-slot:item.detected_at="{ item }">
                  {{ formatDate(item.detected_at) }}
                </template>
                
                <template v-slot:item.reviewed="{ item }">
                  <v-icon
                    :color="item.reviewed ? 'success' : 'warning'"
                    size="small"
                  >
                    {{ item.reviewed ? 'mdi-check-circle' : 'mdi-alert-circle' }}
                  </v-icon>
                </template>
                
                <template v-slot:item.actions="{ item }">
                  <v-btn
                    v-if="!item.reviewed"
                    icon="mdi-check"
                    size="small"
                    @click="markAsReviewed([item.id])"
                    title="Mark as reviewed"
                    color="success"
                  />
                  
                  <v-btn
                    icon="mdi-eye"
                    size="small"
                    @click="showChangeDetails(item)"
                    title="View details"
                    class="ml-1"
                  />
                </template>
              </v-data-table>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </v-expand-transition>

    <!-- Create Baseline Dialog -->
    <v-dialog v-model="showCreateDialog" max-width="600">
      <v-card>
        <v-card-title>Create Permission Baseline</v-card-title>
        
        <v-card-text>
          <v-form ref="createForm">
            <v-select
              v-model="newBaseline.site_id"
              :items="availableSites"
              item-title="site_name"
              item-value="site_id"
              label="Select Site"
              required
              :rules="[v => !!v || 'Site is required']"
            ></v-select>
            
            <v-text-field
              v-model="newBaseline.name"
              label="Baseline Name"
              required
              :rules="[v => !!v || 'Name is required']"
            ></v-text-field>
            
            <v-textarea
              v-model="newBaseline.description"
              label="Description (optional)"
              rows="3"
            ></v-textarea>
            
            <v-checkbox
              v-model="newBaseline.set_as_active"
              label="Set as active baseline"
            ></v-checkbox>
          </v-form>
        </v-card-text>
        
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn text @click="showCreateDialog = false">Cancel</v-btn>
          <v-btn
            color="primary"
            @click="createBaseline"
            :loading="creating"
          >
            Create
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Comparison Results Dialog -->
    <v-dialog v-model="showComparisonDialog" max-width="900">
      <v-card>
        <v-card-title>
          Baseline Comparison Results
          <v-spacer></v-spacer>
          <v-btn icon @click="showComparisonDialog = false">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-card-title>
        
        <v-card-text v-if="comparisonResult">
          <v-row>
            <v-col cols="3">
              <v-card flat outlined>
                <v-card-text class="text-center">
                  <div class="text-h4 success--text">{{ comparisonResult.changes?.summary?.added_count || 0 }}</div>
                  <div>Added</div>
                </v-card-text>
              </v-card>
            </v-col>
            
            <v-col cols="3">
              <v-card flat outlined>
                <v-card-text class="text-center">
                  <div class="text-h4 error--text">{{ comparisonResult.changes?.summary?.removed_count || 0 }}</div>
                  <div>Removed</div>
                </v-card-text>
              </v-card>
            </v-col>
            
            <v-col cols="3">
              <v-card flat outlined>
                <v-card-text class="text-center">
                  <div class="text-h4 warning--text">{{ comparisonResult.changes?.summary?.modified_count || 0 }}</div>
                  <div>Modified</div>
                </v-card-text>
              </v-card>
            </v-col>
            
            <v-col cols="3">
              <v-card flat outlined>
                <v-card-text class="text-center">
                  <div class="text-h4">{{ comparisonResult.changes?.summary?.unchanged_count || 0 }}</div>
                  <div>Unchanged</div>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>
          
          <v-tabs v-model="comparisonTab" class="mt-4">
            <v-tab value="added">Added</v-tab>
            <v-tab value="removed">Removed</v-tab>
            <v-tab value="modified">Modified</v-tab>
          </v-tabs>
          
          <v-window v-model="comparisonTab">
            <v-window-item value="added">
              <v-table density="compact" class="mt-2">
                <thead>
                  <tr>
                    <th>Resource</th>
                    <th>Principal</th>
                    <th>Permission Level</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="perm in comparisonResult.changes?.added_permissions?.slice(0, 20)" :key="perm.resource_id + '_' + perm.principal_id">
                    <td>{{ perm.resource_name }}</td>
                    <td>{{ perm.principal_name }}</td>
                    <td>{{ perm.permission_level }}</td>
                  </tr>
                </tbody>
              </v-table>
            </v-window-item>
            
            <v-window-item value="removed">
              <v-table density="compact" class="mt-2">
                <thead>
                  <tr>
                    <th>Resource</th>
                    <th>Principal</th>
                    <th>Permission Level</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="perm in comparisonResult.changes?.removed_permissions?.slice(0, 20)" :key="perm.resource_id + '_' + perm.principal_id">
                    <td>{{ perm.resource_name }}</td>
                    <td>{{ perm.principal_name }}</td>
                    <td>{{ perm.permission_level }}</td>
                  </tr>
                </tbody>
              </v-table>
            </v-window-item>
            
            <v-window-item value="modified">
              <v-table density="compact" class="mt-2">
                <thead>
                  <tr>
                    <th>Resource</th>
                    <th>Principal</th>
                    <th>Old Permission</th>
                    <th>New Permission</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="perm in comparisonResult.changes?.modified_permissions?.slice(0, 20)" :key="perm.resource_id + '_' + perm.principal_id">
                    <td>{{ perm.resource_name }}</td>
                    <td>{{ perm.principal_name }}</td>
                    <td>{{ perm.old_permission_level }}</td>
                    <td>{{ perm.new_permission_level }}</td>
                  </tr>
                </tbody>
              </v-table>
            </v-window-item>
          </v-window>
        </v-card-text>
      </v-card>
    </v-dialog>

    <!-- Notification Settings Dialog -->
    <v-dialog v-model="showNotificationSettings" max-width="600">
      <v-card>
        <v-card-title>Notification Settings</v-card-title>
        
        <v-card-text>
          <v-list>
            <v-list-item v-for="recipient in notificationRecipients" :key="recipient.id">
              <template v-slot:default>
                <v-list-item-title>{{ recipient.recipient_email }}</v-list-item-title>
                <v-list-item-subtitle>
                  {{ recipient.recipient_name }} - {{ recipient.frequency }}
                </v-list-item-subtitle>
              </template>
              
              <template v-slot:append>
                <v-btn
                  icon="mdi-delete"
                  @click="removeRecipient(recipient)"
                  color="error"
                  variant="text"
                />
              </template>
            </v-list-item>
          </v-list>
          
          <v-divider class="my-4"></v-divider>
          
          <v-form ref="recipientForm">
            <v-text-field
              v-model="newRecipient.email"
              label="Email Address"
              type="email"
              :rules="[v => !!v || 'Email is required', v => /.+@.+/.test(v) || 'Valid email required']"
            ></v-text-field>
            
            <v-text-field
              v-model="newRecipient.name"
              label="Name (optional)"
            ></v-text-field>
            
            <v-select
              v-model="newRecipient.frequency"
              :items="['immediate', 'daily', 'weekly']"
              label="Notification Frequency"
            ></v-select>
            
            <v-btn
              color="primary"
              @click="addRecipient"
              :loading="addingRecipient"
            >
              Add Recipient
            </v-btn>
          </v-form>
        </v-card-text>
        
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn text @click="showNotificationSettings = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script>
import { apiClient } from '../services/api';

export default {
  name: 'PermissionBaselines',
  
  data() {
    return {
      // User role
      userRole: localStorage.getItem('userRole') || 'reviewer',
      
      // Baselines
      baselines: [],
      loading: false,
      search: '',
      
      // Recent changes
      recentChanges: [],
      showRecentChanges: false,
      loadingChanges: false,
      unreviewedCount: 0,
      
      // Create baseline
      showCreateDialog: false,
      creating: false,
      newBaseline: {
        site_id: null,
        name: '',
        description: '',
        set_as_active: true
      },
      availableSites: [],
      
      // Comparison
      showComparisonDialog: false,
      comparisonResult: null,
      comparisonTab: 'added',
      
      // Notifications
      showNotificationSettings: false,
      notificationRecipients: [],
      newRecipient: {
        email: '',
        name: '',
        frequency: 'immediate'
      },
      addingRecipient: false,
      
      // Detection
      detectingChanges: false,
      
      // Table headers
      baselineHeaders: [
        { title: 'Site', key: 'site_url' },
        { title: 'Baseline Name', key: 'baseline_name' },
        { title: 'Status', key: 'is_active' },
        { title: 'Permissions', key: 'permission_count' },
        { title: 'Created', key: 'created_at' },
        { title: 'Created By', key: 'created_by' },
        { title: 'Actions', key: 'actions', sortable: false }
      ],
      
      changesHeaders: [
        { title: 'Site', key: 'site_url' },
        { title: 'Type', key: 'change_type' },
        { title: 'Resource', key: 'resource_name' },
        { title: 'Principal', key: 'principal_name' },
        { title: 'Detected', key: 'detected_at' },
        { title: 'Reviewed', key: 'reviewed' },
        { title: 'Actions', key: 'actions', sortable: false }
      ]
    };
  },
  
  computed: {
    filteredBaselines() {
      return this.baselines;
    }
  },
  
  mounted() {
    this.loadBaselines();
    this.loadSites();
    this.loadRecentChanges();
    if (this.userRole === 'administrator') {
      this.loadNotificationRecipients();
    }
  },
  
  methods: {
    async loadBaselines() {
      this.loading = true;
      try {
        const response = await apiClient.get('/baselines');
        this.baselines = response.data.baselines || [];
      } catch (error) {
        console.error('Error loading baselines:', error);
        this.$root.$emit('show-snackbar', {
          message: 'Failed to load baselines',
          color: 'error'
        });
      } finally {
        this.loading = false;
      }
    },
    
    async loadSites() {
      try {
        // Get sites from SharePoint permissions endpoint
        const response = await apiClient.get('/sharepoint-simple/my-libraries');
        const libraries = response.data.libraries || [];
        
        console.log('Raw libraries response:', libraries);
        
        // Extract unique sites from libraries
        const siteMap = new Map();
        libraries.forEach(lib => {
          // Use library_id as site_id if site_id is not available
          const siteId = lib.site_id || lib.library_id || lib.id;
          const siteName = lib.site_name || lib.library_name || lib.name || `Site ${siteId}`;
          const siteUrl = lib.site_url || lib.library_url || lib.url || '';
          
          if (siteId && !siteMap.has(siteId)) {
            siteMap.set(siteId, {
              site_id: siteId,
              site_name: siteName,
              site_url: siteUrl
            });
          }
        });
        
        this.availableSites = Array.from(siteMap.values());
        
        console.log('Loaded sites for baseline creation:', this.availableSites);
        
        if (this.availableSites.length === 0) {
          console.warn('No sites available - this usually means no SharePoint permissions have been collected yet');
          
          // Try the assignable-sites endpoint as a fallback for admins
          if (this.userRole === 'administrator') {
            try {
              const assignableResponse = await apiClient.get('/sharepoint-simple/assignable-sites');
              const assignableLibraries = assignableResponse.data.libraries || [];
              
              console.log('Assignable sites response:', assignableLibraries);
              
              assignableLibraries.forEach(lib => {
                const siteId = lib.site_id || lib.library_id || lib.id;
                const siteName = lib.site_name || lib.library_name || `Site ${siteId}`;
                const siteUrl = lib.site_url || lib.library_url || '';
                
                if (siteId && !siteMap.has(siteId)) {
                  siteMap.set(siteId, {
                    site_id: siteId,
                    site_name: siteName,
                    site_url: siteUrl
                  });
                }
              });
              
              this.availableSites = Array.from(siteMap.values());
              console.log('Sites from assignable endpoint:', this.availableSites);
            } catch (err) {
              console.error('Error loading assignable sites:', err);
            }
          }
        }
      } catch (error) {
        console.error('Error loading sites:', error);
        this.availableSites = [];
        
        // Handle authentication errors specifically
        if (error.response?.status === 401) {
          console.warn('Authentication required - sites cannot be loaded until re-authentication');
          this.$root.$emit('show-snackbar', {
            message: 'Your session has expired. Please refresh and log in again.',
            color: 'warning'
          });
        }
      }
    },
    
    async loadRecentChanges() {
      this.loadingChanges = true;
      try {
        const response = await apiClient.get('/change-detection/recent-changes?days=7');
        this.recentChanges = response.data.changes || [];
        this.unreviewedCount = response.data.unreviewed_count || 0;
      } catch (error) {
        console.error('Error loading recent changes:', error);
      } finally {
        this.loadingChanges = false;
      }
    },
    
    async createBaseline() {
      if (!this.$refs.createForm.validate()) return;
      
      this.creating = true;
      try {
        const site = this.availableSites.find(s => s.site_id === this.newBaseline.site_id);
        
        await apiClient.post('/baselines/create', {
          site_id: this.newBaseline.site_id,
          site_url: site?.site_url || '',
          baseline_name: this.newBaseline.name,
          baseline_description: this.newBaseline.description,
          set_as_active: this.newBaseline.set_as_active
        });
        
        this.$root.$emit('show-snackbar', {
          message: 'Baseline created successfully',
          color: 'success'
        });
        
        this.showCreateDialog = false;
        this.newBaseline = {
          site_id: null,
          name: '',
          description: '',
          set_as_active: true
        };
        
        await this.loadBaselines();
      } catch (error) {
        console.error('Error creating baseline:', error);
        this.$root.$emit('show-snackbar', {
          message: error.response?.data?.detail || 'Failed to create baseline',
          color: 'error'
        });
      } finally {
        this.creating = false;
      }
    },
    
    async compareBaseline(baseline) {
      try {
        const response = await apiClient.get(`/baselines/${baseline.id}/compare`);
        this.comparisonResult = response.data;
        this.showComparisonDialog = true;
      } catch (error) {
        console.error('Error comparing baseline:', error);
        this.$root.$emit('show-snackbar', {
          message: 'Failed to compare baseline',
          color: 'error'
        });
      }
    },
    
    async activateBaseline(baseline) {
      try {
        await apiClient.put(`/baselines/${baseline.id}/activate`);
        
        this.$root.$emit('show-snackbar', {
          message: 'Baseline activated',
          color: 'success'
        });
        
        await this.loadBaselines();
      } catch (error) {
        console.error('Error activating baseline:', error);
        this.$root.$emit('show-snackbar', {
          message: 'Failed to activate baseline',
          color: 'error'
        });
      }
    },
    
    async deactivateBaseline(baseline) {
      try {
        await apiClient.put(`/baselines/${baseline.id}/deactivate`);
        
        this.$root.$emit('show-snackbar', {
          message: 'Baseline deactivated',
          color: 'success'
        });
        
        await this.loadBaselines();
      } catch (error) {
        console.error('Error deactivating baseline:', error);
        this.$root.$emit('show-snackbar', {
          message: 'Failed to deactivate baseline',
          color: 'error'
        });
      }
    },
    
    async deleteBaseline(baseline) {
      if (!confirm(`Delete baseline "${baseline.baseline_name}"?`)) return;
      
      try {
        await apiClient.delete(`/baselines/${baseline.id}`);
        
        this.$root.$emit('show-snackbar', {
          message: 'Baseline deleted',
          color: 'success'
        });
        
        await this.loadBaselines();
      } catch (error) {
        console.error('Error deleting baseline:', error);
        this.$root.$emit('show-snackbar', {
          message: 'Failed to delete baseline',
          color: 'error'
        });
      }
    },
    
    async detectChanges() {
      this.detectingChanges = true;
      try {
        const response = await apiClient.post('/change-detection/detect-all', {
          notify: true
        });
        
        this.$root.$emit('show-snackbar', {
          message: `Checked ${response.data.sites_checked} sites, found changes in ${response.data.changes_detected}`,
          color: 'success'
        });
        
        await this.loadRecentChanges();
      } catch (error) {
        console.error('Error detecting changes:', error);
        this.$root.$emit('show-snackbar', {
          message: 'Failed to detect changes',
          color: 'error'
        });
      } finally {
        this.detectingChanges = false;
      }
    },
    
    async markAsReviewed(changeIds) {
      try {
        await apiClient.post('/change-detection/mark-reviewed', {
          change_ids: changeIds,
          review_notes: 'Reviewed via UI'
        });
        
        this.$root.$emit('show-snackbar', {
          message: 'Changes marked as reviewed',
          color: 'success'
        });
        
        await this.loadRecentChanges();
      } catch (error) {
        console.error('Error marking as reviewed:', error);
        this.$root.$emit('show-snackbar', {
          message: 'Failed to mark as reviewed',
          color: 'error'
        });
      }
    },
    
    showChangeDetails(change) {
      // Could open a detailed view dialog
      console.log('Change details:', change);
    },
    
    async loadNotificationRecipients() {
      try {
        const response = await apiClient.get('/notifications/recipients');
        this.notificationRecipients = response.data.recipients || [];
      } catch (error) {
        console.error('Error loading recipients:', error);
      }
    },
    
    async addRecipient() {
      if (!this.$refs.recipientForm.validate()) return;
      
      this.addingRecipient = true;
      try {
        await apiClient.post('/notifications/recipients/manage', {
          action: 'add',
          email: this.newRecipient.email,
          name: this.newRecipient.name,
          frequency: this.newRecipient.frequency,
          notification_types: ['permission_change']
        });
        
        this.$root.$emit('show-snackbar', {
          message: 'Recipient added',
          color: 'success'
        });
        
        this.newRecipient = {
          email: '',
          name: '',
          frequency: 'immediate'
        };
        
        await this.loadNotificationRecipients();
      } catch (error) {
        console.error('Error adding recipient:', error);
        this.$root.$emit('show-snackbar', {
          message: 'Failed to add recipient',
          color: 'error'
        });
      } finally {
        this.addingRecipient = false;
      }
    },
    
    async removeRecipient(recipient) {
      if (!confirm(`Remove ${recipient.recipient_email} from notifications?`)) return;
      
      try {
        await apiClient.post('/notifications/recipients/manage', {
          action: 'remove',
          email: recipient.recipient_email
        });
        
        this.$root.$emit('show-snackbar', {
          message: 'Recipient removed',
          color: 'success'
        });
        
        await this.loadNotificationRecipients();
      } catch (error) {
        console.error('Error removing recipient:', error);
        this.$root.$emit('show-snackbar', {
          message: 'Failed to remove recipient',
          color: 'error'
        });
      }
    },
    
    formatDate(dateString) {
      if (!dateString) return '';
      const date = new Date(dateString);
      return date.toLocaleString();
    },
    
    getChangeTypeColor(changeType) {
      const colors = {
        'added': 'success',
        'removed': 'error',
        'modified': 'warning',
        'inheritance_broken': 'orange',
        'inheritance_restored': 'blue'
      };
      return colors[changeType] || 'default';
    }
  }
};
</script>

<style scoped>
.v-data-table {
  background: transparent !important;
}
</style>