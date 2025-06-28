<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Mobile menu -->
    <div v-if="mobileMenuOpen" class="fixed inset-0 z-40 md:hidden">
      <div class="fixed inset-0 bg-gray-600 bg-opacity-75" @click="mobileMenuOpen = false"></div>
      <div class="relative flex flex-col flex-1 w-full max-w-xs bg-white">
        <div class="absolute top-0 right-0 pt-2 -mr-12">
          <button @click="mobileMenuOpen = false" class="flex items-center justify-center w-10 h-10 ml-1 rounded-full focus:outline-none focus:ring-2 focus:ring-inset focus:ring-white">
            <span class="sr-only">Close sidebar</span>
            <svg class="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div class="flex-1 h-0 pt-5 pb-4 overflow-y-auto">
          <div class="flex items-center flex-shrink-0 px-4">
            <h1 class="text-xl font-semibold">SpreadPilot Admin</h1>
          </div>
          <nav class="px-2 mt-5 space-y-1">
            <router-link v-for="item in navigation" :key="item.name" :to="item.href" 
              :class="[isActive(item.href) ? 'bg-gray-100 text-gray-900' : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900',
                'group flex items-center px-2 py-2 text-base font-medium rounded-md']"
              @click="mobileMenuOpen = false">
              <component :is="item.icon" class="flex-shrink-0 w-6 h-6 mr-4" :class="[isActive(item.href) ? 'text-gray-500' : 'text-gray-400 group-hover:text-gray-500']" />
              {{ item.name }}
            </router-link>
          </nav>
        </div>
        <div class="flex flex-shrink-0 p-4 border-t border-gray-200">
          <button @click="logout" class="flex items-center w-full px-2 py-2 text-sm font-medium text-gray-600 rounded-md hover:bg-gray-50 hover:text-gray-900">
            <svg class="w-5 h-5 mr-3 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
            Logout
          </button>
        </div>
      </div>
    </div>

    <!-- Desktop sidebar -->
    <div class="hidden md:fixed md:inset-y-0 md:flex md:w-64 md:flex-col">
      <div class="flex flex-col flex-1 min-h-0 bg-white border-r border-gray-200">
        <div class="flex flex-col flex-1 pt-5 pb-4 overflow-y-auto">
          <div class="flex items-center flex-shrink-0 px-4">
            <h1 class="text-xl font-semibold">SpreadPilot Admin</h1>
          </div>
          <nav class="flex-1 px-2 mt-5 space-y-1">
            <router-link v-for="item in navigation" :key="item.name" :to="item.href"
              :class="[isActive(item.href) ? 'bg-gray-100 text-gray-900' : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900',
                'group flex items-center px-2 py-2 text-sm font-medium rounded-md']">
              <component :is="item.icon" class="flex-shrink-0 w-5 h-5 mr-3" :class="[isActive(item.href) ? 'text-gray-500' : 'text-gray-400 group-hover:text-gray-500']" />
              {{ item.name }}
            </router-link>
          </nav>
        </div>
        <div class="flex flex-shrink-0 p-4 border-t border-gray-200">
          <button @click="logout" class="flex items-center w-full px-2 py-2 text-sm font-medium text-gray-600 rounded-md hover:bg-gray-50 hover:text-gray-900">
            <svg class="w-5 h-5 mr-3 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
            Logout
          </button>
        </div>
      </div>
    </div>

    <!-- Main content -->
    <div class="flex flex-col flex-1 md:pl-64">
      <!-- Mobile header -->
      <div class="sticky top-0 z-10 flex flex-shrink-0 h-16 bg-white shadow md:hidden">
        <button @click="mobileMenuOpen = true" class="px-4 text-gray-500 border-r border-gray-200 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-indigo-500">
          <span class="sr-only">Open sidebar</span>
          <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
        <div class="flex items-center justify-between flex-1 px-4">
          <h2 class="text-lg font-medium">{{ currentPageTitle }}</h2>
        </div>
      </div>

      <!-- Desktop header -->
      <div class="hidden md:flex md:flex-shrink-0 md:h-16 md:bg-white md:shadow">
        <div class="flex items-center justify-between flex-1 px-4">
          <h2 class="text-lg font-medium">{{ currentPageTitle }}</h2>
        </div>
      </div>

      <!-- Page content -->
      <main class="flex-1">
        <div class="py-6">
          <div class="px-4 mx-auto max-w-7xl sm:px-6 md:px-8">
            <slot />
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const mobileMenuOpen = ref(false)

const navigation = [
  { name: 'Followers', href: '/followers', icon: 'UsersIcon' },
  { name: 'Logs', href: '/logs', icon: 'DocumentTextIcon' },
  { name: 'Settings', href: '/settings', icon: 'CogIcon' },
]

const currentPageTitle = computed(() => {
  return route.name || 'Dashboard'
})

const isActive = (path) => {
  return route.path === path
}

const logout = () => {
  localStorage.removeItem('authToken')
  router.push('/login')
}

// Simple icon components
const UsersIcon = {
  template: `<svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
  </svg>`
}

const DocumentTextIcon = {
  template: `<svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
  </svg>`
}

const CogIcon = {
  template: `<svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
  </svg>`
}

// Register icon components
navigation.forEach(item => {
  if (item.name === 'Followers') item.icon = UsersIcon
  if (item.name === 'Logs') item.icon = DocumentTextIcon
  if (item.name === 'Settings') item.icon = CogIcon
})
</script>