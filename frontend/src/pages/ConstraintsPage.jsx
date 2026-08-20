import { useEffect, useMemo, useState } from 'react'
import axios from 'axios'

const BASE = 'http://localhost:8000'

function TypeBadge({ type }) {
  return <span className={`constraint-type ${type === 'hard' ? 'hard' : 'soft'}`}>{type}</span>
}

export default function ConstraintsPage() {
  const [text, setText] = useState('')
  const [preview, setPreview] = useState(null)
  const [clarification, setClarification] = useState(null)
  const [selection, setSelection] = useState(null)
  const [confirmedPreview, setConfirmedPreview] = useState(null)
  const [rules, setRules] = useState([])
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)

  async function loadRules() {
    try {
      const res = await axios.get(`${BASE}/constraints`)
      setRules(Array.isArray(res.data) ? res.data : [])
      setError(null)
    } catch (err) {
      setError(err?.response?.data?.detail || err?.message || 'Could not load active constraints')
    }
  }

  useEffect(() => { loadRules() }, [])

  async function review(extraSelection = null) {
    const value = text.trim()
    if (!value) return
    setLoading(true)
    setError(null)
    setSuccess(null)
    setPreview(null)
    if (!extraSelection) setClarification(null)

    try {
      const res = await axios.post(`${BASE}/constraints/preview`, {
        text: value,
        selection: extraSelection,
      })
      if (res.data?.status === 'needs_clarification') {
        setClarification(res.data)
        setSelection(extraSelection || null)
      } else {
        setClarification(null)
        setSelection(null)
        setPreview(res.data?.constraint || null)
      }
    } catch (err) {
      setError(err?.response?.data?.detail || err?.message || 'Could not interpret this constraint')
    } finally {
      setLoading(false)
    }
  }

  async function resolveSelection() {
    if (!selection) return
    await review(selection)
  }

  function confirmMeaning() {
    if (!preview) return
    setConfirmedPreview(preview)
    setPreview(null)
    setError(null)
    setSuccess(null)
  }

  function resetReview() {
    setPreview(null)
    setClarification(null)
    setSelection(null)
    setConfirmedPreview(null)
    setError(null)
  }

  async function applyConstraint() {
    if (!confirmedPreview) return
    setSaving(true)
    setError(null)
    setSuccess(null)
    try {
      await axios.post(`${BASE}/constraints`, { constraint: confirmedPreview })
      setConfirmedPreview(null)
      setText('')
      await loadRules()
      setSuccess('Constraint added successfully. It will be used the next time you generate a timetable.')
    } catch (err) {
      setError(err?.response?.data?.detail || err?.message || 'Could not add this constraint')
    } finally {
      setSaving(false)
    }
  }

  async function removeConstraint(id) {
    if (!window.confirm('Remove this constraint?')) return
    try {
      await axios.delete(`${BASE}/constraints/${id}`)
      setRules(current => current.filter(rule => rule.constraint_id !== id))
      setSuccess('Constraint removed from the active rule set.')
      setError(null)
    } catch (err) {
      setError(err?.response?.data?.detail || err?.message || 'Could not remove constraint')
    }
  }

  const hardCount = useMemo(() => rules.filter(r => r.constraint_type === 'hard').length, [rules])
  const softCount = useMemo(() => rules.filter(r => r.constraint_type === 'soft').length, [rules])

  return (
    <div className="constraints-page">
      <style>{`
        .constraints-page{min-height:100%;box-sizing:border-box;padding:28px 32px 60px;color:#13203a;font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:radial-gradient(circle at 8% 0%,rgba(96,165,250,.13),transparent 30%),radial-gradient(circle at 92% 8%,rgba(167,139,250,.11),transparent 28%),var(--bg-page,#f0f4f8)}
        .constraints-shell{max-width:1240px;margin:0 auto}.hero{padding:28px 30px;border:1px solid #dfe7f4;border-radius:22px;background:linear-gradient(135deg,#fff,#f3f0ff);box-shadow:0 12px 36px rgba(28,52,96,.07)}
        .eyebrow{color:#3564bb;font-size:10px;font-weight:850;letter-spacing:.17em}.hero h1{margin:7px 0 0;color:#101b35;font-size:30px;letter-spacing:-.035em}.hero p{margin:8px 0 0;max-width:760px;color:#71809d;font-size:13px;line-height:1.6}
        .grid{display:grid;grid-template-columns:minmax(0,1.12fr) minmax(350px,.88fr);gap:18px;margin-top:18px;align-items:start}.card{background:rgba(255,255,255,.95);border:1px solid #dfe6f1;border-radius:18px;box-shadow:0 10px 30px rgba(28,48,90,.06)}.head{padding:20px 22px;border-bottom:1px solid #e7ecf3}.title{color:#15213d;font-size:16px;font-weight:800}.sub{margin-top:4px;color:#71809d;font-size:11.5px;line-height:1.5}.body{padding:20px 22px 22px}
        textarea{width:100%;box-sizing:border-box;min-height:142px;resize:vertical;padding:14px;border:1px solid #cbd5e1;border-radius:12px;outline:none;color:#1e293b;background:#fbfdff;font:inherit;font-size:13px;line-height:1.55}textarea:focus{border-color:#5b8def;box-shadow:0 0 0 3px rgba(37,99,235,.09)}
        .examples{display:flex;flex-wrap:wrap;gap:7px;margin-top:11px}.example{border:1px solid #dbe4f2;background:#f7faff;color:#496386;border-radius:999px;padding:6px 10px;font-size:10.5px;cursor:pointer}.review{width:100%;margin-top:13px;min-height:48px;border:0;border-radius:12px;background:linear-gradient(135deg,#3b74f5,#6d3fe0);color:white;font-weight:800;cursor:pointer}.review:disabled{background:#c5d3eb;cursor:not-allowed}
        .feedback{margin-top:13px;padding:11px 13px;border-radius:10px;font-size:11.5px;line-height:1.5}.error{color:#991b1b;background:#fef2f2;border:1px solid #fecaca}.success{color:#166534;background:#f0fdf4;border:1px solid #bbf7d0}
        .clarify{margin-top:18px;padding:17px;border:1px solid #fcd34d;border-radius:14px;background:#fffbeb}.clarify h3{margin:0;color:#92400e;font-size:15px}.clarify p{margin:7px 0 12px;color:#78520a;font-size:11.5px;line-height:1.5}.options{display:grid;gap:8px}.option{display:flex;justify-content:space-between;align-items:center;gap:12px;width:100%;padding:11px 12px;border:1px solid #fde68a;border-radius:10px;background:white;text-align:left;cursor:pointer}.option.selected{border-color:#2563eb;box-shadow:0 0 0 2px rgba(37,99,235,.1)}.option-main{color:#1f2937;font-size:12px;font-weight:750}.option-meta{margin-top:3px;color:#64748b;font-size:10.5px}.radio{width:16px;height:16px;accent-color:#2563eb}.resolve{width:100%;margin-top:11px;min-height:42px;border:0;border-radius:9px;background:#2563eb;color:white;font-size:11.5px;font-weight:800;cursor:pointer}.resolve:disabled{opacity:.45;cursor:not-allowed}
        .preview{margin-top:18px;padding:17px;border:1px solid #bfdbfe;border-radius:14px;background:#f8fbff}.top{display:flex;justify-content:space-between;align-items:center;gap:12px}.preview-title{color:#1e3a8a;font-size:13px;font-weight:850}.badge{display:inline-flex;padding:4px 8px;border-radius:999px;font-size:9.5px;font-weight:850;text-transform:uppercase}.badge.hard{background:#eff6ff;color:#1d4ed8}.badge.soft{background:#fff7ed;color:#c2410c}.explanation{margin-top:12px;padding:13px;border:1px solid #e2e8f0;border-radius:10px;background:white;color:#334155;font-size:12.5px;line-height:1.55}.assumptions{margin-top:9px;color:#92400e;font-size:10.5px}.actions{display:grid;grid-template-columns:1fr 1.5fr;gap:8px;margin-top:11px}.secondary,.confirm,.apply{min-height:40px;border-radius:9px;font-size:11.5px;font-weight:750;cursor:pointer}.secondary{border:1px solid #cbd5e1;background:white;color:#475569}.confirm,.apply{border:0;background:#16a34a;color:white}.applybox{margin-top:18px;padding:18px;border:1px solid #bbf7d0;border-radius:14px;background:#f0fdf4}.applybox h3{margin:5px 0;color:#14532d;font-size:16px}.applybox p{margin:7px 0;color:#4b6b57;font-size:11.5px}.summarybox{padding:12px;border:1px solid #d1fae5;border-radius:10px;background:white;color:#334155;font-size:12px;line-height:1.5}
        .stats{padding:20px}.statrow{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:12px}.stat{padding:11px;border:1px solid #e2e8f0;border-radius:10px;background:#f8fafc}.num{font-size:19px;font-weight:850;color:#1b2a3b}.label{margin-top:2px;color:#64748b;font-size:9.5px;text-transform:uppercase}.ruleshead{padding:9px 20px;color:#475569;font-size:11px;font-weight:850;text-transform:uppercase}.rules{padding:0 20px 20px}.rule{padding:12px;margin-bottom:8px;border:1px solid #e2e8f0;border-radius:11px;background:#fff}.ruletop{display:flex;justify-content:space-between}.remove{border:0;background:transparent;color:#94a3b8;cursor:pointer;font-size:10.5px}.ruletext{margin-top:8px;color:#334155;font-size:11.5px;line-height:1.5}.empty{padding:24px 8px;text-align:center;color:#94a3b8;font-size:11.5px}.info{margin-top:18px;padding:13px 15px;border:1px solid #dbe4f2;border-radius:12px;background:#f7faff;color:#5b6f91;font-size:11px;line-height:1.5}
        @media(max-width:850px){.grid{grid-template-columns:1fr}}@media(max-width:600px){.constraints-page{padding:18px 14px 40px}.actions{grid-template-columns:1fr}}
      `}</style>

      <div className="constraints-shell">
        <section className="hero"><div className="eyebrow">SCHEDULING INTELLIGENCE</div><h1>Welcome New Constraints</h1><p>Describe timetable rules in plain English. The system interprets them, checks your actual database registrations, asks for clarification when a subject belongs to multiple classes, and only then saves the rule.</p></section>

        <div className="grid">
          <section className="card">
            <div className="head"><div className="title">Describe a new rule</div><div className="sub">Nothing is saved until you review the interpretation and explicitly apply it.</div></div>
            <div className="body">
              <textarea value={text} onChange={e => setText(e.target.value)} placeholder="For example: No classes on Tuesday." disabled={!!confirmedPreview} />
              <div className="examples">
                {['No classes on Tuesday.','No OS lab on Tuesday.','OS cannot occur on Tuesday.','Rahul cannot teach Monday period 3.'].map(example => <button key={example} className="example" onClick={() => setText(example)} disabled={!!confirmedPreview}>{example}</button>)}
              </div>
              <button className="review" onClick={() => review()} disabled={loading || !text.trim() || !!confirmedPreview}>{loading ? 'Interpreting and checking…' : 'Review this constraint →'}</button>

              {error && <div className="feedback error">{error}</div>}
              {success && <div className="feedback success">{success}</div>}

              {clarification && <div className="clarify">
                <h3>Which registration should this rule apply to?</h3>
                <p>{clarification.message}</p>
                <div className="options">
                  {clarification.options.map(option => {
                    const key = `${option.subject_id}-${option.class_id}-${option.subject_type}`
                    const selected = selection?.subject_id === option.subject_id
                    return <button key={key} className={`option ${selected ? 'selected' : ''}`} onClick={() => setSelection({subject_id: option.subject_id, class_id: option.class_id, subject_type: option.subject_type})}>
                      <div><div className="option-main">{option.subject_name} — {option.class_name}</div><div className="option-meta">{option.subject_type}</div></div>
                      <input className="radio" type="radio" checked={selected} onChange={() => {}} />
                    </button>
                  })}
                </div>
                <button className="resolve" onClick={resolveSelection} disabled={!selection || loading}>{loading ? 'Resolving…' : 'Use this class and type →'}</button>
              </div>}

              {preview && <div className="preview">
                <div className="top"><div className="preview-title">Step 1 · Review interpretation</div><TypeBadge type={preview.constraint_type} /></div>
                <div className="explanation">{preview.explanation}</div>
                {preview.assumptions?.length > 0 && <div className="assumptions"><strong>Assumptions:</strong> {preview.assumptions.join(' · ')}</div>}
                <div className="actions"><button className="secondary" onClick={resetReview}>No, edit</button><button className="confirm" onClick={confirmMeaning}>Yes, that's what I mean</button></div>
              </div>}

              {confirmedPreview && <div className="applybox">
                <div className="eyebrow">STEP 2 · APPLY</div><h3>Should we apply this rule?</h3><p>The rule is confirmed but is not saved yet.</p>
                <div className="summarybox"><strong>{confirmedPreview.explanation}</strong><br /><TypeBadge type={confirmedPreview.constraint_type} /></div>
                <div className="actions"><button className="secondary" onClick={resetReview}>Keep editing</button><button className="apply" onClick={applyConstraint} disabled={saving}>{saving ? 'Applying…' : 'Yes — apply to timetable'}</button></div>
              </div>}
            </div>
          </section>

          <section className="card">
            <div className="stats"><div className="title">Active rule library</div><div className="sub">Every rule shown here is applied automatically when you generate a timetable.</div><div className="statrow"><div className="stat"><div className="num">{rules.length}</div><div className="label">Active</div></div><div className="stat"><div className="num">{hardCount}</div><div className="label">Hard</div></div><div className="stat"><div className="num">{softCount}</div><div className="label">Soft</div></div></div></div>
            <div className="ruleshead">Current constraints</div><div className="rules">
              {rules.length === 0 ? <div className="empty">No active constraints yet.<br />Add your first rule on the left.</div> : rules.map(rule => <div className="rule" key={rule.constraint_id}><div className="ruletop"><TypeBadge type={rule.constraint_type} /><button className="remove" onClick={() => removeConstraint(rule.constraint_id)}>Remove</button></div><div className="ruletext">{rule.constraint?.explanation || rule.constraint_name || 'Saved constraint'}</div></div>)}
            </div>
          </section>
        </div>

        <div className="info"><strong>How it works:</strong> natural language → Gemini interpretation → database-aware entity resolution → clarification if needed → confirmation → saved rule → CP-SAT generation. Global rules such as “No classes on Tuesday” do not require a subject or class.</div>
      </div>
    </div>
  )
}
