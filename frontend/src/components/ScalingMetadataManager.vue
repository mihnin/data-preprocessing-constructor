<template>
  <div class="scaling-metadata-manager">
    <el-divider>Управление параметрами масштабирования</el-divider>
    
    <el-tabs v-model="activeTab">
      <!-- Вкладка экспорта метаданных -->
      <el-tab-pane label="Экспорт метаданных" name="export">
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
      </el-tab-pane>
      
      <!-- Вкладка импорта метаданных -->
      <el-tab-pane label="Импорт метаданных" name="import">
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
      </el-tab-pane>
      
      <!-- Вкладка ручного ввода параметров -->
      <el-tab-pane label="Ручной ввод параметров" name="manual">
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
      
      <!-- Новая вкладка для обратного масштабирования -->
      <el-tab-pane label="Обратное преобразование" name="inverse" v-if="hasScalingParams">
        <p>
          Применить обратное масштабирование к выбранным столбцам.
        </p>
        
        <el-form label-width="200px">
          <el-form-item label="Столбцы для преобразования:">
            <el-select 
              v-model="inverseScalingColumns" 
              multiple
              placeholder="Выберите столбцы"
            >
              <el-option
                v-for="column in getScaledColumns()"
                :key="column"
                :label="column"
                :value="column"
              />
            </el-select>
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
      required: true
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
    // Новые параметры
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
    }
  },
  
  emits: ['update:scaling-params', 'metadata-updated', 'inverse-scaling-applied'],
  
  setup(props, { emit }) {
    // Активная вкладка
    const activeTab = ref('export');
    
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
    
    // Инициализация параметров для выбранных столбцов
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
    
    // Реинициализация параметров при смене метода
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
      try {
        isExporting.value = true;
        
        // Здесь исправляем неиспользуемую переменную response
        // Было: const response = await preprocessingService.exportScalingMetadata(...
        // Меняем на один из вариантов:
        
        // Вариант 1: Если данные из response не используются вообще
        await preprocessingService.exportScalingMetadata(
          props.resultId, 
          props.scalingMethodName
        );
        
        // ИЛИ Вариант 2: Если нужны данные из response
        // const { data } = await preprocessingService.exportScalingMetadata(...
        
        ElMessage.success('Метаданные масштабирования успешно экспортированы');
      } catch (error) {
        console.error('Ошибка экспорта метаданных:', error);
        ElMessage.error(error.response?.data?.detail || 'Не удалось экспортировать метаданные');
      } finally {
        isExporting.value = false;
      }
    };
    
    // Функция импорта метаданных - ИСПРАВЛЕННАЯ
    const importMetadata = async () => {
      // Check if either resultId or datasetId is available based on mode
      const id = props.mode === 'dataset' ? props.datasetId : props.resultId;
      if (!id || !selectedFile.value) return;
      
      isImporting.value = true;
      
      try {
        console.log("Importing metadata file:", selectedFile.value.name);
        
        // Create form data with the appropriate ID based on mode
        const formData = new FormData();
        formData.append('file', selectedFile.value);
        formData.append(props.mode === 'dataset' ? 'dataset_id' : 'result_id', id);
        
        // Call the proper import endpoint based on mode and extract scaling params from response
        let scalingParams;
        if (props.mode === 'dataset') {
          const response = await preprocessingService.importMetadataForDataset(id, selectedFile.value);
          scalingParams = response.data.scaling_params;
        } else {
          const response = await preprocessingService.importMetadata(id, selectedFile.value);
          scalingParams = response.data.scaling_params;
        }
        
        ElMessage({
          message: 'Метаданные успешно импортированы',
          type: 'success'
        });
        
        console.log("Import successful, scaling params:", scalingParams);
        
        // Оповещаем родительский компонент об обновлении метаданных
        emit('metadata-updated', scalingParams);
        fileList.value = [];
        selectedFile.value = null;
        
        // After successful import, activate the inverse scaling tab
        activeTab.value = 'inverse';
      } catch (error) {
        console.error('Ошибка импорта метаданных:', error);
        console.log("Error details:", error.response?.data || error.message);
        ElMessage.error(error.response?.data?.detail || 'Не удалось импортировать метаданные');
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
          standardization: {
            method: manualParams.method,
            columns: manualParams.columns,
            params: {}
          }
        };
        
        // Преобразуем плоскую структуру параметров в вложенный формат
        manualParams.columns.forEach(column => {
          formattedParams.standardization.params[column] = manualParams.parameters[column];
        });
        
        console.log('Сохраняем форматированные параметры:', formattedParams);
        
        // Вызываем соответствующий эндпоинт в зависимости от режима
        // Удаляем объявление неиспользуемой переменной response
        if (props.mode === 'dataset') {
          // Предполагаем, что такой метод нужно добавить в сервис
          await preprocessingService.setScalingParamsForDataset(id, formattedParams);
        } else {
          await preprocessingService.setScalingParams(id, formattedParams);
        }
        
        ElMessage({
          message: 'Параметры масштабирования успешно сохранены',
          type: 'success'
        });
        
        // Оповещаем родительский компонент об обновлении метаданных
        emit('metadata-updated', formattedParams);
      } catch (error) {
        console.error('Ошибка сохранения параметров:', error);
        ElMessage.error(error.response?.data?.detail || 'Не удалось сохранить параметры');
      } finally {
        isSaving.value = false;
      }
    };
    
    // Функция для получения столбцов, к которым применимо масштабирование
    const getScaledColumns = () => {
      if (!props.hasScalingParams) return [];
      
      // Получаем список столбцов из параметров масштабирования
      if (props.scalingParams && props.scalingParams.parameters) {
        return Object.keys(props.scalingParams.parameters);
      }
      
      // Если параметры не определены явно, возвращаем все доступные столбцы
      return props.availableColumns;
    };
    
    // Функция применения обратного масштабирования
    const applyInverseScaling = async () => {
      if (!inverseScalingColumns.value.length) {
        ElMessage.warning('Выберите хотя бы один столбец для обратного масштабирования');
        return;
      }
      
      isApplying.value = true;
      
      try {
        const requestData = {
          columns: inverseScalingColumns.value
        };
        
        let scalingResponse;
        
        if (props.mode === 'dataset') {
          scalingResponse = await preprocessingService.applyInverseScalingToDataset(
            props.datasetId, requestData
          );
        } else {
          scalingResponse = await preprocessingService.applyInverseScalingToResult(
            props.resultId, requestData
          );
        }
        
        ElMessage({
          message: 'Обратное масштабирование успешно применено',
          type: 'success'
        });
        
        emit('inverse-scaling-applied', scalingResponse.data);
        
        // Clear selected columns
        inverseScalingColumns.value = [];
      } catch (error) {
        console.error('Ошибка при применении обратного масштабирования:', error);
        ElMessage.error(error.response?.data?.detail || 'Не удалось применить обратное масштабирование');
      } finally {
        isApplying.value = false;
      }
    };
    
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

.metadata-upload {
  margin-top: 15px;
}

.column-params {
  background-color: #f5f7fa;
  border-radius: 4px;
  padding: 15px;
  margin-bottom: 15px;
}

h4 {
  margin-top: 20px;
  margin-bottom: 10px;
}

h5 {
  margin-top: 5px;
  margin-bottom: 15px;
  color: #409eff;
}
</style>