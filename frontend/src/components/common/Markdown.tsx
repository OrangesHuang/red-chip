import React from 'react'

/** 轻量 Markdown 渲染器: 支持标题/粗体/行内代码/代码块/列表/引用/表格/链接。
 *  专为 AI 分析报告设计, 避免引入 react-markdown 依赖。 */

function renderInline(text: string, keyBase: string): React.ReactNode[] {
  // 先处理行内代码, 再处理粗体与链接(避免嵌套冲突)
  const parts = text.split(/(`[^`]+`)/g)
  return parts.map((part, i) => {
    if (part.startsWith('`') && part.endsWith('`')) {
      return (
        <code key={`${keyBase}-c${i}`} className="px-1 py-0.5 rounded bg-gray-800 text-orange-300 text-[0.85em]">
          {part.slice(1, -1)}
        </code>
      )
    }
    const boldParts = part.split(/(\*\*[^*]+\*\*)/g)
    return boldParts.map((bp, j) => {
      if (bp.startsWith('**') && bp.endsWith('**')) {
        return <strong key={`${keyBase}-b${i}-${j}`} className="text-gray-100 font-semibold">{bp.slice(2, -2)}</strong>
      }
      const linkParts = bp.split(/(\[[^\]]+\]\([^)]+\))/g)
      return linkParts.map((lp, k) => {
        const m = lp.match(/^\[([^\]]+)\]\(([^)]+)\)$/)
        if (m) {
          return (
            <a key={`${keyBase}-l${i}-${j}-${k}`} href={m[2]} target="_blank" rel="noreferrer" className="text-red-400 hover:underline">
              {m[1]}
            </a>
          )
        }
        return <React.Fragment key={`${keyBase}-t${i}-${j}-${k}`}>{lp}</React.Fragment>
      })
    })
  })
}

function parseTable(lines: string[]): { headers: string[]; rows: string[][] } | null {
  if (lines.length < 2 || !lines[0].trim().startsWith('|')) return null
  const cells = (line: string) => line.trim().replace(/^\||\|$/g, '').split('|').map(c => c.trim())
  const headers = cells(lines[0])
  // 第二行应为分隔线(---)
  if (!/^[\s|:-]+$/.test(lines[1])) return null
  const rows = lines.slice(2).filter(l => l.trim().startsWith('|')).map(cells)
  return { headers, rows }
}

export default function Markdown({ text }: { text: string }) {
  const lines = text.replace(/\r\n/g, '\n').split('\n')
  const blocks: React.ReactNode[] = []
  let i = 0
  let key = 0

  while (i < lines.length) {
    const line = lines[i]

    // 代码块
    if (line.trim().startsWith('```')) {
      const buf: string[] = []
      i++
      while (i < lines.length && !lines[i].trim().startsWith('```')) {
        buf.push(lines[i])
        i++
      }
      i++ // 跳过结束围栏
      blocks.push(
        <pre key={key++} className="my-2 p-3 rounded bg-gray-950 border border-gray-800 overflow-x-auto text-xs text-gray-300">
          {buf.join('\n')}
        </pre>,
      )
      continue
    }

    // 表格
    const table = parseTable(lines.slice(i, i + 20))
    if (table) {
      blocks.push(
        <div key={key++} className="my-2 overflow-x-auto">
          <table className="w-full text-xs border-collapse">
            <thead>
              <tr>
                {table.headers.map((h, j) => (
                  <th key={j} className="border border-gray-700 px-2 py-1 text-left text-gray-300 bg-gray-800/60">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {table.rows.map((r, j) => (
                <tr key={j}>
                  {r.map((c, k) => (
                    <td key={k} className="border border-gray-800 px-2 py-1 text-gray-400">{renderInline(c, `t${j}-${k}`)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>,
      )
      i += 2 + table.rows.length
      continue
    }

    // 标题
    const h = line.match(/^(#{1,4})\s+(.*)$/)
    if (h) {
      const level = h[1].length
      const cls = level === 1 ? 'text-lg font-bold text-white mt-4 mb-2'
        : level === 2 ? 'text-base font-bold text-white mt-4 mb-2'
        : 'text-sm font-semibold text-gray-100 mt-3 mb-1'
      blocks.push(
        <div key={key++} className={cls}>{renderInline(h[2], `h${key}`)}</div>,
      )
      i++
      continue
    }

    // 引用
    if (line.trim().startsWith('>')) {
      blocks.push(
        <blockquote key={key++} className="my-2 pl-3 border-l-2 border-gray-700 text-xs text-gray-500 italic">
          {renderInline(line.trim().replace(/^>\s?/, ''), `q${key}`)}
        </blockquote>,
      )
      i++
      continue
    }

    // 无序列表
    const ul = line.match(/^\s*[-*]\s+(.*)$/)
    if (ul) {
      const items: string[] = [ul[1]]
      i++
      while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*[-*]\s+/, ''))
        i++
      }
      blocks.push(
        <ul key={key++} className="my-1.5 pl-5 list-disc text-sm text-gray-300 space-y-0.5">
          {items.map((it, j) => <li key={j}>{renderInline(it, `ul${key}-${j}`)}</li>)}
        </ul>,
      )
      continue
    }

    // 有序列表
    const ol = line.match(/^\s*\d+[.、]\s+(.*)$/)
    if (ol) {
      const items: string[] = [ol[1]]
      i++
      while (i < lines.length && /^\s*\d+[.、]\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*\d+[.、]\s+/, ''))
        i++
      }
      blocks.push(
        <ol key={key++} className="my-1.5 pl-5 list-decimal text-sm text-gray-300 space-y-0.5">
          {items.map((it, j) => <li key={j}>{renderInline(it, `ol${key}-${j}`)}</li>)}
        </ol>,
      )
      continue
    }

    // 空行
    if (!line.trim()) {
      i++
      continue
    }

    // 普通段落
    blocks.push(
      <p key={key++} className="my-1.5 text-sm text-gray-300 leading-relaxed">
        {renderInline(line, `p${key}`)}
      </p>,
    )
    i++
  }

  return <div className="text-sm">{blocks}</div>
}
