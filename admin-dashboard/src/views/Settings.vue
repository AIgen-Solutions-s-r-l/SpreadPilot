<template>
  <Layout>
    <div class="sm:flex sm:items-center">
      <div class="sm:flex-auto">
        <h1 class="text-xl font-semibold text-gray-900">Settings</h1>
        <p class="mt-2 text-sm text-gray-700">Manage your system configuration and preferences.</p>
      </div>
    </div>

    <div v-if="loading" class="mt-8 text-center">
      <svg class="inline-block animate-spin h-8 w-8 text-gray-400" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
    </div>

    <form v-else @submit.prevent="saveSettings" class="mt-8 space-y-8 divide-y divide-gray-200">
      <!-- General Settings -->
      <div>
        <div>
          <h3 class="text-lg font-medium leading-6 text-gray-900">General Settings</h3>
          <p class="mt-1 text-sm text-gray-500">Basic system configuration.</p>
        </div>
        <div class="mt-6 grid grid-cols-1 gap-y-6 gap-x-4 sm:grid-cols-6">
          <div class="sm:col-span-3">
            <label for="system-name" class="block text-sm font-medium text-gray-700">System Name</label>
            <div class="mt-1">
              <input v-model="settings.systemName" type="text" name="system-name" id="system-name" class="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm">
            </div>
          </div>
          <div class="sm:col-span-3">
            <label for="admin-email" class="block text-sm font-medium text-gray-700">Admin Email</label>
            <div class="mt-1">
              <input v-model="settings.adminEmail" type="email" name="admin-email" id="admin-email" class="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm">
            </div>
          </div>
        </div>
      </div>

      <!-- Trading Settings -->
      <div class="pt-8">
        <div>
          <h3 class="text-lg font-medium leading-6 text-gray-900">Trading Settings</h3>
          <p class="mt-1 text-sm text-gray-500">Configure trading parameters and thresholds.</p>
        </div>
        <div class="mt-6 grid grid-cols-1 gap-y-6 gap-x-4 sm:grid-cols-6">
          <div class="sm:col-span-3">
            <label for="time-value-threshold" class="block text-sm font-medium text-gray-700">Time Value Threshold</label>
            <div class="mt-1">
              <div class="relative rounded-md shadow-sm">
                <div class="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                  <span class="text-gray-500 sm:text-sm">$</span>
                </div>
                <input v-model="settings.timeValueThreshold" type="number" step="0.01" name="time-value-threshold" id="time-value-threshold" class="block w-full rounded-md border-gray-300 pl-7 pr-12 focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm" placeholder="0.10">
              </div>
            </div>
            <p class="mt-2 text-sm text-gray-500">Positions below this value will be marked as critical.</p>
          </div>
          <div class="sm:col-span-3">
            <label for="poll-interval" class="block text-sm font-medium text-gray-700">Poll Interval (seconds)</label>
            <div class="mt-1">
              <input v-model="settings.pollInterval" type="number" name="poll-interval" id="poll-interval" class="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm">
            </div>
            <p class="mt-2 text-sm text-gray-500">How often to check for updates.</p>
          </div>
        </div>
      </div>

      <!-- Notification Settings -->
      <div class="pt-8">
        <div>
          <h3 class="text-lg font-medium leading-6 text-gray-900">Notifications</h3>
          <p class="mt-1 text-sm text-gray-500">Configure alert and notification preferences.</p>
        </div>
        <div class="mt-6 space-y-6">
          <div class="flex items-start">
            <div class="flex h-5 items-center">
              <input v-model="settings.emailNotifications" id="email-notifications" name="email-notifications" type="checkbox" class="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500">
            </div>
            <div class="ml-3 text-sm">
              <label for="email-notifications" class="font-medium text-gray-700">Email notifications</label>
              <p class="text-gray-500">Receive email alerts for critical events.</p>
            </div>
          </div>
          <div class="flex items-start">
            <div class="flex h-5 items-center">
              <input v-model="settings.pushNotifications" id="push-notifications" name="push-notifications" type="checkbox" class="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500">
            </div>
            <div class="ml-3 text-sm">
              <label for="push-notifications" class="font-medium text-gray-700">Push notifications</label>
              <p class="text-gray-500">Receive browser push notifications.</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Save button -->
      <div class="pt-5">
        <div class="flex justify-end">
          <button type="button" @click="resetSettings" class="rounded-md border border-gray-300 bg-white py-2 px-4 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2">
            Reset
          </button>
          <button type="submit" :disabled="saving" class="ml-3 inline-flex justify-center rounded-md border border-transparent bg-indigo-600 py-2 px-4 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed">
            {{ saving ? 'Saving...' : 'Save' }}
          </button>
        </div>
      </div>
    </form>

    <!-- Success message -->
    <div v-if="successMessage" class="mt-4 rounded-md bg-green-50 p-4">
      <div class="flex">
        <div class="flex-shrink-0">
          <svg class="h-5 w-5 text-green-400" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
          </svg>
        </div>
        <div class="ml-3">
          <p class="text-sm text-green-800">{{ successMessage }}</p>
        </div>
      </div>
    </div>

    <!-- Error message -->
    <div v-if="error" class="mt-4 rounded-md bg-red-50 p-4">
      <div class="flex">
        <div class="flex-shrink-0">
          <svg class="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
          </svg>
        </div>
        <div class="ml-3">
          <p class="text-sm text-red-800">{{ error }}</p>
        </div>
      </div>
    </div>
  </Layout>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import Layout from '../components/Layout.vue'
import { settingsService } from '../services/api'

const settings = ref({
  systemName: '',
  adminEmail: '',
  timeValueThreshold: 0.10,
  pollInterval: 30,
  emailNotifications: true,
  pushNotifications: false
})

const loading = ref(false)
const saving = ref(false)
const error = ref('')
const successMessage = ref('')

const fetchSettings = async () => {
  loading.value = true
  error.value = ''
  
  try {
    const response = await settingsService.get()
    settings.value = response.data
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

const saveSettings = async () => {
  saving.value = true
  error.value = ''
  successMessage.value = ''
  
  try {
    await settingsService.update(settings.value)
    successMessage.value = 'Settings saved successfully!'
    setTimeout(() => {
      successMessage.value = ''
    }, 3000)
  } catch (err) {
    error.value = err.message
  } finally {
    saving.value = false
  }
}

const resetSettings = () => {
  fetchSettings()
  successMessage.value = ''
}

onMounted(() => {
  fetchSettings()
})
</script>