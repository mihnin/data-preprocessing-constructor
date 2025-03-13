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
  
  getDataPreview(resultId, limit = 100, offset = 0) {
    return apiClient.get(`/preprocessing/data/${resultId}?limit=${limit}&offset=${offset}`);
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
    console.log(`[preprocessingService] Импорт метаданных для результата ${resultId}`);
    
    if (!resultId) {
      return Promise.reject(new Error('ID результата не указан'));
    }
    
    if (!file) {
      return Promise.reject(new Error('Файл метаданных не указан'));
    }
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('result_id', resultId);
    
    return apiClient.post('/preprocessing/import-metadata', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    .then(response => {
      console.log(`[preprocessingService] Успешный импорт метаданных для результата:`, response.data);
      return response;
    })
    .catch(error => {
      console.error(`[preprocessingService] Ошибка импорта метаданных:`, 
        error.response?.data || error.message);
      throw error;
    });
  },
  
  // Импорт метаданных масштабирования для датасета
  importMetadataForDataset(datasetId, file) {
    console.log(`[preprocessingService] Импорт метаданных для датасета ${datasetId}`);
    
    if (!datasetId) {
      return Promise.reject(new Error('ID датасета не указан'));
    }
    
    if (!file) {
      return Promise.reject(new Error('Файл метаданных не указан'));
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    return apiClient.post(`/datasets/${datasetId}/import-metadata`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    .then(response => {
      console.log(`[preprocessingService] Успешный импорт метаданных для датасета:`, response.data);
      return response;
    })
    .catch(error => {
      console.error(`[preprocessingService] Ошибка импорта метаданных для датасета:`, 
        error.response?.data || error.message);
      throw error;
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
    
    // Подробная диагностика запроса
    console.log("[preprocessingService] Запрос на обратное масштабирование:");
    console.log("ID:", id);
    console.log("Режим:", mode);
    console.log("Столбцы:", columns);
    console.log("Параметры масштабирования:", JSON.stringify(scaling_params, null, 2));
    
    // Валидация входных данных
    if (!id) {
      console.error("[preprocessingService] Отсутствует ID для обратного масштабирования");
      return Promise.reject(new Error('Необходимо указать ID набора данных или результата'));
    }
    
    if (!columns || !columns.length) {
      console.error("[preprocessingService] Не выбраны столбцы для обратного масштабирования");
      return Promise.reject(new Error('Необходимо указать столбцы для масштабирования'));
    }
    
    // Проверяем наличие параметров масштабирования
    if (!scaling_params || Object.keys(scaling_params).length === 0) {
      console.error("[preprocessingService] Отсутствуют параметры масштабирования", data);
      return Promise.reject(new Error('Необходимо указать параметры масштабирования'));
    }
    
    // Готовим данные запроса
    const requestData = {
      columns: columns,
      scaling_params: scaling_params
    };
    
    console.log(`[preprocessingService] Отправка запроса на обратное масштабирование (${mode}:${id}):`, 
      JSON.stringify(requestData, null, 2));
    
    // Отправляем запрос в зависимости от режима
    let endpoint;
    if (mode === 'dataset') {
      endpoint = `/datasets/${id}/apply-inverse-scaling`;
    } else {
      endpoint = `/preprocessing/apply-inverse-scaling/${id}`;
    }
    
    // Используем низкоуровневый метод apiClient.post с обработкой ошибок
    return apiClient.post(endpoint, requestData)
      .then(response => {
        console.log(`[preprocessingService] Получен ответ от API:`, response.data);
        return response;
      })
      .catch(error => {
        console.error(`[preprocessingService] Ошибка обратного масштабирования:`, 
          error.response?.data || error.message);
        
        // Создаем более информативное сообщение об ошибке
        let message = 'Ошибка обратного масштабирования';
        if (error.response?.data?.detail) {
          message = error.response.data.detail;
        } else if (error.message) {
          message = error.message;
        }
        
        // Создаем новый объект ошибки с подробностями
        const enhancedError = new Error(message);
        enhancedError.originalError = error;
        enhancedError.details = error.response?.data;
        throw enhancedError;
      });
  }
};