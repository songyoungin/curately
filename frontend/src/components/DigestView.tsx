import { Link } from 'react-router-dom'
import { Lightbulb, Link2, Layers } from 'lucide-react'

import type { Digest, DigestSection as DigestSectionType } from '../types'

interface DigestViewProps {
  digest: Digest
}

export default function DigestView({ digest }: DigestViewProps) {
  const { content } = digest

  return (
    <div className="space-y-6">
      {/* Headline */}
      {content.headline && (
        <div className="rounded-xl bg-indigo-50 border border-indigo-100 p-5 sm:p-6">
          <p className="text-lg sm:text-xl font-semibold text-indigo-900 leading-relaxed">
            {content.headline}
          </p>
        </div>
      )}

      {/* Key Takeaways */}
      {content.key_takeaways.length > 0 && (
        <section className="rounded-xl bg-amber-50 border border-amber-100 p-4 sm:p-5">
          <h2 className="flex items-center gap-2 text-base font-semibold text-amber-900">
            <Lightbulb className="w-4 h-4" />
            Key Takeaways
          </h2>
          <ul className="mt-3 space-y-2">
            {content.key_takeaways.map((item, i) => (
              <li key={i} className="flex gap-2 text-sm text-amber-800">
                <span className="mt-1 block w-1.5 h-1.5 rounded-full bg-amber-400 shrink-0" />
                {item}
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Thematic Sections */}
      {content.sections.map((section, i) => (
        <DigestSectionCard key={i} section={section} />
      ))}

      {/* Connections */}
      {content.connections && (
        <section className="rounded-xl bg-gray-50 border border-gray-200 p-4 sm:p-5">
          <h2 className="flex items-center gap-2 text-base font-semibold text-gray-900">
            <Layers className="w-4 h-4 text-gray-600" />
            Connections
          </h2>
          <p className="mt-3 text-sm text-gray-700 leading-relaxed">
            {content.connections}
          </p>
        </section>
      )}
    </div>
  )
}

function DigestSectionCard({ section }: { section: DigestSectionType }) {
  // Build the Today page link with article filter
  const articleParam = section.article_ids.join(',')
  const todayLink = `/?articles=${articleParam}`

  return (
    <section className="rounded-xl bg-white border border-gray-200 p-4 sm:p-5">
      {/* Theme badge + title */}
      <div className="flex items-start justify-between gap-2">
        <div>
          <span className="inline-block px-2 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-700">
            {section.theme}
          </span>
          <h3 className="mt-2 text-base font-semibold text-gray-900">
            {section.title}
          </h3>
        </div>
      </div>

      {/* Body */}
      <p className="mt-3 text-sm text-gray-700 leading-relaxed">{section.body}</p>

      {/* Article link */}
      {section.article_ids.length > 0 && (
        <div className="mt-3 pt-3 border-t border-gray-100">
          <Link
            to={todayLink}
            className="inline-flex items-center gap-1 text-xs font-medium text-indigo-600 hover:text-indigo-800 transition-colors"
          >
            <Link2 className="w-3 h-3" />
            {section.article_ids.length} article
            {section.article_ids.length > 1 ? 's' : ''} →
          </Link>
        </div>
      )}
    </section>
  )
}
