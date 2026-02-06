/**
 * Document Upload Utilities
 * 
 * Unified document upload flow:
 * 1. Upload file to storage → get path
 * 2. Create Document record → get document_id
 * 3. Return RefLink for adding to parent.refs.links.document[]
 * 
 * @see readmes/topics/document-uploads.md
 */
import { apiClient } from '@/api/axios';
import type { RefLink } from './types';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Geolocation coordinates */
export interface GeoLocation {
  lat: number | null;
  lng: number | null;
  altitude?: number | null;
  accuracy?: number | null;
}

/** Address with optional geolocation */
export interface DocumentAddress {
  street?: string;
  street2?: string;
  city?: string;
  state?: string;
  postal_code?: string;
  country?: string;
  geo?: GeoLocation;
  source?: 'exif' | 'manual' | 'gps' | 'ip_lookup' | 'browser' | '';
  captured_at?: number;
}

/** Virus scan status */
export interface VirusScanResult {
  status: 'pending' | 'scanning' | 'clean' | 'infected' | 'error' | 'skipped';
  scanner?: string;
  scanner_version?: string;
  scanned_at?: number;
  threat?: string | null;
  quarantined?: boolean;
  details?: Record<string, unknown>;
}

/** EXIF metadata from images */
export interface ExifData {
  camera_make?: string;
  camera_model?: string;
  lens?: string;
  focal_length?: number | null;
  aperture?: number | null;
  shutter_speed?: string;
  iso?: number | null;
  flash?: boolean;
  orientation?: number;
  width?: number | null;
  height?: number | null;
  datetime_original?: number;
  datetime_digitized?: number;
  software?: string;
  copyright?: string;
  raw?: Record<string, unknown>;
}

/** Document metadata structure */
export interface DocumentMetadata {
  history?: {
    created?: { dt: number; contact_id: number };
    modified?: { dt: number; contact_id: number };
    accessed?: { dt: number; contact_id: number };
    verified?: { dt: number; contact_id: number };
    synced?: { dt: number; contact_id: number };
  };
  health?: {
    rating?: number;
    completeness?: number;
    accuracy?: number;
    freshness?: number;
    consistency?: number;
  };
  address?: DocumentAddress;
  virus?: VirusScanResult;
  exif?: ExifData;
  original_name?: string;
  upload_source?: string;
  purpose?: string;
  [key: string]: unknown;
}

/** Document record from API */
export interface DocumentRecord {
  id: number;
  uuid?: string;
  name: string;
  slug?: string;
  status?: string;
  description?: string;
  mime_type?: string;
  size_bytes?: number;
  path?: {
    storage: string;      // 's3' | 'local' | 'azure'
    bucket?: string;
    key: string;          // full path within storage
    url?: string;         // public/presigned URL
  };
  checksum?: string;
  model_name?: string;    // parent model type (e.g., 'sales_order')
  created_by?: number;
  dt_created?: number;
  metadata?: DocumentMetadata;
}

/** Options for uploading a document */
export interface UploadDocumentOptions {
  /** The file to upload */
  file: File;
  /** Parent model type (e.g., 'sales_order', 'question_answer') */
  parentType: string;
  /** Parent record ID */
  parentId: number;
  /** Purpose/category of the document (e.g., 'qa_image', 'attachment', 'spec_sheet') */
  purpose?: string;
  /** Optional description */
  description?: string;
  /** Optional custom name (defaults to file.name) */
  name?: string;
  /** Additional metadata */
  metadata?: Record<string, unknown>;
  /** Optional address information */
  address?: {
    street?: string;
    street2?: string;
    city?: string;
    state?: string;
    postal_code?: string;
    country?: string;
  };
  /** Optional geolocation (from browser or GPS) */
  geolocation?: {
    lat: number;
    lng: number;
    accuracy?: number;
  };
}

