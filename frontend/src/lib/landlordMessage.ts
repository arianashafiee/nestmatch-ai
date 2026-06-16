import type { ListingAnalysis, LandlordContact } from '@/types/apartment'
import type { StudentProfile } from '@/types/studentProfile'

export function generateLandlordMessage(
  analysis: ListingAnalysis,
  profile: StudentProfile,
  contact?: LandlordContact | null,
): string {
  const university = profile.university || 'my university'
  const location = analysis.location || 'your property'
  const rent =
    analysis.rent_monthly != null
      ? `$${analysis.rent_monthly.toLocaleString()}/month`
      : 'the listed rent'

  const questions = analysis.follow_up_questions
    .map((q, i) => `${i + 1}. ${q}`)
    .join('\n')

  const missing =
    analysis.missing_info.length > 0
      ? `\nI also noticed the listing didn't mention:\n${analysis.missing_info.map((m) => `• ${m}`).join('\n')}\n`
      : ''

  const greeting = contact?.name ? `Hi ${contact.name},` : 'Hi,'

  return `${greeting}

I'm a student at ${university} and I'm interested in your listing${analysis.title ? ` ("${analysis.title}")` : ''} near ${location}. The ${rent} range looks like it could work for my budget.

I'd love to learn a bit more before scheduling a tour. Could you help me with the following?

${questions}
${missing}
I'm hoping to move in for the upcoming semester and can tour on short notice. Please let me know your availability.

Thank you for your time!

Best,
[Your Name]
[Your Phone Number]`
}
