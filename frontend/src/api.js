import axios from 'axios'

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:5000/api',
  timeout: 8000,
  headers: { 'Content-Type': 'application/json' },
})

client.interceptors.request.use((config) => {
  const token = localStorage.getItem('resource-token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

const response = (request) => request.then((result) => result.data)

export const api = {
  me: () => response(client.get('/auth/me')),
  register: (payload) => response(client.post('/auth/register', payload)),
  login: (payload) => response(client.post('/auth/login', payload)),
  enableRole: (role) => response(client.post('/auth/roles', { role })),
  dashboard: (role) => response(client.get(`/dashboard/${role}`)),
  demand: () => response(client.get('/demand')),
  requirements: () => response(client.get('/requirements')),
  createRequirement: (payload) => response(client.post('/requirements', payload)),
  packets: () => response(client.get('/packets')),
  packet: (reference) => response(client.get(`/packets/${reference}`)),
  approvePacket: (reference) => response(client.post(`/packets/${reference}/approve`)),
  inventory: () => response(client.get('/inventory')),
  createInventory: (payload) => response(client.post('/inventory', payload)),
  marketplace: (params = {}) => response(client.get('/marketplace', { params })),
  createPayPalOrder: (packetReference) => response(client.post('/payments/paypal/order', { packet_reference: packetReference })),
  createIntent: (prompt, constraints) => response(client.post('/guardrail/intents', { prompt, constraints })),
  verifyIntent: (intentId, checkoutPayload) => response(client.post('/guardrail/verify', { intent_id: intentId, checkout_payload: checkoutPayload })),
  authorizeIntent: (verificationId) => response(client.post('/guardrail/authorize', { verification_id: verificationId })),
  mcpTools: () => response(client.get('/guardrail/mcp/tools')),
  createRoute: (payload) => response(client.post('/liquidity/routes', payload)),
  routes: () => response(client.get('/liquidity/routes')),
  executeRoute: (reference, payload) => response(client.post(`/liquidity/routes/${reference}/execute`, payload)),
}
