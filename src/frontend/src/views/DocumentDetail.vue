<template>
  <div v-if="loading" class="loading">{{ $t('common.loading') }}</div>
  <div v-else-if="document" class="document-detail">
    <div class="page-header">
      <div>
        <h1>{{ document?.title || $t('nav.documents') }}</h1>
        <StatusBadge :status="document.status" />
      </div>
      <div class="header-actions">
        <button
          @click="confirmDelete"
          class="btn-danger"
        >
          <Trash2 :size="16" />
          {{ $t('common.delete') }}
        </button>
      </div>
    </div>


    <div class="detail-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        @click="activeTab = tab.id"
        :class="['tab-btn', { 'tab-btn-active': activeTab === tab.id }]"
      >
        {{ tab.label }}
      </button>
    </div>

    <div class="detail-content">
      <!-- Preview Tab -->
      <div v-if="activeTab === 'preview'" class="tab-content">
        <div class="preview-controls">
          <div class="preview-options">
            <button
              v-if="!isOfficeOrTextFile"
              @click="showOcrText = !showOcrText"
              :class="['btn-small', { 'btn-active': showOcrText }]"
            >
              {{ showOcrText ? $t('common.hide') : $t('common.show') }} {{ $t('documentDetail.ocrText') }}
            </button>
            <select v-model="selectedVersion" @change="loadVersionPreview" class="version-select">
              <option v-for="v in versions" :key="v.id" :value="v.id">
                {{ $t('documentDetail.version') }} {{ v.version_no }}
              </option>
            </select>
          </div>
        </div>
        <div class="preview-area">
          <!-- For PDF and Images: use iframe -->
          <iframe 
            v-if="canPreviewInIframe && previewUrl && !showOcrText" 
            :src="previewUrl" 
            class="preview-frame"
          ></iframe>
          <!-- For Office files and text: show extracted text -->
          <div v-else-if="showOcrText || isOfficeOrTextFile" class="ocr-text-view">
            <div v-if="ocrText" class="ocr-text-content">
              <div class="ocr-text-header">
                <span>{{ isOfficeOrTextFile ? $t('documentDetail.documentContent') : $t('documentDetail.ocrText') }}</span>
                <div class="text-actions">
                  <button @click="copyOcrText" class="btn-small">
                    <Copy :size="14" />
                    {{ $t('common.copy') }}
                  </button>
                  <button 
                    v-if="isOfficeOrTextFile && previewUrl"
                    @click="downloadOriginal" 
                    class="btn-small"
                  >
                    <Download :size="14" />
                    {{ $t('documentDetail.downloadOriginal') }}
                  </button>
                </div>
              </div>
              <pre class="ocr-text-pre">{{ ocrText }}</pre>
            </div>
            <div v-else class="ocr-text-empty">
              <p>{{ isOfficeOrTextFile ? $t('documentDetail.contentNotAvailable') : $t('documentDetail.ocrTextNotAvailable') }}</p>
            </div>
          </div>
          <div v-else class="preview-placeholder">{{ $t('documentDetail.previewNotAvailable') }}</div>
        </div>
      </div>

      <!-- Metadata Tab -->
      <div v-if="activeTab === 'metadata'" class="tab-content">
        <!-- Editable Metadata Form -->
        <div class="metadata-section">
          <h3>{{ $t('documentDetail.documentInformation') }}</h3>
          <div class="metadata-form">
            <div class="form-group">
              <label>{{ $t('common.title') }} *</label>
              <input v-model="metadataForm.title" />
            </div>
            <div class="form-group">
              <label>{{ $t('common.folder') }}</label>
              <select v-model.number="metadataForm.folder_id">
                <option :value="null">{{ $t('common.none') }}</option>
                <option v-for="f in folders" :key="f.id" :value="f.id">
                  {{ f.name }}
                </option>
              </select>
            </div>
            <div class="form-group">
              <label>{{ $t('upload.retentionPolicy') }}</label>
              <select v-model.number="metadataForm.retention_policy_id">
                <option :value="null">{{ $t('upload.default') }}</option>
                <option
                  v-for="p in retentionPolicies"
                  :key="p.id"
                  :value="p.id"
                >
                  {{ p.name }} ({{ p.duration_days }} {{ $t('upload.days') }})
                </option>
              </select>
            </div>
            <div class="form-group">
              <label>{{ $t('common.tags') }}</label>
              <input
                v-model="tagInput"
                @keyup.enter="addTag"
                :placeholder="$t('documentDetail.pressEnterToAddTag')"
              />
              <div class="tags-list">
                <span
                  v-for="tag in metadataForm.tags"
                  :key="tag"
                  class="tag-badge"
                >
                  {{ tag }}
                  <button @click="removeTag(tag)" class="tag-remove">×</button>
                </span>
              </div>
            </div>
            <div class="form-group">
              <label>{{ $t('documentDetail.owner') }}</label>
              <span>{{ document.owner?.name || $t('common.unknown') }}</span>
            </div>
            <div class="form-group">
              <label>{{ $t('documentDetail.created') }}</label>
              <span>{{ formatDate(document.created_at) }}</span>
            </div>
            <div class="form-group">
              <label>{{ $t('common.size') }}</label>
              <span>{{ formatSize(document.size) }}</span>
            </div>
            <div class="form-actions">
              <button @click="saveMetadata" class="btn-primary">{{ $t('documentDetail.saveChanges') }}</button>
            </div>
          </div>
        </div>

        <!-- Extracted File Metadata -->
        <div v-if="document.metadata" class="metadata-section">
          <h3>{{ $t('documentDetail.fileMetadata') }}</h3>
          <div class="extracted-metadata">
            <!-- File System Metadata -->
            <div v-if="document.metadata.file" class="metadata-group">
              <h4>{{ $t('documentDetail.fileInformation') }}</h4>
              <div class="metadata-grid">
                <div v-if="document.metadata.file.original_filename" class="metadata-item">
                  <label>{{ $t('documentDetail.originalFilename') }}</label>
                  <span>{{ document.metadata.file.original_filename }}</span>
                </div>
                <div v-if="document.metadata.file.size" class="metadata-item">
                  <label>{{ $t('documentDetail.fileSize') }}</label>
                  <span>{{ formatSize(document.metadata.file.size) }}</span>
                </div>
                <div v-if="document.metadata.file.mime" class="metadata-item">
                  <label>{{ $t('documentDetail.mimeType') }}</label>
                  <span>{{ document.metadata.file.mime }}</span>
                </div>
                <div v-if="document.metadata.file.checksum" class="metadata-item">
                  <label>{{ $t('documentDetail.checksum') }}</label>
                  <span class="monospace">{{ document.metadata.file.checksum }}</span>
                </div>
                <div v-if="document.metadata.file.upload_method" class="metadata-item">
                  <label>{{ $t('documentDetail.uploadMethod') }}</label>
                  <span>{{ document.metadata.file.upload_method }}</span>
                </div>
                <div v-if="document.metadata.file.upload_timestamp" class="metadata-item">
                  <label>{{ $t('documentDetail.uploadTime') }}</label>
                  <span>{{ formatDate(document.metadata.file.upload_timestamp) }}</span>
                </div>
              </div>
            </div>

            <!-- EXIF Metadata (Images) -->
            <div v-if="document.metadata.exif" class="metadata-group">
              <h4>{{ $t('documentDetail.imageExifData') }}</h4>
              <div class="metadata-grid">
                <div v-if="document.metadata.exif.camera_make" class="metadata-item">
                  <label>{{ $t('documentDetail.cameraMake') }}</label>
                  <span>{{ document.metadata.exif.camera_make }}</span>
                </div>
                <div v-if="document.metadata.exif.camera_model" class="metadata-item">
                  <label>{{ $t('documentDetail.cameraModel') }}</label>
                  <span>{{ document.metadata.exif.camera_model }}</span>
                </div>
                <div v-if="document.metadata.exif.date_taken" class="metadata-item">
                  <label>{{ $t('documentDetail.dateTaken') }}</label>
                  <span>{{ document.metadata.exif.date_taken }}</span>
                </div>
                <div v-if="document.metadata.exif.resolution" class="metadata-item">
                  <label>{{ $t('documentDetail.resolution') }}</label>
                  <span>{{ document.metadata.exif.resolution.width }} × {{ document.metadata.exif.resolution.height }}</span>
                  <span v-if="document.metadata.exif.resolution.dpi_x"> ({{ document.metadata.exif.resolution.dpi_x }} DPI)</span>
                </div>
                <div v-if="document.metadata.exif.gps" class="metadata-item">
                  <label>{{ $t('documentDetail.gpsLocation') }}</label>
                  <span>{{ document.metadata.exif.gps.lat }}, {{ document.metadata.exif.gps.lon }}</span>
                </div>
                <div v-if="document.metadata.exif.software" class="metadata-item">
                  <label>{{ $t('documentDetail.software') }}</label>
                  <span>{{ document.metadata.exif.software }}</span>
                </div>
                <div v-if="document.metadata.exif.copyright" class="metadata-item">
                  <label>{{ $t('documentDetail.copyright') }}</label>
                  <span>{{ document.metadata.exif.copyright }}</span>
                </div>
              </div>
            </div>

            <!-- PDF Metadata -->
            <div v-if="document.metadata.pdf" class="metadata-group">
              <h4>{{ $t('documentDetail.pdfProperties') }}</h4>
              <div class="metadata-grid">
                <div v-if="document.metadata.pdf.title" class="metadata-item">
                  <label>{{ $t('common.title') }}:</label>
                  <span>{{ document.metadata.pdf.title }}</span>
                </div>
                <div v-if="document.metadata.pdf.author" class="metadata-item">
                  <label>{{ $t('documentDetail.author') }}</label>
                  <span>{{ document.metadata.pdf.author }}</span>
                </div>
                <div v-if="document.metadata.pdf.subject" class="metadata-item">
                  <label>{{ $t('documentDetail.subject') }}</label>
                  <span>{{ document.metadata.pdf.subject }}</span>
                </div>
                <div v-if="document.metadata.pdf.keywords" class="metadata-item">
                  <label>{{ $t('documentDetail.keywords') }}</label>
                  <span>{{ document.metadata.pdf.keywords }}</span>
                </div>
                <div v-if="document.metadata.pdf.creator" class="metadata-item">
                  <label>{{ $t('documentDetail.creator') }}</label>
                  <span>{{ document.metadata.pdf.creator }}</span>
                </div>
                <div v-if="document.metadata.pdf.producer" class="metadata-item">
                  <label>{{ $t('documentDetail.producer') }}</label>
                  <span>{{ document.metadata.pdf.producer }}</span>
                </div>
                <div v-if="document.metadata.pdf.page_count" class="metadata-item">
                  <label>{{ $t('documentDetail.pageCount') }}</label>
                  <span>{{ document.metadata.pdf.page_count }}</span>
                </div>
                <div v-if="document.metadata.pdf.pdf_version" class="metadata-item">
                  <label>{{ $t('documentDetail.pdfVersion') }}</label>
                  <span>{{ document.metadata.pdf.pdf_version }}</span>
                </div>
                <div v-if="document.metadata.pdf.is_encrypted !== undefined" class="metadata-item">
                  <label>{{ $t('documentDetail.encrypted') }}</label>
                  <span>{{ document.metadata.pdf.is_encrypted ? $t('documentDetail.yes') : $t('documentDetail.no') }}</span>
                </div>
                <div v-if="document.metadata.pdf.creation_date" class="metadata-item">
                  <label>{{ $t('documentDetail.creationDate') }}</label>
                  <span>{{ document.metadata.pdf.creation_date }}</span>
                </div>
                <div v-if="document.metadata.pdf.modification_date" class="metadata-item">
                  <label>{{ $t('documentDetail.modificationDate') }}</label>
                  <span>{{ document.metadata.pdf.modification_date }}</span>
                </div>
              </div>
            </div>

            <!-- Office Document Metadata -->
            <div v-if="document.metadata.office" class="metadata-group">
              <h4>{{ $t('documentDetail.officeDocumentProperties') }}</h4>
              <div class="metadata-grid">
                <div v-if="document.metadata.office.title" class="metadata-item">
                  <label>{{ $t('common.title') }}:</label>
                  <span>{{ document.metadata.office.title }}</span>
                </div>
                <div v-if="document.metadata.office.author" class="metadata-item">
                  <label>{{ $t('documentDetail.author') }}</label>
                  <span>{{ document.metadata.office.author }}</span>
                </div>
                <div v-if="document.metadata.office.subject" class="metadata-item">
                  <label>{{ $t('documentDetail.subject') }}</label>
                  <span>{{ document.metadata.office.subject }}</span>
                </div>
                <div v-if="document.metadata.office.keywords" class="metadata-item">
                  <label>{{ $t('documentDetail.keywords') }}</label>
                  <span>{{ document.metadata.office.keywords }}</span>
                </div>
                <div v-if="document.metadata.office.created_date" class="metadata-item">
                  <label>{{ $t('documentDetail.created') }}:</label>
                  <span>{{ formatDate(document.metadata.office.created_date) }}</span>
                </div>
                <div v-if="document.metadata.office.modified_date" class="metadata-item">
                  <label>{{ $t('documentDetail.modificationDate') }}</label>
                  <span>{{ formatDate(document.metadata.office.modified_date) }}</span>
                </div>
                <div v-if="document.metadata.office.last_modified_by" class="metadata-item">
                  <label>{{ $t('documentDetail.lastModifiedBy') }}</label>
                  <span>{{ document.metadata.office.last_modified_by }}</span>
                </div>
                <div v-if="document.metadata.office.application" class="metadata-item">
                  <label>{{ $t('documentDetail.application') }}</label>
                  <span>{{ document.metadata.office.application }}</span>
                </div>
                <div v-if="document.metadata.office.word_count" class="metadata-item">
                  <label>{{ $t('documentDetail.wordCount') }}</label>
                  <span>{{ document.metadata.office.word_count }}</span>
                </div>
                <div v-if="document.metadata.office.page_count" class="metadata-item">
                  <label>{{ $t('documentDetail.pageCount') }}</label>
                  <span>{{ document.metadata.office.page_count }}</span>
                </div>
                <div v-if="document.metadata.office.sheet_count" class="metadata-item">
                  <label>{{ $t('documentDetail.sheetCount') }}</label>
                  <span>{{ document.metadata.office.sheet_count }}</span>
                </div>
                <div v-if="document.metadata.office.slide_count" class="metadata-item">
                  <label>{{ $t('documentDetail.slideCount') }}</label>
                  <span>{{ document.metadata.office.slide_count }}</span>
                </div>
              </div>
            </div>

            <!-- Processing Metadata -->
            <div v-if="latestVersionMetadata?.processing" class="metadata-group">
              <h4>{{ $t('documentDetail.processingInformation') }}</h4>
              <div class="metadata-grid">
                <div v-if="latestVersionMetadata.processing.ocr_provider" class="metadata-item">
                  <label>{{ $t('documentDetail.ocrProvider') }}</label>
                  <span>{{ latestVersionMetadata.processing.ocr_provider }}</span>
                </div>
                <div v-if="latestVersionMetadata.processing.ocr_confidence" class="metadata-item">
                  <label>{{ $t('documentDetail.ocrConfidence') }}</label>
                  <span>{{ (latestVersionMetadata.processing.ocr_confidence * 100).toFixed(1) }}%</span>
                </div>
                <div v-if="latestVersionMetadata.processing.text_extraction_method" class="metadata-item">
                  <label>{{ $t('documentDetail.textExtractionMethod') }}</label>
                  <span>{{ latestVersionMetadata.processing.text_extraction_method }}</span>
                </div>
                <div v-if="latestVersionMetadata.processing.processing_time_ms" class="metadata-item">
                  <label>{{ $t('documentDetail.processingTime') }}</label>
                  <span>{{ latestVersionMetadata.processing.processing_time_ms }}{{ $t('documentDetail.milliseconds') }}</span>
                </div>
                <div v-if="latestVersionMetadata.processing.text_length" class="metadata-item">
                  <label>{{ $t('documentDetail.extractedTextLength') }}</label>
                  <span>{{ latestVersionMetadata.processing.text_length }} {{ $t('documentDetail.characters') }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Comments Tab -->
      <div v-if="activeTab === 'comments'" class="tab-content">
        <div class="comments-section">
          <div class="comments-list">
            <div
              v-for="comment in comments"
              :key="comment.id"
              class="comment-item"
              :class="{ 'comment-annotation': comment.type === 'annotation' }"
            >
              <div class="comment-header">
                <div class="comment-author">
                  <User :size="16" />
                  <span>{{ comment.user?.name || $t('documentDetail.unknown') }}</span>
                </div>
                <span class="comment-date">{{ formatDate(comment.created_at) }}</span>
                <button
                  v-if="comment.user_id === authStore.user?.id"
                  @click="deleteComment(comment.id)"
                  class="btn-link-small"
                >
                  <Trash2 :size="14" />
                </button>
              </div>
              <div class="comment-content">{{ comment.content }}</div>
              <div v-if="comment.position" class="comment-position">
                {{ $t('documentDetail.position') }} {{ JSON.stringify(comment.position) }}
              </div>
            </div>
            <div v-if="comments.length === 0" class="empty-state">
              {{ $t('documentDetail.noCommentsYet') }}
            </div>
          </div>
          <div class="comment-form">
            <div class="comment-type-selector">
              <label>
                <input
                  type="radio"
                  v-model="commentForm.type"
                  value="comment"
                />
                {{ $t('documentDetail.comment') }}
              </label>
              <label>
                <input
                  type="radio"
                  v-model="commentForm.type"
                  value="annotation"
                />
                {{ $t('documentDetail.annotation') }}
              </label>
            </div>
            <textarea
              v-model="commentForm.content"
              :placeholder="$t('documentDetail.addCommentPlaceholder')"
              rows="3"
            ></textarea>
            <div v-if="commentForm.type === 'annotation'" class="annotation-position">
              <label>{{ $t('documentDetail.positionJson') }}</label>
              <input
                v-model="commentForm.position"
                placeholder='{"page": 1, "x": 100, "y": 200}'
              />
            </div>
            <button @click="addComment" class="btn-primary" :disabled="!commentForm.content">
              {{ commentForm.type === 'annotation' ? $t('documentDetail.addAnnotationButton') : $t('documentDetail.addCommentButton') }}
            </button>
          </div>
        </div>
      </div>

      <!-- Versions Tab -->
      <div v-if="activeTab === 'versions'" class="tab-content">
        <div class="versions-timeline">
          <div
            v-for="version in versions"
            :key="version.id"
            class="version-timeline-item"
          >
            <div class="version-marker"></div>
            <div class="version-content">
              <div class="version-header">
                <div>
                  <h4>{{ $t('documentDetail.versionNumber', { number: version.version_no }) }}</h4>
                  <div class="version-meta">
                    <span>{{ version.created_by_user?.name || $t('documentDetail.unknown') }}</span>
                    <span>{{ formatDate(version.created_at) }}</span>
                    <span v-if="version.source">{{ $t('documentDetail.source') }} {{ version.source }}</span>
                    <span v-if="version.device">{{ $t('documentDetail.device') }} {{ version.device }}</span>
                  </div>
                </div>
                <div class="version-actions">
                  <button @click="viewVersion(version)" class="btn-small">
                    <Eye :size="16" />
                    {{ $t('documentDetail.view') }}
                  </button>
                  <button
                    v-if="versions.length > 1"
                    @click="compareWithVersion(version)"
                    class="btn-small"
                  >
                    <GitCompare :size="16" />
                    {{ $t('documentDetail.compare') }}
                  </button>
                  <button @click="downloadVersion(version)" class="btn-small">
                    <Download :size="16" />
                    {{ $t('documentDetail.download') }}
                  </button>
                  <button
                    v-if="authStore.isAdmin && version.version_no !== latestVersion"
                    @click="restoreVersion(version)"
                    class="btn-small"
                  >
                    <RotateCcw :size="16" />
                    {{ $t('documentDetail.restore') }}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Share Tab -->
      <div v-if="activeTab === 'share'" class="tab-content">
        <div class="share-section">
          <h3>{{ $t('documentDetail.shareDocument') }}</h3>
          <div class="share-form">
            <div class="form-group">
              <label>{{ $t('documentDetail.shareWithUsers') }}</label>
              <input
                v-model="shareForm.userEmails"
                :placeholder="$t('documentDetail.enterEmailAddresses')"
              />
            </div>
            <div class="form-group">
              <label>{{ $t('documentDetail.shareWithRoles') }}</label>
              <select v-model="shareForm.roleIds" multiple>
                <option v-for="role in roles" :key="role.id" :value="role.id">
                  {{ role.name }}
                </option>
              </select>
            </div>
            <div class="form-group">
              <label>{{ $t('documentDetail.permissions') }}</label>
              <div class="permissions-checkbox-group">
                <label class="checkbox-label">
                  <input
                    type="checkbox"
                    v-model="shareForm.permissions"
                    value="view"
                    checked
                  />
                  <span>{{ $t('documentDetail.viewPermission') }}</span>
                </label>
                <label class="checkbox-label">
                  <input
                    type="checkbox"
                    v-model="shareForm.permissions"
                    value="search"
                  />
                  <span>{{ $t('documentDetail.searchPermission') }}</span>
                </label>
                <label class="checkbox-label">
                  <input
                    type="checkbox"
                    v-model="shareForm.permissions"
                    value="chat"
                  />
                  <span>{{ $t('documentDetail.chatPermission') }}</span>
                </label>
              </div>
              <p class="hint-text">{{ $t('documentDetail.selectPermissionsHint') }}</p>
            </div>
            <div class="form-group">
              <label>{{ $t('documentDetail.expiresAtOptional') }}</label>
              <input v-model="shareForm.expires_at" type="datetime-local" />
            </div>
            <button @click="shareDocument" class="btn-primary">{{ $t('documentDetail.shareButton') }}</button>
          </div>
          <div v-if="shares.length > 0" class="shares-list">
            <h4>{{ $t('documentDetail.currentShares') }}</h4>
            <div v-for="share in shares" :key="share.id" class="share-item">
              <div class="share-info">
                <span v-if="share.user">{{ share.user.name }}</span>
                <span v-else-if="share.role">{{ share.role.name }}</span>
                <span class="share-permission">{{ Array.isArray(share.permissions) ? share.permissions.join(', ') : (share.permissions || 'view') }}</span>
              </div>
              <button @click="removeShare(share.id)" class="btn-small btn-danger">
                {{ $t('documentDetail.remove') }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Activity Tab -->
      <div v-if="activeTab === 'activity'" class="tab-content">
        <div class="activity-log">
          <div
            v-for="activity in activities"
            :key="activity.id"
            class="activity-item"
          >
            <div class="activity-icon">
              <component :is="getActivityIcon(activity.action)" :size="20" />
            </div>
            <div class="activity-content">
              <div class="activity-header">
                <span class="activity-action">{{ activity.action }}</span>
                <span class="activity-date">{{ formatDate(activity.created_at) }}</span>
              </div>
              <div class="activity-actor">
                {{ $t('documentDetail.by') }} {{ activity.actor?.name || $t('documentDetail.unknown') }}
              </div>
              <div v-if="activity.metadata" class="activity-metadata">
                {{ JSON.stringify(activity.metadata) }}
              </div>
            </div>
          </div>
          <div v-if="activities.length === 0" class="empty-state">
            {{ $t('documentDetail.noActivityRecorded') }}
          </div>
        </div>
      </div>
    </div>

    <!-- Version Compare Modal -->
    <VersionCompare
      v-model:show="showCompareModal"
      :document-id="document.id"
      :v1="compareV1"
      :v2="compareV2"
      @close="showCompareModal = false"
    />

    <!-- Delete Confirmation Modal -->
    <Modal
      :show="showDeleteModal"
      :title="$t('documentDetail.deleteDocumentTitle')"
      @update:show="showDeleteModal = $event"
    >
      <p v-if="document">
        {{ $t('documentDetail.deleteDocumentConfirm', { title: document.title, days: purgeGracePeriodDays }) }}
      </p>
      <template #footer>
        <button @click="showDeleteModal = false" class="btn-secondary">{{ $t('documentDetail.cancel') }}</button>
        <button @click="deleteDocument" class="btn-danger">{{ $t('documentDetail.delete') }}</button>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../store/auth'
import { useDocumentsStore } from '../store/documents'
import { useFoldersStore } from '../store/folders'
import { useSettingsStore } from '../store/settings'
import { useRolesStore } from '../store/roles'
import { documentsAPI, foldersAPI, settingsAPI, rolesAPI } from '../services/api'
import { StatusBadge, VersionCompare, Modal } from '../components'

const { t } = useI18n()
import {
  User,
  Trash2,
  Eye,
  GitCompare,
  Download,
  RotateCcw,
  FileText,
  Share2,
  Clock,
  MessageSquare,
  Copy,
  AlertTriangle
} from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const documentsStore = useDocumentsStore()
const foldersStore = useFoldersStore()
const settingsStore = useSettingsStore()
const rolesStore = useRolesStore()

const document = ref(null)
const versions = ref([])
const comments = ref([])
const shares = ref([])
const activities = ref([])
const folders = ref([])
const retentionPolicies = ref([])
const roles = ref([])
const loading = ref(true)
const activeTab = ref('preview')
const showOcrText = ref(false)
const previewUrl = ref('')
const ocrText = ref('')
const selectedVersion = ref(null)
const showCompareModal = ref(false)
const compareV1 = ref(null)
const compareV2 = ref(null)
const showDeleteModal = ref(false)
const purgeGracePeriodDays = ref(1)

const tabs = computed(() => {
  const { t } = useI18n()
  return [
    { id: 'preview', label: t('documentDetail.preview'), icon: FileText },
    { id: 'metadata', label: t('documentDetail.metadata'), icon: FileText },
    { id: 'comments', label: t('documentDetail.comments'), icon: MessageSquare },
    { id: 'versions', label: t('documentDetail.versions'), icon: Clock },
    { id: 'share', label: t('documentDetail.share'), icon: Share2 },
    { id: 'activity', label: t('documentDetail.activity'), icon: Clock }
  ]
})

const metadataForm = ref({
  title: '',
  folder_id: null,
  retention_policy_id: null,
  tags: []
})

const tagInput = ref('')
const commentForm = ref({
  content: '',
  type: 'comment',
  position: null
})

const shareForm = ref({
  userEmails: '',
  roleIds: [],
  permissions: ['view'], // Default: view permission
  expires_at: null
})

const latestVersion = computed(() => {
  if (versions.value.length === 0) return 0
  return Math.max(...versions.value.map(v => v.version_no))
})

const latestVersionMetadata = computed(() => {
  if (versions.value.length === 0) return null
  const latest = versions.value.find(v => v.version_no === latestVersion.value)
  return latest?.metadata_snapshot || null
})

// Check if file is Office or text file (DOCX, XLSX, CSV, TXT)
const isOfficeOrTextFile = computed(() => {
  if (!document.value) return false
  const mime = document.value.mime || ''
  return mime.includes('wordprocessingml') || // DOCX
         mime.includes('spreadsheetml') ||     // XLSX
         mime === 'text/csv' ||
         mime === 'application/csv' ||
         mime === 'text/plain'
})

// Check if file can be previewed in iframe (PDF, images)
const canPreviewInIframe = computed(() => {
  if (!document.value) return false
  const mime = document.value.mime || ''
  return mime === 'application/pdf' || mime.startsWith('image/')
})

onMounted(async () => {
  const docId = parseInt(route.params.id)
  await loadDocument(docId)
  await loadFolders()
  await loadRetentionPolicies()
  await loadRoles()
})

const loadDocument = async (docId) => {
  loading.value = true
  try {
    await documentsStore.fetchDocument(docId)
    document.value = documentsStore.currentDocument
    versions.value = documentsStore.versions

    if (versions.value.length > 0) {
      selectedVersion.value = versions.value[0].id
      await loadVersionPreview()
    }

    // Load preview URL from document or latest version
    if (document.value.preview_url) {
      previewUrl.value = document.value.preview_url
    } else if (versions.value.length > 0 && versions.value[0].renditions?.preview) {
      previewUrl.value = versions.value[0].renditions.preview
    }

    // Initialize metadata form
    metadataForm.value = {
      title: document.value.title || '',
      folder_id: document.value.folder_id,
      retention_policy_id: document.value.retention_policy_id,
      tags: document.value.tags || []
    }

    // Load comments
    await loadComments(docId)
  } catch (e) {
    console.error('Failed to load document', e)
    // Check if document was not found (404) - likely deleted
    const statusCode = e?.response?.status || e?.status || (e?.message?.includes('404') ? 404 : null)
    if (statusCode === 404) {
      if (window.$toast) {
        window.$toast.show(t('documents.documentNotFoundRedirect'), 'error')
      }
      // Redirect to Recycle Bin after a short delay
      setTimeout(() => {
        router.push('/recycle-bin')
      }, 2000)
    } else {
      if (window.$toast) {
        window.$toast.show(t('documents.failedToLoadDocument'), 'error')
      }
    }
  } finally {
    loading.value = false
  }
}

const loadVersionPreview = async () => {
  if (!selectedVersion.value) return
  const version = versions.value.find(v => v.id === selectedVersion.value)
  if (!version) return
  
  // Load preview URL
  if (version?.renditions?.preview) {
    previewUrl.value = version.renditions.preview
  } else {
    previewUrl.value = ''
  }
  
  // For Office/text files, always load extracted text for preview
  // For PDF/images, load OCR text only if showOcrText is true
  if (isOfficeOrTextFile.value || version?.text_uri || version?.ocr_uri) {
    try {
      const res = await documentsAPI.rendition(document.value.id, 'text', { version_id: version.id })
      if (res.is_success && res.data) {
        // API now returns content directly in res.data.content
        ocrText.value = res.data.content || res.data || ''
      } else {
        ocrText.value = ''
      }
    } catch (e) {
      console.error('Failed to load text content', e)
      ocrText.value = ''
    }
  } else {
    ocrText.value = ''
  }
}

const downloadOriginal = () => {
  if (!document.value || !previewUrl.value) return
  // Open download URL in new tab
  window.open(previewUrl.value, '_blank')
}

const copyOcrText = async () => {
  if (!ocrText.value) return
  try {
    await navigator.clipboard.writeText(ocrText.value)
    if (window.$toast) {
      window.$toast.show(t('documents.ocrTextCopied'), 'success')
    }
  } catch (e) {
    console.error('Failed to copy text', e)
    if (window.$toast) {
      window.$toast.show(t('documents.failedToCopyText'), 'error')
    }
  }
}

const loadComments = async (docId) => {
  try {
    await documentsStore.fetchComments(docId)
    comments.value = documentsStore.comments
  } catch (e) {
    console.error('Failed to load comments', e)
  }
}

const loadFolders = async () => {
  try {
    await foldersStore.fetchFolders()
    folders.value = foldersStore.folders
  } catch (e) {
    console.error('Failed to load folders', e)
  }
}

const loadRetentionPolicies = async () => {
  try {
    await settingsStore.fetchRetentionPolicies()
    retentionPolicies.value = settingsStore.retentionPolicies
  } catch (e) {
    console.error('Failed to load retention policies', e)
  }
}

const loadRoles = async () => {
  try {
    await rolesStore.fetchRoles()
    roles.value = rolesStore.roles
  } catch (e) {
    console.error('Failed to load roles', e)
  }
}

const saveMetadata = async () => {
  try {
    await documentsStore.updateDocument(document.value.id, metadataForm.value)
    if (window.$toast) {
      window.$toast.show(t('documents.metadataSaved'), 'success')
    }
  } catch (e) {
    console.error('Failed to save metadata', e)
    if (window.$toast) {
      window.$toast.show(t('documents.failedToSaveMetadata'), 'error')
    }
  }
}

const addTag = () => {
  if (tagInput.value.trim() && !metadataForm.value.tags.includes(tagInput.value.trim())) {
    metadataForm.value.tags.push(tagInput.value.trim())
    tagInput.value = ''
  }
}

const removeTag = (tag) => {
  metadataForm.value.tags = metadataForm.value.tags.filter(t => t !== tag)
}

const addComment = async () => {
  if (!commentForm.value.content.trim()) return
  try {
    const data = {
      content: commentForm.value.content,
      type: commentForm.value.type
    }
    if (commentForm.value.type === 'annotation' && commentForm.value.position) {
      try {
        data.position = JSON.parse(commentForm.value.position)
      } catch (e) {
        if (window.$toast) {
          window.$toast.show(t('documents.invalidPositionJson'), 'error')
        }
        return
      }
    }
    await documentsStore.createComment(document.value.id, data)
    commentForm.value = { content: '', type: 'comment', position: null }
    if (window.$toast) {
      window.$toast.show(t('documents.commentAdded'), 'success')
    }
  } catch (e) {
    console.error('Failed to add comment', e)
    if (window.$toast) {
      window.$toast.show(t('documents.failedToAddComment'), 'error')
    }
  }
}

const deleteComment = async (commentId) => {
  try {
    await documentsStore.deleteComment(document.value.id, commentId)
    if (window.$toast) {
      window.$toast.show(t('documents.commentDeleted'), 'success')
    }
  } catch (e) {
    console.error('Failed to delete comment', e)
    if (window.$toast) {
      window.$toast.show(t('documents.failedToDeleteComment'), 'error')
    }
  }
}

const viewVersion = (version) => {
  selectedVersion.value = version.id
  loadVersionPreview()
  activeTab.value = 'preview'
}

const compareWithVersion = (version) => {
  const latest = versions.value.find(v => v.version_no === latestVersion.value)
  if (latest && version.id !== latest.id) {
    compareV1.value = latest.version_no
    compareV2.value = version.version_no
    showCompareModal.value = true
  }
}

const downloadVersion = (version) => {
  window.open(`/api/v1/documents/${document.value.id}/versions/${version.id}/download`, '_blank')
}

const restoreVersion = async (version) => {
  if (confirm(t('documents.restoreVersionConfirm', { version: version.version_no }))) {
    try {
      // Implementation depends on backend API
      if (window.$toast) {
        window.$toast.show(t('documents.versionRestoreNotImplemented'), 'info')
      }
    } catch (e) {
      console.error('Failed to restore version', e)
    }
  }
}

const shareDocument = async () => {
  try {
    // Ensure view is always included
    const permissions = shareForm.value.permissions || ['view']
    if (!permissions.includes('view')) {
      permissions.unshift('view')
    }
    
    const data = {
      permissions: permissions
    }
    if (shareForm.value.userEmails) {
      data.user_emails = shareForm.value.userEmails.split(',').map(e => e.trim())
    }
    if (shareForm.value.roleIds.length > 0) {
      data.role_ids = shareForm.value.roleIds
    }
    if (shareForm.value.expires_at) {
      data.expires_at = shareForm.value.expires_at
    }
    await documentsAPI.share(document.value.id, data)
    shareForm.value = { userEmails: '', roleIds: [], permissions: ['view'], expires_at: null }
    await loadDocument(document.value.id) // Reload to refresh shares
    if (window.$toast) {
      window.$toast.show(t('documents.documentShared'), 'success')
    }
  } catch (e) {
    console.error('Failed to share document', e)
    if (window.$toast) {
      window.$toast.show(t('documents.failedToShareDocument'), 'error')
    }
  }
}

const removeShare = async (shareId) => {
  try {
    // Implementation depends on backend API
    if (window.$toast) {
      window.$toast.show(t('documents.removeShareNotImplemented'), 'info')
    }
  } catch (e) {
    console.error('Failed to remove share', e)
  }
}

const getActivityIcon = (action) => {
  const icons = {
    create: FileText,
    update: FileText,
    delete: Trash2,
    share: Share2,
    comment: MessageSquare
  }
  return icons[action] || Clock
}

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleString()
}

const formatSize = (bytes) => {
  if (!bytes) return '0 B'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}

const confirmDelete = async () => {
  // Load purge grace period
  try {
    const res = await settingsAPI.purgeGracePeriod.get()
    if (res.is_success && res.data) {
      purgeGracePeriodDays.value = res.data.days || 1
    }
  } catch (e) {
    console.error('Failed to load purge grace period', e)
  }
  
  showDeleteModal.value = true
}

const deleteDocument = async () => {
  if (!document.value) return
  
  try {
    const res = await documentsAPI.delete(document.value.id)
    if (res.is_success) {
      if (window.$toast) {
        window.$toast.show(t('documents.documentDeletedRedirect'), 'success')
      }
      showDeleteModal.value = false
      // Redirect to Recycle Bin after deletion
      setTimeout(() => {
        router.push('/recycle-bin')
      }, 1500)
    } else {
      if (window.$toast) {
        window.$toast.show(res.message || t('documents.failedToDeleteDocument'), 'error')
      }
    }
  } catch (e) {
    console.error('Failed to delete document', e)
    if (window.$toast) {
      window.$toast.show(t('documents.failedToDeleteDocument'), 'error')
    }
  }
}
</script>

<style scoped>
.document-detail {
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.deleted-banner {
  display: flex;
  align-items: flex-start;
  gap: var(--space-md);
  padding: var(--space-lg);
  background: #fff3cd;
  border: 1px solid #ffc107;
  border-radius: var(--radius-md);
  margin-bottom: var(--space-xl);
  color: #856404;
}

.deleted-banner svg {
  flex-shrink: 0;
  margin-top: 0.125rem;
}

.deleted-banner-content {
  flex: 1;
}

.deleted-banner-content strong {
  display: block;
  font-size: 1rem;
  margin-bottom: var(--space-xs);
}

.deleted-banner-details {
  font-size: 0.875rem;
  color: #856404;
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-xs);
}

.detail-tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
  border-bottom: 2px solid #eee;
}

