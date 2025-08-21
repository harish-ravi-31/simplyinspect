<template>
  <div class="sharepoint-columns-container">
    <v-toolbar dense flat>
      <v-icon class="mr-2">mdi-folder-network</v-icon>
      <v-toolbar-title>SharePoint Browser</v-toolbar-title>
      <v-spacer></v-spacer>
      
      <!-- Permission Legend -->
      <div class="d-flex align-center mr-4">
        <v-chip small color="success" class="mr-2" variant="flat">
          <v-icon small start>mdi-folder</v-icon>
          Inherited
        </v-chip>
        <v-chip small color="error" variant="flat">
          <v-icon small start>mdi-folder-key</v-icon>
          Unique Permissions
        </v-chip>
      </div>
      
      <v-btn 
        size="small" 
        @click="showPermissionsModal = true"
        title="Collect Permissions"
        class="mr-2"
        color="primary"
        variant="tonal"
      >
        <v-icon left>mdi-shield-sync</v-icon>
        Permissions
      </v-btn>
      
      <v-btn
        size="small"
        @click="exportPdfReport"
        title="Export PDF Report"
        class="mr-2"
        color="secondary"
        variant="tonal"
        :loading="exportingPdf"
      >
        <v-icon left>mdi-file-pdf-box</v-icon>
        Export PDF
      </v-btn>
      
      <v-btn icon size="small" @click="showRefreshModal = true">
        <v-icon>mdi-refresh</v-icon>
      </v-btn>
    </v-toolbar>
    
    <!-- Filter Bar -->
    <div class="filter-bar">
      <v-container fluid class="py-2">
        <v-row dense align="center">
          <v-col cols="12" md="4">
            <v-text-field
              v-model="filterPerson"
              density="compact"
              variant="outlined"
              label="Filter by person"
              prepend-inner-icon="mdi-account-search"
              clearable
              placeholder="e.g., john.doe@company.com"
              @update:modelValue="applyFilters"
            ></v-text-field>
          </v-col>
          
          <v-col cols="12" md="4">
            <v-autocomplete
              v-model="filterSite"
              :items="sites"
              item-title="name"
              item-value="id"
              density="compact"
              variant="outlined"
              label="Filter by site"
              prepend-inner-icon="mdi-web"
              clearable
              placeholder="Select a site"
              @update:modelValue="applyFilters"
            ></v-autocomplete>
          </v-col>
          
          <v-col cols="12" md="2">
            <v-select
              v-model="filterPermissionType"
              :items="permissionTypes"
              density="compact"
              variant="outlined"
              label="Permission type"
              prepend-inner-icon="mdi-shield-check"
              clearable
              @update:modelValue="applyFilters"
            ></v-select>
          </v-col>
          
          <v-col cols="12" md="2" class="text-right">
            <v-btn
              v-if="hasActiveFilters"
              color="secondary"
              variant="text"
              @click="clearFilters"
            >
              <v-icon start>mdi-filter-remove</v-icon>
              Clear Filters
            </v-btn>
          </v-col>
        </v-row>
        
        <!-- Active filters display -->
        <v-row v-if="hasActiveFilters" dense class="mt-1">
          <v-col cols="12">
            <div class="text-caption">
              <span class="text-grey">Active filters:</span>
              <v-chip
                v-if="filterPerson"
                size="small"
                closable
                @click:close="filterPerson = ''; applyFilters()"
                class="ml-2"
              >
                <v-icon start small>mdi-account</v-icon>
                {{ filterPerson }}
              </v-chip>
              <v-chip
                v-if="filterSite"
                size="small"
                closable
                @click:close="filterSite = null; applyFilters()"
                class="ml-2"
              >
                <v-icon start small>mdi-web</v-icon>
                {{ sites.find(s => s.id === filterSite)?.name }}
              </v-chip>
              <v-chip
                v-if="filterPermissionType"
                size="small"
                closable
                @click:close="filterPermissionType = null; applyFilters()"
                class="ml-2"
              >
                <v-icon start small>mdi-shield</v-icon>
                {{ filterPermissionType }}
              </v-chip>
            </div>
          </v-col>
        </v-row>
      </v-container>
    </div>
    
    <!-- Breadcrumb trail -->
    <div class="breadcrumb-container" v-if="breadcrumbPath.length > 0">
      <v-breadcrumbs :items="breadcrumbPath" density="compact">
        <template v-slot:item="{ item }">
          <v-breadcrumbs-item @click="navigateToBreadcrumb(item)">
            {{ item.text }}
          </v-breadcrumbs-item>
        </template>
      </v-breadcrumbs>
    </div>
    
    <!-- Filtered Results View -->
    <div v-if="hasActiveFilters && filteredData" class="filtered-results-container">
      <v-container>
        <v-row>
          <v-col cols="12">
            <h3 class="text-h6 mb-2">
              Search Results 
              <span class="text-caption text-grey">({{ filteredData.count }} items found)</span>
            </h3>
            
            <v-data-table
              :headers="[
                { title: 'Name', key: 'name', sortable: true },
                { title: 'Type', key: 'type', sortable: true, width: '100px' },
                { title: 'Site', key: 'site_url', sortable: true },
                { title: 'Permissions', key: 'has_unique_permissions', sortable: true, width: '120px' },
                { title: 'Users with Access', key: 'principal_count', sortable: true, width: '150px' },
                { title: 'Actions', key: 'actions', sortable: false, width: '100px' }
              ]"
              :items="filteredData.items"
              :items-per-page="20"
              class="elevation-1"
            >
              <template v-slot:item.name="{ item }">
                <div class="d-flex align-center">
                  <v-icon size="20" :color="getItemColor(item)" class="mr-2">
                    {{ getItemIcon(item) }}
                  </v-icon>
                  {{ item.name }}
                </div>
              </template>
              
              <template v-slot:item.type="{ item }">
                <v-chip size="small" variant="flat">
                  {{ item.type }}
                </v-chip>
              </template>
              
              <template v-slot:item.site_url="{ item }">
                <span class="text-truncate" style="max-width: 300px; display: block;">
                  {{ item.site_url }}
                </span>
              </template>
              
              <template v-slot:item.has_unique_permissions="{ item }">
                <v-chip 
                  size="small" 
                  :color="item.has_unique_permissions ? 'error' : 'success'"
                  variant="flat"
                >
                  {{ item.has_unique_permissions ? 'Unique' : 'Inherited' }}
                </v-chip>
              </template>
              
              <template v-slot:item.principal_count="{ item }">
                <span>{{ item.principal_count }} ({{ item.human_count }} people)</span>
              </template>
              
              <template v-slot:item.actions="{ item }">
                <v-btn
                  icon
                  size="small"
                  @click="navigateToItem(item)"
                  title="Navigate to item"
                >
                  <v-icon>mdi-arrow-right</v-icon>
                </v-btn>
              </template>
            </v-data-table>
          </v-col>
        </v-row>
      </v-container>
    </div>
    
    <!-- Normal Columns View -->
    <div v-else class="columns-wrapper">
      <!-- Sites Column - Always visible and fixed -->
      <div class="column column-sites" 
           :style="{ width: (columnWidths['sites'] || 300) + 'px' }">
        <div class="column-header">
          <v-icon size="18" class="mr-1">mdi-web</v-icon>
          Sites
        </div>
        <v-list dense class="column-list">
          <v-list-item
            v-for="site in sites"
            :key="site.id"
            @click="selectSite(site)"
            :class="{ 'v-list-item--active': selectedSite?.id === site.id }"
          >
            <template v-slot:prepend>
              <v-icon size="20">mdi-web</v-icon>
            </template>
            <v-list-item-title>
              {{ site.name }}
              <span class="text-caption text-grey ml-1">({{ site.statistics?.total_items || 0 }})</span>
            </v-list-item-title>
          </v-list-item>
        </v-list>
        <div class="column-resizer" 
             @mousedown="startResize('sites', $event)"></div>
      </div>
      
      <!-- Scrollable columns container -->
      <div class="columns-container">
      
      <!-- Site Contents Column -->
      <div class="column" v-if="selectedSite"
           :style="{ width: (columnWidths['site-content'] || 300) + 'px' }">
        <div class="column-header">
          <v-icon size="18" class="mr-1">mdi-folder</v-icon>
          {{ selectedSite.name }}
        </div>
        <v-list dense class="column-list">
          <v-progress-linear v-if="loadingFolders" indeterminate></v-progress-linear>
          <v-list-item
            v-for="item in topLevelFolders"
            :key="item.id"
            @click="selectTopLevelItem(item)"
            :class="{ 'v-list-item--active': selectedPath[0]?.id === item.id }"
          >
            <template v-slot:prepend>
              <v-icon size="20" :color="getItemColor(item)">
                {{ getItemIcon(item) }}
              </v-icon>
            </template>
            <v-list-item-title>
              {{ item.name }}
              <span v-if="item.type === 'folder'" class="text-caption text-grey ml-1">({{ item.childCount || 0 }})</span>
              <v-tooltip v-if="item.has_unique_permissions" location="right">
                <template v-slot:activator="{ props }">
                  <v-icon 
                    v-bind="props" 
                    size="14" 
                    color="error" 
                    class="ml-1"
                  >
                    mdi-shield-alert
                  </v-icon>
                </template>
                <span>This {{ item.type }} has unique permissions</span>
              </v-tooltip>
            </v-list-item-title>
          </v-list-item>
        </v-list>
        <div class="column-resizer" 
             @mousedown="startResize('site-content', $event)"></div>
      </div>
      
      <!-- Dynamic columns for each folder level -->
      <div 
        v-for="(column, index) in dynamicColumns" 
        :key="`column-${index}`"
        class="column"
        :style="{ width: (columnWidths['dynamic-' + index] || 300) + 'px' }"
      >
        <div class="column-header">
          <v-icon size="18" class="mr-1">{{ column.icon }}</v-icon>
          {{ column.title }}
        </div>
        <v-list dense class="column-list">
          <v-progress-linear v-if="column.loading" indeterminate></v-progress-linear>
          <v-list-item
            v-for="item in column.items"
            :key="item.id"
            @click="selectDynamicItem(item, index)"
            :class="{ 'v-list-item--active': isItemSelected(item, index) }"
          >
            <template v-slot:prepend>
              <v-icon size="20" :color="getItemColor(item)">
                {{ getItemIcon(item) }}
              </v-icon>
            </template>
            <v-list-item-title>
              {{ item.name }}
              <span v-if="item.type === 'folder'" class="text-caption text-grey ml-1">
                ({{ item.childCount || 0 }})
              </span>
              <v-tooltip v-if="item.has_unique_permissions" location="right">
                <template v-slot:activator="{ props }">
                  <v-icon 
                    v-bind="props" 
                    size="14" 
                    color="error" 
                    class="ml-1"
                  >
                    mdi-shield-alert
                  </v-icon>
                </template>
                <span>This {{ item.type }} has unique permissions</span>
              </v-tooltip>
            </v-list-item-title>
          </v-list-item>
        </v-list>
        <div class="column-resizer" 
             @mousedown="startResize('dynamic-' + index, $event)"></div>
      </div>
      
      <!-- Empty folder message -->
      <div v-if="showEmptyFolderMessage" class="empty-folder-message">
        <div class="empty-folder-content">
          <v-icon size="64" color="grey-lighten-2">mdi-folder-open-outline</v-icon>
          <div class="text-h6 text-grey mt-3">Empty Folder</div>
          <div class="text-body-2 text-grey">
            The folder "{{ selectedEmptyFolder ? selectedEmptyFolder.name : '' }}" contains no items
          </div>
        </div>
      </div>
      
      </div>
      <!-- End of scrollable columns container -->
      
      <!-- Details Column - Fixed width, outside scrollable area -->
      <div class="column details-column" v-if="detailItem"
           :style="{ width: (columnWidths['details'] || 500) + 'px' }">
        <div class="column-header">
          <v-icon size="18" class="mr-1">mdi-information</v-icon>
          Details
        </div>
        <div class="details-content">
          <div v-if="detailItem" class="pa-4">
            <div class="d-flex align-center mb-4">
              <v-icon size="48" :color="getItemColor(detailItem)" class="mr-3">
                {{ getItemIcon(detailItem) }}
              </v-icon>
              <div>
                <div class="text-h6">{{ detailItem.name }}</div>
                <div class="text-caption text-grey">{{ detailItem.type }}</div>
              </div>
            </div>
            
            <v-divider class="my-3"></v-divider>
            
            <div class="detail-row">
              <span class="detail-label">Type:</span>
              <span class="detail-value">{{ detailItem.type }}</span>
            </div>
            
            <div class="detail-row" v-if="detailItem.url">
              <span class="detail-label">URL:</span>
              <a :href="detailItem.url" target="_blank" class="detail-value text-truncate">
                {{ detailItem.url }}
              </a>
            </div>
            
            <div class="detail-row">
              <span class="detail-label">Permissions:</span>
              <span class="detail-value">
                <v-chip small :color="detailItem.has_unique_permissions ? 'orange' : 'green'">
                  {{ detailItem.has_unique_permissions ? 'Unique' : 'Inherited' }}
                </v-chip>
              </span>
            </div>
            
            <div class="detail-row" v-if="itemPermissionsLoaded && itemPermissions">
              <span class="detail-label">Users with access:</span>
              <span class="detail-value">
                {{ getTotalPermissionsCount() }}
                <span v-if="getTotalPermissionsCount() > 0" class="text-caption text-grey ml-1">
                  ({{ (itemPermissions.users || []).length }} users, {{ (itemPermissions.groups || []).length }} groups{{ (itemPermissions.shared_links || []).length > 0 ? ', ' + (itemPermissions.shared_links || []).length + ' links' : '' }})
                </span>
              </span>
            </div>
            <div class="detail-row" v-else-if="detailItem.statistics">
              <span class="detail-label">Users with access:</span>
              <span class="detail-value">
                {{ detailItem.statistics.principal_count || 0 }}
                <span v-if="detailItem.statistics.principal_count > 0" class="text-caption text-grey ml-1">
                  ({{ detailItem.statistics.user_count || 0 }} users, {{ detailItem.statistics.group_count || 0 }} groups{{ detailItem.statistics.shared_count > 0 ? ', ' + detailItem.statistics.shared_count + ' links' : '' }})
                </span>
              </span>
            </div>
            
            <div class="detail-row" v-if="detailItem.type === 'folder' || detailItem.type === 'site'">
              <span class="detail-label">Contains:</span>
              <span class="detail-value">
                {{ detailItem.childCount || detailItem.statistics?.total_items || 0 }} items
              </span>
            </div>
            
            <v-divider class="my-3"></v-divider>
            
            <!-- Permissions Section -->
            <div class="mt-4" v-if="detailItem && detailItem.type !== 'site'">
              <div class="permissions-header d-flex align-center justify-space-between mb-3">
                <div class="text-subtitle-2 d-flex align-center">
                  <v-icon size="18" class="mr-1">mdi-shield-account</v-icon>
                  <span>Permissions</span>
                </div>
                <v-btn
                  x-small
                  icon
                  @click="loadItemPermissions"
                  :loading="loadingPermissions"
                  title="Refresh permissions"
                >
                  <v-icon>mdi-refresh</v-icon>
                </v-btn>
              </div>
              
              <!-- Loading state -->
              <div v-if="loadingPermissions" class="text-center py-4">
                <v-progress-circular indeterminate size="32" width="3"></v-progress-circular>
                <div class="text-caption mt-2">Loading permissions...</div>
              </div>
              
              <!-- Permissions loaded -->
              <div v-else-if="itemPermissions">
                <!-- Summary card -->
                <v-card flat class="mb-3 permission-summary" color="grey-lighten-5">
                  <v-card-text class="pa-3">
                    <div class="d-flex justify-space-around text-center">
                      <div>
                        <div class="text-h6 font-weight-bold primary--text">
                          {{ getTotalPermissionsCount() }}
                        </div>
                        <div class="text-caption">Total Access</div>
                      </div>
                      <v-divider vertical></v-divider>
                      <div>
                        <div class="text-h6 font-weight-bold">
                          {{ (itemPermissions.users || []).length }}
                        </div>
                        <div class="text-caption">Users</div>
                      </div>
                      <v-divider vertical></v-divider>
                      <div>
                        <div class="text-h6 font-weight-bold">
                          {{ (itemPermissions.groups || []).length }}
                        </div>
                        <div class="text-caption">Groups</div>
                      </div>
                      <div v-if="(itemPermissions.shared_links || []).length > 0">
                        <v-divider vertical class="mx-2"></v-divider>
                        <div>
                          <div class="text-h6 font-weight-bold blue--text">
                            {{ (itemPermissions.shared_links || []).length }}
                          </div>
                          <div class="text-caption">Links</div>
                        </div>
                      </div>
                    </div>
                  </v-card-text>
                </v-card>
                
                <!-- Permission entries -->
                <div class="permissions-list">
                  <!-- Users Section -->
                  <div v-if="itemPermissions.users && itemPermissions.users.length > 0" class="permission-section">
                    <div class="permission-section-header">
                      <v-icon size="16" class="mr-1">mdi-account</v-icon>
                      <span class="text-caption font-weight-medium">USERS</span>
                    </div>
                    <v-list dense class="pa-0">
                      <v-list-item
                        v-for="user in itemPermissions.users"
                        :key="user.principal_id || user.principal_name"
                        class="px-0 permission-item"
                      >
                        <template v-slot:prepend>
                          <v-avatar size="32" :color="getAvatarColor(user.principal_name || user.principal_email)" class="mr-3">
                            <span class="white--text text-caption">
                              {{ getInitials(user.principal_name || user.principal_email) }}
                            </span>
                          </v-avatar>
                        </template>
                        <template v-slot:default>
                          <v-list-item-title class="text-body-2">
                            {{ formatPrincipalName(user.principal_name, user.principal_email) }}
                          </v-list-item-title>
                          <v-list-item-subtitle>
                            <div class="d-flex align-center flex-wrap">
                              <v-chip x-small label :color="getPermissionColor(user.permission_level)" class="mr-2">
                                {{ formatPermissionLevel(user.permission_level) }}
                              </v-chip>
                              <span v-if="user.permission_type === 'direct'" class="mr-2">
                                <v-icon size="12" color="orange">mdi-shield-key</v-icon>
                                Direct
                              </span>
                              <span v-if="user.permission_type === 'inherited'" class="mr-2 text-grey">
                                <v-icon size="12">mdi-shield-check</v-icon>
                                Inherited
                              </span>
                            </div>
                            <div v-if="user.principal_email && user.principal_email !== user.principal_name" class="text-caption text-grey mt-1">
                              {{ user.principal_email }}
                            </div>
                          </v-list-item-subtitle>
                        </template>
                      </v-list-item>
                    </v-list>
                  </div>
                  
                  <!-- Groups Section -->
                  <div v-if="itemPermissions.groups && itemPermissions.groups.length > 0" class="permission-section mt-3">
                    <div class="permission-section-header d-flex justify-space-between align-center">
                      <div>
                        <v-icon size="16" class="mr-1">mdi-account-multiple</v-icon>
                        <span class="text-caption font-weight-medium">GROUPS</span>
                      </div>
                      <v-btn
                        size="x-small"
                        variant="text"
                        color="primary"
                        @click="openGroupPermissionsModal"
                      >
                        <v-icon size="14">mdi-eye</v-icon>
                        <span class="ml-1">View permissions</span>
                      </v-btn>
                    </div>
                    <v-list dense class="pa-0">
                      <v-list-item
                        v-for="group in itemPermissions.groups"
                        :key="group.principal_id || group.principal_name"
                        class="px-0 permission-item clickable-group"
                        @click="openGroupMembersModal(group)"
                        style="cursor: pointer;"
                        :ripple="true"
                      >
                        <template v-slot:prepend>
                          <v-avatar size="32" color="blue-grey" class="mr-3">
                            <v-icon size="18" color="white">mdi-account-multiple</v-icon>
                          </v-avatar>
                        </template>
                        <template v-slot:default>
                          <v-list-item-title class="text-body-2">
                            <span>{{ formatPrincipalName(group.principal_name, group.principal_email) }}</span>
                            <v-tooltip v-if="group.principal_name === detailItem.name" location="top">
                              <template v-slot:activator="{ props }">
                                <v-icon 
                                  v-bind="props" 
                                  size="14" 
                                  color="warning" 
                                  class="ml-1"
                                >
                                  mdi-alert
                                </v-icon>
                              </template>
                              <span>Group name appears corrupted. Re-collect permissions to fix.</span>
                            </v-tooltip>
                          </v-list-item-title>
                          <v-list-item-subtitle>
                            <div class="d-flex align-center flex-wrap">
                              <v-chip x-small label :color="getPermissionColor(group.permission_level)" class="mr-2">
                                {{ formatPermissionLevel(group.permission_level) }}
                              </v-chip>
                              <span v-if="group.permission_type === 'direct'" class="mr-2">
                                <v-icon size="12" color="orange">mdi-shield-key</v-icon>
                                Direct
                              </span>
                              <span v-if="group.permission_type === 'inherited'" class="mr-2 text-grey">
                                <v-icon size="12">mdi-shield-check</v-icon>
                                Inherited
                              </span>
                            </div>
                            <div v-if="group.principal_email" class="text-caption text-grey mt-1">
                              {{ group.principal_email }}
                            </div>
                            <div v-if="showDebugInfo && group.principal_id" class="text-caption text-grey mt-1">
                              ID: {{ group.principal_id.substring(0, 40) }}{{ group.principal_id.length > 40 ? '...' : '' }}
                            </div>
                          </v-list-item-subtitle>
                        </template>
                      </v-list-item>
                    </v-list>
                  </div>
                  
                  <!-- Shared Links Section -->
                  <div v-if="itemPermissions.shared_links && itemPermissions.shared_links.length > 0" class="permission-section mt-3">
                    <div class="permission-section-header">
                      <v-icon size="16" class="mr-1" color="blue">mdi-link</v-icon>
                      <span class="text-caption font-weight-medium">SHARED LINKS</span>
                    </div>
                    <v-list dense class="pa-0">
                      <v-list-item
                        v-for="link in itemPermissions.shared_links"
                        :key="link.principal_name"
                        class="px-0 permission-item"
                      >
                        <template v-slot:prepend>
                          <v-avatar size="32" color="blue" class="mr-3">
                            <v-icon size="18" color="white">mdi-link</v-icon>
                          </v-avatar>
                        </template>
                        <template v-slot:default>
                          <v-list-item-title class="text-body-2">
                            {{ link.principal_name }}
                          </v-list-item-title>
                          <v-list-item-subtitle class="text-caption">
                            <v-chip x-small label color="blue" text-color="white">
                              {{ formatPermissionLevel(link.permission_level) }}
                            </v-chip>
                          </v-list-item-subtitle>
                        </template>
                      </v-list-item>
                    </v-list>
                  </div>
                </div>
                
                <!-- No permissions message -->
                <div v-if="getTotalPermissionsCount() === 0" class="text-center py-4 text-grey">
                  <v-icon size="48" color="grey-lighten-1">mdi-shield-off</v-icon>
                  <div class="text-body-2 mt-2">No specific permissions found</div>
                  <div class="text-caption">This item inherits permissions from its parent</div>
                </div>
              </div>
              
              <!-- Permissions not loaded yet -->
              <div v-else class="text-center py-4">
                <div v-if="detailItem.statistics && detailItem.statistics.principal_count > 0">
                  <v-card flat class="mb-3 permission-summary" color="grey-lighten-5">
                    <v-card-text class="pa-3">
                      <div class="d-flex justify-space-around text-center">
                        <div>
                          <div class="text-h6 font-weight-bold primary--text">
                            {{ detailItem.statistics.principal_count }}
                          </div>
                          <div class="text-caption">Total Access</div>
                        </div>
                        <v-divider vertical></v-divider>
                        <div>
                          <div class="text-h6 font-weight-bold">
                            {{ detailItem.statistics.user_count || 0 }}
                          </div>
                          <div class="text-caption">Users</div>
                        </div>
                        <v-divider vertical></v-divider>
                        <div>
                          <div class="text-h6 font-weight-bold">
                            {{ detailItem.statistics.group_count || 0 }}
                          </div>
                          <div class="text-caption">Groups</div>
                        </div>
                        <div v-if="detailItem.statistics.shared_count > 0">
                          <v-divider vertical class="mx-2"></v-divider>
                          <div>
                            <div class="text-h6 font-weight-bold blue--text">
                              {{ detailItem.statistics.shared_count }}
                            </div>
                            <div class="text-caption">Links</div>
                          </div>
                        </div>
                      </div>
                    </v-card-text>
                  </v-card>
                  <div class="d-flex gap-2">
                    <v-btn
                      small
                      color="primary"
                      @click="loadItemPermissions"
                      class="mt-2"
                    >
                      <v-icon left>mdi-account-details</v-icon>
                      View Details
                    </v-btn>
                    <v-btn
                      small
                      color="blue-grey"
                      @click="openGroupPermissionsModal"
                      class="mt-2"
                    >
                      <v-icon left>mdi-account-multiple</v-icon>
                      View Permissions
                    </v-btn>
                  </div>
                </div>
                <div v-else class="text-grey">
                  <v-icon size="48" color="grey-lighten-1">mdi-shield-off</v-icon>
                  <div class="text-body-2 mt-2">No permissions data</div>
                  <div class="text-caption">Run permissions collection to see who has access</div>
                </div>
              </div>
            </div>
            
            <v-divider class="my-3"></v-divider>
            
            <!-- Purview Audit Events -->
            <div class="mt-4">
              <div class="text-subtitle-2 mb-2">
                <v-icon size="16" class="mr-1">mdi-shield-check</v-icon>
                Recent Activity (Purview)
                <v-progress-circular
                  v-if="loadingActivity"
                  indeterminate
                  size="16"
                  width="2"
                  color="primary"
                  class="ml-2"
                ></v-progress-circular>
              </div>
              <div v-if="!loadingActivity && purviewEvents.length === 0" class="text-center py-3 text-grey">
                <v-icon size="32" color="grey-lighten-1">mdi-calendar-blank</v-icon>
                <div class="text-caption mt-1">No recent activity found</div>
              </div>
              <v-timeline v-if="purviewEvents.length > 0" dense align-top>
                <v-timeline-item
                  v-for="(event, index) in purviewEvents"
                  :key="index"
                  :dot-color="getEventColor(event.operation)"
                  size="x-small"
                >
                  <template v-slot:opposite>
                    <span class="text-caption">{{ formatEventTime(event.timestamp) }}</span>
                  </template>
                  <div class="pa-2">
                    <div class="font-weight-medium">{{ event.operation }}</div>
                    <div class="text-caption">{{ event.user }}</div>
                    <div class="text-caption text-grey" v-if="event.details">
                      {{ event.details }}
                    </div>
                    <div class="text-caption text-grey" v-if="event.ip">
                      IP: {{ event.ip }}
                    </div>
                  </div>
                </v-timeline-item>
              </v-timeline>
            </div>
          </div>
        </div>
      </div>
    </div><!-- End columns-wrapper -->
    
    <!-- Refresh Modal -->
    <v-dialog v-model="showRefreshModal" max-width="600px">
      <v-card>
        <v-card-title class="text-h5">
          <v-icon left>mdi-refresh</v-icon>
          Refresh SharePoint Data
        </v-card-title>
        <v-card-text>
          <v-alert type="info" outlined class="mb-4">
            Choose which SharePoint data to refresh. This will re-scan and update the folder structure and permissions.
          </v-alert>
          
          <v-radio-group v-model="refreshScope" mandatory>
            <v-radio
              label="Refresh All Sites and Data"
              value="all"
              color="primary"
            >
              <template v-slot:label>
                <div>
                  <strong>Refresh All Sites and Data</strong>
                  <div class="text-caption text-grey">
                    Re-discover all SharePoint sites and scan all folders and permissions
                  </div>
                </div>
              </template>
            </v-radio>
            
            <v-radio
              label="Refresh Specific Site"
              value="site"
              color="primary"
            >
              <template v-slot:label>
                <div>
                  <strong>Refresh Specific Site</strong>
                  <div class="text-caption text-grey">
                    Re-scan folders and permissions for a single SharePoint site
                  </div>
                </div>
              </template>
            </v-radio>
            
            <v-radio
              label="Refresh Current View"
              value="current"
              color="primary"
            >
              <template v-slot:label>
                <div>
                  <strong>Refresh Current View</strong>
                  <div class="text-caption text-grey">
                    Refresh only the data currently visible in the browser
                  </div>
                </div>
              </template>
            </v-radio>
            
            <v-radio
              label="Force Complete Refresh"
              value="force"
              color="warning"
            >
              <template v-slot:label>
                <div>
                  <strong>Force Complete Refresh</strong>
                  <div class="text-caption text-orange">
                    Actually run SharePoint collector to gather fresh data from Microsoft Graph API (slower)
                  </div>
                </div>
              </template>
            </v-radio>
          </v-radio-group>
          
          <!-- Site selector - only show when "site" is selected -->
          <v-select
            v-if="refreshScope === 'site'"
            v-model="selectedRefreshSite"
            :items="sites"
            item-title="name"
            item-value="id"
            label="Select SharePoint Site"
            outlined
            density="compact"
            prepend-icon="mdi-web"
            hint="Choose which site to refresh"
            persistent-hint
            class="mt-3"
          >
            <template v-slot:item="{ props, item }">
              <v-list-item v-bind="props">
                <v-list-item-title>{{ item.raw.name }}</v-list-item-title>
                <v-list-item-subtitle>
                  {{ item.raw.statistics?.total_items || 0 }} items
                </v-list-item-subtitle>
              </v-list-item>
            </template>
          </v-select>
          
          <!-- Progress indicator -->
          <div v-if="refreshing" class="mt-4">
            <v-progress-linear 
              :model-value="refreshProgress" 
              height="6" 
              color="primary"
              striped
            ></v-progress-linear>
            <div class="text-caption text-center mt-2">
              {{ refreshStatusMessage }}
            </div>
          </div>
        </v-card-text>
        
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn 
            text 
            @click="showRefreshModal = false"
            :disabled="refreshing"
          >
            Cancel
          </v-btn>
          <v-btn 
            color="primary" 
            @click="startRefresh"
            :loading="refreshing"
            :disabled="refreshScope === 'site' && !selectedRefreshSite"
          >
            <v-icon left>mdi-refresh</v-icon>
            Start Refresh
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    
    <!-- Permissions Collection Modal -->
    <v-dialog v-model="showPermissionsModal" max-width="600px">
      <v-card>
        <v-card-title>
          <v-icon class="mr-2">mdi-shield-sync</v-icon>
          Collect SharePoint Permissions
        </v-card-title>
        
        <v-card-text>
          <v-alert type="info" variant="tonal" class="mb-4">
            This will scan all SharePoint items and collect detailed permission information, 
            including detecting items with unique (broken) permissions.
          </v-alert>
          
          <div v-if="!collectingPermissions">
            <p class="mb-4">
              The permission collection process will:
            </p>
            <ul class="mb-4">
              <li>Check each folder and file for permission inheritance</li>
              <li>Identify items with unique permissions</li>
              <li>Collect information about who has access to each item</li>
              <li>Update the visual indicators in the browser</li>
            </ul>
            
            <v-alert type="warning" variant="tonal">
              This process may take several minutes depending on the number of items.
            </v-alert>
          </div>
          
          <!-- Progress indicator -->
          <div v-if="collectingPermissions" class="mt-4">
            <v-progress-linear 
              :model-value="permissionsProgress" 
              height="6" 
              color="primary"
              striped
              :indeterminate="permissionsProgress === 0"
            ></v-progress-linear>
            <div class="text-caption text-center mt-2">
              {{ permissionsStatusMessage }}
            </div>
            
            <!-- Statistics during collection -->
            <div v-if="permissionsStats" class="mt-4">
              <v-simple-table dense>
                <tbody>
                  <tr>
                    <td>Total Resources:</td>
                    <td class="text-right">{{ permissionsStats.total_resources }}</td>
                  </tr>
                  <tr>
                    <td>Processed:</td>
                    <td class="text-right">{{ permissionsStats.processed }}</td>
                  </tr>
                  <tr>
                    <td>Unique Permissions Found:</td>
                    <td class="text-right">{{ permissionsStats.unique_permissions_found }}</td>
                  </tr>
                  <tr v-if="permissionsStats.errors > 0">
                    <td>Errors:</td>
                    <td class="text-right text-error">{{ permissionsStats.errors }}</td>
                  </tr>
                </tbody>
              </v-simple-table>
            </div>
          </div>
        </v-card-text>
        
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn 
            text 
            @click="showPermissionsModal = false"
            :disabled="collectingPermissions"
          >
            {{ collectingPermissions ? 'Close' : 'Cancel' }}
          </v-btn>
          <v-btn 
            color="primary" 
            @click="startPermissionsCollection"
            :loading="collectingPermissions"
            v-if="!permissionsStats"
          >
            <v-icon left>mdi-play</v-icon>
            Start Collection
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Group Permissions Modal - Smart Scalable Design -->
    <v-dialog v-model="showGroupPermissionsModal" max-width="1000px">
      <v-card class="group-modal-card">
        <div class="modal-header-gradient">
          <v-card-title class="d-flex align-center text-white">
            <v-icon class="mr-3" size="28" color="white">mdi-shield-account</v-icon>
            <div class="flex-grow-1">
              <div class="text-h5">Group Permissions & Membership</div>
              <div class="text-caption opacity-80">
                {{ getGroupsFromPermissions().length }} group{{ getGroupsFromPermissions().length !== 1 ? 's' : '' }} with access
              </div>
            </div>
            <!-- View Toggle for many groups -->
            <v-btn-toggle 
              v-if="getGroupsFromPermissions().length > 6"
              v-model="groupViewMode"
              mandatory
              density="compact"
              class="ml-4"
            >
              <v-btn value="cards" size="small">
                <v-icon size="16">mdi-view-grid</v-icon>
              </v-btn>
              <v-btn value="list" size="small">
                <v-icon size="16">mdi-view-list</v-icon>
              </v-btn>
            </v-btn-toggle>
          </v-card-title>
        </div>
        
        <v-card-text class="pa-0">
          <!-- Loading state while fetching permissions -->
          <div v-if="!itemPermissionsLoaded && loadingPermissions" class="text-center py-8">
            <v-progress-circular indeterminate size="48" color="primary" :width="3"></v-progress-circular>
            <div class="text-body-2 mt-3 text-grey">Discovering groups...</div>
          </div>
          
          <div v-else-if="itemPermissions && itemPermissions.groups && itemPermissions.groups.length > 0" class="groups-container">
            <!-- Search/Filter Bar for many groups -->
            <div v-if="getGroupsFromPermissions().length > 6" class="px-4 pt-4 pb-2 search-section">
              <v-text-field
                v-model="groupSearchQuery"
                density="compact"
                variant="outlined"
                placeholder="Search groups..."
                prepend-inner-icon="mdi-magnify"
                clearable
                hide-details
                class="mb-3"
              ></v-text-field>
              
              <!-- Quick filters -->
              <div class="d-flex gap-2 flex-wrap">
                <v-chip
                  v-for="level in getUniquePermissionLevels()"
                  :key="level"
                  size="small"
                  :color="groupPermissionFilter === level ? 'primary' : 'default'"
                  :variant="groupPermissionFilter === level ? 'flat' : 'outlined'"
                  @click="togglePermissionFilter(level)"
                  class="cursor-pointer"
                >
                  <v-icon size="14" start>{{ getPermissionIcon(level) }}</v-icon>
                  {{ formatPermissionLevel(level) }}
                </v-chip>
                <v-chip
                  v-if="groupPermissionFilter"
                  size="small"
                  color="error"
                  variant="tonal"
                  @click="groupPermissionFilter = null"
                  class="cursor-pointer"
                >
                  <v-icon size="14" start>mdi-close</v-icon>
                  Clear Filter
                </v-chip>
              </div>
            </div>
            
            <!-- Smart Layout: Cards for ≤6 groups, List for >6 groups -->
            <div v-if="groupViewMode === 'cards' && filteredGroups().length <= 12" class="groups-grid pa-4">
              <v-row>
                <v-col 
                  v-for="group in filteredGroups()"
                  :key="group.principal_id || group.principal_name"
                  cols="12"
                  :md="getGroupsFromPermissions().length <= 3 ? 4 : 6"
                  :lg="getGroupsFromPermissions().length <= 3 ? 4 : 4"
                >
                  <v-card 
                    @click="selectGroup(group)"
                    :class="['group-card', { 'group-card-selected': selectedGroup && selectedGroup.principal_id === group.principal_id }]"
                    :elevation="selectedGroup && selectedGroup.principal_id === group.principal_id ? 8 : 2"
                  >
                    <div class="group-card-gradient-compact">
                      <v-avatar size="48" color="white" class="elevation-2">
                        <v-icon 
                          size="28" 
                          :color="getGroupIconColor(group.permission_level)"
                        >
                          {{ getGroupIcon(group.permission_level) }}
                        </v-icon>
                      </v-avatar>
                    </div>
                    
                    <v-card-text class="text-center pb-2">
                      <div class="text-subtitle-2 font-weight-bold text-truncate">
                        {{ formatPrincipalName(group.principal_name, group.principal_email) }}
                      </div>
                      <v-chip 
                        size="x-small" 
                        :color="getPermissionColor(group.permission_level)"
                        variant="flat"
                        class="mt-1"
                      >
                        {{ formatPermissionLevel(group.permission_level) }}
                      </v-chip>
                    </v-card-text>
                  </v-card>
                </v-col>
              </v-row>
              
              <!-- Show more message if filtered -->
              <div v-if="groupSearchQuery && filteredGroups().length === 0" class="text-center py-4 text-grey">
                <v-icon size="48">mdi-magnify-remove</v-icon>
                <div class="text-body-2 mt-2">No groups match "{{ groupSearchQuery }}"</div>
              </div>
            </div>
            
            <!-- Compact List View for many groups -->
            <div v-else class="groups-list-view">
              <v-list class="py-0">
                <template v-for="(group, index) in filteredGroups()" :key="group.principal_id || group.principal_name">
                  <v-list-item
                    @click="selectGroup(group)"
                    :class="{ 'selected-list-item': selectedGroup && selectedGroup.principal_id === group.principal_id }"
                    class="group-list-item"
                  >
                    <template v-slot:prepend>
                      <v-avatar size="36" :color="getGroupIconColor(group.permission_level)">
                        <v-icon size="20" color="white">
                          {{ getGroupIcon(group.permission_level) }}
                        </v-icon>
                      </v-avatar>
                    </template>
                    
                    <v-list-item-title class="text-body-2 font-weight-medium">
                      {{ formatPrincipalName(group.principal_name, group.principal_email) }}
                    </v-list-item-title>
                    
                    <v-list-item-subtitle>
                      <v-chip 
                        size="x-small" 
                        :color="getPermissionColor(group.permission_level)"
                        variant="tonal"
                      >
                        {{ formatPermissionLevel(group.permission_level) }}
                      </v-chip>
                    </v-list-item-subtitle>
                    
                    <template v-slot:append>
                      <v-icon size="20" color="grey">mdi-chevron-right</v-icon>
                    </template>
                  </v-list-item>
                  <v-divider v-if="index < filteredGroups().length - 1" />
                </template>
              </v-list>
              
              <!-- No results message -->
              <div v-if="filteredGroups().length === 0" class="text-center py-4 text-grey">
                <v-icon size="48">mdi-filter-remove</v-icon>
                <div class="text-body-2 mt-2">No groups match your filters</div>
              </div>
            </div>
            
            <!-- Selected Group Members Section - Beautiful Design -->
            <v-expand-transition>
              <div v-if="selectedGroup" class="members-section">
                <div class="members-header px-4 py-3">
                  <div class="d-flex align-center">
                    <v-avatar size="40" :color="getGroupIconColor(selectedGroup.permission_level)" class="mr-3">
                      <v-icon size="24" color="white">{{ getGroupIcon(selectedGroup.permission_level) }}</v-icon>
                    </v-avatar>
                    <div class="flex-grow-1">
                      <div class="text-h6 font-weight-medium">
                        {{ selectedGroup.principal_name }}
                      </div>
                      <div class="text-caption">
                        <v-icon size="14" class="mr-1">mdi-account-group</v-icon>
                        Group Members
                      </div>
                    </div>
                    <v-menu>
                      <template v-slot:activator="{ props }">
                        <v-btn
                          icon
                          size="small"
                          variant="text"
                          v-bind="props"
                          :loading="loadingGroupMembers"
                        >
                          <v-icon>mdi-dots-vertical</v-icon>
                        </v-btn>
                      </template>
                      <v-list density="compact">
                        <v-list-item @click="refreshGroupMembers(false)">
                          <v-list-item-title>
                            <v-icon size="small" start>mdi-refresh</v-icon>
                            Refresh from Cache
                          </v-list-item-title>
                        </v-list-item>
                        <v-list-item @click="syncGroupMembers">
                          <v-list-item-title>
                            <v-icon size="small" start>mdi-cloud-sync</v-icon>
                            Sync from Entra ID
                          </v-list-item-title>
                        </v-list-item>
                      </v-list>
                    </v-menu>
                  </div>
                </div>
                
                <!-- Loading members with beautiful animation -->
                <div v-if="loadingGroupMembers || (groupMembers && groupMembers.syncing)" class="text-center py-8">
                  <div class="loading-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                  <div class="text-body-2 mt-3 text-grey">
                    {{ groupMembers && groupMembers.syncing ? 'Syncing members from Entra ID...' : 'Discovering members...' }}
                  </div>
                  <div v-if="groupMembers && groupMembers.syncing" class="text-caption mt-2 text-grey">
                    This may take a few moments for large groups
                  </div>
                </div>
                
                <!-- Members Grid - Modern Card Layout -->
                <div v-else-if="groupMembers && groupMembers.members && groupMembers.members.length > 0" class="px-4 pb-4">
                  <div class="members-stats mb-4 d-flex align-center justify-space-between">
                    <div>
                      <v-chip color="primary" variant="flat" size="small">
                        <v-icon size="14" start>mdi-account-multiple</v-icon>
                        {{ groupMembers.totalMembers || groupMembers.members.length }} Total Members
                      </v-chip>
                      <v-chip v-if="groupMembers.source === 'cached'" color="grey" variant="tonal" size="small" class="ml-2">
                        <v-icon size="14" start>mdi-database</v-icon>
                        Cached
                      </v-chip>
                    </div>
                    <div v-if="groupMembers.last_sync" class="text-caption text-grey">
                      Last synced: {{ formatLastSync(groupMembers.last_sync) }}
                    </div>
                  </div>
                  
                  <v-row>
                    <v-col 
                      v-for="member in groupMembers.members"
                      :key="member.id"
                      cols="12"
                      sm="6"
                      md="4"
                    >
                      <v-card class="member-card" :elevation="1">
                        <div class="member-card-header">
                          <v-avatar 
                            size="48" 
                            :color="getMemberAvatarColor(member)"
                            class="elevation-2"
                          >
                            <span v-if="member.displayName" class="text-h6 text-white">
                              {{ member.displayName.charAt(0).toUpperCase() }}
                            </span>
                            <v-icon v-else size="28" color="white">
                              {{ member.memberType === 'user' ? 'mdi-account' : member.memberType === 'group' ? 'mdi-account-multiple' : 'mdi-application' }}
                            </v-icon>
                          </v-avatar>
                        </div>
                        
                        <v-card-text class="text-center pb-2">
                          <div class="text-subtitle-2 font-weight-bold text-truncate">
                            {{ member.displayName || member.name || 'Unknown' }}
                          </div>
                          <div class="text-caption text-grey text-truncate">
                            {{ member.email || member.userPrincipalName || '—' }}
                          </div>
                          
                          <div class="mt-2">
                            <v-chip 
                              size="x-small" 
                              :color="getMemberTypeColor(member.memberType)"
                              variant="tonal"
                            >
                              <v-icon size="12" start>{{ getMemberTypeIcon(member.memberType) }}</v-icon>
                              {{ member.memberType || member.type || 'Unknown' }}
                            </v-chip>
                          </div>
                          
                          <div v-if="member.jobTitle" class="text-caption mt-2 text-grey">
                            {{ member.jobTitle }}
                          </div>
                          <div v-if="member.department" class="text-caption text-grey">
                            {{ member.department }}
                          </div>
                        </v-card-text>
                      </v-card>
                    </v-col>
                  </v-row>
                </div>
                
                <!-- No Data Available Message -->
                <div v-else-if="groupMembers && groupMembers.no_data" class="px-4 pb-4">
                  <v-alert
                    :type="groupMembers.is_legacy_group ? 'error' : 'warning'"
                    variant="tonal"
                    class="mb-0"
                  >
                    <v-icon slot="prepend">{{ groupMembers.is_legacy_group ? 'mdi-microsoft-sharepoint' : 'mdi-database-remove' }}</v-icon>
                    <div class="text-subtitle-2 font-weight-medium mb-1">
                      {{ groupMembers.is_legacy_group ? 'SharePoint-Only Group' : 'No Member Data Available' }}
                    </div>
                    <div class="text-body-2">{{ groupMembers.message || 'Group member data has not been synchronized from Entra ID.' }}</div>
                    
                    <!-- Show required permissions if specified -->
                    <div v-if="groupMembers.permission_required" class="mt-2">
                      <v-chip size="small" color="error" variant="outlined">
                        <v-icon size="14" start>mdi-shield-lock</v-icon>
                        Required Permission: {{ groupMembers.permission_required }}
                      </v-chip>
                    </div>
                    
                    <div class="mt-3 d-flex gap-2">
                      <!-- Sync button only if not a legacy group -->
                      <v-btn
                        v-if="!groupMembers.is_legacy_group"
                        small
                        color="primary"
                        variant="flat"
                        @click="syncGroupMembers"
                        prepend-icon="mdi-cloud-sync"
                        :loading="loadingGroupMembers"
                      >
                        Sync from Entra ID
                      </v-btn>
                      
                      <!-- SharePoint link button if available -->
                      <v-btn
                        v-if="groupMembers.sharepoint_url"
                        small
                        :color="groupMembers.is_legacy_group ? 'primary' : 'secondary'"
                        :variant="groupMembers.is_legacy_group ? 'flat' : 'tonal'"
                        :href="groupMembers.sharepoint_url"
                        target="_blank"
                        prepend-icon="mdi-open-in-new"
                      >
                        View in SharePoint
                      </v-btn>
                    </div>
                  </v-alert>
                </div>
                
                <!-- API Limitation Message (for other errors) -->
                <div v-else-if="groupMembers && groupMembers.message && !groupMembers.no_data" class="px-4 pb-4">
                  <v-alert
                    type="info"
                    variant="tonal"
                    class="mb-0"
                  >
                    <v-icon slot="prepend">mdi-information</v-icon>
                    <div class="text-subtitle-2 font-weight-medium mb-1">Information</div>
                    <div class="text-body-2">{{ groupMembers.message }}</div>
                  </v-alert>
                </div>
                
                <!-- No members found -->
                <div v-else class="text-center py-8">
                  <v-icon size="64" color="grey-lighten-2">mdi-database-off</v-icon>
                  <div class="text-body-1 mt-3 text-grey">No member data available</div>
                  <div class="text-caption text-grey">Sync from Entra ID to view group members</div>
                  <v-btn
                    small
                    color="primary"
                    variant="flat"
                    @click="syncGroupMembers"
                    class="mt-3"
                    prepend-icon="mdi-cloud-sync"
                    :loading="loadingGroupMembers"
                  >
                    Sync from Entra ID
                  </v-btn>
                </div>
              </div>
            </v-expand-transition>
            
            <!-- No group selected message -->
            <div v-if="!selectedGroup && getGroupsFromPermissions().length > 0" class="text-center py-4 text-grey">
              <v-icon size="48" color="grey-lighten-1">mdi-hand-pointing-up</v-icon>
              <div class="text-body-2 mt-2">Select a group to view its members</div>
            </div>
          </div>
          
          <!-- No groups message -->
          <div v-else class="text-center py-4 text-grey">
            <v-icon size="48" color="grey-lighten-1">mdi-account-multiple-remove</v-icon>
            <div class="text-body-2 mt-2">No groups found</div>
          </div>
        </v-card-text>
        
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn
            text
            @click="closeGroupPermissionsModal"
          >
            Close
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script>
import { apiClient } from '../services/api';

