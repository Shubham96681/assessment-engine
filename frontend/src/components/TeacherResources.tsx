import { useCallback, useEffect, useMemo, useState } from 'react'
import { BookOpen, ChevronRight, ExternalLink, Eye, FolderOpen, Loader2, Upload, Wand2 } from 'lucide-react'
import { apiUrl, authHeaders } from '../apiBase'
import { resourcesLibraryFolderUrl } from '../config/resourcesLibrary'

type BookMetadata = {
  localLibraryRel?: string
  libraryKind?: string
  localLibrary?: boolean
}

type BookRow = {
  id: string
  title: string
  author: string | null
  fileName: string
  fileType: string
  processingStatus: string
  questionsExtracted: number
  createdAt: string
  fileSize?: string
  metadata?: BookMetadata | Record<string, unknown>
}

type ListMeta = { total?: number; page?: number; limit?: number }

type ExtractedQuestionRow = {
  id: string
  questionType: string
  questionText: string
  difficulty: string
  options?: { id: string; optionText: string; isCorrect: boolean }[]
}

/** CBSE-style path: CLASS N / Subject / … / file.pdf → folder grouping */
function classSortKey(label: string): number {
  const m = /^CLASS\s*(\d+)/i.exec(label.trim())
  return m ? Number.parseInt(m[1], 10) : 999
}

function parseLibraryFolders(rel: string): { className: string; subjectName: string; pathDetail: string } | null {
  const parts = rel.split('/').filter(Boolean)
  if (parts.length < 2) return null
  const file = parts[parts.length - 1]
  const className = parts[0]
  const subjectName = parts[1]
  const mid = parts.slice(2, -1)
  const pathDetail = mid.length ? `${mid.join(' / ')} · ${file}` : file
  return { className, subjectName, pathDetail }
}

function groupBooksByFolders(books: BookRow[]) {
  const tree = new Map<string, Map<string, BookRow[]>>()
  const other: BookRow[] = []

  for (const b of books) {
    const meta = b.metadata && typeof b.metadata === 'object' ? (b.metadata as BookMetadata) : null
    const rel = meta?.localLibraryRel
    if (typeof rel === 'string' && rel.trim()) {
      const parsed = parseLibraryFolders(rel)
      if (parsed) {
        const { className, subjectName } = parsed
        if (!tree.has(className)) tree.set(className, new Map())
        const sub = tree.get(className)!
        if (!sub.has(subjectName)) sub.set(subjectName, [])
        sub.get(subjectName)!.push(b)
      } else {
        other.push(b)
      }
    } else {
      other.push(b)
    }
  }

  const sortedClasses = [...tree.keys()].sort((a, b) => {
    const da = classSortKey(a)
    const db = classSortKey(b)
    if (da !== db) return da - db
    return a.localeCompare(b)
  })

  return { tree, sortedClasses, other }
}

type Props = {
  accessToken: string | null
}

