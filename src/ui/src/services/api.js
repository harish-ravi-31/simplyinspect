import axios from 'axios';

// Create an Axios instance with base URL and common headers
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api/v1', // Use environment variable with fallback
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  },
  timeout: 30000,
  withCredentials: true
});

// Log all API requests in development mode
apiClient.interceptors.request.use(request => {
  const fullUrl = request.baseURL ? request.baseURL + request.url : request.url;
  console.log('API Request:', request.method.toUpperCase(), fullUrl);
  return request;
});

// Request interceptor for handling auth tokens
apiClient.interceptors.request.use(
  config => {
    // Add auth token if available
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  error => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
// Note: 401 handling is done in useAuth.js to avoid conflicts
apiClient.interceptors.response.use(
  response => response,
  error => {
    // Let useAuth.js handle 401 errors for consistent behavior
    // Other error handling can be added here if needed
    return Promise.reject(error);
  }
);

// Email API
export const emailsApi = {
  search(params) {
    return apiClient.post('emails/search', params);
  },
  listEmails(params) {
    return apiClient.get('/emails', { params });
  },
  getEmail(id) {
    return apiClient.get(`/emails/${id}`);
  },
  updateEmailStatus(id, status) {
    return apiClient.patch(`/emails/${id}/status`, { archival_status: status });
  },
  deleteEmail(id) {
    return apiClient.delete(`/emails/${id}`);
  },
  getAttachmentUrl(emailId, attachmentIndex) {
    return `${apiClient.defaults.baseURL}/emails/${emailId}/attachments/${attachmentIndex}`;
  },
  getEmailsApproachingExpiration(days = 90, withBuckets = true) {
    console.log(`Getting emails approaching expiration: days=${days}, withBuckets=${withBuckets}`);
    return apiClient.get(`/emails/approaching-expiration?days=${days}&with_buckets=${withBuckets}`);
  },
};

// Retention Policy API
export const retentionApi = {
  getPolicies(activeOnly = true) {
    return apiClient.get(`/retention-policies/?active_only=${activeOnly}`);
  },
  getPolicy(id) {
    return apiClient.get(`/retention-policies/${id}/`);
  },
  createPolicy(policy) {
    return apiClient.post('retention-policies/', policy);
  },
  updatePolicy(id, policy) {
    return apiClient.put(`retention-policies/${id}/`, policy);
  },
  createExemption(exemption) {
    return apiClient.post('retention/exemptions', exemption);
  },
  runEnforcement(limit = 1000) {
    return apiClient.post(`retention/run-enforcement?limit=${limit}`);
  },
  getEnforcementStatus() {
    return apiClient.get('retention/enforcement-status');
  }
};

// Accepted Domains API
export const acceptedDomainsApi = {
  deleteAcceptedDomain(id) {
    return apiClient.delete(`/accepted-domains/${id}`);
  },
};

// Legal Hold API
export const legalHoldApi = {
  getLegalHolds(activeOnly = true) {
    return apiClient.get(`/legal-holds/?active_only=${activeOnly}`);
  },
  listLegalHolds(params) {
    return apiClient.get('/legal-holds', { params });
  },
  getLegalHold(id) {
    return apiClient.get(`/legal-holds/${id}`);
  },
  createLegalHold(legalHold) {
    return apiClient.post('legal-holds', legalHold);
  },
  updateLegalHold(id, legalHold) {
    return apiClient.put(`legal-holds/${id}`, legalHold);
  },
  addCriteria(id, criteria) {
    return apiClient.post(`legal-holds/${id}/criteria`, criteria);
  },
  getLegalHoldCriteria(holdId) {
    return apiClient.get(`/legal-holds/${holdId}/criteria`);
  },
  addLegalHoldCriteria(criteria) {
    const holdId = criteria.legal_hold_id;
    if (!holdId) {
      console.error('Error: legal_hold_id is required for constructing the endpoint path');
      return Promise.reject(new Error('legal_hold_id is required for constructing the endpoint path'));
    }
    const payload = {
      criteria_type: criteria.criteria_type,
      criteria_value: criteria.criteria_value
    };
    return apiClient.post(`legal-holds/${holdId}/criteria`, payload);
  },
  getEmailsOnHold() {
    return apiClient.get('legal-holds/emails/');
  },
  getLegalHoldStatistics(id) {
    return apiClient.get(`/legal-holds/${id}/statistics`);
  },
  applyCriteriaToEmails(id) {
    return apiClient.post(`/legal-holds/${id}/apply-criteria`);
  },
  applyDocumentCriteria(id) {
    return apiClient.post(`/legal-holds/${id}/apply-to-documents`);
  },
  getDocumentLegalHoldStatistics(id) {
    return apiClient.get(`/legal-holds/${id}/document-statistics`);
  },
  getDocumentsOnHold() {
    return apiClient.get('/legal-holds/documents-on-hold');
  },
  getDocumentLegalHoldStatus(documentId) {
    return apiClient.get(`/document-legal-holds/status/${documentId}`);
  }
};

// Dashboard API
export const dashboardApi = {
  getSummary() {
    return apiClient.get('dashboard/summary');
  },
  getLegalHolds(activeOnly = true) {
    return apiClient.get(`/legal-holds/?active_only=${activeOnly}`);
  },
  getRetentionPolicies(activeOnly = true) {
    return apiClient.get(`/dashboard/retention-policies?active_only=${activeOnly}`);
  },
  getDSRRequests(status = null) {
    return apiClient.get(`/dashboard/dsr-requests${status ? `?status=${status}` : ''}`);
  },
  getTotalArchiveSize() {
    return apiClient.get('system-metrics/total-archive-size');
  },
  getStorageStats(days) {
    return apiClient.get(`/dashboard/storage-growth?days=${days}`);
  },
  getAttachmentTypeStats() {
    return apiClient.get('dashboard/attachment-type-stats');
  }
};

// Chain of Custody API
export const custodyApi = {
  getChainOfCustody(emailId) {
    // Corresponds to get_full_chain_for_email in routes/chain_of_custody.py
    return apiClient.get(`/chain-of-custody/emails/${emailId}/chain`);
  },
  getDocumentChainOfCustody(documentId) {
    // Corresponds to get_full_chain_for_document in routes/chain_of_custody.py
    return apiClient.get(`/chain-of-custody/documents/${documentId}/chain`);
  },
  verifyReceipt(emailId) {
    // Corresponds to verify_email_receipt in routes/chain_of_custody.py
    // NOTE: Backend is GET, not POST as the old comment suggested.
    return apiClient.get(`/chain-of-custody/receipts/${emailId}/verify`);
  },
  verifyDocumentReceipt(documentId) {
    // Corresponds to verify_document_receipt in routes/chain_of_custody.py
    return apiClient.get(`/chain-of-custody/documents/${documentId}/verify`);
  },
  verifyReceiptByType(contentType, contentId) {
    // Corresponds to verify_receipt in routes/chain_of_custody.py
    return apiClient.get(`/chain-of-custody/receipts/verify`, {
      params: {
        content_type: contentType,
        content_id: contentId
      }
    });
  },
  runChainVerification() {
    // The apiClient.baseURL already includes /api/v1 prefix
    return apiClient.post('chain-of-custody/run-verification');
  },
};

// Audit and Export API
export const auditApi = {
  exportAuditTrail(emailId, format = 'pdf', accessedBy = 'web_ui') {
    return apiClient.post('/audit/export', {
      email_id: emailId,
      format: format,
      accessed_by: accessedBy
    });
  },
  generateLegalCertificate(emailId) {
    return apiClient.get(`/audit/legal-certificate/${emailId}`);
  },
  downloadAuditFile(filename) {
    return apiClient.get(`/audit/download/${filename}`, {
      responseType: 'blob'
    });
  },
  logUserAction(action, details, userId = null) {
    return apiClient.post('/audit/log', {
      action,
      details,
      user_id: userId,
      timestamp: new Date().toISOString()
    });
  }
};

// Key Management API
export const keyManagementApi = {
  getStatus(tenantId) {
    return apiClient.get(`/keys/status/${tenantId}`);
  },
  registerKey(keyData) {
    return apiClient.post('keys/register', keyData);
  },
  rotateKey(keyData) {
    return apiClient.post('keys/rotate', keyData);
  },
  enableEncryption(tenantId) {
    return apiClient.post(`keys/enable/${tenantId}`);
  },
  disableEncryption(tenantId) {
    return apiClient.post(`keys/disable/${tenantId}`);
  }
};

// Documents API
export const documentsApi = {
  getDocuments(params) {
    return apiClient.get('/documents', { params });
  },
  getDocument(id) {
    return apiClient.get(`/documents/${id}`);
  },
  uploadDocument(file, metadata = {}) {
    const formData = new FormData();
    formData.append('file', file);
    Object.keys(metadata).forEach(key => {
      formData.append(key, metadata[key]);
    });
    return apiClient.post('/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
  },
  deleteDocument(id) {
    return apiClient.delete(`/documents/${id}`);
  },
  updateDocumentStatus(id, status) {
    return apiClient.patch(`/documents/${id}/status`, { archival_status: status });
  },
  getDocumentStats() {
    return apiClient.get('/documents/stats/summary');
  },
  searchDocuments(query, filters = {}) {
    return apiClient.post('/documents/search', { query, ...filters });
  },
  advancedSearch(params) {
    return apiClient.get('/search/advanced', { params });
  },
  getDocumentsByType() {
    return apiClient.get('/documents/stats/by-type');
  },
  getDocumentsApproachingExpiration(days = 90) {
    return apiClient.get(`/documents/approaching-expiration?days=${days}`);
  },
  previewDocument(id) {
    // Use blob to handle binary responses (PDFs, images) properly
    // Add cache-busting parameter to prevent browser caching
    const cacheBuster = Date.now();
    return apiClient.get(`/documents/${id}/preview?_t=${cacheBuster}`, {
      responseType: 'blob'
    });
  },
  downloadDocument(id) {
    return apiClient.get(`/documents/${id}/download`, {
      responseType: 'blob'
    });
  }
};

// Integrations API
export const integrationsApi = {
  importEmlFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    return apiClient.post('integrations/import/eml', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
  },
  importEmlBatch(files) {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });
    return apiClient.post('integrations/import/eml/batch', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
  }
};

// External Audit Logs API
export const externalAuditLogsApi = {
  // Source Management
  getSources() {
    return apiClient.get('/external-audit-logs/sources');
  },
  createSource(sourceConfig) {
    return apiClient.post('/external-audit-logs/sources', sourceConfig);
  },
  updateSource(sourceSystem, sourceConfig) {
    return apiClient.put(`/external-audit-logs/sources/${sourceSystem}`, sourceConfig);
  },
  getSource(sourceSystem) {
    return apiClient.get(`/external-audit-logs/sources/${sourceSystem}`);
  },
  testConnection(sourceSystem) {
    return apiClient.get(`/external-audit-logs/test-connection/${sourceSystem}`);
  },
  
  // Collection Management
  collectLogs(sourceSystem, jobType = 'manual') {
    return apiClient.post('/external-audit-logs/collect', {
      source_system: sourceSystem,
      job_type: jobType
    });
  },
  getJobs() {
    return apiClient.get('/external-audit-logs/jobs');
  },
  getStats(sourceSystem = null, days = 30) {
    const params = { days };
    if (sourceSystem) params.source_system = sourceSystem;
    return apiClient.get('/external-audit-logs/stats', { params });
  },
  
  // Search and Analytics
  searchLogs(searchParams) {
    return apiClient.post('/external-audit-logs/search', searchParams);
  },
  getAIInsights(insightsParams) {
    return apiClient.post('/external-audit-logs/ai-insights', insightsParams);
  },
  detectAnomalies(anomalyParams) {
    return apiClient.post('/external-audit-logs/anomaly-detection', anomalyParams);
  },
  getComplianceReport(complianceParams) {
    return apiClient.post('/external-audit-logs/compliance-report', complianceParams);
  },
  getAlerts(status = null, severity = null, limit = 100) {
    const params = { limit };
    if (status) params.status = status;
    if (severity) params.severity = severity;
    return apiClient.get('/external-audit-logs/alerts', { params });
  }
};

// Audit Graph API
export const auditGraphApi = {
  buildGraph(query) {
    return apiClient.post('/audit-graph/graph', query);
  },
  getEventDetails(eventId) {
    return apiClient.get(`/audit-graph/graph/event/${eventId}`);
  },
  getGraphReadyEvents(params = {}) {
    return apiClient.get('/audit-graph/graph/events', { params });
  },
  getGraphStats(days = 30) {
    return apiClient.get(`/audit-graph/graph/stats?days=${days}`);
  }
};

// Export the configured axios client
export { apiClient };

export default {
  emails: emailsApi,
  documents: documentsApi,
  retention: retentionApi,
  legalHold: legalHoldApi,
  custody: custodyApi,
  audit: auditApi,
  auditGraph: auditGraphApi,
  dashboard: dashboardApi,
  integrations: integrationsApi,
  keyManagement: keyManagementApi,
  acceptedDomains: acceptedDomainsApi,
  externalAuditLogs: externalAuditLogsApi
};
