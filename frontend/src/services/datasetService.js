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
  },

  // Method for setting target column
  setTargetColumn(datasetId, targetColumn) {
    return apiClient.post(`/datasets/${datasetId}/set-target`, {
      target_column: targetColumn
    });
  }
};