<template>
  <div class="preprocessing-view">
    <h1>Выбор методов предобработки</h1>
    
    <el-alert
      v-if="!datasetId"
      title="Необходимо загрузить данные"
      type="warning"
      description="Пожалуйста, вернитесь на шаг загрузки данных"
      show-icon
      :closable="false"
    >
      <template #default>
        <el-button type="primary" size="small" @click="goToUpload">
          К загрузке данных
        </el-button>
      </template>
    </el-alert>
    
    <div v-if="datasetId" class="preprocessing-container">
      <!-- Вкладки для категорий методов предобработки -->
      <el-tabs v-model="activeTab">
        <el-tab-pane label="Общие методы" name="general">
          <el-card class="method-list">
            <div 
              v-for="method in generalMethods" 
              :key="method.method_id"
              class="method-item"
            >
              <div class="method-header">
                <el-checkbox 
                  v-model="selectedMethods[method.method_id]"
                  @change="(val) => handleMethodSelection(method.method_id, val)"
                >
                  <span class="method-name">{{ method.name }}</span>
                </el-checkbox>
                
                <el-button 
                  type="primary" 
                  size="small" 
                  icon="el-icon-setting" 
                  plain
                  :disabled="!selectedMethods[method.method_id]"
                  @click="configureMethod(method)"
                >
                  Настроить
                </el-button>
              </div>
              
              <div class="method-description">
                {{ method.description }}
              </div>
              
              <el-divider></el-divider>
            </div>
          </el-card>
        </el-tab-pane>
        
        <el-tab-pane label="Методы для временных рядов" name="timeseries">
          <el-card class="method-list">
            <div 
              v-for="method in timeSeriesMethods" 
              :key="method.method_id"
              class="method-item"
            >
              <div class="method-header">
                <el-checkbox 
                  v-model="selectedMethods[method.method_id]"
                  @change="(val) => handleMethodSelection(method.method_id, val)"
                >
                  <span class="method-name">{{ method.name }}</span>
                </el-checkbox>
                
                <el-button 
                  type="primary" 
                  size="small" 
                  icon="el-icon-setting" 
                  plain
                  :disabled="!selectedMethods[method.method_id]"
                  @click="configureMethod(method)"
                >
                  Настроить
                </el-button>
              </div>
              
              <div class="method-description">
                {{ method.description }}
              </div>
              
              <el-divider></el-divider>
            </div>
          </el-card>
        </el-tab-pane>
        
        <el-tab-pane label="Обратное масштабирование" name="inverse-scaling">
          <el-card class="method-list">
            <div v-if="!hasScalingParams" class="no-scaling-params">
              <el-alert
                title="Отсутствуют параметры масштабирования"
                type="info"
                description="Для применения обратного масштабирования необходимо импортировать параметры или указать их вручную"
                show-icon
                :closable="false"
              />
            </div>
            
            <ScalingMetadataManager
              mode="dataset"
              :dataset-id="datasetId"
              :result-id="null"
              :has-scaling-params="hasScalingParams"
              :scaling-method-name="scalingMethodName"
              :available-columns="availableColumns"
              :scaling-params="scalingParams"
              :in-preprocessing-view="true"
              @metadata-updated="onScalingMetadataUpdated"
              @inverse-scaling-applied="onInverseScalingApplied"
            />
          </el-card>
        </el-tab-pane>
      </el-tabs>
      
      <!-- Информация о выбранных методах -->
      <el-card class="selected-methods-summary" v-if="hasSelectedMethods">
        <template #header>
          <div class="card-header">
            <span>Выбранные методы</span>
            <el-button 
              type="success" 
              size="small"
              @click="previewResults"
              :loading="isPreviewLoading"
            >
              Предпросмотр результатов
            </el-button>
          </div>
        </template>
        
        <div v-for="(method, index) in selectedMethodsList" :key="index" class="selected-method">
          <span>{{ index + 1 }}. {{ method.name }}</span>
          <el-tag size="small" type="info">{{ getParametersSummary(method) }}</el-tag>
          </div>
      </el-card>
      
      <!-- Кнопки навигации -->
      <div class="navigation-buttons">
        <el-button @click="goBack">Назад</el-button>
        <el-button 
          type="primary" 
          @click="processData"
          :disabled="!hasSelectedMethods || isProcessing"
        >
          {{ isProcessing ? 'Обработка...' : 'Выполнить предобработку' }}
        </el-button>
      </div>
    </div>
    
    <!-- Диалог настройки метода -->
    <el-dialog
      :title="`Настройка метода: ${currentMethod?.name || ''}`"
      v-model="showConfigDialog"
      width="60%"
    >
      <div v-if="currentMethod">
        <div class="method-info">
          <el-alert type="info" :closable="false">
            {{ currentMethod.description }}
          </el-alert>
        </div>
        
        <div class="method-parameters">
          <div 
            v-for="(param, paramName) in currentMethod.parameters"
            :key="paramName"
            class="parameter-item"
          >
            <h4>{{ param.description || capitalize(paramName) }}</h4>
            
            <!-- Select параметр -->
            <template v-if="param.type === 'select'">
              <el-form-item>
                <el-select 
                  v-model="methodConfigs[currentMethod.method_id][paramName]"
                  placeholder="Выберите значение"
                >
                  <el-option 
                    v-for="option in getOptionsForParam(param, paramName)"
                    :key="option.value"
                    :label="option.label"
                    :value="option.value"
                  />
                </el-select>
              </el-form-item>
            </template>
            
            <!-- Multiselect параметр -->
            <template v-else-if="param.type === 'multiselect'">
              <el-form-item>
                <el-select 
                  v-model="methodConfigs[currentMethod.method_id][paramName]"
                  multiple
                  placeholder="Выберите значения"
                >
                  <el-option 
                    v-for="option in getOptionsForParam(param, paramName)"
                    :key="option.value"
                    :label="option.label"
                    :value="option.value"
                  />
                </el-select>
              </el-form-item>
            </template>
            
            <!-- Number параметр -->
            <template v-else-if="param.type === 'number'">
              <el-form-item>
                <el-input-number 
                  v-model="methodConfigs[currentMethod.method_id][paramName]"
                  :min="param.min || 1"
                  :max="param.max || 100"
                  :step="param.step || 1"
                />
              </el-form-item>
            </template>
          </div>
        </div>
      </div>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showConfigDialog = false">Отмена</el-button>
          <el-button type="primary" @click="saveMethodConfig">
            Сохранить настройки
          </el-button>
        </span>
      </template>
    </el-dialog>
    
    <!-- Диалог предпросмотра результатов -->
    <el-dialog
      title="Предпросмотр результатов предобработки"
      v-model="showPreviewDialog"
      width="80%"
      :fullscreen="true"
    >
      <div v-if="isPreviewLoading" class="preview-loading">
        <el-spinner></el-spinner>
        <p>Генерация предпросмотра...</p>
      </div>
      
      <div v-else-if="previewError" class="preview-error">
        <el-alert
          title="Ошибка предпросмотра"
          type="error"
          :description="previewError"
          show-icon
        />
      </div>
      
      <div v-else-if="previewData" class="preview-content">
        <el-tabs v-model="previewTab">
          <el-tab-pane label="Исходные данные" name="original">
            <el-table
              :data="previewData.original_sample"
              border
              style="width: 100%"
              max-height="500"
            >
              <el-table-column
                v-for="column in previewData.original_columns"
                :key="column"
                :prop="column"
                :label="column"
                min-width="150"
              />
            </el-table>
          </el-tab-pane>
          
          <el-tab-pane label="Обработанные данные" name="processed">
            <el-table
              :data="previewData.processed_sample"
              border
              style="width: 100%"
              max-height="500"
            >
              <el-table-column
                v-for="column in previewData.processed_columns"
                :key="column"
                :prop="column"
                :label="column"
                min-width="150"
              />
            </el-table>
          </el-tab-pane>
          
          <el-tab-pane label="Сравнение" name="comparison">
            <div class="columns-comparison">
              <div class="column-list">
                <h4>Исходные столбцы ({{ previewData.original_columns.length }})</h4>
                <el-tag
                  v-for="column in previewData.original_columns"
                  :key="`orig-${column}`"
                  class="column-tag"
                >
                  {{ column }}
                </el-tag>
              </div>
              
              <div class="column-list">
                <h4>Обработанные столбцы ({{ previewData.processed_columns.length }})</h4>
                <el-tag
                  v-for="column in previewData.processed_columns"
                  :key="`proc-${column}`"
                  :type="isNewColumn(column) ? 'success' : ''"
                  class="column-tag"
                >
                  {{ column }}
                </el-tag>
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showPreviewDialog = false">Закрыть</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { defineComponent, ref, computed, reactive, onMounted, watch } from 'vue';
import { useRouter } from 'vue-router';
import { useStore } from 'vuex';
import { ElMessage } from 'element-plus';
import preprocessingService from '@/services/preprocessingService';
import datasetService from '@/services/datasetService';
import ScalingMetadataManager from '@/components/ScalingMetadataManager.vue';

