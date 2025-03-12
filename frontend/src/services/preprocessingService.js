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
  },
  
  // Экспорт метаданных масштабирования
  exportMetadata(resultId) {
    return apiClient.get(`/preprocessing/export-metadata/${resultId}`, {
      responseType: 'blob'
    });
  },
  
  // Импорт метаданных масштабирования
  importMetadata(resultId, file) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('result_id', resultId);
    
    return apiClient.post('/preprocessing/import-metadata', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
  },
  
  // Импорт метаданных масштабирования для датасета
  importMetadataForDataset(datasetId, file) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('dataset_id', datasetId);
    
    return apiClient.post(`/datasets/${datasetId}/import-metadata`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
  },
  
  // Установка параметров масштабирования вручную
  setScalingParams(resultId, params) {
    return apiClient.post(`/preprocessing/set-scaling-params/${resultId}`, params);
  },

  // Метод для применения обратного масштабирования к датасету
  applyInverseScalingToDataset(datasetId, data) {
    return apiClient.post(`/datasets/${datasetId}/apply-inverse-scaling`, data);
  },
  
  // Метод для применения обратного масштабирования к результату
  applyInverseScalingToResult(resultId, data) {
    return apiClient.post(`/preprocessing/apply-inverse-scaling/${resultId}`, data);
  },
  
  // Общий метод, который выбирает нужный эндпоинт в зависимости от режима
  applyInverseScaling(data) {
    const { id, mode } = data;
    if (mode === 'dataset') {
      return this.applyInverseScalingToDataset(id, data);
    } else {
      return this.applyInverseScalingToResult(id, data);
    }
  }
};