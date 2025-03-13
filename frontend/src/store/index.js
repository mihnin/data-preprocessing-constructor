import { createStore } from 'vuex'

export default createStore({
  state: {
    datasetId: null,
    resultId: null,
    datasetInfo: null,
    scalingParams: null  // Параметры масштабирования данных
  },
  mutations: {
    setDatasetId(state, id) {
      state.datasetId = id;
    },
    setResultId(state, id) {
      state.resultId = id;
    },
    setDatasetInfo(state, info) {
      state.datasetInfo = info;
    },
    setScalingParams(state, params) {
      console.log('[store] Сохранение параметров масштабирования:', params);
      
      // Проверка на корректность параметров
      if (!params) {
        console.error('[store] Попытка сохранить пустые параметры масштабирования');
        return;
      }
      
      // Глубокое копирование объекта для избежания ссылочных проблем
      state.scalingParams = JSON.parse(JSON.stringify(params));
    },
    clearPreprocessingState(state) {
      state.datasetId = null;
      state.resultId = null;
      state.datasetInfo = null;
      state.scalingParams = null;
    }
  },
  actions: {
    setDataset({ commit }, { id, info }) {
      commit('setDatasetId', id);
      if (info) {
        commit('setDatasetInfo', info);
      }
    },
    setResult({ commit }, id) {
      commit('setResultId', id);
    },
    setScalingParams({ commit }, params) {
      console.log('Сохранение параметров масштабирования в хранилище:', params);
      commit('setScalingParams', params);
    },
    resetState({ commit }) {
      commit('clearPreprocessingState');
    }
  },
  getters: {
    hasDataset: state => !!state.datasetId,
    hasResult: state => !!state.resultId,
    hasScalingParams: state => {
      if (!state.scalingParams) return false;
      
      // Проверка наличия параметров standardization
      if (state.scalingParams.standardization) {
        if ((state.scalingParams.standardization.columns && 
             state.scalingParams.standardization.columns.length > 0) ||
            (state.scalingParams.standardization.params && 
             Object.keys(state.scalingParams.standardization.params).length > 0)) {
          return true;
        }
      }
      
      // Проверка альтернативных форматов
      if (state.scalingParams.mean && state.scalingParams.std) {
        return true;
      }
      
      if (state.scalingParams.min && state.scalingParams.max) {
        return true;
      }
      
      // Проверка простой структуры с методом и columns/params
      if (state.scalingParams.method) {
        if ((state.scalingParams.columns && state.scalingParams.columns.length > 0) ||
            (state.scalingParams.params && Object.keys(state.scalingParams.params).length > 0)) {
          return true;
        }
      }
      
      return false;
    }
  }
})