.tab-btn {
  padding: 0.75rem 1.5rem;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  font-weight: 500;
  color: #666;
  transition: all 0.2s;
  margin-bottom: -2px;
}

.tab-btn:hover {
  color: var(--primary);
}

.tab-btn-active {
  color: var(--primary);
  border-bottom-color: var(--primary);
}

.detail-content {
  background: white;
  border-radius: 8px;
  padding: 2rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.tab-content {
  min-height: 400px;
}

.preview-controls {
  margin-bottom: 1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.preview-options {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.version-select {
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 6px;
}

.preview-area {
  height: 800px;
  border: 1px solid #eee;
  border-radius: 6px;
  overflow: hidden;
}

.preview-frame {
  width: 100%;
  height: 100%;
  border: none;
}

.ocr-text-view {
  padding: 0;
  background: var(--bg-white);
  border-radius: 6px;
  max-height: 600px;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.ocr-text-content {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.ocr-text-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-md);
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-light);
  border-radius: 6px 6px 0 0;
}

.ocr-text-header span {
  font-weight: 600;
  color: var(--text-dark);
}

.text-actions {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.ocr-text-pre {
  flex: 1;
  margin: 0;
  padding: var(--space-lg);
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: 'Courier New', monospace;
  font-size: 0.875rem;
  line-height: 1.6;
  overflow-y: auto;
  background: var(--bg-white);
  color: var(--text-dark);
}

.ocr-text-empty {
  padding: var(--space-3xl);
  text-align: center;
  color: var(--text-medium);
}

.preview-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #666;
}

.metadata-form {
  max-width: 600px;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
}

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: var(--space-md) var(--space-lg);
  border: 2px solid rgba(0, 0, 0, 0.1);
  border-radius: var(--radius-lg);
  background: var(--bg-white);
  font-size: 0.95rem;
  font-family: inherit;
  transition: all var(--transition-base);
  box-shadow: var(--shadow-sm);
}

.form-group input[type="date"],
.form-group input[type="datetime-local"] {
  padding-right: var(--space-xl);
  cursor: pointer;
  position: relative;
}

.form-group input[type="date"]::-webkit-calendar-picker-indicator,
.form-group input[type="datetime-local"]::-webkit-calendar-picker-indicator {
  cursor: pointer;
  opacity: 0.6;
  filter: grayscale(1);
  transition: all var(--transition-base);
  padding: var(--space-xs);
  border-radius: var(--radius-sm);
}

.form-group input[type="date"]::-webkit-calendar-picker-indicator:hover,
.form-group input[type="datetime-local"]::-webkit-calendar-picker-indicator:hover {
  opacity: 1;
  filter: grayscale(0);
  background: var(--gradient-ai-soft);
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  outline: none;
  border-color: var(--ai-cyan);
  box-shadow: var(--shadow-md), 0 0 0 3px rgba(0, 217, 255, 0.1);
}

.form-group input[type="date"]:focus::-webkit-calendar-picker-indicator,
.form-group input[type="datetime-local"]:focus::-webkit-calendar-picker-indicator {
  opacity: 1;
  filter: grayscale(0);
}

.tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.tag-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  background: var(--primary-light);
  color: var(--primary);
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.85rem;
}

