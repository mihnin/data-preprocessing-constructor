import axios from 'axios';

const apiClient = axios.create({
  baseURL: '/api',
  timeout: 300000, // 5 минут
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  }
});

export default apiClient;