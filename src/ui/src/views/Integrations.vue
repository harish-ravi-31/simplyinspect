<template>
  <v-container fluid class="fill-height">
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title>
            <v-icon left color="primary" class="mr-2">mdi-source-branch</v-icon>
            Integrations
          </v-card-title>
          
          
          <v-tabs v-model="activeTab" background-color="primary" dark show-arrows>
            <v-tab :key="0">
              <v-icon left>mdi-email-plus</v-icon>
              EML Import
            </v-tab>
            <v-tab :key="1">
              <v-icon left>mdi-file-document-multiple</v-icon>
              Document Import
            </v-tab>
            <v-tab :key="2">
              <v-icon left>mdi-api</v-icon>
              API Settings
            </v-tab>
            <v-tab :key="3">
              <v-icon left>mdi-export</v-icon>
              Exports
            </v-tab>
            <v-tab :key="4">
              <v-icon left>mdi-shield-account</v-icon>
              External Audit Logs
            </v-tab>
          </v-tabs>
          
          <!-- Tab Content with Conditional Rendering -->
          <div class="mt-4">
            <!-- EML Import Tab Content -->
            <div v-if="activeTab === 0">
              <v-card flat>
                <v-card-text>
                  <v-row>
                    <v-col cols="12" md="6">
                      <v-card outlined>
                        <v-card-title class="text-subtitle-1">
                          <v-icon left color="amber darken-2">mdi-email-multiple</v-icon>
                          Import EML Files
                        </v-card-title>
                        <v-card-text>
                          <p>
                            Upload EML files to be processed through the email pipeline. Files will be imported 
                            with the same verification, legal hold detection, and retention policies as emails received via SMTP.
                          </p>
                          <v-file-input
                            v-model="selectedFiles"
                            :loading="isUploading"
                            accept=".eml"
                            chips
                            multiple
                            show-size
                            counter
                            label="Select EML files"
                            prepend-icon="mdi-email-plus"
                            append-outer-icon="mdi-cloud-upload"
                            @click:append-outer="uploadFiles"
                            hint="Select one or more EML files to import"
                            persistent-hint
                          ></v-file-input>
                        </v-card-text>
                        <v-card-actions>
                          <v-btn
                            color="primary"
                            :disabled="!selectedFiles || selectedFiles.length === 0"
                            :loading="isUploading"
                            @click="uploadFiles"
                          >
                            <v-icon left>mdi-upload</v-icon>
                            Upload Files
                          </v-btn>
                          <v-spacer></v-spacer>
                          <v-btn text @click="selectedFiles = []">
                            Clear
                          </v-btn>
                        </v-card-actions>
                      </v-card>
                    </v-col>
                    <v-col cols="12" md="6">
                      <v-card outlined>
                        <v-card-title class="text-subtitle-1">
                          <v-icon left color="blue darken-2">mdi-information</v-icon>
                          Import Information
                        </v-card-title>
                        <v-card-text>
                          <v-alert type="info" outlined>
                            <strong>Supported Features:</strong>
                            <ul class="mt-2">
                              <li>Email metadata extraction</li>
                              <li>Attachment processing</li>
                              <li>Legal hold detection</li>
                              <li>Retention policy application</li>
                              <li>Full-text indexing</li>
                            </ul>
                          </v-alert>
                          <v-alert type="warning" outlined class="mt-3">
                            <strong>File Requirements:</strong>
                            <ul class="mt-2">
                              <li>Files must have .eml extension</li>
                              <li>Maximum file size: 25MB per file</li>
                              <li>Maximum batch size: 100 files</li>
                              <li>Valid RFC 2822 format required</li>
                            </ul>
                          </v-alert>
                        </v-card-text>
                      </v-card>
                    </v-col>
                  </v-row>
                </v-card-text>
              </v-card>
            </div>

            <!-- Document Import Tab Content -->
            <div v-if="activeTab === 1">
              <v-card flat>
                <v-card-text>
                  <v-row>
                    <v-col cols="12" md="6">
                      <v-card outlined>
                        <v-card-title class="text-subtitle-1">
                          <v-icon left color="green darken-2">mdi-file-document-multiple</v-icon>
                          Import Documents
                        </v-card-title>
                        <v-card-text>
                          <p>
                            Upload documents to be processed and archived. Supported formats include PDF, Word, Excel, PowerPoint, images, and more.
                            Documents will be indexed and made searchable with retention policies applied.
                          </p>
                          <v-file-input
                            v-model="selectedDocuments"
                            :loading="isUploadingDocs"
                            accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.jpg,.jpeg,.png,.gif"
                            chips
                            multiple
                            show-size
                            counter
                            label="Select documents"
                            prepend-icon="mdi-file-document-plus"
                            append-outer-icon="mdi-cloud-upload"
                            @click:append-outer="uploadDocuments"
                            hint="Select one or more documents to import"
                            persistent-hint
                          ></v-file-input>
                        </v-card-text>
                        <v-card-actions>
                          <v-btn
                            color="primary"
                            :disabled="!selectedDocuments || selectedDocuments.length === 0"
                            :loading="isUploadingDocs"
                            @click="uploadDocuments"
                          >
                            <v-icon left>mdi-upload</v-icon>
                            Upload Documents
                          </v-btn>
                          <v-spacer></v-spacer>
                          <v-btn text @click="selectedDocuments = []">
                            Clear
                          </v-btn>
                        </v-card-actions>
                      </v-card>
                    </v-col>
                    <v-col cols="12" md="6">
                      <v-card outlined>
                        <v-card-title class="text-subtitle-1">
                          <v-icon left color="blue darken-2">mdi-information</v-icon>
                          Document Information
                        </v-card-title>
                        <v-card-text>
                          <v-alert type="info" outlined>
                            <strong>Supported Formats:</strong>
                            <ul class="mt-2">
                              <li>PDF documents</li>
                              <li>Microsoft Office (Word, Excel, PowerPoint)</li>
                              <li>Text files</li>
                              <li>Images (JPG, PNG, GIF)</li>
                              <li>Archives (ZIP, RAR)</li>
                            </ul>
                          </v-alert>
                          <v-alert type="warning" outlined class="mt-3">
                            <strong>File Requirements:</strong>
                            <ul class="mt-2">
                              <li>Maximum file size: 100MB per file</li>
                              <li>Maximum batch size: 50 files</li>
                              <li>Files must not be password protected</li>
                              <li>OCR will be applied to image files</li>
                            </ul>
                          </v-alert>
                        </v-card-text>
                      </v-card>
                    </v-col>
                  </v-row>
                  
                  <!-- Folder Import Section -->
                  <v-row class="mt-4">
                    <v-col cols="12">
                      <v-card outlined>
                        <v-card-title class="text-subtitle-1">
                          <v-icon left color="orange darken-2">mdi-folder-multiple</v-icon>
                          Import Document Folders
                        </v-card-title>
                        <v-card-text>
                          <p>
                            Import entire folders containing documents. The system will recursively scan all subfolders
                            and process supported document types while maintaining the folder structure.
                          </p>
                          <v-text-field
                            v-model="selectedFolderPath"
                            label="Folder Path"
                            outlined
                            prepend-icon="mdi-folder-open"
                            append-outer-icon="mdi-folder-search"
                            @click:append-outer="browseFolders"
                            hint="Enter or browse for a folder path to import"
                            persistent-hint
                            readonly
                          ></v-text-field>
                          
                          <!-- Folder Import Options -->
                          <v-row class="mt-3">
                            <v-col cols="12" md="6">
                              <v-checkbox
                                v-model="folderImportOptions.includeSubfolders"
                                label="Include subfolders"
                                hide-details
                              ></v-checkbox>
                              <v-checkbox
                                v-model="folderImportOptions.preserveStructure"
                                label="Preserve folder structure"
                                hide-details
                              ></v-checkbox>
                              <v-checkbox
                                v-model="folderImportOptions.skipDuplicates"
                                label="Skip duplicate files"
                                hide-details
                              ></v-checkbox>
                            </v-col>
                            <v-col cols="12" md="6">
                              <v-select
                                v-model="folderImportOptions.fileFilter"
                                :items="documentFilters"
                                label="File Type Filter"
                                outlined
                                dense
                                hint="Filter files by type during import"
                                persistent-hint
                              ></v-select>
                            </v-col>
                          </v-row>
                        </v-card-text>
                        <v-card-actions>
                          <v-btn
                            color="primary"
                            :disabled="!selectedFolderPath"
                            :loading="isImportingFolder"
                            @click="importFolder"
                          >
                            <v-icon left>mdi-folder-upload</v-icon>
                            Import Folder
                          </v-btn>
                          <v-btn
                            color="secondary"
                            :disabled="!selectedFolderPath"
                            @click="scanFolder"
                          >
                            <v-icon left>mdi-folder-search</v-icon>
                            Scan Folder
                          </v-btn>
                          <v-spacer></v-spacer>
                          <v-btn text @click="selectedFolderPath = ''">
                            Clear
                          </v-btn>
                        </v-card-actions>
                      </v-card>
                    </v-col>
                  </v-row>
                  
                  <!-- Folder Scan Results -->
                  <v-row v-if="folderScanResults.length > 0" class="mt-4">
                    <v-col cols="12">
                      <v-card outlined>
                        <v-card-title class="text-subtitle-1">
                          <v-icon left color="blue darken-2">mdi-file-tree</v-icon>
                          Folder Scan Results
                        </v-card-title>
                        <v-card-text>
                          <v-alert type="info" dense class="mb-3">
                            Found {{ folderScanResults.length }} files in {{ selectedFolderPath }}
                          </v-alert>
                          <v-data-table
                            :headers="folderScanHeaders"
                            :items="folderScanResults"
                            :items-per-page="10"
                            class="elevation-0"
                          >
                            <template v-slot:item.size="{ item }">
                              {{ formatFileSize(item.size) }}
                            </template>
                            <template v-slot:item.type="{ item }">
                              <v-chip small :color="getFileTypeColor(item.type)">{{ item.type }}</v-chip>
                            </template>
                          </v-data-table>
                        </v-card-text>
                      </v-card>
                    </v-col>
                  </v-row>
                </v-card-text>
              </v-card>
            </div>

            <!-- API Settings Tab Content -->
            <div v-if="activeTab === 2">
              <v-card flat>
                <v-card-text>
                  <v-alert
                    type="info"
                    outlined
                    class="mb-4"
                  >
                    API settings and configuration will be available in a future release.
                  </v-alert>
                </v-card-text>
              </v-card>
            </div>

            <!-- Exports Tab Content -->
            <div v-if="activeTab === 3">
              <v-card flat>
                <v-card-text>
                  <v-row>
                    <v-col cols="12" md="8">
                      <v-card outlined>
                        <v-card-title class="text-subtitle-1">
                          <v-icon left color="orange darken-2">mdi-export</v-icon>
                          Export Configuration
                        </v-card-title>
                        <v-card-text>
                          <!-- Vendor Selection -->
                          <v-row>
                            <v-col cols="12" md="6">
                              <v-select
                                v-model="selectedVendor"
                                :items="exportVendors"
                                label="Export Vendor"
                                outlined
                                prepend-icon="mdi-domain"
                                hint="Select the target export platform"
                                persistent-hint
                              ></v-select>
                            </v-col>
                            <v-col cols="12" md="6">
                              <v-select
                                v-model="selectedExportFormat"
                                :items="availableExportFormats"
                                label="Export Format"
                                outlined
                                prepend-icon="mdi-file-export"
                                :disabled="!selectedVendor"
                                hint="Choose the export file format"
                                persistent-hint
                              ></v-select>
                            </v-col>
                          </v-row>

                          <!-- Export Options -->
                          <v-divider class="my-4"></v-divider>
                          <h3 class="text-h6 mb-3">Export Options</h3>
                          
                          <!-- Extraction Scope -->
                          <v-row>
                            <v-col cols="12" md="6">
                              <v-select
                                v-model="exportOptions.extractionScope"
                                :items="extractionScopes"
                                label="Extraction Scope"
                                outlined
                                prepend-icon="mdi-target"
                              ></v-select>
                            </v-col>
                            <v-col cols="12" md="6">
                              <v-text-field
                                v-model="exportOptions.sizeLimit"
                                label="Size Limit (GB)"
                                outlined
                                type="number"
                                prepend-icon="mdi-harddisk"
                                hint="Maximum export size in GB"
                                persistent-hint
                              ></v-text-field>
                            </v-col>
                          </v-row>

                          <!-- Content Options -->
                          <v-row>
                            <v-col cols="12">
                              <h4 class="text-subtitle-1 mb-2">Content Options</h4>
                              <v-checkbox
                                v-model="exportOptions.includeAttachments"
                                label="Include Attachments"
                                hide-details
                              ></v-checkbox>
                              <v-checkbox
                                v-model="exportOptions.includeMetadata"
                                label="Include Metadata"
                                hide-details
                              ></v-checkbox>
                              <v-checkbox
                                v-model="exportOptions.includeThreading"
                                label="Include Email Threading"
                                hide-details
                              ></v-checkbox>
                              <v-checkbox
                                v-model="exportOptions.includeDocuments"
                                label="Include Documents"
                                hide-details
                              ></v-checkbox>
                            </v-col>
                          </v-row>

                          <!-- Compliance Options -->
                          <v-row>
                            <v-col cols="12">
                              <h4 class="text-subtitle-1 mb-2">Compliance & Security</h4>
                              <v-checkbox
                                v-model="exportOptions.chainOfCustody"
                                label="Chain of Custody Documentation"
                                hide-details
                              ></v-checkbox>
                              <v-checkbox
                                v-model="exportOptions.encryption"
                                label="Encrypt Export"
                                hide-details
                              ></v-checkbox>
                              <v-checkbox
                                v-model="exportOptions.legalHolds"
                                label="Include Legal Hold Information"
                                hide-details
                              ></v-checkbox>
                            </v-col>
                          </v-row>

                          <!-- Date Range -->
                          <v-row>
                            <v-col cols="12" md="6">
                              <v-text-field
                                v-model="exportOptions.dateFrom"
                                label="Date From"
                                type="date"
                                outlined
                                prepend-icon="mdi-calendar-start"
                              ></v-text-field>
                            </v-col>
                            <v-col cols="12" md="6">
                              <v-text-field
                                v-model="exportOptions.dateTo"
                                label="Date To"
                                type="date"
                                outlined
                                prepend-icon="mdi-calendar-end"
                              ></v-text-field>
                            </v-col>
                          </v-row>
                        </v-card-text>
                        <v-card-actions>
                          <v-btn
                            color="primary"
                            :disabled="!selectedVendor || !selectedExportFormat"
                            :loading="isExporting"
                            @click="startExport"
                          >
                            <v-icon left>mdi-play</v-icon>
                            Start Export
                          </v-btn>
                          <v-btn
                            color="secondary"
                            :disabled="!selectedVendor || !selectedExportFormat"
                            :loading="isPreviewingExport"
                            @click="previewExport"
                          >
                            <v-icon left>mdi-eye</v-icon>
                            Preview Export
                          </v-btn>
                          <v-spacer></v-spacer>
                          <v-btn
                            text
                            :disabled="!selectedVendor"
                            @click="downloadTemplate"
                          >
                            <v-icon left>mdi-download</v-icon>
                            Download Template
                          </v-btn>
                        </v-card-actions>
                      </v-card>
                    </v-col>
                    
                    <!-- Vendor Information Panel -->
                    <v-col cols="12" md="4">
                      <v-card outlined v-if="selectedVendor">
                        <v-card-title class="text-subtitle-1">
                          <v-icon left color="blue darken-2">mdi-information</v-icon>
                          {{ selectedVendor }} Information
                        </v-card-title>
                        <v-card-text>
                          <div v-if="vendorInfo">
                            <p><strong>Features:</strong></p>
                            <ul>
                              <li v-for="feature in vendorInfo.features" :key="feature">{{ feature }}</li>
                            </ul>
                            <p class="mt-3"><strong>Requirements:</strong></p>
                            <ul>
                              <li v-for="requirement in vendorInfo.requirements" :key="requirement">{{ requirement }}</li>
                            </ul>
                          </div>
                        </v-card-text>
                      </v-card>
                    </v-col>
                  </v-row>
                </v-card-text>
              </v-card>
            </div>

            <!-- External Audit Logs Tab Content -->
            <div v-if="activeTab === 4">
              <v-card flat>
                <v-card-text>
                  <v-row>
                                       
                    <!-- Microsoft Purview Configuration -->
                    <v-col cols="12" md="6">
                      <v-card outlined>
                        <v-card-title class="text-subtitle-1">
                          <v-icon left color="blue darken-2">mdi-microsoft</v-icon>
                          Microsoft Purview Configuration
                        </v-card-title>
                        <v-card-text>
                          <p class="mb-4">
                            Configure Microsoft Purview integration to collect audit logs from Office 365 Management Activity API.
                            This enables automated collection of user activities, file access, and compliance events.
                          </p>
                          
                          <!-- Purview Status -->
                          <v-alert
                            :type="purviewStatus.status"
                            outlined
                            class="mb-4"
                          >
                            <strong>Purview Status:</strong> {{ purviewStatus.message }}
                          </v-alert>
                          
                          <!-- Azure Configuration Selector -->
                          <v-select
                            v-model="selectedAzureConfig"
                            :items="azureConfigurations"
                            item-title="display_name"
                            item-value="name"
                            label="Azure Configuration"
                            outlined
                            density="compact"
                            prepend-icon="mdi-microsoft-azure"
                            hint="Select existing configuration or enter custom credentials"
                            persistent-hint
                            :loading="isLoadingConfigs"
                            @update:modelValue="onAzureConfigChange"
                            class="mb-3"
                          >
                            <template v-slot:item="{ props, item }">
                              <v-list-item v-bind="props">
                                <v-list-item-title>{{ item.raw.display_name }}</v-list-item-title>
                                <v-list-item-subtitle v-if="item.raw.name !== 'custom'">
                                  Tenant: {{ item.raw.tenant_id.substring(0, 8) }}...
                                </v-list-item-subtitle>
                              </v-list-item>
                            </template>
                          </v-select>
                          
                          <!-- Azure Configuration -->
                          <v-text-field
                            v-model="purviewConfig.tenantId"
                            label="Azure Tenant ID"
                            outlined
                            dense
                            prepend-icon="mdi-domain"
                            hint="Your Azure AD tenant ID"
                            persistent-hint
                            :readonly="selectedAzureConfig !== 'custom'"
                            :filled="selectedAzureConfig !== 'custom'"
                          ></v-text-field>
                          
                          <v-text-field
                            v-model="purviewConfig.clientId"
                            label="Client ID (App Registration)"
                            outlined
                            dense
                            prepend-icon="mdi-application"
                            hint="Azure app registration client ID"
                            persistent-hint
                            :readonly="selectedAzureConfig !== 'custom'"
                            :filled="selectedAzureConfig !== 'custom'"
                          ></v-text-field>
                          
                          <v-text-field
                            v-model="purviewConfig.clientSecret"
                            label="Client Secret"
                            outlined
                            dense
                            :type="showClientSecret ? 'text' : 'password'"
                            prepend-icon="mdi-key"
                            hint="Azure app registration client secret"
                            persistent-hint
                            :readonly="selectedAzureConfig !== 'custom'"
                            :filled="selectedAzureConfig !== 'custom'"
                            :append-icon="showClientSecret ? 'mdi-eye' : 'mdi-eye-off'"
                            @click:append="showClientSecret = !showClientSecret"
                          ></v-text-field>
                          
                          <!-- Content Types -->
                          <v-select
                            v-model="purviewConfig.contentTypes"
                            :items="availableContentTypes"
                            label="Content Types to Collect"
                            outlined
                            dense
                            multiple
                            chips
                            prepend-icon="mdi-format-list-bulleted"
                            hint="Select audit log content types"
                            persistent-hint
                          ></v-select>
                          
                          <!-- Collection Schedule -->
                          <v-select
                            v-model="purviewConfig.schedule"
                            :items="collectionSchedules"
                            label="Collection Schedule"
                            outlined
                            dense
                            prepend-icon="mdi-clock"
                            hint="How often to collect audit logs"
                            persistent-hint
                          ></v-select>
                        </v-card-text>
                        <v-card-actions>
                          <v-btn
                            color="primary"
                            :loading="isConfiguringPurview"
                            @click="configurePurview"
                          >
                            <v-icon left>mdi-cog</v-icon>
                            Configure Purview
                          </v-btn>
                          <v-btn
                            color="secondary"
                            :loading="isTestingPurview"
                            @click="testPurviewConnection"
                          >
                            <v-icon left>mdi-connection</v-icon>
                            Test Connection
                          </v-btn>
                          <v-spacer></v-spacer>
                          <v-btn
                            text
                            @click="resetPurviewConfig"
                          >
                            <v-icon left>mdi-refresh</v-icon>
                            Reset
                          </v-btn>
                        </v-card-actions>
                      </v-card>
                    </v-col>
                  </v-row>
                  
                  <!-- AI-Enhanced Features Section -->
                  <v-row class="mt-4">
                    <v-col cols="12">
                      <v-card outlined>
                        <v-card-title class="text-subtitle-1">
                          <v-icon left color="purple darken-2">mdi-brain</v-icon>
                          AI-Enhanced Features
                        </v-card-title>
                        <v-card-text>
                          <v-row>
                            <v-col cols="12" md="4">
                              <v-card outlined class="text-center pa-4">
                                <v-icon size="48" color="red darken-2" class="mb-3">mdi-shield-check</v-icon>
                                <h4 class="text-h6 mb-2">Security Analysis</h4>
                                <p class="text-body-2">
                                  Automatic threat detection, anomaly scoring, and security risk assessment
                                </p>
                              </v-card>
                            </v-col>
                            <v-col cols="12" md="4">
                              <v-card outlined class="text-center pa-4">
                                <v-icon size="48" color="blue darken-2" class="mb-3">mdi-gavel</v-icon>
                                <h4 class="text-h6 mb-2">Compliance Framework</h4>
                                <p class="text-body-2">
                                  GDPR, SOX, HIPAA, and ISO 27001 compliance tagging and reporting
                                </p>
                              </v-card>
                            </v-col>
                            <v-col cols="12" md="4">
                              <v-card outlined class="text-center pa-4">
                                <v-icon size="48" color="green darken-2" class="mb-3">mdi-chart-line</v-icon>
                                <h4 class="text-h6 mb-2">Advanced Analytics</h4>
                                <p class="text-body-2">
                                  Temporal patterns, risk analysis, and AI-powered insights
                                </p>
                              </v-card>
                            </v-col>
                          </v-row>
                        </v-card-text>
                      </v-card>
                    </v-col>
                  </v-row>
                  
                  <!-- Collection Status Section -->
                  <v-row class="mt-4">
                    <v-col cols="12">
                      <v-card outlined>
                        <v-card-title class="text-subtitle-1">
                          <v-icon left color="orange darken-2">mdi-chart-timeline-variant</v-icon>
                          Collection Status & History
                        </v-card-title>
                        <v-card-text>
                          <v-row>
                            <v-col cols="12" md="6">
                              <h4 class="text-subtitle-1 mb-3">Recent Collection Jobs</h4>
                              <v-data-table
                                :headers="collectionJobHeaders"
                                :items="recentCollectionJobs"
                                :items-per-page="5"
                                class="elevation-0"
                              >
                                <template v-slot:item.status="{ item }">
                                  <v-chip
                                    small
                                    :color="getStatusColor(item.status)"
                                    text-color="white"
                                  >
                                    {{ item.status }}
                                  </v-chip>
                                </template>
                                <template v-slot:item.recordsProcessed="{ item }">
                                  {{ item.recordsProcessed }} / {{ item.recordsTotal }}
                                </template>
                              </v-data-table>
                            </v-col>
                            <v-col cols="12" md="6">
                              <h4 class="text-subtitle-1 mb-3">Quick Actions</h4>
                              <v-btn
                                color="primary"
                                block
                                class="mb-2"
                                :loading="isStartingCollection"
                                @click="startManualCollection"
                              >
                                <v-icon left>mdi-play</v-icon>
                                Start Manual Collection
                              </v-btn>
                              <v-btn
                                color="secondary"
                                block
                                class="mb-2"
                                @click="viewCollectionStats"
                              >
                                <v-icon left>mdi-chart-bar</v-icon>
                                View Statistics
                              </v-btn>
                              <v-btn
                                color="info"
                                block
                                class="mb-2"
                                @click="viewAIInsights"
                              >
                                <v-icon left>mdi-brain</v-icon>
                                AI Insights
                              </v-btn>
                              <v-btn
                                color="warning"
                                block
                                @click="viewComplianceReport"
                              >
                                <v-icon left>mdi-file-document</v-icon>
                                Compliance Report
                              </v-btn>
                            </v-col>
                          </v-row>
                        </v-card-text>
                      </v-card>
                    </v-col>
                  </v-row>
                </v-card-text>
              </v-card>
            </div>
          </div>
        </v-card>
      </v-col>
    </v-row>
    
    <!-- Snackbar for notifications -->
    <v-snackbar
      v-model="snackbar.show"
      :color="snackbar.color"
      :timeout="snackbar.timeout"
    >
      {{ snackbar.text }}
      <template v-slot:action="{ attrs }">
        <v-btn
          text
          v-bind="attrs"
          @click="snackbar.show = false"
        >
          Close
        </v-btn>
      </template>
    </v-snackbar>
  </v-container>
