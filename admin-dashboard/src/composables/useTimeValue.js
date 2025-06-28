import { ref, computed, onMounted, onUnmounted } from 'vue'
import { followersService } from '../services/api'

export function useTimeValue(followerId) {
  const timeValue = ref(null)
  const loading = ref(false)
  const error = ref(null)
  let intervalId = null

  const riskLevel = computed(() => {
    if (!timeValue.value) return 'UNKNOWN'
    
    const value = parseFloat(timeValue.value)
    if (value >= 0.10) return 'SAFE'
    if (value >= 0.05) return 'RISK'
    return 'CRITICAL'
  })

  const riskColor = computed(() => {
    switch (riskLevel.value) {
      case 'SAFE': return 'text-green-600 bg-green-100'
      case 'RISK': return 'text-yellow-600 bg-yellow-100'
      case 'CRITICAL': return 'text-red-600 bg-red-100'
      default: return 'text-gray-600 bg-gray-100'
    }
  })

  const fetchTimeValue = async () => {
    if (!followerId) return
    
    try {
      loading.value = true
      const response = await followersService.getPnL(followerId)
      timeValue.value = response.data.timeValue
      error.value = null
    } catch (err) {
      error.value = err.message
      console.error('Failed to fetch time value:', err)
    } finally {
      loading.value = false
    }
  }

  const startPolling = (interval = 30000) => {
    fetchTimeValue()
    intervalId = setInterval(fetchTimeValue, interval)
  }

  const stopPolling = () => {
    if (intervalId) {
      clearInterval(intervalId)
      intervalId = null
    }
  }

  onMounted(() => {
    startPolling()
  })

  onUnmounted(() => {
    stopPolling()
  })

  return {
    timeValue,
    loading,
    error,
    riskLevel,
    riskColor,
    fetchTimeValue,
    startPolling,
    stopPolling
  }
}