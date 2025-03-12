import apiClient from './api';

export default {
  uploadDataset(formData) {
    return apiClient.post('/datasets/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
  },
  
  getDatasetInfo(datasetId) {
    return apiClient.get(`/datasets/${datasetId}`);
  }
};