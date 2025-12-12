<template>
  <div class="folder-tree">
    <div
      v-for="folder in foldersList"
      :key="folder.id"
      class="folder-item"
      :class="{ 'folder-selected': selectedId === folder.id }"
    >
      <div
        class="folder-row"
        @click="selectFolder(folder)"
        :style="{ paddingLeft: `${level * 1.5}rem` }"
      >
        <ChevronRight
          v-if="hasChildren(folder)"
          :class="['folder-chevron', { 'folder-chevron-open': isExpanded(folder.id) }]"
          @click.stop="toggleExpand(folder.id)"
          :size="16"
        />
        <Folder :size="16" class="folder-icon" />
        <span class="folder-name">{{ folder.name || 'Unnamed Folder' }}</span>
      </div>
      <div v-if="isExpanded(folder.id) && folder.children && Array.isArray(folder.children) && folder.children.length > 0">
        <FolderTree
          :folders="folder.children"
          :selected-id="selectedId"
          :level="level + 1"
          @select="handleSelect"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { Folder, ChevronRight } from 'lucide-vue-next'

const props = defineProps({
  folders: {
    type: Array,
    default: () => []
  },
  selectedId: {
    type: Number,
    default: null
  },
  level: {
    type: Number,
    default: 0
  }
})

// Ensure folders is always an array
const foldersList = computed(() => {
  return Array.isArray(props.folders) ? props.folders : []
})

const emit = defineEmits(['select'])

const expanded = ref(new Set())

const hasChildren = (folder) => {
  return folder.children && Array.isArray(folder.children) && folder.children.length > 0
}

const isExpanded = (folderId) => {
  return expanded.value.has(folderId)
}

const toggleExpand = (folderId) => {
  if (expanded.value.has(folderId)) {
    expanded.value.delete(folderId)
  } else {
    expanded.value.add(folderId)
  }
}

const selectFolder = (folder) => {
  emit('select', folder)
}

const handleSelect = (folder) => {
  emit('select', folder)
}
</script>

<style scoped>
.folder-tree {
  user-select: none;
}

.folder-item {
  margin-bottom: 0.25rem;
}

.folder-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
}

.folder-row:hover {
  background: var(--bg-light);
}

.folder-selected .folder-row {
  background: var(--primary-light);
  color: var(--primary);
}

.folder-chevron {
  transition: transform 0.2s;
  cursor: pointer;
  color: #666;
}

.folder-chevron-open {
  transform: rotate(90deg);
}

.folder-icon {
  color: #666;
  flex-shrink: 0;
}

.folder-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>