</template>

<script>
// Force rebuild: 2025-06-14T22:05:41.000Z
import { integrationsApi } from '../services/api';

export default {
  name: 'Integrations',
  data() {
    return {
      activeTab: 0,
      selectedFiles: [],
      selectedDocuments: [],
      isUploading: false,
      isUploadingDocs: false,
      uploadProgress: [],
      importHeaders: [
        { text: 'File Name', value: 'fileName' },
        { text: 'Import Date', value: 'importDate' },
        { text: 'Status', value: 'status' },
        { text: 'Records', value: 'recordCount' },
        { text: 'Actions', value: 'actions', sortable: false }
      ],
      recentImports: [
        {
          fileName: 'emails_batch_1.eml',
          importDate: '2024-01-15',
          status: 'completed',
          recordCount: 150
        },
        {
          fileName: 'archive_export.eml',
          importDate: '2024-01-14',
          status: 'failed',
          recordCount: 0
        }
      ],
      snackbar: {
        show: false,
        text: '',
        color: 'success',
        timeout: 3000
      },
      // Export-related data
      selectedVendor: '',
      selectedExportFormat: '',
      isExporting: false,
      isPreviewingExport: false,
      exportVendors: [
        'Microsoft Purview',
        'Proofpoint',
        'Mimecast',
        'Global Relay'
      ],
      exportOptions: {
        extractionScope: 'All Data',
        includeAttachments: true,
        includeMetadata: true,
        includeThreading: true,
        includeDocuments: true,
        chainOfCustody: true,
        encryption: false,
        legalHolds: true,
        dateFrom: '',
        dateTo: '',
        sizeLimit: 10
      },
      extractionScopes: [
        'All Data',
        'Legal Hold Data Only',
        'Specific Date Range',
        'Custom Query'
      ],
      // Folder import data
      selectedFolderPath: '',
      isImportingFolder: false,
      folderImportOptions: {
        includeSubfolders: true,
        preserveStructure: true,
        skipDuplicates: true,
        fileFilter: 'All Files'
      },
      documentFilters: [
        'All Files',
        'PDF Documents',
        'Microsoft Office',
        'Images',
        'Text Files',
        'Archives'
      ],
      folderScanResults: [],
      folderScanHeaders: [
        { text: 'File Name', value: 'name' },
        { text: 'Type', value: 'type' },
        { text: 'Size', value: 'size' },
        { text: 'Modified', value: 'modified' },
        { text: 'Path', value: 'path' }
      ],
      // External Audit Logs data
      purviewConfig: {
        tenantId: '',
        clientId: '',
        clientSecret: '',
        contentTypes: ['Audit.AzureActiveDirectory', 'Audit.Exchange', 'Audit.SharePoint'],
        schedule: '24_hours'
      },
      purviewStatus: {
        status: 'info',
        message: 'Microsoft Purview not configured'
      },
      isConfiguringPurview: false,
      isTestingPurview: false,
      isStartingCollection: false,
      // Azure configuration selector
      selectedAzureConfig: 'custom',
      azureConfigurations: [],
      isLoadingConfigs: false,
      showClientSecret: false,
      availableContentTypes: [
        'Audit.AzureActiveDirectory',
        'Audit.Exchange', 
        'Audit.SharePoint',
        'Audit.General',
        'DLP.All'
      ],
      collectionSchedules: [
        { text: 'Every 6 hours', value: '6_hours' },
        { text: 'Every 12 hours', value: '12_hours' },
        { text: 'Every 24 hours', value: '24_hours' },
        { text: 'Custom schedule', value: 'custom' }
      ],
      collectionJobHeaders: [
        { text: 'Job ID', value: 'jobId' },
        { text: 'Source', value: 'sourceSystem' },
        { text: 'Status', value: 'status' },
        { text: 'Records', value: 'recordsProcessed' },
        { text: 'Start Time', value: 'startTime' },
        { text: 'End Time', value: 'endTime' }
      ],
      recentCollectionJobs: []
    };
  },
  computed: {
    availableExportFormats() {
      if (!this.selectedVendor) return [];
      
      const formats = {
        'Microsoft Purview': ['PST', 'EML', 'MSG', 'JSON'],
        'Proofpoint': ['PST', 'EML', 'MBOX'],
        'Mimecast': ['PST', 'EML', 'JSON'],
        'Global Relay': ['EML', 'MSG', 'XML']
      };
      
      return formats[this.selectedVendor] || [];
    },
    vendorInfo() {
      if (!this.selectedVendor) return null;
      
      const info = {
        'Microsoft Purview': {
          features: ['Advanced compliance', 'Data loss prevention', 'Retention policies', 'eDiscovery'],
          requirements: ['Azure AD integration', 'Compliance center access', 'Export permissions']
        },
        'Proofpoint': {
          features: ['Email security', 'Threat protection', 'Data archiving', 'Compliance reporting'],
          requirements: ['API credentials', 'Export license', 'Network connectivity']
        },
        'Mimecast': {
          features: ['Email continuity', 'Security services', 'Archive search', 'Policy management'],
          requirements: ['Admin console access', 'API authentication', 'Export permissions']
        },
        'Global Relay': {
          features: ['Message archiving', 'Supervision', 'eDiscovery', 'Compliance monitoring'],
          requirements: ['Archive access', 'Export credentials', 'Data retention policies']
        }
      };
      
      return info[this.selectedVendor];
    }
  },
  watch: {
    activeTab(newVal) {
      console.log('Active tab changed to:', newVal);
      // Load collection jobs when external audit logs tab is selected
      if (newVal === 4) {
        this.loadCollectionJobs();
        this.loadPurviewConfig();
      }
    }
  },
  mounted() {
    console.log('Integrations component mounted, activeTab:', this.activeTab);
    // Load collection jobs if external audit logs tab is active
    if (this.activeTab === 4) {
      this.loadCollectionJobs();
      this.loadPurviewConfig();
    }
    this.loadAzureConfigurations();
  },
  methods: {
    async uploadFiles() {
      if (!this.selectedFiles || this.selectedFiles.length === 0) {
        this.showSnackbar('Please select files to upload', 'error');
        return;
      }

      this.isUploading = true;
      this.uploadProgress = [];

      try {
        for (let i = 0; i < this.selectedFiles.length; i++) {
          const file = this.selectedFiles[i];
          
          // Add progress tracking
          this.uploadProgress.push({
            fileName: file.name,
            percentage: 0,
            status: 'uploading'
          });

          // Simulate upload progress
          for (let progress = 0; progress <= 100; progress += 20) {
            this.uploadProgress[i].percentage = progress;
            await new Promise(resolve => setTimeout(resolve, 200));
          }

          // Simulate API call
          try {
            await integrationsApi.uploadEmlFile(file);
            this.uploadProgress[i].status = 'completed';
            this.uploadProgress[i].percentage = 100;
          } catch (error) {
            this.uploadProgress[i].status = 'error';
            console.error('Upload failed:', error);
          }
        }

        this.showSnackbar(`Successfully uploaded ${this.selectedFiles.length} files`, 'success');
        this.selectedFiles = [];
        
        // Clear progress after delay
        setTimeout(() => {
          this.uploadProgress = [];
        }, 3000);

      } catch (error) {
        console.error('Upload error:', error);
        this.showSnackbar('Upload failed: ' + error.message, 'error');
      } finally {
        this.isUploading = false;
      }
    },

    async uploadDocuments() {
      if (!this.selectedDocuments || this.selectedDocuments.length === 0) {
        this.showSnackbar('Please select documents to upload', 'error');
        return;
      }

      this.isUploadingDocs = true;
      try {
        // Simulate document upload
        await new Promise(resolve => setTimeout(resolve, 2000));
        this.showSnackbar(`Successfully uploaded ${this.selectedDocuments.length} documents`, 'success');
        this.selectedDocuments = [];
      } catch (error) {
        console.error('Document upload error:', error);
        this.showSnackbar('Document upload failed: ' + error.message, 'error');
      } finally {
        this.isUploadingDocs = false;
      }
    },

    viewImportDetails(item) {
      console.log('Viewing import details for:', item);
      // Implementation for viewing import details
    },

    showSnackbar(text, color = 'success') {
      this.snackbar.text = text;
      this.snackbar.color = color;
      this.snackbar.show = true;
    },

    // Export methods
    async startExport() {
      this.isExporting = true;
      try {
        await this.simulateExport();
        this.showSnackbar(`Export started for ${this.selectedVendor}`, 'success');
      } catch (error) {
        this.showSnackbar('Export failed: ' + error.message, 'error');
      } finally {
        this.isExporting = false;
      }
    },

    async previewExport() {
      this.isPreviewingExport = true;
      try {
        await this.simulatePreview();
        this.showSnackbar('Export preview generated', 'info');
      } catch (error) {
        this.showSnackbar('Preview failed: ' + error.message, 'error');
      } finally {
        this.isPreviewingExport = false;
      }
    },

    async downloadTemplate() {
      try {
        await this.simulateTemplateDownload();
        this.showSnackbar(`Template downloaded for ${this.selectedVendor}`, 'success');
      } catch (error) {
        this.showSnackbar('Template download failed: ' + error.message, 'error');
      }
    },

    async simulateExport() {
      await new Promise(resolve => setTimeout(resolve, 1000));
      // In a real implementation, this would call the backend API
      console.log(`Starting export to ${this.selectedVendor} in ${this.selectedExportFormat} format`);
    },

    async simulatePreview() {
      await new Promise(resolve => setTimeout(resolve, 800));
      // In a real implementation, this would generate a preview
      console.log(`Generating preview for ${this.selectedVendor}`);
    },

    async simulateTemplateDownload() {
      await new Promise(resolve => setTimeout(resolve, 500));
      // In a real implementation, this would trigger a file download
      console.log(`Downloading template for ${this.selectedVendor}`);
    },
    
    // Folder import methods
    browseFolders() {
      // In a real implementation, this would open a folder browser dialog
      // For now, simulate folder selection
      this.selectedFolderPath = '/Users/example/Documents/ImportFolder';
      this.showSnackbar('Folder selected (simulated)', 'info');
    },
    
    async scanFolder() {
      if (!this.selectedFolderPath) {
        this.showSnackbar('Please select a folder first', 'error');
        return;
      }
      
      try {
        this.showSnackbar('Scanning folder...', 'info');
        
        // Simulate folder scanning
        await new Promise(resolve => setTimeout(resolve, 1500));
        
        // Mock scan results
        this.folderScanResults = [
          {
            name: 'document1.pdf',
            type: 'PDF',
            size: 2048576,
            modified: '2024-01-15',
            path: '/Documents/document1.pdf'
          },
          {
            name: 'presentation.pptx',
            type: 'PowerPoint',
            size: 5242880,
            modified: '2024-01-14',
            path: '/Documents/presentation.pptx'
          },
          {
            name: 'spreadsheet.xlsx',
            type: 'Excel',
            size: 1048576,
            modified: '2024-01-13',
            path: '/Documents/spreadsheet.xlsx'
          },
          {
            name: 'image.jpg',
            type: 'Image',
            size: 3145728,
            modified: '2024-01-12',
            path: '/Documents/image.jpg'
          }
        ];
        
        this.showSnackbar(`Found ${this.folderScanResults.length} files`, 'success');
      } catch (error) {
        console.error('Folder scan error:', error);
        this.showSnackbar('Folder scan failed: ' + error.message, 'error');
      }
    },
    
    async importFolder() {
      if (!this.selectedFolderPath) {
        this.showSnackbar('Please select a folder first', 'error');
        return;
      }
      
      this.isImportingFolder = true;
      
      try {
        this.showSnackbar('Starting folder import...', 'info');
        
        // Simulate folder import process
        await new Promise(resolve => setTimeout(resolve, 3000));
        
        // In a real implementation, this would:
        // 1. Recursively scan the folder based on options
        // 2. Filter files by type if specified
        // 3. Upload files to the archive system
        // 4. Preserve folder structure if requested
        // 5. Skip duplicates if enabled
        
        const fileCount = this.folderScanResults.length || 15; // Use scan results or default
        this.showSnackbar(`Successfully imported ${fileCount} files from folder`, 'success');
        
        // Clear the folder path and scan results
        this.selectedFolderPath = '';
        this.folderScanResults = [];
        
      } catch (error) {
        console.error('Folder import error:', error);
        this.showSnackbar('Folder import failed: ' + error.message, 'error');
      } finally {
        this.isImportingFolder = false;
      }
    },
    
    formatFileSize(bytes) {
      if (bytes === 0) return '0 Bytes';
      const k = 1024;
      const sizes = ['Bytes', 'KB', 'MB', 'GB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },
    
    getFileTypeColor(type) {
      const colors = {
        'PDF': 'red',
        'Word': 'blue',
        'Excel': 'green',
        'PowerPoint': 'orange',
        'Image': 'purple',
        'Text': 'grey',
        'Archive': 'brown'
      };
      return colors[type] || 'grey';
    },
    
    // Debug method to test tab switching
    switchToTab(tabIndex) {
      console.log('Manually switching to tab:', tabIndex);
      this.activeTab = tabIndex;
    },
    
    // System status methods
    async refreshSystemStatus() {
      try {
        // In a real implementation, this would call an API to get system status
        this.showSnackbar('System status refreshed', 'info');
      } catch (error) {
        console.error('Error refreshing system status:', error);
        this.showSnackbar('Failed to refresh system status', 'error');
      }
    },
    
    async viewSystemLogs() {
      try {
        // In a real implementation, this would open a modal or navigate to logs
        this.showSnackbar('System logs view not implemented yet', 'info');
      } catch (error) {
        console.error('Error viewing system logs:', error);
        this.showSnackbar('Failed to view system logs', 'error');
      }
    },
    
    // External Audit Logs methods
    async configurePurview() {
      this.isConfiguringPurview = true;
      try {
        // First check if the source already exists
        const checkResponse = await fetch('/api/v1/external-audit-logs/sources/microsoft_purview');
        const method = checkResponse.ok ? 'PUT' : 'POST';
        const url = checkResponse.ok 
          ? '/api/v1/external-audit-logs/sources/microsoft_purview'
          : '/api/v1/external-audit-logs/sources';
        
        // Use PascalCase keys for PUT (update), original for POST (create)
        const requestBody = checkResponse.ok ? {
          DisplayName: 'Microsoft Purview Production',
          Description: 'Office 365 Management Activity API',
          Configuration: JSON.stringify({
            tenant_id: this.purviewConfig.tenantId,
            client_id: this.purviewConfig.clientId,
            client_secret: this.purviewConfig.clientSecret,
            content_types: this.purviewConfig.contentTypes
          }),
          Schedule: JSON.stringify({
            type: 'interval',
            hours: this.getScheduleHours(this.purviewConfig.schedule)
          }),
          RetentionDays: 2555,
          IsActive: true
        } : {
          source_system: 'microsoft_purview',
          display_name: 'Microsoft Purview Production',
          description: 'Office 365 Management Activity API',
          configuration: {
            tenant_id: this.purviewConfig.tenantId,
            client_id: this.purviewConfig.clientId,
            client_secret: this.purviewConfig.clientSecret,
            content_types: this.purviewConfig.contentTypes
          },
          schedule: {
            type: 'interval',
            hours: this.getScheduleHours(this.purviewConfig.schedule)
          },
          retention_days: 2555,
          is_active: true
        };
        
        const response = await fetch(url, {
          method: method,
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(requestBody)
        });
        
        if (response.ok) {
          const action = checkResponse.ok ? 'updated' : 'configured';
          this.purviewStatus = {
            status: 'success',
            message: `Microsoft Purview ${action} successfully`
          };
          this.showSnackbar(`Microsoft Purview ${action} successfully`, 'success');
        } else {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || 'Purview configuration failed');
        }
      } catch (error) {
        console.error('Purview configuration error:', error);
        this.purviewStatus = {
          status: 'error',
          message: 'Purview configuration failed: ' + error.message
        };
        this.showSnackbar('Purview configuration failed: ' + error.message, 'error');
      } finally {
        this.isConfiguringPurview = false;
      }
    },
    
    async testPurviewConnection() {
      this.isTestingPurview = true;
      try {
        const response = await fetch('/api/v1/external-audit-logs/test-connection/microsoft_purview', {
          method: 'GET'
        });
        
        if (response.ok) {
          const result = await response.json();
          if (result.connection_ok) {
            this.purviewStatus = {
              status: 'success',
              message: 'Microsoft Purview connection successful'
            };
            this.showSnackbar('Microsoft Purview connection test successful', 'success');
          } else {
            throw new Error('Connection test failed');
          }
        } else {
          throw new Error('Connection test failed');
        }
      } catch (error) {
        console.error('Purview connection test error:', error);
        this.purviewStatus = {
          status: 'error',
          message: 'Purview connection failed: ' + error.message
        };
        this.showSnackbar('Purview connection test failed: ' + error.message, 'error');
      } finally {
        this.isTestingPurview = false;
      }
    },
    
    resetPurviewConfig() {
      this.purviewConfig = {
        tenantId: '',
        clientId: '',
        clientSecret: '',
        contentTypes: ['Audit.AzureActiveDirectory', 'Audit.Exchange', 'Audit.SharePoint'],
        schedule: '24_hours'
      };
      this.purviewStatus = {
        status: 'info',
        message: 'Microsoft Purview not configured'
      };
      this.showSnackbar('Purview configuration reset', 'info');
    },
    
    getScheduleHours(schedule) {
      const scheduleMap = {
        '6_hours': 6,
        '12_hours': 12,
        '24_hours': 24,
        'custom': 24
      };
      return scheduleMap[schedule] || 24;
    },
    
    async loadPurviewConfig() {
      try {
        const response = await fetch('/api/v1/external-audit-logs/sources/microsoft_purview');
        if (response.ok) {
          const source = await response.json();
          if (source.configuration) {
            this.purviewConfig = {
              tenantId: source.configuration.tenant_id || '',
              clientId: source.configuration.client_id || '',
              clientSecret: source.configuration.client_secret || '',
              contentTypes: source.configuration.content_types || ['Audit.AzureActiveDirectory', 'Audit.Exchange', 'Audit.SharePoint'],
              schedule: this.getScheduleFromHours(source.schedule?.hours || 24)
            };
            this.purviewStatus = {
              status: 'success',
              message: 'Microsoft Purview configuration loaded'
            };
          }
        }
      } catch (error) {
        console.error('Error loading Purview config:', error);
        // Keep default values if loading fails
      }
    },
    
    getScheduleFromHours(hours) {
      const scheduleMap = {
        6: '6_hours',
        12: '12_hours',
        24: '24_hours'
      };
      return scheduleMap[hours] || '24_hours';
    },
    
    async startManualCollection() {
      this.isStartingCollection = true;
      try {
        const response = await fetch('/api/v1/external-audit-logs/collect', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            source_system: 'microsoft_purview',
            job_type: 'manual'
          })
        });
        
        if (response.ok) {
          const result = await response.json();
          this.showSnackbar(`Manual collection started. Job ID: ${result.job_id}`, 'success');
          // Refresh collection jobs
          await this.loadCollectionJobs();
        } else {
          throw new Error('Failed to start collection');
        }
      } catch (error) {
        console.error('Manual collection error:', error);
        this.showSnackbar('Failed to start manual collection: ' + error.message, 'error');
      } finally {
        this.isStartingCollection = false;
      }
    },
    
    async loadCollectionJobs() {
      try {
        const response = await fetch('/api/v1/external-audit-logs/jobs?limit=10');
        if (response.ok) {
          const jobs = await response.json();
          this.recentCollectionJobs = jobs.map(job => ({
            jobId: job.job_id,
            sourceSystem: job.source_system,
            status: job.status,
            recordsProcessed: job.records_processed || 0,
            recordsTotal: job.records_total || 0,
            startTime: job.start_time,
            endTime: job.end_time
          }));
        }
      } catch (error) {
        console.error('Error loading collection jobs:', error);
      }
    },
    
    getStatusColor(status) {
      const colors = {
        'completed': 'green',
        'running': 'blue',
        'failed': 'red',
        'cancelled': 'orange'
      };
      return colors[status] || 'grey';
    },
    
    async viewCollectionStats() {
      try {
        const response = await fetch('/api/v1/external-audit-logs/stats?days=30');
        if (response.ok) {
          const stats = await response.json();
          // In a real implementation, this would open a modal or navigate to a stats page
          this.showSnackbar(`Total events: ${stats.total_events}, Security events: ${stats.security_events}`, 'info');
        }
      } catch (error) {
        console.error('Error loading stats:', error);
        this.showSnackbar('Failed to load statistics', 'error');
      }
    },
    
    async viewAIInsights() {
      try {
        const response = await fetch('/api/v1/external-audit-logs/ai-insights', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            days: 30,
            include_temporal_patterns: true,
            include_risk_analysis: true,
            include_compliance_insights: true
          })
        });
        
        if (response.ok) {
          const insights = await response.json();
          // In a real implementation, this would open a modal with AI insights
          this.showSnackbar('AI insights loaded successfully', 'success');
        }
      } catch (error) {
        console.error('Error loading AI insights:', error);
        this.showSnackbar('Failed to load AI insights', 'error');
      }
    },
    
    async viewComplianceReport() {
      try {
        const response = await fetch('/api/v1/external-audit-logs/compliance-report', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            start_date: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(),
            end_date: new Date().toISOString(),
            include_legal_hold_events: true,
            include_retention_events: true
          })
        });
        
        if (response.ok) {
          const report = await response.json();
          // In a real implementation, this would open a modal with compliance report
          this.showSnackbar(`Compliance score: ${report.compliance_score}%`, 'success');
        }
      } catch (error) {
        console.error('Error loading compliance report:', error);
        this.showSnackbar('Failed to load compliance report', 'error');
      }
    },
    
    async loadAzureConfigurations() {
      this.isLoadingConfigs = true;
      try {
        const response = await fetch('/api/v1/azure-configurations');
        if (response.ok) {
          const data = await response.json();
          this.azureConfigurations = data.configurations;
          
          // Set default to first available configuration if any exist (excluding custom)
          const realConfigs = data.configurations.filter(c => c.name !== 'custom');
          if (realConfigs.length > 0 && !this.purviewConfig.tenantId) {
            this.selectedAzureConfig = realConfigs[0].name;
            await this.onAzureConfigChange(realConfigs[0].name);
          }
        }
      } catch (error) {
        console.error('Error loading Azure configurations:', error);
        this.showSnackbar('Failed to load Azure configurations', 'error');
        // Add custom option as fallback
        this.azureConfigurations = [{
          name: 'custom',
          tenant_id: '',
          client_id: '',
          client_secret: '',
          display_name: 'Enter Custom Credentials',
          is_masked: false
        }];
      } finally {
        this.isLoadingConfigs = false;
      }
    },
    
    async onAzureConfigChange(configName) {
      if (!configName || configName === 'custom') {
        // Clear fields for custom entry
        this.purviewConfig.tenantId = '';
        this.purviewConfig.clientId = '';
        this.purviewConfig.clientSecret = '';
        return;
      }
      
      try {
        // Get full configuration including unmasked client secret
        const response = await fetch(`/api/v1/azure-configurations/${configName}/full`);
        if (response.ok) {
          const config = await response.json();
          this.purviewConfig.tenantId = config.tenant_id;
          this.purviewConfig.clientId = config.client_id;
          this.purviewConfig.clientSecret = config.client_secret;
          this.showSnackbar(`Loaded ${config.display_name}`, 'success');
        }
      } catch (error) {
        console.error('Error loading Azure configuration:', error);
        this.showSnackbar('Failed to load configuration details', 'error');
      }
    }
  }
};
</script>

<style scoped>
/* Let Vuetify handle tab behavior naturally */
</style>
