import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export interface GenerateRequest {
  description: string
  count: number
  source_photo?: string
  width?: number
  height?: number
  pulid_weight?: number
}

export interface ImageOut {
  id: number
  filename: string
  positive_prompt: string
  scene_description: string | null
  seed: number | null
  created_at: string
}

export interface JobOut {
  id: number
  description: string
  status: string
  total_images: number
  completed_images: number
  source_photo: string
  created_at: string
  error_message: string | null
  images: ImageOut[]
}

export const generateImages = (req: GenerateRequest) =>
  api.post<JobOut>('/generate', req).then(r => r.data)

export const getJobs = () =>
  api.get<JobOut[]>('/jobs').then(r => r.data)

export const getJob = (id: number) =>
  api.get<JobOut>(`/jobs/${id}`).then(r => r.data)

export const getGallery = () =>
  api.get<{ filename: string; size_kb: number; modified: number }[]>('/gallery').then(r => r.data)

export const getSourcePhotos = () =>
  api.get<{ filename: string; size_kb: number }[]>('/source-photos').then(r => r.data)

export const imageUrl = (filename: string) => `/api/gallery/${filename}`
