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
}

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
  }
}
