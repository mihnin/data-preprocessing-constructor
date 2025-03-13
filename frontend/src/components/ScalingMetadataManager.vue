<template>
  <div class="scaling-metadata-manager">
    <el-divider>Управление параметрами масштабирования</el-divider>
    
    <el-tabs v-model="activeTab">
      <!-- Вкладка файловых операций (объединенный импорт и экспорт) -->
      <el-tab-pane label="Импорт/Экспорт параметров" name="file-operations">
        <div class="tab-content">
          <!-- Экспорт метаданных -->
          <div class="section">
            <h4>Экспорт метаданных</h4>
            <el-alert
              v-if="!hasScalingParams"
              type="info"
              show-icon
              :closable="false"
            >
              <template #title>
                Для этого набора данных не найдены параметры масштабирования.
              </template>
            </el-alert>
            
            <template v-else>
              <p>
                Параметры масштабирования ({{ scalingMethodName }}) можно экспортировать в файл JSON
                для последующего использования при обратном преобразовании.
              </p>
              
              <el-button 
                type="primary" 
                @click="exportMetadata" 
                :disabled="isExporting"
              >
                <i class="el-icon-download" v-if="!isExporting"></i>
                <i class="el-icon-loading" v-else></i>
                {{ isExporting ? 'Экспорт...' : 'Экспортировать метаданные' }}
              </el-button>
            </template>
          </div>
          
          <!-- Импорт метаданных -->
          <div class="section">
            <h4>Импорт метаданных</h4>
            <p>
              Загрузите файл метаданных масштабирования (JSON), сохраненный ранее.
            </p>
            
            <el-upload
              class="metadata-upload"
              action="#"
              :auto-upload="false"
              :limit="1"
              :on-change="handleFileChange"
              :file-list="fileList"
            >
              <el-button type="primary">Выбрать файл метаданных</el-button>
              <template #tip>
                <div class="el-upload__tip">Только файлы JSON с параметрами масштабирования</div>
              </template>
            </el-upload>
            
            <el-button 
              type="success" 
              @click="importMetadata" 
              :disabled="!selectedFile || isImporting"
              style="margin-top: 15px;"
            >
              <i class="el-icon-upload2" v-if="!isImporting"></i>
              <i class="el-icon-loading" v-else></i>
              {{ isImporting ? 'Импорт...' : 'Импортировать метаданные' }}
            </el-button>
          </div>
        </div>
      </el-tab-pane>
      
      <!-- Вкладка ручного ввода параметров -->
      <el-tab-pane label="Указать параметры вручную" name="manual">
        <p>
          Введите параметры масштабирования вручную для каждого столбца.
        </p>
        
        <el-form label-width="200px" :model="manualParams">
          <el-form-item label="Метод масштабирования:">
            <el-select v-model="manualParams.method" placeholder="Выберите метод">
              <el-option label="Стандартизация (StandardScaler)" value="standard" />
              <el-option label="Нормализация (MinMaxScaler)" value="minmax" />
            </el-select>
          </el-form-item>
          
          <el-form-item label="Выберите столбцы:">
            <el-select 
              v-model="manualParams.columns" 
              multiple
              placeholder="Выберите столбцы для масштабирования"
              filterable
            >
              <el-option
                v-for="column in availableColumns"
                :key="column"
                :label="column"
                :value="column"
              />
            </el-select>
          </el-form-item>
          
          <div v-if="manualParams.columns.length > 0">
            <h4>Параметры для выбранных столбцов:</h4>
            
            <div v-for="column in manualParams.columns" :key="column" class="column-params">
              <h5>{{ column }}</h5>
              
              <template v-if="manualParams.method === 'standard'">
                <el-form-item :label="'Среднее (mean) для ' + column">
                  <el-input-number 
                    v-model="manualParams.parameters[column].mean" 
                    :precision="4"
                    :step="0.1"
                  />
                </el-form-item>
                
                <el-form-item :label="'Стд. отклонение (std) для ' + column">
                  <el-input-number 
                    v-model="manualParams.parameters[column].std" 
                    :precision="4"
                    :step="0.1"
                    :min="0.0001"
                  />
                </el-form-item>
              </template>
              
              <template v-else-if="manualParams.method === 'minmax'">
                <el-form-item :label="'Минимум (min) для ' + column">
                  <el-input-number 
                    v-model="manualParams.parameters[column].min" 
                    :precision="4"
                    :step="0.1"
                  />
                </el-form-item>
                
                <el-form-item :label="'Максимум (max) для ' + column">
                  <el-input-number 
                    v-model="manualParams.parameters[column].max" 
                    :precision="4"
                    :step="0.1"
                  />
                </el-form-item>
              </template>
            </div>
          </div>
          
          <el-form-item>
            <el-button 
              type="primary" 
              @click="saveManualParams"
              :disabled="!canSaveManualParams || isSaving"
            >
              <i class="el-icon-check" v-if="!isSaving"></i>
              <i class="el-icon-loading" v-else></i>
              {{ isSaving ? 'Сохранение...' : 'Сохранить параметры' }}
            </el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>
      
      <!-- Вкладка для обратного масштабирования -->
      <el-tab-pane label="Применить обратное преобразование" name="inverse" v-if="hasScalingParams">
        <div class="inverse-scaling-info">
          <el-alert
            type="info"
            :closable="false"
            show-icon
          >
            <template #title>
              Состояние метаданных масштабирования
            </template>
            <template #default>
              <div class="metadata-status">
                <p><strong>Метод масштабирования:</strong> {{ scalingMethodName || 'Не определен' }}</p>
                <p><strong>Доступные столбцы:</strong> 
                  <span v-if="getScaledColumns().length > 0">
                    {{ getScaledColumns().join(', ') }}
                  </span>
                  <span v-else>Столбцы не найдены</span>
                </p>
              </div>
            </template>
          </el-alert>
          
          <el-alert
            type="info"
            :closable="false"
            show-icon
            style="margin-top: 10px;"
          >
            <template #title>
              Применение обратного масштабирования
            </template>
            <template #default>
              <p>
                Данная функция позволяет вернуть масштабированным данным их исходные значения.
                Выберите столбцы, к которым нужно применить обратное масштабирование ({{ scalingMethodName }}).
              </p>
            </template>
          </el-alert>
        </div>
        
        <el-form label-width="200px" style="margin-top: 20px;">
          <el-form-item label="Столбцы для преобразования:">
            <el-select 
              v-model="inverseScalingColumns" 
              multiple
              placeholder="Выберите столбцы"
              filterable
            >
              <el-option
                v-for="column in getScaledColumns()"
                :key="column"
                :label="column"
                :value="column"
              />
            </el-select>
            <div class="selection-info" v-if="getScaledColumns().length > 0">
              <small>Выбрано {{ inverseScalingColumns.length }} из {{ getScaledColumns().length }} доступных столбцов</small>
              <el-button 
                type="text" 
                @click="inverseScalingColumns = getScaledColumns()"
                v-if="inverseScalingColumns.length < getScaledColumns().length"
              >
                Выбрать все
              </el-button>
              <el-button 
                type="text" 
                @click="inverseScalingColumns = []"
                v-if="inverseScalingColumns.length > 0"
              >
                Очистить выбор
              </el-button>
            </div>
          </el-form-item>
          
          <el-form-item>
            <el-button 
              type="primary" 
              @click="applyInverseScaling"
              :disabled="inverseScalingColumns.length === 0 || isApplying"
            >
              <i class="el-icon-refresh" v-if="!isApplying"></i>
              <i class="el-icon-loading" v-else></i>
              {{ isApplying ? 'Применение...' : 'Применить обратное масштабирование' }}
            </el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script>
