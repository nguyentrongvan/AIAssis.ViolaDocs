<template>
  <div class="admin-page">
    <h1 class="page-header">Reports</h1>
      <div class="report-filters">
        <div class="filter-group">
          <label>Report Type</label>
          <select v-model="reportType">
            <option value="audit">Audit Log</option>
            <option value="usage">Usage Statistics</option>
            <option value="workflow">Workflow SLA</option>
            <option value="quality">Data Quality</option>
          </select>
        </div>
        <div class="filter-group">
          <label>Date From</label>
          <input v-model="dateFrom" type="date" />
        </div>
        <div class="filter-group">
          <label>Date To</label>
          <input v-model="dateTo" type="date" />
        </div>
        <button @click="generateReport" class="btn-primary">Generate</button>
        <button @click="exportReport" class="btn-secondary">Export</button>
      </div>
      <div v-if="reportData" class="report-content">
        <div class="report-stats">
          <div v-for="(value, key) in reportData.summary" :key="key" class="stat-item">
            <div class="stat-label">{{ key }}</div>
            <div class="stat-value">{{ value }}</div>
          </div>
        </div>
        <div v-if="reportData.items" class="report-table">
          <table>
            <thead>
              <tr>
                <th v-for="col in reportColumns" :key="col">{{ col }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, idx) in reportData.items" :key="idx">
                <td v-for="col in reportColumns" :key="col">{{ item[col] }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import api from '../../services/api'

const reportType = ref('audit')
const dateFrom = ref('')
const dateTo = ref('')
const reportData = ref(null)

const reportColumns = computed(() => {
  if (!reportData.value?.items?.[0]) return []
  return Object.keys(reportData.value.items[0])
})

const generateReport = async () => {
  try {
    const res = await api.get(`/reports/${reportType.value}`, {
      params: {
        from: dateFrom.value,
        to: dateTo.value
      }
    })
    if (res.is_success) {
      reportData.value = res.data
    }
  } catch (e) {
    console.error('Failed to generate report', e)
  }
}

const exportReport = async () => {
  try {
    const res = await api.post(`/reports/${reportType.value}/export`, {
      from: dateFrom.value,
      to: dateTo.value,
      format: 'csv'
    }, { responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([res]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `report_${reportType.value}_${Date.now()}.csv`)
    document.body.appendChild(link)
    link.click()
    link.remove()
  } catch (e) {
    console.error('Failed to export report', e)
  }
}
</script>

<style scoped>
.admin-page {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}
.report-filters {
  display: flex;
  gap: 1rem;
  align-items: flex-end;
  margin-bottom: 2rem;
  padding-bottom: 2rem;
  border-bottom: 1px solid #eee;
}
.filter-group {
  display: flex;
  flex-direction: column;
}
.filter-group label {
  margin-bottom: 0.5rem;
  font-weight: 500;
}
.filter-group input,
.filter-group select {
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 6px;
}
.report-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}
.stat-item {
  background: var(--bg-light);
  padding: 1rem;
  border-radius: 8px;
  text-align: center;
}
.stat-label {
  font-size: 0.9rem;
  color: #666;
  margin-bottom: 0.5rem;
}
.stat-value {
  font-size: 1.5rem;
  font-weight: bold;
  color: var(--primary);
}
.report-table {
  overflow-x: auto;
}
.report-table table {
  width: 100%;
  border-collapse: collapse;
}
.report-table th,
.report-table td {
  padding: 0.75rem;
  text-align: left;
  border-bottom: 1px solid #eee;
}
.report-table th {
  font-weight: 600;
  background: var(--bg-light);
}
</style>

