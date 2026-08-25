import { defineStore } from 'pinia'

export const useUiStore = defineStore('ui', {
  state: () => ({
    sidebarCollapsed: false,
    isMobile: false,
  }),
  actions: {
    toggleSidebar() {
      this.sidebarCollapsed = !this.sidebarCollapsed
    },
    setMobile(value: boolean) {
      this.isMobile = value
      if (value) this.sidebarCollapsed = true
    },
  },
})
