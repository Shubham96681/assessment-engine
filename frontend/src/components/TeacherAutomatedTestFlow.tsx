import { useCallback, useEffect, useMemo, useState } from 'react'
import { apiUrl, authHeaders } from '../apiBase'
import { Loader2, Wand2, CheckCircle2, ChevronLeft } from 'lucide-react'

type PreviewQuestion = {
  id: string
  questionType: string
  questionText: string
  difficulty: string
  suggestedMarks: number
  topics: string[]
  chapter: string | null
  subject: { id: string; name: string } | null
  options: { id: string; optionText: string; isCorrect: boolean }[]
  tags: string[]
}

type PreviewSummary = {
  totalQuestions: number
  validQuestions: number
  invalidCount: number
  qualityScore: number
  topicCoveragePct: number
  difficultyBalance: Record<string, number>
  difficultyBalanceLabel: string
  warnings?: string[]
  issues?: { questionId: string; issues: string[] }[]
}

type Props = {
  accessToken: string | null
  onCancel: () => void
  onCreated?: () => void
}

function defaultWindow() {
  const start = new Date()
  const end = new Date(start.getTime() + 7 * 24 * 60 * 60 * 1000)
  return { start: start.toISOString(), end: end.toISOString() }
}

type BankFilters = {
  questionCount: number
  topics: string[]
  tagFilters: string[]
  chapters: string[]
}

type CbseChapter = { title: string; rel: string; bookId: string | null }
type CbseBook = { label: string; bookKey: string; chapters: CbseChapter[] }
type CbseSubject = { label: string; books: CbseBook[] }
type CbseClass = { label: string; subjects: CbseSubject[] }
type CbseTreePayload = {
  diskRootConfigured: boolean
  diskPdfCount: number
  importedBooksWithPath: number
  classes: CbseClass[]
}

/** Board/tag options now come from `GET /questions/bank-filters`. This stays empty; defining the name avoids `ReferenceError` if a dev HMR chunk still references the old `BOARDS` binding. */
const BOARDS: readonly string[] = []

