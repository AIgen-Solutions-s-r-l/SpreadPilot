<template>
  <Layout>
    <div class="sm:flex sm:items-center">
      <div class="sm:flex-auto">
        <h1 class="text-xl font-semibold text-gray-900">System Logs</h1>
        <p class="mt-2 text-sm text-gray-700">Real-time system logs and events.</p>
      </div>
      <div class="mt-4 sm:mt-0 sm:ml-16 sm:flex-none">
        <button @click="refreshLogs" type="button" class="inline-flex items-center justify-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2">
          <svg class="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Refresh
        </button>
      </div>
    </div>

    <!-- Filters -->
    <div class="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
      <div>
        <label for="level" class="block text-sm font-medium text-gray-700">Level</label>
        <select v-model="filters.level" id="level" name="level" class="mt-1 block w-full rounded-md border-gray-300 py-2 pl-3 pr-10 text-base focus:border-indigo-500 focus:outline-none focus:ring-indigo-500 sm:text-sm">
          <option value="">All levels</option>
          <option value="debug">Debug</option>
          <option value="info">Info</option>
          <option value="warning">Warning</option>
          <option value="error">Error</option>
        </select>
      </div>
      <div>
        <label for="service" class="block text-sm font-medium text-gray-700">Service</label>
        <select v-model="filters.service" id="service" name="service" class="mt-1 block w-full rounded-md border-gray-300 py-2 pl-3 pr-10 text-base focus:border-indigo-500 focus:outline-none focus:ring-indigo-500 sm:text-sm">
          <option value="">All services</option>
          <option value="trading-bot">Trading Bot</option>
          <option value="admin-api">Admin API</option>
          <option value="alert-router">Alert Router</option>
          <option value="report-worker">Report Worker</option>
        </select>
      </div>
      <div>
        <label for="search" class="block text-sm font-medium text-gray-700">Search</label>
        <input v-model="filters.search" type="text" name="search" id="search" class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm" placeholder="Search logs...">
      </div>
    </div>

    <!-- Logs list -->
    <div class="mt-6 bg-gray-900 rounded-lg overflow-hidden">
      <div class="px-4 py-3 border-b border-gray-800">
        <div class="flex items-center justify-between">
          <h3 class="text-sm font-medium text-gray-300">Log Output</h3>
          <span class="text-xs text-gray-500">{{ logs.length }} entries</span>
        </div>
      </div>
      <div class="h-96 overflow-y-auto">
        <div v-if="loading" class="p-4 text-center">
          <svg class="inline-block animate-spin h-6 w-6 text-gray-400" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        </div>
        <div v-else-if="logs.length === 0" class="p-4 text-center text-gray-500">
          No logs found
        </div>
        <div v-else class="divide-y divide-gray-800">
          <div v-for="log in filteredLogs" :key="log.id" class="px-4 py-2 hover:bg-gray-800">
            <div class="flex items-start space-x-3">
              <span :class="[
                'flex-shrink-0 inline-block px-2 py-0.5 text-xs font-medium rounded',
                getLevelColor(log.level)
              ]">
                {{ log.level }}
              </span>
              <div class="flex-1 min-w-0">
                <p class="text-sm text-gray-300">
                  <span class="font-medium">{{ log.service }}</span>
                  <span class="mx-2 text-gray-600">•</span>
                  <span class="text-gray-500">{{ formatTimestamp(log.timestamp) }}</span>
                </p>
                <p class="mt-1 text-sm text-gray-400 break-all">{{ log.message }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Layout>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import Layout from '../components/Layout.vue'
import { logsService } from '../services/api'

const logs = ref([])
const loading = ref(false)
const error = ref('')
let pollInterval = null

const filters = ref({
  level: '',
  service: '',
  search: ''
})

const filteredLogs = computed(() => {
  return logs.value.filter(log => {
    if (filters.value.level && log.level !== filters.value.level) return false
    if (filters.value.service && log.service !== filters.value.service) return false
    if (filters.value.search && !log.message.toLowerCase().includes(filters.value.search.toLowerCase())) return false
    return true
  })
})

const getLevelColor = (level) => {
  switch (level) {
    case 'debug': return 'bg-gray-700 text-gray-300'
    case 'info': return 'bg-blue-900 text-blue-300'
    case 'warning': return 'bg-yellow-900 text-yellow-300'
    case 'error': return 'bg-red-900 text-red-300'
    default: return 'bg-gray-700 text-gray-300'
  }
}

const formatTimestamp = (timestamp) => {
  return new Date(timestamp).toLocaleString()
}

const fetchLogs = async () => {
  loading.value = true
  error.value = ''
  
  try {
    const response = await logsService.getAll({
      limit: 100,
      ...filters.value
    })
    logs.value = response.data
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

const refreshLogs = () => {
  fetchLogs()
}

const startPolling = () => {
  pollInterval = setInterval(fetchLogs, 5000) // Poll every 5 seconds
}

const stopPolling = () => {
  if (pollInterval) {
    clearInterval(pollInterval)
    pollInterval = null
  }
}

onMounted(() => {
  fetchLogs()
  startPolling()
})

onUnmounted(() => {
  stopPolling()
})
</script>