export default defineComponent({
  name: 'PreprocessingView',
  
  components: {
    ScalingMetadataManager
  },
  
  setup() {
    const router = useRouter();
    const store = useStore();
    // Добавляем переменную для хранения выбранных столбцов для обратного масштабирования
  
    // Состояние набора данных
    const datasetId = computed(() => store.state.datasetId);
    const datasetInfo = ref(null);
    
    // Добавляем получение параметров масштабирования из хранилища
    const scalingParams = computed(() => store.state.scalingParams);
    const hasScalingParams = computed(() => !!scalingParams.value);
    
    // Состояние методов предобработки
    const methods = ref([]);
    const activeTab = ref('general');
    
    // Выбранные методы
    const selectedMethods = reactive({});
    const methodConfigs = reactive({});
    
    // Состояние настройки метода
    const showConfigDialog = ref(false);
    const currentMethod = ref(null);
    
    // Состояние предпросмотра
    const showPreviewDialog = ref(false);
    const isPreviewLoading = ref(false);
    const previewData = ref(null);
    const previewError = ref(null);
    const previewTab = ref('comparison');
    
    // Результат обработки
    const resultMetadata = ref({ columns: [] });
    
    // Состояние обработки
    const isProcessing = ref(false);

    // Доступные столбцы для операций
    const availableColumns = computed(() => {
      if (datasetInfo.value && datasetInfo.value.columns) {
        return datasetInfo.value.columns.map(col => col.name);
      }
      return [];
    });

    // Название метода масштабирования
    const scalingMethodName = ref('');

    // Методы для категорий
    const generalMethods = computed(() => 
      methods.value.filter(method => 
        !['lagging', 'rolling_statistics', 'time_series_analysis', 'date_components'].includes(method.method_id)
      )
    );
    
    const timeSeriesMethods = computed(() => 
      methods.value.filter(method => 
        ['lagging', 'rolling_statistics', 'time_series_analysis', 'date_components'].includes(method.method_id)
      )
    );
    
    // Список выбранных методов
    const selectedMethodsList = computed(() => {
      return methods.value.filter(method => selectedMethods[method.method_id]);
    });
    
    // Есть ли выбранные методы
    const hasSelectedMethods = computed(() => {
      return Object.values(selectedMethods).some(value => value);
    });
    
    // Получение и обработка методов предобработки
    onMounted(async () => {
      if (!datasetId.value) return;
      
      try {
        // Получаем информацию о наборе данных
        const datasetResponse = await datasetService.getDatasetInfo(datasetId.value);
        datasetInfo.value = datasetResponse.data;
        
        // Получаем доступные методы предобработки
        const methodsResponse = await preprocessingService.getPreprocessingMethods();
        methods.value = methodsResponse.data;
        
        // Инициализация состояния выбранных методов и конфигураций
        methods.value.forEach(method => {
          // Автоматически выбираем рекомендуемые методы
          selectedMethods[method.method_id] = datasetInfo.value.recommended_methods.includes(method.method_id);
          
          // Инициализируем конфигурацию метода
          methodConfigs[method.method_id] = {};
          
          // Заполняем значениями по умолчанию
          Object.entries(method.parameters).forEach(([paramName, paramConfig]) => {
            methodConfigs[method.method_id][paramName] = paramConfig.default !== undefined 
              ? paramConfig.default 
              : (paramConfig.type === 'multiselect' ? [] : null);
          });
        });
      } catch (error) {
        console.error('Ошибка загрузки данных:', error);
        ElMessage.error('Не удалось загрузить методы предобработки');
      }
    });
    
    // Функция для обновления состояния выбора метода обратного масштабирования
    const updateInverseScalingState = (isSelected) => {
      // Обновляем состояние в списке методов
      selectedMethods['inverse_scaling'] = isSelected;
      
      // Если метод не выбран, очищаем список столбцов
      if (!isSelected) {
        inverseScalingColumns.value = [];
      }
    };

    // Наблюдатель для вкладки
    watch(() => activeTab.value, (newTab) => {
      // При переключении на вкладку обратного масштабирования
      if (newTab === 'inverse-scaling') {
        // Проверяем наличие параметров масштабирования
        if (store.getters.hasScalingParams) {
          // Автоматически выбираем метод, если есть параметры масштабирования
          updateInverseScalingState(true);
        }
      }
    });
    
    // Обработка выбора метода
    const handleMethodSelection = (methodId, isSelected) => {
      selectedMethods[methodId] = isSelected;
      
      // Автоматический переход на вкладку "Обратное масштабирование" при выборе метода
      if (methodId === 'inverse_scaling' && isSelected) {
        activeTab.value = 'inverse-scaling';
      }
      
      // Синхронизация с состоянием обратного масштабирования
      if (methodId === 'inverse_scaling') {
        updateInverseScalingState(isSelected);
      }
    };
    
    // Открытие диалога настройки метода
    const configureMethod = (method) => {
      // Если метод - обратное масштабирование, перенаправляем на вкладку
      if (method.method_id === 'inverse_scaling') {
        ElMessage({
          message: 'Для настройки параметров обратного масштабирования перейдите на вкладку "Обратное масштабирование"',
          type: 'info',
          duration: 5000 // Увеличиваем время отображения сообщения
        });
        activeTab.value = 'inverse-scaling'; // Автоматически переключаемся
        return;
      }

      currentMethod.value = method;
      showConfigDialog.value = true;
      
      // Если у нас нет инициализированной конфигурации для этого метода, создаем ее
      if (!methodConfigs[method.method_id]) {
        methodConfigs[method.method_id] = {};
      }
      
      // Инициализируем параметры значениями по умолчанию, если они не заданы
      Object.entries(method.parameters).forEach(([paramName, paramConfig]) => {
        if (methodConfigs[method.method_id][paramName] === undefined) {
          methodConfigs[method.method_id][paramName] = paramConfig.default !== undefined 
            ? paramConfig.default 
            : (paramConfig.type === 'multiselect' ? [] : null);
        }
      });
      
      // Автоматически заполняем целевую переменную, если она уже выбрана
      if (datasetInfo.value && datasetInfo.value.target_column) {
        const hasTargetParam = Object.keys(method.parameters).includes('target_column');
        if (hasTargetParam) {
          methodConfigs[method.method_id]['target_column'] = datasetInfo.value.target_column;
        }
      }
      
      // Добавляем автоматическое заполнение целевой переменной для временных рядов
      if (datasetInfo.value && datasetInfo.value.target_column && ['lagging', 'rolling_statistics'].includes(method.method_id)) {
        methodConfigs[method.method_id]['target_column'] = datasetInfo.value.target_column;
      }
    };
    
    // Сохранение конфигурации метода
    const saveMethodConfig = () => {
      showConfigDialog.value = false;
      ElMessage({
        message: `Настройки метода "${currentMethod.value.name}" сохранены`,
        type: 'success'
      });
    };
    
    // Предпросмотр результатов предобработки
    const previewResults = async () => {
      if (!hasSelectedMethods.value) return;
      
      showPreviewDialog.value = true;
      isPreviewLoading.value = true;
      previewError.value = null;
      previewData.value = null;
      
      try {
        const config = {
          dataset_id: datasetId.value,
          methods: selectedMethodsList.value.map(method => ({
            method_id: method.method_id,
            parameters: methodConfigs[method.method_id]
          }))
        };
        
        const response = await preprocessingService.previewPreprocessing(config);
        previewData.value = response.data;
      } catch (error) {
        console.error('Ошибка предпросмотра:', error);
        previewError.value = error.response?.data?.detail || 'Не удалось выполнить предпросмотр';
      } finally {
        isPreviewLoading.value = false;
      }
    };
    
    // Выполнение полной предобработки
    const processData = async () => {
      if ((!hasSelectedMethods.value && !store.getters.hasScalingParams) || 
          (activeTab.value === 'inverse-scaling' && 
          (!inverseScalingColumns.value || inverseScalingColumns.value.length === 0))) {
        ElMessage.warning('Выберите методы предобработки или настройте параметры обратного масштабирования');
        return;
      }
      
      isProcessing.value = true;
      
      try {
        // Формируем список методов предобработки
        const methods = [];
        
        // Флаг для отслеживания наличия метода inverse_scaling
        let hasInverseScaling = false;
        
        // Добавляем выбранные методы
        selectedMethodsList.value.forEach(method => {
          // Проверяем наличие метода inverse_scaling
          if (method.method_id === 'inverse_scaling') {
            hasInverseScaling = true;
            
            // Проверяем наличие выбранных столбцов и параметров
            if (!inverseScalingColumns.value || inverseScalingColumns.value.length === 0) {
              console.warn('[PreprocessingView] Для обратного масштабирования не выбраны столбцы');
              ElMessage.warning('Выберите столбцы для обратного масштабирования');
              isProcessing.value = false;
              return;
            }
            
            if (!store.getters.hasScalingParams) {
              console.error('[PreprocessingView] Отсутствуют параметры масштабирования');
              ElMessage.error('Для обратного масштабирования необходимо загрузить метаданные');
              isProcessing.value = false;
              return;
            }
            
            // Добавляем метод с правильными параметрами
            methods.push({
              method_id: 'inverse_scaling',
              parameters: {
                columns: inverseScalingColumns.value,
                scaling_params: store.state.scalingParams
              }
            });
          } else {
            // Добавляем остальные методы как обычно
            methods.push({
              method_id: method.method_id,
              parameters: methodConfigs[method.method_id]
            });
          }
        });
        
        // Проверяем, нужно ли добавить метод обратного масштабирования,
        // если он выбран на вкладке, но не в списке методов
        if (activeTab.value === 'inverse-scaling' && !hasInverseScaling && 
            inverseScalingColumns.value.length > 0 && store.getters.hasScalingParams) {
          console.log('[PreprocessingView] Добавляю метод обратного масштабирования из вкладки');
          
          methods.push({
            method_id: 'inverse_scaling',
            parameters: {
              columns: inverseScalingColumns.value,
              scaling_params: store.state.scalingParams
            }
          });
        }
        
        // Проверка на пустой список методов
        if (methods.length === 0) {
          ElMessage.warning('Не выбран ни один метод предобработки');
          isProcessing.value = false;
          return;
        }
        
        console.log('[PreprocessingView] Отправка методов предобработки:', JSON.stringify(methods, null, 2));
        
        const config = {
          dataset_id: datasetId.value,
          methods
        };
        
        const response = await preprocessingService.executePreprocessing(config);
        
        // Сохраняем ID результата в хранилище
        store.dispatch('setResult', response.data.result_id);
        
        ElMessage({
          message: 'Предобработка запущена успешно',
          type: 'success'
        });
        
        // Переходим к следующему шагу
        router.push('/preview');
      } catch (error) {
        console.error('[PreprocessingView] Ошибка обработки:', error);
        ElMessage.error(error.response?.data?.detail || 'Не удалось запустить предобработку');
      } finally {
        isProcessing.value = false;
      }
    };

    // Навигация
    const goToUpload = () => {
      router.push('/upload');
    };
    
    const goBack = () => {
      router.push('/upload');
    };
    
    // Вспомогательные функции
    const capitalize = (str) => {
      return str.charAt(0).toUpperCase() + str.slice(1);
    };
    
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

    const formatOptionLabel = (option, paramName) => {
      // Форматирование отображаемых названий опций
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
        return strategyLabels[option] || option;
      }
      return option;
    };

    const getOptionsForParam = (param, paramName) => {
      // Обработка параметров выбора столбцов
      if (paramName === 'target_column' || paramName === 'exog_columns') {
        // Для методов временных рядов нужны числовые столбцы
        if (datasetInfo.value && datasetInfo.value.columns) {
          return datasetInfo.value.columns
            .filter(col => col.type === 'numeric')
            .map(col => ({
              value: col.name,
              label: col.name
            }));
        }
      }
      
      // Обработка параметра statistics для rolling_statistics
      if (paramName === 'statistics' && param.options) {
        return param.options.map(option => ({
          value: option,
          label: option === 'mean' ? 'Среднее' : 
                 option === 'std' ? 'Станд. отклонение' : 
                 option === 'min' ? 'Минимум' : 
                 option === 'max' ? 'Максимум' : option
        }));
      }
      
      // Существующая обработка для select с options
      if (param.type === 'select' && param.options) {
        return param.options.map(option => ({
          value: option,
          label: formatOptionLabel(option, paramName)
        }));
      }
      
      // Существующая обработка для параметра columns
      if (paramName === 'columns') {
        // Для метода date_components нужно отфильтровать столбцы типа datetime
        if (currentMethod.value && currentMethod.value.method_id === 'date_components') {
          return datasetInfo.value.columns
            .filter(col => col.type === 'datetime')
            .map(col => ({
              value: col.name,
              label: col.name
            }));
        }
        
        // Для других методов возвращаем все столбцы
        return datasetInfo.value.columns.map(col => ({
          value: col.name,
          label: col.name
        }));
      }
      
      return [];
    };

    const getParametersSummary = (method) => {
      const config = methodConfigs[method.method_id];
      if (!config) return '';
      
      // Получаем краткую информацию о настройках
      const summaryParts = [];
      
      // Добавляем информацию о стратегии, если есть
      if (config.strategy) {
        summaryParts.push(`Метод: ${formatParameterValue('strategy', config.strategy)}`);
      }
      
      // Добавляем информацию о выбранных столбцах
      if (config.columns && config.columns.length) {
        summaryParts.push(`Столбцов: ${config.columns.length}`);
      }
      
      // Добавляем информацию о компонентах даты, если есть
      if (config.components && config.components.length) {
        summaryParts.push(`Компоненты: ${formatParameterValue('components', config.components)}`);
      }
      
      return summaryParts.join(', ') || 'Настройки по умолчанию';
    };
    
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
            'week_of_year': 'Неделя года'
          };
          
          return value.map(component => componentLabels[component] || component).join(', ');
        }
      }
      
      if (Array.isArray(value)) {
        return value.length > 0 ? value.join(', ') : 'Не выбрано';
      }
      
      return value === null || value === undefined ? 'Не указано' : value;
    };
    
    // Проверка, является ли столбец новым
    const isNewColumn = (column) => {
      if (!previewData.value || !previewData.value.original_columns) return false;
      return !previewData.value.original_columns.includes(column);
    };

    // Обработчики для компонента ScalingMetadataManager
    const onScalingMetadataUpdated = (params) => {
      console.log('[PreprocessingView] Обновление параметров масштабирования:', params);
      
      // Защитная проверка
      if (!params) {
        console.error('[PreprocessingView] Получены пустые параметры масштабирования');
        ElMessage.error('Получены некорректные параметры масштабирования');
        return;
      }
      
      // Сохраняем параметры в хранилище
      store.dispatch('setScalingParams', params);
      
      // Определяем тип метода масштабирования для отображения
      if (params.standardization && params.standardization.method) {
        const methodNames = {
          'standard': 'Стандартизация (StandardScaler)',
          'minmax': 'Мин-макс нормализация (MinMaxScaler)',
          'robust': 'Устойчивое масштабирование (RobustScaler)'
        };
        scalingMethodName.value = methodNames[params.standardization.method] || params.standardization.method;
      }
      
      // Автоматически выбираем метод обратного масштабирования
      selectedMethods['inverse_scaling'] = true;
      
      // Извлекаем списки столбцов из параметров масштабирования
      let columns = [];
      
      // Проверяем различные форматы хранения списка столбцов
      if (params.standardization) {
        if (params.standardization.columns && Array.isArray(params.standardization.columns)) {
          columns = params.standardization.columns;
        } else if (params.standardization.params) {
          columns = Object.keys(params.standardization.params);
        }
      }
      
      console.log('[PreprocessingView] Извлеченные столбцы для масштабирования:', columns);
      
      // Если найдены столбцы, автоматически выбираем их для обратного масштабирования
      if (columns.length > 0) {
        inverseScalingColumns.value = columns;
        
        ElMessage({
          message: `Автоматически выбраны столбцы для обратного масштабирования: ${columns.join(', ')}`,
          type: 'success',
          duration: 5000
        });
        
        // Переходим на вкладку обратного масштабирования
        activeTab.value = 'inverse-scaling';
      } else {
        console.warn('[PreprocessingView] Не найдены столбцы для обратного масштабирования');
        ElMessage.warning('Не удалось определить столбцы для обратного масштабирования');
      }
    };

    const onInverseScalingApplied = (data) => {
      // Сохраняем ID результата и переходим к просмотру
      store.commit('setResultId', data.result_id);
      router.push('/preview');
    };

    const inverseScalingColumns = ref([]);

    return {
      datasetId,
      methods,
      activeTab,
      selectedMethods,
      methodConfigs,
      generalMethods,
      timeSeriesMethods,
      selectedMethodsList,
      hasSelectedMethods,
      showConfigDialog,
      currentMethod,
      showPreviewDialog,
      isPreviewLoading,
      previewData,
      previewError,
      previewTab,
      isProcessing,
      resultMetadata,
      availableColumns,
      scalingParams,
      hasScalingParams,
      scalingMethodName,
      handleMethodSelection,
      configureMethod,
      saveMethodConfig,
      previewResults,
      processData,
      goToUpload,
      goBack,
      capitalize,
      formatOptionLabel,
      getOptionsForParam,
      getParametersSummary,
      formatParameterValue,
      isNewColumn,
      getMethodName,
      onScalingMetadataUpdated,
      onInverseScalingApplied,
      inverseScalingColumns
    };
  }
});
</script>

<style scoped>
.preprocessing-view {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.preprocessing-container {
  margin-top: 20px;
}

.method-list {
  margin-bottom: 20px;
}

.method-item {
  padding: 10px 0;
}

.method-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.method-name {
  font-weight: bold;
  font-size: 16px;
}

.method-description {
  color: #606266;
  margin-left: 24px;
}

.selected-methods-summary {
  margin-top: 20px;
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.selected-method {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid #ebeef5;
}

.selected-method:last-child {
  border-bottom: none;
}

.navigation-buttons {
  display: flex;
  justify-content: space-between;
  margin-top: 20px;
}

.method-info {
  margin-bottom: 20px;
}

.parameter-item {
  margin-bottom: 20px;
}

.preview-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 50px;
}

.preview-error {
  padding: 20px;
}

.columns-comparison {
  display: flex;
  justify-content: space-between;
}

.column-list {
  width: 48%;
}

.column-tag {
  margin: 5px;
}
</style>