/** Result from document upload */
export interface UploadDocumentResult {
  /** The created Document record */
  document: DocumentRecord;
  /** RefLink formatted for adding to refs.links.document[] */
  refLink: RefLink;
  /** Direct URL to the uploaded file */
  url?: string;
}

/** Progress callback for upload */
export type UploadProgressCallback = (progress: number) => void;

// ---------------------------------------------------------------------------
// API Functions
// ---------------------------------------------------------------------------

/**
 * Upload a document and create a Document record
 * 
 * Single-step flow: Upload file → Backend creates Document record → Returns doc info
 * 
 * Features:
 * - Checksum-based deduplication (same file = same Document record)
 * - Automatic metadata extraction (size, mime type)
 * - EXIF extraction for images (including GPS coordinates)
 * - Optional address/geolocation from browser
 * - Virus scanning (if enabled on backend)
 * - RefLink generation for parent entity
 */
export async function uploadDocument(
  options: UploadDocumentOptions,
  onProgress?: UploadProgressCallback
): Promise<UploadDocumentResult> {
  const {
    file,
    parentType,
    parentId,
    purpose = 'attachment',
    description,
    name,
    address,
    geolocation,
  } = options;

  // Single-step: Upload file and create Document record
  const formData = new FormData();
  formData.append('file', file);
  formData.append('model_name', parentType);
  formData.append('parent_id', String(parentId));
  formData.append('purpose', purpose);
  if (description) formData.append('description', description);
  
  // Add address fields if provided
  if (address) {
    if (address.street) formData.append('address_street', address.street);
    if (address.street2) formData.append('address_street2', address.street2);
    if (address.city) formData.append('address_city', address.city);
    if (address.state) formData.append('address_state', address.state);
    if (address.postal_code) formData.append('address_postal_code', address.postal_code);
    if (address.country) formData.append('address_country', address.country);
  }
  
  // Add geolocation if provided (from browser navigator.geolocation)
  if (geolocation) {
    formData.append('geo_lat', String(geolocation.lat));
    formData.append('geo_lng', String(geolocation.lng));
    if (geolocation.accuracy) formData.append('geo_accuracy', String(geolocation.accuracy));
  }

  // Backend response type from /wcapi/upload/
  interface UploadResponse {
    document_id: number;
    path: string;
    checksum: string;
    is_duplicate: boolean;
    url: string;
    name: string;
    size_bytes: number;
    mime_type: string;
    has_exif?: boolean;
    has_geo?: boolean;
    virus_status?: string;
  }

  const uploadRes = await apiClient.post<UploadResponse | { data: UploadResponse }>(
    '/wcapi/upload/',
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(percent);
        }
      },
    }
  );

  // Handle both envelope {data: ...} and direct response
  const responseData = 'document_id' in uploadRes.data 
    ? uploadRes.data as UploadResponse
    : (uploadRes.data as { data: UploadResponse }).data;

  const { document_id, path, checksum, is_duplicate, url, size_bytes, mime_type } = responseData;
  const docName = name || responseData.name || file.name;

  // Build Document record
  const document: DocumentRecord = {
    id: document_id,
    name: docName,
    description,
    mime_type,
    size_bytes,
    path: {
      storage: 'local',
      key: path,
      url,
    },
    checksum,
    model_name: parentType,
    metadata: {
      original_name: file.name,
      upload_source: 'web',
      purpose,
      is_duplicate,
    },
  };

  // Build RefLink for parent entity's refs.links.document[]
  const refLink: RefLink = {
    id: document_id,
    display: docName,
    name: docName,
    type: getDocumentType(mime_type, file.name),
    purpose,
  };

  return {
    document,
    refLink,
    url,
  };
}

/**
 * Upload multiple documents
 */