.tag-remove {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--primary);
  font-size: 1.2rem;
  line-height: 1;
  padding: 0;
}

.comments-section {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.comments-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.comment-item {
  padding: 1rem;
  background: var(--bg-light);
  border-radius: 6px;
  border-left: 3px solid var(--primary);
}

.comment-annotation {
  border-left-color: #f59e0b;
}

.comment-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.comment-author {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 500;
}

.comment-date {
  font-size: 0.85rem;
  color: #666;
}

.comment-content {
  margin-top: 0.5rem;
  white-space: pre-wrap;
}

.comment-position {
  margin-top: 0.5rem;
  font-size: 0.85rem;
  color: #666;
  font-family: monospace;
}

.comment-form {
  padding: 1.5rem;
  background: var(--bg-light);
  border-radius: 6px;
}

.comment-type-selector {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
}

.comment-type-selector label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
}

.comment-form textarea {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  margin-bottom: 1rem;
  font-family: inherit;
}

.annotation-position {
  margin-bottom: 1rem;
}

.annotation-position label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
}

.annotation-position input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-family: monospace;
}

.versions-timeline {
  position: relative;
  padding-left: 2rem;
}

.versions-timeline::before {
  content: '';
  position: absolute;
  left: 0.5rem;
  top: 0;
  bottom: 0;
  width: 2px;
  background: #eee;
}