export function TeacherResources({ accessToken }: Props) {
  const [books, setBooks] = useState<BookRow[]>([])
  const [listMeta, setListMeta] = useState<ListMeta | null>(null)
  const [loading, setLoading] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [title, setTitle] = useState('')
  const [author, setAuthor] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [banner, setBanner] = useState<{ type: 'ok' | 'err'; text: string } | null>(null)
  const [extractingId, setExtractingId] = useState<string | null>(null)
  const [extractStrategy, setExtractStrategy] = useState<'numbered_first' | 'non_ai_only' | 'combined'>(
    'numbered_first'
  )
  const [questionsPanelBookId, setQuestionsPanelBookId] = useState<string | null>(null)
  const [bookQuestionsById, setBookQuestionsById] = useState<Record<string, ExtractedQuestionRow[]>>({})
  const [bookQuestionsLoading, setBookQuestionsLoading] = useState<string | null>(null)
  const [bookQuestionsError, setBookQuestionsError] = useState<string | null>(null)
  const [libUrlTitle, setLibUrlTitle] = useState('')
  const [libUrlAuthor, setLibUrlAuthor] = useState('')
  const [libFileUrl, setLibFileUrl] = useState('')
  const [libFileName, setLibFileName] = useState('')
  const [registeringUrl, setRegisteringUrl] = useState(false)
  const [importingCbse, setImportingCbse] = useState(false)
  /** Default off so “Run CBSE import” registers books; turn on to only preview counts. */
  const [cbseDryRun, setCbseDryRun] = useState(false)
  const [cbseLimit, setCbseLimit] = useState('')
  const [resourcesTab, setResourcesTab] = useState<'books' | 'add'>('books')

  const authBypassUi = import.meta.env.VITE_AUTH_DISABLED === 'true'

  const headers = useCallback(() => authHeaders(accessToken), [accessToken])

  const loadBooks = useCallback(async () => {
    if (!accessToken && !authBypassUi) return
    setLoading(true)
    setLoadError(null)
    try {
      const res = await fetch(apiUrl('/api/v1/resources?type=book&limit=500'), { headers: headers() })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body.message || `Could not load books (${res.status})`)
      setBooks(body.data ?? [])
      setListMeta(body.meta ?? null)
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : 'Failed to load books')
      setBooks([])
      setListMeta(null)
    } finally {
      setLoading(false)
    }
  }, [accessToken, headers, authBypassUi])

  const fetchQuestionsForBook = useCallback(
    async (bookId: string) => {
      setBookQuestionsLoading(bookId)
      setBookQuestionsError(null)
      try {
        const qs = new URLSearchParams({
          limit: '200',
          sourceResourceId: bookId,
          sourceResourceType: 'book',
        })
        const res = await fetch(apiUrl(`/api/v1/questions?${qs.toString()}`), { headers: headers() })
        const body = await res.json().catch(() => ({}))
        if (!res.ok) throw new Error(body.message || `Could not load questions (${res.status})`)
        setBookQuestionsById((m) => ({ ...m, [bookId]: Array.isArray(body.data) ? body.data : [] }))
      } catch (e) {
        setBookQuestionsError(e instanceof Error ? e.message : 'Failed to load questions')
        setBookQuestionsById((m) => ({ ...m, [bookId]: [] }))
      } finally {
        setBookQuestionsLoading(null)
      }
    },
    [headers]
  )

  const toggleBookQuestionsPanel = (bookId: string) => {
    if (questionsPanelBookId === bookId) {
      setQuestionsPanelBookId(null)
      return
    }
    setQuestionsPanelBookId(bookId)
    void fetchQuestionsForBook(bookId)
  }

  const { tree, sortedClasses, other } = useMemo(() => groupBooksByFolders(books), [books])

  useEffect(() => {
    void loadBooks()
  }, [loadBooks])

  const onUpload = async (e: React.FormEvent) => {
    e.preventDefault()
    setBanner(null)
    if (!accessToken) {
      setBanner({ type: 'err', text: 'You need to be logged in with a school account to upload books.' })
      return
    }
    if (!file) {
      setBanner({ type: 'err', text: 'Choose a PDF or text file to upload.' })
      return
    }
    if (!title.trim()) {
      setBanner({ type: 'err', text: 'Title is required.' })
      return
    }

    const fd = new FormData()
    fd.append('file', file)
    fd.append('title', title.trim())
    if (author.trim()) fd.append('author', author.trim())

    setUploading(true)
    try {
      const res = await fetch(apiUrl('/api/v1/resources/books'), {
        method: 'POST',
        headers: headers(),
        body: fd,
      })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body.message || `Upload failed (${res.status})`)
      setBanner({ type: 'ok', text: 'Book uploaded successfully.' })
      setFile(null)
      setTitle('')
      setAuthor('')
      await loadBooks()
    } catch (err) {
      setBanner({ type: 'err', text: err instanceof Error ? err.message : 'Upload failed' })
    } finally {
      setUploading(false)
    }
  }

  const onRegisterFromUrl = async (e: React.FormEvent) => {
    e.preventDefault()
    setBanner(null)
    if (!accessToken) return
    if (!libUrlTitle.trim()) {
      setBanner({ type: 'err', text: 'Title is required for the linked book.' })
      return
    }
    if (!libFileUrl.trim()) {
      setBanner({ type: 'err', text: 'Paste a public https file URL (not the folder link).' })
      return
    }
    setRegisteringUrl(true)
    try {
      const body: Record<string, string> = {
        title: libUrlTitle.trim(),
        fileUrl: libFileUrl.trim(),
      }
      if (libUrlAuthor.trim()) body.author = libUrlAuthor.trim()
      if (libFileName.trim()) body.fileName = libFileName.trim()
      const res = await fetch(apiUrl('/api/v1/resources/books/from-url'), {
        method: 'POST',
        headers: { ...headers(), 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const json = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(json.message || `Could not add book (${res.status})`)
      setBanner({ type: 'ok', text: 'Book linked. You can run extraction when ready.' })
      setLibUrlTitle('')
      setLibUrlAuthor('')
      setLibFileUrl('')
      setLibFileName('')
      await loadBooks()
    } catch (err) {
      setBanner({ type: 'err', text: err instanceof Error ? err.message : 'Request failed' })
    } finally {
      setRegisteringUrl(false)
    }
  }

  const onImportLocalCbse = async (e: React.FormEvent) => {
    e.preventDefault()
    setBanner(null)
    if (!accessToken) return
    const lim = cbseLimit.trim()
    let limit: number | null = null
    if (lim) {
      const n = Number.parseInt(lim, 10)
      if (Number.isNaN(n) || n < 1) {
        setBanner({ type: 'err', text: 'Limit must be a positive integer or empty for no cap.' })
        return
      }
      limit = n
    }
    setImportingCbse(true)
    try {
      const res = await fetch(apiUrl('/api/v1/resources/books/import-local-cbse'), {
        method: 'POST',
        headers: { ...headers(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ dryRun: cbseDryRun, limit }),
      })
      const json = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(json.message || `Import failed (${res.status})`)
      const d = json.data as {
        scanned: number
        created: number
        skipped: number
        dryRun: boolean
        books: unknown[]
      }
      const preview = d.dryRun
        ? ` Preview ${d.books?.length ?? 0} new file(s) (cap applies).`
        : ''
      setBanner({
        type: 'ok',
        text: `CBSE scan: ${d.scanned} PDF(s). ${d.dryRun ? 'Dry run — no books created.' : `Created ${d.created} book(s).`} Skipped ${d.skipped} (already imported).${preview}`,
      })
      if (!d.dryRun) {
        await loadBooks()
        setResourcesTab('books')
      }
    } catch (err) {
      setBanner({ type: 'err', text: err instanceof Error ? err.message : 'Import failed' })
    } finally {
      setImportingCbse(false)
    }
  }

  const onExtract = async (id: string) => {
    if (!accessToken && !authBypassUi) return
    setBanner(null)
    setExtractingId(id)
    try {
      const res = await fetch(apiUrl(`/api/v1/resources/book/${id}/extract`), {
        method: 'POST',
        headers: { ...headers(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ strategy: extractStrategy }),
      })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body.message || `Extraction failed (${res.status})`)
      const n = body.data?.questionsCreated ?? 0
      const method = typeof body.data?.method === 'string' ? body.data.method : ''
      setBanner({
        type: 'ok',
        text: n
          ? `Created ${n} draft question(s)${method ? ` (${method})` : ''}. Use "View extracted" on this book to review them.`
          : 'Extraction finished.',
      })
      await loadBooks()
      if (questionsPanelBookId === id) void fetchQuestionsForBook(id)
    } catch (err) {
      setBanner({ type: 'err', text: err instanceof Error ? err.message : 'Extraction failed' })
    } finally {
      setExtractingId(null)
    }
  }

  if (!accessToken && !authBypassUi) {
    return (
      <div className="bg-white border-[2px] border-ink rounded-xl p-6 shadow-[3px_3px_0_0_#1A1A1A]">
        <h3 className="font-display font-black text-2xl mb-2">Resources</h3>
        <p className="text-sm font-bold text-ink/70 mb-4">
          Sign in with your school account (same email and password as the Assessment Engine API) to upload books.
          Use the seeded teacher e.g. <span className="font-mono text-xs bg-paper px-1 border border-ink rounded">teacher@demo-school.test</span> after running{' '}
          <span className="font-mono text-xs">npx prisma db seed</span> on the backend.
        </p>
      </div>
    )
  }

  const libraryFolder = resourcesLibraryFolderUrl()

  const tabBtn = (id: 'books' | 'add', label: string) => (
    <button
      type="button"
      role="tab"
      aria-selected={resourcesTab === id}
      onClick={() => setResourcesTab(id)}
      className={`font-display font-extrabold text-sm px-4 py-2 rounded-lg border-[2px] border-ink transition-all cursor-pointer ${
        resourcesTab === id
          ? 'bg-cobalt text-white shadow-[3px_3px_0_0_#1A1A1A]'
          : 'bg-white text-ink hover:bg-paper shadow-[2px_2px_0_0_#1A1A1A]'
      }`}
    >
      {label}
    </button>
  )

  const renderBookQuestionsPanel = (bookId: string) => {
    if (questionsPanelBookId !== bookId) return null
    const list = bookQuestionsById[bookId] ?? []
    return (
      <div className="w-full border-t-[2px] border-dashed border-ink/20 pt-3 space-y-2 max-h-72 overflow-y-auto text-left">
        {bookQuestionsLoading === bookId && (
          <p className="text-xs font-bold text-ink/50 flex items-center gap-2 justify-center py-2">
            <Loader2 className="animate-spin" size={14} /> Loading extracted questions…
          </p>
        )}
        {bookQuestionsLoading !== bookId && bookQuestionsError && (
          <p className="text-xs font-bold text-red-700">{bookQuestionsError}</p>
        )}
        {bookQuestionsLoading !== bookId && !bookQuestionsError && list.length === 0 && (
          <p className="text-xs font-bold text-ink/55">
            No draft questions for this book yet. Choose an extract mode and click Extract questions.
          </p>
        )}
        {bookQuestionsLoading !== bookId &&
          !bookQuestionsError &&
          list.map((q) => (
            <div key={q.id} className="rounded-lg border-[2px] border-ink/25 bg-white p-2.5">
              <p className="text-[10px] font-bold text-ink/45 uppercase tracking-wide">
                {q.questionType} · {q.difficulty}
              </p>
              <p className="text-xs font-bold text-ink mt-1 whitespace-pre-wrap break-words">{q.questionText}</p>
              {q.options && q.options.length > 0 && (
                <ul className="mt-2 text-[11px] font-bold text-ink/80 list-disc pl-4 space-y-0.5">
                  {q.options.map((o) => (
                    <li key={o.id} className={o.isCorrect ? 'text-emerald-800' : ''}>
                      {o.optionText}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ))}
      </div>
    )
  }

  return (
    <div className="bg-white border-[2px] border-ink rounded-xl shadow-[3px_3px_0_0_#1A1A1A] overflow-hidden">
      <div className="border-b-[2px] border-ink bg-paper px-4 py-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h3 className="font-display font-black text-2xl">School library</h3>
          <p className="text-xs font-bold text-ink/55 mt-0.5">Browse imported books or add PDFs for your school.</p>
        </div>
        <div className="flex flex-wrap gap-2" role="tablist" aria-label="Library sections">
          {tabBtn('books', 'My books')}
          {tabBtn('add', 'Add curriculum')}
        </div>
      </div>

      {banner && (
        <div
          className={`mx-4 mt-4 p-3 rounded-lg border-[2px] text-sm font-bold ${
            banner.type === 'ok' ? 'bg-mint/30 border-ink' : 'bg-bubble/40 border-ink'
          }`}
        >
          {banner.text}
        </div>
      )}

      {resourcesTab === 'add' && (
        <div className="p-6 space-y-10 border-t-[2px] border-dashed border-ink/20">
          <div className="flex items-start gap-3">
            <div className="p-2 bg-mint/40 border-[2px] border-ink rounded-lg shadow-[2px_2px_0_0_#1A1A1A] shrink-0">
              <ExternalLink size={22} />
            </div>
            <div className="flex-1 min-w-0">
              <h4 className="font-display font-black text-xl">Curriculum library (Drive)</h4>
              <p className="text-sm font-bold text-ink/60 mt-1">
                Open the shared folder, download a PDF, then upload below — or paste a direct <strong>https</strong> file link.
              </p>
              <a
                href={libraryFolder}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 mt-3 font-display font-extrabold text-sm text-cobalt border-b-2 border-dashed border-cobalt hover:text-ink hover:border-ink"
              >
                <ExternalLink size={16} />
                Open Books folder in Google Drive
              </a>
            </div>
          </div>

        <form onSubmit={onRegisterFromUrl} className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2 border-t-[2px] border-dashed border-ink/20">
          <div className="md:col-span-2">
            <p className="text-xs font-bold text-ink/55 mb-2">
              Optional: add a book from a direct file URL (e.g. public <span className="font-mono">uc?export=download</span>{' '}
              style link). Private or HTML-only links will fail on extract.
            </p>
          </div>
          <div>
            <label className="font-display font-bold text-xs block mb-1">Title *</label>
            <input
              value={libUrlTitle}
              onChange={(e) => setLibUrlTitle(e.target.value)}
              className="w-full p-2.5 border-[2px] border-ink rounded-lg text-sm focus:outline-none focus:shadow-[2px_2px_0_0_#1A1A1A]"
              placeholder="e.g. CBSE Science sample paper"
            />
          </div>
          <div>
            <label className="font-display font-bold text-xs block mb-1">Author</label>
            <input
              value={libUrlAuthor}
              onChange={(e) => setLibUrlAuthor(e.target.value)}
              className="w-full p-2.5 border-[2px] border-ink rounded-lg text-sm focus:outline-none focus:shadow-[2px_2px_0_0_#1A1A1A]"
              placeholder="Optional"
            />
          </div>
          <div className="md:col-span-2">
            <label className="font-display font-bold text-xs block mb-1">File URL * (https)</label>
            <input
              value={libFileUrl}
              onChange={(e) => setLibFileUrl(e.target.value)}
              className="w-full p-2.5 border-[2px] border-ink rounded-lg text-sm font-mono focus:outline-none focus:shadow-[2px_2px_0_0_#1A1A1A]"
              placeholder="https://…"
            />
          </div>
          <div className="md:col-span-2">
            <label className="font-display font-bold text-xs block mb-1">File name hint (optional)</label>
            <input
              value={libFileName}
              onChange={(e) => setLibFileName(e.target.value)}
              className="w-full p-2.5 border-[2px] border-ink rounded-lg text-sm focus:outline-none focus:shadow-[2px_2px_0_0_#1A1A1A]"
              placeholder="e.g. chapter3.pdf (helps pick PDF vs text)"
            />
          </div>
          <div>
            <button
              type="submit"
              disabled={registeringUrl}
              className="inline-flex items-center gap-2 bg-paper font-display font-extrabold text-sm px-5 py-2.5 border-[2px] border-ink rounded-lg shadow-[3px_3px_0_0_#1A1A1A] hover:translate-x-[-1px] hover:translate-y-[-1px] disabled:opacity-60 cursor-pointer"
            >
              {registeringUrl ? <Loader2 className="animate-spin" size={18} /> : <BookOpen size={18} />}
              Add book from URL
            </button>
          </div>
        </form>

        <form onSubmit={onImportLocalCbse} className="mt-6 pt-6 border-t-[2px] border-dashed border-ink/20 grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="md:col-span-2 flex items-start gap-3">
            <div className="p-2 bg-mint/40 border-[2px] border-ink rounded-lg shadow-[2px_2px_0_0_#1A1A1A] shrink-0">
              <FolderOpen size={22} />
            </div>
            <div>
              <h4 className="font-display font-black text-lg">Import from server CBSE folder</h4>
              <p className="text-xs font-bold text-ink/55 mt-1">
                Set <span className="font-mono">LOCAL_CBSE_LIBRARY_ROOT</span> in backend <span className="font-mono">.env</span> to
                the absolute path of your unpacked CBSE folder (class → subject → chapter PDFs). Then dry-run or import; extraction
                reads PDFs from disk — nothing is uploaded to S3.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <input
              id="cbse-dry-run"
              type="checkbox"
              checked={cbseDryRun}
              onChange={(e) => setCbseDryRun(e.target.checked)}
              className="h-4 w-4 border-[2px] border-ink rounded accent-cobalt cursor-pointer"
            />
            <label htmlFor="cbse-dry-run" className="text-sm font-bold cursor-pointer">
              Dry run only (preview counts, no books created)
            </label>
          </div>
          <div>
            <label className="font-display font-bold text-xs block mb-1">Max books (optional)</label>
            <input
              value={cbseLimit}
              onChange={(e) => setCbseLimit(e.target.value)}
              className="w-full p-2.5 border-[2px] border-ink rounded-lg text-sm font-mono focus:outline-none focus:shadow-[2px_2px_0_0_#1A1A1A]"
              placeholder="empty = all PDFs (dry-run preview capped at 80)"
            />
          </div>
          <div className="md:col-span-2">
            <button
              type="submit"
              disabled={importingCbse}
              className="inline-flex items-center gap-2 bg-white font-display font-extrabold text-sm px-5 py-2.5 border-[2px] border-ink rounded-lg shadow-[3px_3px_0_0_#1A1A1A] hover:translate-x-[-1px] hover:translate-y-[-1px] disabled:opacity-60 cursor-pointer"
            >
              {importingCbse ? <Loader2 className="animate-spin" size={18} /> : <FolderOpen size={18} />}
              Run CBSE import
            </button>
          </div>
        </form>

          <div className="border-t-[2px] border-dashed border-ink/20 pt-10 space-y-6">
            <div className="flex items-start gap-3">
              <div className="p-2 bg-lemon border-[2px] border-ink rounded-lg shadow-[2px_2px_0_0_#1A1A1A] shrink-0">
                <Upload size={22} />
              </div>
              <div>
                <h4 className="font-display font-black text-xl">Upload a book</h4>
                <p className="text-sm font-bold text-ink/60 mt-1">
                  PDF or plain text. Stored on the server (S3/MinIO when configured). Then run{' '}
                  <strong>non-AI text extraction</strong> to draft numbered questions.
                </p>
              </div>
            </div>

            <form onSubmit={onUpload} className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="space-y-4">
            <div>
              <label className="font-display font-bold text-xs block mb-1">Title *</label>
              <input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full p-2.5 border-[2px] border-ink rounded-lg text-sm focus:outline-none focus:shadow-[2px_2px_0_0_#1A1A1A]"
                placeholder="e.g. NCERT Mathematics X"
              />
            </div>
            <div>
              <label className="font-display font-bold text-xs block mb-1">Author</label>
              <input
                value={author}
                onChange={(e) => setAuthor(e.target.value)}
                className="w-full p-2.5 border-[2px] border-ink rounded-lg text-sm focus:outline-none focus:shadow-[2px_2px_0_0_#1A1A1A]"
                placeholder="Optional"
              />
            </div>
            <div>
              <label className="font-display font-bold text-xs block mb-1">File *</label>
              <input
                type="file"
                accept=".pdf,.txt,application/pdf,text/plain"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                className="w-full text-sm font-bold file:mr-3 file:py-2 file:px-3 file:rounded-lg file:border-[2px] file:border-ink file:bg-paper file:font-display file:font-extrabold file:text-xs"
              />
            </div>
            <button
              type="submit"
              disabled={uploading}
              className="inline-flex items-center gap-2 bg-cobalt text-white font-display font-extrabold text-sm px-5 py-2.5 border-[2px] border-ink rounded-lg shadow-[3px_3px_0_0_#1A1A1A] hover:translate-x-[-1px] hover:translate-y-[-1px] disabled:opacity-60 cursor-pointer"
            >
              {uploading ? <Loader2 className="animate-spin" size={18} /> : <Upload size={18} />}
              Upload book
            </button>
          </div>
          <div className="bg-paper border-[2px] border-dashed border-ink rounded-xl p-5 text-sm font-bold text-ink/70">
            <p className="mb-2 font-display text-ink">Tips</p>
            <ul className="list-disc pl-5 space-y-2">
              <li>
                Use the{' '}
                <a href={libraryFolder} target="_blank" rel="noopener noreferrer" className="text-cobalt underline">
                  shared Books folder
                </a>{' '}
                to download PDFs, then upload here.
              </li>
              <li>Ensure the backend is running on port 3000 (Vite proxies <code className="font-mono text-xs">/api</code> there).</li>
              <li>Numbered questions in PDFs (1., 2)) extract more reliably than unstructured prose.</li>
              <li>
                Under <strong>My books</strong>, choose an extract mode: textbook-style PDFs can use <strong>Chapter patterns
                only</strong> (see NON_AI_QUESTION_GENERATION.md on the repo).
              </li>
              <li>MCQ answer keys for numbered items are not guessed — edit questions after extraction.</li>
            </ul>
          </div>
            </form>
          </div>
        </div>
      )}

      {resourcesTab === 'books' && (
        <div className="p-6 border-t-[2px] border-dashed border-ink/15">
        <div className="flex justify-between items-start gap-3 mb-4 flex-wrap">
          <div>
            <h3 className="font-display font-black text-2xl flex items-center gap-2">
              <FolderOpen size={22} /> Your curriculum folders
            </h3>
            <p className="text-xs font-bold text-ink/55 mt-1 max-w-2xl">
              CBSE imports are grouped by <strong>class</strong> and <strong>subject</strong> (same as your disk folders). Uploads
              without a library path appear under “Other books.”
            </p>
            <label className="mt-3 block text-[10px] font-bold text-ink/50 uppercase tracking-wide">
              Extract mode (non-AI)
            </label>
            <select
              value={extractStrategy}
              onChange={(e) =>
                setExtractStrategy(e.target.value as 'numbered_first' | 'non_ai_only' | 'combined')
              }
              className="mt-1 max-w-xs w-full p-2 border-[2px] border-ink rounded-lg text-xs font-bold bg-white"
            >
              <option value="numbered_first">Numbered items first, then chapter patterns if none</option>
              <option value="non_ai_only">Chapter patterns only (definitions, blanks, true/false)</option>
              <option value="combined">Numbered + chapter patterns (deduped)</option>
            </select>
          </div>
          <div className="flex flex-col items-end gap-1 shrink-0">
            {listMeta?.total != null && (
              <span className="text-xs font-bold text-ink/60">
                {books.length} loaded
                {listMeta.total > books.length ? ` · ${listMeta.total} total (raise limit if needed)` : ` · ${listMeta.total} total`}
              </span>
            )}
            <button
              type="button"
              onClick={() => void loadBooks()}
              className="text-xs font-bold border-b-2 border-dashed border-cobalt text-cobalt cursor-pointer"
            >
              Refresh
            </button>
          </div>
        </div>

        {loading && (
          <div className="flex items-center gap-2 text-sm font-bold text-ink/60 py-6">
            <Loader2 className="animate-spin" size={18} /> Loading…
          </div>
        )}
        {loadError && (
          <p className="text-sm font-bold text-bubble py-2 border-[2px] border-ink rounded-lg px-3 bg-bubble/20">
            {loadError}
            <span className="block text-xs font-bold text-ink/70 mt-2">
              If this says 401, set <span className="font-mono">AUTH_DISABLED=true</span> in backend{' '}
              <span className="font-mono">.env</span> for local dev or log in and refresh.
            </span>
          </p>
        )}
        {!loading && !loadError && books.length === 0 && (
          <div className="rounded-xl border-[2px] border-dashed border-ink/35 bg-paper p-6 space-y-4">
            <p className="font-display font-black text-lg">No books in your school library yet</p>
            <p className="text-sm font-bold text-ink/65">
              Books appear here after they are registered in the database — a <strong>dry run</strong> does not create rows.
            </p>
            <ol className="list-decimal pl-5 space-y-2 text-sm font-bold text-ink/80">
              <li>
                Open the <strong>Add curriculum</strong> tab (above).
              </li>
              <li>
                Under <strong>Import from server CBSE folder</strong>, leave <strong>Dry run</strong> unchecked and click{' '}
                <strong>Run CBSE import</strong> (backend needs <span className="font-mono">LOCAL_CBSE_LIBRARY_ROOT</span>).
              </li>
              <li>Or upload PDFs / add a URL — then return to <strong>My books</strong> and refresh.</li>
            </ol>
            <button
              type="button"
              onClick={() => setResourcesTab('add')}
              className="inline-flex items-center gap-2 bg-lemon font-display font-extrabold text-sm px-5 py-2.5 border-[2px] border-ink rounded-lg shadow-[3px_3px_0_0_#1A1A1A] hover:translate-x-[-1px] hover:translate-y-[-1px] cursor-pointer"
            >
              <Upload size={18} /> Go to Add curriculum
            </button>
          </div>
        )}
        {!loading && !loadError && books.length > 0 && (
          <div className="space-y-3">
            {sortedClasses.map((className) => {
              const subjects = tree.get(className)!
              const subjectKeys = [...subjects.keys()].sort((a, b) => a.localeCompare(b))
              return (
                <details key={className} className="border-[2px] border-ink rounded-xl bg-paper shadow-[2px_2px_0_0_#1A1A1A]" open>
                  <summary className="font-display font-black text-lg cursor-pointer list-none flex items-center gap-2 p-4 hover:bg-white/80 rounded-xl [&::-webkit-details-marker]:hidden">
                    <ChevronRight size={20} className="shrink-0 text-ink" aria-hidden />
                    <FolderOpen size={20} className="text-cobalt shrink-0" />
                    <span>{className}</span>
                    <span className="text-xs font-bold text-ink/50 ml-auto">
                      {subjectKeys.reduce((n, s) => n + (subjects.get(s)?.length ?? 0), 0)} PDF(s)
                    </span>
                  </summary>
                  <div className="px-3 pb-3 pt-0 space-y-2 border-t-[2px] border-dashed border-ink/15">
                    {subjectKeys.map((subjectName) => {
                      const list = subjects.get(subjectName) ?? []
                      return (
                        <details key={`${className}/${subjectName}`} className="border-[2px] border-ink rounded-lg bg-white ml-2" open>
                          <summary className="font-display font-bold text-sm cursor-pointer list-none flex items-center gap-2 px-3 py-2.5 [&::-webkit-details-marker]:hidden">
                            <ChevronRight size={16} className="shrink-0 text-ink/80" aria-hidden />
                            <span>{subjectName}</span>
                            <span className="text-[11px] font-bold text-ink/45 ml-auto">{list.length} file(s)</span>
                          </summary>
                          <div className="space-y-2 px-3 pb-3 pt-1">
                            {list.map((b) => {
                              const rel =
                                b.metadata && typeof b.metadata === 'object' && 'localLibraryRel' in b.metadata
                                  ? String((b.metadata as BookMetadata).localLibraryRel || '')
                                  : ''
                              const parsed = rel ? parseLibraryFolders(rel) : null
                              return (
                                <div key={b.id} className="border-[2px] border-ink rounded-lg p-3 flex flex-col gap-3 bg-paper">
                                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                                    <div className="min-w-0">
                                      <p className="font-display font-bold text-base truncate">{b.title}</p>
                                      <p className="text-[11px] font-bold text-ink/50 truncate">
                                        {parsed?.pathDetail ?? b.fileName} · {b.processingStatus}
                                        {typeof b.questionsExtracted === 'number'
                                          ? ` · ${b.questionsExtracted} questions linked`
                                          : ''}
                                      </p>
                                    </div>
                                    <div className="flex flex-wrap items-center gap-2 shrink-0">
                                      <button
                                        type="button"
                                        disabled={!!extractingId}
                                        onClick={() => toggleBookQuestionsPanel(b.id)}
                                        className="inline-flex items-center gap-1.5 bg-white font-display font-extrabold text-xs px-3 py-2 border-[2px] border-ink rounded-lg shadow-[2px_2px_0_0_#1A1A1A] hover:translate-x-[-1px] hover:translate-y-[-1px] disabled:opacity-50 cursor-pointer"
                                      >
                                        <Eye size={14} aria-hidden />
                                        {questionsPanelBookId === b.id ? 'Hide' : 'View'} extracted
                                      </button>
                                      <button
                                        type="button"
                                        disabled={!!extractingId}
                                        onClick={() => void onExtract(b.id)}
                                        className="inline-flex items-center gap-1.5 bg-white font-display font-extrabold text-xs px-3 py-2 border-[2px] border-ink rounded-lg shadow-[2px_2px_0_0_#1A1A1A] hover:translate-x-[-1px] hover:translate-y-[-1px] disabled:opacity-50 cursor-pointer"
                                      >
                                        {extractingId === b.id ? (
                                          <Loader2 className="animate-spin" size={14} />
                                        ) : (
                                          <Wand2 size={14} />
                                        )}
                                        Extract questions
                                      </button>
                                    </div>
                                  </div>
                                  {renderBookQuestionsPanel(b.id)}
                                </div>
                              )
                            })}
                          </div>
                        </details>
                      )
                    })}
                  </div>
                </details>
              )
            })}

            {other.length > 0 && (
              <details className="border-[2px] border-ink rounded-xl bg-paper shadow-[2px_2px_0_0_#1A1A1A]" open>
                <summary className="font-display font-bold text-base cursor-pointer list-none flex items-center gap-2 p-4 [&::-webkit-details-marker]:hidden">
                  <ChevronRight size={18} className="shrink-0 text-ink/80" aria-hidden />
                  <BookOpen size={18} />
                  Other books
                  <span className="text-xs font-bold text-ink/50 ml-auto">{other.length}</span>
                </summary>
                <div className="space-y-2 px-4 pb-4">
                  {other.map((b) => (
                    <div key={b.id} className="border-[2px] border-ink rounded-lg p-3 flex flex-col gap-3 bg-white">
                      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                        <div className="min-w-0">
                          <p className="font-display font-bold text-base truncate">{b.title}</p>
                          <p className="text-[11px] font-bold text-ink/50 truncate">
                            {b.fileName} · {b.processingStatus}
                            {typeof b.questionsExtracted === 'number'
                              ? ` · ${b.questionsExtracted} questions linked`
                              : ''}
                          </p>
                        </div>
                        <div className="flex flex-wrap items-center gap-2 shrink-0">
                          <button
                            type="button"
                            disabled={!!extractingId}
                            onClick={() => toggleBookQuestionsPanel(b.id)}
                            className="inline-flex items-center gap-1.5 bg-paper font-display font-extrabold text-xs px-3 py-2 border-[2px] border-ink rounded-lg shadow-[2px_2px_0_0_#1A1A1A] disabled:opacity-50 cursor-pointer"
                          >
                            <Eye size={14} aria-hidden />
                            {questionsPanelBookId === b.id ? 'Hide' : 'View'} extracted
                          </button>
                          <button
                            type="button"
                            disabled={!!extractingId}
                            onClick={() => void onExtract(b.id)}
                            className="inline-flex items-center gap-1.5 bg-paper font-display font-extrabold text-xs px-3 py-2 border-[2px] border-ink rounded-lg shadow-[2px_2px_0_0_#1A1A1A] shrink-0 disabled:opacity-50 cursor-pointer"
                          >
                            {extractingId === b.id ? <Loader2 className="animate-spin" size={14} /> : <Wand2 size={14} />}
                            Extract questions
                          </button>
                        </div>
                      </div>
                      {renderBookQuestionsPanel(b.id)}
                    </div>
                  ))}
                </div>
              </details>
            )}
          </div>
        )}
        </div>
      )}
    </div>
  )
}