export async function uploadDocuments(
  files: File[],
  parentType: string,
  parentId: number,
  options?: {
    purpose?: string;
    onProgress?: (fileIndex: number, progress: number) => void;
  }
): Promise<UploadDocumentResult[]> {
  const results: UploadDocumentResult[] = [];

  for (let i = 0; i < files.length; i++) {
    const result = await uploadDocument(
      {
        file: files[i],
        parentType,
        parentId,
        purpose: options?.purpose,
      },
      options?.onProgress ? (p) => options.onProgress!(i, p) : undefined
    );
    results.push(result);
  }

  return results;
}

/**
 * Delete a document record (soft delete)
 */
export async function deleteDocument(documentId: number): Promise<boolean> {
  try {
    await apiClient.delete(`/wcapi/document/${documentId}/delete/`);
    return true;
  } catch (err) {
    console.error('Failed to delete document:', err);
    return false;
  }
}

/**
 * Get document info and download URL
 */
export async function getDocumentUrl(documentId: number): Promise<string | null> {
  try {
    interface DocResponse {
      document_id: number;
      name: string;
      url: string;
      size_bytes: number;
      mime_type: string;
    }
    const res = await apiClient.get<DocResponse | { data: DocResponse }>(
      `/wcapi/document/${documentId}/`
    );
    // Handle both envelope and direct response
    const data = 'url' in res.data ? res.data : (res.data as { data: DocResponse }).data;
    return data.url;
  } catch (err) {
    console.error('Failed to get document URL:', err);
    return null;
  }
}

// ---------------------------------------------------------------------------
// Helper Functions
// ---------------------------------------------------------------------------

/**
 * Determine document type from mime type or filename
 */
function getDocumentType(mimeType: string, filename: string): string {
  const ext = filename.split('.').pop()?.toLowerCase() || '';
  
  if (mimeType.startsWith('image/')) return 'image';
  if (mimeType.startsWith('video/')) return 'video';
  if (mimeType.startsWith('audio/')) return 'audio';
  if (mimeType.includes('pdf')) return 'pdf';
  if (mimeType.includes('word') || ['doc', 'docx'].includes(ext)) return 'document';
  if (mimeType.includes('sheet') || mimeType.includes('excel') || ['xls', 'xlsx', 'csv'].includes(ext)) return 'spreadsheet';
  if (mimeType.includes('presentation') || ['ppt', 'pptx'].includes(ext)) return 'presentation';
  if (['zip', 'tar', 'gz', 'rar', '7z'].includes(ext)) return 'archive';
  if (['txt', 'md', 'rtf'].includes(ext)) return 'text';
  
  return 'file';
}

/**
 * Format file size for display
 */
export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
}

/**
 * Check if file type is allowed
 */
export function isAllowedFileType(
  file: File,
  allowedTypes?: string[],
  allowedExtensions?: string[]
): boolean {
  if (!allowedTypes && !allowedExtensions) return true;

  const ext = file.name.split('.').pop()?.toLowerCase() || '';

  if (allowedExtensions && allowedExtensions.includes(ext)) return true;
  if (allowedTypes && allowedTypes.some(t => file.type.includes(t))) return true;

  return false;
}

/**
 * Validate file before upload
 */
export function validateFile(
  file: File,
  options?: {
    maxSizeBytes?: number;
    allowedTypes?: string[];
    allowedExtensions?: string[];
  }
): { valid: boolean; error?: string } {
  const { maxSizeBytes, allowedTypes, allowedExtensions } = options || {};

  if (maxSizeBytes && file.size > maxSizeBytes) {
    return {
      valid: false,
      error: `File size ${formatFileSize(file.size)} exceeds maximum ${formatFileSize(maxSizeBytes)}`,
    };
  }

  if ((allowedTypes || allowedExtensions) && !isAllowedFileType(file, allowedTypes, allowedExtensions)) {
    return {
      valid: false,
      error: `File type not allowed. Allowed: ${[...(allowedExtensions || []), ...(allowedTypes || [])].join(', ')}`,
    };
  }

  return { valid: true };
}

