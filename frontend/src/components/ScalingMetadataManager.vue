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
    }
  },
  
  emits: ['update:scaling-params', 'metadata-updated'],
  
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
      if (!props.resultId || !props.hasScalingParams) return;
      
      isExporting.value = true;
      
      try {
        const response = await preprocessingService.exportMetadata(props.resultId);
        
        // Создание ссылки для скачивания
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `scaling_metadata_${props.resultId}.json`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        ElMessage({
          message: 'Метаданные успешно экспортированы',
          type: 'success'
        });
      } catch (error) {
        console.error('Ошибка экспорта метаданных:', error);
        ElMessage.error('Не удалось экспортировать метаданные');
      } finally {
        isExporting.value = false;
      }
    };
    
    // Функция импорта метаданных
    const importMetadata = async () => {
      if (!props.resultId || !selectedFile.value) return;
      
      isImporting.value = true;
      
      try {
        const response = await preprocessingService.importMetadata(props.resultId, selectedFile.value);
        
        ElMessage({
          message: 'Метаданные успешно импортированы',
          type: 'success'
        });
        
        // Оповещаем родительский компонент об обновлении метаданных
        emit('metadata-updated', response.data.scaling_params);
        fileList.value = [];
        selectedFile.value = null;
      } catch (error) {
        console.error('Ошибка импорта метаданных:', error);
        ElMessage.error(error.response?.data?.detail || 'Не удалось импортировать метаданные');
      } finally {
        isImporting.value = false;
      }
    };
    
    // Функция сохранения ручного ввода параметров
    const saveManualParams = async () => {
      if (!props.resultId || !canSaveManualParams.value) return;
      
      isSaving.value = true;
      
      try {
        const params = {
          method: manualParams.method,
          columns: manualParams.columns,
          parameters: manualParams.parameters
        };
        
        const response = await preprocessingService.setScalingParams(props.resultId, params);
        
        ElMessage({
          message: 'Параметры масштабирования успешно сохранены',
          type: 'success'
        });
        
        // Оповещаем родительский компонент об обновлении метаданных
        emit('metadata-updated', response.data.scaling_params);
      } catch (error) {
        console.error('Ошибка сохранения параметров:', error);
        ElMessage.error(error.response?.data?.detail || 'Не удалось сохранить параметры');
      } finally {
        isSaving.value = false;
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
      handleFileChange,
      exportMetadata,
      importMetadata,
      saveManualParams
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