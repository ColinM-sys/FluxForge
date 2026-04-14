import { useState } from 'react'
import { Routes, Route, Link, useLocation } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { generateImages, getJobs, getJob, getGallery, getSourcePhotos, imageUrl } from './api'
import type { JobOut, GenerateRequest } from './api'

function Nav() {
  const loc = useLocation()
  const links = [
    { to: '/', label: 'Generate' },
    { to: '/jobs', label: 'Jobs' },
    { to: '/gallery', label: 'Gallery' },
  ]
  return (
    <nav className="flex items-center gap-6 px-6 py-4 border-b border-gray-800 bg-[#14141a]">
      <h1 className="text-xl font-bold text-white mr-8">FluxForge</h1>
      {links.map(l => (
        <Link key={l.to} to={l.to}
          className={`text-sm font-medium transition-colors ${loc.pathname === l.to ? 'text-purple-400' : 'text-gray-400 hover:text-white'}`}>
          {l.label}
        </Link>
      ))}
    </nav>
  )
}

function GeneratePage() {
  const [description, setDescription] = useState('')
  const [count, setCount] = useState(5)
  const [sourcePhoto, setSourcePhoto] = useState('colin_face3.jpg')
  const queryClient = useQueryClient()

  const photos = useQuery({ queryKey: ['source-photos'], queryFn: getSourcePhotos })
  const mutation = useMutation({
    mutationFn: (req: GenerateRequest) => generateImages(req),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      setDescription('')
    }
  })

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-6">
      <div className="space-y-2">
        <label className="text-sm text-gray-400">What do you want to generate?</label>
        <textarea
          className="w-full h-32 bg-[#1a1a24] border border-gray-700 rounded-lg p-4 text-white resize-none focus:outline-none focus:border-purple-500"
          placeholder="e.g. Put me in 10 iconic world scenes as a hacker with hood up, stacks of cash everywhere"
          value={description}
          onChange={e => setDescription(e.target.value)}
        />
      </div>

      <div className="flex gap-4 items-end">
        <div className="space-y-2">
          <label className="text-sm text-gray-400">Number of images</label>
          <select className="bg-[#1a1a24] border border-gray-700 rounded-lg px-4 py-2 text-white"
            value={count} onChange={e => setCount(Number(e.target.value))}>
            {[1, 3, 5, 8, 10, 15, 20].map(n => <option key={n} value={n}>{n}</option>)}
          </select>
        </div>

        <div className="space-y-2">
          <label className="text-sm text-gray-400">Source photo</label>
          <select className="bg-[#1a1a24] border border-gray-700 rounded-lg px-4 py-2 text-white"
            value={sourcePhoto} onChange={e => setSourcePhoto(e.target.value)}>
            {photos.data?.map(p => <option key={p.filename} value={p.filename}>{p.filename}</option>)}
          </select>
        </div>

        <button
          className="px-6 py-2 bg-purple-600 hover:bg-purple-500 text-white font-medium rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          disabled={!description.trim() || mutation.isPending}
          onClick={() => mutation.mutate({ description, count, source_photo: sourcePhoto })}
        >
          {mutation.isPending ? 'Starting...' : 'Generate'}
        </button>
      </div>

      {mutation.isSuccess && (
        <div className="p-4 bg-green-900/30 border border-green-700 rounded-lg text-green-300">
          Job #{mutation.data.id} started. Check the Jobs tab for progress.
        </div>
      )}

      {mutation.isError && (
        <div className="p-4 bg-red-900/30 border border-red-700 rounded-lg text-red-300">
          Failed to start generation. Make sure ComfyUI and Ollama are running.
        </div>
      )}
    </div>
  )
}

