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
  
  // Add this method to handle dataset mode parameter setting
  setScalingParamsForDataset(datasetId, params) {
    return apiClient.post(`/datasets/${datasetId}/set-scaling-params`, params);
  },

  // Метод для применения обратного масштабирования к датасету
  applyInverseScalingToDataset(datasetId, data) {
    console.log('Applying inverse scaling to dataset:', datasetId, JSON.stringify(data));
    return apiClient.post(`/datasets/${datasetId}/apply-inverse-scaling`, data)
      .catch(error => {
        console.error('API Error:', error.response?.data || error.message);
        throw error;
      });
  },
  
  // Метод для применения обратного масштабирования к результату
  applyInverseScalingToResult(resultId, data) {
    console.log('Отправка запроса на обратное масштабирование результата:', resultId, data);
    return apiClient.post(`/preprocessing/apply-inverse-scaling/${resultId}`, data);
  },
  
  // Общий метод, который выбирает нужный эндпоинт в зависимости от режима
  applyInverseScaling(data) {
    const { id, mode, columns, scaling_params } = data;
    
    // Проверяем наличие необходимых данных
    if (!id || !columns || !columns.length || !scaling_params) {
      console.error('Недостаточно данных для обратного масштабирования', data);
      throw new Error('Необходимо указать ID, столбцы и параметры масштабирования');
    }
    
    const requestData = {
      columns: columns,
      scaling_params: scaling_params
    };
    
    if (mode === 'dataset') {
      return this.applyInverseScalingToDataset(id, requestData);
    } else {
      return this.applyInverseScalingToResult(id, requestData);
    }
  }
};