/**
 * Get current browser geolocation
 * 
 * @returns Promise with coordinates or null if unavailable/denied
 */
export function getBrowserGeolocation(): Promise<{ lat: number; lng: number; accuracy: number } | null> {
  return new Promise((resolve) => {
    if (!navigator.geolocation) {
      resolve(null);
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        resolve({
          lat: position.coords.latitude,
          lng: position.coords.longitude,
          accuracy: position.coords.accuracy,
        });
      },
      () => {
        // User denied or error occurred
        resolve(null);
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 300000, // 5 minutes
      }
    );
  });
}

/**
 * Upload with automatic browser geolocation capture
 * 
 * @param options Upload options (geolocation will be auto-captured if not provided)
 * @param onProgress Progress callback
 * @returns Upload result
 */
export async function uploadDocumentWithLocation(
  options: UploadDocumentOptions,
  onProgress?: UploadProgressCallback
): Promise<UploadDocumentResult> {
  // If no geolocation provided, try to get from browser
  if (!options.geolocation) {
    const geo = await getBrowserGeolocation();
    if (geo) {
      options = { ...options, geolocation: geo };
    }
  }
  return uploadDocument(options, onProgress);
}

// ---------------------------------------------------------------------------
// React Hook
// ---------------------------------------------------------------------------

import { useState, useCallback } from 'react';

interface UseDocumentUploadOptions {
  parentType: string;
  parentId: number;
  purpose?: string;
  maxSizeBytes?: number;
  allowedTypes?: string[];
  allowedExtensions?: string[];
  onSuccess?: (result: UploadDocumentResult) => void;
  onError?: (error: Error) => void;
}

interface UseDocumentUploadReturn {
  upload: (file: File) => Promise<UploadDocumentResult | null>;
  uploadMultiple: (files: File[]) => Promise<UploadDocumentResult[]>;
  isUploading: boolean;
  progress: number;
  error: string | null;
  reset: () => void;
}

/**
 * Hook for uploading documents with progress tracking
 */
export function useDocumentUpload(
  options: UseDocumentUploadOptions
): UseDocumentUploadReturn {
  const [isUploading, setIsUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const reset = useCallback(() => {
    setIsUploading(false);
    setProgress(0);
    setError(null);
  }, []);

  const upload = useCallback(
    async (file: File): Promise<UploadDocumentResult | null> => {
      // Validate file
      const validation = validateFile(file, {
        maxSizeBytes: options.maxSizeBytes,
        allowedTypes: options.allowedTypes,
        allowedExtensions: options.allowedExtensions,
      });

      if (!validation.valid) {
        setError(validation.error || 'Invalid file');
        options.onError?.(new Error(validation.error));
        return null;
      }

      setIsUploading(true);
      setProgress(0);
      setError(null);

      try {
        const result = await uploadDocument(
          {
            file,
            parentType: options.parentType,
            parentId: options.parentId,
            purpose: options.purpose,
          },
          setProgress
        );

        setIsUploading(false);
        setProgress(100);
        options.onSuccess?.(result);
        return result;
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Upload failed';
        setError(errorMsg);
        setIsUploading(false);
        options.onError?.(err instanceof Error ? err : new Error(errorMsg));
        return null;
      }
    },
    [options]
  );

  const uploadMultiple = useCallback(
    async (files: File[]): Promise<UploadDocumentResult[]> => {
      setIsUploading(true);
      setProgress(0);
      setError(null);

      const results: UploadDocumentResult[] = [];

      try {
        for (let i = 0; i < files.length; i++) {
          const result = await upload(files[i]);
          if (result) {
            results.push(result);
          }
          setProgress(Math.round(((i + 1) / files.length) * 100));
        }
      } finally {
        setIsUploading(false);
      }

      return results;
    },
    [upload]
  );

  return {
    upload,
    uploadMultiple,
    isUploading,
    progress,
    error,
    reset,
  };
}
