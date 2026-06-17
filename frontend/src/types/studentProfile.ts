export type CommuteMode = 'walking' | 'transit' | 'biking'

export type AmenityTag =
  | 'laundry'
  | 'parking'
  | 'ac'
  | 'furnished'
  | 'no_basements'

export interface StudentProfile {
  id?: number
  university: string
  campusLocation: string
  maxRent: number
  maxCommuteMinutes: number
  commuteMode: CommuteMode
  livingSituation: 'solo' | 'roommates'
  roommateCount: number
  mustHaves: AmenityTag[]
  dealbreakers: AmenityTag[]
  fullName: string
  phoneNumber: string
  preferredLeaseLength: string
}

export const LEASE_LENGTH_OPTIONS: { value: string; label: string }[] = [
  { value: '12 months', label: '12 months' },
  { value: '9 months (academic year)', label: '9 months (academic year)' },
  { value: '6 months', label: '6 months' },
  { value: '1 month', label: '1 month / month-to-month' },
  { value: 'August – May', label: 'August – May (school year)' },
]

export const AMENITY_OPTIONS: {
  value: AmenityTag
  label: string
}[] = [
  { value: 'laundry', label: 'Laundry' },
  { value: 'parking', label: 'Parking' },
  { value: 'ac', label: 'AC' },
  { value: 'furnished', label: 'Furnished' },
  { value: 'no_basements', label: 'No Basements' },
]

export const COMMUTE_OPTIONS: {
  value: CommuteMode
  label: string
}[] = [
  { value: 'walking', label: 'Walking' },
  { value: 'transit', label: 'Transit' },
  { value: 'biking', label: 'Biking' },
]

export const defaultStudentProfile: StudentProfile = {
  university: '',
  campusLocation: '',
  maxRent: 1500,
  maxCommuteMinutes: 30,
  commuteMode: 'walking',
  livingSituation: 'solo',
  roommateCount: 0,
  mustHaves: [],
  dealbreakers: [],
  fullName: '',
  phoneNumber: '',
  preferredLeaseLength: '',
}

export function profileToApi(profile: StudentProfile) {
  return {
    university: profile.university,
    campus_location: profile.campusLocation,
    max_rent: profile.maxRent,
    max_commute_minutes: profile.maxCommuteMinutes,
    commute_mode: profile.commuteMode,
    living_situation: profile.livingSituation,
    roommate_count: profile.roommateCount,
    must_haves: profile.mustHaves,
    dealbreakers: profile.dealbreakers,
    full_name: profile.fullName,
    phone_number: profile.phoneNumber,
    preferred_lease_length: profile.preferredLeaseLength,
  }
}

export function profileFromApi(data: Record<string, unknown>): StudentProfile {
  return {
    id: data.id as number | undefined,
    university: (data.university as string) ?? '',
    campusLocation: (data.campus_location as string) ?? '',
    maxRent: (data.max_rent as number) ?? 1500,
    maxCommuteMinutes: (data.max_commute_minutes as number) ?? 30,
    commuteMode: (data.commute_mode as CommuteMode) ?? 'walking',
    livingSituation:
      (data.living_situation as StudentProfile['livingSituation']) ?? 'solo',
    roommateCount: (data.roommate_count as number) ?? 0,
    mustHaves: (data.must_haves as AmenityTag[]) ?? [],
    dealbreakers: (data.dealbreakers as AmenityTag[]) ?? [],
    fullName: (data.full_name as string) ?? '',
    phoneNumber: (data.phone_number as string) ?? '',
    preferredLeaseLength: (data.preferred_lease_length as string) ?? '',
  }
}
