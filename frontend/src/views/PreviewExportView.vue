<template>
  <div class="preview-export-view">
    <h1>Результаты предобработки</h1>
    
    <el-alert
      v-if="!resultId"
      title="Нет доступных результатов"
      type="warning"
      description="Для доступа к этой странице необходимо сначала выполнить предобработку данных"
      show-icon
      :closable="false"
    >
      <template #default>
        <el-button type="primary" size="small" @click="goToPreprocessing">
          К выбору методов предобработки
        </el-button>
      </template>
    </el-alert>
    
    <template v-if="resultId">
      <!-- Индикатор прогресса обработки -->
      <el-card v-if="processingStatus === 'processing'" class="processing-card">
        <div class="processing-indicator">
          <el-progress 
            type="circle" 
            :percentage="processingProgress.percent || 0" 
            :status="processingProgress.percent < 100 ? 'exception' : 'success'"
          ></el-progress>
          <h3>{{ getProcessingStageTitle(processingProgress.stage) }}</h3>
          <p v-if="processingProgress.method_name">
            Выполняется: {{ processingProgress.method_name }}
          </p>
          <p>Это может занять некоторое время в зависимости от размера данных и выбранных методов.</p>
          <el-button type="primary" plain @click="checkStatus">
            Обновить статус
          </el-button>
        </div>
      </el-card>
      
      <!-- Сообщение об ошибке -->
      <el-card v-else-if="processingStatus === 'error'" class="error-card">
        <div class="error-message">
          <i class="el-icon-error" style="font-size: 48px; color: #F56C6C;"></i>
          <h3>Произошла ошибка при обработке данных</h3>
          <p>{{ errorMessage }}</p>
          <el-button type="primary" @click="goToPreprocessing">
            Вернуться к настройке предобработки
          </el-button>
        </div>
      </el-card>
      
      <!-- Результаты предобработки -->
      <div v-else-if="processingStatus === 'completed' && resultMetadata" class="result-container">
        <el-card class="result-summary">
          <template #header>
            <div class="card-header">
              <span>Сводка результатов предобработки</span>
            </div>
          </template>
          
          <el-descriptions :column="2" border>
            <el-descriptions-item label="Количество строк">
              {{ resultMetadata.row_count }}
            </el-descriptions-item>
            <el-descriptions-item label="Количество столбцов">
              {{ resultMetadata.column_count }}
            </el-descriptions-item>
            <el-descriptions-item label="ID набора данных">
              {{ resultMetadata.dataset_id }}
            </el-descriptions-item>
            <el-descriptions-item label="ID результата">
              {{ resultMetadata.result_id }}
            </el-descriptions-item>
          </el-descriptions>
          
          <h3>Применённые методы предобработки</h3>
          
          <el-table :data="appliedMethods" style="width: 100%" border>
            <el-table-column prop="name" label="Метод"></el-table-column>
            <el-table-column label="Параметры">
              <template #default="scope">
                <div v-for="(value, key) in scope.row.parameters" :key="key">
                  <strong>{{ formatParameterName(key) }}:</strong> {{ formatParameterValue(key, value) }}
                </div>
              </template>
            </el-table-column>
          </el-table>
          
          <h3>Столбцы в обработанных данных</h3>
          <el-tag
            v-for="column in resultMetadata.columns"
            :key="column"
            :type="isNewColumn(column) ? 'success' : ''"
            class="column-tag"
          >
            {{ column }}
          </el-tag>
        </el-card>
        
        <!-- Добавляем компонент для управления метаданными масштабирования -->
        <el-card v-if="hasScalingParams" class="metadata-card">
          <template #header>
            <div class="card-header">
              <span>Управление параметрами масштабирования</span>
            </div>
          </template>
          
          <ScalingMetadataManager
            :result-id="resultId"
            :has-scaling-params="hasScalingParams"
            :scaling-method-name="scalingMethodName"
            :available-columns="resultMetadata.columns || []"
            @metadata-updated="onMetadataUpdated"
            @inverse-scaling-applied="onInverseScalingApplied"
          />
        </el-card>
        
        <el-card class="data-preview">
          <template #header>
            <div class="card-header">
              <span>Предпросмотр данных</span>
              <el-button type="primary" @click="loadDataPreview" :loading="isPreviewLoading">
                Загрузить предпросмотр
              </el-button>
            </div>
          </template>
          <div v-if="isPreviewLoading" class="preview-loading">
            <el-spinner></el-spinner>
            <p>Загрузка данных...</p>
          </div>
          <div v-else-if="previewError" class="preview-error">
            <el-alert type="error" :closable="false">
              {{ previewError }}
            </el-alert>
          </div>
          <div v-else-if="previewData && previewData.length > 0" class="preview-content">
            <el-table
              :data="previewData"
              border
              style="width: 100%"
              max-height="400"
            >
              <el-table-column
                v-for="column in resultMetadata.columns"
                :key="column"
                :prop="column"
                :label="column"
                min-width="150"
              />
            </el-table>
          </div>
          <div v-else class="no-preview">
            <p>Нажмите кнопку "Загрузить предпросмотр" для просмотра обработанных данных</p>
          </div>
        </el-card>
        
        <el-card class="export-card">
          <template #header>
            <div class="card-header">
              <span>Экспорт обработанных данных</span>
            </div>
          </template>
          <el-form label-width="200px">
            <el-form-item label="Формат экспорта:">
              <el-radio-group v-model="exportFormat">
                <el-radio label="csv">CSV</el-radio>
                <el-radio label="excel">Excel</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="Параметры CSV:" v-if="exportFormat === 'csv'">
              <el-select v-model="csvDelimiter" placeholder="Разделитель" style="width: 150px">
                <el-option label="Запятая (,)" value="," />
                <el-option label="Точка с запятой (;)" value=";" />
                <el-option label="Табуляция" value="\t" />
              </el-select>
            </el-form-item>
          </el-form>
          <el-button 
            type="success" 
            icon="el-icon-download" 
            @click="exportData"
            :loading="isExporting"
          >
            Экспортировать данные
          </el-button>
        </el-card>
        
        <div class="navigation-buttons">
          <el-button @click="goToPreprocessing">Назад</el-button>
          <el-button type="primary" @click="finishProcess">Завершить</el-button>
        </div>
      </div>
    </template>
  </div>