export default {
  name: 'SharePointColumns',
  
  data() {
    return {
      sites: [],
      selectedSite: null,
      topLevelFolders: [],
      dynamicColumns: [], // Dynamic columns for deep navigation
      selectedPath: [], // Track selected items at each level
      allSiteData: {}, // Cache site data
      loading: false,
      loadingFolders: false,
      tenantId: '213f39fb-b0c7-42d6-8289-01785b02b388',
      breadcrumbPath: [],
      purviewEvents: [], // Purview audit events from external audit logs
      loadingActivity: false,
      columnWidths: {
        'sites': 300,
        'site-content': 300,
        'details': 500
      }, // Store custom column widths
      resizing: null, // Track which column is being resized
      startX: 0,
      startWidth: 0,
      // Refresh modal properties
      showRefreshModal: false,
      refreshScope: 'current', // 'all', 'site', 'current'
      selectedRefreshSite: null,
      refreshing: false,
      refreshProgress: 0,
      refreshStatusMessage: '',
      // Filter properties
      filterPerson: '',
      filterSite: null,
      filterPermissionType: null,
      // PDF export
      exportingPdf: false,
      permissionTypes: [
        { title: 'All Permissions', value: 'all' },
        { title: 'Unique Permissions Only', value: 'unique' },
        { title: 'Inherited Permissions Only', value: 'inherited' }
      ],
      filteredData: null,
      // Permissions collection properties
      showPermissionsModal: false,
      collectingPermissions: false,
      permissionsProgress: 0,
      permissionsStatusMessage: '',
      permissionsStats: null,
      itemPermissions: null,
      itemPermissionsLoaded: false,
      loadingPermissions: false,
      showDebugInfo: false,  // Set to true to show principal IDs
      // Group permissions modal properties
      showGroupPermissionsModal: false,
      selectedGroup: null,
      groupMembers: null,
      loadingGroupMembers: false,
      // Search and filter properties for scalable modal
      groupSearchQuery: '',
      groupPermissionFilter: null,
      groupViewMode: 'cards',
      // Empty folder tracking
      selectedEmptyFolder: null
    };
  },
  
  computed: {
    detailItem() {
      // Return the last selected item from selectedPath, or selectedSite
      if (this.selectedPath.length > 0) {
        return this.selectedPath[this.selectedPath.length - 1];
      }
      return this.selectedSite;
    },
    
    showEmptyFolderMessage() {
      // Show message when an empty folder is selected and no dynamic columns are shown
      return this.selectedEmptyFolder !== null && this.dynamicColumns.length === 0 && 
             this.selectedPath.length > 0 && 
             this.selectedPath[this.selectedPath.length - 1].type === 'folder';
    },
    
    hasActiveFilters() {
      return !!(this.filterPerson || this.filterSite || this.filterPermissionType);
    }
  },
  
  watch: {
    detailItem(newItem) {
      // Generate Purview events when a new item is selected
      if (newItem) {
        console.log('Selected item:', newItem); // Debug log
        if (newItem.type !== 'site') {
          // Load real activity data from audit logs
          this.loadActivityData(newItem);
          // Load permissions for the item
          this.itemPermissions = null;
          this.itemPermissionsLoaded = false;
          this.loadItemPermissions();
        } else {
          this.purviewEvents = [];
          this.itemPermissions = null;
          this.itemPermissionsLoaded = false;
        }
      }
    }
  },
  
  mounted() {
    this.loadSites();
    
    // Add mouse event listeners for resize - bind to preserve 'this' context
    this.boundHandleResize = this.handleResize.bind(this);
    this.boundStopResize = this.stopResize.bind(this);
    document.addEventListener('mousemove', this.boundHandleResize);
    document.addEventListener('mouseup', this.boundStopResize);
  },
  
  beforeUnmount() {
    // Clean up event listeners
    document.removeEventListener('mousemove', this.boundHandleResize);
    document.removeEventListener('mouseup', this.boundStopResize);
  },
  
  methods: {
    async loadSites() {
      this.loading = true;
      try {
        const response = await apiClient.get(`/sharepoint-simple/tenant/${this.tenantId}/sites`);
        if (response.data && response.data.sites) {
          this.sites = response.data.sites;
          console.log('Loaded sites:', this.sites.length);
        }
      } catch (error) {
        console.error('Error loading sites:', error);
      } finally {
        this.loading = false;
      }
    },
    
    async selectSite(site) {
      this.selectedSite = site;
      this.selectedPath = []; // Clear selection path
      this.dynamicColumns = []; // Clear all dynamic columns
      this.selectedEmptyFolder = null; // Reset empty folder tracking
      
      // Update breadcrumb
      this.breadcrumbPath = [
        { text: site.name, value: site, type: 'site' }
      ];
      
      await this.loadSiteFolders(site);
    },
    
    async loadSiteFolders(site) {
      this.loadingFolders = true;
      this.topLevelFolders = [];
      
      try {
        // Check cache first
        if (!this.allSiteData[site.id]) {
          console.log('Loading data for site:', site.name);
          const response = await apiClient.get(`/sharepoint-simple/tenant/${this.tenantId}/site/${site.id}`);
          
          if (response.data && response.data.nodes) {
            this.allSiteData[site.id] = response.data.nodes;
          }
        }
        
        const nodes = this.allSiteData[site.id] || [];
        
        // Get ALL top-level items (folders AND files)
        // Items with parent_id matching site.id OR with is_top_level flag
        const topItems = nodes.filter(n => 
          (n.parent_id === site.id || n.is_top_level === true) && 
          (n.type === 'folder' || n.type === 'file')
        );
        
        // Remove duplicates and count children
        const uniqueItems = {};
        topItems.forEach(item => {
          if (!uniqueItems[item.id] || item.has_unique_permissions) {
            // For folders, count their children
            if (item.type === 'folder') {
              const childCount = nodes.filter(n => n.parent_id === item.id).length;
              uniqueItems[item.id] = {
                ...item,
                childCount
              };
            } else {
              uniqueItems[item.id] = item;
            }
          }
        });
        
        // Sort folders first, then files
        this.topLevelFolders = Object.values(uniqueItems).sort((a, b) => {
          if (a.type === b.type) return a.name.localeCompare(b.name);
          return a.type === 'folder' ? -1 : 1;
        });
        console.log('Top-level items:', this.topLevelFolders.length);
        
      } catch (error) {
        console.error('Error loading folders:', error);
      } finally {
        this.loadingFolders = false;
      }
    },
    
    selectTopLevelItem(item) {
      // Clear any existing dynamic columns
      this.dynamicColumns = [];
      this.selectedPath = [item];
      this.selectedEmptyFolder = null; // Reset empty folder tracking
      
      if (item.type === 'folder') {
        if (item.childCount > 0) {
          // Only add a new column if the folder has contents
          this.addDynamicColumn(item, 0);
        } else {
          // Track that we selected an empty folder
          this.selectedEmptyFolder = item;
        }
      }
      
      // Update breadcrumb
      this.breadcrumbPath = [
        { text: this.selectedSite.name, value: this.selectedSite, type: 'site' },
        { text: item.name, value: item, type: item.type }
      ];
    },
    
    async addDynamicColumn(folder, columnIndex) {
      // Remove any columns after this index
      this.dynamicColumns = this.dynamicColumns.slice(0, columnIndex);
      
      // First check if the folder has any items
      const nodes = this.allSiteData[this.selectedSite.id] || [];
      const items = nodes.filter(n => n.parent_id === folder.id);
      
      // If folder is empty, don't create a column
      if (items.length === 0) {
        console.log(`Folder ${folder.name} is empty, not creating column`);
        return;
      }
      
      // Create new column
      const newColumn = {
        id: folder.id,
        title: folder.name,
        icon: 'mdi-folder',
        items: [],
        loading: true,
        parentFolder: folder
      };
      
      this.dynamicColumns.push(newColumn);
      
      // Load contents for this folder
      try {
        // Remove duplicates and count children
        const uniqueItems = {};
        items.forEach(item => {
          if (!uniqueItems[item.id] || item.has_unique_permissions) {
            // For folders, count their children
            if (item.type === 'folder') {
              const childCount = nodes.filter(n => n.parent_id === item.id).length;
              uniqueItems[item.id] = {
                ...item,
                childCount
              };
            } else {
              uniqueItems[item.id] = item;
            }
          }
        });
        
        // Sort folders first, then files
        newColumn.items = Object.values(uniqueItems).sort((a, b) => {
          if (a.type === b.type) return a.name.localeCompare(b.name);
          return a.type === 'folder' ? -1 : 1;
        });
        
        console.log(`Loaded ${newColumn.items.length} items for folder ${folder.name}`);
        
      } catch (error) {
        console.error('Error loading folder contents:', error);
      } finally {
        newColumn.loading = false;
      }
      
      // Auto-scroll to show the new column
      this.$nextTick(() => {
        const container = this.$el.querySelector('.columns-container');
        if (container) {
          container.scrollLeft = container.scrollWidth;
        }
      });
    },
    
    getItemIcon(item) {
      if (item.type === 'site') return 'mdi-web';
      if (item.type === 'folder') {
        return item.has_unique_permissions ? 'mdi-folder-key' : 'mdi-folder';
      }
      
      // File icons based on extension - with lock overlay for unique permissions
      const ext = item.name.split('.').pop().toLowerCase();
      let baseIcon;
      switch (ext) {
        case 'doc':
        case 'docx': baseIcon = 'mdi-file-word'; break;
        case 'xls':
        case 'xlsx': baseIcon = 'mdi-file-excel'; break;
        case 'ppt':
        case 'pptx': baseIcon = 'mdi-file-powerpoint'; break;
        case 'pdf': baseIcon = 'mdi-file-pdf-box'; break;
        default: baseIcon = 'mdi-file-document';
      }
      
      // Add lock variant for files with unique permissions
      if (item.has_unique_permissions) {
        switch (ext) {
          case 'doc':
          case 'docx': return 'mdi-file-word-box';
          case 'xls':
          case 'xlsx': return 'mdi-file-excel-box';
          case 'ppt':
          case 'pptx': return 'mdi-file-powerpoint-box';
          default: return 'mdi-file-lock';
        }
      }
      return baseIcon;
    },
    
    getItemColor(item) {
      // Color scheme:
      // - Red/Orange: Broken inheritance or unique permissions
      // - Green: Normal inherited permissions
      // - Blue: Sites
      
      if (item.type === 'site') return 'blue';
      
      // Items with broken inheritance or unique permissions
      if (item.has_unique_permissions) {
        return 'error'; // Red color for broken inheritance
      }
      
      // Normal items with inherited permissions
      if (item.type === 'folder') {
        return 'success'; // Green for folders with inherited permissions
      }
      
      // Files with inherited permissions
      return 'grey darken-1';
    },
    
    async viewPermissions() {
      // Call the group permissions modal instead
      this.openGroupPermissionsModal();
    },
    
    async refresh() {
      this.allSiteData = {}; // Clear cache
      await this.loadSites();
      if (this.selectedSite) {
        await this.selectSite(this.selectedSite);
      }
    },
    
    async startRefresh() {
      this.refreshing = true;
      this.refreshProgress = 0;
      this.refreshStatusMessage = 'Starting refresh...';
      
      try {
        if (this.refreshScope === 'all') {
          await this.refreshAllData();
        } else if (this.refreshScope === 'site') {
          await this.refreshSiteData();
        } else if (this.refreshScope === 'current') {
          await this.refreshCurrentView();
        } else if (this.refreshScope === 'force') {
          await this.forceRefreshAllData();
        }
        
        this.refreshStatusMessage = 'Refresh completed successfully!';
        this.refreshProgress = 100;
        
        // Close modal after a short delay
        setTimeout(() => {
          this.showRefreshModal = false;
          this.refreshing = false;
          this.refreshProgress = 0;
          this.refreshStatusMessage = '';
        }, 1500);
        
      } catch (error) {
        console.error('Refresh error:', error);
        this.refreshStatusMessage = `Refresh failed: ${error.message}`;
        
        // Close modal after error display
        setTimeout(() => {
          this.showRefreshModal = false;
          this.refreshing = false;
          this.refreshProgress = 0;
          this.refreshStatusMessage = '';
        }, 3000);
      }
    },
    
    async refreshAllData() {
      this.refreshStatusMessage = 'Re-discovering SharePoint sites...';
      this.refreshProgress = 10;
      
      // Trigger backend to re-discover all sites
      await apiClient.post('/sharepoint-simple/refresh-all');
      this.refreshProgress = 30;
      
      this.refreshStatusMessage = 'Clearing local cache...';
      this.allSiteData = {};
      this.selectedSite = null;
      this.topLevelFolders = [];
      this.dynamicColumns = [];
      this.selectedPath = [];
      this.breadcrumbPath = [];
      this.refreshProgress = 50;
      
      this.refreshStatusMessage = 'Loading updated site data...';
      await this.loadSites();
      this.refreshProgress = 100;
    },
    
    async refreshSiteData() {
      if (!this.selectedRefreshSite) {
        throw new Error('No site selected for refresh');
      }
      
      this.refreshStatusMessage = 'Refreshing site data...';
      this.refreshProgress = 20;
      
      // Trigger backend to refresh specific site
      const response = await apiClient.post(`/sharepoint-simple/refresh-site/${this.selectedRefreshSite}`);
      this.refreshProgress = 50;
      
      // Show collection stats if available
      if (response.data?.statistics) {
        const stats = response.data.statistics;
        this.refreshStatusMessage = `Collected ${stats.folders} folders and ${stats.files} files`;
        this.refreshProgress = 60;
      }
      
      this.refreshStatusMessage = 'Clearing site cache...';
      // Clear cache for this site
      if (this.allSiteData[this.selectedRefreshSite]) {
        delete this.allSiteData[this.selectedRefreshSite];
      }
      this.refreshProgress = 70;
      
      this.refreshStatusMessage = 'Reloading sites list...';
      // Reload the sites list to get updated counts
      await this.loadSites();
      this.refreshProgress = 85;
      
      this.refreshStatusMessage = 'Reloading site data...';
      // If this is the currently selected site, reload its data
      if (this.selectedSite && this.selectedSite.id === this.selectedRefreshSite) {
        const site = this.sites.find(s => s.id === this.selectedRefreshSite);
        if (site) {
          await this.selectSite(site);
        }
      }
      this.refreshProgress = 100;
    },
    
    async refreshCurrentView() {
      this.refreshStatusMessage = 'Refreshing current view...';
      this.refreshProgress = 25;
      
      if (this.selectedSite) {
        this.refreshStatusMessage = 'Clearing local cache...';
        // Clear local cache for current site to force reload from backend
        if (this.allSiteData[this.selectedSite.id]) {
          delete this.allSiteData[this.selectedSite.id];
        }
        this.refreshProgress = 50;
        
        this.refreshStatusMessage = 'Reloading current data...';
        await this.selectSite(this.selectedSite);
        this.refreshProgress = 100;
      } else {
        // Just reload sites if no site is selected
        this.refreshStatusMessage = 'Reloading sites list...';
        await this.loadSites();
        this.refreshProgress = 100;
      }
    },
    
    async forceRefreshAllData() {
      this.refreshStatusMessage = 'Starting intensive SharePoint collection...';
      this.refreshProgress = 10;
      
      // Call the force refresh endpoint that actually runs the collector
      const response = await apiClient.post('/sharepoint-simple/force-refresh-all');
      this.refreshProgress = 50;
      
      this.refreshStatusMessage = 'Collection completed, clearing local cache...';
      this.allSiteData = {};
      this.selectedSite = null;
      this.topLevelFolders = [];
      this.dynamicColumns = [];
      this.selectedPath = [];
      this.breadcrumbPath = [];
      this.refreshProgress = 80;
      
      this.refreshStatusMessage = 'Loading updated site data...';
      await this.loadSites();
      this.refreshProgress = 100;
      
      // Show additional info if available
      if (response.data?.sites_processed) {
        this.refreshStatusMessage = `Refresh completed! Processed ${response.data.sites_processed} of ${response.data.total_sites_found} sites.`;
      }
    },
    
    async navigateToBreadcrumb(item) {
      // Navigate back to the selected breadcrumb item
      if (item.type === 'site') {
        await this.selectSite(item.value);
      } else {
        // Find the index of this item in the breadcrumb
        const breadcrumbIndex = this.breadcrumbPath.findIndex(b => b.value.id === item.value.id);
        if (breadcrumbIndex > 0) {
          // Reconstruct the path up to this item
          const newPath = [];
          for (let i = 1; i <= breadcrumbIndex; i++) {
            newPath.push(this.breadcrumbPath[i].value);
          }
          
          // Clear and rebuild the columns
          this.selectedPath = newPath;
          this.dynamicColumns = [];
          
          // Rebuild dynamic columns for folders in the path
          for (let i = 0; i < newPath.length; i++) {
            if (newPath[i].type === 'folder') {
              await this.addDynamicColumn(newPath[i], i);
            }
          }
          
          this.updateBreadcrumbFromPath();
        }
      }
    },
    
    async loadActivityData(item) {
      if (!item || !item.id) {
        this.purviewEvents = [];
        return;
      }
      
      this.loadingActivity = true;
      try {
        console.log('Loading activity data for:', item.id, item.name);
        
        // Try to get real data first
        const response = await apiClient.get(`/sharepoint-activity/${item.id}`, {
          params: {
            days: 30,
            limit: 15
          }
        });
        
        if (response.data && response.data.events && response.data.events.length > 0) {
          console.log('Loaded activity events:', response.data.events.length, 'Data source:', response.data.data_source);
          
          // Transform events to match the UI format
          this.purviewEvents = response.data.events.map(event => ({
            timestamp: event.timestamp,
            operation: event.operation,
            user: event.user,
            ip: event.ip,
            details: event.details,
            result: event.result,
            client: event.client,
            target: event.target
          }));
        } else {
          console.log('No activity events found, using mock data');
          // Fall back to mock data if no real events
          this.purviewEvents = this.generatePurviewEvents(item);
        }
      } catch (error) {
        console.error('Failed to load activity data:', error);
        // Fall back to mock data on error
        this.purviewEvents = this.generatePurviewEvents(item);
      } finally {
        this.loadingActivity = false;
      }
    },
    
    generatePurviewEvents(item) {
      // No mock data - only show real data
      return [];
    },
    
    generatePurviewEventsOld(item) {
      // Original mock generation code (disabled)
      const operations = [
        { op: 'FileAccessed', weight: 40 },
        { op: 'FileModified', weight: 20 },
        { op: 'FileDownloaded', weight: 15 },
        { op: 'FileViewed', weight: 10 },
        { op: 'FileShared', weight: 5 },
        { op: 'FileSyncDownloadedFull', weight: 3 },
        { op: 'FileCheckedOut', weight: 2 },
        { op: 'FileCheckedIn', weight: 2 },
        { op: 'FileVersionViewed', weight: 1 },
        { op: 'FileRestored', weight: 1 },
        { op: 'FileDeleted', weight: 1 }
      ];
      
      const users = [
        'john.smith@company.com',
        'jane.doe@company.com',
        'admin@company.com',
        'sarah.jones@company.com',
        'mike.wilson@company.com',
        'External User <guest_2a4b@company.com>',
        'SharePoint App',
        'System Account'
      ];
      
      const events = [];
      const numEvents = Math.floor(Math.random() * 8) + 3; // 3-10 events
      
      for (let i = 0; i < numEvents; i++) {
        const operation = this.weightedRandom(operations);
        const user = users[Math.floor(Math.random() * users.length)];
        const daysAgo = Math.floor(Math.random() * 30); // Within last 30 days
        const hoursAgo = Math.floor(Math.random() * 24);
        const timestamp = new Date();
        timestamp.setDate(timestamp.getDate() - daysAgo);
        timestamp.setHours(timestamp.getHours() - hoursAgo);
        
        const event = {
          operation: operation,
          user: user,
          timestamp: timestamp,
          ip: this.generateIP(),
          workload: 'SharePoint',
          result: 'Success'
        };
        
        // Add operation-specific details
        if (operation === 'FileShared') {
          event.details = `Shared with ${users[Math.floor(Math.random() * users.length)]}`;
        } else if (operation === 'FileModified') {
          event.details = `Modified ${Math.floor(Math.random() * 50) + 1} lines`;
        } else if (operation === 'FileDownloaded') {
          event.details = `Downloaded via ${Math.random() > 0.5 ? 'Browser' : 'OneDrive Sync'}`;
        } else if (operation === 'FileRestored') {
          event.details = 'Restored from recycle bin';
        }
        
        events.push(event);
      }
      
      // Sort by timestamp descending (most recent first)
      return [];
    },
    
    weightedRandom(items) {
      const totalWeight = items.reduce((sum, item) => sum + item.weight, 0);
      let random = Math.random() * totalWeight;
      
      for (const item of items) {
        random -= item.weight;
        if (random <= 0) {
          return item.op;
        }
      }
      
      return items[0].op;
    },
    
    generateIP() {
      // Generate realistic IP addresses
      const internalIPs = [
        '10.0.1.',
        '10.0.2.',
        '192.168.1.',
        '172.16.0.'
      ];
      
      const externalIPs = [
        '52.108.', // Microsoft
        '40.97.',  // Microsoft
        '13.107.', // Microsoft
        '204.79.'  // Microsoft
      ];
      
      const isInternal = Math.random() > 0.3; // 70% internal
      const base = isInternal ? 
        internalIPs[Math.floor(Math.random() * internalIPs.length)] :
        externalIPs[Math.floor(Math.random() * externalIPs.length)];
      
      return base + Math.floor(Math.random() * 254 + 1) + '.' + Math.floor(Math.random() * 254 + 1);
    },
    
    async applyFilters() {
      // If no filters are active, clear filtered data
      if (!this.hasActiveFilters) {
        this.filteredData = null;
        return;
      }
      
      // Start loading
      this.loading = true;
      
      try {
        // Build query parameters
        const params = new URLSearchParams();
        
        if (this.filterPerson) {
          params.append('person', this.filterPerson);
        }
        
        if (this.filterSite) {
          params.append('site_id', this.filterSite);
        }
        
        if (this.filterPermissionType && this.filterPermissionType !== 'all') {
          params.append('permission_type', this.filterPermissionType);
        }
        
        // Call backend API to get filtered results
        const response = await apiClient.get(
          `/sharepoint-simple/search?${params.toString()}`
        );
        
        if (response.data) {
          this.filteredData = response.data;
          
          // If filtering by site, automatically select that site
          if (this.filterSite && !this.selectedSite) {
            const site = this.sites.find(s => s.id === this.filterSite);
            if (site) {
              await this.selectSite(site);
            }
          }
        }
      } catch (error) {
        console.error('Error applying filters:', error);
        this.$toast?.error('Failed to apply filters');
      } finally {
        this.loading = false;
      }
    },
    
    clearFilters() {
      this.filterPerson = '';
      this.filterSite = null;
      this.filterPermissionType = null;
      this.filteredData = null;
    },
    
    async exportPdfReport() {
      this.exportingPdf = true;
      try {
        // Build query parameters
        const params = new URLSearchParams();
        
        if (this.filterSite) {
          params.append('site_id', this.filterSite);
        }
        if (this.filterPerson) {
          params.append('person_email', this.filterPerson);
        }
        if (this.filterPermissionType) {
          // Map UI filter values to API values
          if (this.filterPermissionType === 'unique') {
            params.append('permission_type', 'unique');
          } else if (this.filterPermissionType === 'inherited') {
            params.append('permission_type', 'inherited');
          }
        }
        
        // Add charts option
        params.append('include_charts', 'true');
        
        // Make API request
        const response = await apiClient.get(
          `/sharepoint-simple/permissions-report/pdf?${params.toString()}`,
          {
            responseType: 'blob',
            timeout: 60000 // 60 second timeout for large reports
          }
        );
        
        // Create download link
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        
        // Generate filename with timestamp
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
        link.setAttribute('download', `SharePoint_Permissions_Report_${timestamp}.pdf`);
        
        // Trigger download
        document.body.appendChild(link);
        link.click();
        
        // Cleanup
        link.remove();
        window.URL.revokeObjectURL(url);
        
        // Show success message
        this.$root.$emit('show-snackbar', {
          message: 'PDF report generated successfully',
          color: 'success'
        });
        
      } catch (error) {
        console.error('Error generating PDF report:', error);
        
        let errorMessage = 'Failed to generate PDF report';
        if (error.response?.status === 404) {
          errorMessage = 'No permissions data found for the selected filters';
        } else if (error.response?.data?.detail) {
          errorMessage = error.response.data.detail;
        } else if (error.code === 'ECONNABORTED') {
          errorMessage = 'Report generation timed out. Try with fewer filters.';
        }
        
        this.$root.$emit('show-snackbar', {
          message: errorMessage,
          color: 'error'
        });
      } finally {
        this.exportingPdf = false;
      }
    },
    
    async navigateToItem(item) {
      // Clear filters first
      this.clearFilters();
      
      // Find and select the site
      const site = this.sites.find(s => s.id === item.site_id);
      if (site) {
        await this.selectSite(site);
        
        // TODO: Navigate to the specific item within the site
        // This would require loading the site structure and finding the item
        console.log('Navigate to item:', item);
      }
    },
    
    async loadItemPermissions() {
      if (!this.detailItem || !this.detailItem.id || this.detailItem.type === 'site') {
        return;
      }
      
      this.loadingPermissions = true;
      try {
        console.log('Loading permissions for item:', this.detailItem.id, this.detailItem.name);
        const response = await apiClient.get(`/sharepoint-simple/item/${this.detailItem.id}/permissions`);
        console.log('Permissions response:', response.data);
        
        // Check if we actually got permissions or empty arrays
        const hasData = response.data && (
          (response.data.users && response.data.users.length > 0) ||
          (response.data.groups && response.data.groups.length > 0) ||
          (response.data.shared_links && response.data.shared_links.length > 0)
        );
        
        if (hasData) {
          this.itemPermissions = response.data;
          console.log('Loaded permissions - Users:', response.data.users?.length, 
                      'Groups:', response.data.groups?.length,
                      'Links:', response.data.shared_links?.length);
          
          // Log first group if any to debug name issue
          if (response.data.groups && response.data.groups.length > 0) {
            console.log('First group data:', response.data.groups[0]);
          }
        } else {
          console.log('No permissions data returned for item');
          // Try to generate mock data from statistics if available
          if (this.detailItem.statistics && this.detailItem.statistics.principal_count > 0) {
            console.log('Using statistics to show permission counts');
            this.itemPermissions = {
              users: [],
              groups: this.detailItem.statistics.group_count > 0 ? 
                [{principal_name: 'SharePoint Group', 
                  principal_type: 'group',
                  permission_level: 'Read',
                  permission_type: 'inherited'}] : [],
              shared_links: []
            };
          } else {
            this.itemPermissions = null;
          }
        }
        
        this.itemPermissionsLoaded = true;
      } catch (error) {
        console.error('Failed to load item permissions:', error);
        this.itemPermissions = null;
        this.itemPermissionsLoaded = true;
      } finally {
        this.loadingPermissions = false;
      }
    },
    
    getTotalPermissionsCount() {
      if (!this.itemPermissions) return 0;
      return (this.itemPermissions.users || []).length + 
             (this.itemPermissions.groups || []).length + 
             (this.itemPermissions.shared_links || []).length;
    },
    
    getInitials(name) {
      if (!name) return '?';
      const parts = name.split(/[\s@._-]+/).filter(p => p.length > 0);
      if (parts.length >= 2) {
        return (parts[0][0] + parts[1][0]).toUpperCase();
      }
      return name.substring(0, 2).toUpperCase();
    },
    
    getAvatarColor(name) {
      // Generate consistent color based on name
      const colors = ['red', 'pink', 'purple', 'deep-purple', 'indigo', 'blue', 
                     'light-blue', 'cyan', 'teal', 'green', 'light-green', 
                     'lime', 'amber', 'orange', 'deep-orange'];
      let hash = 0;
      for (let i = 0; i < name.length; i++) {
        hash = name.charCodeAt(i) + ((hash << 5) - hash);
      }
      return colors[Math.abs(hash) % colors.length];
    },
    
    getPermissionColor(level) {
      const lowerLevel = level.toLowerCase();
      if (lowerLevel.includes('full') || lowerLevel.includes('owner')) return 'red';
      if (lowerLevel.includes('edit') || lowerLevel.includes('contribute')) return 'orange';
      if (lowerLevel.includes('read') || lowerLevel.includes('view')) return 'green';
      return 'grey';
    },
    
    formatPermissionLevel(level) {
      // Clean up permission level text
      if (!level) return 'Unknown';
      // Remove "(Shared via ... link)" suffix if present
      const cleanLevel = level.replace(/\s*\(Shared via.*\)$/, '');
      // Capitalize first letter of each word
      return cleanLevel.split(' ')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
        .join(' ');
    },
    
    formatPrincipalName(name, email) {
      // Clean up principal names that look like they contain the resource name
      if (!name || name === 'Unknown' || name === '') {
        return email || 'Unknown User';
      }
      
      // Check if this is the same as the current item name (data corruption issue)
      if (this.detailItem && (name === this.detailItem.name || name === this.detailItem.name + ' Permissions')) {
        console.warn('Principal name matches resource name, likely data corruption:', name);
        return email || 'SharePoint Group (Name Unknown)';
      }
      
      // Check if the name looks like it contains "Permissions" suffix
      if (name.includes(' Permissions')) {
        // This might be a data issue - try to extract the real group name
        const parts = name.split(' Permissions');
        if (parts.length > 1 && parts[0]) {
          // If the first part looks like a filename or matches current item, it's probably wrong
          if (parts[0].includes('.') || parts[0].includes('-') || 
              (this.detailItem && parts[0] === this.detailItem.name)) {
            return email || 'SharePoint Group';
          }
          return parts[0];
        }
      }
      
      // If name looks like an email, just return it
      if (name.includes('@')) {
        return name;
      }
      
      // If we have both name and email, and they're different
      if (email && email !== name && !name.includes(email)) {
        return name;
      }
      
      return name;
    },
    
    async startPermissionsCollection() {
      this.collectingPermissions = true;
      this.permissionsProgress = 0;
      this.permissionsStatusMessage = 'Starting permissions collection...';
      this.permissionsStats = null;
      
      try {
        // Start the collection
        await apiClient.post('/sharepoint-simple/collect-permissions');
        
        // Poll for progress
        const pollInterval = setInterval(async () => {
          try {
            const statusResponse = await apiClient.get('/sharepoint-simple/permissions-status');
            const status = statusResponse.data;
            
            if (status.status === 'running') {
              // Update progress
              const progress = (status.processed / status.total) * 100;
              this.permissionsProgress = Math.round(progress);
              this.permissionsStatusMessage = status.message || 'Processing...';
              
              // Update stats
              this.permissionsStats = {
                total_resources: status.total,
                processed: status.processed,
                unique_permissions_found: status.unique_found,
                errors: status.errors
              };
            } else if (status.status === 'completed') {
              // Collection completed
              clearInterval(pollInterval);
              this.permissionsProgress = 100;
              this.permissionsStatusMessage = status.message || 'Permissions collection completed!';
              
              // Reload the current view to show updated permissions
              if (this.selectedSite) {
                // Clear cache and reload
                if (this.allSiteData[this.selectedSite.id]) {
                  delete this.allSiteData[this.selectedSite.id];
                }
                await this.selectSite(this.selectedSite);
              }
              
              // If filters were active, reapply them
              if (this.hasActiveFilters) {
                await this.applyFilters();
              }
              
              this.collectingPermissions = false;
            } else if (status.status === 'error' || status.status === 'no_collection') {
              clearInterval(pollInterval);
              this.collectingPermissions = false;
            }
          } catch (error) {
            console.error('Error polling status:', error);
          }
        }, 2000); // Poll every 2 seconds
        
        // Set a timeout to stop polling after 1 hour
        setTimeout(() => {
          clearInterval(pollInterval);
          if (this.collectingPermissions) {
            this.collectingPermissions = false;
            this.permissionsStatusMessage = 'Collection timed out';
          }
        }, 3600000); // 1 hour
        
      } catch (error) {
        console.error('Permissions collection error:', error);
        this.permissionsStatusMessage = `Error: ${error.message}`;
        this.permissionsProgress = 0;
        this.collectingPermissions = false;
      }
    },
    
    formatEventTime(timestamp) {
      const now = new Date();
      const diff = now - timestamp;
      const hours = Math.floor(diff / (1000 * 60 * 60));
      const days = Math.floor(hours / 24);
      
      if (hours < 1) {
        return 'Just now';
      } else if (hours < 24) {
        return `${hours}h ago`;
      } else if (days < 7) {
        return `${days}d ago`;
      } else {
        return timestamp.toLocaleDateString();
      }
    },
    
    getEventColor(operation) {
      const colorMap = {
        'FileAccessed': 'blue',
        'FileViewed': 'blue',
        'FileModified': 'orange',
        'FileDownloaded': 'green',
        'FileShared': 'purple',
        'FileDeleted': 'red',
        'FileRestored': 'teal',
        'FileCheckedOut': 'amber',
        'FileCheckedIn': 'lime'
      };
      
      return colorMap[operation] || 'grey';
    },
    
    // Dynamic column methods for deep navigation
    selectDynamicItem(item, columnIndex) {
      // Update selected path - keep items up to and including this column
      this.selectedPath = this.selectedPath.slice(0, 1); // Keep first item from topLevelFolders
      
      // Add items from dynamic columns up to this point
      for (let i = 0; i <= columnIndex; i++) {
        if (i === columnIndex) {
          this.selectedPath.push(item);
        } else if (this.dynamicColumns[i]) {
          // Find the selected item in this column
          const selected = this.dynamicColumns[i].items.find(it => 
            this.selectedPath.some(p => p.id === it.id)
          );
          if (selected) {
            this.selectedPath.push(selected);
          }
        }
      }
      
      // Reset empty folder tracking
      this.selectedEmptyFolder = null;
      
      // If it's a folder, check if it has contents
      if (item.type === 'folder') {
        if (item.childCount > 0) {
          this.addDynamicColumn(item, columnIndex + 1);
        } else {
          // Track empty folder and remove columns after this one
          this.selectedEmptyFolder = item;
          this.dynamicColumns = this.dynamicColumns.slice(0, columnIndex + 1);
        }
      } else {
        // It's a file, remove any columns after this one
        this.dynamicColumns = this.dynamicColumns.slice(0, columnIndex + 1);
      }
      
      // Update breadcrumb
      this.updateBreadcrumbFromPath();
    },
    
    isItemSelected(item, columnIndex) {
      // Check if this item is in the selected path at the appropriate level
      const pathIndex = columnIndex + 1; // +1 because path includes the top-level item
      return this.selectedPath[pathIndex]?.id === item.id;
    },
    
    updateBreadcrumbFromPath() {
      this.breadcrumbPath = [
        { text: this.selectedSite.name, value: this.selectedSite, type: 'site' }
      ];
      
      this.selectedPath.forEach(item => {
        this.breadcrumbPath.push({
          text: item.name,
          value: item,
          type: item.type
        });
      });
    },
    
    // Column resize methods
    startResize(columnId, event) {
      this.resizing = columnId;
      this.startX = event.clientX;
      this.startWidth = this.columnWidths[columnId] || 300;
      event.preventDefault();
      event.stopPropagation();
      document.body.style.cursor = 'col-resize';
      
      // Add a class to the body to prevent text selection while dragging
      document.body.classList.add('resizing');
    },
    
    handleResize(event) {
      if (!this.resizing) return;
      
      const diff = event.clientX - this.startX;
      const newWidth = Math.max(200, Math.min(800, this.startWidth + diff));
      
      // Update width reactively
      this.columnWidths = {
        ...this.columnWidths,
        [this.resizing]: newWidth
      };
    },
    
    stopResize() {
      if (this.resizing) {
        this.resizing = null;
        document.body.style.cursor = '';
        document.body.classList.remove('resizing');
        
        // Save column widths to localStorage
        localStorage.setItem('sharepoint-column-widths', JSON.stringify(this.columnWidths));
      }
    },

    // Group permissions modal methods
    selectGroup(group) {
      this.selectedGroup = group;
      this.groupMembers = null;
      this.loadGroupMembers();
    },

    async loadGroupMembers(useCache = true) {
      if (!this.selectedGroup) return;
      
      this.loadingGroupMembers = true;
      try {
        console.log('Loading members for group:', this.selectedGroup.principal_id, this.selectedGroup.principal_name, 'useCache:', useCache);
        const response = await apiClient.get(`/sharepoint-simple/group/${this.selectedGroup.principal_id}/members`, {
          params: { use_cache: useCache }
        });
        console.log('Group members response:', response.data);
        this.groupMembers = response.data;
        
        // If syncing, poll for updates
        if (response.data.syncing) {
          setTimeout(() => {
            this.loadGroupMembers(true);
          }, 3000);
        }
      } catch (error) {
        console.error('Failed to load group members:', error);
        this.groupMembers = null;
      } finally {
        this.loadingGroupMembers = false;
      }
    },

    async refreshGroupMembers(useCache = true) {
      await this.loadGroupMembers(useCache);
    },
    
    async syncGroupMembers() {
      if (!this.selectedGroup) return;
      
      this.loadingGroupMembers = true;
      try {
        // Trigger sync from Entra ID
        const syncResponse = await apiClient.post(`/sharepoint-simple/group/${this.selectedGroup.principal_id}/sync`);
        console.log('Sync response:', syncResponse.data);
        
        if (syncResponse.data.success === false) {
          // Show error message
          this.groupMembers = {
            ...this.groupMembers,
            no_data: true,
            message: syncResponse.data.message || syncResponse.data.error,
            permission_required: syncResponse.data.permission_required
          };
          this.loadingGroupMembers = false;
          return;
        }
        
        // Wait a moment then refresh to get the synced data
        setTimeout(async () => {
          await this.loadGroupMembers(true);
        }, 2000);
        
      } catch (error) {
        console.error('Failed to sync group members:', error);
        // Still try to load what we have
        await this.loadGroupMembers(true);
      }
    },
    
    formatLastSync(timestamp) {
      if (!timestamp) return '';
      const date = new Date(timestamp);
      const now = new Date();
      const diff = now - date;
      
      if (diff < 60000) return 'just now';
      if (diff < 3600000) return `${Math.floor(diff / 60000)} minutes ago`;
      if (diff < 86400000) return `${Math.floor(diff / 3600000)} hours ago`;
      return date.toLocaleDateString();
    },

    openGroupPermissionsModal() {
      console.log('Opening group permissions modal...');
      console.log('Current itemPermissions:', this.itemPermissions);
      console.log('itemPermissionsLoaded:', this.itemPermissionsLoaded);
      
      this.showGroupPermissionsModal = true;
      console.log('showGroupPermissionsModal set to:', this.showGroupPermissionsModal);
      
      // If permissions haven't been loaded yet, load them
      if (!this.itemPermissionsLoaded) {
        console.log('Loading item permissions...');
        this.loadItemPermissions();
      }
    },

    closeGroupPermissionsModal() {
      this.showGroupPermissionsModal = false;
      this.selectedGroup = null;
      this.groupMembers = null;
    },

    openGroupMembersModal(group) {
      // Open the modal and pre-select the group
      this.showGroupPermissionsModal = true;
      this.selectedGroup = group;
      // Load members for the selected group
      this.loadGroupMembers(group.principal_id);
    },

    getGroupsFromPermissions() {
      if (!this.itemPermissions) {
        return [];
      }
      // Return the groups array from the itemPermissions
      // The API now properly classifies groups in the 'groups' array
      return this.itemPermissions.groups || [];
    },
    
    filteredGroups() {
      let groups = this.getGroupsFromPermissions();
      
      // Apply search filter
      if (this.groupSearchQuery) {
        const query = this.groupSearchQuery.toLowerCase();
        groups = groups.filter(group => 
          (group.principal_name && group.principal_name.toLowerCase().includes(query)) ||
          (group.permissions && group.permissions.some(p => p.toLowerCase().includes(query)))
        );
      }
      
      // Apply permission filter
      if (this.groupPermissionFilter) {
        groups = groups.filter(group => 
          group.permissions && group.permissions.some(p => 
            p.toLowerCase().includes(this.groupPermissionFilter.toLowerCase())
          )
        );
      }
      
      return groups;
    },
    
    getUniquePermissionLevels() {
      const groups = this.getGroupsFromPermissions();
      const permissions = new Set();
      
      groups.forEach(group => {
        if (group.permissions) {
          group.permissions.forEach(perm => {
            // Extract main permission type (e.g., 'Read', 'Edit', 'Full Control')
            const mainPerm = perm.split(',')[0].trim();
            permissions.add(mainPerm);
          });
        }
      });
      
      return Array.from(permissions).sort();
    },
    
    togglePermissionFilter(permission) {
      if (this.groupPermissionFilter === permission) {
        this.groupPermissionFilter = null;
      } else {
        this.groupPermissionFilter = permission;
      }
    },
    
    getPermissionIcon(level) {
      // Get icon for permission filter chips
      const permission = (level || '').toLowerCase();
      if (permission.includes('full') || permission.includes('owner')) return 'mdi-shield-crown';
      if (permission.includes('edit') || permission.includes('contribute')) return 'mdi-pencil';
      if (permission.includes('read') || permission.includes('view')) return 'mdi-eye';
      if (permission.includes('limited')) return 'mdi-eye-off';
      return 'mdi-shield-outline';
    },

    getGroupIcon(permissionLevel) {
      const level = (permissionLevel || '').toLowerCase();
      if (level.includes('owner') || level.includes('full')) return 'mdi-shield-crown';
      if (level.includes('write') || level.includes('edit')) return 'mdi-shield-edit';
      if (level.includes('read') || level.includes('view')) return 'mdi-shield-eye';
      return 'mdi-shield-account';
    },

    getGroupIconColor(permissionLevel) {
      const level = (permissionLevel || '').toLowerCase();
      if (level.includes('owner') || level.includes('full')) return 'deep-purple';
      if (level.includes('write') || level.includes('edit')) return 'blue';
      if (level.includes('read') || level.includes('view')) return 'teal';
      return 'grey';
    },

    getPermissionIcon(permissionLevel) {
      const level = (permissionLevel || '').toLowerCase();
      if (level.includes('owner') || level.includes('full')) return 'mdi-crown';
      if (level.includes('write') || level.includes('edit')) return 'mdi-pencil';
      if (level.includes('read') || level.includes('view')) return 'mdi-eye';
      return 'mdi-lock';
    },

    getMemberAvatarColor(member) {
      const colors = ['deep-purple', 'indigo', 'blue', 'teal', 'green', 'orange', 'deep-orange'];
      const index = (member.id || member.displayName || '').charCodeAt(0) % colors.length;
      return colors[index];
    },

    getMemberTypeColor(type) {
      switch(type) {
        case 'user': return 'green';
        case 'group': return 'blue';
        case 'application': return 'orange';
        default: return 'grey';
      }
    },

    getMemberTypeIcon(type) {
      switch(type) {
        case 'user': return 'mdi-account';
        case 'group': return 'mdi-account-multiple';
        case 'application': return 'mdi-application';
        default: return 'mdi-help-circle';
      }
    }
  },
  
  created() {
    // Load saved column widths
    const saved = localStorage.getItem('sharepoint-column-widths');
    if (saved) {
      try {
        this.columnWidths = JSON.parse(saved);
      } catch (e) {
        console.error('Failed to load saved column widths:', e);
      }
    }
  }
};
</script>