.version-timeline-item {
  position: relative;
  margin-bottom: 2rem;
}

.version-marker {
  position: absolute;
  left: -1.75rem;
  top: 0.5rem;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--primary);
  border: 2px solid white;
  box-shadow: 0 0 0 2px var(--primary);
}

.version-content {
  background: var(--bg-light);
  padding: 1.5rem;
  border-radius: 6px;
}

.version-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 0.5rem;
}

.version-header h4 {
  margin: 0 0 0.5rem 0;
  color: var(--primary);
}

.version-meta {
  display: flex;
  gap: 1rem;
  font-size: 0.85rem;
  color: #666;
  flex-wrap: wrap;
}

.version-actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.share-section {
  max-width: 600px;
}

.share-form {
  margin-bottom: 2rem;
}

.shares-list {
  margin-top: 2rem;
  padding-top: 2rem;
  border-top: 1px solid #eee;
}

.shares-list h4 {
  margin: 0 0 1rem 0;
  color: var(--primary);
}

.share-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background: var(--bg-light);
  border-radius: 6px;
  margin-bottom: 0.5rem;
}

.share-info {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.share-permission {
  padding: 0.25rem 0.75rem;
  background: white;
  border-radius: 12px;
  font-size: 0.85rem;
}

.activity-log {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.activity-item {
  display: flex;
  gap: 1rem;
  padding: 1rem;
  background: var(--bg-light);
  border-radius: 6px;
}

.activity-icon {
  flex-shrink: 0;
  color: var(--primary);
}

.activity-content {
  flex: 1;
}

.activity-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.25rem;
}

.activity-action {
  font-weight: 500;
  color: var(--primary);
}

.activity-date {
  font-size: 0.85rem;
  color: #666;
}

.activity-actor {
  font-size: 0.9rem;
  color: #666;
}

.activity-metadata {
  margin-top: 0.5rem;
  font-size: 0.85rem;
  color: #999;
  font-family: monospace;
}

.empty-state {
  text-align: center;
  padding: 3rem;
  color: #666;
}

.loading {
  text-align: center;
  padding: 3rem;
}

.btn-small {
  background: var(--bg-white);
  border: 1.5px solid #e5e7eb;
  color: var(--text-dark);
  padding: var(--space-sm) var(--space-md);
  border-radius: var(--radius-md);
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-base);
  display: inline-flex;
  align-items: center;
  gap: var(--space-xs);
  box-shadow: var(--shadow-sm);
}

