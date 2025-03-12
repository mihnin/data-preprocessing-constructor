import apiClient from './api';

export default {
  getPreprocessingMethods() {
    return apiClient.get('/preprocessing/methods');
  },
  
  previewPreprocessing(config) {
    return apiClient.post('/preprocessing/preview', config);
  },
  
  executePreprocessing(config) {
    return apiClient.post('/preprocessing/execute', config);
  },
  
  getPreprocessingStatus(resultId) {
    return apiClient.get(`/preprocessing/status/${resultId}`);
  },
  
  getDataPreview(resultId) {
    return apiClient.get(`/preprocessing/data/${resultId}?limit=100`);
  },
  
  exportDataset(resultId, format = 'csv') {
    return apiClient.get(`/datasets/export/${resultId}?format=${format}`, {
      responseType: 'blob'
    });
  }
};