<style scoped>
.sharepoint-columns-container {
  height: calc(100vh - 64px); /* Subtract app bar height */
  display: flex;
  flex-direction: column;
  width: 100%;
  position: relative;
  margin: 0;
  padding: 0;
}

.filter-bar {
  background: #f8f8f8;
  border-bottom: 1px solid #e0e0e0;
  position: relative;
  z-index: 5;
}

.filtered-results-container {
  flex: 1;
  overflow-y: auto;
  background: white;
}

.breadcrumb-container {
  background: #f5f5f5;
  border-bottom: 1px solid #e0e0e0;
  padding: 0 16px;
  min-height: 40px;
  display: flex;
  align-items: center;
  overflow-x: auto;
  white-space: nowrap;
}

.columns-wrapper {
  display: flex;
  flex: 1;
  overflow: hidden;
  background: #fafafa;
  width: 100%;
  position: relative;
}

.columns-container {
  display: flex;
  flex: 1;
  overflow-x: auto;
  overflow-y: hidden;
  align-items: stretch;
}

.column {
  background: white;
  border-right: 1px solid #e0e0e0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  flex-shrink: 0;
  position: relative;
}

.column-sites {
  flex-shrink: 0;
  border-right: 2px solid #e0e0e0;
}

.column.details-column {
  flex-shrink: 0;
  width: 500px;
  border-left: 2px solid #e0e0e0;
}

