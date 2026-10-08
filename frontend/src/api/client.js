import axios from 'axios';

// Create an Axios instance with your backend URL
const api = axios.create({
  baseURL: 'http://localhost:8000', // Change this if your backend runs elsewhere
});

// Automatically attach the JWT token to every request
api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default api;