.btn-small:hover {
  background: var(--primary-light);
  border-color: var(--primary);
  color: var(--primary-dark);
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.btn-small:active {
  transform: translateY(0);
  box-shadow: var(--shadow-sm);
}

.btn-small.btn-active {
  background: var(--gradient-primary);
  color: white;
  border-color: transparent;
  box-shadow: var(--shadow-md), var(--shadow-glow);
}

.btn-small.btn-active:hover {
  background: var(--gradient-primary);
  color: white;
  transform: translateY(-1px);
  box-shadow: var(--shadow-lg), var(--shadow-glow);
}

.btn-link-small {
  background: transparent;
  border: none;
  cursor: pointer;
  color: var(--primary);
  padding: var(--space-xs) var(--space-sm);
  font-size: 0.875rem;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: var(--space-xs);
  border-radius: var(--radius-sm);
  transition: all var(--transition-base);
  text-decoration: none;
}

.btn-link-small:hover {
  background: var(--primary-light);
  color: var(--primary-dark);
  transform: translateY(-1px);
}

.btn-link-small:active {
  transform: translateY(0);
}

.permissions-checkbox-group {
  display: flex;
  gap: 2rem;
  flex-wrap: wrap;
  margin-top: 0.75rem;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.875rem;
  cursor: pointer;
  font-size: 1rem;
  margin: 0;
  font-weight: 500;
  color: var(--text-dark);
  padding: 0.625rem 1rem;
  border-radius: var(--radius-md);
  transition: all var(--transition-base);
  position: relative;
  user-select: none;
}

.checkbox-label:hover {
  background: var(--bg-light);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.checkbox-label input[type="checkbox"] {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
  cursor: pointer;
}

.checkbox-label input[type="checkbox"] + span {
  position: relative;
  display: inline-flex;
  align-items: center;
  padding-left: 32px;
  line-height: 1.5;
}

.checkbox-label input[type="checkbox"] + span::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 22px;
  height: 22px;
  border: 2px solid #ddd;
  border-radius: 6px;
  background: var(--bg-white);
  display: inline-block;
  transition: all var(--transition-base);
  flex-shrink: 0;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.checkbox-label:hover input[type="checkbox"] + span::before {
  border-color: var(--primary);
  box-shadow: 0 2px 8px rgba(108, 92, 231, 0.25);
  transform: translateY(-50%) scale(1.08);
}

.checkbox-label input[type="checkbox"]:checked + span::before {
  background: var(--gradient-cyan-purple);
  border-color: var(--primary);
  box-shadow: 0 2px 12px rgba(108, 92, 231, 0.4);
  transform: translateY(-50%) scale(1);
}

.checkbox-label input[type="checkbox"]:checked + span::after {
  content: '✓';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  color: white;
  font-size: 15px;
  font-weight: bold;
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}

.hint-text {
  font-size: 0.85rem;
  color: var(--text-secondary);
  margin-top: 0.5rem;
  font-style: italic;
}

.metadata-section {
  margin-bottom: 2rem;
}

.metadata-section h3 {
  margin: 0 0 1rem 0;
  color: var(--primary);
  font-size: 1.25rem;
  border-bottom: 2px solid var(--primary-light);
  padding-bottom: 0.5rem;
}

.extracted-metadata {
  background: var(--bg-light);
  border-radius: 8px;
  padding: 1.5rem;
}

.metadata-group {
  margin-bottom: 2rem;
}

.metadata-group:last-child {
  margin-bottom: 0;
}

.metadata-group h4 {
  margin: 0 0 1rem 0;
  color: var(--text-dark);
  font-size: 1rem;
  font-weight: 600;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid #e5e7eb;
}

.metadata-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
}

.metadata-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.metadata-item label {
  font-weight: 500;
  font-size: 0.875rem;
  color: var(--text-medium);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.metadata-item span {
  color: var(--text-dark);
  font-size: 0.95rem;
  word-break: break-word;
}

.metadata-item .monospace {
  font-family: 'Courier New', monospace;
  font-size: 0.85rem;
  background: rgba(0, 0, 0, 0.05);
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  display: inline-block;
}
</style>
