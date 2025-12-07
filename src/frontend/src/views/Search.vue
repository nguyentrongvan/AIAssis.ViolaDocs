<template>
  <div class="search-page">
    <h1 class="page-header">Search Documents</h1>
      <div class="search-bar">
        <input v-model="query" @keyup.enter="doSearch" placeholder="Search documents..." class="search-input" />
        <div class="search-mode">
          <label><input type="radio" v-model="mode" value="keyword" /> Keyword</label>
          <label><input type="radio" v-model="mode" value="vector" /> Semantic</label>
          <label><input type="radio" v-model="mode" value="hybrid" /> Hybrid</label>
        </div>
        <button @click="doSearch" class="btn-primary">Search</button>
      </div>
      <div v-if="results.length > 0" class="results">
        <div v-for="doc in results" :key="doc.id" class="result-card" @click="$router.push(`/documents/${doc.id}`)">
          <h3>{{ doc.title }}</h3>
          <p class="meta">By {{ doc.owner?.name }} • {{ formatDate(doc.created_at) }}</p>
          <p v-if="doc.snippet" class="snippet" v-html="doc.snippet"></p>
          <div class="tags">
            <span v-for="tag in doc.tags" :key="tag" class="tag">{{ tag }}</span>
          </div>
        </div>
      </div>
      <div v-else-if="searched" class="no-results">
        No documents found
      </div>
    </div>
</template>

<script setup>
import { ref } from 'vue'
import api from '../services/api'

const query = ref('')
const mode = ref('hybrid')
const results = ref([])
const searched = ref(false)

const doSearch = async () => {
  if (!query.value.trim()) return
  try {
    const res = await api.post('/search', {
      query: query.value,
      mode: mode.value
    })
    if (res.is_success) {
      results.value = res.data.results || []
      searched.value = true
    }
  } catch (e) {
    console.error('Search failed', e)
  }
}

const formatDate = (dateStr) => {
  return new Date(dateStr).toLocaleDateString()
}
</script>

<style scoped>
.search-page {
  max-width: 1000px;
  margin: 0 auto;
}
.search-bar {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  margin-bottom: 2rem;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}
.search-input {
  width: 100%;
  padding: 0.75rem;
  font-size: 1rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  margin-bottom: 1rem;
}
.search-mode {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
}
.search-mode label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.results {
  display: grid;
  gap: 1rem;
}
.result-card {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
  cursor: pointer;
  transition: transform 0.2s;
}
.result-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0,0,0,0.1);
}
.result-card h3 {
  margin: 0 0 0.5rem 0;
  color: var(--primary);
}
.meta {
  color: #666;
  font-size: 0.9rem;
  margin-bottom: 0.5rem;
}
.snippet {
  color: #333;
  margin-bottom: 1rem;
}
.tags {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.tag {
  background: var(--primary-light);
  color: var(--primary);
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.85rem;
}
.no-results {
  text-align: center;
  padding: 3rem;
  color: #666;
}
</style>