</template>

<script>
import { defineComponent, ref, computed, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import { useStore } from 'vuex';
import { ElMessage } from 'element-plus';
import preprocessingService from '@/services/preprocessingService';
import datasetService from '@/services/datasetService';
import ScalingMetadataManager from '@/components/ScalingMetadataManager.vue';

export default defineComponent({
  name: 'PreviewExportView',
  components: {
    ScalingMetadataManager
  },
  setup() {
    const router = useRouter();
    const store = useStore();
    
    // Состояние результата
    const resultId = computed(() => store.state.resultId);
    const processingStatus = ref('processing'); // processing, error, completed
    const errorMessage = ref('');
    const resultMetadata = ref(null);
    
    // Информация о прогрессе обработки
    const processingProgress = ref({
      percent: 0,
      stage: 'preparing',
      method_name: null
    });
    
    // Добавляем переменную для хранения интервала
    const statusInterval = ref(null);
    
    // Состояние предпросмотра
    const isPreviewLoading = ref(false);
    const previewData = ref(null);
    const previewError = ref(null);
    const originalColumns = ref([]);
    
    // Состояние экспорта
    const exportFormat = ref('csv');
    const csvDelimiter = ref(',');
    const isExporting = ref(false);
    
    // Запуск периодического опроса статуса
    const startStatusPolling = () => {
      // Проверяем статус каждые 3 секунды
      statusInterval.value = setInterval(() => {
        checkStatus();
      }, 3000);
    };
    
    // Останавливаем опрос при размонтировании компонента
    onUnmounted(() => {
      if (statusInterval.value) {
        clearInterval(statusInterval.value);
      }
    });
    
    // Получение статуса обработки
    onMounted(() => {
      if (resultId.value) {
        checkStatus();
        startStatusPolling(); // Запускаем автоматический опрос
      }
    });
    
    // Проверка статуса обработки
    const checkStatus = async () => {
      if (!resultId.value) return;
      
      try {
        const response = await preprocessingService.getPreprocessingStatus(resultId.value);
        
        if (response.data.status === 'error') {
          processingStatus.value = 'error';
          errorMessage.value = response.data.message;
          // Останавливаем опрос при ошибке
          if (statusInterval.value) {
            clearInterval(statusInterval.value);
          }
        } else if (response.data.status === 'completed') {
          processingStatus.value = 'completed';
          resultMetadata.value = response.data.metadata;
          // Останавливаем опрос при завершении
          if (statusInterval.value) {
            clearInterval(statusInterval.value);
          }
          // Получение оригинальных столбцов из метаданных датасета
          try {
            const datasetResponse = await datasetService.getDatasetInfo(resultMetadata.value.dataset_id);
            originalColumns.value = datasetResponse.data.columns.map(col => col.name);
          } catch (error) {
            console.error('Ошибка получения исходных столбцов:', error);
          }
        } else {
          processingStatus.value = 'processing';
          // Обновляем информацию о прогрессе, если она доступна
          if (response.data.progress) {
            processingProgress.value = response.data.progress;
          }
        }
      } catch (error) {
        console.error('Ошибка проверки статуса:', error);
        processingStatus.value = 'error';
        errorMessage.value = 'Не удалось получить статус обработки';
        // Останавливаем опрос при ошибке
        if (statusInterval.value) {
          clearInterval(statusInterval.value);
        }
      }
    };
    
    // Загрузка предпросмотра данных
    const loadDataPreview = async () => {
      if (!resultId.value) return;
      
      isPreviewLoading.value = true;
      previewError.value = null;
      
      try {
        // Здесь должен быть запрос для получения превью данных
        // Пример заглушки:
        const response = await preprocessingService.getDataPreview(resultId.value);
        previewData.value = response.data.preview;
      } catch (error) {
        console.error('Ошибка загрузки предпросмотра:', error);
        previewError.value = 'Не удалось загрузить предпросмотр данных';
      } finally {
        isPreviewLoading.value = false;
      }
    };
    
    // Экспорт данных
    const exportData = async () => {
      if (!resultId.value) return;
      
      isExporting.value = true;
      
      try {
        // Запрос для экспорта данных с учетом выбранного формата
        const response = await preprocessingService.exportDataset(resultId.value, exportFormat.value);
        // Создание ссылки для скачивания
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        // Устанавливаем правильное расширение файла
        const fileExtension = exportFormat.value === 'excel' ? 'xlsx' : 'csv';
        link.setAttribute('download', `processed_data_${resultId.value}.${fileExtension}`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        ElMessage({
          message: 'Данные успешно экспортированы',
          type: 'success'
        });
      } catch (error) {
        console.error('Ошибка экспорта данных:', error);
        ElMessage.error('Не удалось экспортировать данные');
      } finally {
        isExporting.value = false;
      }
    };
    
    // Проверка, является ли столбец новым
    const isNewColumn = (column) => {
      return originalColumns.value.length > 0 && !originalColumns.value.includes(column);
    };
    
    // Применённые методы
    const appliedMethods = computed(() => {
      if (!resultMetadata.value || !resultMetadata.value.config || !resultMetadata.value.config.methods) {
        return [];
      }
      return resultMetadata.value.config.methods.map(method => {
        // Получение информации о методе из метаданных
        return {
          name: getMethodName(method.method_id),
          parameters: method.parameters || {}
        };
      });
    });
    
    // Получение названия метода
    const getMethodName = (methodId) => {
      const methodNames = {
        'missing_values': 'Обработка пропущенных значений',
        'outliers': 'Обработка выбросов',
        'standardization': 'Стандартизация данных',
        'categorical_encoding': 'Кодирование категориальных переменных',
        'pca': 'Снижение размерности (PCA)',
        'time_series_analysis': 'Анализ временных рядов',
        'lagging': 'Лагирование переменных',
        'rolling_statistics': 'Скользящие статистики',
        'date_components': 'Извлечение компонентов даты'
      };
      return methodNames[methodId] || methodId;
    };
    
    // Форматирование названия параметра
    const formatParameterName = (paramName) => {
      const paramNames = {
        'strategy': 'Стратегия',
        'columns': 'Столбцы',
        'threshold': 'Порог',
        'target_column': 'Целевая переменная',
        'lag_periods': 'Периоды лагирования',
        'exog_columns': 'Экзогенные переменные',
        'window_size': 'Размер окна',
        'statistics': 'Статистики',
        'n_components': 'Количество компонент',
        'components': 'Компоненты даты'
      };
      return paramNames[paramName] || paramName;
    };
    
    // Форматирование значения параметра
    const formatParameterValue = (paramName, value) => {
      if (paramName === 'strategy') {
        const strategyLabels = {
          'mean': 'Заполнить средним',
          'median': 'Заполнить медианой',
          'mode': 'Заполнить модой',
          'drop_rows': 'Удалить строки',
          'zscore': 'Z-оценка',
          'iqr': 'Межквартильный размах',
          'standard': 'Стандартизация',
          'minmax': 'Мин-макс нормализация',
          'onehot': 'One-Hot кодирование',
          'label': 'Label кодирование'
        };
        return strategyLabels[value] || value;
      }
      // Добавляем форматирование для компонентов даты
      if (paramName === 'components') {
        if (Array.isArray(value)) {
          // Преобразуем идентификаторы компонентов в удобочитаемые названия
          const componentLabels = {
            'year': 'Год',
            'month': 'Месяц',
            'quarter': 'Квартал',
            'day_of_week': 'День недели',
            'day_of_month': 'День месяца',
            'day_of_year': 'День года',
            'week_of_year': 'Неделя года',
          };
          return value.map(component => componentLabels[component] || component).join(', ');
        }
      }
      if (Array.isArray(value)) {
        return value.length > 0 ? value.join(', ') : 'Не выбрано';
      }
      return value === null || value === undefined ? 'Не указано' : value;
    };
    
    // Получение заголовка для текущего этапа обработки
    const getProcessingStageTitle = (stage) => {
      const stageTitles = {
        'preparing': 'Подготовка к обработке...',
        'loading': 'Загрузка данных...',
        'preprocessing': 'Инициализация предобработки...',
        'processing_method': 'Выполнение предобработки...',
        'saving': 'Сохранение результатов...',
        'completed': 'Обработка завершена',
        'error': 'Ошибка при обработке'
      };
      return stageTitles[stage] || 'Выполняется обработка данных...';
    };
    
    // Навигация
    const goToPreprocessing = () => {
      router.push('/preprocessing');
    };
    
    const finishProcess = () => {
      // Очистка состояния
      store.commit('clearPreprocessingState');
      router.push('/');
    };
    
    // Проверка наличия параметров масштабирования
    const hasScalingParams = computed(() => {
      // Проверяем прямое наличие scaling_params в метаданных
      if (resultMetadata.value && resultMetadata.value.scaling_params) {
        return true;
      }
      // Проверяем наличие методов масштабирования в примененных методах
      if (resultMetadata.value && resultMetadata.value.config && resultMetadata.value.config.methods) {
        return resultMetadata.value.config.methods.some(method => 
          ['standardization', 'minmax_scaling', 'normalization'].includes(method.method_id)
        );
      }
      return false;
    });
    
    // Получение названия метода масштабирования
    const scalingMethodName = computed(() => {
      if (!resultMetadata.value || !resultMetadata.value.config || !resultMetadata.value.config.methods) {
        return '';
      }
      const scalingMethod = resultMetadata.value.config.methods.find(method => 
        ['standardization', 'minmax_scaling', 'normalization'].includes(method.method_id)
      );
      if (!scalingMethod) return '';
      
      const methodNames = {
        'standardization': 'Стандартизация',
        'minmax_scaling': 'Мин-макс нормализация',
        'normalization': 'Нормализация'
      };
      return methodNames[scalingMethod.method_id] || scalingMethod.method_id;
    });
    
    // Обработчик события обновления метаданных
    const onMetadataUpdated = (scalingParams) => {
      console.log('Обновление параметров масштабирования:', scalingParams);
      // Обновляем метаданные результата, добавляя информацию о масштабировании
      if (resultMetadata.value) {
        if (!resultMetadata.value.scaling_params) {
          resultMetadata.value = {
            ...resultMetadata.value,
            scaling_params: scalingParams
          };
        } else {
          resultMetadata.value.scaling_params = scalingParams;
        }
        // Важно! Сохраняем параметры масштабирования в хранилище
        store.dispatch('setScalingParams', scalingParams);
      }
      // Обновляем предпросмотр данных, если он загружен
      if (previewData.value) {
        loadDataPreview();
      }
      ElMessage({
        message: 'Параметры масштабирования обновлены',
        type: 'success'
      });
    };

    // Обработчик события применения обратного масштабирования
    const onInverseScalingApplied = (data) => {
      console.log('Результат обратного масштабирования:', data);
      
      // Обновляем ID результата
      if (data && data.result_id) {
        store.dispatch('setResult', data.result_id);
        // Обновляем текущий resultId для обновления представления
        resultId.value = data.result_id;
        // Сбрасываем состояние и перезагружаем данные
        checkStatus();
      }
      
      ElMessage({
        message: 'Обратное масштабирование успешно применено. Результаты обновлены.',
        type: 'success',
        duration: 5000
      });
    };

    return {
      resultId,
      processingStatus,
      errorMessage,
      resultMetadata,
      isPreviewLoading,
      previewData,
      previewError,
      exportFormat,
      csvDelimiter,
      isExporting,
      appliedMethods,
      processingProgress,
      checkStatus,
      getProcessingStageTitle,
      loadDataPreview,
      exportData,
      isNewColumn,
      getMethodName,
      formatParameterName,
      formatParameterValue,
      goToPreprocessing,
      finishProcess,
      hasScalingParams,
      scalingMethodName,
      onMetadataUpdated,
      onInverseScalingApplied
    };
  },
});
</script>

<style scoped>
.preview-export-view {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.processing-card, .error-card {
  margin-top: 20px;
  text-align: center;
}

.metadata-card {
  margin-bottom: 20px;
}

.processing-indicator, .error-message {
  padding: 40px;
}

.result-container {
  margin-top: 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
}

.result-summary, .data-preview, .export-card {
  margin-top: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.column-tag {
  margin: 5px;
}

.preview-loading, .no-preview {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 50px;
}

.preview-error {
  padding: 20px;
}

.navigation-buttons {
  display: flex;
  justify-content: space-between;
  margin-top: 20px;
}

.export-options {
  margin-top: 20px;
  display: flex;
  justify-content: space-between;
}

.table-container {
  overflow-x: auto;
  margin-bottom: 20px;
  width: 100%;
  border-radius: 4px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.el-table {
  min-width: 800px; /* Обеспечивает минимальную ширину для горизонтальной прокрутки */
}

.el-table .cell {
  word-break: normal;
  white-space: nowrap;
}

.cell-content {
  display: inline-block;
  max-width: 300px;
  font-weight: bold;
  color: #67c23a;
  white-space: nowrap;
  text-overflow: ellipsis;
  overflow: hidden;
}
</style>