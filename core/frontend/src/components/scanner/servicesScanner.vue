<template>
  <span />
</template>

<script lang="ts">
import Vue from 'vue'
import axios from 'axios'
import { getModule } from 'vuex-module-decorators'
import ServicesScannerStore from '@/store/servicesScanner'
import {Service} from '@/types/SERVICE'

const servicesHelper: ServicesScannerStore = getModule(ServicesScannerStore)

/**
 * Actual scanner for running services.
 * This periodically fetches /helper/latest/web_services
 * and updates the ServiceHelperStore with the available services
 * @displayName Services Scanner
 */
export default Vue.extend({
  name: 'ServicesFetcher',
  data () {
    return {
      interval: 0,
    }
  },
  mounted () {
    // Fetch network data
    this.requestData()

    // Fetch periodic API request
    this.startPeriodicRequest()
  },
  beforeDestroy () {
    clearInterval(this.interval)
  },
  methods: {
    startPeriodicRequest () {
      this.interval = setInterval(() => {
        this.requestData()
      }, 5000)
    },
    requestData () {
      axios.get('/helper/latest/web_services').then((response) => {
        // Sort services by port number
        const services = response.data.sort(
          (first: Service, second: Service) => first.port - second.port,
        )
        servicesHelper.updateFoundServices(services)
      }).catch((error) => {
        console.log('Error scanning for services:')
        // logging the error as a whole gives us a better backtrace
        console.log(error)
        servicesHelper.updateFoundServices([])
      })
    },
  },
})
</script>

<style scoped>
.helper-table {
    max-width: 70%;
    margin: auto;
}
</style>