.column-header {
  padding: 12px 16px;
  background: #f5f5f5;
  border-bottom: 1px solid #e0e0e0;
  font-weight: 500;
  font-size: 14px;
  display: flex;
  align-items: center;
}

.column-list {
  flex: 1;
  overflow-y: auto;
  padding: 0;
}

.details-content {
  flex: 1;
  overflow-y: auto;
}

.detail-row {
  display: flex;
  margin-bottom: 12px;
  align-items: flex-start;
}

.detail-label {
  font-weight: 500;
  min-width: 140px;
  color: #666;
  font-size: 14px;
}

.detail-value {
  flex: 1;
  font-size: 14px;
}

.v-list-item {
  min-height: 36px !important;
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.v-list-item--active {
  background-color: #1976d2 !important;
  color: white !important;
}

.v-list-item--active .text-grey {
  color: rgba(255, 255, 255, 0.7) !important;
}

.v-list-item--active .v-icon {
  color: white !important;
}

:deep(.v-list-item__prepend) {
  margin-right: 12px !important;
}

.text-truncate {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: block;
}

.column-resizer {
  position: absolute;
  top: 0;
  right: -4px;
  width: 8px;
  height: 100%;
  cursor: col-resize;
  background: transparent;
  z-index: 10;
  transition: background-color 0.2s;
}

.column-resizer:hover {
  background-color: #1976d2;
}

.column-resizer:active {
  background-color: #1565c0;
}

/* Prevent text selection while resizing */
:global(body.resizing) {
  user-select: none;
  -webkit-user-select: none;
  -moz-user-select: none;
  -ms-user-select: none;
}

/* Permissions styling */
.permission-summary {
  border: 1px solid #e0e0e0;
}

.permission-section-header {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
  color: #666;
}

.permission-item {
  min-height: 60px;
  padding: 8px 0;
  border-bottom: 1px solid #f5f5f5;
}

.permission-item .v-list-item__subtitle {
  margin-top: 4px;
  line-height: 1.3;
}

.permission-item:last-child {
  border-bottom: none;
}

.permission-item:hover {
  background-color: #fafafa;
}

.permissions-list {
  max-height: 500px;
  overflow-y: auto;
}

.permissions-list::-webkit-scrollbar {
  width: 6px;
}

.permissions-list::-webkit-scrollbar-track {
  background: #f1f1f1;
}

.permissions-list::-webkit-scrollbar-thumb {
  background: #888;
  border-radius: 3px;
}

.permissions-list::-webkit-scrollbar-thumb:hover {
  background: #555;
}

/* Clickable group hover effect */
.clickable-group:hover {
  background-color: rgba(33, 150, 243, 0.08);
}

.clickable-group {
  transition: background-color 0.2s ease;
}

/* Beautiful Modal Styles */
.group-modal-card {
  overflow: hidden;
  border-radius: 12px !important;
}

.modal-header-gradient {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 24px;
}

.groups-container {
  max-height: 70vh;
  overflow-y: auto;
}

.groups-grid {
  background: #f5f5f5;
}

.group-card {
  border-radius: 12px !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
  overflow: hidden;
}

.group-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.15) !important;
}

