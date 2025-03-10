import axios from 'axios';

export async function managerRequest(baseURL, endpoint, data = {}) {
  const url = `${baseURL}/management/${endpoint}`;
  const response = await axios.post(url, data);
  return response.data;
}

export async function chordRequest(baseURL, workerId, endpoint, data = {}) {
  const url = `${baseURL}/${workerId}/api/${endpoint}`;
  const response = await axios.post(url, data);
  if (response.data.error) {
    throw new Error(response.data.error);
  }
  return response.data.response;
}