function JobsPage() {
  const jobs = useQuery({ queryKey: ['jobs'], queryFn: getJobs, refetchInterval: 2000 })

  const statusColor = (s: string) => {
    switch (s) {
      case 'completed': return 'text-green-400'
      case 'generating': case 'expanding': return 'text-yellow-400'
      case 'failed': return 'text-red-400'
      default: return 'text-gray-400'
    }
  }

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-4">
      <h2 className="text-lg font-semibold text-white">Generation Jobs</h2>
      {jobs.data?.length === 0 && <p className="text-gray-500">No jobs yet. Go generate something.</p>}
      {jobs.data?.map(job => (
        <JobCard key={job.id} job={job} statusColor={statusColor} />
      ))}
    </div>
  )
}

function JobCard({ job, statusColor }: { job: JobOut; statusColor: (s: string) => string }) {
  const [expanded, setExpanded] = useState(false)
  const progress = job.total_images > 0 ? (job.completed_images / job.total_images) * 100 : 0

  return (
    <div className="bg-[#1a1a24] border border-gray-700 rounded-lg p-4 space-y-3">
      <div className="flex justify-between items-center">
        <div>
          <span className="text-white font-medium">Job #{job.id}</span>
          <span className={`ml-3 text-sm font-mono ${statusColor(job.status)}`}>{job.status}</span>
        </div>
        <span className="text-sm text-gray-500">{new Date(job.created_at).toLocaleString()}</span>
      </div>
      <p className="text-gray-300 text-sm">{job.description}</p>

      {job.status === 'generating' && (
        <div className="w-full bg-gray-700 rounded-full h-2">
          <div className="bg-purple-500 h-2 rounded-full transition-all" style={{ width: `${progress}%` }} />
        </div>
      )}
      <div className="text-xs text-gray-500">{job.completed_images}/{job.total_images} images</div>

      {job.images.length > 0 && (
        <>
          <button className="text-xs text-purple-400 hover:text-purple-300" onClick={() => setExpanded(!expanded)}>
            {expanded ? 'Hide images' : `Show ${job.images.length} images`}
          </button>
          {expanded && (
            <div className="grid grid-cols-3 gap-2 mt-2">
              {job.images.map(img => (
                <div key={img.id} className="relative group">
                  <img src={imageUrl(img.filename)} alt={img.scene_description || ''} className="rounded w-full" />
                  <div className="absolute bottom-0 left-0 right-0 bg-black/70 text-xs text-gray-300 p-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    {img.scene_description}
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {job.error_message && <p className="text-xs text-red-400">{job.error_message}</p>}
    </div>
  )
}

function GalleryPage() {
  const gallery = useQuery({ queryKey: ['gallery'], queryFn: getGallery, refetchInterval: 5000 })
  const [selected, setSelected] = useState<string | null>(null)

  return (
    <div className="p-6">
      <h2 className="text-lg font-semibold text-white mb-4">Gallery ({gallery.data?.length || 0} images)</h2>
      <div className="columns-2 md:columns-3 lg:columns-4 gap-3">
        {gallery.data?.map(img => (
          <div key={img.filename} className="mb-3 break-inside-avoid cursor-pointer group" onClick={() => setSelected(img.filename)}>
            <img src={imageUrl(img.filename)} alt={img.filename} className="rounded-lg w-full group-hover:ring-2 ring-purple-500 transition-all" />
          </div>
        ))}
      </div>

      {selected && (
        <div className="fixed inset-0 bg-black/90 flex items-center justify-center z-50" onClick={() => setSelected(null)}>
          <img src={imageUrl(selected)} alt={selected} className="max-h-[90vh] max-w-[90vw] rounded-lg" />
          <p className="absolute bottom-4 text-gray-400 text-sm">{selected}</p>
        </div>
      )}
    </div>
  )
}

function App() {
  return (
    <div className="min-h-screen bg-[#0f0f13]">
      <Nav />
      <Routes>
        <Route path="/" element={<GeneratePage />} />
        <Route path="/jobs" element={<JobsPage />} />
        <Route path="/gallery" element={<GalleryPage />} />
      </Routes>
    </div>
  )
}

export default App