export function TeacherAutomatedTestFlow({ accessToken, onCancel, onCreated }: Props) {
  const authBypassUi = import.meta.env.VITE_AUTH_DISABLED === 'true'
  const canUseApi = Boolean(accessToken) || authBypassUi

  const [step, setStep] = useState<'setup' | 'review'>('setup')
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [title, setTitle] = useState('Auto-generated assessment')
  const [description, setDescription] = useState('')
  const [durationMinutes, setDurationMinutes] = useState(60)
  const [maxAttempts, setMaxAttempts] = useState(1)
  const [passingMarks, setPassingMarks] = useState(40)
  const [numberOfQuestions, setNumberOfQuestions] = useState(20)

  const [types, setTypes] = useState({
    mcq: true,
    true_false: true,
    fill_blank: true,
    descriptive: true,
  })
  const [mix, setMix] = useState({ mcq: 40, true_false: 20, fill_blank: 20, descriptive: 20 })
  const [difficulty, setDifficulty] = useState({ easy: 30, medium: 50, hard: 20 })
  const [marksByType, setMarksByType] = useState({ mcq: 1, true_false: 1, fill_blank: 2, descriptive: 4 })

  const [subjectId, setSubjectId] = useState('')
  const [subjects, setSubjects] = useState<{ id: string; name: string }[]>([])
  const [board, setBoard] = useState('')
  const [chapterLabel, setChapterLabel] = useState('')
  const [topics, setTopics] = useState<string[]>([])
  const [includeHeritage, setIncludeHeritage] = useState(false)
  const [excludeSample, setExcludeSample] = useState(false)

  const [bankFilters, setBankFilters] = useState<BankFilters | null>(null)
  const [bankFiltersError, setBankFiltersError] = useState<string | null>(null)

  const [cbseTree, setCbseTree] = useState<CbseTreePayload | null>(null)
  const [cbseTreeError, setCbseTreeError] = useState<string | null>(null)
  const [cbseClassLabel, setCbseClassLabel] = useState('')
  const [cbseSubjectLabel, setCbseSubjectLabel] = useState('')
  const [cbseBookKey, setCbseBookKey] = useState('')
  const [cbseChapterRel, setCbseChapterRel] = useState('')

  const [preview, setPreview] = useState<PreviewQuestion[]>([])
  const [summary, setSummary] = useState<PreviewSummary | null>(null)
  const [genParams, setGenParams] = useState<Record<string, unknown> | null>(null)
  const [approved, setApproved] = useState<Record<string, boolean>>({})
  const [marks, setMarks] = useState<Record<string, number>>({})

  const headers = useCallback(() => authHeaders(accessToken), [accessToken])

  useEffect(() => {
    if (!canUseApi) return
    void (async () => {
      setBankFiltersError(null)
      try {
        const [subRes, bfRes, qRes, cbseRes] = await Promise.all([
          fetch(apiUrl('/api/v1/subjects'), { headers: headers() }),
          fetch(apiUrl('/api/v1/questions/bank-filters'), { headers: headers() }),
          fetch(apiUrl('/api/v1/questions?limit=500'), { headers: headers() }),
          fetch(apiUrl('/api/v1/resources/cbse-curriculum-tree'), { headers: headers() }),
        ])
        const subBody = await subRes.json().catch(() => ({}))
        const bfBody = await bfRes.json().catch(() => ({}))
        const qBody = await qRes.json().catch(() => ({}))
        const cbseBody = await cbseRes.json().catch(() => ({}))

        setCbseTreeError(null)
        if (cbseRes.ok && cbseBody.data && typeof cbseBody.data === 'object') {
          const d = cbseBody.data as CbseTreePayload
          setCbseTree({
            diskRootConfigured: Boolean(d.diskRootConfigured),
            diskPdfCount: Number(d.diskPdfCount) || 0,
            importedBooksWithPath: Number(d.importedBooksWithPath) || 0,
            classes: Array.isArray(d.classes) ? d.classes : [],
          })
        } else {
          setCbseTree(null)
          if (!cbseRes.ok) {
            setCbseTreeError(
              typeof cbseBody.message === 'string' ? cbseBody.message : `Curriculum tree (${cbseRes.status})`
            )
          }
        }

        if (bfRes.ok && bfBody.data && typeof bfBody.data === 'object') {
          const d = bfBody.data as BankFilters
          setBankFilters({
            questionCount: Number(d.questionCount) || 0,
            topics: Array.isArray(d.topics) ? d.topics : [],
            tagFilters: Array.isArray(d.tagFilters) ? d.tagFilters : [],
            chapters: Array.isArray(d.chapters) ? d.chapters : [],
          })
        } else {
          setBankFilters({ questionCount: 0, topics: [], tagFilters: [], chapters: [] })
          if (!bfRes.ok) {
            setBankFiltersError(
              typeof bfBody.message === 'string' ? bfBody.message : `Could not load bank filters (${bfRes.status})`
            )
          }
        }

        const map = new Map<string, string>()
        if (subRes.ok && Array.isArray(subBody.data)) {
          for (const s of subBody.data as { id: string; name: string }[]) {
            map.set(s.id, s.name)
          }
        }
        if (qRes.ok && Array.isArray(qBody.data)) {
          const rows = qBody.data as { subject?: { id: string; name: string } | null }[]
          for (const r of rows) {
            if (r.subject?.id) map.set(r.subject.id, r.subject.name)
          }
        }
        setSubjects(
          [...map.entries()]
            .map(([id, name]) => ({ id, name }))
            .sort((a, b) => a.name.localeCompare(b.name))
        )
      } catch {
        setBankFiltersError('Could not load question bank metadata.')
        setBankFilters({ questionCount: 0, topics: [], tagFilters: [], chapters: [] })
        setCbseTree(null)
        setCbseTreeError('Could not load curriculum tree.')
      }
    })()
  }, [canUseApi, headers])

  const cbseSubjects = useMemo(() => {
    const c = cbseTree?.classes.find((x) => x.label === cbseClassLabel)
    return c?.subjects ?? []
  }, [cbseTree, cbseClassLabel])

  const cbseBooks = useMemo(() => {
    const s = cbseSubjects.find((x) => x.label === cbseSubjectLabel)
    return s?.books ?? []
  }, [cbseSubjects, cbseSubjectLabel])

  const cbseChapters = useMemo(() => {
    const b = cbseBooks.find((x) => x.bookKey === cbseBookKey)
    return b?.chapters ?? []
  }, [cbseBooks, cbseBookKey])

  const selectedCbseChapter = useMemo(
    () => cbseChapters.find((ch) => ch.rel === cbseChapterRel) ?? null,
    [cbseChapters, cbseChapterRel]
  )

  const toggleTopic = (t: string) => {
    setTopics((prev) => (prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t]))
  }

  const buildGenerationBody = () => ({
    numberOfQuestions,
    questionTypes: types,
    questionTypeMix: mix,
    difficultyDistribution: difficulty,
    marksByType,
    subjectId: subjectId || null,
    board: board.trim() || null,
    chapterLabel: chapterLabel || null,
    topics,
    includeHeritage,
    excludeTags: excludeSample ? ['sample_paper'] : [],
    resourcePriority: { preferExtracted: true },
    localLibraryRel: cbseChapterRel.trim() || null,
  })

  const onGenerate = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    if (!canUseApi) {
      setError('You must be logged in.')
      return
    }
    setLoading(true)
    try {
      const body = buildGenerationBody()
      const res = await fetch(apiUrl('/api/v1/tests/generate-preview'), {
        method: 'POST',
        headers: { ...headers(), 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const json = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(json.message || `Generation failed (${res.status})`)
      const data = json.data
      const qs: PreviewQuestion[] = data.questions ?? []
      setPreview(qs)
      setSummary(data.summary ?? null)
      setGenParams(data.generationParameters ?? body)
      const appr: Record<string, boolean> = {}
      const mk: Record<string, number> = {}
      for (const q of qs) {
        appr[q.id] = true
        mk[q.id] = q.suggestedMarks
      }
      setApproved(appr)
      setMarks(mk)
      setStep('review')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Generation failed')
    } finally {
      setLoading(false)
    }
  }

  const onCreateDraft = async () => {
    setError(null)
    if (!canUseApi) {
      setError('You must be logged in.')
      return
    }
    const approvedList = preview.filter((q) => approved[q.id])
    if (!approvedList.length) {
      setError('Approve at least one question.')
      return
    }
    const totalMarks = approvedList.reduce((s, q) => s + (marks[q.id] ?? q.suggestedMarks), 0)
    const schedule = defaultWindow()
    setSaving(true)
    try {
      const test = {
        title: title.trim() || 'Untitled test',
        description: description.trim() || null,
        subjectId: subjectId || null,
        classIds: [],
        durationMinutes,
        totalMarks,
        passingMarks,
        instructions: 'Answer all questions. Read each section carefully.',
        questionSelectionMode: 'mixed' as const,
        shuffleQuestions: false,
        shuffleOptions: true,
        showResultsImmediately: false,
        allowReview: true,
        maxAttempts,
        showAnswersAfterTest: false,
        negativeMarking: false,
        negativeMarkingValue: 0.25,
        startTime: schedule.start,
        endTime: schedule.end,
        status: 'draft' as const,
        settings: {},
      }
      const res = await fetch(apiUrl('/api/v1/tests/from-generation'), {
        method: 'POST',
        headers: { ...headers(), 'Content-Type': 'application/json' },
        body: JSON.stringify({
          generationParameters: genParams,
          test,
          approvedQuestions: approvedList.map((q) => ({
            questionId: q.id,
            marks: marks[q.id] ?? q.suggestedMarks,
            sectionName: null,
          })),
        }),
      })
      const json = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(json.message || `Could not create test (${res.status})`)
      onCreated?.()
      onCancel()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  if (!canUseApi) {
    return (
      <div className="border-[2px] border-ink rounded-lg p-5 bg-paper text-sm font-bold text-ink/70">
        Sign in to use automated test generation.
      </div>
    )
  }

  if (step === 'review') {
    const s: PreviewSummary =
      summary ?? {
        totalQuestions: preview.length,
        validQuestions: preview.length,
        invalidCount: 0,
        qualityScore: 0,
        topicCoveragePct: 0,
        difficultyBalance: {},
        difficultyBalanceLabel: '',
      }
    return (
      <div className="border-[2px] border-ink rounded-lg p-5 bg-paper space-y-5">
        <div className="flex justify-between items-start gap-4 flex-wrap">
          <button
            type="button"
            onClick={() => setStep('setup')}
            className="inline-flex items-center gap-1 text-xs font-bold text-cobalt border-b border-dashed border-cobalt cursor-pointer"
          >
            <ChevronLeft size={14} /> Back to settings
          </button>
          <button type="button" onClick={onCancel} className="text-xs font-bold text-ink/60 border-b border-dashed cursor-pointer">
            Close
          </button>
        </div>

        <div className="bg-white border-[2px] border-ink rounded-xl p-4 shadow-[2px_2px_0_0_#1A1A1A]">
          <h4 className="font-display font-black text-lg mb-2">Generation summary</h4>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-bold">
            <div>
              <p className="text-ink/50">Total</p>
              <p className="font-display text-xl">{s.totalQuestions}</p>
            </div>
            <div>
              <p className="text-ink/50">Valid</p>
              <p className="font-display text-xl text-mint">{s.validQuestions}</p>
            </div>
            <div>
              <p className="text-ink/50">Quality</p>
              <p className="font-display text-xl">{s.qualityScore}/100</p>
            </div>
            <div>
              <p className="text-ink/50">Topic coverage</p>
              <p className="font-display text-xl">{s.topicCoveragePct}%</p>
            </div>
          </div>
          <p className="text-xs font-bold text-ink/60 mt-2">{s.difficultyBalanceLabel}</p>
          {(s.warnings ?? []).map((w) => (
            <p key={w} className="text-xs font-bold text-bubble mt-1">
              {w}
            </p>
          ))}
        </div>

        {error && <p className="text-sm font-bold text-bubble">{error}</p>}

        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => {
              const next: Record<string, boolean> = {}
              for (const q of preview) next[q.id] = true
              setApproved(next)
            }}
            className="text-xs font-bold px-3 py-2 border-[2px] border-ink rounded-lg bg-mint/40 cursor-pointer"
          >
            Approve all
          </button>
          <button
            type="button"
            onClick={() => {
              const next: Record<string, boolean> = {}
              for (const q of preview) next[q.id] = false
              setApproved(next)
            }}
            className="text-xs font-bold px-3 py-2 border-[2px] border-ink rounded-lg bg-paper cursor-pointer"
          >
            Clear approvals
          </button>
        </div>

        <div className="space-y-4 max-h-[55vh] overflow-y-auto pr-1">
          {preview.map((q, i) => (
            <div key={q.id} className="bg-white border-[2px] border-ink rounded-lg p-4 space-y-2">
              <div className="flex flex-wrap justify-between gap-2">
                <p className="font-display font-bold text-sm">
                  {i + 1}. <span className="uppercase text-ink/50">{q.questionType}</span> · {q.difficulty}
                </p>
                <label className="flex items-center gap-2 text-xs font-bold cursor-pointer">
                  <input
                    type="checkbox"
                    checked={!!approved[q.id]}
                    onChange={() => setApproved((p) => ({ ...p, [q.id]: !p[q.id] }))}
                  />
                  Approve
                </label>
              </div>
              <p className="text-sm font-bold">{q.questionText}</p>
              {q.options?.length > 0 && (
                <ul className="text-xs font-bold space-y-1 pl-4 list-disc">
                  {q.options.map((o) => (
                    <li key={o.id} className={o.isCorrect ? 'text-mint' : ''}>
                      {o.optionText} {o.isCorrect ? '✓' : ''}
                    </li>
                  ))}
                </ul>
              )}
              <div className="flex flex-wrap gap-3 items-center text-xs">
                <label className="font-bold flex items-center gap-1">
                  Marks
                  <input
                    type="number"
                    min={0.5}
                    step={0.5}
                    value={marks[q.id] ?? q.suggestedMarks}
                    onChange={(e) =>
                      setMarks((m) => ({
                        ...m,
                        [q.id]: Number(e.target.value) || 1,
                      }))
                    }
                    className="w-16 p-1 border-[2px] border-ink rounded"
                  />
                </label>
                {q.subject && (
                  <span className="text-ink/50">
                    Subject: {q.subject.name}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>

        <div className="flex justify-end gap-3 pt-2 border-t-[2px] border-dashed border-ink/30">
          <button
            type="button"
            disabled={saving}
            onClick={() => void onCreateDraft()}
            className="inline-flex items-center gap-2 bg-cobalt text-white font-display font-extrabold text-sm px-5 py-2.5 border-[2px] border-ink rounded-lg shadow-[3px_3px_0_0_#1A1A1A] disabled:opacity-50 cursor-pointer"
          >
            {saving ? <Loader2 className="animate-spin" size={18} /> : <CheckCircle2 size={18} />}
            Create draft test
          </button>
        </div>
      </div>
    )
  }

  return (
    <form onSubmit={onGenerate} className="border-[2px] border-ink rounded-lg p-5 bg-paper space-y-6">
      <div className="flex justify-between items-center">
        <h4 className="font-display font-bold text-lg flex items-center gap-2">
          <Wand2 size={20} /> Quick test (auto-select from bank)
        </h4>
        <button type="button" onClick={onCancel} className="text-xs font-bold text-ink/60 border-b border-dashed cursor-pointer">
          Cancel
        </button>
      </div>

      <p className="text-xs font-bold text-ink/60">
        Picks existing school questions to match counts, types, and difficulty. Add questions via Resources → extract or the
        question bank first. Subject, topics, tag, and chapter options below come from your live question bank.
      </p>

      {error && <p className="text-sm font-bold text-bubble">{error}</p>}

      {bankFiltersError && (
        <p className="text-xs font-bold text-bubble border-[2px] border-ink rounded-lg p-2 bg-bubble/20">{bankFiltersError}</p>
      )}
      {bankFilters && (
        <p className="text-[11px] font-bold text-ink/50">
          Bank scan: {bankFilters.questionCount} question(s) indexed for filters (topics / tags / chapters).
        </p>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="md:col-span-2">
          <label className="font-display font-bold text-xs block mb-1">Test title *</label>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full p-2 border-[2px] border-ink rounded-lg text-sm"
            required
          />
        </div>
        <div className="md:col-span-2">
          <label className="font-display font-bold text-xs block mb-1">Description</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={2}
            className="w-full p-2 border-[2px] border-ink rounded-lg text-sm"
          />
        </div>
        <div>
          <label className="font-display font-bold text-xs block mb-1">Duration (minutes)</label>
          <input
            type="number"
            min={1}
            value={durationMinutes}
            onChange={(e) => setDurationMinutes(Number(e.target.value) || 60)}
            className="w-full p-2 border-[2px] border-ink rounded-lg text-sm"
          />
        </div>
        <div>
          <label className="font-display font-bold text-xs block mb-1">Max attempts</label>
          <input
            type="number"
            min={1}
            value={maxAttempts}
            onChange={(e) => setMaxAttempts(Number(e.target.value) || 1)}
            className="w-full p-2 border-[2px] border-ink rounded-lg text-sm"
          />
        </div>
        <div>
          <label className="font-display font-bold text-xs block mb-1">Passing marks (%)</label>
          <input
            type="number"
            min={0}
            max={100}
            value={passingMarks}
            onChange={(e) => setPassingMarks(Number(e.target.value) || 0)}
            className="w-full p-2 border-[2px] border-ink rounded-lg text-sm"
          />
        </div>
        <div>
          <label className="font-display font-bold text-xs block mb-1">Number of questions</label>
          <input
            type="number"
            min={1}
            max={100}
            value={numberOfQuestions}
            onChange={(e) => setNumberOfQuestions(Number(e.target.value) || 20)}
            className="w-full p-2 border-[2px] border-ink rounded-lg text-sm"
          />
        </div>
      </div>

      <div>
        <p className="font-display font-bold text-xs mb-2">Question types</p>
        <div className="flex flex-wrap gap-3 text-xs font-bold">
          {(['mcq', 'true_false', 'fill_blank', 'descriptive'] as const).map((k) => (
            <label key={k} className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" checked={types[k]} onChange={() => setTypes((t) => ({ ...t, [k]: !t[k] }))} />
              {k.replace('_', ' ')}
            </label>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {(['mcq', 'true_false', 'fill_blank', 'descriptive'] as const).map((k) => (
          <div key={k}>
            <label className="font-display font-bold text-xs block mb-1">% {k}</label>
            <input
              type="number"
              min={0}
              max={100}
              value={mix[k]}
              onChange={(e) => setMix((m) => ({ ...m, [k]: Number(e.target.value) || 0 }))}
              className="w-full p-2 border-[2px] border-ink rounded-lg text-sm"
            />
          </div>
        ))}
      </div>

      <div className="grid grid-cols-3 gap-3">
        {(['easy', 'medium', 'hard'] as const).map((k) => (
          <div key={k}>
            <label className="font-display font-bold text-xs block mb-1">% {k}</label>
            <input
              type="number"
              min={0}
              max={100}
              value={difficulty[k]}
              onChange={(e) => setDifficulty((d) => ({ ...d, [k]: Number(e.target.value) || 0 }))}
              className="w-full p-2 border-[2px] border-ink rounded-lg text-sm"
            />
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {(['mcq', 'true_false', 'fill_blank', 'descriptive'] as const).map((k) => (
          <div key={`m-${k}`}>
            <label className="font-display font-bold text-xs block mb-1">Marks ({k})</label>
            <input
              type="number"
              min={0.5}
              step={0.5}
              value={marksByType[k]}
              onChange={(e) => setMarksByType((m) => ({ ...m, [k]: Number(e.target.value) || 1 }))}
              className="w-full p-2 border-[2px] border-ink rounded-lg text-sm"
            />
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 border-t-[2px] border-dashed border-ink/20 pt-4">
        {(cbseTree?.classes.length ?? 0) > 0 && (
          <div className="md:col-span-2 rounded-xl border-[2px] border-ink/15 bg-ink/[0.02] p-4 space-y-3">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <p className="font-display font-bold text-sm">CBSE library: class → subject → book → chapter</p>
              <button
                type="button"
                className="text-[10px] font-bold underline decoration-2 underline-offset-2"
                onClick={() => {
                  setCbseClassLabel('')
                  setCbseSubjectLabel('')
                  setCbseBookKey('')
                  setCbseChapterRel('')
                  setChapterLabel('')
                }}
              >
                Clear picks
              </button>
            </div>
            {cbseTree && (
              <p className="text-[10px] font-bold text-ink/45">
                {cbseTree.diskRootConfigured
                  ? `Disk: ${cbseTree.diskPdfCount} PDF(s) under LOCAL_CBSE_LIBRARY_ROOT. `
                  : 'Set LOCAL_CBSE_LIBRARY_ROOT on the API to scan your CBSE folder. '}
                Imported books with path: {cbseTree.importedBooksWithPath}. Questions filter to a chapter only after that PDF is imported as a book and extracted.
              </p>
            )}
            {cbseTreeError && <p className="text-xs font-bold text-red-700">{cbseTreeError}</p>}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              <div>
                <label className="font-display font-bold text-xs block mb-1">Class</label>
                <select
                  value={cbseClassLabel}
                  onChange={(e) => {
                    setCbseClassLabel(e.target.value)
                    setCbseSubjectLabel('')
                    setCbseBookKey('')
                    setCbseChapterRel('')
                  }}
                  className="w-full p-2 border-[2px] border-ink rounded-lg text-sm font-bold"
                >
                  <option value="">—</option>
                  {(cbseTree?.classes ?? []).map((c) => (
                    <option key={c.label} value={c.label}>
                      {c.label}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="font-display font-bold text-xs block mb-1">Subject (folder)</label>
                <select
                  value={cbseSubjectLabel}
                  disabled={!cbseClassLabel}
                  onChange={(e) => {
                    setCbseSubjectLabel(e.target.value)
                    setCbseBookKey('')
                    setCbseChapterRel('')
                  }}
                  className="w-full p-2 border-[2px] border-ink rounded-lg text-sm font-bold disabled:opacity-50"
                >
                  <option value="">—</option>
                  {cbseSubjects.map((s) => (
                    <option key={s.label} value={s.label}>
                      {s.label}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="font-display font-bold text-xs block mb-1">Book</label>
                <select
                  value={cbseBookKey}
                  disabled={!cbseSubjectLabel}
                  onChange={(e) => {
                    setCbseBookKey(e.target.value)
                    setCbseChapterRel('')
                  }}
                  className="w-full p-2 border-[2px] border-ink rounded-lg text-sm font-bold disabled:opacity-50"
                >
                  <option value="">—</option>
                  {cbseBooks.map((b) => (
                    <option key={b.bookKey} value={b.bookKey}>
                      {b.label}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="font-display font-bold text-xs block mb-1">Chapter (PDF)</label>
                <select
                  value={cbseChapterRel}
                  disabled={!cbseBookKey}
                  onChange={(e) => {
                    const rel = e.target.value
                    setCbseChapterRel(rel)
                    if (rel) setSubjectId('')
                    const ch = cbseChapters.find((c) => c.rel === rel)
                    if (ch) setChapterLabel(ch.title)
                    else if (!rel) setChapterLabel('')
                  }}
                  className="w-full p-2 border-[2px] border-ink rounded-lg text-sm font-bold disabled:opacity-50"
                >
                  <option value="">—</option>
                  {cbseChapters.map((ch) => (
                    <option key={ch.rel} value={ch.rel}>
                      {ch.title}
                      {ch.bookId ? '' : ' · not imported'}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            {selectedCbseChapter && !selectedCbseChapter.bookId && (
              <p className="text-xs font-bold text-amber-800">
                This PDF is visible from disk but is not registered as a book yet. Use Resources → Add curriculum → import local CBSE, then extract questions from that book. Until then, “Generate preview” cannot narrow the pool to this file.
              </p>
            )}
            {selectedCbseChapter?.bookId && (
              <p className="text-xs font-bold text-ink/60">
                This chapter is linked to a library book. If preview shows zero scoped questions, open{' '}
                <strong>Resources → My books</strong>, find this book, choose an extract mode, and click <strong>Extract</strong>{' '}
                (use <strong>Chapter patterns only</strong> for NCERT-style prose). Then generate preview again.
              </p>
            )}
          </div>
        )}

        <div>
          <label className="font-display font-bold text-xs block mb-1">Subject (optional)</label>
          <select
            value={subjectId}
            onChange={(e) => setSubjectId(e.target.value)}
            className="w-full p-2 border-[2px] border-ink rounded-lg text-sm font-bold"
          >
            <option value="">All subjects in bank</option>
            {subjects.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
          {subjects.length === 0 && (
            <p className="text-xs font-bold text-ink/50 mt-1">
              No subjects yet for your school. Run <span className="font-mono">npx prisma db seed</span> in the backend (adds demo subjects) or create subjects in the database.
            </p>
          )}
        </div>
        <div>
          <label className="font-display font-bold text-xs block mb-1">Tag / board filter (optional)</label>
          <select
            value={board}
            onChange={(e) => setBoard(e.target.value)}
            className="w-full p-2 border-[2px] border-ink rounded-lg text-sm font-bold"
          >
            <option value="">Any — do not filter by tag</option>
            {(bankFilters?.tagFilters ?? [...BOARDS]).map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
          <p className="text-[10px] font-bold text-ink/45 mt-1">
            Matches questions that have a tag containing this text (same as server “board” filter). Options = distinct tags in your bank.
          </p>
        </div>
        <div className="md:col-span-2">
          <label className="font-display font-bold text-xs block mb-1">Chapter / unit (contains)</label>
          <input
            value={chapterLabel}
            onChange={(e) => setChapterLabel(e.target.value)}
            placeholder="Type or pick from bank chapters…"
            list="auto-test-chapter-suggestions"
            className="w-full p-2 border-[2px] border-ink rounded-lg text-sm"
          />
          <datalist id="auto-test-chapter-suggestions">
            {(bankFilters?.chapters ?? []).map((c) => (
              <option key={c} value={c} />
            ))}
          </datalist>
          <p className="text-[10px] font-bold text-ink/45 mt-1">
            Suggestions from your bank’s <span className="font-mono">chapter</span> field; you can still type a partial match.
          </p>
        </div>
      </div>

      <div>
        <p className="font-display font-bold text-xs mb-2">Topics (optional filters)</p>
        {(bankFilters?.topics ?? []).length === 0 ? (
          <p className="text-xs font-bold text-ink/50">No topic strings on questions yet — add topics when creating or editing questions.</p>
        ) : (
          <div className="flex flex-wrap gap-2 max-h-40 overflow-y-auto pr-1">
            {(bankFilters?.topics ?? []).map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => toggleTopic(t)}
                className={`text-xs font-bold px-2 py-1 rounded-lg border-[2px] border-ink cursor-pointer ${
                  topics.includes(t) ? 'bg-mint' : 'bg-white'
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="flex flex-wrap gap-4 text-xs font-bold">
        <label className="flex items-center gap-2 cursor-pointer">
          <input type="checkbox" checked={includeHeritage} onChange={() => setIncludeHeritage((v) => !v)} />
          Prefer heritage-tagged items
        </label>
        {(bankFilters?.tagFilters ?? []).some((x) => x.toLowerCase() === 'sample_paper') && (
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={excludeSample} onChange={() => setExcludeSample((v) => !v)} />
            Exclude tag “sample_paper”
          </label>
        )}
      </div>

      <div className="flex justify-end">
        <button
          type="submit"
          disabled={loading}
          className="inline-flex items-center gap-2 bg-lemon font-display font-extrabold text-sm px-5 py-2.5 border-[2px] border-ink rounded-lg shadow-[3px_3px_0_0_#1A1A1A] disabled:opacity-50 cursor-pointer"
        >
          {loading ? <Loader2 className="animate-spin" size={18} /> : <Wand2 size={18} />}
          Generate preview
        </button>
      </div>
    </form>
  )
}