.group-card-selected {
  border: 2px solid #667eea;
  background: linear-gradient(to bottom, rgba(102, 126, 234, 0.05), rgba(255, 255, 255, 0));
}

.group-card-gradient {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
  display: flex;
  justify-content: center;
  align-items: center;
}

.members-section {
  background: white;
  border-top: 1px solid #e0e0e0;
}

.members-header {
  background: linear-gradient(to right, #f5f5f5, #fafafa);
  border-bottom: 1px solid #e0e0e0;
}

.member-card {
  border-radius: 12px !important;
  transition: all 0.2s ease;
  overflow: hidden;
}

.member-card:hover {
  transform: scale(1.02);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1) !important;
}

.member-card-header {
  background: linear-gradient(135deg, #f5f5f5 0%, #e0e0e0 100%);
  padding: 16px;
  display: flex;
  justify-content: center;
  align-items: center;
}

/* Loading dots animation */
.loading-dots {
  display: inline-flex;
  gap: 8px;
}

.loading-dots span {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #667eea;
  animation: pulse 1.4s infinite ease-in-out both;
}

.loading-dots span:nth-child(1) {
  animation-delay: -0.32s;
}

.loading-dots span:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes pulse {
  0%, 80%, 100% {
    transform: scale(0);
    opacity: 0.5;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

/* Smooth transitions */
.v-expand-transition-enter-active,
.v-expand-transition-leave-active {
  transition: all 0.3s ease;
}

/* Compact styles for many groups */
.compact-group-card {
  max-height: 150px;
  overflow: hidden;
}

.compact-group-card .v-card-text {
  padding: 8px;
}

.compact-group-card .group-card-gradient-compact {
  padding: 12px 0;
  text-align: center;
}

/* List view styles */
.group-list-item {
  transition: all 0.2s ease;
  cursor: pointer;
}

.group-list-item:hover {
  background: rgba(33, 150, 243, 0.05);
}

.selected-list-item {
  background: rgba(33, 150, 243, 0.1);
  border-left: 3px solid #2196F3;
}

/* Search and filter section */
.search-section {
  background: #f5f5f5;
  border-bottom: 1px solid #e0e0e0;
}

/* Responsive grid adjustments */
@media (max-width: 960px) {
  .groups-grid .v-col {
    min-width: 200px;
  }
}

/* Filter chips */
.cursor-pointer {
  cursor: pointer;
}

.groups-list-view {
  max-height: 400px;
  overflow-y: auto;
}

/* View toggle buttons */
.v-btn-toggle {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 4px;
}

.v-btn-toggle .v-btn {
  color: white !important;
}

.v-btn-toggle .v-btn--active {
  background: rgba(255, 255, 255, 0.3);
}

/* Empty folder message */
.empty-folder-message {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 300px;
  padding: 40px;
}

.empty-folder-content {
  text-align: center;
  max-width: 400px;
}

.empty-folder-content .v-icon {
  opacity: 0.3;
}
</style>