import { ref, reactive, computed, watch } from 'vue';
import { ElMessage } from 'element-plus';
import preprocessingService from '@/services/preprocessingService';

export default {
  name: 'ScalingMetadataManager',
  
  props: {
    resultId: {
      type: String,
      default: null
    },
    hasScalingParams: {
      type: Boolean,
      default: false
    },
    scalingMethodName: {
      type: String,
      default: ''
    },
    availableColumns: {
      type: Array,
      default: () => []
    },
    mode: {
      type: String,
      default: 'result', // 'result' или 'dataset'
      validator: (value) => ['result', 'dataset'].includes(value)
    },
    datasetId: {
      type: String,
      default: null
    },
    scalingParams: {
      type: Object,
      default: () => ({})
    },
    // Флаг для использования в представлении предобработки или предпросмотра
    inPreprocessingView: {
      type: Boolean,
      default: false
    }
  },
  
  emits: ['update:scaling-params', 'metadata-updated', 'inverse-scaling-applied'],
  
  setup(props, { emit }) {
    // Активная вкладка
    const activeTab = ref(props.inPreprocessingView ? 'inverse' : 'file-operations');
    
    // Состояние экспорта
    const isExporting = ref(false);
    
    // Состояние импорта
    const isImporting = ref(false);
    const fileList = ref([]);
    const selectedFile = ref(null);
    
    // Состояние ручного ввода
    const isSaving = ref(false);
    const manualParams = reactive({
      method: 'standard',
      columns: [],
      parameters: {}
    });
    
    // Состояние обратного масштабирования
    const inverseScalingColumns = ref([]);
    const isApplying = ref(false);
    
    // Отслеживание обновления столбцов
    watch(() => manualParams.columns, (newColumns, oldColumns) => {
      // Определяем новые добавленные столбцы
      const addedColumns = newColumns.filter(col => !oldColumns.includes(col));
      
      // Для каждого нового столбца инициализируем параметры
      addedColumns.forEach(column => {
        if (!manualParams.parameters[column]) {
          if (manualParams.method === 'standard') {
            manualParams.parameters[column] = {
              mean: 0,
              std: 1
            };
          } else if (manualParams.method === 'minmax') {
            manualParams.parameters[column] = {
              min: 0,
              max: 1
            };
          }
        }
      });
      
      // Удаляем параметры для неактивных столбцов
      Object.keys(manualParams.parameters).forEach(column => {
        if (!newColumns.includes(column)) {
          delete manualParams.parameters[column];
        }
      });
    });
    
    // Отслеживание изменения метода
    watch(() => manualParams.method, (newMethod) => {
      manualParams.columns.forEach(column => {
        if (newMethod === 'standard') {
          manualParams.parameters[column] = {
            mean: 0,
            std: 1
          };
        } else if (newMethod === 'minmax') {
          manualParams.parameters[column] = {
            min: 0,
            max: 1
          };
        }
      });
    });
    
    // Проверка возможности сохранения параметров
    const canSaveManualParams = computed(() => {
      if (manualParams.columns.length === 0) return false;
      
      // Проверка заполнения всех параметров
      for (const column of manualParams.columns) {
        if (!manualParams.parameters[column]) return false;
        
        if (manualParams.method === 'standard') {
          if (manualParams.parameters[column].mean === undefined || 
              manualParams.parameters[column].std === undefined) {
            return false;
          }
          
          // Стандартное отклонение не может быть нулевым или отрицательным
          if (manualParams.parameters[column].std <= 0) {
            return false;
          }
        } else if (manualParams.method === 'minmax') {
          if (manualParams.parameters[column].min === undefined || 
              manualParams.parameters[column].max === undefined) {
            return false;
          }
          
          // Минимум должен быть меньше максимума
          if (manualParams.parameters[column].min >= manualParams.parameters[column].max) {
            return false;
          }
        }
      }
      
      return true;
    });
    
    // Функция обработки выбора файла
    const handleFileChange = (file) => {
      selectedFile.value = file.raw;
      fileList.value = [file];
    };
    
    // Функция экспорта метаданных
    const exportMetadata = async () => {
      const id = props.mode === 'dataset' ? props.datasetId : props.resultId;
      if (!id) {
        ElMessage.warning('Необходим идентификатор данных для экспорта метаданных');
        return;
      }
      
      try {
        isExporting.value = true;
        
        await preprocessingService.exportMetadata(id);
        
        ElMessage.success('Метаданные масштабирования успешно экспортированы');
      } catch (error) {
        console.error('Ошибка экспорта метаданных:', error);
        ElMessage.error(error.response?.data?.detail || 'Не удалось экспортировать метаданные');
      } finally {
        isExporting.value = false;
      }
    };
    
    // Функция импорта метаданных
    const importMetadata = async () => {
      // Проверяем наличие идентификатора в зависимости от режима
      const id = props.mode === 'dataset' ? props.datasetId : props.resultId;
      if (!id || !selectedFile.value) return;
      
      isImporting.value = true;
      
      try {
        console.log("Импорт файла метаданных:", selectedFile.value.name);
        
        // Создаем FormData с соответствующим ID в зависимости от режима
        let response;
        if (props.mode === 'dataset') {
          if (!props.datasetId) {
            throw new Error("ID датасета не указан");
          }
          response = await preprocessingService.importMetadataForDataset(props.datasetId, selectedFile.value);
        } else {
          if (!props.resultId) {
            throw new Error("ID результата не указан");
          }
          response = await preprocessingService.importMetadata(props.resultId, selectedFile.value);
        }
        
        // Детальное логирование ответа для отладки
        console.log("[ScalingMetadataManager] Ответ сервера при импорте:", response.data);
        
        const scalingParams = response.data.scaling_params;
        
        // Проверяем наличие параметров масштабирования в ответе
        if (!scalingParams) {
          console.error("[ScalingMetadataManager] Отсутствуют параметры масштабирования в ответе:", response.data);
          throw new Error("Сервер вернул ответ без параметров масштабирования");
        }
        
        ElMessage({
          message: 'Метаданные успешно импортированы',
          type: 'success'
        });
        
        console.log("[ScalingMetadataManager] Импортированы параметры:", JSON.stringify(scalingParams, null, 2));
        
        // Оповещаем родительский компонент об обновлении метаданных
        emit('metadata-updated', scalingParams);
        fileList.value = [];
        selectedFile.value = null;
        
        // После успешного импорта активируем вкладку обратного масштабирования
        activeTab.value = 'inverse';
        
        // Автоматически выбираем все доступные столбцы для обратного масштабирования
        const scaledColumns = getScaledColumns(scalingParams);
        inverseScalingColumns.value = scaledColumns;
        
        // Если есть столбцы, показываем уведомление
        if (scaledColumns.length > 0) {
          ElMessage({
            message: `Автоматически выбрано ${scaledColumns.length} столбца(ов) для обратного масштабирования`,
            type: 'info'
          });
        }
      } catch (error) {
        console.error('[ScalingMetadataManager] Ошибка импорта метаданных:', error);
        console.log("[ScalingMetadataManager] Детали ошибки:", error.response?.data || error.message);
        
        // Формируем более информативное сообщение об ошибке
        let errorMessage = 'Не удалось импортировать метаданные';
        
        if (error.response) {
          if (error.response.status === 400) {
            errorMessage = 'Некорректный формат файла метаданных';
          } else if (error.response.status === 404) {
            errorMessage = 'Не найден датасет или результат для применения метаданных';
          } else if (error.response.data && error.response.data.detail) {
            errorMessage = `Ошибка сервера: ${error.response.data.detail}`;
          }
        } else if (error.message) {
          errorMessage = error.message;
        }
        
        ElMessage.error(errorMessage);
      } finally {
        isImporting.value = false;
      }
    };
    
    // Функция сохранения ручного ввода параметров
    const saveManualParams = async () => {
      // Определяем ID в зависимости от режима работы
      const id = props.mode === 'dataset' ? props.datasetId : props.resultId;
      
      if (!id || !canSaveManualParams.value) {
        ElMessage.warning('Необходим корректный ID для сохранения параметров');
        return;
      }
      
      isSaving.value = true;
      
      try {
        // Форматируем параметры в структуру, ожидаемую бэкендом
        const formattedParams = {
          scaling_params: {
            standardization: {
              method: manualParams.method,
              columns: manualParams.columns,
              params: {}
            }
          }
        };
        
        // Преобразуем плоскую структуру параметров в вложенный формат
        manualParams.columns.forEach(column => {
          formattedParams.scaling_params.standardization.params[column] = manualParams.parameters[column];
        });
        
        console.log('Сохраняем форматированные параметры:', formattedParams);
        
        // Вызываем соответствующий эндпоинт в зависимости от режима
        if (props.mode === 'dataset') {
          await preprocessingService.setScalingParamsForDataset(id, formattedParams);
        } else {
          await preprocessingService.setScalingParams(id, formattedParams);
        }
        
        ElMessage({
          message: 'Параметры масштабирования успешно сохранены',
          type: 'success'
        });
        
        // Оповещаем родительский компонент об обновлении метаданных 
        emit('metadata-updated', formattedParams.scaling_params);
        
        // Переходим к вкладке обратного масштабирования
        activeTab.value = 'inverse';
      } catch (error) {
        console.error('Ошибка сохранения параметров:', error);
        ElMessage.error(error.response?.data?.detail || 'Не удалось сохранить параметры');
      } finally {
        isSaving.value = false;
      }
    };
    
    // Функция для получения столбцов, к которым применимо масштабирование
    const getScaledColumns = (customParams) => {
      // Используем переданные параметры или текущие из props
      const params = customParams || props.scalingParams;
      
      console.log("[ScalingMetadataManager] Поиск столбцов в параметрах:", params);
      
      if (!params) {
        console.log("[ScalingMetadataManager] Параметры не определены");
        return [];
      }
      
      // Проверяем формат standardization (наиболее распространенный)
      if (params.standardization) {
        console.log("[ScalingMetadataManager] Найдена секция standardization");
        
        // Сначала проверяем явный список столбцов
        if (params.standardization.columns && 
            Array.isArray(params.standardization.columns) && 
            params.standardization.columns.length > 0) {
          console.log("[ScalingMetadataManager] Использую явно указанные столбцы:", 
                     params.standardization.columns);
          return params.standardization.columns;
        }
        
        // Затем проверяем ключи в объекте params
        if (params.standardization.params) {
          const columnsFromParams = Object.keys(params.standardization.params);
          console.log("[ScalingMetadataManager] Извлекаю столбцы из params:", columnsFromParams);
          return columnsFromParams;
        }
      }
      
      // Проверяем альтернативный формат с параметрами mean/std
      if (params.mean && params.std) {
        const meanColumns = Object.keys(params.mean);
        const stdColumns = Object.keys(params.std);
        // Возвращаем пересечение (столбцы, которые есть и в mean, и в std)
        const commonColumns = meanColumns.filter(col => stdColumns.includes(col));
        console.log("[ScalingMetadataManager] Нашел столбцы из mean/std:", commonColumns);
        return commonColumns;
      }
      
      // Проверяем формат с явно указанным методом и столбцами
      if (params.method && params.columns) {
        console.log("[ScalingMetadataManager] Нашел столбцы в формате method/columns:", 
                   params.columns);
        return Array.isArray(params.columns) ? params.columns : [params.columns];
      }
      
      // Проверяем формат с методом и параметрами
      if (params.method && params.params) {
        const columnsFromMethodParams = Object.keys(params.params);
        console.log("[ScalingMetadataManager] Извлекаю столбцы из params метода:", 
                   columnsFromMethodParams);
        return columnsFromMethodParams;
      }
      
      console.log("[ScalingMetadataManager] Не удалось найти столбцы в параметрах");
      return [];
    };
    
    // Функция применения обратного масштабирования
    const applyInverseScaling = async () => {
      if (!inverseScalingColumns.value.length) {
        ElMessage.warning('Выберите хотя бы один столбец для обратного масштабирования');
        return;
      }
      
      // Проверяем наличие параметров масштабирования
      if (!props.scalingParams || Object.keys(props.scalingParams).length === 0) {
        console.error("[ScalingMetadataManager] Отсутствуют параметры масштабирования:", props.scalingParams);
        ElMessage.error('Не найдены параметры масштабирования. Пожалуйста, загрузите метаданные');
        return;
      }
      
      isApplying.value = true;
      
      try {
        const id = props.mode === 'dataset' ? props.datasetId : props.resultId;
        
        // Подробное логирование перед отправкой запроса
        console.log("[ScalingMetadataManager] Подготовка запроса на обратное масштабирование:");
        console.log("ID:", id);
        console.log("Режим:", props.mode);
        console.log("Выбранные столбцы:", inverseScalingColumns.value);
        console.log("Параметры масштабирования:", JSON.stringify(props.scalingParams, null, 2));
        
        const requestData = {
          id: id,
          mode: props.mode,
          columns: inverseScalingColumns.value,
          scaling_params: props.scalingParams
        };
        
        console.log("[ScalingMetadataManager] Отправка запроса:", JSON.stringify(requestData, null, 2));
        
        const scalingResponse = await preprocessingService.applyInverseScaling(requestData);
        
        console.log("[ScalingMetadataManager] Получен ответ:", scalingResponse.data);
        
        ElMessage({
          message: `Обратное масштабирование успешно применено к ${inverseScalingColumns.value.length} столбцам`,
          type: 'success',
          duration: 5000
        });
        
        emit('inverse-scaling-applied', scalingResponse.data);
        
        // Очищаем выбранные столбцы только если мы не находимся в представлении предобработки
        if (!props.inPreprocessingView) {
          inverseScalingColumns.value = [];
        }
      } catch (error) {
        console.error('[ScalingMetadataManager] Ошибка при применении обратного масштабирования:', error);
        
        // Формируем информативное сообщение об ошибке
        let errorMessage = 'Не удалось применить обратное масштабирование';
        
        if (error.response?.data?.detail) {
          errorMessage = `Ошибка: ${error.response.data.detail}`;
        } else if (error.message) {
          errorMessage = `Ошибка: ${error.message}`;
        }
        
        ElMessage.error(errorMessage);
      } finally {
        isApplying.value = false;
      }
    };
    
    // Инициализация при создании компонента
    if (props.hasScalingParams && props.inPreprocessingView) {
      // Если компонент используется в представлении предобработки и есть параметры масштабирования,
      // автоматически выбираем все доступные столбцы для обратного масштабирования
      inverseScalingColumns.value = getScaledColumns();
    }
    
    return {
      activeTab,
      isExporting,
      isImporting,
      isSaving,
      fileList,
      selectedFile,
      manualParams,
      canSaveManualParams,
      inverseScalingColumns,
      isApplying,
      handleFileChange,
      exportMetadata,
      importMetadata,
      saveManualParams,
      getScaledColumns,
      applyInverseScaling
    };
  }
};
</script>

<style scoped>
.scaling-metadata-manager {
  margin-top: 20px;
  margin-bottom: 20px;
}

.tab-content {
  padding: 10px 0;
}

.section {
  margin-bottom: 25px;
  padding-bottom: 15px;
  border-bottom: 1px solid #ebeef5;
}

.section:last-child {
  border-bottom: none;
}

.metadata-upload {
  margin-top: 15px;
}

.column-params {
  background-color: #f5f7fa;
  border-radius: 4px;
  padding: 15px;
  margin-top: 5px;
  margin-bottom: 15px;
}

h4 {
  margin-top: 20px;
  margin-bottom: 20px;
}

h5 {
  margin-top: 5px;
  margin-bottom: 10px;
  font-weight: 500;
  font-size: 16px;
}

.no-scaling-params {
  margin-bottom: 20px;
}

.selection-info {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 5px;
  margin-bottom: 20px;
}

.inverse-scaling-info {
  margin-bottom: 15px;
}

</style>